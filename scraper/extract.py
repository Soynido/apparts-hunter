"""Extraction d'attributs immobiliers depuis un bloc de texte (regex robustes).

Calibré sur des cartes d'annonces réelles (Bien'ici, PAP). Exemple de texte type :
  "Appartement meublé 2 pièces 48 m² 13008 Marseille 8e (Saint-Giniez)
   1 200 € par mois charges comprises TERRASSE ... Disponible à partir du 08/09/2026"
"""
from __future__ import annotations

import re
from typing import Optional

from models import Listing

RE_PRICE = re.compile(r"(\d[\d  .]{1,7})\s*€")
RE_SURFACE = re.compile(r"(\d{2,3}(?:[.,]\d{1,2})?)\s*m(?:²|2)\b", re.I)
RE_ROOMS_T = re.compile(r"\bT\s*(\d)\b", re.I)
RE_ROOMS_P = re.compile(r"(\d)\s*pi[eè]ces?", re.I)
RE_BEDROOMS = re.compile(r"(\d)\s*chambres?", re.I)
RE_POSTAL = re.compile(r"\b(130\d{2})\b")
RE_ARR = re.compile(r"Marseille\s+(\d{1,2})\s*(?:e|er|ème|eme)\b", re.I)
RE_EXTERIOR = re.compile(r"terrasse|balcon|jardin|loggia|patio|rooftop", re.I)
RE_PARKING = re.compile(r"parking|garage|stationnement|place\s+de\s+parking", re.I)
RE_AVAILABLE = re.compile(
    r"disponib\w*\s+(?:le|à partir(?: du)?|d[eè]s)\s+"
    r"(\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{2,4}|\d{1,2}\s+\w+\.?\s*\d{0,4})",
    re.I,
)


def _to_int_price(raw: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return None
    val = int(digits)
    return val if 200 <= val <= 10000 else None  # garde-fou loyer plausible


def extract_attrs(text: str, listing: Listing) -> None:
    """Remplit les attributs manquants de `listing` à partir d'un bloc de texte."""
    text = text.replace("\xa0", " ").replace(" ", " ")

    if listing.price is None:
        prices = [p for p in (_to_int_price(m.group(1)) for m in RE_PRICE.finditer(text)) if p]
        if prices:
            listing.price = max(prices)  # le loyer est en général le plus gros montant

    if listing.surface is None:
        m = RE_SURFACE.search(text)
        if m:
            listing.surface = float(m.group(1).replace(",", "."))

    if listing.rooms is None:
        m = RE_ROOMS_T.search(text) or RE_ROOMS_P.search(text)
        if m:
            listing.rooms = int(m.group(1))

    if listing.bedrooms is None:
        m = RE_BEDROOMS.search(text)
        if m:
            listing.bedrooms = int(m.group(1))

    if listing.postal_code is None:
        m = RE_POSTAL.search(text)
        if m:
            listing.postal_code = int(m.group(1))
            listing.arrondissement = listing.postal_code % 100
    if listing.arrondissement is None:
        m = RE_ARR.search(text)
        if m:
            listing.arrondissement = int(m.group(1))

    if listing.exterior is None and RE_EXTERIOR.search(text):
        listing.exterior = True

    if listing.parking is None and RE_PARKING.search(text):
        listing.parking = True

    if listing.available_from is None:
        m = RE_AVAILABLE.search(text)
        if m:
            listing.available_from = m.group(1).strip()
