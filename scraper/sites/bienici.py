"""Scraper Bien'ici — source primaire (HTML SSR riche, validé en live).

URL de recherche : https://www.bienici.com/recherche/location/marseille-130XX/appartement
Les cartes (.ad-overview) contiennent type, pièces, surface, arrondissement, prix CC,
et la description (terrasse/parking/dispo). L'URL d'annonce encode aussi pièces + arr.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from extract import extract_attrs
from models import Listing
from sites.base import BaseScraper

BASE = "https://www.bienici.com"
# Tri par date de publication décroissante => les nouvelles annonces en premier.
SORT = "?tri=publication-desc"

RE_URL_PIECES = re.compile(r"/(\d+)pieces?/", re.I)
RE_URL_ARR = re.compile(r"/marseille-(\d{1,2})e?/", re.I)


class BienIciScraper(BaseScraper):
    site = "bienici"
    dynamic = True

    def search_urls(self, cfg: dict) -> list[str]:
        codes = cfg["criteria"]["postal_codes"]
        return [f"{BASE}/recherche/location/marseille-{cp}/appartement{SORT}" for cp in codes]

    def parse(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "lxml")
        listings: list[Listing] = []
        seen: set[str] = set()

        for a in soup.select("a[href*='/annonce/location/']"):
            href = a.get("href", "")
            if "/annonce/location/" not in href:
                continue
            url = href if href.startswith("http") else BASE + href
            key = url.split("?")[0]
            if key in seen:
                continue
            seen.add(key)

            listing = Listing(site=self.site, url=key)

            # Indices fiables depuis l'URL elle-même.
            m = RE_URL_PIECES.search(href)
            if m:
                listing.rooms = int(m.group(1))
            m = RE_URL_ARR.search(href)
            if m:
                listing.arrondissement = int(m.group(1))

            # Texte de la carte (remonter au conteneur porteur de prix+surface).
            block = self._card_text(a)
            listing.raw_text = block[:400]
            listing.title = self._title(block)
            extract_attrs(block, listing)
            listings.append(listing)

        return listings

    @staticmethod
    def _card_text(anchor) -> str:
        node = anchor
        for _ in range(7):
            if node.parent is None:
                break
            node = node.parent
            txt = node.get_text(" ", strip=True)
            if "€" in txt and ("m²" in txt or "m2" in txt):
                return txt
        return anchor.get_text(" ", strip=True)

    @staticmethod
    def _title(block: str) -> str | None:
        m = re.search(r"(Appartement|Studio|Loft|Duplex)[^.]{0,60}", block, re.I)
        return m.group(0).strip() if m else None
