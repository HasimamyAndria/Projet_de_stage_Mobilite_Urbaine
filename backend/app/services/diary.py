"""
Déplacements individuels et indices en couples de paramètres.

Les volumes du jour, de la semaine, du mois et de l'année partent tous
de la semaine type. Le mois la répète sur 30 jours. L'année la répète
12 mois, avec une baisse illustrée en juillet-août (hypothèse de démo,
pas une série observée).

Distance : orthodromie × 1,35 (même proxy de route que l'aide à la décision).
Le temps des trajets simulés vient des heures déclarées. Le temps d'une
saisie manuelle est estimé selon le mode, faute d'heure d'arrivée.
"""
from __future__ import annotations

import math

from app.data.persons import PERSONS, person_by_id, persons_of
from app.data.territory import (
    CITIES,
    MIN_CITY_POPULATION,
    PLACES,
    ROLES,
    city_by_id,
)

ROAD_FACTOR = 1.35

PURPOSES = {
    "travail": ("Travail", "#0284c7", "#0369a1"),
    "supermarche": ("Supermarché", "#fb923c", "#c2410c"),
    "marche": ("Marché", "#facc15", "#a16207"),
    "ecole": ("École", "#a78bfa", "#6d28d9"),
    "sante": ("Santé", "#fb7185", "#be123c"),
    "loisirs": ("Loisirs", "#2dd4bf", "#0f766e"),
    "culte": ("Culte", "#cbd5e1", "#475569"),
    "visite": ("Visite", "#f472b6", "#9d174d"),
    "domicile": ("Retour domicile", "#94a3b8", "#334155"),
    "autre": ("Autre", "#e7e5e4", "#57534e"),
}

MODES = {
    "marche": ("Marche", "#94a3b8"),
    "velo": ("Vélo", "#2dd4bf"),
    "bus": ("Bus", "#818cf8"),
    "voiture": ("Voiture", "#fb923c"),
    "taxi": ("Taxi", "#f87171"),
}

SPEED_KMH = {
    "marche": 4.5,
    "velo": 15.0,
    "bus": 16.0,
    "voiture": 22.0,
    "taxi": 20.0,
}

WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
# Baisse illustrée pendant les grandes vacances. Hypothèse, pas une mesure.
MONTH_FACTORS = [0.96, 0.97, 1.0, 1.02, 1.04, 0.99, 0.90, 0.88, 1.01, 1.03, 1.04, 0.98]

PERIODS = ("day", "week", "month", "year")
SHOP = {"supermarche", "marche"}
MOTOR = {"voiture", "taxi"}

PERIOD_NOTES = {
    "day": "Journée type de la personne simulée. Le temps passé sur place (bureau, courses) n'est pas un déplacement.",
    "week": "Semaine type. Le samedi et le dimanche n'ont pas le même programme que les jours ouvrés.",
    "month": "Mois = cette semaine type répétée sur 30 jours, en partant d'un lundi. Ce n'est pas un calendrier observé.",
    "year": "Année = 12 mois bâtis sur la semaine type, avec une baisse illustrée en juillet et août. À remplacer par l'enquête.",
}

# Saisies de la session HTTP. Perdues au redémarrage du processus.
# Elles ne sont pas des enquêtes, et le seed ne les écrit pas.
_EXTRAS: list[dict] = []
_SEQ = 1


def _hour_label(value: float) -> str:
    value = value % 24
    hour = int(value)
    minute = int(round((value - hour) * 60))
    if minute == 60:
        hour = (hour + 1) % 24
        minute = 0
    return f"{hour:02d}:{minute:02d}"


def _route_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    crow = 2 * radius * math.asin(math.sqrt(arc))
    return round(crow * ROAD_FACTOR, 2)


def _public_person(person: dict) -> dict:
    return {
        "id": person["id"],
        "name": person["name"],
        "age": person["age"],
        "job": person["job"],
        "city_id": person["city_id"],
        "home": PLACES[person["home_id"]]["name"],
        "work": PLACES[person["work_id"]]["name"],
        "organization_id": person.get("organization_id"),
        "blurb": person["blurb"],
    }


