"""
Lecture territoriale : arrondissement, quartier, origine et destination.

L'indice emploi-habitat est lu avec les navettes. Un quartier surtout
résidentiel envoie ses habitants travailler ailleurs : ce déséquilibre
est le déplacement domicile-travail.

Les volumes sont des groupes simulés (20 personnes et plus).
"""
from __future__ import annotations

import math
import unicodedata
from collections import defaultdict

from app.data.organizations import ORGANIZATIONS, REGULAR_ERRANDS
from app.data.territory import CITIES, PLACES, ROLES, places_of

ROAD_FACTOR = 1.35
MIN_GAIN_KM = 4.0
MAX_ANNEX_KM = 8.0
HOST_ROLES = {"emploi", "mixte", "equipement", "commerce"}

PURPOSE_LABELS = {
    "travail": "Travail",
    "courses": "Courses",
    "culte": "Culte",
    "ecole": "École",
    "sante": "Santé",
    "visite": "Visite",
}


def _zone_kind(role: str) -> str:
    return {
        "emploi": "zone d'emploi",
        "mixte": "zone mixte",
        "equipement": "zone d'équipement",
        "commerce": "zone commerciale",
        "habitat": "zone d'habitat",
    }.get(role, "zone")


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value.lower().strip())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.split(",")[0].strip()


def resolve_city(label: str) -> dict:
    folded = _fold(label)
    for city in CITIES:
        names = {_fold(city["id"]), _fold(city["name"]), _fold(city["aka"])}
        if folded in names or any(name and name in folded for name in names):
            return city
    raise ValueError(
        f"« {label} » n'est pas dans le catalogue "
        "(villes d'au moins 200 000 habitants)."
    )


def _km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    crow = 2 * radius * math.asin(math.sqrt(min(1.0, arc)))
    return round(crow * ROAD_FACTOR, 1)


def _circle(lon: float, lat: float, radius_m: float) -> dict:
    steps = 28
    lat_rad = math.radians(lat)
    dlat = radius_m / 111_320
    dlon = radius_m / (111_320 * max(0.2, math.cos(lat_rad)))
    ring = []
    for index in range(steps + 1):
        angle = 2 * math.pi * index / steps
        ring.append([round(lon + dlon * math.cos(angle), 6), round(lat + dlat * math.sin(angle), 6)])
    return {"type": "Polygon", "coordinates": [ring]}


def _join(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} et {names[1]}"
    return ", ".join(names[:-1]) + " et " + names[-1]


def _de_name(name: str) -> str:
    if name[:1].lower() in "aeiouyàâäéèêëîïôöùûüh":
        return f"d'{name}"
    return f"de {name}"


