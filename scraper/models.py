"""Structures de données partagées."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlsplit, urlunsplit


@dataclass
class Listing:
    """Une annonce immobilière extraite d'un email d'alerte."""

    site: str                       # seloger | pap | bienici | leboncoin | jinka
    url: str                        # URL de l'annonce
    title: Optional[str] = None
    price: Optional[int] = None     # loyer en €
    surface: Optional[float] = None # m²
    rooms: Optional[int] = None     # nombre de pièces
    bedrooms: Optional[int] = None  # nombre de chambres
    postal_code: Optional[int] = None
    arrondissement: Optional[int] = None
    exterior: Optional[bool] = None # terrasse/balcon/jardin détecté
    parking: Optional[bool] = None  # parking détecté
    available_from: Optional[str] = None
    raw_text: str = ""              # contexte texte pour debug
    flags: list[str] = field(default_factory=list)  # ex: "parking à vérifier"

    def canonical_url(self) -> str:
        """URL sans query/fragment, host en minuscule — pour le dédoublonnage."""
        parts = urlsplit(self.url)
        netloc = parts.netloc.lower()
        path = parts.path.rstrip("/")
        return urlunsplit((parts.scheme or "https", netloc, path, "", ""))

    def dedup_key(self) -> str:
        """Clé stable basée sur l'URL canonique complète (sans query/fragment).

        On hashe l'URL entière plutôt qu'un ID extrait : c'est le choix le plus sûr
        contre les FAUX doublons (qui feraient rater une vraie nouvelle annonce),
        ex. deux annonces d'une même agence `ag130161-529643066` / `ag130161-529643070`.
        """
        return hashlib.sha1(self.canonical_url().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)
