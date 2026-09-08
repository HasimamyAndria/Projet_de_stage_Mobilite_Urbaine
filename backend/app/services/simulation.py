"""
M4 — Simulation what-if paramétrique (MVP).

Modèle : élasticités / reports modaux forfaitaires documentés.
Pas un affectation trafic ni un modèle 4 étapes complet.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.disaggregation import CO2_KG_PER_PKM, mode_shares_for_distance
from app.services.od import list_od_rows

ACTIONS = {
    "add_tc_stop": "Ajout d'un arrêt TC",
    "add_bike_lane": "Ajout d'une piste cyclable",
    "add_park_ride": "Parking relais",
    "add_satellite_office": "Bureau satellite / tiers-lieu",
    "zoning_housing": "Zonage : logements (friche → habitat)",
    "zoning_jobs": "Zonage : emplois (mixité fonctionnelle)",
    "telework": "Télétravail",
}

TELEWORK_DAY_SHARE = {
    "full_remote": 1.00,
    "hybrid_1_2": 0.30,
    "hybrid_3_4": 0.70,
}


def _baseline_indicators(rows) -> dict[str, Any]:
    trips = 0
    km = 0.0
    time_h = 0.0
    mode_trips = {"car": 0, "bus": 0, "walk": 0, "bike": 0}
    co2 = 0.0

    for r in rows:
        n = int(r.passenger_count)
        dist = float(r.average_distance or 0)
        minutes = float(r.average_time or 0)
        trips += n
        km += n * dist
        time_h += n * minutes / 60.0
        shares = mode_shares_for_distance(dist)
        for mode, share in shares.items():
            mt = n * share
            mode_trips[mode] += mt
            co2 += mt * dist * CO2_KG_PER_PKM.get(mode, 0.12)

    if trips <= 0:
        return {
            "trips": 0,
            "km": 0.0,
            "time_h": 0.0,
            "avg_time_min": 0.0,
            "modal_share": {m: 0.0 for m in mode_trips},
            "co2_t": 0.0,
        }

    return {
        "trips": int(trips),
        "km": round(km, 1),
        "time_h": round(time_h, 1),
        "avg_time_min": round(time_h * 60.0 / trips, 1),
        "modal_share": {
            m: round(v / trips, 3) for m, v in mode_trips.items()
        },
        "co2_t": round(co2 / 1000.0, 2),
    }


def _copy_ind(ind: dict) -> dict:
    return {
        "trips": ind["trips"],
        "km": ind["km"],
        "time_h": ind["time_h"],
        "avg_time_min": ind["avg_time_min"],
        "modal_share": dict(ind["modal_share"]),
        "co2_t": ind["co2_t"],
    }


def _apply_modal_shift(ind: dict, from_mode: str, to_mode: str, share: float) -> dict:
    """Report d'une part des voyages from→to, CO2 et km inchangés (même OD)."""
    out = _copy_ind(ind)
    moved = out["modal_share"].get(from_mode, 0) * share
    out["modal_share"][from_mode] = round(
        out["modal_share"].get(from_mode, 0) - moved, 3
    )
    out["modal_share"][to_mode] = round(
        out["modal_share"].get(to_mode, 0) + moved, 3
    )
    # CO2 : on retire l'écart d'émission sur les km VP reportés
    km_moved = out["km"] * moved
    delta_co2_kg = km_moved * (
        CO2_KG_PER_PKM.get(to_mode, 0) - CO2_KG_PER_PKM.get(from_mode, 0.18)
    )
    out["co2_t"] = round(max(0.0, out["co2_t"] + delta_co2_kg / 1000.0), 2)
    return out


