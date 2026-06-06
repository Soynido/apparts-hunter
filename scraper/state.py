"""Persistance de l'état de dédoublonnage (annonces déjà notifiées)."""
from __future__ import annotations

import json
from pathlib import Path


def load_seen(path: str | Path) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return set(data.get("seen", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(path: str | Path, seen: set[str], max_keep: int = 5000) -> None:
    """Sauvegarde les clés vues. Tronque pour éviter une croissance infinie."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    kept = list(seen)[-max_keep:]
    p.write_text(
        json.dumps({"seen": kept, "count": len(kept)}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )
