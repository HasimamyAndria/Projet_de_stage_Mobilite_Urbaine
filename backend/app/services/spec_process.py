"""
Démarche du chapitre 6 de la spécification (v1.2).

Cinq étapes, sur les groupes simulés d'Antananarivo (au moins 20 personnes) :
1. Cartographie de la demande (domicile, siège, temps, km, CO₂).
2. Sites candidats, gardés si au moins 30 % des salariés sont à moins de 30 min.
3. P-médianes glouton : minimiser le temps de trajet pondéré par l'effectif.
4. Score 30 % temps, 25 % km, 20 % CO₂, 15 % desserte, 10 % faisabilité.
5. Restitution : top 5, comparaison à la situation de référence.

Les trois cas reprennent la structure de la section 6.5, sur les quartiers
déjà catalogués. Les effectifs ne sont pas ceux de l'illustration (3 000,
2 800, 500) : ce sont les groupes simulés.
"""
from __future__ import annotations

import math
from typing import Any

from app.data.organizations import ORGANIZATIONS
from app.data.territory import PLACES, places_of

WEIGHTS = (
    ("time", "Réduction du temps de trajet", 0.30, "min·personnes/j"),
    ("km", "Réduction des kilomètres", 0.25, "km·personnes/j"),
    ("co2", "Impact environnemental", 0.20, "t CO₂/an"),
    ("access", "Accessibilité multimodale", 0.15, "/100"),
    ("feasibility", "Faisabilité opérationnelle", 0.10, "/100"),
)

WORKDAYS = 220
WITHIN_MIN = 30.0
MIN_SHARE = 0.30
CAPACITY = 500
ROAD_FACTOR = 1.35

SPEED_KMH = {
    "marche": 4.5,
    "velo": 15.0,
    "bus": 16.0,
    "taxi": 20.0,
    "voiture": 22.0,
    "car": 22.0,
}
CO2_KG_PER_KM = {
    "marche": 0.0,
    "velo": 0.0,
    "bus": 0.08,
    "taxi": 0.18,
    "voiture": 0.18,
    "car": 0.18,
}
FEASIBILITY = {
    "habitat": 85.0,
    "mixte": 70.0,
    "equipement": 60.0,
    "commerce": 45.0,
    "emploi": 35.0,
}
ACCESS_ROLE = {
    "equipement": 30.0,
    "mixte": 25.0,
    "commerce": 20.0,
    "emploi": 15.0,
    "habitat": 10.0,
}

NORTH_HOMES = (
    "tana.ivato-centre",
    "tana.talatamaty-centre",
    "tana.ambohibao",
    "tana.ambatomaro",
)
NORTH_PARENTS = ("tana.ivato", "tana.talatamaty", "tana.arr5")

CASES: dict[str, dict[str, Any]] = {
    "entreprise": {
        "id": "entreprise",
        "pdf": "6.5.1",
        "title": "Grande organisation centralisée",
        "actor": "DRH",
        "question": "Où ouvrir une annexe pour rapprocher les salariés du siège ?",
        "org_ids": ("exemple-bassin-nord",),
        "home_ids": None,
        "candidate_parents": None,
        "p": 3,
        "kind": "sites",
    },
    "collectivite": {
        "id": "collectivite",
        "pdf": "6.5.2",
        "title": "Terrain mutable en périphérie",
        "actor": "Collectivité",
        "question": "Logements, activités ou mixte : qu'est-ce qui absorbe les navettes ?",
        "org_ids": None,
        "home_ids": NORTH_HOMES,
        "candidate_parents": NORTH_PARENTS,
        "p": 3,
        "kind": "zoning",
        "terrain_id": "tana.ambohibao",
        "activite_ids": ("tana.ambohibao",),
        "mixte_ids": ("tana.ambohibao", "tana.ivato-centre"),
    },
    "multi": {
        "id": "multi",
        "pdf": "6.5.3",
        "title": "Tiers-lieu partagé du bassin nord",
        "actor": "Employeurs du bassin",
        "question": "Un lieu partagé peut-il capter les navettes qui vont au centre ?",
        "org_ids": None,
        "home_ids": NORTH_HOMES,
        "candidate_parents": NORTH_PARENTS,
        "p": 1,
        "kind": "shared",
    },
}


def list_cases() -> list[dict[str, str]]:
    return [
        {
            "id": case["id"],
            "pdf": case["pdf"],
            "title": case["title"],
            "actor": case["actor"],
            "question": case["question"],
        }
        for case in CASES.values()
    ]


