"""Scraper PAP — best-effort.

PAP filtre par identifiants géo internes (`geo_objets_ids`) non devinables : les URL
de recherche doivent être fournies dans config.yaml (sites.pap.search_urls), récupérées
une fois depuis le site. Sans elles, le scraper se contente d'une note.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from extract import extract_attrs
from models import Listing
from sites.base import BaseScraper

BASE = "https://www.pap.fr"
RE_LISTING = re.compile(r"/annonce/[a-z0-9-]+-r\d+", re.I)


class PapScraper(BaseScraper):
    site = "pap"
    dynamic = False  # PAP passe avec le fetch léger (TLS impersonation)

    def search_urls(self, cfg: dict) -> list[str]:
        return cfg.get("sites", {}).get("pap", {}).get("search_urls", []) or []

    def parse(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[Listing] = []
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
            block = self._card_text(a)
            listing.raw_text = block[:400]
            extract_attrs(block, listing)
            listings.append(listing)
        return listings

    @staticmethod
    def _card_text(anchor) -> str:
        node = anchor
        for _ in range(6):
            if node.parent is None:
                break
            node = node.parent
            txt = node.get_text(" ", strip=True)
            if "€" in txt and ("m²" in txt or "m2" in txt):
                return txt
        return anchor.get_text(" ", strip=True)