def _public_place(place: dict) -> dict:
    return {
        "id": place["id"],
        "name": place["name"],
        "level": place["level"],
        "role": place["role"],
        "role_label": ROLES.get(place["role"], place["role"]),
        "parent_id": place["parent_id"],
        "parent_name": place["parent_name"],
        "city_id": place["city_id"],
        "lon": place["lon"],
        "lat": place["lat"],
    }


def catalog() -> dict:
    return {
        "min_population": MIN_CITY_POPULATION,
        "population_rule": (
            "Toute ville d'au moins 200 000 habitants peut utiliser l'application. "
            "On l'ajoute en décrivant ses sous-villes, puis ses quartiers."
        ),
        "periods": [
            {"id": "day", "label": "Jour"},
            {"id": "week", "label": "Semaine"},
            {"id": "month", "label": "Mois"},
            {"id": "year", "label": "Année"},
        ],
        "weekdays": [{"id": index, "label": label} for index, label in enumerate(WEEKDAYS)],
        "purposes": [
            {"id": key, "label": label, "color": color, "map_color": map_color}
            for key, (label, color, map_color) in PURPOSES.items()
        ],
        "modes": [
            {"id": key, "label": label, "color": color}
            for key, (label, color) in MODES.items()
        ],
        "cities": CITIES,
        "places": [_public_place(place) for place in PLACES.values()],
        "persons": [_public_person(person) for person in PERSONS],
        "zoom": {"city_below": 11, "quartier_from": 13.5},
        "synthetic": True,
        "note": (
            "Enquête de mobilité pas encore réalisée. "
            f"{len(PERSONS)} individus inventés servent de semaine type. "
            "Le jeu diary-week est marqué SIMULATED. Ce n'est pas une observation."
        ),
    }


def _trip_from_stops(person: dict, weekday: int, index: int, origin: dict, dest: dict) -> dict:
    origin_place = PLACES[origin["place_id"]]
    dest_place = PLACES[dest["place_id"]]
    minutes = round((dest["arrive"] - origin["leave"]) * 60)
    return _make_trip(
        trip_id=f"sim-{person['id']}-{weekday}-{index}",
        person_id=person["id"],
        weekday=weekday,
        origin=origin_place,
        destination=dest_place,
        purpose=dest["purpose"],
        detail=dest["detail"],
        mode=dest["mode"],
        depart_hour=origin["leave"],
        minutes=max(minutes, 1),
        source="simulated",
    )


def _make_trip(
    *,
    trip_id: str,
    person_id: str,
    weekday: int,
    origin: dict,
    destination: dict,
    purpose: str,
    detail: str,
    mode: str,
    depart_hour: float,
    minutes: int,
    source: str,
) -> dict:
    purpose_label, purpose_color, map_color = PURPOSES[purpose]
    mode_label, mode_color = MODES[mode]
    km = _route_km(origin["lon"], origin["lat"], destination["lon"], destination["lat"])
    return {
        "id": trip_id,
        "person_id": person_id,
        "weekday": weekday,
        "weekday_label": WEEKDAYS[weekday],
        "origin_id": origin["id"],
        "origin_name": origin["name"],
        "destination_id": destination["id"],
        "destination_name": destination["name"],
        "purpose": purpose,
        "purpose_label": purpose_label,
        "purpose_color": purpose_color,
        "map_color": map_color,
        "detail": detail,
        "mode": mode,
        "mode_label": mode_label,
        "mode_color": mode_color,
        "depart_hour": depart_hour,
        "depart_label": _hour_label(depart_hour),
        "minutes": minutes,
        "km": km,
        "source": source,
        "origin": [origin["lon"], origin["lat"]],
        "destination": [destination["lon"], destination["lat"]],
    }


def read_backend() -> str:
    """`postgres` (défaut) ou `memory` pour revenir au calcul Python."""
    import os

    choice = os.getenv("DIARY_READ", "postgres").strip().lower()
    if choice not in {"postgres", "memory"}:
        raise ValueError("DIARY_READ doit valoir postgres ou memory.")
    return choice


def _scripted_day_trips(person: dict, weekday: int) -> list[dict]:
    """Semaine type seule, sans les saisies manuelles."""
    stops = person["days"][weekday]
    return [
        _trip_from_stops(person, weekday, index, stops[index], stops[index + 1])
        for index in range(len(stops) - 1)
    ]