def simulate(
    db: Session,
    action: str,
    zone_id: int | None = None,
    intensity: float = 0.25,
    telework_rate: float = 0.15,
    telework_pattern: str = "hybrid_1_2",
) -> dict:
    action = (action or "add_tc_stop").strip()
    if action not in ACTIONS:
        action = "add_tc_stop"
    intensity = max(0.05, min(1.0, float(intensity)))
    telework_rate = max(0.0, min(0.8, float(telework_rate)))
    pattern = telework_pattern if telework_pattern in TELEWORK_DAY_SHARE else "hybrid_1_2"

    rows = list_od_rows(db)
    baseline = _baseline_indicators(rows)
    scenario = _copy_ind(baseline)
    assumptions: list[str] = []

    zone_name = None
    if zone_id is not None:
        for r in rows:
            if int(r.origin_zone_id) == int(zone_id):
                zone_name = r.origin_name
                break
            if int(r.destination_zone_id) == int(zone_id):
                zone_name = r.destination_name
                break

    if action == "add_tc_stop":
        scenario = _apply_modal_shift(scenario, "car", "bus", 0.12 * intensity / 0.25)
        scenario["avg_time_min"] = round(scenario["avg_time_min"] * (1 - 0.04 * intensity), 1)
        scenario["time_h"] = round(scenario["trips"] * scenario["avg_time_min"] / 60.0, 1)
        assumptions.append(
            "Arrêt TC : 12% des VP de la zone (intensité 0.25) reportés vers le bus, "
            "temps moyen -4%."
        )
    elif action == "add_bike_lane":
        scenario = _apply_modal_shift(scenario, "car", "bike", 0.08 * intensity / 0.25)
        assumptions.append("Piste cyclable : 8% des VP reportés vers le vélo (corridors < 5 km, proxy global).")
    elif action == "add_park_ride":
        scenario = _apply_modal_shift(scenario, "car", "bus", 0.15 * intensity / 0.25)
        scenario["km"] = round(scenario["km"] * (1 - 0.10 * intensity), 1)
        scenario["co2_t"] = round(scenario["co2_t"] * (1 - 0.12 * intensity), 2)
        assumptions.append(
            "P+R : 15% VP→bus + 10% km centre (proxy entrée de ville)."
        )
    elif action == "add_satellite_office":
        reduce = 0.18 * intensity
        scenario["km"] = round(scenario["km"] * (1 - reduce), 1)
        scenario["time_h"] = round(scenario["time_h"] * (1 - reduce), 1)
        scenario["avg_time_min"] = round(
            scenario["time_h"] * 60.0 / max(scenario["trips"], 1), 1
        )
        scenario["co2_t"] = round(scenario["co2_t"] * (1 - reduce), 2)
        assumptions.append(
            "Bureau satellite : 18% des km domicile-travail évités (relocalisation partielle)."
        )
    elif action == "zoning_housing":
        reduce = 0.10 * intensity
        scenario["km"] = round(scenario["km"] * (1 - reduce), 1)
        scenario["time_h"] = round(scenario["time_h"] * (1 - reduce * 0.8), 1)
        scenario["co2_t"] = round(scenario["co2_t"] * (1 - reduce), 2)
        scenario["avg_time_min"] = round(
            scenario["time_h"] * 60.0 / max(scenario["trips"], 1), 1
        )
        assumptions.append("Friche → logements près des emplois : raccourcit une part des navettes.")
    elif action == "zoning_jobs":
        reduce = 0.12 * intensity
        scenario["km"] = round(scenario["km"] * (1 - reduce), 1)
        scenario["time_h"] = round(scenario["time_h"] * (1 - reduce), 1)
        scenario["co2_t"] = round(scenario["co2_t"] * (1 - reduce), 2)
        scenario["avg_time_min"] = round(
            scenario["time_h"] * 60.0 / max(scenario["trips"], 1), 1
        )
        assumptions.append("Emplois ajoutés en zone résidentielle : mixité fonctionnelle.")
    elif action == "telework":
        day_share = TELEWORK_DAY_SHARE[pattern]
        # ~70 % des volumes OD sont traités comme navettes
        removed = 0.70 * telework_rate * day_share
        scenario["trips"] = int(round(scenario["trips"] * (1 - removed)))
        scenario["km"] = round(scenario["km"] * (1 - removed), 1)
        scenario["time_h"] = round(scenario["time_h"] * (1 - removed), 1)
        scenario["co2_t"] = round(scenario["co2_t"] * (1 - removed), 2)
        assumptions.append(
            f"Télétravail {pattern} à {int(telework_rate*100)}% des salariés, "
            f"{int(day_share*100)}% des jours. Sans migration résidentielle."
        )

    def delta(key: str) -> float:
        b, s = baseline[key], scenario[key]
        if isinstance(b, (int, float)) and isinstance(s, (int, float)):
            return round(float(s) - float(b), 2)
        return 0.0

    comparison = {
        "trips": {"ref": baseline["trips"], "scenario": scenario["trips"], "delta": delta("trips")},
        "km": {"ref": baseline["km"], "scenario": scenario["km"], "delta": delta("km")},
        "avg_time_min": {
            "ref": baseline["avg_time_min"],
            "scenario": scenario["avg_time_min"],
            "delta": delta("avg_time_min"),
        },
        "co2_t": {"ref": baseline["co2_t"], "scenario": scenario["co2_t"], "delta": delta("co2_t")},
        "modal_share": {
            "ref": baseline["modal_share"],
            "scenario": scenario["modal_share"],
        },
    }

    return {
        "action": action,
        "action_label": ACTIONS[action],
        "zone_id": zone_id,
        "zone_name": zone_name,
        "intensity": intensity,
        "telework_rate": telework_rate,
        "telework_pattern": pattern,
        "baseline": baseline,
        "scenario": scenario,
        "comparison": comparison,
        "assumptions": assumptions,
        "actions_catalog": ACTIONS,
        "synthetic": True,
        "note": (
            "Modèle paramétrique MVP (reports forfaitaires). "
            "Pas une affectation sur le graphe routier. "
            "À utiliser pour comparer des ordres de grandeur en comité."
        ),
    }
