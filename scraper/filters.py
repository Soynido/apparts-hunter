"""Application des critères de recherche (durs vs souples)."""
from __future__ import annotations

from dataclasses import dataclass

from models import Listing


@dataclass
class Verdict:
    passes: bool
    reject_reason: str | None = None


def evaluate(listing: Listing, cfg: dict) -> Verdict:
    """Filtre une annonce. Critères DURS => rejet si connu et non conforme.
    Critères SOUPLES => on garde et on ajoute un flag "à vérifier"."""
    c = cfg["criteria"]
    strict_ext = c.get("strict_exterior", False)
    strict_park = c.get("strict_parking", False)
    flags: list[str] = []

    # --- DURS (rejet si l'info est connue et non conforme) ---
    if listing.rooms is not None and listing.rooms < c["rooms_min"]:
        return Verdict(False, f"{listing.rooms} pièces < {c['rooms_min']}")
    if listing.bedrooms is not None and listing.bedrooms < c["bedrooms_min"]:
        return Verdict(False, f"{listing.bedrooms} chambres < {c['bedrooms_min']}")
    if listing.price is not None and listing.price > c["rent_max"]:
        return Verdict(False, f"{listing.price}€ > {c['rent_max']}€")
    if listing.surface is not None and listing.surface < c["surface_min"]:
        return Verdict(False, f"{listing.surface}m² < {c['surface_min']}m²")
    if listing.arrondissement is not None and listing.arrondissement not in c["arrondissements"]:
        return Verdict(False, f"arr. {listing.arrondissement} hors zone")

    # --- SOUPLES (flag si inconnu ; rejet seulement si strict_* activé) ---
    if listing.exterior is not True:
        if strict_ext:
            return Verdict(False, "extérieur non confirmé")
        flags.append("extérieur à vérifier")
    if listing.parking is not True:
        if strict_park:
            return Verdict(False, "parking non confirmé")
        flags.append("parking à vérifier")

    # Infos manquantes => flag (sans rejet)
    if listing.rooms is None:
        flags.append("pièces à vérifier")
    if listing.price is None:
        flags.append("prix à vérifier")
    if listing.surface is None:
        flags.append("surface à vérifier")
    if listing.available_from:
        flags.append(f"dispo {listing.available_from}")

    # Heuristique anti-arnaque : loyer anormalement bas pour la surface (Marseille ~15-25 €/m²),
    # ou référence d'agence en email perso (gmail/hotmail/...) dans l'URL.
    if listing.price and listing.surface and listing.surface > 0:
        if listing.price / listing.surface < 8:
            flags.append("⚠️ prix suspect (arnaque ?)")
    if any(d in listing.url.lower() for d in ("gmail", "hotmail", "yahoo", "outlook")):
        flags.append("⚠️ contact perso (arnaque ?)")

    listing.flags = flags
    return Verdict(True)