def _trip_from_stored(row: dict) -> dict:
    from app.services.diary_contract import CODE_TO_DIARY

    purpose = CODE_TO_DIARY.get(row["purpose_code"])
    if purpose is None:
        raise ValueError(f"Motif canonique sans traduction d'écran : {row['purpose_code']}")
    if row["mode_code"] not in MODES:
        raise ValueError(f"Mode hors écran : {row['mode_code']}")
    origin = {
        "id": row["origin_id"],
        "name": row["origin_name"],
        "lon": row["origin_lon"],
        "lat": row["origin_lat"],
    }
    destination = {
        "id": row["destination_id"],
        "name": row["destination_name"],
        "lon": row["destination_lon"],
        "lat": row["destination_lat"],
    }
    trip = _make_trip(
        trip_id=row["trip_id"],
        person_id=row.get("person_id", ""),
        weekday=row["weekday"],
        origin=origin,
        destination=destination,
        purpose=purpose,
        detail=row["detail"],
        mode=row["mode_code"],
        depart_hour=row["depart_hour"],
        minutes=row["minutes"],
        source="simulated",
    )
    trip["km"] = row["km"]
    trip["minutes"] = row["minutes"]
    return trip


def _stored_day_trips(person: dict, weekday: int) -> list[dict]:
    from app.repositories.diary_store import week_by_person

    week = week_by_person()
    if person["id"] not in week:
        # Le catalogue Python a déjà la semaine type. On l'affiche tant que
        # le jeu diary-week n'a pas été rechargé avec cette personne.
        if person.get("days"):
            return _scripted_day_trips(person, weekday)
        raise ValueError(
            "Personne absente du jeu diary-week. "
            "Relancer scripts/seed_diary_trips.py ou définir DIARY_READ=memory."
        )
    rows = week[person["id"]].get(weekday, [])
    trips = []
    for row in rows:
        stored = dict(row)
        stored["person_id"] = person["id"]
        trips.append(_trip_from_stored(stored))
    return trips


def _manual_day_trips(person: dict, weekday: int) -> list[dict]:
    return [
        trip
        for trip in _EXTRAS
        if trip["person_id"] == person["id"] and trip["weekday"] == weekday
    ]


def _day_trips(person: dict, weekday: int) -> list[dict]:
    if read_backend() == "memory":
        base = _scripted_day_trips(person, weekday)
    else:
        base = _stored_day_trips(person, weekday)
    return base + _manual_day_trips(person, weekday)


def _listed_days(period: str, weekday: int) -> list[int]:
    """Jours dessinés sur la carte et dans le tableau (sans répétition)."""
    if period == "day":
        return [weekday]
    return list(range(7))


def _weighted_days(period: str, weekday: int) -> list[tuple[int, float]]:
    """Chaque jour de la semaine type, avec le poids du calendrier choisi."""
    if period == "day":
        return [(weekday, 1.0)]
    if period == "week":
        return [(day, 1.0) for day in range(7)]
    if period == "month":
        sequence = [day for _ in range(4) for day in range(7)] + [0, 1]
        return [(day, 1.0) for day in sequence]
    pairs: list[tuple[int, float]] = []
    for factor in MONTH_FACTORS:
        for _week in range(4):
            for day in range(7):
                pairs.append((day, factor))
    return pairs


def _empty_agg() -> dict:
    return {
        "trips": 0.0,
        "km": 0.0,
        "minutes": 0.0,
        "by_purpose": {},
        "by_mode": {},
        "non_work": 0.0,
        "non_work_detailed": 0.0,
        "work_trips": 0.0,
        "work_km": 0.0,
        "work_minutes": 0.0,
        "shop_trips": 0.0,
        "shop_km": 0.0,
        "shop_motor": 0.0,
        "bus_trips": 0.0,
        "workplaces": set(),
        "pairs": {},
    }


