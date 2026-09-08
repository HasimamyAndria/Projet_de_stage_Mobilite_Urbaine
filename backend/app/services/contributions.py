"""Contributions citoyennes (mémoire processus, MVP démo)."""
from __future__ import annotations

from datetime import datetime, timezone

_MAX = 80
_ITEMS: list[dict] = []
_NEXT_ID = 1


def list_contributions() -> dict:
    return {
        "items": list(reversed(_ITEMS)),
        "count": len(_ITEMS),
        "note": "Stockage en mémoire processus (reset au redémarrage API). Pas d'identité nominative.",
    }


def add_contribution(
    *,
    kind: str,
    message: str,
    zone_id: int | None = None,
    zone_name: str | None = None,
) -> dict:
    global _NEXT_ID
    kind = kind if kind in {"besoin", "suggestion"} else "suggestion"
    text = (message or "").strip()[:500]
    if not text:
        raise ValueError("message vide")
    item = {
        "id": _NEXT_ID,
        "kind": kind,
        "message": text,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _NEXT_ID += 1
    _ITEMS.append(item)
    if len(_ITEMS) > _MAX:
        del _ITEMS[0 : len(_ITEMS) - _MAX]
    return item
