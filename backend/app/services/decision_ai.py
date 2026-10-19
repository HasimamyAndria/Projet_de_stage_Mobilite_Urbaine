"""
Aide à la décision domicile-travail — deux méthodes comparables.

1. Algorithme déterministe (formules ci-dessous, reproductible).
2. Même situation envoyée à l'API DeepSeek, sans le résultat de l'algorithme.

Règles :
- moins de 2 km, ou déjà entre 2 et 5 km : rester groupés sur le site, modes actifs ;
- entre 5 et 20 km : annexe dont le domicile tombe dans 2–5 km, sinon
  construction en périphérie (ex. Ivato) et regroupement de l'habitat dans cette couronne ;
- 20–30 km : télétravail 4 jours sur 5 ;
- au-delà de 30 km : télétravail à temps plein.

Les distances sont une orthodromie × 1,35 (proxy de route). Ce n'est pas pgRouting.
"""
from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except Exception:
    pass

# Centroïdes approchés (démo Antananarivo), pas un référentiel cadastral.
PLACES: list[dict[str, Any]] = [
    {"name": "Anosy", "lon": 47.5218, "lat": -18.9142, "kind": "centre"},
    {"name": "Analakely", "lon": 47.5215, "lat": -18.9072, "kind": "centre"},
    {"name": "Antaninarenina", "lon": 47.5262, "lat": -18.9100, "kind": "centre"},
    {"name": "Isoraka", "lon": 47.5168, "lat": -18.9105, "kind": "centre"},
    {"name": "Mahamasina", "lon": 47.5255, "lat": -18.9220, "kind": "centre"},
    {"name": "Behoririka", "lon": 47.5285, "lat": -18.9045, "kind": "centre"},
    {"name": "Ankorondrano", "lon": 47.5230, "lat": -18.8795, "kind": "urbain"},
    {"name": "Andraharo", "lon": 47.5140, "lat": -18.8735, "kind": "urbain"},
    {"name": "Ivandry", "lon": 47.5385, "lat": -18.8695, "kind": "urbain"},
    {"name": "Ambodivona", "lon": 47.5280, "lat": -18.8950, "kind": "urbain"},
    {"name": "Soavimasoandro", "lon": 47.5480, "lat": -18.8920, "kind": "urbain"},
    {"name": "Ankadimbahoaka", "lon": 47.5080, "lat": -18.8550, "kind": "peripherie"},
    {"name": "Talatamaty", "lon": 47.4785, "lat": -18.8465, "kind": "peripherie"},
    {"name": "Ambohibao", "lon": 47.4680, "lat": -18.8580, "kind": "peripherie"},
    {"name": "Antehiroka", "lon": 47.4760, "lat": -18.8220, "kind": "peripherie"},
    {"name": "Ivato", "lon": 47.4788, "lat": -18.7969, "kind": "peripherie"},
    {"name": "Sabotsy Namehana", "lon": 47.5450, "lat": -18.8350, "kind": "peripherie"},
    {"name": "Itaosy", "lon": 47.4650, "lat": -18.9480, "kind": "peripherie"},
    {"name": "Tanjombato", "lon": 47.5280, "lat": -18.9680, "kind": "peripherie"},
    {"name": "Ambohidratrimo", "lon": 47.4350, "lat": -18.8250, "kind": "peripherie"},
    {"name": "Ambohimanga", "lon": 47.5650, "lat": -18.7620, "kind": "lointain"},
    {"name": "Mahitsy", "lon": 47.3480, "lat": -18.7520, "kind": "lointain"},
]

ROAD_FACTOR = 1.35
PEAK_SPEED_KMH = 15.0
LOCAL_SPEED_KMH = 25.0
WORKDAYS = 220
OCCUPANCY = 1.2
FUEL_L_PER_100KM = 7.5
CO2_KG_PER_L = 2.31
HOUSING_TARGET_KM = 3.5
DYNAMISM_HOURS_FOR_100 = 120.0

