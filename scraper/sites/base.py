"""Socle commun des scrapers de sites : fetch Scrapling + détection de blocage."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from models import Listing

BLOCK_SIGNALS = (
    "datadome", "captcha", "access denied", "verify you are human",
    "are you a robot", "challenge-platform", "px-captcha", "請稍候",
)


@dataclass
class FetchResult:
    url: str
    status: Optional[int]
    html: str
    blocked: bool
    error: Optional[str] = None


def _looks_blocked(status: Optional[int], html: str) -> bool:
    if status is not None and status in (401, 403, 429) or (status and status >= 500):
        return True
    low = html.lower()
    return any(sig in low for sig in BLOCK_SIGNALS)


def fetch(url: str, *, dynamic: bool = True, wait_selector: Optional[str] = None,
          network_idle: bool = True, timeout_ms: int = 45000,
          cookies: Optional[list[dict]] = None) -> FetchResult:
    """Récupère une page. `dynamic=True` => navigateur furtif (anti-bot).

    `wait_selector` + `network_idle=False` = beaucoup plus rapide (on s'arrête dès que
    les cartes d'annonces apparaissent au lieu d'attendre la fin du trafic réseau).

    Échoue proprement : renvoie un FetchResult avec blocked/error plutôt que de lever.
    """
    headless = os.environ.get("SCRAPER_HEADLESS", "true").lower() != "false"
    try:
        if dynamic:
            from scrapling.fetchers import StealthyFetcher
            kwargs = dict(headless=headless, network_idle=network_idle, timeout=timeout_ms)
            if wait_selector:
                kwargs["wait_selector"] = wait_selector
            if cookies:
                kwargs["cookies"] = cookies
            page = StealthyFetcher.fetch(url, **kwargs)
        else:
            from scrapling.fetchers import Fetcher
            page = Fetcher.get(url, stealthy_headers=True, timeout=int(timeout_ms / 1000))
        html = getattr(page, "html_content", "") or ""
        status = getattr(page, "status", None)
        return FetchResult(url, status, html, _looks_blocked(status, html))
    except Exception as e:  # réseau, timeout, navigateur indisponible…
        return FetchResult(url, None, "", True, error=f"{type(e).__name__}: {e}")


class BaseScraper:
    site: str = "base"
    dynamic: bool = True
    wait_selector: Optional[str] = None   # accélère le rendu si défini
    network_idle: bool = True             # mettre False avec wait_selector pour la vitesse

    def search_urls(self, cfg: dict) -> list[str]:
        """URLs de recherche à visiter (une par arrondissement en général)."""
        raise NotImplementedError

    def parse(self, html: str, source_url: str) -> list[Listing]:
        """Extrait les annonces d'une page de résultats."""
        raise NotImplementedError

    def run(self, cfg: dict) -> tuple[list[Listing], list[str]]:
        """Retourne (annonces, notes). Ne lève jamais : capture les erreurs en notes."""
        listings: list[Listing] = []
        notes: list[str] = []
        for url in self.search_urls(cfg):
            res = fetch(url, dynamic=self.dynamic,
                        wait_selector=self.wait_selector, network_idle=self.network_idle)
            if res.blocked or res.error or not res.html:
                notes.append(
                    f"[{self.site}] bloqué/échec sur {url} "
                    f"(status={res.status}, err={res.error})"
                )
                continue
            try:
                found = self.parse(res.html, url)
                listings.extend(found)
                notes.append(f"[{self.site}] {len(found)} annonce(s) depuis {url}")
            except Exception as e:
                notes.append(f"[{self.site}] parse error sur {url}: {type(e).__name__}: {e}")
        return listings, notes
