"""Notifications push via ntfy.sh — UN SEUL message batch listant toutes les offres."""
from __future__ import annotations

import os

import requests

from models import Listing

MAX_IN_BODY = 25  # au-delà, on tronque le corps pour rester sous la limite ntfy


def _block(listing: Listing, idx: int) -> str:
    """Un bloc par offre : ligne d'infos + URL BRUTE (auto-cliquable sur iOS/Android)."""
    bits = [f"T{listing.rooms}" if listing.rooms else "T?"]
    if listing.surface:
        bits.append(f"{int(listing.surface)}m²")
    if listing.price:
        bits.append(f"{listing.price}€")
    if listing.arrondissement:
        bits.append(f"{listing.arrondissement}e")
    head = f"{idx}. " + " · ".join(bits) + f" ({listing.site})"
    flags = f"\n   ⚠️ {', '.join(listing.flags)}" if listing.flags else ""
    # URL brute sur sa propre ligne => détectée comme lien tappable automatiquement.
    return f"{head}{flags}\n{listing.url}"


def notify_batch(listings: list[Listing], *, server: str, topic: str,
                 priority: int = 4, tags: str = "house") -> bool:
    if not listings:
        return False
    n = len(listings)
    shown = listings[:MAX_IN_BODY]
    blocks = [_block(x, i + 1) for i, x in enumerate(shown)]
    if n > MAX_IN_BODY:
        blocks.append(f"… + {n - MAX_IN_BODY} autre(s)")
    body = "\n\n".join(blocks)

    title = f"{n} nouveau{'x' if n > 1 else ''} bien{'s' if n > 1 else ''} Marseille"

    # Boutons d'action : jusqu'à 3 "view" qui ouvrent directement une annonce
    # (labels/URLs en ASCII obligatoire dans l'en-tête).
    actions = "; ".join(
        f"view, Ouvrir #{i + 1}, {x.url}, clear=false"
        for i, x in enumerate(shown[:3])
    )

    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": tags,
        "Click": shown[0].url,   # tap sur la notif => 1re annonce
        "Actions": actions,      # boutons cliquables (max 3)
    }
    resp = requests.post(f"{server.rstrip('/')}/{topic}",
                         data=body.encode("utf-8"), headers=headers, timeout=20)
    resp.raise_for_status()
    return True


def send_test(*, server: str, topic: str) -> None:
    requests.post(
        f"{server.rstrip('/')}/{topic}",
        data="Test de configuration — le chasseur d'appartements Marseille est opérationnel ✅".encode(),
        headers={"Title": "Test ntfy", "Priority": "3", "Tags": "white_check_mark"},
        timeout=20,
    ).raise_for_status()
