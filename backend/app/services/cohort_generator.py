"""Brouillon d'une cohorte fictive. Aucune écriture en base.

Le résultat est un objet en mémoire (`persisted` reste False).
L'insertion dans `datasets`, `persons` et `trips` est réservée au script
du lot C. Ce module n'ouvre pas PostgreSQL et ne modifie pas `random`.

Distances : orthodromie terrestre × 1,35, le même proxy que le journal
des huit personnes. Ce n'est pas un itinéraire pgRouting.
Durée : `max(1, round(km / vitesse_du_mode × 60))`.
Vitesses : marche 4,5, vélo 15, bus 16, voiture 22, taxi 20 km/h.

Les lieux viennent uniquement de `territory.py`. Si une ville n'a pas
le rôle idéal, le profil est ancré sur le rôle suivant déjà présent.
Aucun lieu n'est inventé.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, time, timedelta

from app.data.persons import PERSONS
from app.data.territory import CITIES, PLACES

DATASET_ID = "sim-cohort"
SOURCE = "SIMULATED"
ALLOWED_PERSON_COUNTS = (50, 75, 100)
ROAD_FACTOR = 1.35
DISTANCE_METHOD = "orthodromie_km_x_1_35"
DURATION_METHOD = "max(1, round(distance_km / vitesse_kmh * 60))"
DATASET_LABEL = (
    "Cohorte fictive de personnes inventées. "
    "Jeu SIMULATED, pas une enquête observée. "
    "Distances : orthodromie × 1,35, pas un itinéraire pgRouting."
)

SPEED_KMH = {
    "marche": 4.5,
    "velo": 15.0,
    "bus": 16.0,
    "voiture": 22.0,
    "taxi": 20.0,
}

# Sous-ensemble des codes de la table purposes. Les codes existent.
# `courses`, `autre` et `service_public` ne sont pas utilisés : chaque
# scénario a un motif plus précis.
PURPOSES = frozenset({
    "travail",
    "retour_domicile",
    "courses_supermarche",
    "courses_marche",
    "ecole",
    "sante",
    "loisirs",
    "culte",
    "visite",
    "deplacement_professionnel",
})
MODES = frozenset(SPEED_KMH)

DATASET_COLUMNS = ("id", "source", "label", "seed", "anchor_monday")
PERSON_COLUMNS = (
    "person_id",
    "dataset_id",
    "display_name",
    "city_id",
    "home_place_id",
    "work_place_id",
    "activity",
    "source",
)
TRIP_COLUMNS = (
    "trip_id",
    "dataset_id",
    "person_id",
    "trip_date",
    "depart_time",
    "arrive_time",
    "origin_place_id",
    "destination_place_id",
    "purpose_code",
    "mode_code",
    "distance_km",
    "duration_min",
    "detail",
    "source",
    "validation_status",
    "survey_id",
    "import_batch_id",
)

PROFILE_WEIGHTS = (
    ("salarie", 45),
    ("etudiant", 15),
    ("commercant", 15),
    ("professionnel", 10),
    ("foyer", 15),
)
PROFILE_ACTIVITY = {
    "salarie": "Salarié fictif",
    "etudiant": "Étudiant fictif",
    "commercant": "Commerçant fictif",
    "professionnel": "Professionnel mobile fictif",
    "foyer": "Foyer fictif",
}
# Premier rôle présent dans la ville. L'ordre est la stratégie d'adaptation.
ANCHOR_ROLES = {
    "salarie": ("emploi", "mixte", "equipement"),
    "professionnel": ("emploi", "mixte", "equipement"),
    "etudiant": ("equipement", "mixte", "emploi"),
    "commercant": ("commerce",),
    "foyer": (),
}

FIRST_NAMES = (
    "Aina", "Nirina", "Fetra", "Hasina", "Lova", "Mialy", "Nomena", "Rija",
    "Sitraka", "Tahina", "Zo", "Feno", "Kolo", "Mbola", "Narivony", "Ony",
    "Pela", "Rado", "Solo", "Tsiory",
)
LAST_NAMES = (
    "Andriamanana", "Rabe", "Rakotomanga", "Rasoa", "Randrianarisoa",
    "Raharijaona", "Ratovonirina", "Rakotondrabe", "Ranaivo", "Razafy",
)

EARLIEST_MINUTE = 5 * 60
LATEST_MINUTE = 23 * 60 + 59
_WINDOWS = {
    "commute": (6 * 60 + 15, 8 * 60 + 15),
    "ecole": (6 * 60 + 15, 8 * 60 + 15),
    "errand": (6 * 60 + 15, 8 * 60 + 15),
    "loisirs": (6 * 60 + 15, 8 * 60 + 15),
    "tour": (7 * 60, 9 * 60),
    "shop": (8 * 60, 10 * 60),
    "culte": (8 * 60, 9 * 60 + 30),
    "visite": (8 * 60, 11 * 60),
    "sante": (8 * 60, 11 * 60),
}
_DETAILS = {
    "travail": "Trajet fictif vers le travail",
    "ecole": "Cours fictif",
    "retour_domicile": "Retour au domicile fictif",
    "courses_supermarche": "Courses fictives au supermarché",
    "courses_marche": "Courses fictives au marché",
    "loisirs": "Loisirs fictifs",
    "sante": "Consultation fictive",
    "culte": "Culte fictif",
    "visite": "Visite fictive",
    "deplacement_professionnel": "Déplacement professionnel fictif",
}


@dataclass(frozen=True)
class CohortSpec:
    """Paramètres demandés. Ils ne sont pas tous des colonnes SQL."""

    persons: int
    seed: int
    start: date
    days: int


@dataclass(frozen=True)
class DatasetDraft:
    id: str
    source: str
    label: str
    seed: int
    anchor_monday: date

    def row(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "label": self.label,
            "seed": self.seed,
            "anchor_monday": self.anchor_monday,
        }


@dataclass(frozen=True)
class PersonDraft:
    person_id: str
    dataset_id: str
    display_name: str
    city_id: str
    home_place_id: str
    work_place_id: str | None
    activity: str
    source: str
    profile: str

    def row(self) -> dict:
        """Colonnes de `persons` seulement. `profile` n'est pas une colonne."""
        return {
            "person_id": self.person_id,
            "dataset_id": self.dataset_id,
            "display_name": self.display_name,
            "city_id": self.city_id,
            "home_place_id": self.home_place_id,
            "work_place_id": self.work_place_id,
            "activity": self.activity,
            "source": self.source,
        }