def _add_trip(agg: dict, trip: dict, weight: float) -> None:
    agg["trips"] += weight
    agg["km"] += trip["km"] * weight
    agg["minutes"] += trip["minutes"] * weight

    purpose = agg["by_purpose"].setdefault(trip["purpose"], {"count": 0.0, "km": 0.0})
    purpose["count"] += weight
    purpose["km"] += trip["km"] * weight

    mode = agg["by_mode"].setdefault(trip["mode"], {"count": 0.0, "km": 0.0})
    mode["count"] += weight
    mode["km"] += trip["km"] * weight

    if trip["purpose"] not in {"travail", "domicile"}:
        agg["non_work"] += weight
        if len(trip["detail"].strip()) >= 8:
            agg["non_work_detailed"] += weight
    if trip["purpose"] == "travail":
        agg["work_trips"] += weight
        agg["work_km"] += trip["km"] * weight
        agg["work_minutes"] += trip["minutes"] * weight
        agg["workplaces"].add(trip["destination_id"])
    if trip["purpose"] in SHOP:
        agg["shop_trips"] += weight
        agg["shop_km"] += trip["km"] * weight
        if trip["mode"] in MOTOR:
            agg["shop_motor"] += weight
    if trip["mode"] == "bus":
        agg["bus_trips"] += weight

    key = (trip["origin_name"], trip["destination_name"], trip["purpose_label"])
    pair = agg["pairs"].setdefault(key, {"count": 0.0, "km": 0.0})
    pair["count"] += weight
    pair["km"] += trip["km"] * weight


def _accumulate(people: list[dict], period: str, weekday: int) -> dict:
    agg = _empty_agg()
    for person in people:
        for day, weight in _weighted_days(period, weekday):
            for trip in _day_trips(person, day):
                _add_trip(agg, trip, weight)
    return agg


def _count(value: float) -> int | float:
    rounded = round(value)
    if abs(value - rounded) < 0.05:
        return int(rounded)
    return round(value, 1)


def _share(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round(100 * part / whole, 1)


def _duration(minutes: float) -> dict:
    if minutes >= 120:
        return {"value": round(minutes / 60, 1), "unit": "h"}
    return {"value": int(round(minutes)), "unit": "min"}


def _stats(agg: dict) -> dict:
    ranked = sorted(agg["pairs"].items(), key=lambda item: item[1]["km"], reverse=True)[:3]
    return {
        "trip_count": _count(agg["trips"]),
        "km": round(agg["km"], 1),
        "duration": _duration(agg["minutes"]),
        "non_work_share": _share(agg["non_work"], agg["trips"]),
        "top_pairs": [
            {
                "label": f"{origin} → {dest}",
                "purpose": purpose,
                "count": _count(bucket["count"]),
                "km": round(bucket["km"], 1),
            }
            for (origin, dest, purpose), bucket in ranked
        ],
    }


def _bars(bucket: dict, catalog_map: dict, whole: float) -> list[dict]:
    rows = []
    for key, values in bucket.items():
        if key not in catalog_map or values["count"] <= 0:
            continue
        label = catalog_map[key][0]
        color = catalog_map[key][1]
        rows.append(
            {
                "id": key,
                "label": label,
                "color": color,
                "count": _count(values["count"]),
                "share": _share(values["count"], whole),
            }
        )
    rows.sort(key=lambda row: row["share"], reverse=True)
    return rows


def _volume(people: list[dict], period: str, weekday: int) -> dict:
    if period == "day":
        slots = [
            (5, 9, "5h–9h"),
            (9, 12, "9h–12h"),
            (12, 14, "12h–14h"),
            (14, 17, "14h–17h"),
            (17, 21, "17h–21h"),
            (21, 24, "21h–24h"),
        ]
        points = []
        trips = [trip for person in people for trip in _day_trips(person, weekday)]
        for start, end, label in slots:
            count = sum(1 for trip in trips if start <= trip["depart_hour"] < end)
            points.append({"label": label, "value": count})
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    if period == "week":
        points = []
        for day in range(7):
            count = sum(len(_day_trips(person, day)) for person in people)
            points.append({"label": WEEKDAYS[day][:3], "value": count})
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    if period == "month":
        sequence = [day for _ in range(4) for day in range(7)] + [0, 1]
        points = []
        for index, day in enumerate(sequence, start=1):
            count = sum(len(_day_trips(person, day)) for person in people)
            points.append({"label": str(index), "value": count})
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    points = []
    for name, factor in zip(MONTHS, MONTH_FACTORS):
        total = 0.0
        for day in range(7):
            total += sum(len(_day_trips(person, day)) for person in people) * 4 * factor
        points.append({"label": name, "value": _count(total)})
    return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}


