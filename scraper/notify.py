"""Notifications push via ntfy.sh — UN SEUL message batch listant toutes les offres."""
from __future__ import annotations

import os

import requests

from models import Listing
from score import is_top_deal

MAX_IN_BODY = 25  # au-delà, on tronque le corps pour rester sous la limite ntfy


def _block(listing: Listing, idx: int) -> str:
    """Un bloc par offre en MARKDOWN (liens cliquables dans la page web ntfy)."""
    bits = [f"T{listing.rooms}" if listing.rooms else "T?"]
    if listing.surface:
        bits.append(f"{int(listing.surface)}m²")
    if listing.price:
        bits.append(f"{listing.price}€")
    if listing.arrondissement:
        bits.append(f"{listing.arrondissement}e")
    label = " · ".join(bits) + f" ({listing.site})"
    flags = f" — ⚠️ {', '.join(listing.flags)}" if listing.flags else ""
    # Préfixe score : ⭐ pour les top deals, sinon la note brute.
    if listing.score is not None:
        star = "⭐ " if is_top_deal(listing.score) else ""
        prefix = f"{star}[{listing.score}] "
    else:
        prefix = ""
    # Lien markdown : rendu cliquable + copiable sur la page web du topic.
    return f"{idx}. {prefix}[{label}]({listing.url}){flags}"


def notify_batch(listings: list[Listing], *, server: str, topic: str,
                 priority: int = 4, tags: str = "house") -> bool:
    if not listings:
        return False
    n = len(listings)
    shown = listings[:MAX_IN_BODY]
    blocks = [_block(x, i + 1) for i, x in enumerate(shown)]
    if n > MAX_IN_BODY:
        blocks.append(f"… + {n - MAX_IN_BODY} autre(s)")
    topic_url = f"{server.rstrip('/')}/{topic}"
    body = "\n".join(blocks) + f"\n\n👉 Tous les liens cliquables : {topic_url}"

    title = f"{n} nouveau{'x' if n > 1 else ''} bien{'s' if n > 1 else ''} Marseille"

    # Boutons "view" (max 3) : ouvrent directement une annonce ; + un bouton vers la
    # page web du topic où TOUS les liens sont cliquables et copiables.
    parts = [f"view, Ouvrir {i + 1}, {x.url}, clear=false" for i, x in enumerate(shown[:2])]
    parts.append(f"view, Voir tout, {topic_url}, clear=false")
    actions = "; ".join(parts)

    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": tags,
        "Markdown": "yes",       # liens cliquables dans la page web / app Android
        "Click": topic_url,      # tap sur la notif => page web avec tous les liens cliquables
        "Actions": actions,
    }
    resp = requests.post(topic_url, data=body.encode("utf-8"), headers=headers, timeout=20)
    resp.raise_for_status()
    return True


def send_test(*, server: str, topic: str) -> None:
    requests.post(
        f"{server.rstrip('/')}/{topic}",
        data="Test de configuration — le chasseur d'appartements Marseille est opérationnel ✅".encode(),
        headers={"Title": "Test ntfy", "Priority": "3", "Tags": "white_check_mark"},
        timeout=20,
    ).raise_for_status()