def _de_list(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return _de_name(names[0])
    if len(names) == 2:
        return f"{_de_name(names[0])} et {_de_name(names[1])}"
    return ", ".join(_de_name(name) for name in names[:-1]) + " et " + _de_name(names[-1])


def _expand(city_id: str, raw: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        place = PLACES.get(token)
        if place is None or place["city_id"] != city_id:
            continue
        if place["level"] == "quartier":
            ids = [token]
        elif place["level"] == "commune":
            ids = [
                item["id"]
                for item in places_of(city_id)
                if item["level"] == "quartier" and item["parent_id"] == token
            ]
        else:
            ids = []
        for item_id in ids:
            if item_id not in seen:
                seen.add(item_id)
                found.append(item_id)
    return found


def _eh(residents: int, jobs: int) -> float | None:
    total = residents + jobs
    if total <= 0:
        return None
    return round(1 - abs(jobs - residents) / total, 2)


def _inside(place_id: str) -> str:
    place = PLACES[place_id]
    role = ROLES.get(place["role"], place["role"])
    seated = [org["name"] for org in ORGANIZATIONS if org["seat_id"] == place_id]
    if seated:
        activities = [org["activity"] for org in ORGANIZATIONS if org["seat_id"] == place_id]
        return f"{role} — {', '.join(seated)} ({'; '.join(activities)})"
    return f"{role} — pas de siège d'organisation dans le jeu simulé"


def _edges(city_id: str) -> list[dict]:
    rows: list[dict] = []
    for org in ORGANIZATIONS:
        if org["city_id"] != city_id:
            continue
        seat = PLACES[org["seat_id"]]
        for cluster in org["clusters"]:
            home = PLACES[cluster["home_id"]]
            distance = _km(home["lon"], home["lat"], seat["lon"], seat["lat"])
            count = cluster["headcount"]
            rows.append(
                {
                    "origin_id": home["id"],
                    "destination_id": seat["id"],
                    "purpose": "travail",
                    "purpose_label": "Travail",
                    "detail": org["activity"],
                    "headcount": count,
                    "km": distance,
                    "time_min": int(round(distance / 18 * 60)),
                    "frequency": "5 jours/semaine",
                    "cadence": "jours ouvrés",
                    "mode": cluster["mode"],
                    "regular": True,
                    "organization_id": org["id"],
                    "organization_name": org["name"],
                    "organization_kind": org["kind_label"],
                    "why": (
                        f"{org['name']} : {count} employés habitent {home['name']} "
                        f"et travaillent à {seat['name']} ({distance} km, jours ouvrés)."
                    ),
                }
            )
    for errand in REGULAR_ERRANDS:
        if errand["city_id"] != city_id:
            continue
        home = PLACES[errand["home_id"]]
        dest = PLACES[errand["dest_id"]]
        distance = _km(home["lon"], home["lat"], dest["lon"], dest["lat"])
        label = PURPOSE_LABELS.get(errand["purpose"], errand["purpose"])
        count = errand["headcount"]
        rows.append(
            {
                "origin_id": home["id"],
                "destination_id": dest["id"],
                "purpose": errand["purpose"],
                "purpose_label": label,
                "detail": errand["detail"],
                "headcount": count,
                "km": distance,
                "time_min": int(round(distance / 18 * 60)),
                "frequency": "hebdomadaire",
                "cadence": errand["cadence"],
                "mode": errand["mode"],
                "regular": True,
                "organization_id": None,
                "organization_name": None,
                "organization_kind": None,
                "why": (
                    f"{count} habitants {_de_name(home['name'])} vont à {dest['name']} "
                    f"pour {label.lower()} ({errand['cadence']}, {distance} km). "
                    f"Sur place : {_inside(dest['id'])}."
                ),
            }
        )
    return rows


def _public_flow(row: dict) -> dict:
    origin = PLACES[row["origin_id"]]
    dest = PLACES[row["destination_id"]]
    origin_parent = PLACES[origin["parent_id"]]
    dest_parent = PLACES[dest["parent_id"]]
    return {
        **row,
        "origin_name": origin["name"],
        "destination_name": dest["name"],
        "origin_lon": origin["lon"],
        "origin_lat": origin["lat"],
        "destination_lon": dest["lon"],
        "destination_lat": dest["lat"],
        "origin_parent_id": origin_parent["id"],
        "origin_parent_name": origin_parent["name"],
        "destination_parent_id": dest_parent["id"],
        "destination_parent_name": dest_parent["name"],
        "destination_role": dest["role"],
        "destination_role_label": ROLES.get(dest["role"], dest["role"]),
        "inside": _inside(dest["id"]),
    }


def _quartier_stats(work_rows: list[dict], quartiers: list[dict]) -> list[dict]:
    residents: dict[str, int] = defaultdict(int)
    jobs: dict[str, int] = defaultdict(int)
    km_sum: dict[str, float] = defaultdict(float)
    leave: dict[str, int] = defaultdict(int)
    for row in work_rows:
        residents[row["origin_id"]] += row["headcount"]
        jobs[row["destination_id"]] += row["headcount"]
        km_sum[row["origin_id"]] += row["km"] * row["headcount"]
        if row["origin_id"] != row["destination_id"]:
            leave[row["origin_id"]] += row["headcount"]
    stats = []
    for place in quartiers:
        pop = residents[place["id"]]
        job_count = jobs[place["id"]]
        stats.append(
            {
                "id": place["id"],
                "name": place["name"],
                "parent_id": place["parent_id"],
                "parent_name": place["parent_name"],
                "role": place["role"],
                "role_label": ROLES.get(place["role"], place["role"]),
                "lon": place["lon"],
                "lat": place["lat"],
                "residents": pop,
                "jobs": job_count,
                "eh_index": _eh(pop, job_count),
                "outbound_share": round(leave[place["id"]] / pop, 2) if pop else 0,
                "mean_km": round(km_sum[place["id"]] / pop, 1) if pop else None,
            }
        )
    return stats


def _weighted_eh(stats: list[dict]) -> float | None:
    weight = 0
    total = 0.0
    for item in stats:
        if item["eh_index"] is None:
            continue
        people = item["residents"] + item["jobs"]
        if people <= 0:
            continue
        weight += people
        total += item["eh_index"] * people
    if weight <= 0:
        return None
    return round(total / weight, 2)


def _relocations(work_rows: list[dict], city_id: str, origin_ids: set[str]) -> list[dict]:
    hosts = [
        place
        for place in places_of(city_id)
        if place["level"] == "quartier" and place["role"] in HOST_ROLES
    ]
    ideas = []
    for row in work_rows:
        if row["purpose"] != "travail":
            continue
        if origin_ids and row["origin_id"] not in origin_ids:
            continue
        if row["km"] < MIN_GAIN_KM + 2:
            continue
        home = PLACES[row["origin_id"]]
        best = None
        for host in hosts:
            if host["id"] in {row["origin_id"], row["destination_id"]}:
                continue
            annex_km = _km(home["lon"], home["lat"], host["lon"], host["lat"])
            gain = round(row["km"] - annex_km, 1)
            if annex_km > MAX_ANNEX_KM or gain < MIN_GAIN_KM:
                continue
            if best is None or gain > best["gain_km"]:
                best = {"host": host, "annex_km": annex_km, "gain_km": gain}
        if best is None:
            continue
        host = best["host"]
        count = row["headcount"]
        ideas.append(
            {
                "organization_name": row["organization_name"],
                "headcount": count,
                "home_name": home["name"],
                "home_parent": home["parent_name"],
                "work_name": PLACES[row["destination_id"]]["name"],
                "km": row["km"],
                "empty_zone_id": host["id"],
                "empty_zone_name": host["name"],
                "empty_zone_parent": host["parent_name"],
                "empty_zone_role": ROLES.get(host["role"], host["role"]),
                "annex_km": best["annex_km"],
                "gain_km": best["gain_km"],
                "text": (
                    f"{row['organization_name']} : {count} employés habitent {home['name']} "
                    f"({home['parent_name']}) et travaillent à "
                    f"{PLACES[row['destination_id']]['name']}, à {row['km']} km. "
                    f"Le quartier {host['name']} ({host['parent_name']}) est une "
                    f"{_zone_kind(host['role'])} proche du domicile, sans siège de cette organisation. "
                    f"Y installer une antenne ramènerait le trajet à {best['annex_km']} km "
                    f"(gain {best['gain_km']} km)."
                ),
            }
        )
    ideas.sort(key=lambda item: item["headcount"] * item["gain_km"], reverse=True)
    return ideas[:4]


def _question(city: dict, origin_names: list[str], dest_names: list[str]) -> str:
    title = f"{city['name']} ({city['aka']})"
    if origin_names and dest_names:
        return f"{title} — {_join(origin_names)} vers {_join(dest_names)}"
    if origin_names:
        return f"{title} — où vont les habitants {_de_list(origin_names)} ?"
    if dest_names:
        return f"{title} — qui se rend à {_join(dest_names)} ?"
    return f"{title} — déplacements réguliers de toute la ville"


def _scope_sentence(origin_names: list[str], dest_names: list[str]) -> str:
    if origin_names and dest_names:
        return (
            f"Origines : {_join(origin_names)}. "
            f"Destination retenue : {_join(dest_names)}."
        )
    if origin_names:
        return (
            f"Origines : {_join(origin_names)}. "
            "Le graphe montre où ces habitants vont."
        )
    if dest_names:
        return (
            f"Destinations : {_join(dest_names)}. "
            "Le graphe montre qui s'y rend."
        )
    return (
        "Toute la ville. Cliquez un quartier ou un arrondissement : "
        "en mode origine, on voit où vont les habitants ; "
        "en mode destination, on voit le trafic qui arrive."
    )


def build_lens(city_label: str, origins: str = "", destinations: str = "", purpose: str = "") -> dict:
    city = resolve_city(city_label)
    city_id = city["id"]
    origin_ids = _expand(city_id, origins)
    dest_ids = _expand(city_id, destinations)
    origin_set = set(origin_ids)
    dest_set = set(dest_ids)

    rows = _edges(city_id)
    work_rows = [row for row in rows if row["purpose"] == "travail"]
    if purpose and purpose not in {"tous", "all"}:
        rows = [row for row in rows if row["purpose"] == purpose]
    quartiers = [place for place in places_of(city_id) if place["level"] == "quartier"]
    stats = _quartier_stats(work_rows, quartiers)

    filtered = [
        row
        for row in rows
        if (not origin_set or row["origin_id"] in origin_set)
        and (not dest_set or row["destination_id"] in dest_set)
    ]
    filtered.sort(key=lambda row: row["headcount"], reverse=True)
    flows = [_public_flow(row) for row in filtered[:40]]

    if origin_set:
        measure = origin_set
    elif dest_set:
        measure = dest_set
    else:
        measure = None

    if measure is None:
        residents = sum(row["headcount"] for row in work_rows)
        jobs = residents
        eh_index = _weighted_eh(stats)
        outside = sum(
            row["headcount"] for row in work_rows if row["origin_id"] != row["destination_id"]
        )
        outbound_share = round(outside / residents, 2) if residents else 0
        scope_name = city["name"]
    else:
        residents = sum(row["headcount"] for row in work_rows if row["origin_id"] in measure)
        jobs = sum(row["headcount"] for row in work_rows if row["destination_id"] in measure)
        eh_index = _eh(residents, jobs)
        outside = sum(
            row["headcount"]
            for row in work_rows
            if row["origin_id"] in measure and row["destination_id"] not in measure
        )
        outbound_share = round(outside / residents, 2) if residents else 0
        scope_name = _join([PLACES[item]["name"] for item in (origin_ids or dest_ids)])

    travail = [row for row in filtered if row["purpose"] == "travail"]
    others = [row for row in filtered if row["purpose"] != "travail"]
    worker_count = sum(row["headcount"] for row in travail)
    other_count = sum(row["headcount"] for row in others)
    if worker_count:
        mean_km = round(
            sum(row["km"] * row["headcount"] for row in travail) / worker_count,
            1,
        )
    else:
        mean_km = None
    distance_for_pressure = mean_km if mean_km is not None else 0
    pressure = int(round(outbound_share * min(distance_for_pressure, 25) / 25 * 100))

    if measure is None:
        shown = "—" if eh_index is None else f"{eh_index:.2f}"
        eh_sentence = (
            f"Sur l'ensemble d'{city['name']} ({city['aka']}), "
            f"l'indice moyen des quartiers est {shown}. "
            f"{residents} habitants simulés travaillent dans la ville, "
            f"mais {int(round(outbound_share * 100))} % quittent leur quartier pour le faire. "
            "Le déséquilibre, et donc le trafic, se lit quartier par quartier."
        )
    elif eh_index is None:
        eh_sentence = f"{scope_name} : pas d'effectif simulé dans ce cadre."
    else:
        if eh_index >= 0.75:
            tone = "plutôt équilibré"
        elif eh_index < 0.45:
            tone = "déséquilibré"
        else:
            tone = "intermédiaire"
        eh_sentence = (
            f"À {scope_name}, l'indice emploi-habitat vaut {eh_index:.2f} ({tone}). "
            f"{residents} habitants simulés pour {jobs} emplois sur place. "
            f"{int(round(outbound_share * 100))} % de ces habitants travaillent hors du cadre : "
            "c'est cette navette qui relie l'indice au trafic, pas un score isolé."
        )

    origin_names = [PLACES[item]["name"] for item in origin_ids]
    dest_names = [PLACES[item]["name"] for item in dest_ids]

    arrivals: dict[str, dict] = {}
    for flow in flows:
        bucket = arrivals.setdefault(
            flow["destination_id"],
            {
                "id": flow["destination_id"],
                "name": flow["destination_name"],
                "parent_name": flow["destination_parent_name"],
                "role_label": flow["destination_role_label"],
                "inside": flow["inside"],
                "people": 0,
                "purposes": [],
            },
        )
        bucket["people"] += flow["headcount"]
        if flow["purpose_label"] not in bucket["purposes"]:
            bucket["purposes"].append(flow["purpose_label"])
    arrival_list = sorted(arrivals.values(), key=lambda item: item["people"], reverse=True)

    purposes: dict[str, int] = defaultdict(int)
    for flow in flows:
        purposes[flow["purpose_label"]] += flow["headcount"]
    purpose_bars = [
        {"label": label, "people": count}
        for label, count in sorted(purposes.items(), key=lambda item: item[1], reverse=True)
    ]

    communes = []
    for place in places_of(city_id):
        if place["level"] != "commune":
            continue
        children = [item for item in quartiers if item["parent_id"] == place["id"]]
        radius = 700.0
        for child in children:
            meters = _km(place["lon"], place["lat"], child["lon"], child["lat"]) * 1000 / ROAD_FACTOR
            radius = max(radius, meters * 1.35)
        communes.append(
            {
                "id": place["id"],
                "name": place["name"],
                "lon": place["lon"],
                "lat": place["lat"],
                "quartier_ids": [child["id"] for child in children],
                "geometry": _circle(place["lon"], place["lat"], radius),
            }
        )

    return {
        "city": {
            "id": city_id,
            "name": city["name"],
            "aka": city["aka"],
            "population": city["population"],
        },
        "question": _question(city, origin_names, dest_names),
        "scope_sentence": _scope_sentence(origin_names, dest_names),
        "selection": {"origins": origin_ids, "destinations": dest_ids},
        "indices": {
            "scope_name": scope_name,
            "residents": residents,
            "jobs": jobs,
            "eh_index": eh_index,
            "eh_sentence": eh_sentence,
            "outbound_share": outbound_share,
            "mean_km": mean_km,
            "regular_workers": worker_count,
            "regular_other": other_count,
            "pressure": pressure,
        },
        "flows": flows,
        "purposes": purpose_bars,
        "arrivals": arrival_list[:8],
        "relocations": _relocations(work_rows, city_id, origin_set),
        "quartiers": stats,
        "communes": communes,
        "synthetic": True,
        "note": (
            "Effectifs simulés par organisation, en groupes de 20 personnes et plus. "
            "Aucune enquête ménage n'a encore été collectée. "
            "Hors travail, seuls les trajets qui reviennent chaque semaine sont comptés."
        ),
    }