def run_case(
    case_id: str,
    *,
    adoption: float = 0.6,
    telework: float = 0.0,
    horizon_years: int = 1,
) -> dict[str, Any]:
    case = CASES.get(case_id)
    if case is None:
        raise ValueError("Cas inconnu.")
    adoption = max(0.2, min(1.0, float(adoption)))
    telework = max(0.0, min(0.8, float(telework)))
    horizon = horizon_years if horizon_years in {1, 3, 5, 10} else 1

    groups = _groups(case)
    if not groups:
        raise ValueError("Aucun groupe simulé pour ce cas.")

    places = _candidates(case)
    kept = [place for place in places if _within_share(groups, place) >= MIN_SHARE]
    relaxed = False
    if len(kept) < case["p"]:
        kept = [place for place in places if _within_share(groups, place) >= 0.15]
        relaxed = True
    if not kept:
        kept = places

    scored = _score_places(groups, kept, adoption)
    chosen = _greedy(groups, kept, int(case["p"]))
    chosen_ids = [place["id"] for place in chosen]
    for row in scored:
        row["selected"] = row["id"] in chosen_ids

    scenarios = _scenarios(case, groups, scored, chosen_ids, adoption, telework, horizon)
    dominant = _dominant(scenarios)
    steps = _steps(case, groups, kept, relaxed, chosen, scored, adoption, telework)
    focus = scored[0] if scored else {"lon": groups[0]["seat_lon"], "lat": groups[0]["seat_lat"]}

    return {
        "case": {
            "id": case["id"],
            "pdf": case["pdf"],
            "title": case["title"],
            "actor": case["actor"],
            "question": case["question"],
        },
        "parameters": {
            "adoption": adoption,
            "telework": telework,
            "horizon_years": horizon,
            "workdays": WORKDAYS,
            "capacity": CAPACITY,
            "within_min": WITHIN_MIN,
        },
        "weights": [
            {"id": key, "label": label, "weight": weight}
            for key, label, weight, _unit in WEIGHTS
        ],
        "steps": steps,
        "candidates": scored[:5],
        "scenarios": scenarios,
        "dominant_id": dominant,
        "focus": {"lon": focus["lon"], "lat": focus["lat"], "name": focus.get("name")},
        "geojson": _geojson(scored[:5], groups),
        "note": (
            "Groupes simulés d'au moins 20 personnes. Distance = orthodromie × 1,35. "
            "Le taux d'adoption plafonne une probabilité de bascule (logit) qui augmente "
            "avec les minutes gagnées. Ordre de grandeur pour comparer des hypothèses, "
            "pas une prédiction ni les chiffres d'illustration du PDF."
        ),
    }


def _groups(case: dict) -> list[dict]:
    rows: list[dict] = []
    for org in ORGANIZATIONS:
        if org["city_id"] != "tana":
            continue
        if case["org_ids"] is not None and org["id"] not in case["org_ids"]:
            continue
        seat = PLACES[org["seat_id"]]
        for cluster in org["clusters"]:
            if not cluster["relocatable"]:
                continue
            if case["home_ids"] is not None and cluster["home_id"] not in case["home_ids"]:
                continue
            home = PLACES[cluster["home_id"]]
            if home["id"] == seat["id"]:
                continue
            km = _road_km(home["lon"], home["lat"], seat["lon"], seat["lat"])
            mode = cluster["mode"] if cluster["mode"] in SPEED_KMH else "bus"
            rows.append(
                {
                    "org_id": org["id"],
                    "org_name": org["name"],
                    "home_id": home["id"],
                    "home_name": home["name"],
                    "home_lon": home["lon"],
                    "home_lat": home["lat"],
                    "seat_id": seat["id"],
                    "seat_name": seat["name"],
                    "seat_lon": seat["lon"],
                    "seat_lat": seat["lat"],
                    "headcount": int(cluster["headcount"]),
                    "mode": mode,
                    "km": km,
                    "minutes": _minutes(km, mode),
                }
            )
    return rows


def _candidates(case: dict) -> list[dict]:
    parents = case["candidate_parents"]
    rows = []
    for place in places_of("tana"):
        if place.get("level") != "quartier":
            continue
        if place.get("role") not in FEASIBILITY:
            continue
        if parents is not None and place.get("parent_id") not in parents:
            continue
        rows.append(place)
    return rows