@dataclass(frozen=True)
class TripDraft:
    trip_id: str
    dataset_id: str
    person_id: str
    trip_date: date
    depart_time: time
    arrive_time: time
    origin_place_id: str
    destination_place_id: str
    purpose_code: str
    mode_code: str
    distance_km: float
    duration_min: int
    detail: str
    source: str
    validation_status: str
    survey_id: None = None
    import_batch_id: None = None

    def row(self) -> dict:
        return {
            "trip_id": self.trip_id,
            "dataset_id": self.dataset_id,
            "person_id": self.person_id,
            "trip_date": self.trip_date,
            "depart_time": self.depart_time,
            "arrive_time": self.arrive_time,
            "origin_place_id": self.origin_place_id,
            "destination_place_id": self.destination_place_id,
            "purpose_code": self.purpose_code,
            "mode_code": self.mode_code,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "detail": self.detail,
            "source": self.source,
            "validation_status": self.validation_status,
            "survey_id": self.survey_id,
            "import_batch_id": self.import_batch_id,
        }


@dataclass(frozen=True)
class CohortDraft:
    """Cohorte calculée, non persistée.

    `adaptations` explique les rôles manquants du catalogue.
    `insertion_rows` fournit les dictionnaires du futur INSERT.
    """

    spec: CohortSpec
    persisted: bool
    dataset: DatasetDraft
    persons: tuple[PersonDraft, ...]
    trips: tuple[TripDraft, ...]
    adaptations: tuple[str, ...]
    distance_method: str
    duration_method: str


@dataclass(frozen=True)
class _Plan:
    index: int
    profile: str
    city_id: str
    home_id: str
    work_id: str | None
    display_name: str
    weekday_off: int | None


@dataclass(frozen=True)
class _Intent:
    place_id: str
    purpose: str
    dwell_min: int
    dwell_max: int
    optional: bool


