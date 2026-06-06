"""Registre des scrapers par site."""
from __future__ import annotations

from sites.base import BaseScraper
from sites.bienici import BienIciScraper
from sites.leboncoin import LeBonCoinScraper
from sites.pap import PapScraper
from sites.seloger import SeLogerScraper
from sites.jinka import JinkaScraper

ALL_SCRAPERS: dict[str, BaseScraper] = {
    "bienici": BienIciScraper(),
    "pap": PapScraper(),
    "seloger": SeLogerScraper(),
    "leboncoin": LeBonCoinScraper(),
    "jinka": JinkaScraper(),
}


def get_scrapers(enabled: list[str] | None = None) -> list[BaseScraper]:
    if not enabled:
        return list(ALL_SCRAPERS.values())
    return [ALL_SCRAPERS[name] for name in enabled if name in ALL_SCRAPERS]