ACTION_LABELS = {
    "proximite_active": "Proximité : annexe du site et modes actifs",
    "annexe_couronne": "Annexe dans un rayon de 2 à 5 km du domicile",
    "regroupement_habitat": "Annexe en périphérie et habitat regroupé (2 à 5 km)",
    "teletravail": "Télétravail conditionnel",
}


def list_places() -> list[dict[str, Any]]:
    return [
        {"name": p["name"], "lon": p["lon"], "lat": p["lat"], "kind": p["kind"]}
        for p in PLACES
    ]


def _find_place(name: str) -> dict[str, Any] | None:
    key = name.strip().casefold()
    for place in PLACES:
        if place["name"].casefold() == key:
            return place
    return None


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius = 6371.0
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def _road_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return _haversine_km(a, b) * ROAD_FACTOR


def _band(distance_km: float) -> str:
    if distance_km < 2:
        return "lt_2"
    if distance_km <= 5:
        return "ring_2_5"
    if distance_km < 20:
        return "mid_5_20"
    if distance_km <= 30:
        return "remote_20_30"
    return "remote_30_plus"


def _rank_sites(home: dict, work: dict, distance_hw: float) -> list[dict[str, Any]]:
    home_xy = (float(home["lon"]), float(home["lat"]))
    work_xy = (float(work["lon"]), float(work["lat"]))
    ranked: list[dict[str, Any]] = []
    for place in PLACES:
        if place["name"] in (home["name"], work["name"]):
            continue
        d_home = _road_km(home_xy, (float(place["lon"]), float(place["lat"])))
        d_work = _road_km(work_xy, (float(place["lon"]), float(place["lat"])))
        saved = distance_hw - d_home
        in_ring = 2.0 <= d_home <= 5.0
        peripheral = d_work >= 6.0
        score = saved * 10.0
        if in_ring:
            score += 50.0
        elif d_home < 2.0:
            score += 10.0
        else:
            score -= (d_home - 5.0) * 8.0
        if peripheral:
            score += 15.0
        else:
            score -= 20.0
        if saved <= 0:
            score -= 30.0
        ranked.append(
            {
                "name": place["name"],
                "lon": place["lon"],
                "lat": place["lat"],
                "kind": place["kind"],
                "distance_home_km": round(d_home, 2),
                "distance_work_km": round(d_work, 2),
                "in_ring_2_5": in_ring,
                "peripheral": peripheral,
                "score": round(score, 1),
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def _impacts(employees: int, legs: list[dict[str, Any]]) -> dict[str, float]:
    km = 0.0
    fuel_l = 0.0
    co2_t = 0.0
    time_h = 0.0
    vehicle_city_days = 0.0
    for leg in legs:
        share = float(leg["day_share"])
        dist = float(leg["dist_km"])
        person_km = employees * dist * 2.0 * WORKDAYS * share
        km += person_km
        vehicle_km = person_km * float(leg["fuel_share"]) / OCCUPANCY
        fuel = vehicle_km * FUEL_L_PER_100KM / 100.0
        fuel_l += fuel
        co2_t += fuel * CO2_KG_PER_L / 1000.0
        time_h += employees * (dist / float(leg["speed"])) * 2.0 * WORKDAYS * share
        if leg["enters_city"]:
            vehicle_city_days += (
                employees / OCCUPANCY * WORKDAYS * share * float(leg["fuel_share"])
            )
    return {
        "km": km,
        "fuel_l": fuel_l,
        "co2_t": co2_t,
        "time_h": time_h,
        "vehicle_city_days": vehicle_city_days,
    }


def _round_impacts(raw: dict[str, float]) -> dict[str, float]:
    return {
        "km": round(raw["km"], 0),
        "fuel_l": round(raw["fuel_l"], 0),
        "co2_t": round(raw["co2_t"], 2),
        "time_h": round(raw["time_h"], 0),
        "vehicle_city_days": round(raw["vehicle_city_days"], 0),
    }


def _benefits(baseline: dict[str, float], scenario: dict[str, float], employees: int) -> dict[str, Any]:
    def delta(key: str) -> float:
        return baseline[key] - scenario[key]

    km = delta("km")
    fuel = delta("fuel_l")
    co2 = delta("co2_t")
    time_h = delta("time_h")
    city = delta("vehicle_city_days")
    traffic_pct = 0.0 if baseline["vehicle_city_days"] <= 0 else 100.0 * city / baseline["vehicle_city_days"]
    pollution_pct = 0.0 if baseline["co2_t"] <= 0 else 100.0 * co2 / baseline["co2_t"]
    hours_per = 0.0 if employees <= 0 else time_h / employees
    dynamism = max(0.0, min(100.0, hours_per / DYNAMISM_HOURS_FOR_100 * 100.0))
    return {
        "km_avoided": round(km, 0),
        "fuel_l_saved": round(fuel, 0),
        "co2_t_avoided": round(co2, 2),
        "time_h_saved": round(time_h, 0),
        "city_vehicle_days_avoided": round(city, 0),
        "traffic_reduction_pct": round(traffic_pct, 1),
        "pollution_reduction_pct": round(pollution_pct, 1),
        "hours_saved_per_employee": round(hours_per, 1),
        "dynamism_index": round(dynamism, 0),
    }


def _baseline_legs(distance_km: float) -> list[dict[str, Any]]:
    return [
        {
            "dist_km": distance_km,
            "speed": PEAK_SPEED_KMH,
            "day_share": 1.0,
            "fuel_share": 1.0,
            "enters_city": True,
        }
    ]


def _ivato_aside(ranked: list[dict[str, Any]], chosen: dict[str, Any]) -> str:
    ivato = next((item for item in ranked if item["name"] == "Ivato"), None)
    if not ivato or ivato["name"] == chosen["name"] or ivato["in_ring_2_5"]:
        return ""
    return (
        f" Ivato reste une variante de périphérie nord, à {ivato['distance_home_km']:.1f} km "
        "du domicile : hors de la couronne 2–5 km, donc seulement en regroupant l'habitat autour."
    )


def _site_public(site: dict[str, Any] | None) -> dict[str, Any] | None:
    if not site:
        return None
    return {
        "name": site["name"],
        "lon": site["lon"],
        "lat": site["lat"],
        "distance_home_km": site["distance_home_km"],
        "distance_work_km": site["distance_work_km"],
        "in_ring_2_5": site["in_ring_2_5"],
    }


def _pack(
    action: str,
    site: dict[str, Any] | None,
    rationale: str,
    employees: int,
    legs: list[dict[str, Any]],
    distance_hw: float,
    remote_share: float,
) -> dict[str, Any]:
    baseline = _impacts(employees, _baseline_legs(distance_hw))
    scenario = _impacts(employees, legs)
    benefits = _benefits(baseline, scenario, employees)
    benefits["narrative"] = (
        f"{benefits['traffic_reduction_pct']:.0f} % de véhicules en moins vers le centre, "
        f"{benefits['co2_t_avoided']:.1f} t de CO₂ évitées, "
        f"{benefits['fuel_l_saved']:.0f} L de carburant, "
        f"{benefits['km_avoided']:.0f} km et {benefits['time_h_saved']:.0f} h de trajet. "
        f"Indice de dynamisme {benefits['dynamism_index']:.0f}/100 "
        f"({benefits['hours_saved_per_employee']:.0f} h rendues par salarié et par an)."
    )
    return {
        "action": action,
        "label": ACTION_LABELS[action],
        "site": _site_public(site),
        "remote_eligible": distance_hw >= 20.0,
        "remote_share": remote_share,
        "rationale": rationale,
        "baseline": _round_impacts(baseline),
        "scenario": _round_impacts(scenario),
        "benefits": benefits,
    }


def _annex_legs(distance_hw: float, site: dict[str, Any]) -> list[dict[str, Any]]:
    d_home = float(site["distance_home_km"])
    local_fuel = 0.55 if d_home <= 5.0 else 0.85
    return [
        {
            "dist_km": d_home,
            "speed": LOCAL_SPEED_KMH,
            "day_share": 0.8,
            "fuel_share": local_fuel,
            "enters_city": not site["peripheral"],
        },
        {
            "dist_km": distance_hw,
            "speed": PEAK_SPEED_KMH,
            "day_share": 0.2,
            "fuel_share": 1.0,
            "enters_city": True,
        },
    ]


def _housing_legs(site: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "dist_km": HOUSING_TARGET_KM,
            "speed": LOCAL_SPEED_KMH,
            "day_share": 1.0,
            "fuel_share": 0.45,
            "enters_city": not site["peripheral"],
        }
    ]


def decide_algorithm(
    home_name: str,
    work_name: str,
    employees: int = 80,
    work_label: str = "Domaine Finance",
) -> dict[str, Any]:
    home = _find_place(home_name)
    work = _find_place(work_name)
    if home is None or work is None:
        known = ", ".join(p["name"] for p in PLACES)
        missing = home_name if home is None else work_name
        raise ValueError(f"Lieu inconnu : {missing}. Lieux disponibles : {known}.")
    if home["name"] == work["name"]:
        raise ValueError("Le domicile et le lieu de travail doivent être distincts.")
    if employees < 1:
        raise ValueError("L'effectif doit être d'au moins 1 salarié.")

    employees = int(employees)
    label = (work_label or "le site").strip() or "le site"
    home_xy = (float(home["lon"]), float(home["lat"]))
    work_xy = (float(work["lon"]), float(work["lat"]))
    straight = _haversine_km(home_xy, work_xy)
    distance = _road_km(home_xy, work_xy)
    band = _band(distance)
    ranked = _rank_sites(home, work, distance)
    ring = sorted(
        (item for item in ranked if item["in_ring_2_5"]),
        key=lambda item: item["distance_home_km"],
    )
    peripheral = [
        item for item in sorted(ranked, key=lambda item: item["distance_home_km"]) if item["peripheral"]
    ]
    chosen_ring = ring[0] if ring else None
    chosen_out = peripheral[0] if peripheral else ranked[0]
    best = chosen_ring or chosen_out
    remote_share = 1.0 if distance > 30 else (0.8 if distance >= 20 else 0.0)

    common = (
        f"{employees} salariés de {label} à {work['name']} habitent à {home['name']}. "
        f"Distance estimée {distance:.1f} km de route ({straight:.1f} km à vol d'oiseau), "
        f"en pointe dans les deux sens (environ {PEAK_SPEED_KMH:.0f} km/h)."
    )

    if band in {"lt_2", "ring_2_5"}:
        fuel_share = 0.35 if distance < 2 else 0.50
        speed = 18.0 if distance < 2 else 20.0
        rationale = (
            f"{common} Ils sont déjà dans la couronne utile (moins de 5 km) : "
            "pas de télétravail et pas de nouvelle cité en périphérie. "
            f"Les regrouper dans l'annexe de {work['name']} et reporter une partie des trajets "
            "vers la marche et le vélo."
        )
        primary = _pack(
            "proximite_active",
            None,
            rationale,
            employees,
            [
                {
                    "dist_km": distance,
                    "speed": speed,
                    "day_share": 1.0,
                    "fuel_share": fuel_share,
                    "enters_city": True,
                }
            ],
            distance,
            0.0,
        )
    elif band == "mid_5_20":
        best = chosen_ring if chosen_ring else chosen_out
        if chosen_ring:
            rationale = (
                f"{common} Le seuil de télétravail (20 km) n'est pas atteint. "
                f"Le site {best['name']} met le domicile dans la couronne de 2 à 5 km "
                f"({best['distance_home_km']:.1f} km) et reste à {best['distance_work_km']:.1f} km du siège. "
                "Quatre jours sur cinq, le travail se fait dans cette annexe ; un jour reste au siège. "
                "Les embauches suivantes peuvent resserrer l'habitat dans le même rayon."
                + _ivato_aside(ranked, best)
            )
            primary = _pack(
                "annexe_couronne",
                best,
                rationale,
                employees,
                _annex_legs(distance, best),
                distance,
                0.0,
            )
        else:
            rationale = (
                f"{common} Aucun site du référentiel ne place le domicile actuel entre 2 et 5 km. "
                f"Construire l'annexe à {best['name']} "
                f"({best['distance_home_km']:.1f} km du domicile actuel, "
                f"{best['distance_work_km']:.1f} km du siège) et regrouper les logements salariés "
                f"dans un rayon de 2 à 5 km autour de cette annexe (cible {HOUSING_TARGET_KM:.1f} km). "
                "Ivato illustre ce type d'implantation en périphérie nord quand le bassin y est proche. "
                "Le télétravail n'est pas retenu : le domicile est à moins de 20 km."
            )
            primary = _pack(
                "regroupement_habitat",
                best,
                rationale,
                employees,
                _housing_legs(best),
                distance,
                0.0,
            )
    else:
        days = "à temps plein" if remote_share >= 1 else "4 jours sur 5"
        window = "au-delà de 30 km" if distance > 30 else "dans la fourchette 20–30 km"
        rationale = (
            f"{common} Le domicile est {window}. "
            f"Le télétravail est proposé {days} : c'est la condition qui évite les longs "
            f"allers-retours vers {work['name']} sans obliger à reloger tout l'effectif. "
            "Une annexe reste possible pour les jours de présence, mais ce n'est pas l'action principale."
        )
        primary = _pack(
            "teletravail",
            None,
            rationale,
            employees,
            [
                {
                    "dist_km": distance,
                    "speed": PEAK_SPEED_KMH,
                    "day_share": 1.0 - remote_share,
                    "fuel_share": 1.0,
                    "enters_city": True,
                }
            ],
            distance,
            remote_share,
        )

    alternatives: list[dict[str, Any]] = []
    if primary["action"] == "annexe_couronne":
        alternatives.append(
            _pack(
                "regroupement_habitat",
                best,
                (
                    f"Variante logement : rapprocher l'habitat à {HOUSING_TARGET_KM:.1f} km "
                    f"de l'annexe de {best['name']}, au lieu de garder les domiciles actuels."
                ),
                employees,
                _housing_legs(best),
                distance,
                0.0,
            )
        )
    if primary["action"] == "teletravail" and best["in_ring_2_5"]:
        alternatives.append(
            _pack(
                "annexe_couronne",
                best,
                (
                    f"Non retenue comme action principale : {best['name']} est dans les 2–5 km, "
                    "mais la règle remote s'applique d'abord à partir de 20 km."
                ),
                employees,
                _annex_legs(distance, best),
                distance,
                0.0,
            )
        )

    ivato = next((item for item in ranked if item["name"] == "Ivato"), None)
    if (
        ivato
        and band == "mid_5_20"
        and (primary["site"] or {}).get("name") != "Ivato"
    ):
        ivato_action = "annexe_couronne" if ivato["in_ring_2_5"] else "regroupement_habitat"
        ivato_legs = _annex_legs(distance, ivato) if ivato["in_ring_2_5"] else _housing_legs(ivato)
        alternatives.append(
            _pack(
                ivato_action,
                ivato,
                (
                    f"Variante périphérie Ivato : {ivato['distance_home_km']:.1f} km du domicile, "
                    f"{ivato['distance_work_km']:.1f} km du siège. "
                    + (
                        "Le domicile est déjà dans la couronne 2–5 km."
                        if ivato["in_ring_2_5"]
                        else "Hors couronne 2–5 km : l'intérêt d'Ivato suppose de regrouper l'habitat autour du site."
                    )
                ),
                employees,
                ivato_legs,
                distance,
                0.0,
            )
        )

    return {
        "method": "algorithm",
        "model": "rules-distance-v1",
        "input": {
            "home": {"name": home["name"], "lon": home["lon"], "lat": home["lat"]},
            "work": {"name": work["name"], "lon": work["lon"], "lat": work["lat"]},
            "work_label": label,
            "employees": employees,
            "distance_km_straight": round(straight, 2),
            "distance_km_road": round(distance, 2),
            "band": band,
        },
        "primary": primary,
        "alternatives": alternatives[:3],
        "candidates": [
            {
                "name": item["name"],
                "distance_home_km": item["distance_home_km"],
                "distance_work_km": item["distance_work_km"],
                "in_ring_2_5": item["in_ring_2_5"],
                "peripheral": item["peripheral"],
            }
            for item in sorted(ranked, key=lambda item: item["distance_home_km"])[:6]
        ],
        "hypotheses": {
            "road_factor": ROAD_FACTOR,
            "peak_speed_kmh": PEAK_SPEED_KMH,
            "local_speed_kmh": LOCAL_SPEED_KMH,
            "workdays": WORKDAYS,
            "occupancy_pers_per_vehicle": OCCUPANCY,
            "fuel_l_per_100km": FUEL_L_PER_100KM,
            "co2_kg_per_litre": CO2_KG_PER_L,
            "housing_target_km": HOUSING_TARGET_KM,
            "annex_share_of_days": 0.8,
            "remote_share_20_30": 0.8,
            "remote_share_over_30": 1.0,
            "dynamism_hours_for_index_100": DYNAMISM_HOURS_FOR_100,
            "note": (
                "Proxy d'aide à la décision. La distance n'est pas un itinéraire pgRouting. "
                "L'indice de dynamisme mesure le temps de trajet rendu (100 = 120 h/salarié/an), "
                "pas une productivité RH observée. Le CO₂ suit le carburant (2,31 kg/L)."
            ),
        },
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Réponse DeepSeek : JSON objet attendu.")
    return data


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _deepseek_prompt(decision: dict[str, Any]) -> str:
    info = decision["input"]
    lines = [
        f"Domicile : {info['home']['name']}",
        f"Travail : {info['work_label']} à {info['work']['name']}",
        f"Effectif : {info['employees']}",
        f"Distance route estimée (déjà calculée, ne pas la modifier) : {info['distance_km_road']} km",
        f"Distance à vol d'oiseau : {info['distance_km_straight']} km",
        "Candidats d'annexe (distance domicile, distance siège, dans la couronne 2–5 km) :",
    ]
    for cand in decision["candidates"]:
        ring = "oui" if cand["in_ring_2_5"] else "non"
        lines.append(
            f"- {cand['name']} : {cand['distance_home_km']} km du domicile, "
            f"{cand['distance_work_km']} km du siège, couronne 2–5 km = {ring}"
        )
    lines.append(
        "Hypothèses de chiffrage : 220 jours, aller-retour, pointe 15 km/h, "
        "trajet local 25 km/h, 7,5 L/100 km, 1,2 personne par véhicule, 2,31 kg CO₂ par litre, "
        "annexe = 4 jours sur 5 sur place et 1 jour au siège, "
        "habitat regroupé = trajet cible 3,5 km, "
        "télétravail 20–30 km = 4 jours sur 5, au-delà de 30 km = temps plein. "
        "L'indice de dynamisme vaut 100 lorsque 120 h de trajet sont rendues par salarié et par an."
    )
    return "\n".join(lines)


_DEEPSEEK_SYSTEM = """Tu es un assistant d'aide à la décision pour les trajets domicile-travail à Antananarivo.
Tu appliques STRICTEMENT les règles suivantes. Tu réponds uniquement avec un objet JSON, sans markdown.

Règles de choix :
- distance < 2 km, ou distance entre 2 et 5 km : primary_action = proximite_active, site_name = null.
  Les salariés sont déjà proches : annexe du site et modes actifs. Pas de télétravail.
- 5 km < distance < 20 km :
  - s'il existe un candidat dont la distance domicile est entre 2 et 5 km, primary_action = annexe_couronne et site_name = le plus proche du domicile dans cette couronne ;
  - sinon primary_action = regroupement_habitat et site_name = le candidat périphérique (au moins 6 km du siège) le plus proche du domicile. Les logements sont à regrouper entre 2 et 5 km de cette annexe. Ivato n'est retenu que s'il est ce candidat, pas par défaut.
- 20 km <= distance <= 30 km : primary_action = teletravail, site_name = null (4 jours sur 5).
- distance > 30 km : primary_action = teletravail, site_name = null (temps plein).
Le télétravail n'est jamais l'action principale en dessous de 20 km.

Calcule les avantages annuels pour l'effectif, avec les hypothèses fournies.
Schéma JSON :
{
  "primary_action": "proximite_active|annexe_couronne|regroupement_habitat|teletravail",
  "site_name": "nom exact d'un candidat ou null",
  "rationale": "4 à 6 phrases en français, concrètes",
  "benefits": {
    "traffic_reduction_pct": 0,
    "co2_t_avoided": 0,
    "fuel_l_saved": 0,
    "km_avoided": 0,
    "time_h_saved": 0,
    "dynamism_index": 0,
    "narrative": "une phrase sur le trafic, la pollution, le carburant, les déplacements en ville et le dynamisme"
  }
}"""


def _call_deepseek(decision: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return {
            "method": "deepseek",
            "available": False,
            "skipped": False,
            "error": (
                "Clé DEEPSEEK_API_KEY absente du fichier .env. "
                "L'algorithme reste utilisable. Ajoutez la clé pour comparer les deux méthodes."
            ),
            "model": None,
            "primary_action": None,
            "site_name": None,
            "rationale": None,
            "benefits": None,
        }

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _DEEPSEEK_SYSTEM},
            {"role": "user", "content": _deepseek_prompt(decision)},
        ],
    }
    request = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        exc.read()
        if exc.code == 401:
            message = (
                "DeepSeek a refusé la clé API (HTTP 401). "
                "Vérifiez DEEPSEEK_API_KEY dans le fichier .env."
            )
        elif exc.code == 402:
            message = "Quota DeepSeek insuffisant (HTTP 402)."
        elif exc.code == 429:
            message = "DeepSeek limite le débit (HTTP 429). Réessayez dans un instant."
        else:
            message = f"DeepSeek a répondu HTTP {exc.code}."
        return {
            "method": "deepseek",
            "available": False,
            "skipped": False,
            "error": message,
            "model": model,
            "primary_action": None,
            "site_name": None,
            "rationale": None,
            "benefits": None,
        }
    except Exception as exc:  # noqa: BLE001 — remonter un message court, pas la clé
        return {
            "method": "deepseek",
            "available": False,
            "skipped": False,
            "error": f"Appel DeepSeek impossible ({type(exc).__name__}).",
            "model": model,
            "primary_action": None,
            "site_name": None,
            "rationale": None,
            "benefits": None,
        }

    try:
        content = body["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError):
        return {
            "method": "deepseek",
            "available": False,
            "skipped": False,
            "error": "Réponse DeepSeek illisible (JSON attendu).",
            "model": model,
            "primary_action": None,
            "site_name": None,
            "rationale": None,
            "benefits": None,
        }

    action = str(parsed.get("primary_action") or "").strip()
    if action not in ACTION_LABELS:
        action = "inconnu"
    site_name = parsed.get("site_name")
    if site_name in ("", "null", None):
        site_name = None
    elif not isinstance(site_name, str):
        site_name = str(site_name)
    benefits_raw = parsed.get("benefits") if isinstance(parsed.get("benefits"), dict) else {}
    benefits = {
        "traffic_reduction_pct": _num(benefits_raw.get("traffic_reduction_pct")),
        "co2_t_avoided": _num(benefits_raw.get("co2_t_avoided")),
        "fuel_l_saved": _num(benefits_raw.get("fuel_l_saved")),
        "km_avoided": _num(benefits_raw.get("km_avoided")),
        "time_h_saved": _num(benefits_raw.get("time_h_saved")),
        "dynamism_index": _num(benefits_raw.get("dynamism_index")),
        "pollution_reduction_pct": _num(benefits_raw.get("pollution_reduction_pct")),
        "narrative": str(benefits_raw.get("narrative") or "").strip(),
    }
    return {
        "method": "deepseek",
        "available": True,
        "skipped": False,
        "error": None,
        "model": model,
        "primary_action": action,
        "label": ACTION_LABELS.get(action, action),
        "site_name": site_name,
        "rationale": str(parsed.get("rationale") or "").strip(),
        "benefits": benefits,
    }


def _comparison(algorithm: dict[str, Any], deepseek: dict[str, Any]) -> dict[str, Any] | None:
    if not deepseek.get("available"):
        return None
    algo_action = algorithm["primary"]["action"]
    ds_action = deepseek.get("primary_action")
    algo_site = (algorithm["primary"].get("site") or {}).get("name")
    ds_site = deepseek.get("site_name")
    same_action = algo_action == ds_action
    same_site = (algo_site or None) == (ds_site or None)
    deltas: dict[str, float | None] = {}
    algo_b = algorithm["primary"]["benefits"]
    ds_b = deepseek.get("benefits") or {}
    for key in (
        "traffic_reduction_pct",
        "co2_t_avoided",
        "fuel_l_saved",
        "km_avoided",
        "time_h_saved",
        "dynamism_index",
    ):
        ds_val = ds_b.get(key)
        if ds_val is None:
            deltas[key] = None
        else:
            deltas[key] = round(float(algo_b[key]) - float(ds_val), 2)
    if same_action and same_site:
        reading = "Les deux méthodes retiennent la même action et le même site. L'écart porte sur les chiffres : l'algorithme applique les formules, DeepSeek les estime."
    elif same_action:
        reading = "Même famille d'action, site différent. L'algorithme sert de référence chiffrée."
    else:
        reading = "Divergence de décision. L'algorithme reste la référence auditable ; DeepSeek est un second avis sur les mêmes règles."
    return {
        "same_action": same_action,
        "same_site": same_site,
        "algorithm_action": algo_action,
        "deepseek_action": ds_action,
        "algorithm_site": algo_site,
        "deepseek_site": ds_site,
        "deltas_algorithm_minus_deepseek": deltas,
        "reading": reading,
    }


def compare_decision(
    home_name: str,
    work_name: str,
    employees: int = 80,
    work_label: str = "Domaine Finance",
    include_deepseek: bool = True,
) -> dict[str, Any]:
    algorithm = decide_algorithm(home_name, work_name, employees, work_label)
    if not include_deepseek:
        deepseek = {
            "method": "deepseek",
            "available": False,
            "skipped": True,
            "error": None,
            "model": None,
            "primary_action": None,
            "site_name": None,
            "rationale": None,
            "benefits": None,
        }
    else:
        deepseek = _call_deepseek(algorithm)
    return {
        "input": algorithm["input"],
        "hypotheses": algorithm["hypotheses"],
        "candidates": algorithm["candidates"],
        "algorithm": {
            "method": algorithm["method"],
            "model": algorithm["model"],
            "primary": algorithm["primary"],
            "alternatives": algorithm["alternatives"],
        },
        "deepseek": deepseek,
        "comparison": _comparison(algorithm, deepseek),
    }