def route_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Kilomètres d'orthodromie multipliés par 1,35.

    Proxy de détour urbain. pgRouting n'est pas appelé.
    """
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    crow = 2 * radius * math.asin(math.sqrt(arc))
    return round(crow * ROAD_FACTOR, 2)


def duration_minutes(distance_km: float, mode_code: str) -> int:
    """Minutes cohérentes avec la distance proxy et la vitesse du mode."""
    speed = SPEED_KMH[mode_code]
    return max(1, round(distance_km / speed * 60))


def modes_for_distance(distance_km: float) -> tuple[str, ...]:
    """Modes autorisés pour une distance proxy, du plus court au plus long."""
    if distance_km < 1.5:
        return ("marche", "velo")
    if distance_km <= 8:
        return ("bus", "velo", "taxi")
    return ("bus", "voiture", "taxi")


def _quartiers(city_id: str) -> list[dict]:
    rows = [
        place
        for place in PLACES.values()
        if place["city_id"] == city_id and place["level"] == "quartier"
    ]
    return sorted(rows, key=lambda place: place["id"])


def _role_counts(city_id: str) -> Counter:
    return Counter(place["role"] for place in _quartiers(city_id))


def anchor_role(city_id: str, profile: str) -> str | None:
    """Rôle du lieu d'ancrage, ou None pour un foyer sans lieu de travail."""
    wanted = ANCHOR_ROLES[profile]
    if not wanted:
        return None
    counts = _role_counts(city_id)
    for role in wanted:
        if counts[role] > 0:
            return role
    city_name = next(city["name"] for city in CITIES if city["id"] == city_id)
    raise ValueError(
        f"{city_name} : aucun quartier pour le profil {profile} "
        f"parmi {', '.join(wanted)}."
    )


def _city_weights() -> tuple[tuple[str, int], ...]:
    weights = []
    for city in CITIES:
        homes = _role_counts(city["id"])["habitat"]
        if homes > 0:
            weights.append((city["id"], homes))
    if not weights:
        raise ValueError("Aucune ville du catalogue n'a de quartier habitat.")
    return tuple(weights)


def catalog_adaptations() -> tuple[str, ...]:
    """Écarts entre le rôle idéal et les quartiers réellement disponibles."""
    notes = []
    for city in CITIES:
        counts = _role_counts(city["id"])
        name = city["name"]
        if counts["habitat"] == 0:
            notes.append(f"{name} : aucun quartier habitat. Aucune personne n'y est affectée.")
            continue
        if counts["emploi"] == 0:
            role = anchor_role(city["id"], "salarie")
            notes.append(
                f"{name} : aucun quartier emploi. "
                f"Les salariés et les professionnels mobiles sont ancrés sur le rôle {role}."
            )
        if counts["equipement"] == 0:
            role = anchor_role(city["id"], "etudiant")
            notes.append(
                f"{name} : aucun quartier equipement. "
                f"Les étudiants sont ancrés sur le rôle {role}. "
                "Les déplacements santé et culte ne sont pas générés dans cette ville."
            )
        if counts["habitat"] + counts["mixte"] < 2:
            notes.append(
                f"{name} : un seul quartier résidentiel. "
                "Le scénario visite est remplacé par des courses."
            )
    return tuple(notes)


def _apportion(total: int, parts: tuple[tuple[str, int], ...]) -> list[str]:
    """Méthode des plus forts restes. L'ordre d'origine départage les ex æquo."""
    weight_sum = sum(weight for _, weight in parts)
    raw = []
    for index, (key, weight) in enumerate(parts):
        quota = total * weight / weight_sum
        floored = math.floor(quota)
        raw.append((key, floored, quota - floored, index))
    remaining = total - sum(item[1] for item in raw)
    ranked = sorted(raw, key=lambda item: (-item[2], item[3]))
    extra = {item[0]: 0 for item in raw}
    for item in ranked[:remaining]:
        extra[item[0]] += 1
    expanded: list[str] = []
    for key, floored, _fraction, _index in raw:
        expanded.extend([key] * (floored + extra[key]))
    if len(expanded) != total:
        raise RuntimeError("Répartition incohérente.")
    return expanded


def planned_profile_counts(persons: int) -> dict[str, int]:
    _check_counts(persons)
    return dict(Counter(_apportion(persons, PROFILE_WEIGHTS)))


def planned_city_counts(persons: int) -> dict[str, int]:
    _check_counts(persons)
    return dict(Counter(_apportion(persons, _city_weights())))


def _check_counts(persons: int) -> None:
    if isinstance(persons, bool) or not isinstance(persons, int):
        raise ValueError("Le nombre de personnes doit être 50, 75 ou 100.")
    if persons not in ALLOWED_PERSON_COUNTS:
        raise ValueError("Le nombre de personnes doit être 50, 75 ou 100.")


