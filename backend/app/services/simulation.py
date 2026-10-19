"""
M4 — Simulation what-if.

Modèle paramétrique sur les flux origine-destination synthétiques.
Les résultats comparent une situation de référence et une hypothèse.
Ce n'est pas une prédiction de trafic ni une affectation sur le graphe.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.disaggregation import CO2_KG_PER_PKM, mode_shares_for_distance

ACTIONS = {
    "add_satellite_office": "Créer un bureau satellite",
    "telework": "Télétravail",
    "add_tc_stop": "Créer un arrêt de transport collectif",
    "add_park_ride": "Créer un parking relais",
    "add_bike_lane": "Créer une piste cyclable",
    "shift_schedules": "Modifier les horaires",
    "relocate_jobs": "Déplacer une activité",
    "zoning_housing": "Zonage : logements",
    "zoning_jobs": "Zonage : emplois",
}

SCENARIO_CARDS = [
    {
        "code": "A",
        "action": "add_satellite_office",
        "label": "Bureau satellite",
        "question": "Et si une partie des salariés travaillait plus près de chez eux ?",
    },
    {
        "code": "B",
        "action": "telework",
        "label": "Télétravail",
        "question": "Et si 10 %, 20 % ou 30 % des journées de bureau disparaissaient ?",
    },
    {
        "code": "C",
        "action": "add_tc_stop",
        "label": "Arrêt de transport collectif",
        "question": "Et si un arrêt de bus ouvrait dans cette zone ?",
    },
    {
        "code": "D",
        "action": "add_park_ride",
        "label": "Parking relais",
        "question": "Et si les longues navettes en voiture s'arrêtaient en entrée de ville ?",
    },
    {
        "code": "E",
        "action": "add_bike_lane",
        "label": "Piste cyclable",
        "question": "Et si les trajets courts pouvaient se faire à vélo ?",
    },
    {
        "code": "F",
        "action": "shift_schedules",
        "label": "Horaires",
        "question": "Et si une partie des arrivées quittait l'heure de pointe ?",
    },
    {
        "code": "G",
        "action": "relocate_jobs",
        "label": "Déplacer une activité",
        "question": "Et si un site d'emploi changeait de quartier ?",
    },
    {
        "code": "H",
        "action": "zoning_housing",
        "label": "Zonage logements",
        "question": "Et si l'on ajoutait des logements près des emplois ?",
    },
    {
        "code": "I",
        "action": "zoning_jobs",
        "label": "Zonage emplois",
        "question": "Et si l'on ajoutait des emplois dans les quartiers résidentiels ?",
    },
]

TELEWORK_DAY_SHARE = {
    "full_remote": 1.00,
    "hybrid_1_2": 0.30,
    "hybrid_3_4": 0.70,
}

DISCLAIMER = (
    "SIMULATION — ordre de grandeur pour comparer des hypothèses, "
    "pas une prédiction du trafic réel."
)
COMMUTE_SHARE = 0.70
SPEED_KMH = 22.0
EFFECT_THRESHOLD = 0.012

INDICATORS = [
    ("trips", "Déplacements", "trajets/j", False),
    ("km", "Distance", "km/j", False),
    ("avg_time_min", "Temps", "min", False),
    ("co2_t", "CO₂", "t/j", False),
    ("flow_volume", "Volume des flux", "plus gros flux", False),
    ("corridor_pressure", "Pression corridors", "% sur 5 flux", False),
    ("emploi_habitat", "Emploi-habitat", "indice", True),
]


def _hav_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def _trips(flow: dict) -> float:
    return float(sum(flow["modes"].values()))


def _co2_kg(flow: dict) -> float:
    dist = float(flow["dist"])
    return sum(
        float(n) * dist * CO2_KG_PER_PKM.get(mode, 0.12)
        for mode, n in flow["modes"].items()
    )


def _copy_flow(flow: dict) -> dict:
    return {**flow, "modes": dict(flow["modes"])}


def _minutes_for(dist_km: float) -> float:
    return max(4.0, dist_km / SPEED_KMH * 60.0)


def _load_base(db: Session) -> tuple[list[dict], list[dict]]:
    zone_rows = db.execute(
        text(
            """
            SELECT
                id,
                name,
                COALESCE(population_proxy, 0) AS population_proxy,
                COALESCE(jobs_proxy, 0) AS jobs_proxy,
                ST_AsGeoJSON(geometry)::json AS geometry,
                ST_X(ST_Centroid(geometry)) AS lon,
                ST_Y(ST_Centroid(geometry)) AS lat
            FROM mobility_zones
            ORDER BY name
            """
        )
    ).fetchall()
    zones = [
        {
            "id": int(r.id),
            "name": r.name,
            "pop": int(r.population_proxy),
            "jobs": int(r.jobs_proxy),
            "geometry": r.geometry,
            "lon": float(r.lon),
            "lat": float(r.lat),
        }
        for r in zone_rows
    ]
    flow_rows = db.execute(
        text(
            """
            SELECT
                origin_zone_id,
                destination_zone_id,
                origin_name,
                destination_name,
                passenger_count,
                average_distance,
                average_time,
                ST_X(ST_StartPoint(geom)) AS ox,
                ST_Y(ST_StartPoint(geom)) AS oy,
                ST_X(ST_EndPoint(geom)) AS dx,
                ST_Y(ST_EndPoint(geom)) AS dy
            FROM v_od_desire_lines
            WHERE passenger_count >= 5
            """
        )
    ).fetchall()
    flows = []
    for r in flow_rows:
        dist = float(r.average_distance or 0)
        trips = float(r.passenger_count)
        shares = mode_shares_for_distance(dist)
        flows.append(
            {
                "origin_id": int(r.origin_zone_id),
                "dest_id": int(r.destination_zone_id),
                "origin_name": r.origin_name,
                "dest_name": r.destination_name,
                "dist": dist,
                "minutes": float(r.average_time or _minutes_for(dist)),
                "ox": float(r.ox) if r.ox is not None else None,
                "oy": float(r.oy) if r.oy is not None else None,
                "dx": float(r.dx) if r.dx is not None else None,
                "dy": float(r.dy) if r.dy is not None else None,
                "modes": {m: trips * s for m, s in shares.items()},
                "peak_factor": 1.0,
            }
        )
    return flows, zones


def _load_organizations(db: Session) -> list[dict]:
    try:
        rows = db.execute(
            text(
                """
                SELECT id, name, employee_count
                FROM organizations
                ORDER BY employee_count DESC
                LIMIT 8
                """
            )
        ).fetchall()
    except Exception:
        db.rollback()
        return []
    return [
        {
            "id": int(r.id),
            "name": r.name,
            "employee_count": int(r.employee_count),
        }
        for r in rows
    ]


def _companies(orgs: list[dict], zones: list[dict]) -> list[dict]:
    job_zones = sorted(zones, key=lambda z: z["jobs"], reverse=True)
    if not job_zones:
        return []
    if orgs:
        companies = []
        for index, org in enumerate(orgs):
            zone = job_zones[index % len(job_zones)]
            companies.append(
                {
                    "key": f"org-{org['id']}",
                    "name": org["name"],
                    "work_zone_id": zone["id"],
                    "work_zone_name": zone["name"],
                    "employee_count": org["employee_count"],
                    "attachment": "rank",
                }
            )
        return companies
    return [
        {
            "key": f"zone-{zone['id']}",
            "name": f"Site d'emploi — {zone['name']}",
            "work_zone_id": zone["id"],
            "work_zone_name": zone["name"],
            "employee_count": int(zone["jobs"]),
            "attachment": "zone",
        }
        for zone in job_zones[:8]
    ]


def catalog(db: Session) -> dict:
    flows, zones = _load_base(db)
    companies = _companies(_load_organizations(db), zones)
    return {
        "scenarios": SCENARIO_CARDS,
        "organizations": companies,
        "zones": [
            {
                "id": z["id"],
                "name": z["name"],
                "population_proxy": z["pop"],
                "jobs_proxy": z["jobs"],
            }
            for z in zones
        ],
        "telework_rates": [0.1, 0.2, 0.3, 0.4],
        "employee_shares": [0.1, 0.2, 0.3, 0.4],
        "disclaimer": DISCLAIMER,
        "flow_count": len(flows),
        "synthetic": True,
    }


def _modal_share(flows: list[dict]) -> dict[str, float]:
    totals = {"car": 0.0, "bus": 0.0, "walk": 0.0, "bike": 0.0}
    trips = 0.0
    for flow in flows:
        for mode, count in flow["modes"].items():
            totals[mode] = totals.get(mode, 0.0) + float(count)
            trips += float(count)
    if trips <= 0:
        return {mode: 0.0 for mode in totals}
    return {mode: round(value / trips, 3) for mode, value in totals.items()}


def _eh(pop: int, jobs: int) -> float | None:
    total = pop + jobs
    if total <= 0:
        return None
    return 1.0 - abs(jobs - pop) / total


def _aggregate(flows: list[dict], zones: list[dict]) -> dict[str, Any]:
    trips = 0.0
    km = 0.0
    person_min = 0.0
    co2 = 0.0
    weighted = []
    for flow in flows:
        count = _trips(flow)
        peak = float(flow.get("peak_factor", 1.0))
        trips += count
        km += count * float(flow["dist"])
        person_min += count * float(flow["minutes"])
        co2 += _co2_kg(flow)
        weighted.append(count * peak)
    weighted.sort(reverse=True)
    busiest = weighted[0] if weighted else 0.0
    top5 = sum(weighted[:5])
    scores = [score for z in zones if (score := _eh(z["pop"], z["jobs"])) is not None]
    eh_avg = sum(scores) / len(scores) if scores else 0.0
    return {
        "trips": int(round(trips)),
        "km": round(km, 1),
        "time_h": round(person_min / 60.0, 1),
        "avg_time_min": round(person_min / trips, 1) if trips else 0.0,
        "co2_t": round(co2 / 1000.0, 2),
        "flow_volume": int(round(busiest)),
        "corridor_pressure": round(100.0 * top5 / trips, 1) if trips else 0.0,
        "emploi_habitat": round(eh_avg, 3),
        "modal_share": _modal_share(flows),
    }


def _pack_indicators(before: dict, after: dict) -> dict[str, dict]:
    packed = {}
    for key, label, unit, _higher in INDICATORS:
        b = before[key]
        a = after[key]
        digits = 3 if key == "emploi_habitat" else 2
        packed[key] = {
            "key": key,
            "label": label,
            "unit": unit,
            "before": b,
            "after": a,
            "delta": round(float(a) - float(b), digits),
            "higher_is_better": key == "emploi_habitat",
        }
    return packed


def _comparison(before: dict, after: dict) -> dict:
    out = {}
    for key in (
        "trips",
        "km",
        "avg_time_min",
        "co2_t",
        "flow_volume",
        "corridor_pressure",
        "emploi_habitat",
    ):
        out[key] = {
            "ref": before[key],
            "scenario": after[key],
            "delta": round(float(after[key]) - float(before[key]), 3),
        }
    out["modal_share"] = {"ref": before["modal_share"], "scenario": after["modal_share"]}
    return out


def _shift_mode(flow: dict, source: str, target: str, share: float) -> float:
    available = float(flow["modes"].get(source, 0.0))
    moved = available * share
    flow["modes"][source] = available - moved
    flow["modes"][target] = float(flow["modes"].get(target, 0.0)) + moved
    return moved


def _scale_distance(flow: dict, factor: float) -> None:
    flow["dist"] = round(max(0.4, float(flow["dist"]) * factor), 2)
    flow["minutes"] = round(_minutes_for(flow["dist"]), 1)


def _retarget(flow: dict, share: float, dest: dict) -> dict | None:
    if share <= 0:
        return None
    moved = {mode: float(count) * share for mode, count in flow["modes"].items()}
    if sum(moved.values()) < 0.5:
        return None
    for mode in list(flow["modes"]):
        flow["modes"][mode] = float(flow["modes"][mode]) * (1.0 - share)
    lon = flow["ox"] if flow["ox"] is not None else dest["lon"]
    lat = flow["oy"] if flow["oy"] is not None else dest["lat"]
    dist = _hav_km(lon, lat, dest["lon"], dest["lat"])
    if flow["origin_id"] == dest["id"]:
        dist = 0.8
    dist = max(0.4, dist)
    return {
        "origin_id": flow["origin_id"],
        "dest_id": dest["id"],
        "origin_name": flow["origin_name"],
        "dest_name": dest["name"],
        "dist": round(dist, 2),
        "minutes": round(_minutes_for(dist), 1),
        "ox": flow["ox"],
        "oy": flow["oy"],
        "dx": dest["lon"],
        "dy": dest["lat"],
        "modes": moved,
        "peak_factor": float(flow.get("peak_factor", 1.0)),
    }


def _zone_by_id(zones: list[dict]) -> dict[int, dict]:
    return {int(z["id"]): z for z in zones}


def _inbound(flows: list[dict]) -> dict[int, float]:
    totals: dict[int, float] = defaultdict(float)
    for flow in flows:
        totals[int(flow["dest_id"])] += _trips(flow)
    return totals


def _pick_busiest_dest(flows: list[dict], zones: list[dict]) -> dict:
    totals = _inbound(flows)
    if not totals:
        return zones[0]
    zone_id = max(totals, key=totals.get)
    return _zone_by_id(zones)[zone_id]


def _pick_outer_residence(zones: list[dict]) -> dict:
    ranked = sorted(
        zones,
        key=lambda z: (z["pop"] / max(z["jobs"], 1), z["pop"]),
        reverse=True,
    )
    return ranked[0]


def _pick_receiver(zones: list[dict], source_id: int) -> dict:
    others = [z for z in zones if z["id"] != source_id]
    others.sort(key=lambda z: (z["pop"] - z["jobs"], z["pop"]), reverse=True)
    return others[0] if others else zones[0]


def _satellite_zone(flows: list[dict], zones: list[dict], hq_id: int) -> dict | None:
    totals: dict[int, float] = defaultdict(float)
    for flow in flows:
        if int(flow["dest_id"]) == hq_id and int(flow["origin_id"]) != hq_id:
            totals[int(flow["origin_id"])] += _trips(flow)
    if not totals:
        return None
    zone_id = max(totals, key=totals.get)
    return _zone_by_id(zones).get(zone_id)


def _apply(
    action: str,
    flows: list[dict],
    zones: list[dict],
    *,
    zone_id: int | None,
    target_zone_id: int | None,
    intensity: float,
    telework_rate: float,
    telework_pattern: str,
    employee_share: float | None,
    organization_key: str | None,
    stagger_share: float,
    companies: list[dict],
) -> dict[str, Any]:
    assumptions: list[str] = []
    pressure_extra: dict[int, float] = defaultdict(float)
    sites: list[dict] = []
    company_info = None
    question = ACTIONS.get(action, action)
    created: list[dict] = []
    by_id = _zone_by_id(zones)
    strength = max(0.2, min(4.0, intensity / 0.25))

    def zone_or(preferred: int | None, fallback: dict) -> dict:
        if preferred is not None and preferred in by_id:
            return by_id[preferred]
        return fallback

    if action == "add_satellite_office":
        company = None
        if organization_key:
            company = next((c for c in companies if c["key"] == organization_key), None)
        if company is None and zone_id is not None and zone_id in by_id:
            zone = by_id[zone_id]
            company = {
                "key": f"zone-{zone_id}",
                "name": zone["name"],
                "work_zone_id": zone_id,
                "work_zone_name": zone["name"],
                "employee_count": max(int(zone["jobs"]), 1),
                "attachment": "zone",
            }
        if company is None and companies:
            company = companies[0]
        share = employee_share if employee_share is not None else min(0.5, intensity)
        share = max(0.0, min(0.6, share))
        if company is None:
            assumptions.append("Aucun site d'emploi disponible pour un bureau satellite.")
        else:
            hq = by_id[company["work_zone_id"]]
            satellite = _satellite_zone(flows, zones, hq["id"])
            effective = share * COMMUTE_SHARE
            moved_trips = 0.0
            eligible_trips = 0.0
            if satellite is not None and effective > 0:
                for flow in list(flows):
                    if flow["dest_id"] != hq["id"]:
                        continue
                    origin = by_id.get(flow["origin_id"])
                    if origin is None:
                        continue
                    current = float(flow["dist"])
                    proposed = _hav_km(origin["lon"], origin["lat"], satellite["lon"], satellite["lat"])
                    if flow["origin_id"] == satellite["id"]:
                        proposed = 0.8
                    count = _trips(flow)
                    eligible_trips += count
                    if proposed >= current * 0.98:
                        continue
                    spawned = _retarget(flow, effective, satellite)
                    if spawned is not None:
                        if spawned["dist"] < 2.0:
                            _shift_mode(spawned, "car", "walk", 0.25)
                            _shift_mode(spawned, "bus", "bike", 0.15)
                        created.append(spawned)
                        moved_trips += _trips(spawned)
            frac = (eligible_trips and moved_trips / (eligible_trips * effective)) or 0.0
            people = int(round(company["employee_count"] * share * min(1.0, frac if effective else 0.0)))
            hq["jobs"] = max(0, hq["jobs"] - people)
            if satellite is not None:
                satellite["jobs"] += people
                sites.append(
                    {
                        "role": "satellite",
                        "name": satellite["name"],
                        "lon": satellite["lon"],
                        "lat": satellite["lat"],
                        "label": f"Bureau satellite — {satellite['name']}",
                    }
                )
            company_info = {
                "key": company["key"],
                "name": company["name"],
                "employee_share": share,
                "employee_count": company["employee_count"],
                "concerned": int(round(company["employee_count"] * share)),
                "relocated": people,
                "work_zone_name": hq["name"],
                "satellite_name": satellite["name"] if satellite else None,
            }
            pct = int(round(share * 100))
            sat_name = satellite["name"] if satellite else "un site plus proche"
            question = (
                f"Si {pct} % des employés de {company['name']} travaillent dans un bureau "
                f"satellite à {sat_name}, plus proche de leur domicile, quel est l'impact estimé ?"
            )
            assumptions.append(
                f"{pct} % des salariés sont concernés. Seuls ceux dont le satellite est "
                "plus proche que le site actuel y sont affectés."
            )
            assumptions.append(
                f"{int(COMMUTE_SHARE * 100)} % des volumes OD vers le pôle sont traités comme les navettes "
                "de l'entreprise. Le reste (achats, autres motifs) ne bouge pas. "
                "L'effectif sert à dire combien de personnes sont concernées."
            )
            assumptions.append(
                "Même mode sur le trajet raccourci, avec un report vers la marche et le vélo sous 2 km. "
                "Pas de déménagement des ménages."
            )
            if company.get("attachment") == "rank":
                assumptions.append(
                    f"« {company['name']} » est rattaché au pôle {hq['name']} "
                    "(même rang dans la grille démo, sans jointure cadastrale)."
                )

    elif action == "telework":
        pattern = telework_pattern if telework_pattern in TELEWORK_DAY_SHARE else "hybrid_1_2"
        day_share = TELEWORK_DAY_SHARE[pattern]
        removed = COMMUTE_SHARE * telework_rate * day_share
        for flow in flows:
            for mode in list(flow["modes"]):
                flow["modes"][mode] *= 1.0 - removed
        labels = {
            "full_remote": "jours entièrement à distance",
            "hybrid_1_2": "1 à 2 jours à distance",
            "hybrid_3_4": "3 à 4 jours à distance",
        }
        pct = int(round(telework_rate * 100))
        question = (
            f"Si {pct} % des salariés sont en télétravail ({labels[pattern]}), "
            "que deviennent les navettes ?"
        )
        assumptions.append(
            f"Taux {pct} %, rythme « {labels[pattern]} » soit {int(day_share * 100)} % des jours ouvrés."
        )
        assumptions.append(
            f"Seules les navettes sont retirées ({int(COMMUTE_SHARE * 100)} % des volumes OD). "
            "Les emplois et les domiciles ne bougent pas."
        )

    elif action == "add_tc_stop":
        zone = zone_or(zone_id, _pick_busiest_dest(flows, zones))
        shift = min(0.4, 0.12 * strength)
        for flow in flows:
            touches = flow["origin_id"] == zone["id"] or flow["dest_id"] == zone["id"]
            if not touches:
                continue
            moved = _shift_mode(flow, "car", "bus", shift)
            if moved <= 0:
                continue
            flow["minutes"] = round(float(flow["minutes"]) * (1.0 + 0.04 * shift), 1)
            flow["peak_factor"] = float(flow["peak_factor"]) * (1.0 - 0.08 * strength)
        pressure_extra[zone["id"]] += _inbound(flows).get(zone["id"], 0.0) * 0.45
        sites.append(
            {
                "role": "tc_stop",
                "name": zone["name"],
                "lon": zone["lon"],
                "lat": zone["lat"],
                "label": f"Arrêt TC — {zone['name']}",
            }
        )
        question = f"Si un arrêt de transport collectif est créé à {zone['name']}, quel report modal estimer ?"
        assumptions.append(
            f"Environ {int(shift * 100)} % des trajets voiture qui touchent {zone['name']} passent au bus."
        )
        assumptions.append(
            "Le bus est un peu plus lent que la voiture sur le même trajet. "
            "La pointe baisse légèrement. L'arrêt concentre des montées : la zone peut être plus chargée."
        )

    elif action == "add_park_ride":
        zone = zone_or(zone_id, _pick_outer_residence(zones))
        shift = min(0.45, 0.15 * strength)
        converged = 0.0
        for flow in flows:
            from_site = flow["origin_id"] == zone["id"]
            long_haul = float(flow["dist"]) >= 4.0
            if not from_site and not long_haul:
                continue
            moved = _shift_mode(flow, "car", "bus", shift)
            if moved <= 0:
                continue
            _scale_distance(flow, 1.0 - 0.10 * strength)
            flow["peak_factor"] = float(flow["peak_factor"]) * (1.0 - 0.10 * strength)
            converged += moved
        pressure_extra[zone["id"]] += converged
        sites.append(
            {
                "role": "park_ride",
                "name": zone["name"],
                "lon": zone["lon"],
                "lat": zone["lat"],
                "label": f"Parking relais — {zone['name']}",
            }
        )
        question = f"Si un parking relais ouvre à {zone['name']}, quel effet sur les longues navettes ?"
        assumptions.append(
            f"{int(shift * 100)} % des voitures sur les liaisons longues basculent vers le bus après le relais."
        )
        assumptions.append(
            "Le kilométrage des liaisons d'au moins 4 km baisse d'environ 10 % à l'intensité de référence. "
            "Le quartier du relais reçoit davantage de voitures : pression locale en hausse."
        )

    elif action == "add_bike_lane":
        zone = zone_or(zone_id, _pick_busiest_dest(flows, zones))
        shift = min(0.35, 0.08 * strength)
        for flow in flows:
            touches = flow["origin_id"] == zone["id"] or flow["dest_id"] == zone["id"]
            if not touches:
                continue
            if float(flow["dist"]) < 5.0:
                _shift_mode(flow, "car", "bike", shift)
                flow["minutes"] = round(float(flow["minutes"]) * (1.0 - 0.03 * strength), 1)
            else:
                flow["minutes"] = round(float(flow["minutes"]) * (1.0 + 0.06 * strength), 1)
        inbound_now = _inbound(flows).get(zone["id"], 0.0)
        pressure_extra[zone["id"]] += inbound_now * 0.28
        sites.append(
            {
                "role": "bike_lane",
                "name": zone["name"],
                "lon": zone["lon"],
                "lat": zone["lat"],
                "label": f"Piste cyclable — {zone['name']}",
            }
        )
        question = f"Si une piste cyclable dessert {zone['name']}, que deviennent les trajets courts ?"
        assumptions.append(
            f"Sur les liaisons de moins de 5 km touchant {zone['name']}, "
            f"{int(shift * 100)} % des trajets voiture passent au vélo."
        )
        assumptions.append(
            "Les trajets longs qui touchent la zone perdent un peu de capacité routière (+6 % de temps à l'intensité de référence). "
            "La zone de la piste absorbe plus de mouvements locaux."
        )

    elif action == "shift_schedules":
        stagger = max(0.0, min(0.5, stagger_share))
        counts = sorted(_trips(flow) for flow in flows)
        median = counts[len(counts) // 2] if counts else 0.0
        for flow in flows:
            if _trips(flow) >= median:
                flow["peak_factor"] = 1.0 - 0.45 * stagger
            else:
                flow["peak_factor"] = 1.0 + 0.55 * stagger
            flow["minutes"] = round(float(flow["minutes"]) * (1.0 - 0.06 * stagger), 1)
        pct = int(round(stagger * 100))
        question = f"Si {pct} % des arrivées quittent l'heure de pointe, quelle pression reste sur les corridors ?"
        assumptions.append(
            f"{pct} % des arrivées sont décalées d'environ 90 minutes. Le nombre de déplacements du jour ne change pas."
        )
        assumptions.append(
            "La pointe baisse sur les gros flux. Une partie du volume horaire se reporte sur les liaisons plus faibles : "
            "certaines zones calmes deviennent un peu plus chargées."
        )
        assumptions.append("Le CO₂ et les kilomètres du jour sont inchangés : seuls le pic et le temps de congestion bougent.")

    elif action == "relocate_jobs":
        source = zone_or(zone_id, _pick_busiest_dest(flows, zones))
        target = zone_or(target_zone_id, _pick_receiver(zones, source["id"]))
        if target["id"] == source["id"]:
            target = _pick_receiver(zones, source["id"])
        share = max(0.05, min(0.8, intensity))
        people = int(round(source["jobs"] * share))
        source["jobs"] = max(0, source["jobs"] - people)
        target["jobs"] += people
        for flow in list(flows):
            if flow["dest_id"] != source["id"]:
                continue
            spawned = _retarget(flow, share, target)
            if spawned is not None:
                created.append(spawned)
        sites.append(
            {
                "role": "jobs_from",
                "name": source["name"],
                "lon": source["lon"],
                "lat": source["lat"],
                "label": f"Site allégé — {source['name']}",
            }
        )
        sites.append(
            {
                "role": "jobs_to",
                "name": target["name"],
                "lon": target["lon"],
                "lat": target["lat"],
                "label": f"Activité déplacée — {target['name']}",
            }
        )
        question = (
            f"Si {int(round(share * 100))} % de l'activité de {source['name']} "
            f"est déplacée vers {target['name']}, quels trajets raccourcissent ou s'allongent ?"
        )
        assumptions.append(
            "La même part des navettes suit le site. La nouvelle distance est la distance à vol d'oiseau "
            "vers le quartier d'accueil, à 22 km/h de vitesse moyenne."
        )
        assumptions.append(
            "Les ménages ne déménagent pas. Le quartier d'accueil reçoit plus d'arrivées : "
            "sa pression peut augmenter même si d'autres trajets raccourcissent."
        )

    elif action == "zoning_housing":
        factor = 0.10 * strength
        for flow in flows:
            _scale_distance(flow, 1.0 - min(0.35, factor))
        question = "Si des logements sont ajoutés près des emplois, les navettes raccourcissent-elles ?"
        assumptions.append("Proxy : une part des distances domicile-travail est raccourcie, sans nouveau graphe.")

    elif action == "zoning_jobs":
        factor = 0.12 * strength
        for flow in flows:
            _scale_distance(flow, 1.0 - min(0.4, factor))
        question = "Si des emplois sont ajoutés dans les quartiers résidentiels, quel raccourcissement estimer ?"
        assumptions.append("Proxy de mixité : les distances OD diminuent, les effectifs de zone ne sont pas réécrits un à un.")

    flows.extend(created)
    assumptions.append(
        "Volumes OD synthétiques (modèle gravitaire). Aucune affectation sur le réseau routier."
    )
    assumptions.append(DISCLAIMER)
    return {
        "assumptions": assumptions,
        "pressure_extra": pressure_extra,
        "sites": sites,
        "company": company_info,
        "question": question,
    }


def _flow_metrics(flows: list[dict]) -> dict[int, dict[str, float]]:
    metrics: dict[int, dict[str, float]] = defaultdict(
        lambda: {"in": 0.0, "km": 0.0, "co2": 0.0, "time": 0.0}
    )
    for flow in flows:
        count = _trips(flow)
        peak = float(flow.get("peak_factor", 1.0))
        origin = int(flow["origin_id"])
        dest = int(flow["dest_id"])
        metrics[dest]["in"] += count * peak
        metrics[origin]["km"] += count * float(flow["dist"])
        metrics[origin]["co2"] += _co2_kg(flow)
        metrics[origin]["time"] += count * float(flow["minutes"])
    return metrics


def _relative(before: float, after: float) -> float:
    if before < 1e-6:
        return 0.0 if after < 1e-6 else 1.0
    return (after - before) / before


def _zone_collection(
    zones_before: list[dict],
    zones_after: list[dict],
    flows_before: list[dict],
    flows_after: list[dict],
    pressure_extra: dict[int, float],
) -> tuple[dict, dict]:
    before = _flow_metrics(flows_before)
    after = _flow_metrics(flows_after)
    after_jobs = {z["id"]: z for z in zones_after}
    features = []
    counts = {"improved": 0, "worsened": 0, "neutral": 0}
    improved_names: list[str] = []
    worsened_names: list[str] = []
    for zone in zones_before:
        zid = zone["id"]
        b = before[zid]
        a = after[zid]
        inbound_after = a["in"] + float(pressure_extra.get(zid, 0.0))
        score = (
            0.30 * _relative(b["in"], inbound_after)
            + 0.25 * _relative(b["km"], a["km"])
            + 0.25 * _relative(b["co2"], a["co2"])
            + 0.20 * _relative(b["time"], a["time"])
        )
        if score <= -EFFECT_THRESHOLD:
            effect = "improved"
        elif score >= EFFECT_THRESHOLD:
            effect = "worsened"
        else:
            effect = "neutral"
        counts[effect] += 1
        later = after_jobs[zid]
        eh_before = _eh(zone["pop"], zone["jobs"])
        eh_after = _eh(later["pop"], later["jobs"])
        feature = {
            "type": "Feature",
            "geometry": zone["geometry"],
            "properties": {
                "id": zid,
                "name": zone["name"],
                "effect": effect,
                "effect_label": {
                    "improved": "Zone améliorée",
                    "worsened": "Zone potentiellement aggravée",
                    "neutral": "Peu de changement",
                }[effect],
                "score": round(score, 3),
                "eh_before": round(eh_before, 3) if eh_before is not None else None,
                "eh_after": round(eh_after, 3) if eh_after is not None else None,
            },
        }
        features.append(feature)
        if effect == "improved":
            improved_names.append(zone["name"])
        elif effect == "worsened":
            worsened_names.append(zone["name"])
    improved_names.sort(key=lambda name: next(
        f["properties"]["score"] for f in features if f["properties"]["name"] == name
    ))
    worsened_names.sort(
        key=lambda name: next(f["properties"]["score"] for f in features if f["properties"]["name"] == name),
        reverse=True,
    )
    return (
        {"type": "FeatureCollection", "features": features},
        {
            "improved": counts["improved"],
            "worsened": counts["worsened"],
            "neutral": counts["neutral"],
            "improved_names": improved_names[:6],
            "worsened_names": worsened_names[:6],
        },
    )


def _keyed(flows: list[dict]) -> dict[tuple[int, int], dict]:
    merged: dict[tuple[int, int], dict] = {}
    for flow in flows:
        key = (int(flow["origin_id"]), int(flow["dest_id"]))
        if key not in merged:
            merged[key] = _copy_flow(flow)
            continue
        current = merged[key]
        for mode, count in flow["modes"].items():
            current["modes"][mode] = float(current["modes"].get(mode, 0.0)) + float(count)
        current["peak_factor"] = max(float(current["peak_factor"]), float(flow.get("peak_factor", 1)))
    return merged


def _flow_collection(before: list[dict], after: list[dict]) -> dict:
    left = _keyed(before)
    right = _keyed(after)
    features = []
    for key in set(left) | set(right):
        origin = right.get(key) or left[key]
        b = _trips(left[key]) * float(left[key].get("peak_factor", 1)) if key in left else 0.0
        a = _trips(right[key]) * float(right[key].get("peak_factor", 1)) if key in right else 0.0
        if max(b, a) < 5:
            continue
        if b <= 0:
            effect = "worsened"
        elif a <= 0:
            effect = "improved"
        else:
            rel = (a - b) / b
            if rel <= -EFFECT_THRESHOLD:
                effect = "improved"
            elif rel >= EFFECT_THRESHOLD:
                effect = "worsened"
            else:
                effect = "neutral"
        if origin["ox"] is None or origin["dx"] is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [origin["ox"], origin["oy"]],
                        [origin["dx"], origin["dy"]],
                    ],
                },
                "properties": {
                    "origin_name": origin["origin_name"],
                    "dest_name": origin["dest_name"],
                    "volume_before": int(round(b)),
                    "volume_after": int(round(a)),
                    "delta": int(round(a - b)),
                    "effect": effect,
                },
            }
        )
    features.sort(key=lambda f: abs(f["properties"]["delta"]), reverse=True)
    return {"type": "FeatureCollection", "features": features[:80]}


def _site_collection(sites: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": {
                    "role": s["role"],
                    "name": s["name"],
                    "label": s["label"],
                },
            }
            for s in sites
        ],
    }


def simulate(
    db: Session,
    action: str,
    zone_id: int | None = None,
    intensity: float = 0.25,
    telework_rate: float = 0.15,
    telework_pattern: str = "hybrid_1_2",
    target_zone_id: int | None = None,
    employee_share: float | None = None,
    organization_key: str | None = None,
    stagger_share: float = 0.20,
) -> dict:
    action = (action or "add_tc_stop").strip()
    if action not in ACTIONS:
        action = "add_tc_stop"
    intensity = max(0.05, min(1.0, float(intensity)))
    telework_rate = max(0.0, min(0.8, float(telework_rate)))
    stagger_share = max(0.0, min(0.5, float(stagger_share)))

    base_flows, base_zones = _load_base(db)
    companies = _companies(_load_organizations(db), base_zones)
    flows = [_copy_flow(flow) for flow in base_flows]
    zones = [dict(zone) for zone in base_zones]
    applied = _apply(
        action,
        flows,
        zones,
        zone_id=zone_id,
        target_zone_id=target_zone_id,
        intensity=intensity,
        telework_rate=telework_rate,
        telework_pattern=telework_pattern,
        employee_share=employee_share,
        organization_key=organization_key,
        stagger_share=stagger_share,
        companies=companies,
    )
    baseline = _aggregate(base_flows, base_zones)
    scenario = _aggregate(flows, zones)
    zone_fc, effects = _zone_collection(
        base_zones,
        zones,
        base_flows,
        flows,
        applied["pressure_extra"],
    )
    indicators = _pack_indicators(baseline, scenario)
    zone_name = None
    if zone_id is not None:
        zone_name = next((z["name"] for z in base_zones if z["id"] == zone_id), None)

    return {
        "action": action,
        "action_label": ACTIONS[action],
        "zone_id": zone_id,
        "zone_name": zone_name,
        "intensity": intensity,
        "telework_rate": telework_rate,
        "telework_pattern": telework_pattern if telework_pattern in TELEWORK_DAY_SHARE else "hybrid_1_2",
        "baseline": baseline,
        "scenario": scenario,
        "comparison": _comparison(baseline, scenario),
        "indicators": indicators,
        "assumptions": applied["assumptions"],
        "actions_catalog": {card["action"]: ACTIONS[card["action"]] for card in SCENARIO_CARDS},
        "synthetic": True,
        "kind": "simulation",
        "disclaimer": DISCLAIMER,
        "note": DISCLAIMER,
        "question": applied["question"],
        "company": applied["company"],
        "zone_effects": effects,
        "zones": zone_fc,
        "flows": _flow_collection(base_flows, flows),
        "sites": _site_collection(applied["sites"]),
    }
