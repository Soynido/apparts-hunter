"""Application des critères de recherche (durs vs souples)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from models import Listing

# Mots-clés indiquant une colocation / location de chambre (à exclure : on veut un appart ENTIER).
RE_COLOC = re.compile(
    r"\bcoloc\w*|coliving|co-living|colive|chambre\s+(?:meubl\w+\s+)?(?:dans|en|à louer)"
    r"|location\s+de\s+chambre|room\s+in|chambre\s+priv\w+",
    re.I,
)


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
    min_ppm2 = c.get("min_price_per_m2", 9)
    flags: list[str] = []

    # --- EXCLURE LES COLOCATIONS (on veut un appartement ENTIER) ---
    haystack = f"{listing.title or ''} {listing.raw_text or ''} {listing.url}"
    if c.get("exclude_colocation", True) and RE_COLOC.search(haystack):
        return Verdict(False, "colocation / chambre")
    # Loyer/m² anormalement bas => colocation déguisée ou arnaque (gros m², petit loyer).
    if listing.price and listing.surface and listing.surface > 0:
        if listing.price / listing.surface < min_ppm2:
            return Verdict(False, f"{listing.price/listing.surface:.1f} €/m² < {min_ppm2} (coloc/arnaque ?)")

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

    # Référence d'agence en email perso (gmail/hotmail/...) dans l'URL => signal d'arnaque.
    if any(d in listing.url.lower() for d in ("gmail", "hotmail", "yahoo", "outlook")):
        flags.append("⚠️ contact perso (arnaque ?)")

    listing.flags = flags
    return Verdict(True)