def _indicator(name: str, value: float, unit: str, hint: str) -> dict:
    return {"name": name, "value": round(value, 1), "unit": unit, "hint": hint}


def _param(name: str, value: float | int, unit: str) -> dict:
    return {"name": name, "value": value if isinstance(value, int) else round(value, 1), "unit": unit}


def _couples(agg: dict, person_count: int) -> list[dict]:
    if person_count == 0 or agg["trips"] <= 0:
        return []

    mean_work_km = agg["work_km"] / agg["work_trips"] if agg["work_trips"] else 0
    mean_work_min = agg["work_minutes"] / agg["work_trips"] if agg["work_trips"] else 0
    mean_shop_km = agg["shop_km"] / agg["shop_trips"] if agg["shop_trips"] else 0
    work_km_share = _share(agg["work_km"], agg["km"])
    shop_motor_share = _share(agg["shop_motor"], agg["shop_trips"])
    bus_share = _share(agg["bus_trips"], agg["trips"])
    detail_share = _share(agg["non_work_detailed"], agg["non_work"]) if agg["non_work"] else 100.0
    job_proximity = round(100 * (1 - min(mean_work_km, 20) / 20), 1)
    shop_proximity = round(100 * (1 - min(mean_shop_km, 8) / 8), 1)

    return [
        {
            "id": "habitat_emploi",
            "title": "Habitat ↔ Emploi",
            "left": _param("Personnes", person_count, "individus"),
            "right": _param("Lieux d'emploi", len(agg["workplaces"]), "lieux"),
            "indicator": _indicator(
                "Part des km liée au travail",
                work_km_share,
                "%",
                "100 % = toute la distance parcourue va vers le lieu de travail.",
            ),
            "stats": [
                _param("Km vers le travail", round(agg["work_km"], 1), "km"),
                _param("Km pour les autres motifs", round(agg["km"] - agg["work_km"], 1), "km"),
            ],
            "reading": "Ce couple compare les habitants de l'échantillon et les lieux d'emploi qu'ils rejoignent.",
        },
        {
            "id": "emploi_distance",
            "title": "Emploi ↔ Distance",
            "left": _param("Distance moyenne", mean_work_km, "km"),
            "right": _param("Temps moyen", mean_work_min, "min"),
            "indicator": _indicator(
                "Proximité de l'emploi",
                job_proximity,
                "/100",
                "100 = trajet travail très court. 0 = 20 km ou plus.",
            ),
            "stats": [
                _param("Trajets travail", _count(agg["work_trips"]), "trajets"),
                _param("Temps de trajet travail", round(agg["work_minutes"] / 60, 1), "h"),
            ],
            "reading": "Plus l'indice est bas, plus le domicile et l'emploi sont éloignés.",
        },
        {
            "id": "courses_commerce",
            "title": "Courses ↔ Commerce",
            "left": _param("Trajets courses", _count(agg["shop_trips"]), "trajets"),
            "right": _param("Distance moyenne", mean_shop_km, "km"),
            "indicator": _indicator(
                "Proximité du commerce",
                shop_proximity,
                "/100",
                "Courses = supermarché + marché. 100 = très proche. 0 = 8 km ou plus.",
            ),
            "stats": [
                _param("Courses motorisées", shop_motor_share, "%"),
                _param("Km de courses", round(agg["shop_km"], 1), "km"),
            ],
            "reading": "Ce couple dit si le supermarché et le marché sont proches du domicile.",
        },
        {
            "id": "habitants_bus",
            "title": "Habitants ↔ Bus",
            "left": _param("Personnes", person_count, "individus"),
            "right": _param("Trajets en bus", _count(agg["bus_trips"]), "trajets"),
            "indicator": _indicator(
                "Part modale du bus",
                bus_share,
                "%",
                "Part des déplacements déclarés qui se font en bus.",
            ),
            "stats": [
                _param("Autres modes", _count(agg["trips"] - agg["bus_trips"]), "trajets"),
                _param("Km totaux", round(agg["km"], 1), "km"),
            ],
            "reading": "Ce couple relie la taille de l'échantillon et l'usage réel du bus sur leurs trajets.",
        },
        {
            "id": "hors_travail",
            "title": "Hors travail ↔ Motif saisi",
            "left": _param("Trajets hors travail", _count(agg["non_work"]), "trajets"),
            "right": _param("Avec un motif écrit", _count(agg["non_work_detailed"]), "trajets"),
            "indicator": _indicator(
                "Motifs renseignés",
                detail_share,
                "%",
                "Hors travail, la personne doit écrire ce qu'elle va faire (courses, visite, santé…).",
            ),
            "stats": [
                _param("Part des trajets hors travail", _share(agg["non_work"], agg["trips"]), "%"),
                _param("Retours domicile", _count(agg["by_purpose"].get("domicile", {}).get("count", 0)), "trajets"),
            ],
            "reading": "Le travail est un motif connu. Tout autre déplacement doit être nommé dans la saisie.",
        },
    ]


