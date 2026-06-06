"""Chasseur d'appartements Marseille — orchestration.

Usage :
  python scraper/main.py --dry-run      # scrape + filtre + affiche, sans notif ni état
  python scraper/main.py --test-notify  # envoie une notif de test puis quitte
  python scraper/main.py                # run réel : notifie les nouveaux biens (batch)

Variables d'env : NTFY_TOPIC (requis pour notifier), NTFY_SERVER (optionnel),
JINKA_COOKIE (optionnel), SCRAPER_HEADLESS=false (optionnel, debug navigateur).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from filters import evaluate
from models import Listing
from notify import notify_batch, send_test
from sites import get_scrapers
from state import load_seen, save_seen

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
STATE_PATH = ROOT / "state" / "seen.json"


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def collect(cfg: dict) -> tuple[list[Listing], list[str]]:
    enabled = cfg.get("enabled_sites")
    listings: list[Listing] = []
    notes: list[str] = []
    for scraper in get_scrapers(enabled):
        found, site_notes = scraper.run(cfg)
        listings.extend(found)
        notes.extend(site_notes)
    return listings, notes


def filter_listings(listings: list[Listing], cfg: dict) -> list[Listing]:
    kept = []
    for x in listings:
        if evaluate(x, cfg).passes:
            kept.append(x)
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="affiche sans notifier ni écrire l'état")
    ap.add_argument("--test-notify", action="store_true", help="envoie une notif de test")
    args = ap.parse_args()

    cfg = load_config()
    ntfy = cfg.get("ntfy", {})
    server = os.environ.get("NTFY_SERVER", ntfy.get("server", "https://ntfy.sh"))
    topic = os.environ.get("NTFY_TOPIC", "").strip()

    if args.test_notify:
        if not topic:
            print("ERREUR : NTFY_TOPIC non défini.", file=sys.stderr)
            return 2
        send_test(server=server, topic=topic)
        print(f"Notif de test envoyée sur {server}/{topic}")
        return 0

    listings, notes = collect(cfg)
    for note in notes:
        print(note)
    print(f"\nTotal annonces récupérées : {len(listings)}")

    kept = filter_listings(listings, cfg)
    print(f"Annonces conformes aux critères : {len(kept)}")

    # Dédoublonnage par clé stable.
    seen = load_seen(STATE_PATH)
    new = [x for x in kept if x.dedup_key() not in seen]
    print(f"Dont nouvelles (jamais notifiées) : {len(new)}")

    for x in new:
        flags = f"  [{', '.join(x.flags)}]" if x.flags else ""
        print(f"  - {x.site} | T{x.rooms} {x.surface}m² {x.price}€ {x.arrondissement}e{flags}\n    {x.url}")

    if args.dry_run:
        print("\n[dry-run] aucune notif envoyée, état non modifié.")
        return 0

    if new:
        if not topic:
            print("ERREUR : NTFY_TOPIC non défini — impossible de notifier.", file=sys.stderr)
            return 2
        notify_batch(new, server=server, topic=topic,
                     priority=int(ntfy.get("priority", 4)), tags=ntfy.get("tags", "house"))
        print(f"\nNotif batch envoyée ({len(new)} bien(s)) sur {server}/{topic}")
        for x in new:
            seen.add(x.dedup_key())
        save_seen(STATE_PATH, seen)
        print(f"État mis à jour : {STATE_PATH}")
    else:
        print("\nAucun nouveau bien — pas de notif.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