def _score_places(groups: list[dict], places: list[dict], adoption: float) -> list[dict]:
    raw = []
    for place in places:
        effect = _effect(groups, [place["id"]], adoption, 0.0)
        raw.append(
            {
                "id": place["id"],
                "name": place["name"],
                "role": place.get("role"),
                "lon": place["lon"],
                "lat": place["lat"],
                "parent": place.get("parent_name"),
                "within_share": round(_within_share(groups, place), 2),
                "access": _access(groups, place),
                "feasibility": FEASIBILITY.get(place.get("role"), 40.0),
                "time_min": effect["minutes_saved_per_day"],
                "km": effect["km_saved_per_day"],
                "co2_t": effect["co2_t_year"],
                "people": effect["people"],
            }
        )
    if not raw:
        return []
    time_n = _unit([row["time_min"] for row in raw])
    km_n = _unit([row["km"] for row in raw])
    co2_n = _unit([row["co2_t"] for row in raw])
    for index, row in enumerate(raw):
        parts = {
            "time": time_n[index],
            "km": km_n[index],
            "co2": co2_n[index],
            "access": row["access"],
            "feasibility": row["feasibility"],
        }
        shown = {
            "time": round(row["time_min"], 1),
            "km": round(row["km"], 1),
            "co2": round(row["co2_t"], 2),
            "access": round(row["access"]),
            "feasibility": round(row["feasibility"]),
        }
        total = 0.0
        criteria = []
        for key, label, weight, unit in WEIGHTS:
            total += weight * parts[key]
            criteria.append(
                {
                    "id": key,
                    "label": label,
                    "weight": weight,
                    "score": int(round(parts[key])),
                    "value": shown[key],
                    "unit": unit,
                }
            )
        row["impact_score"] = int(round(total))
        row["criteria"] = criteria
    raw.sort(key=lambda item: item["impact_score"], reverse=True)
    for rank, row in enumerate(raw, start=1):
        row["rank"] = rank
    return raw


def _greedy(groups: list[dict], places: list[dict], p: int) -> list[dict]:
    remaining = list(places)
    chosen: list[dict] = []
    for _ in range(max(1, p)):
        best = None
        best_gain = 0.0
        chosen_ids = [item["id"] for item in chosen]
        for place in remaining:
            gain = _effect(groups, chosen_ids + [place["id"]], 1.0, 0.0)["minutes_saved_per_day"]
            if gain > best_gain + 0.05:
                best_gain = gain
                best = place
        if best is None:
            break
        chosen.append(best)
        remaining = [place for place in remaining if place["id"] != best["id"]]
    return chosen


def _scenarios(
    case: dict,
    groups: list[dict],
    scored: list[dict],
    chosen_ids: list[str],
    adoption: float,
    telework: float,
    horizon: int,
) -> list[dict]:
    reference = _scenario("reference", "Référence — aucune action", groups, [], 0.0, 0.0, horizon)
    if case["kind"] == "zoning":
        housing = _scenario(
            "logements",
            "Logements seuls",
            groups,
            [],
            0.0,
            0.0,
            horizon,
        )
        housing["detail"] = "Le logement seul ne déplace pas l'emploi : les navettes vers le centre restent."
        activite = _scenario(
            "activites",
            "Zone d'activités",
            groups,
            list(case["activite_ids"]),
            adoption,
            0.0,
            horizon,
        )
        mixte = _scenario(
            "mixte",
            "Mixte : activités + tiers-lieu",
            groups,
            list(case["mixte_ids"]),
            adoption,
            0.0,
            horizon,
        )
        return [reference, housing, activite, mixte]

    best_ids = [scored[0]["id"]] if scored else []
    single = _scenario("site", "Meilleur site", groups, best_ids, adoption, 0.0, horizon)
    bundle = _scenario(
        "bundle",
        "Sites retenus par le calcul",
        groups,
        chosen_ids,
        adoption,
        0.0,
        horizon,
    )
    combined_rate = telework if telework > 0 else 0.4
    combined = _scenario(
        "combine",
        "Sites + télétravail"
        if telework > 0
        else "Sites + télétravail 2 j/5",
        groups,
        chosen_ids,
        adoption,
        combined_rate,
        horizon,
    )
    return [reference, single, bundle, combined]


def _scenario(
    scenario_id: str,
    label: str,
    groups: list[dict],
    site_ids: list[str],
    adoption: float,
    telework: float,
    horizon: int,
) -> dict:
    effect = _effect(groups, site_ids, adoption, telework)
    baseline = _effect(groups, [], 0.0, 0.0)
    return {
        "id": scenario_id,
        "label": label,
        "people": effect["people"],
        "basins": effect["basins"],
        "employers": effect["employers"],
        "minutes_per_person": effect["minutes_per_person"],
        "km_saved_per_day": round(effect["km_saved_per_day"], 1),
        "co2_t_year": round(effect["co2_t_year"], 2),
        "co2_t_horizon": round(effect["co2_t_year"] * horizon, 2),
        "trips_captured": effect["trips_captured"],
        "peak_reduction_pct": effect["peak_reduction_pct"],
        "hours_year": effect["hours_year"],
        "avg_minutes_now": baseline["avg_minutes"],
        "avg_minutes_after": effect["avg_minutes"],
    }