def _decisions(agg: dict) -> list[str]:
    if agg["trips"] <= 0:
        return [
            "Aucun individu simulé sur cette ville. Le découpage ville, sous-ville et quartier est prêt pour une enquête."
        ]
    hints: list[str] = []
    if agg["work_trips"]:
        mean_km = agg["work_km"] / agg["work_trips"]
        if mean_km >= 8:
            hints.append(
                f"Domicile–travail moyen de {mean_km:.1f} km : rapprocher l'emploi de l'habitat (logement près des pôles, ou annexe)."
            )
    if agg["shop_trips"]:
        mean_shop = agg["shop_km"] / agg["shop_trips"]
        motor = agg["shop_motor"] / agg["shop_trips"]
        if mean_shop >= 3 and motor >= 0.35:
            hints.append(
                "Les courses sont souvent motorisées et éloignées : un commerce de proximité réduirait ces déplacements."
            )
    bus_share = agg["bus_trips"] / agg["trips"]
    mean_km = agg["km"] / agg["trips"]
    if bus_share < 0.25 and mean_km > 3:
        hints.append(
            "Peu de trajets en bus dans cet échantillon : vérifier la desserte des axes domicile–travail et domicile–courses."
        )
    if not hints:
        hints.append(
            "Les trajets simulés restent relativement courts : maintenir la mixité emploi-habitat et les commerces de quartier."
        )
    return hints[:3]


def _check_period(period: str, weekday: int) -> None:
    if period not in PERIODS:
        raise ValueError("Période inconnue. Choisir jour, semaine, mois ou année.")
    if weekday < 0 or weekday > 6:
        raise ValueError("Jour inconnu.")


def person_diary(person_id: str, period: str, weekday: int) -> dict:
    _check_period(period, weekday)
    person = person_by_id(person_id)
    if person is None:
        raise ValueError("Personne inconnue.")

    people = [person]
    agg = _accumulate(people, period, weekday)
    listed = []
    for day in _listed_days(period, weekday):
        listed.extend(_day_trips(person, day))
    listed.sort(key=lambda trip: (trip["weekday"], trip["depart_hour"], trip["id"]))

    return {
        "synthetic": True,
        "period": period,
        "weekday": weekday,
        "note": PERIOD_NOTES[period],
        "listing_note": (
            "Liste de la journée."
            if period == "day"
            else "Liste de la semaine type. Les totaux du mois et de l'année multiplient ce rythme."
        ),
        "person": _public_person(person),
        "stats": _stats(agg),
        "volume": _volume(people, period, weekday),
        "purposes": {
            "question": "Pourquoi se déplace-t-on ?",
            "items": _bars(agg["by_purpose"], PURPOSES, agg["trips"]),
        },
        "modes": {
            "question": "Quel mode est utilisé ?",
            "items": _bars(agg["by_mode"], MODES, agg["trips"]),
        },
        "trips": listed,
        "geojson": _geojson(listed),
    }


def city_overview(city_id: str, period: str, weekday: int) -> dict:
    _check_period(period, weekday)
    city = city_by_id(city_id)
    if city is None:
        raise ValueError("Ville inconnue, ou sous le seuil de 200 000 habitants.")
    people = persons_of(city_id)
    agg = _accumulate(people, period, weekday)
    return {
        "synthetic": True,
        "city": city,
        "period": period,
        "person_count": len(people),
        "stats": _stats(agg),
        "couples": _couples(agg, len(people)),
        "decisions": _decisions(agg),
        "note": (
            f"Échantillon simulé de {len(people)} individu(s) à {city['name']}. "
            "Pas une enquête représentative. " + PERIOD_NOTES[period]
        ),
    }