def _check_spec(persons: int, seed: int, start: date, days: int) -> None:
    _check_counts(persons)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("La graine doit être un entier positif ou nul.")
    if type(start) is not date:
        raise ValueError("La date de départ doit être un lundi (objet date).")
    if start.weekday() != 0:
        raise ValueError("La date de départ doit être un lundi.")
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("La durée doit être un nombre de jours strictement positif.")


def _ids_of(quartiers: list[dict], roles: tuple[str, ...] | set[str], exclude: set[str]) -> list[str]:
    return [
        place["id"]
        for place in quartiers
        if place["role"] in roles and place["id"] not in exclude
    ]


def _choose(rng: random.Random, ids: list[str], why: str) -> str:
    if not ids:
        raise ValueError(f"Catalogue insuffisant : {why}")
    return rng.choice(ids)


def _pseudonym(index: int, reserved: set[str], used: set[str]) -> str:
    name = f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[index // len(FIRST_NAMES)]}"
    if name in reserved or name in used:
        name = f"{name} fictif"
    used.add(name)
    return name


def _scenario(plan: _Plan, weekday: int, counts: Counter) -> str | None:
    """Nom du scénario, ou None pour une journée sans déplacement."""
    profile = plan.profile
    if profile == "salarie":
        if weekday == plan.weekday_off:
            return None
        if weekday <= 3:
            return "commute"
        if weekday == 4:
            return "errand"
        if weekday == 5:
            return "shop"
        return "culte" if counts["equipement"] else None
    if profile == "etudiant":
        if weekday == 2:
            return None
        if weekday in (0, 1, 3):
            return "ecole"
        if weekday == 4:
            return "loisirs"
        if weekday == 5:
            return "shop"
        return "culte" if counts["equipement"] else None
    if profile == "commercant":
        if weekday == plan.weekday_off or weekday == 6:
            return None
        return "commute"
    if profile == "professionnel":
        if weekday in (0, 1, 3, 4):
            return "tour"
        return None
    if weekday in (0, 2):
        return None
    if weekday == 1:
        if counts["habitat"] + counts["mixte"] >= 2:
            return "visite"
        return "shop"
    if weekday == 3:
        return "sante" if counts["equipement"] else None
    if weekday in (4, 5):
        return "shop"
    return "culte" if counts["equipement"] else None


def _shop_purpose(day_index: int) -> str:
    if (day_index // 7) % 2:
        return "courses_marche"
    return "courses_supermarche"


def _intents(
    rng: random.Random,
    plan: _Plan,
    scenario: str,
    day_index: int,
    quartiers: list[dict],
) -> list[_Intent]:
    home = plan.home_id
    work = plan.work_id
    intents: list[_Intent] = []

    def _stay(place_id: str, purpose: str, dwell_min: int, dwell_max: int, optional: bool = False) -> None:
        intents.append(_Intent(place_id, purpose, dwell_min, dwell_max, optional))

    def _home() -> None:
        _stay(home, "retour_domicile", 0, 0, False)

    if scenario in {"commute", "ecole", "errand", "loisirs"}:
        if work is None:
            raise ValueError(f"{plan.profile} sans lieu d'ancrage.")
        purpose = "ecole" if scenario in {"ecole", "loisirs"} else "travail"
        if scenario == "errand":
            _stay(work, purpose, 360, 450)
            shop = _choose(
                rng,
                _ids_of(quartiers, {"commerce"}, {home, work}),
                "courses sans commerce distinct",
            )
            _stay(shop, "courses_supermarche", 20, 50, True)
        elif scenario == "loisirs":
            _stay(work, purpose, 300, 420)
            pool = _ids_of(quartiers, {"commerce", "mixte", "equipement"}, {home, work})
            if pool:
                _stay(_choose(rng, pool, "loisirs"), "loisirs", 45, 90, True)
        elif scenario == "ecole":
            _stay(work, purpose, 300, 420)
        else:
            _stay(work, purpose, 420, 510)
        _home()
        return intents

    if scenario == "tour":
        pool = [place["id"] for place in quartiers if place["id"] != home]
        order = list(pool)
        rng.shuffle(order)
        if len(order) < 2:
            raise ValueError("Tournée impossible : moins de deux quartiers hors domicile.")
        _stay(order[0], "deplacement_professionnel", 45, 100)
        _stay(order[1], "deplacement_professionnel", 45, 100, True)
        _home()
        return intents

    if scenario == "shop":
        shop = _choose(rng, _ids_of(quartiers, {"commerce"}, {home}), "courses sans commerce")
        _stay(shop, _shop_purpose(day_index), 30, 70)
        _home()
        return intents

    if scenario == "culte":
        pool = _ids_of(quartiers, {"equipement"}, {home})
        preferred = [place_id for place_id in pool if place_id != work]
        _stay(_choose(rng, preferred or pool, "culte sans équipement"), "culte", 60, 100)
        _home()
        return intents

    if scenario == "sante":
        pool = _ids_of(quartiers, {"equipement"}, {home})
        preferred = [place_id for place_id in pool if place_id != work]
        _stay(_choose(rng, preferred or pool, "santé sans équipement"), "sante", 30, 70)
        _home()
        return intents

    pool = _ids_of(quartiers, {"habitat", "mixte"}, {home})
    _stay(_choose(rng, pool, "visite sans second quartier résidentiel"), "visite", 90, 180)
    _home()
    return intents


def _select_mode(distance_km: float, person_index: int, day_index: int, leg_index: int) -> str:
    options = modes_for_distance(distance_km)
    salt = person_index * 31 + day_index * 7 + leg_index
    return options[salt % len(options)]


def _clock(minute: int) -> time:
    if minute < 0 or minute > LATEST_MINUTE:
        raise ValueError("Heure hors de la journée civile.")
    return time(minute // 60, minute % 60)


def _fit_start(preferred: int, total: int) -> int | None:
    latest = LATEST_MINUTE - total
    if latest < EARLIEST_MINUTE:
        return None
    start = min(preferred, latest)
    if start < EARLIEST_MINUTE:
        start = EARLIEST_MINUTE
    if start > latest:
        return None
    return start


def _emit(
    spec: CohortSpec,
    plan: _Plan,
    day: date,
    day_index: int,
    intents: list[_Intent],
    dwells: list[int],
    preferred_start: int,
) -> list[TripDraft] | None:
    if intents[-1].place_id != plan.home_id:
        return None
    specs = []
    origin_id = plan.home_id
    for leg_index, intent in enumerate(intents):
        if intent.place_id == origin_id:
            return None
        origin = PLACES[origin_id]
        dest = PLACES[intent.place_id]
        km = route_km(origin["lon"], origin["lat"], dest["lon"], dest["lat"])
        mode = _select_mode(km, plan.index, day_index, leg_index)
        minutes = duration_minutes(km, mode)
        specs.append((origin_id, intent, km, mode, minutes))
        origin_id = intent.place_id
    if len(dwells) != len(intents) - 1:
        return None
    total = sum(item[4] for item in specs) + sum(dwells)
    start = _fit_start(preferred_start, total)
    if start is None:
        return None
    clock = start
    trips = []
    for step, ((origin_id, intent, km, mode, minutes), dwell) in enumerate(
        zip(specs, [*dwells, 0])
    ):
        depart = clock
        arrive = clock + minutes
        if arrive > LATEST_MINUTE or arrive <= depart:
            return None
        dest = PLACES[intent.place_id]
        trips.append(
            TripDraft(
                trip_id=(
                    f"cohort-{spec.seed}-{plan.index:03d}-"
                    f"{day.strftime('%Y%m%d')}-{step:02d}"
                ),
                dataset_id=DATASET_ID,
                person_id=f"cohort-{spec.seed}-{plan.index:03d}",
                trip_date=day,
                depart_time=_clock(depart),
                arrive_time=_clock(arrive),
                origin_place_id=origin_id,
                destination_place_id=intent.place_id,
                purpose_code=intent.purpose,
                mode_code=mode,
                distance_km=km,
                duration_min=minutes,
                detail=f"{_DETAILS[intent.purpose]}, {dest['name']}",
                source=SOURCE,
                validation_status="validated",
                survey_id=None,
                import_batch_id=None,
            )
        )
        clock = arrive + dwell
    return trips


def _schedule(
    rng: random.Random,
    spec: CohortSpec,
    plan: _Plan,
    day: date,
    day_index: int,
    intents: list[_Intent],
) -> list[TripDraft]:
    dwell_of = [rng.randint(intent.dwell_min, intent.dwell_max) for intent in intents[:-1]]
    preferred = rng.randint(*_WINDOWS[_scenario_window(intents)])
    full = list(range(len(intents)))
    required = [index for index, intent in enumerate(intents) if not intent.optional]

    def attempt(indices: list[int], minimum: bool) -> list[TripDraft] | None:
        chosen = [intents[index] for index in indices]
        if minimum:
            dwells = [intents[index].dwell_min for index in indices[:-1]]
        else:
            dwells = [dwell_of[index] for index in indices[:-1]]
        return _emit(spec, plan, day, day_index, chosen, dwells, preferred)

    passes = ((full, False), (full, True))
    if len(required) < len(full):
        passes = (*passes, (required, False), (required, True))
    for indices, minimum in passes:
        trips = attempt(indices, minimum)
        if trips:
            return trips
    return []


def _scenario_window(intents: list[_Intent]) -> str:
    purpose = intents[0].purpose
    if purpose == "deplacement_professionnel":
        return "tour"
    if purpose == "courses_supermarche" or purpose == "courses_marche":
        return "shop"
    if purpose == "culte":
        return "culte"
    if purpose == "visite":
        return "visite"
    if purpose == "sante":
        return "sante"
    if purpose == "ecole" and any(item.purpose == "loisirs" for item in intents):
        return "loisirs"
    if purpose == "ecole":
        return "ecole"
    if any(item.purpose == "courses_supermarche" for item in intents):
        return "errand"
    return "commute"


def _plans(rng: random.Random, persons: int, seed: int) -> list[_Plan]:
    for city in CITIES:
        counts = _role_counts(city["id"])
        if counts["habitat"] == 0:
            continue
        for profile, _weight in PROFILE_WEIGHTS:
            anchor_role(city["id"], profile)
    cities = _apportion(persons, _city_weights())
    profiles = _apportion(persons, PROFILE_WEIGHTS)
    rng.shuffle(cities)
    rng.shuffle(profiles)
    reserved = {person["name"] for person in PERSONS}
    used: set[str] = set()
    salarie_seen = 0
    commercant_seen = 0
    plans = []
    for index, (city_id, profile) in enumerate(zip(cities, profiles)):
        quartiers = _quartiers(city_id)
        home_id = _choose(
            rng,
            _ids_of(quartiers, {"habitat"}, set()),
            f"domicile à {city_id}",
        )
        role = anchor_role(city_id, profile)
        work_id = None
        if role is not None:
            work_id = _choose(
                rng,
                _ids_of(quartiers, {role}, {home_id}),
                f"ancrage {profile} à {city_id}",
            )
        if profile == "salarie":
            weekday_off = salarie_seen % 5
            salarie_seen += 1
        elif profile == "commercant":
            weekday_off = commercant_seen % 4
            commercant_seen += 1
        else:
            weekday_off = None
        plans.append(
            _Plan(
                index=index,
                profile=profile,
                city_id=city_id,
                home_id=home_id,
                work_id=work_id,
                display_name=_pseudonym(index, reserved, used),
                weekday_off=weekday_off,
            )
        )
    return plans


def generate_cohort(*, persons: int, seed: int, start: date, days: int) -> CohortDraft:
    """Construit la cohorte en mémoire. Ne persiste rien.

    Les identifiants `cohort-{graine}-{index}` sont stables pour une
    même graine. Une journée sans déplacement n'a simplement aucune étape.
    Le jour chômé des salariés tourne du lundi au vendredi selon leur
    rang, afin qu'un horizon d'un seul jour contienne toujours des
    personnes sans déplacement, quelle que soit la graine.
    """
    _check_spec(persons, seed, start, days)
    rng = random.Random(seed)
    plans = _plans(rng, persons, seed)
    spec = CohortSpec(persons=persons, seed=seed, start=start, days=days)
    people = tuple(
        PersonDraft(
            person_id=f"cohort-{seed}-{plan.index:03d}",
            dataset_id=DATASET_ID,
            display_name=plan.display_name,
            city_id=plan.city_id,
            home_place_id=plan.home_id,
            work_place_id=plan.work_id,
            activity=PROFILE_ACTIVITY[plan.profile],
            source=SOURCE,
            profile=plan.profile,
        )
        for plan in plans
    )
    trips: list[TripDraft] = []
    for plan in plans:
        quartiers = _quartiers(plan.city_id)
        counts = _role_counts(plan.city_id)
        for offset in range(days):
            day = start + timedelta(days=offset)
            scenario = _scenario(plan, day.weekday(), counts)
            if scenario is None:
                continue
            intents = _intents(rng, plan, scenario, offset, quartiers)
            trips.extend(_schedule(rng, spec, plan, day, offset, intents))
    draft = CohortDraft(
        spec=spec,
        persisted=False,
        dataset=DatasetDraft(
            id=DATASET_ID,
            source=SOURCE,
            label=DATASET_LABEL,
            seed=seed,
            anchor_monday=start,
        ),
        persons=people,
        trips=tuple(sorted(trips, key=lambda trip: (trip.person_id, trip.trip_date, trip.depart_time, trip.trip_id))),
        adaptations=catalog_adaptations(),
        distance_method=DISTANCE_METHOD,
        duration_method=DURATION_METHOD,
    )
    validate_cohort(draft)
    return draft


def insertion_rows(draft: CohortDraft) -> dict:
    """Dictionnaires alignés sur les colonnes actuelles. Aucun INSERT ici."""
    validate_cohort(draft)
    return {
        "dataset": draft.dataset.row(),
        "persons": [person.row() for person in draft.persons],
        "trips": [trip.row() for trip in draft.trips],
    }


def validate_cohort(draft: CohortDraft) -> None:
    """Contrôle le brouillon. Lève ValueError au premier lot d'écarts."""
    errors = _problems(draft)
    if errors:
        preview = "; ".join(errors[:8])
        raise ValueError(f"{len(errors)} écarts dans le brouillon : {preview}")


def _problems(draft: CohortDraft) -> list[str]:
    errors: list[str] = []
    spec = draft.spec
    if draft.persisted:
        errors.append("le brouillon est marqué persisté")
    if draft.distance_method != DISTANCE_METHOD or "pgr" in draft.distance_method.lower():
        errors.append("méthode de distance inattendue")
    if draft.duration_method != DURATION_METHOD:
        errors.append("méthode de durée inattendue")
    if draft.adaptations != catalog_adaptations():
        errors.append("adaptations différentes du catalogue")
    dataset = draft.dataset
    if dataset.id != DATASET_ID or dataset.source != SOURCE:
        errors.append("jeu ou source inattendus")
    if dataset.seed != spec.seed or dataset.anchor_monday != spec.start:
        errors.append("graine ou lundi d'ancrage incohérents")
    if "SIMULATED" not in dataset.label or "pgRouting" not in dataset.label:
        errors.append("libellé insuffisamment explicite")
    if set(dataset.row()) != set(DATASET_COLUMNS):
        errors.append("colonnes dataset")

    if len(draft.persons) != spec.persons:
        errors.append("effectif inattendu")
    seen_ids: set[str] = set()
    diary_ids = {person["id"] for person in PERSONS}
    horizon = {spec.start + timedelta(days=offset) for offset in range(spec.days)}
    by_person: dict[str, list[TripDraft]] = {person.person_id: [] for person in draft.persons}
    person_by_id = {}
    for person in draft.persons:
        person_by_id[person.person_id] = person
        if person.person_id in seen_ids:
            errors.append(f"personne en double {person.person_id}")
        seen_ids.add(person.person_id)
        if person.person_id in diary_ids or not person.person_id.startswith("cohort-"):
            errors.append(f"identifiant réservé {person.person_id}")
        if person.dataset_id != DATASET_ID or person.source != SOURCE:
            errors.append(f"rattachement {person.person_id}")
        if person.profile not in PROFILE_ACTIVITY:
            errors.append(f"profil {person.person_id}")
        if person.activity != PROFILE_ACTIVITY[person.profile]:
            errors.append(f"activité {person.person_id}")
        if set(person.row()) != set(PERSON_COLUMNS) or "profile" in person.row():
            errors.append(f"colonnes personne {person.person_id}")
        home = PLACES.get(person.home_place_id)
        if home is None or home["level"] != "quartier" or home["city_id"] != person.city_id:
            errors.append(f"domicile {person.person_id}")
        elif home["role"] != "habitat":
            errors.append(f"domicile non résidentiel {person.person_id}")
        if person.profile == "foyer":
            if person.work_place_id is not None:
                errors.append(f"foyer avec travail {person.person_id}")
        else:
            work = PLACES.get(person.work_place_id or "")
            expected = anchor_role(person.city_id, person.profile)
            if (
                work is None
                or work["level"] != "quartier"
                or work["city_id"] != person.city_id
                or work["id"] == person.home_place_id
                or work["role"] != expected
            ):
                errors.append(f"ancrage {person.person_id}")
        if person.display_name in {item["name"] for item in PERSONS}:
            errors.append(f"pseudonyme du journal initial {person.display_name}")
    names = [person.display_name for person in draft.persons]
    if len(names) != len(set(names)):
        errors.append("pseudonymes en double")

    seen_trips: set[str] = set()
    trip_pattern = re.compile(rf"^cohort-{spec.seed}-\d{{3}}-\d{{8}}-\d{{2}}$")
    for trip in draft.trips:
        if trip.trip_id in seen_trips or not trip_pattern.match(trip.trip_id):
            errors.append(f"identifiant d'étape {trip.trip_id}")
        seen_trips.add(trip.trip_id)
        person = person_by_id.get(trip.person_id)
        if person is None or trip.dataset_id != DATASET_ID or trip.source != SOURCE:
            errors.append(f"étape orpheline {trip.trip_id}")
            continue
        if trip.trip_date not in horizon:
            errors.append(f"date hors horizon {trip.trip_id}")
        if trip.purpose_code not in PURPOSES or trip.mode_code not in MODES:
            errors.append(f"code {trip.trip_id}")
        if trip.validation_status != "validated" or trip.survey_id is not None or trip.import_batch_id is not None:
            errors.append(f"provenance {trip.trip_id}")
        if set(trip.row()) != set(TRIP_COLUMNS):
            errors.append(f"colonnes étape {trip.trip_id}")
        origin = PLACES.get(trip.origin_place_id)
        dest = PLACES.get(trip.destination_place_id)
        if (
            origin is None
            or dest is None
            or origin["id"] == dest["id"]
            or origin["city_id"] != person.city_id
            or dest["city_id"] != person.city_id
            or origin["level"] != "quartier"
            or dest["level"] != "quartier"
        ):
            errors.append(f"lieux {trip.trip_id}")
            continue
        expected_km = route_km(origin["lon"], origin["lat"], dest["lon"], dest["lat"])
        expected_min = duration_minutes(expected_km, trip.mode_code)
        if trip.distance_km != expected_km or trip.duration_min != expected_min:
            errors.append(f"distance ou durée {trip.trip_id}")
        if trip.mode_code not in modes_for_distance(trip.distance_km):
            errors.append(f"mode incohérent {trip.trip_id}")
        depart = trip.depart_time.hour * 60 + trip.depart_time.minute
        arrive = trip.arrive_time.hour * 60 + trip.arrive_time.minute
        if (
            trip.depart_time.second != 0
            or trip.arrive_time.second != 0
            or depart < EARLIEST_MINUTE
            or arrive > LATEST_MINUTE
            or arrive - depart != trip.duration_min
        ):
            errors.append(f"horaire {trip.trip_id}")
        if "ficti" not in trip.detail.lower():
            errors.append(f"détail {trip.trip_id}")
        by_person.setdefault(trip.person_id, []).append(trip)

    empty_days = 0
    multi = 0
    returns = 0
    for person_id, rows in by_person.items():
        person = person_by_id[person_id]
        grouped: dict[date, list[TripDraft]] = {}
        for trip in rows:
            grouped.setdefault(trip.trip_date, []).append(trip)
        empty_days += len(horizon - set(grouped))
        for day_rows in grouped.values():
            ordered = sorted(day_rows, key=lambda item: (item.depart_time, item.trip_id))
            if len(ordered) >= 2:
                multi += 1
            if len(ordered) < 2:
                errors.append(f"journée incomplète {person_id} {ordered[0].trip_date}")
                continue
            if ordered[0].origin_place_id != person.home_place_id:
                errors.append(f"départ hors domicile {person_id}")
            last = ordered[-1]
            if last.destination_place_id != person.home_place_id or last.purpose_code != "retour_domicile":
                errors.append(f"retour manquant {person_id} {last.trip_date}")
            else:
                returns += 1
            for previous, current in zip(ordered, ordered[1:]):
                if previous.destination_place_id != current.origin_place_id:
                    errors.append(f"chaîne cassée {current.trip_id}")
                if current.depart_time <= previous.arrive_time:
                    errors.append(f"chevauchement {current.trip_id}")
            steps = [trip.trip_id.rsplit("-", 1)[-1] for trip in ordered]
            if steps != [f"{index:02d}" for index in range(len(ordered))]:
                errors.append(f"numéros d'étape {person_id}")
    if empty_days < 1:
        errors.append("aucune journée sans déplacement")
    if multi < 1 or returns < 1:
        errors.append("aucun aller-retour")
    if spec.persons in ALLOWED_PERSON_COUNTS:
        profiles = Counter(person.profile for person in draft.persons)
        cities = Counter(person.city_id for person in draft.persons)
        if dict(profiles) != planned_profile_counts(spec.persons):
            errors.append("répartition des profils")
        if dict(cities) != planned_city_counts(spec.persons):
            errors.append("répartition des villes")
    return errors
