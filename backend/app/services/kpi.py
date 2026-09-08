"""
M5 — Tableau de bord exécutif (6-8 KPI + séries + benchmark + objectifs).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.disaggregation import CO2_KG_PER_PKM, mode_shares_for_distance
from app.services.emploi_habitat import get_emploi_habitat
from app.services.keypoints import get_keypoints
from app.services.od import get_od_summary, list_od_rows

OBJECTIVES = [
    {
        "id": "tc_share",
        "name": "Part modale TC",
        "horizon": "PDM 2030",
        "target": 0.40,
        "unit": "%",
        "direction": "up",
    },
    {
        "id": "co2",
        "name": "Réduction CO₂ vs référence",
        "horizon": "SCoT / PCAET",
        "target": -0.20,
        "unit": "%",
        "direction": "down",
    },
    {
        "id": "eh",
        "name": "Indice emploi-habitat moyen",
        "horizon": "SCoT",
        "target": 0.70,
        "unit": "",
        "direction": "up",
    },
    {
        "id": "time",
        "name": "Temps moyen de trajet",
        "horizon": "PDM",
        "target": 25.0,
        "unit": "min",
        "direction": "down",
    },
]


def _modal_and_co2(rows) -> tuple[dict[str, float], float, float, float]:
    trips = 0
    km = 0.0
    time_h = 0.0
    mode_trips = {"car": 0.0, "bus": 0.0, "walk": 0.0, "bike": 0.0}
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
        return {m: 0.0 for m in mode_trips}, 0.0, 0.0, 0.0
    modal = {m: round(v / trips, 3) for m, v in mode_trips.items()}
    return modal, round(co2 / 1000.0, 2), round(km, 1), round(time_h * 60 / trips, 1)


def get_dashboard(db: Session) -> dict:
    summary = get_od_summary(db, top_n=5)
    kp = get_keypoints(db, corridor_top_n=5)
    eh = get_emploi_habitat(db)
    rows = list_od_rows(db)
    modal, co2_t, km, avg_time = _modal_and_co2(rows)

    eh_avg = eh.get("summary", {}).get("avg_score")
    deserts = kp.get("counts", {}).get("deserts", 0)
    corridors = kp.get("counts", {}).get("corridors", 0)

    kpis = [
        {
            "id": "trips",
            "label": "Déplacements / jour",
            "value": summary["total_passengers"],
            "unit": "",
            "hint": "Volume OD agrégé (synthétique)",
        },
        {
            "id": "km",
            "label": "km parcourus / jour",
            "value": km,
            "unit": "km",
            "hint": "Somme volume × distance OD",
        },
        {
            "id": "time",
            "label": "Temps moyen",
            "value": avg_time,
            "unit": "min",
            "hint": "Proxy vitesse 22 km/h",
        },
        {
            "id": "co2",
            "label": "CO₂ / jour",
            "value": co2_t,
            "unit": "t",
            "hint": "Facteurs ADEME-like VP/bus",
        },
        {
            "id": "modal_tc",
            "label": "Part TC",
            "value": round(modal.get("bus", 0) * 100, 1),
            "unit": "%",
            "hint": "Split modal proxy selon distance",
        },
        {
            "id": "modal_car",
            "label": "Part VP",
            "value": round(modal.get("car", 0) * 100, 1),
            "unit": "%",
            "hint": "Voiture particulière",
        },
        {
            "id": "eh",
            "label": "Indice emploi-habitat",
            "value": eh_avg,
            "unit": "",
            "hint": "0 = déséquilibre, 1 = équilibre",
        },
        {
            "id": "alerts",
            "label": "Alertes territoriales",
            "value": deserts + corridors,
            "unit": "",
            "hint": f"{deserts} déserts · {corridors} corridors",
        },
    ]

    # Série mensuelle synthétique autour de la référence (variation saisonnière)
    seasonal = [0.92, 0.95, 0.98, 1.00, 1.02, 1.04, 0.90, 0.88, 1.03, 1.05, 1.04, 0.97]
    months = [f"2025-{i:02d}" for i in range(1, 13)]
    timeseries = {
        "granularity": "month",
        "points": [
            {
                "period": months[i],
                "trips": int(round(summary["total_passengers"] * seasonal[i])),
                "km": round(km * seasonal[i], 1),
                "co2_t": round(co2_t * seasonal[i], 2),
            }
            for i in range(12)
        ],
        "note": "Série illustrative (saisonnalité forfaitaire), pas un historique réel.",
    }

    benchmark = [
        {
            "city": "Antananarivo (démo)",
            "eh_index": eh_avg,
            "tc_share": modal.get("bus", 0),
            "avg_time_min": avg_time,
            "self": True,
        },
        {
            "city": "Nairobi (illust.)",
            "eh_index": 0.48,
            "tc_share": 0.33,
            "avg_time_min": 42,
            "self": False,
        },
        {
            "city": "Dakar (illust.)",
            "eh_index": 0.52,
            "tc_share": 0.29,
            "avg_time_min": 38,
            "self": False,
        },
        {
            "city": "Lyon (illust.)",
            "eh_index": 0.71,
            "tc_share": 0.32,
            "avg_time_min": 29,
            "self": False,
        },
    ]

    current_by_id = {
        "tc_share": modal.get("bus", 0),
        "co2": 0.0,
        "eh": eh_avg or 0,
        "time": avg_time,
    }
    objectives = []
    for obj in OBJECTIVES:
        current = current_by_id[obj["id"]]
        target = obj["target"]
        if obj["direction"] == "up":
            progress = current / target if target else 0
        else:
            # target négatif (réduction) ou temps à baisser
            if obj["id"] == "co2":
                progress = 0.0  # référence = 0% de réduction aujourd'hui
            else:
                progress = target / current if current else 0
        objectives.append(
            {
                **obj,
                "current": round(current, 3) if isinstance(current, float) else current,
                "progress": round(min(1.5, max(0.0, progress)), 2),
            }
        )

    return {
        "kpis": kpis,
        "timeseries": timeseries,
        "benchmark": benchmark,
        "objectives": objectives,
        "top_flows": summary.get("top_flows", []),
        "counts": kp.get("counts", {}),
        "synthetic": True,
        "note": (
            "Vue exécutive MVP. Benchmarks métropoles = ordres de grandeur illustratifs, "
            "non issus d'une enquête comparée. Objectifs PDM/SCoT paramétrés pour la démo."
        ),
    }