def _effect(groups: list[dict], site_ids: list[str], adoption: float, telework: float) -> dict:
    present = 1.0 - telework
    sites = [PLACES[site_id] for site_id in site_ids if site_id in PLACES]
    people = 0.0
    relocate_min = 0.0
    full_min = full_km = full_co2 = 0.0
    actual_min = actual_km = actual_co2 = 0.0
    removed = 0.0
    total_people = 0.0
    basins: set[str] = set()
    employers: set[str] = set()
    room = float(CAPACITY)

    for group in groups:
        head = float(group["headcount"])
        total_people += head
        seat_min = group["minutes"]
        seat_km = group["km"]
        seat_co2 = seat_km * CO2_KG_PER_KM[group["mode"]]
        best_min = seat_min
        best_km = seat_km
        best_co2 = seat_co2
        best_name = None
        for site in sites:
            km = _road_km(group["home_lon"], group["home_lat"], site["lon"], site["lat"])
            minutes = _minutes(km, group["mode"])
            if minutes <= WITHIN_MIN and minutes + 0.4 < best_min:
                best_min = minutes
                best_km = km
                best_co2 = km * CO2_KG_PER_KM[group["mode"]]
                best_name = site["name"]
        share = 0.0
        if best_name is not None:
            share = adoption * _logit(seat_min - best_min)
        moved = min(room, head * share)
        room = max(0.0, room - moved)
        stayed = head - moved
        if moved >= 1 and best_name is not None:
            people += moved
            basins.add(group["home_name"])
            employers.add(group["org_name"])
            relocate_min += moved * 2 * (seat_min - best_min)
        removed += head * telework + moved * present
        full_min += head * 2 * seat_min
        full_km += head * 2 * seat_km
        full_co2 += head * 2 * seat_co2
        actual_min += present * 2 * (stayed * seat_min + moved * best_min)
        actual_km += present * 2 * (stayed * seat_km + moved * best_km)
        actual_co2 += present * 2 * (stayed * seat_co2 + moved * best_co2)

    min_saved = max(0.0, full_min - actual_min)
    km_saved = max(0.0, full_km - actual_km)
    co2_saved_kg = max(0.0, full_co2 - actual_co2) * WORKDAYS
    return {
        "people": int(round(people)),
        "basins": len(basins),
        "employers": len(employers),
        "minutes_saved_per_day": min_saved,
        "minutes_per_person": round(relocate_min / people, 1) if people >= 1 else 0.0,
        "km_saved_per_day": km_saved,
        "co2_t_year": co2_saved_kg / 1000.0,
        "trips_captured": int(round(people)),
        "peak_reduction_pct": round(100.0 * removed / total_people, 1) if total_people else 0.0,
        "hours_year": int(round(min_saved / 60.0 * WORKDAYS)),
        "avg_minutes": round(actual_min / total_people, 1) if total_people else 0.0,
        "baseline_minutes": full_min,
    }


def _logit(minutes_saved: float) -> float:
    if minutes_saved <= 1:
        return 0.0
    return 1.0 / (1.0 + math.exp(-0.15 * (minutes_saved - 10.0)))


