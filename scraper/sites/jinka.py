"""Scraper Jinka — best-effort. Les résultats sont derrière une authentification
(/alerts). Nécessite un cookie de session fourni via la variable d'env JINKA_COOKIE
(format JSON: liste d'objets {name, value, domain}). Sans cookie => note et skip.

Note légale : Jinka a été condamné en justice pour la republication d'annonces.
Usage strictement personnel ici (lecture de sa propre alerte)."""
from __future__ import annotations

import json
import os
import re

from bs4 import BeautifulSoup

from extract import extract_attrs
from models import Listing
from sites.base import BaseScraper, fetch

RE_OUT = re.compile(r"(seloger|leboncoin|pap\.fr|bienici|logic-immo)\.", re.I)


class JinkaScraper(BaseScraper):
    site = "jinka"
    dynamic = True

    def search_urls(self, cfg: dict) -> list[str]:
        return cfg.get("sites", {}).get("jinka", {}).get("search_urls", []) or []

    def _cookies(self) -> list[dict] | None:
        raw = os.environ.get("JINKA_COOKIE", "").strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else None
        except json.JSONDecodeError:
            # Format "name=value; name2=value2" -> liste pour le domaine jinka.fr
            jar = []
            for part in raw.split(";"):
                if "=" in part:
                    n, v = part.strip().split("=", 1)
                    jar.append({"name": n, "value": v, "domain": ".jinka.fr", "path": "/"})
            return jar or None

    def run(self, cfg: dict) -> tuple[list[Listing], list[str]]:
        cookies = self._cookies()
        urls = self.search_urls(cfg)
        if not urls:
            return [], ["[jinka] aucune search_url configurée — ignoré"]
        if not cookies:
            return [], ["[jinka] JINKA_COOKIE absent (login requis) — ignoré"]
        listings: list[Listing] = []
        notes: list[str] = []
        for url in urls:
            res = fetch(url, dynamic=True, cookies=cookies)
            if res.blocked or res.error or not res.html:
                notes.append(f"[jinka] échec sur {url} (status={res.status}, err={res.error})")
                continue
            found = self.parse(res.html, url)
            listings.extend(found)
            notes.append(f"[jinka] {len(found)} annonce(s) depuis {url}")
        return listings, notes

    def parse(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "lxml")
        out: list[Listing] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not href.startswith("http") or not RE_OUT.search(href):
                continue
            key = href.split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            listing = Listing(site="jinka", url=href, title=a.get_text(" ", strip=True) or None)
            block = _ctx(a)
            listing.raw_text = block[:400]
            extract_attrs(block, listing)
            out.append(listing)
        return out


def _ctx(anchor) -> str:
    node = anchor
    for _ in range(6):
        if node.parent is None:
            break
        node = node.parent
        txt = node.get_text(" ", strip=True)
        if "€" in txt and ("m²" in txt or "m2" in txt):
            return txt
    return anchor.get_text(" ", strip=True)
