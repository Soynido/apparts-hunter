"""Scraper SeLoger — best-effort. Bloqué par DataDome dans la majorité des cas
(403 même en IP résidentielle). Conservé pour basculer facilement si l'accès s'ouvre
(IP différente, proxy résidentiel). URLs de recherche dans config.yaml."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from extract import extract_attrs
from models import Listing
from sites.base import BaseScraper

BASE = "https://www.seloger.com"
RE_LISTING = re.compile(r"seloger\.com/annonces/.+?\d{6,}|/annonces/.+?/\d{6,}", re.I)


class SeLogerScraper(BaseScraper):
    site = "seloger"
    dynamic = False   # bloqué DataDome de toute façon => échec rapide (~0.4s, pas de navigateur)

    def search_urls(self, cfg: dict) -> list[str]:
        return cfg.get("sites", {}).get("seloger", {}).get("search_urls", []) or []

    def parse(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "lxml")
        out: list[Listing] = []
        seen: set[str] = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not RE_LISTING.search(href):
                continue
            url = href if href.startswith("http") else BASE + href
            key = url.split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            listing = Listing(site=self.site, url=key, title=a.get_text(" ", strip=True) or None)
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