def _steps(
    case: dict,
    groups: list[dict],
    kept: list[dict],
    relaxed: bool,
    chosen: list[dict],
    scored: list[dict],
    adoption: float,
    telework: float,
) -> list[dict]:
    people = sum(group["headcount"] for group in groups)
    homes = sorted({group["home_name"] for group in groups})
    orgs = sorted({group["org_name"] for group in groups})
    seats = sorted({group["seat_name"] for group in groups})
    avg_min = round(
        sum(group["headcount"] * 2 * group["minutes"] for group in groups) / people,
        0,
    )
    bary_lon, bary_lat = _barycenter(groups)
    bary_name = _nearest_name(bary_lon, bary_lat, kept or [PLACES[groups[0]["home_id"]]])
    filter_note = (
        f"{len(kept)} quartiers gardés : au moins 30 % des salariés à moins de {WITHIN_MIN:.0f} min."
    )
    if relaxed:
        filter_note = (
            f"Filtre assoupli à 15 % : {len(kept)} quartiers restent à moins de {WITHIN_MIN:.0f} min."
        )
    chosen_names = ", ".join(place["name"] for place in chosen) or "aucun"
    top = scored[0]["name"] if scored else "—"
    top_score = scored[0]["impact_score"] if scored else 0
    return [
        {
            "id": 1,
            "title": "Cartographie de la demande",
            "lines": [
                f"{people} salariés déplaçables, en groupes d'au moins 20, vers {', '.join(seats)}.",
                f"Bassins : {', '.join(homes)}.",
                f"Employeurs : {', '.join(orgs)}.",
                f"Temps actuel moyen : {avg_min:.0f} min/jour (aller-retour).",
                f"Barycentre pondéré des domiciles : vers {bary_name}.",
            ],
        },
        {
            "id": 2,
            "title": "Sites candidats",
            "lines": [
                filter_note,
                "Contrainte douce : rôle du quartier (habitat, mixte, équipement, commerce, emploi) comme proxy de foncier et de desserte.",
                "Pas de PLU ni de prix immobilier dans le jeu simulé.",
            ],
        },
        {
            "id": 3,
            "title": "Choix des emplacements",
            "lines": [
                f"P-médianes glouton, p = {case['p']}. Objectif : minimiser le temps pondéré par l'effectif.",
                f"Sites ouverts par le calcul : {chosen_names}.",
                f"Capacité hypothétique : {CAPACITY} postes. Taux d'adoption du scénario : {adoption:.0%}.",
                "La probabilité de bascule suit un logit sur les minutes gagnées, puis le taux d'adoption.",
            ],
        },
        {
            "id": 4,
            "title": "Score multi-critères",
            "lines": [
                "Poids du PDF : temps 30 %, kilomètres 25 %, CO₂ 20 %, desserte 15 %, faisabilité 10 %.",
                f"Premier du classement : {top} (score {top_score}/100).",
                "La desserte et la faisabilité sont des proxys du rôle du quartier, pas une mesure de bus réel ni de foncier.",
            ],
        },
        {
            "id": 5,
            "title": "Restitution",
            "lines": [
                "La référence (aucune action) reste affichée.",
                "Les autres colonnes sont des hypothèses : un site, le paquet retenu, ou le télétravail combiné.",
                f"Télétravail du curseur : {telework:.0%} des jours."
                if telework > 0
                else "Le curseur télétravail est à 0 : la colonne combinée utilise 2 jours sur 5.",
                "Les points classés sont dessinés sur la carte.",
            ],
        },
    ]


def _dominant(scenarios: list[dict]) -> str:
    ranked = [item for item in scenarios if item["id"] != "reference"]
    if not ranked:
        return "reference"
    best = max(ranked, key=lambda item: (item["co2_t_year"], item["trips_captured"]))
    return best["id"]


def _geojson(scored: list[dict], groups: list[dict]) -> dict:
    features = []
    for row in scored:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                "properties": {
                    "name": row["name"],
                    "rank": row["rank"],
                    "impact_score": row["impact_score"],
                    "type": "barycenter" if row["rank"] == 1 else "candidate",
                },
            }
        )
    lon, lat = _barycenter(groups)
    features.append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            "properties": {"name": "Barycentre des domiciles", "type": "demand"},
        }
    )
    return {"type": "FeatureCollection", "features": features}


def _barycenter(groups: list[dict]) -> tuple[float, float]:
    weight = sum(group["headcount"] for group in groups) or 1
    lon = sum(group["home_lon"] * group["headcount"] for group in groups) / weight
    lat = sum(group["home_lat"] * group["headcount"] for group in groups) / weight
    return lon, lat


def _nearest_name(lon: float, lat: float, places: list[dict]) -> str:
    best = min(places, key=lambda place: _road_km(lon, lat, place["lon"], place["lat"]))
    return best["name"]


def _within_share(groups: list[dict], place: dict) -> float:
    total = sum(group["headcount"] for group in groups) or 1
    close = 0
    for group in groups:
        km = _road_km(group["home_lon"], group["home_lat"], place["lon"], place["lat"])
        if _minutes(km, group["mode"]) <= WITHIN_MIN:
            close += group["headcount"]
    return close / total


def _access(groups: list[dict], place: dict) -> float:
    share = _within_share(groups, place)
    bonus = ACCESS_ROLE.get(place.get("role"), 10.0)
    return max(0.0, min(100.0, share * 80.0 + bonus))


def _unit(values: list[float]) -> list[float]:
    low, high = min(values), max(values)
    if high <= low:
        return [0.0 if high <= 0 else 100.0 for _ in values]
    return [100.0 * (value - low) / (high - low) for value in values]


def _road_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    crow = 2 * radius * math.asin(math.sqrt(min(1.0, arc)))
    return crow * ROAD_FACTOR


def _minutes(km: float, mode: str) -> float:
    speed = SPEED_KMH.get(mode, 16.0)
    return km / speed * 60.0
