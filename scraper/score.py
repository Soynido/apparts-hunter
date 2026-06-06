"""Scoring des offres pour faire remonter les meilleures opportunités.

Score 0-100. Composantes (sur des annonces déjà filtrées comme conformes) :
  - Rapport €/m² (dominant)   : moins cher au m² = mieux
  - Surface au-delà du minimum : plus grand = mieux
  - Terrasse/balcon/jardin confirmé
  - Parking confirmé
  - Bonus pièces (T4/T5 dans le budget = bonne affaire)
  - Pénalités : signaux d'arnaque, infos manquantes ("à vérifier")
"""
from __future__ import annotations

from models import Listing

# Bornes €/m² typiques d'un appartement entier à Marseille pour normaliser la valeur.
PPM2_BEST = 11.0    # très bonne affaire
PPM2_WORST = 22.0   # cher


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_score(listing: Listing, cfg: dict) -> int:
    c = cfg["criteria"]
    surface_min = c["surface_min"]
    rooms_min = c["rooms_min"]
    score = 0.0

    # Valeur €/m² (jusqu'à 50 pts)
    if listing.price and listing.surface and listing.surface > 0:
        ppm2 = listing.price / listing.surface
        frac = (PPM2_WORST - ppm2) / (PPM2_WORST - PPM2_BEST)
        score += _clamp(frac, 0.0, 1.0) * 50
    else:
        score += 25  # neutre si inconnu

    # Surface au-delà du minimum (jusqu'à 15 pts, satura à +40 m²)
    if listing.surface:
        extra = _clamp(listing.surface - surface_min, 0, 40)
        score += extra / 40 * 15

    # Extérieur confirmé (12 pts)
    if listing.exterior is True:
        score += 12
    # Parking confirmé (12 pts)
    if listing.parking is True:
        score += 12

    # Bonus pièces (jusqu'à 10 pts : T4 = +5, T5+ = +10)
    if listing.rooms:
        score += _clamp((listing.rooms - rooms_min) * 5, 0, 10)

    # Pénalités
    for f in listing.flags:
        if "arnaque" in f:
            score -= 25
        elif "à vérifier" in f:
            score -= 2

    return int(_clamp(round(score), 0, 100))


def is_top_deal(score: int) -> bool:
    return score >= 70


def rank(listings: list[Listing], cfg: dict) -> list[Listing]:
    """Calcule le score de chaque offre et renvoie la liste triée (meilleures d'abord)."""
    for x in listings:
        x.score = compute_score(x, cfg)
    return sorted(listings, key=lambda x: (x.score or 0), reverse=True)
