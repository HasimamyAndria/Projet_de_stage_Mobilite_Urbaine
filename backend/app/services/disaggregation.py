"""
Désagrégation synthétique des flux OD (mode, heure, jour).

Les volumes en base sont des totaux journaliers mode='all'.
On applique des profils déterministes, documentés dans docs/methodes.md.
"""
from __future__ import annotations

from typing import Any

# Part de la journée (somme = 1.0) — pointe matin 7-9, soir 17-19
_HOURLY_RAW: list[float] = [
    0.004, 0.003, 0.002, 0.002, 0.004, 0.012,  # 0-5
    0.040, 0.092, 0.108, 0.052, 0.038, 0.036,  # 6-11
    0.048, 0.042, 0.038, 0.040, 0.068, 0.098,  # 12-17
    0.082, 0.052, 0.032, 0.024, 0.016, 0.009,  # 18-23
]
_H_SUM = sum(_HOURLY_RAW)
HOURLY_SHARE: list[float] = [x / _H_SUM for x in _HOURLY_RAW]

# 1 = lundi … 7 = dimanche
WEEKDAY_FACTOR: dict[int, float] = {
    1: 1.00,
    2: 1.02,
    3: 1.01,
    4: 1.03,
    5: 0.98,
    6: 0.55,
    7: 0.34,
}

WEEKDAY_LABELS: dict[int, str] = {
    1: "Lundi",
    2: "Mardi",
    3: "Mercredi",
    4: "Jeudi",
    5: "Vendredi",
    6: "Samedi",
    7: "Dimanche",
}

MODES = ("car", "bus", "walk", "bike")

# Facteurs d'émission MVP (kg CO₂ / voyageur-km) — ordres de grandeur ADEME
CO2_KG_PER_PKM: dict[str, float] = {
    "car": 0.180,
    "bus": 0.080,
    "walk": 0.0,
    "bike": 0.0,
    "all": 0.120,
}


def mode_shares_for_distance(distance_km: float | None) -> dict[str, float]:
    """Parts modales proxy selon la distance OD."""
    d = float(distance_km or 5.0)
    if d < 2.0:
        return {"walk": 0.40, "bike": 0.25, "bus": 0.15, "car": 0.20}
    if d < 8.0:
        return {"walk": 0.05, "bike": 0.15, "bus": 0.35, "car": 0.45}
    return {"walk": 0.01, "bike": 0.04, "bus": 0.30, "car": 0.65}


def profiles_payload() -> dict[str, Any]:
    return {
        "hourly": HOURLY_SHARE,
        "weekday": WEEKDAY_FACTOR,
        "weekday_labels": WEEKDAY_LABELS,
        "modes": list(MODES),
        "note": (
            "Profils synthétiques déterministes (pas d'enquête ménage). "
            "Le volume horaire affiché = volume journalier × part horaire × 24 "
            "(l'heure moyenne retrouve le volume journalier)."
        ),
    }


def volume_factor(
    *,
    hour: int | None = None,
    weekday: int | None = None,
    mode: str | None = None,
    distance_km: float | None = None,
) -> float:
    """
    Facteur à appliquer au volume journalier mode=all.

    - heure : part[h] * 24  (moyenne = 1)
    - jour : facteur calendaire
    - mode : part modale selon la distance
    """
    factor = 1.0
    if hour is not None:
        h = max(0, min(23, int(hour)))
        factor *= HOURLY_SHARE[h] * 24.0
    if weekday is not None:
        w = int(weekday)
        factor *= WEEKDAY_FACTOR.get(w, 1.0)
    if mode and mode != "all":
        shares = mode_shares_for_distance(distance_km)
        factor *= shares.get(mode, 0.0)
    return factor


def scale_volume(
    daily: int | float,
    *,
    hour: int | None = None,
    weekday: int | None = None,
    mode: str | None = None,
    distance_km: float | None = None,
) -> int:
    raw = float(daily) * volume_factor(
        hour=hour, weekday=weekday, mode=mode, distance_km=distance_km
    )
    return max(0, int(round(raw)))


def modal_split_volumes(daily: int | float, distance_km: float | None) -> dict[str, int]:
    shares = mode_shares_for_distance(distance_km)
    total = float(daily)
    return {m: int(round(total * shares[m])) for m in MODES}
