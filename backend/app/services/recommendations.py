"""
M3 — Recommandations d'urbanisation typées (règles métier MVP).

Chaque reco est déclenchée par un point clé M2 et porte un score d'impact 0-100.
Ce n'est pas une optimisation p-médianes ; les indicateurs sont des proxies.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.keypoints import get_keypoints

RECO_CATALOG = [
    {
        "type": "tc_stop",
        "label_fr": "Création d'un arrêt TC",
        "trigger": "Désert de mobilité avec demande > seuil",
        "impact_indicator": "Voyageurs/jour captés",
    },
    {
        "type": "multimodal_hub",
        "label_fr": "Pôle multimodal",
        "trigger": "Nœud de convergence multi-modes",
        "impact_indicator": "% report modal",
    },
    {
        "type": "park_and_ride",
        "label_fr": "Parking relais",
        "trigger": "Entrée de ville saturée, TC disponible",
        "impact_indicator": "Véhicules retirés du centre",
    },
    {
        "type": "bike_lane",
        "label_fr": "Piste cyclable",
        "trigger": "Corridor < 5 km à forte demande",
        "impact_indicator": "Trajets vélo potentiels",
    },
    {
        "type": "housing_densify",
        "label_fr": "Densification logement",
        "trigger": "Proximité emplois sous-exploitée",
        "impact_indicator": "Réduction km parcourus",
    },
    {
        "type": "coworking",
        "label_fr": "Tiers-lieu / coworking",
        "trigger": "Trajets longs récurrents",
        "impact_indicator": "Heures de trajet économisées",
    },
    {
        "type": "carpool_line",
        "label_fr": "Ligne de covoiturage",
        "trigger": "Flux parallèles concentrés",
        "impact_indicator": "Taux d'occupation projeté",
    },
]


def _score(value: float, lo: float, hi: float) -> int:
    if hi <= lo:
        return 50
    t = (value - lo) / (hi - lo)
    return int(max(8, min(98, round(t * 100))))


def get_recommendations(db: Session, corridor_top_n: int = 5) -> dict:
    kp = get_keypoints(db, corridor_top_n=corridor_top_n)
    items: list[dict] = []
    rid = 1

    deserts = kp["deserts"]["features"]
    for feat in deserts:
        p = feat["properties"]
        demand = float(p.get("demand_proxy") or 0)
        captured = int(round(demand * 0.12))
        items.append(
            {
                "id": rid,
                "type": "tc_stop",
                "label_fr": "Création d'un arrêt TC",
                "title": f"Arrêt TC — {p.get('name')}",
                "zone_id": p.get("id"),
                "zone_name": p.get("name"),
                "trigger": "Désert de mobilité avec demande > seuil",
                "impact_indicator": "Voyageurs/jour captés",
                "impact_value": captured,
                "impact_unit": "voy/j",
                "impact_score": _score(demand, 5000, 40000),
                "geometry": feat["geometry"],
                "lon": p.get("lon"),
                "lat": p.get("lat"),
            }
        )
        rid += 1

    for feat in kp["convergence"]["features"]:
        p = feat["properties"]
        inbound = float(p.get("inbound") or 0)
        modal = round(min(18.0, 4.0 + inbound / 8000.0), 1)
        items.append(
            {
                "id": rid,
                "type": "multimodal_hub",
                "label_fr": "Pôle multimodal",
                "title": f"Pôle d'échanges — {p.get('name')}",
                "zone_id": p.get("id"),
                "zone_name": p.get("name"),
                "trigger": "Nœud de convergence multi-modes",
                "impact_indicator": "% report modal",
                "impact_value": modal,
                "impact_unit": "%",
                "impact_score": _score(inbound, 2000, 25000),
                "geometry": feat["geometry"],
                "lon": p.get("lon"),
                "lat": p.get("lat"),
            }
        )
        rid += 1

    corridors = kp["corridors"]["features"]
    if corridors:
        entry = corridors[0]
        p = entry["properties"]
        veh = int(round(float(p.get("passenger_count") or 0) * 0.18))
        items.append(
            {
                "id": rid,
                "type": "park_and_ride",
                "label_fr": "Parking relais",
                "title": f"P+R entrée de ville — {p.get('origin_name')}",
                "zone_id": p.get("origin_zone_id"),
                "zone_name": p.get("origin_name"),
                "trigger": "Entrée de ville saturée, TC disponible",
                "impact_indicator": "Véhicules retirés du centre",
                "impact_value": veh,
                "impact_unit": "véh./j",
                "impact_score": _score(float(p.get("passenger_count") or 0), 80, 400),
                "geometry": entry["geometry"],
                "lon": None,
                "lat": None,
            }
        )
        rid += 1

    for feat in corridors:
        p = feat["properties"]
        dist = p.get("average_distance_km")
        if dist is None or float(dist) >= 5.0:
            continue
        bike_trips = int(round(float(p.get("passenger_count") or 0) * 0.10))
        items.append(
            {
                "id": rid,
                "type": "bike_lane",
                "label_fr": "Piste cyclable",
                "title": f"Piste {p.get('origin_name')} → {p.get('destination_name')}",
                "zone_id": p.get("origin_zone_id"),
                "zone_name": p.get("origin_name"),
                "trigger": "Corridor < 5 km à forte demande",
                "impact_indicator": "Trajets vélo potentiels",
                "impact_value": bike_trips,
                "impact_unit": "trajets/j",
                "impact_score": _score(float(p.get("passenger_count") or 0), 50, 300),
                "geometry": feat["geometry"],
                "lon": None,
                "lat": None,
            }
        )
        rid += 1

    for feat in kp["zones"]["features"]:
        p = feat["properties"]
        if p.get("label") != "employment":
            continue
        km = int(round((p.get("jobs_proxy") or 0) * 0.004))
        items.append(
            {
                "id": rid,
                "type": "housing_densify",
                "label_fr": "Densification logement",
                "title": f"Logements près des emplois — {p.get('name')}",
                "zone_id": p.get("id"),
                "zone_name": p.get("name"),
                "trigger": "Proximité emplois sous-exploitée",
                "impact_indicator": "Réduction km parcourus",
                "impact_value": km,
                "impact_unit": "km/j",
                "impact_score": _score(float(p.get("jobs_proxy") or 0), 4000, 20000),
                "geometry": feat["geometry"],
                "lon": p.get("lon"),
                "lat": p.get("lat"),
            }
        )
        rid += 1

    for feat in kp["unbalanced_pairs"]["features"][:4]:
        p = feat["properties"]
        hours = int(round(float(p.get("passenger_count") or 0) * 0.35))
        items.append(
            {
                "id": rid,
                "type": "coworking",
                "label_fr": "Tiers-lieu / coworking",
                "title": f"Tiers-lieu — {p.get('origin_name')}",
                "zone_id": p.get("origin_zone_id"),
                "zone_name": p.get("origin_name"),
                "trigger": "Trajets longs récurrents",
                "impact_indicator": "Heures de trajet économisées",
                "impact_value": hours,
                "impact_unit": "h/j",
                "impact_score": _score(float(p.get("passenger_count") or 0), 40, 250),
                "geometry": feat["geometry"],
                "lon": None,
                "lat": None,
            }
        )
        rid += 1

    carpool_seen: set[int] = set()
    for feat in kp["carpool"]["features"]:
        p = feat["properties"]
        fid = int(p.get("id") or 0)
        if fid in carpool_seen:
            continue
        carpool_seen.add(fid)
        occ = round(1.2 + min(0.8, float(p.get("passenger_count") or 0) / 400.0), 2)
        items.append(
            {
                "id": rid,
                "type": "carpool_line",
                "label_fr": "Ligne de covoiturage",
                "title": f"Covoiturage {p.get('origin_name')} → {p.get('destination_name')}",
                "zone_id": p.get("origin_zone_id"),
                "zone_name": p.get("origin_name"),
                "trigger": "Flux parallèles concentrés",
                "impact_indicator": "Taux d'occupation projeté",
                "impact_value": occ,
                "impact_unit": "pers./véh.",
                "impact_score": _score(float(p.get("passenger_count") or 0), 40, 250),
                "geometry": feat["geometry"],
                "lon": None,
                "lat": None,
            }
        )
        rid += 1
        if len(carpool_seen) >= 6:
            break

    items.sort(key=lambda x: x["impact_score"], reverse=True)

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": it["geometry"],
                "properties": {k: v for k, v in it.items() if k != "geometry"},
            }
            for it in items
            if it.get("geometry")
        ],
    }

    return {
        "items": items,
        "geojson": geojson,
        "catalog": RECO_CATALOG,
        "counts": {c["type"]: sum(1 for i in items if i["type"] == c["type"]) for c in RECO_CATALOG},
        "synthetic": True,
        "note": (
            "Scores d'impact heuristiques (proxies), pas une évaluation socio-économique. "
            "À valider en comité technique avant tout arbitrage."
        ),
    }