def add_manual_trip(
    *,
    person_id: str,
    weekday: int,
    origin_id: str,
    destination_id: str,
    purpose: str,
    detail: str,
    mode: str,
    depart_hour: float,
) -> dict:
    global _SEQ
    if weekday < 0 or weekday > 6:
        raise ValueError("Jour inconnu.")
    person = person_by_id(person_id)
    if person is None:
        raise ValueError("Personne inconnue.")
    origin = PLACES.get(origin_id)
    destination = PLACES.get(destination_id)
    if origin is None or destination is None:
        raise ValueError("Lieu inconnu.")
    if origin["level"] != "quartier" or destination["level"] != "quartier":
        raise ValueError("Choisissez un quartier de départ et un quartier d'arrivée.")
    if origin["city_id"] != person["city_id"] or destination["city_id"] != person["city_id"]:
        raise ValueError("Les deux quartiers doivent être dans la ville de la personne.")
    if origin_id == destination_id:
        raise ValueError("Le départ et l'arrivée sont le même lieu.")
    if purpose not in PURPOSES:
        raise ValueError("Motif inconnu.")
    if mode not in MODES:
        raise ValueError("Mode inconnu.")
    if not 0 <= depart_hour < 24:
        raise ValueError("Heure de départ invalide.")

    text = (detail or "").strip()
    if purpose != "travail" and len(text) < 8:
        raise ValueError(
            "Hors travail, décrivez le motif (au moins 8 caractères). Ex. : courses au supermarché Jumbo."
        )
    if purpose == "travail" and not text:
        text = "Trajet vers le lieu de travail"

    km = _route_km(origin["lon"], origin["lat"], destination["lon"], destination["lat"])
    minutes = max(5, round(km / SPEED_KMH[mode] * 60))
    trip = _make_trip(
        trip_id=f"saisie-{_SEQ}",
        person_id=person_id,
        weekday=weekday,
        origin=origin,
        destination=destination,
        purpose=purpose,
        detail=text,
        mode=mode,
        depart_hour=depart_hour,
        minutes=minutes,
        source="saisie",
    )
    _SEQ += 1
    _EXTRAS.append(trip)
    return trip


def delete_manual_trip(trip_id: str) -> None:
    for index, trip in enumerate(_EXTRAS):
        if trip["id"] == trip_id:
            del _EXTRAS[index]
            return
    raise ValueError("Cette saisie est introuvable.")


def _offset(origin: list[float], dest: list[float], index: int, total: int) -> tuple[list[float], list[float]]:
    if total <= 1:
        return origin, dest
    dx = dest[0] - origin[0]
    dy = dest[1] - origin[1]
    length = math.hypot(dx, dy) or 1.0
    shift = (index - (total - 1) / 2) * 0.0016
    ox = -dy / length * shift
    oy = dx / length * shift
    return [origin[0] + ox, origin[1] + oy], [dest[0] + ox, dest[1] + oy]


def _geojson(trips: list[dict]) -> dict:
    groups: dict[tuple[str, str], list[dict]] = {}
    for trip in trips:
        groups.setdefault((trip["origin_id"], trip["destination_id"]), []).append(trip)

    features = []
    for group in groups.values():
        for index, trip in enumerate(group):
            start, end = _offset(trip["origin"], trip["destination"], index, len(group))
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [start, end]},
                    "properties": {
                        "id": trip["id"],
                        "label": f"{trip['origin_name']} → {trip['destination_name']}",
                        "purpose": trip["purpose_label"],
                        "detail": trip["detail"],
                        "mode": trip["mode_label"],
                        "when": f"{trip['weekday_label']} {trip['depart_label']}",
                        "km": trip["km"],
                        "color": trip["map_color"],
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}


def _check_scripted_week() -> None:
    """Contrôle la semaine type au chargement, sans ouvrir PostgreSQL."""
    import os

    previous = os.environ.get("DIARY_READ")
    os.environ["DIARY_READ"] = "memory"
    try:
        person_diary("hery", "week", 0)
        city_overview("tana", "year", 0)
    finally:
        if previous is None:
            os.environ.pop("DIARY_READ", None)
        else:
            os.environ["DIARY_READ"] = previous


_check_scripted_week()
