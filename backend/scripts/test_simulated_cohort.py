# -*- coding: utf-8 -*-
"""Valide le générateur, le seed sim-cohort et l'absence de régression.

Les contrôles du brouillon restent en mémoire. PostgreSQL de travail est
lu, jamais réécrit. L'idempotence, le remplacement de paramètres et le
rollback s'exécutent sur une base vide créée pour ce script,
``mobilite_lotd_cohort``, qui ne reçoit que les tables du contrat.
Elle est supprimée à la fin. Les tables OSM et ``sim_*`` n'y sont pas
copiées : un clone du 16 Go de travail n'est pas nécessaire, et ces
tables restent contrôlées par empreinte sur la base de travail.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_simulated_cohort.py
"""
from __future__ import annotations

import hashlib
import inspect
import math
import os
import random
import re
import subprocess
import sys
import traceback
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Connection, Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.data.persons import PERSONS  # noqa: E402
from app.data.territory import CITIES, PLACES  # noqa: E402
from app.services import cohort_generator as cohort  # noqa: E402
from app.services.diary import _scripted_day_trips  # noqa: E402
from app.services.diary_contract import (  # noqa: E402
    ANCHOR_MONDAY,
    DATASET_ID as DIARY_DATASET_ID,
    DIARY_TO_CODE,
    hour_to_time,
)

START = date(2026, 10, 5)
SEED = 20261005
PERSONS_N = 75
DAYS = 28
HORIZON_END = date(2026, 11, 1)
ISOLATED_DB = "mobilite_lotd_cohort"
IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")

# Codes canoniques lus dans purposes / modes (migration 30, base du 12 octobre 2026).
CANONICAL_PURPOSES = frozenset({
    "travail",
    "retour_domicile",
    "courses_supermarche",
    "courses_marche",
    "courses",
    "ecole",
    "sante",
    "loisirs",
    "culte",
    "visite",
    "autre",
    "deplacement_professionnel",
    "service_public",
})
CANONICAL_MODES = frozenset({"marche", "velo", "bus", "voiture", "taxi"})
DIARY_PURPOSE_LABELS = frozenset({
    "domicile",
    "supermarche",
    "marche",
})

# Liste auditée dans seed_simulated_cohort.REFERENCE_TABLES.
AUDITED_REFERENCE_TABLES = (
    "planet_osm_line",
    "planet_osm_point",
    "planet_osm_polygon",
    "planet_osm_roads",
    "roads_network",
    "mobility_zones",
    "mobility_flows",
    "sim_zones",
    "sim_companies",
    "sim_persons",
    "sim_trips",
    "sim_indicators",
    "sim_clusters",
    "sim_scenarios",
)
LARGE_TABLES = frozenset({
    "planet_osm_line",
    "planet_osm_point",
    "planet_osm_polygon",
    "planet_osm_roads",
    "roads_network",
})
CONTRACT_TABLES = (
    "purposes",
    "modes",
    "datasets",
    "places",
    "surveys",
    "import_batches",
    "persons",
    "import_rows",
    "trips",
)
PLACE_LEVELS = {"city": 0, "commune": 1, "quartier": 2}

PERSON_ID = re.compile(r"^cohort-20261005-\d{3}$")
TRIP_ID = re.compile(r"^cohort-20261005-\d{3}-\d{8}-\d{2}$")

WRITE_CHECKS = (
    "seed isolé : la connexion vise mobilite_lotd_cohort",
    "idempotence : effectifs stables",
    "idempotence : identifiants stables",
    "idempotence : empreintes métier stables",
    "remplacement : 50 personnes sur 14 jours remplace le jeu",
    "remplacement : le retour à la référence restaure les empreintes",
    "rollback : une durée négative annule la transaction du seed",
)


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.items.append(("PASS" if ok else "FAIL", label, detail))

    def skip(self, label: str, reason: str) -> None:
        self.items.append(("SKIP", label, reason))

    def counts(self) -> dict[str, int]:
        passed = sum(1 for status, _label, _detail in self.items if status == "PASS")
        failed = sum(1 for status, _label, _detail in self.items if status == "FAIL")
        skipped = sum(1 for status, _label, _detail in self.items if status == "SKIP")
        return {
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }


def _detail(status: str, label: str, detail: str) -> str:
    suffix = f" — {detail}" if detail else ""
    return f"{status} {label}{suffix}"


def raises_value_error(fn) -> tuple[bool, str]:
    try:
        fn()
    except ValueError as exc:
        return True, str(exc)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return False, "aucune ValueError"


def proxy_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Orthodromie terrestre × 1,35. Ce n'est pas un itinéraire."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    arc = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lon / 2) ** 2
    )
    crow = 2 * radius * math.asin(math.sqrt(arc))
    return round(crow * cohort.ROAD_FACTOR, 2)


def empty_person_days(draft: cohort.CohortDraft) -> int:
    active = {(trip.person_id, trip.trip_date) for trip in draft.trips}
    return len(draft.persons) * draft.spec.days - len(active)


def first_difference(left: cohort.CohortDraft, right: cohort.CohortDraft) -> str:
    if len(left.persons) != len(right.persons) or len(left.trips) != len(right.trips):
        return (
            f"effectifs {len(left.persons)}/{len(left.trips)} "
            f"contre {len(right.persons)}/{len(right.trips)}"
        )
    for index, (person, other) in enumerate(zip(left.persons, right.persons)):
        if person != other:
            return f"personne {index} {person.person_id}"
    for trip, other in zip(left.trips, right.trips):
        if trip != other:
            return (
                f"{trip.trip_id} date={trip.trip_date} "
                f"horaires={trip.depart_time}-{trip.arrive_time} "
                f"lieux={trip.origin_place_id}->{trip.destination_place_id} "
                f"motif={trip.purpose_code} mode={trip.mode_code} "
                f"km={trip.distance_km} min={trip.duration_min}"
            )
    if left != right:
        return "écart hors personnes et trajets"
    return ""


def check_generator(report: Report) -> cohort.CohortDraft | None:
    saved = random.getstate()
    places_before = tuple(sorted(PLACES))
    draft: cohort.CohortDraft | None = None
    try:
        report.check(START.weekday() == 0, "2026-10-05 est un lundi", START.isoformat())
        report.check(
            HORIZON_END == START + timedelta(days=DAYS - 1),
            "28 jours se terminent le 1er novembre 2026",
            HORIZON_END.isoformat(),
        )

        for count, days in ((50, 7), (75, 7), (100, 7)):
            try:
                sample = cohort.generate_cohort(persons=count, seed=SEED, start=START, days=days)
            except Exception as exc:
                report.check(False, f"accepte {count} personnes", f"{type(exc).__name__}: {exc}")
                continue
            report.check(
                len(sample.persons) == count and sample.persisted is False,
                f"accepte {count} personnes",
                f"{len(sample.persons)} personnes, {len(sample.trips)} trajets sur {days} jours",
            )

        forbidden = [0, 1, 49, 51, 74, 76, 99, 101, 150, -5, True, 75.0, "75"]
        accepted: list[str] = []
        for value in forbidden:
            try:
                cohort.generate_cohort(persons=value, seed=SEED, start=START, days=7)  # type: ignore[arg-type]
            except ValueError:
                continue
            except Exception as exc:
                accepted.append(f"{value!r} a levé {type(exc).__name__}")
            else:
                accepted.append(repr(value))
        report.check(
            not accepted,
            "effectifs hors 50, 75 et 100 refusés",
            "ok" if not accepted else "; ".join(accepted),
        )

        ok, message = raises_value_error(
            lambda: cohort.generate_cohort(persons=PERSONS_N, seed=-1, start=START, days=7)
        )
        report.check(ok, "graine négative refusée", message)
        non_int = []
        for seed in (1.5, "20261005", True):
            try:
                cohort.generate_cohort(persons=PERSONS_N, seed=seed, start=START, days=7)  # type: ignore[arg-type]
            except ValueError:
                continue
            else:
                non_int.append(repr(seed))
        report.check(not non_int, "graine non entière refusée", "ok" if not non_int else str(non_int))
        try:
            zero_seed = cohort.generate_cohort(persons=50, seed=0, start=START, days=7)
            report.check(zero_seed.dataset.seed == 0, "graine nulle acceptée", "seed=0")
        except ValueError as exc:
            report.check(False, "graine nulle acceptée", str(exc))

        ok, message = raises_value_error(
            lambda: cohort.generate_cohort(
                persons=PERSONS_N, seed=SEED, start=date(2026, 10, 6), days=7
            )
        )
        report.check(ok and date(2026, 10, 6).weekday() != 0, "départ qui n'est pas un lundi refusé", message)
        bad_days = []
        for days in (0, -1):
            try:
                cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days=days)
            except ValueError:
                continue
            else:
                bad_days.append(str(days))
        report.check(not bad_days, "durée inférieure à un jour refusée", "ok" if not bad_days else str(bad_days))

        invalid_calls = (
            ("personnes booléennes", lambda: cohort.generate_cohort(persons=True, seed=SEED, start=START, days=7)),  # type: ignore[arg-type]
            ("durée flottante", lambda: cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days=2.5)),  # type: ignore[arg-type]
            ("durée texte", lambda: cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days="28")),  # type: ignore[arg-type]
            ("départ datetime", lambda: cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=datetime(2026, 10, 5), days=7)),  # type: ignore[arg-type]
            ("départ texte", lambda: cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start="2026-10-05", days=7)),  # type: ignore[arg-type]
        )
        invalid_misses = []
        for label, fn in invalid_calls:
            try:
                fn()
            except ValueError:
                continue
            except Exception as exc:
                invalid_misses.append(f"{label}:{type(exc).__name__}")
            else:
                invalid_misses.append(label)
        report.check(
            not invalid_misses,
            "types de paramètres invalides refusés",
            "ok" if not invalid_misses else "; ".join(invalid_misses),
        )

        random.seed(12345)
        before_random = random.getstate()
        try:
            draft = cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days=DAYS)
        except Exception as exc:
            report.check(False, "brouillon de référence", f"{type(exc).__name__}: {exc}")
            return None
        after_random = random.getstate()
        report.check(before_random == after_random, "generate_cohort laisse l'état global de random intact")
        again = cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days=DAYS)
        difference = first_difference(draft, again)
        report.check(difference == "", "deux brouillons identiques aux mêmes paramètres", difference or "ok")
        report.check(tuple(sorted(PLACES)) == places_before, "aucun lieu ajouté au catalogue")
    finally:
        random.setstate(saved)
    return draft


def check_identity_and_calendar(report: Report, draft: cohort.CohortDraft) -> None:
    person_ids = [person.person_id for person in draft.persons]
    trip_ids = [trip.trip_id for trip in draft.trips]
    known = set(person_ids)
    bad_person_ids = [value for value in person_ids if not PERSON_ID.match(value)]
    bad_trip_ids = [value for value in trip_ids if not TRIP_ID.match(value)]
    orphans = sorted({trip.person_id for trip in draft.trips if trip.person_id not in known})
    report.check(len(person_ids) == len(set(person_ids)), "identifiants de personnes uniques", str(len(person_ids)))
    report.check(len(trip_ids) == len(set(trip_ids)), "identifiants de trajets uniques", str(len(trip_ids)))
    report.check(not bad_person_ids, "format cohort-{graine}-{index} des personnes", str(bad_person_ids[:3]))
    report.check(not bad_trip_ids, "format cohort-{graine}-{index}-{date}-{étape} des trajets", str(bad_trip_ids[:3]))
    report.check(not orphans, "chaque trajet pointe vers une personne du brouillon", str(orphans[:3]))
    diary_ids = {person["id"] for person in PERSONS}
    report.check(known.isdisjoint(diary_ids), "aucun identifiant du journal diary-week", str(sorted(known & diary_ids)))

    horizon = {START + timedelta(days=offset) for offset in range(DAYS)}
    outside = sorted({trip.trip_date.isoformat() for trip in draft.trips if trip.trip_date not in horizon})
    present = {trip.trip_date for trip in draft.trips}
    report.check(draft.dataset.anchor_monday == START, "lundi d'ancrage enregistré", draft.dataset.anchor_monday.isoformat())
    report.check(not outside, "toutes les dates restent dans les 28 jours", ", ".join(outside[:4]))
    report.check(
        bool(present) and min(present) == START and max(present) == HORIZON_END,
        "dates présentes du 5 octobre au 1er novembre 2026",
        f"{min(present).isoformat() if present else '-'} → {max(present).isoformat() if present else '-'}",
    )
    empty = empty_person_days(draft)
    report.check(empty > 0, "des journées sans déplacement existent", str(empty))
    report.check(
        empty == 516 and len(draft.persons) == 75 and len(draft.trips) == 3452,
        "référence 75 × 28, graine 20261005 : 3452 trajets et 516 journées vides",
        f"personnes={len(draft.persons)} trajets={len(draft.trips)} vides={empty}",
    )
    report.check(
        len(draft.trips) != 130 * 4 and max(present) > START + timedelta(days=6),
        "sim-cohort n'est pas une répétition de la semaine diary-week",
        f"{len(draft.trips)} trajets, {len(present)} dates distinctes",
    )


def check_trips(report: Report, draft: cohort.CohortDraft) -> None:
    report.check(cohort.ROAD_FACTOR == 1.35, "facteur de détour 1,35", str(cohort.ROAD_FACTOR))
    used_places: set[str] = set()
    place_errors: list[str] = []
    distance_errors: list[str] = []
    zero_distances = 0
    duration_errors: list[str] = []
    schedule_errors: list[str] = []
    purposes: set[str] = set()
    modes: set[str] = set()
    persons = {person.person_id: person for person in draft.persons}

    for person in draft.persons:
        used_places.add(person.home_place_id)
        if person.work_place_id:
            used_places.add(person.work_place_id)
        home = PLACES.get(person.home_place_id)
        if home is None or home["level"] != "quartier" or home["city_id"] != person.city_id or home["role"] != "habitat":
            place_errors.append(f"domicile {person.person_id}")
            continue
        if person.profile == "foyer":
            if person.work_place_id is not None:
                place_errors.append(f"foyer {person.person_id}")
            continue
        expected_role = cohort.anchor_role(person.city_id, person.profile)
        work = PLACES.get(person.work_place_id or "")
        if (
            work is None
            or work["level"] != "quartier"
            or work["city_id"] != person.city_id
            or work["role"] != expected_role
            or work["id"] == person.home_place_id
        ):
            place_errors.append(f"ancrage {person.person_id}")

    for trip in draft.trips:
        purposes.add(trip.purpose_code)
        modes.add(trip.mode_code)
        used_places.add(trip.origin_place_id)
        used_places.add(trip.destination_place_id)
        person = persons[trip.person_id]
        origin = PLACES.get(trip.origin_place_id)
        dest = PLACES.get(trip.destination_place_id)
        if (
            origin is None
            or dest is None
            or origin["level"] != "quartier"
            or dest["level"] != "quartier"
            or origin["city_id"] != person.city_id
            or dest["city_id"] != person.city_id
            or origin["id"] == dest["id"]
        ):
            place_errors.append(trip.trip_id)
            continue
        if not math.isfinite(trip.distance_km) or trip.distance_km < 0:
            distance_errors.append(trip.trip_id)
            continue
        if trip.distance_km == 0:
            zero_distances += 1
        expected_km = proxy_km(origin["lon"], origin["lat"], dest["lon"], dest["lat"])
        if trip.distance_km != expected_km or expected_km != cohort.route_km(
            origin["lon"], origin["lat"], dest["lon"], dest["lat"]
        ):
            distance_errors.append(trip.trip_id)
        speed = cohort.SPEED_KMH.get(trip.mode_code)
        if speed is None:
            duration_errors.append(trip.trip_id)
            continue
        expected_min = max(1, round(trip.distance_km / speed * 60))
        if trip.duration_min != expected_min or trip.duration_min != cohort.duration_minutes(trip.distance_km, trip.mode_code):
            duration_errors.append(trip.trip_id)
        if trip.duration_min <= 0:
            duration_errors.append(trip.trip_id)
        depart = trip.depart_time.hour * 60 + trip.depart_time.minute
        arrive = trip.arrive_time.hour * 60 + trip.arrive_time.minute
        if (
            type(trip.depart_time) is not time
            or type(trip.arrive_time) is not time
            or trip.depart_time.second != 0
            or trip.arrive_time.second != 0
            or arrive <= depart
            or arrive - depart != trip.duration_min
            or depart < cohort.EARLIEST_MINUTE
            or arrive > cohort.LATEST_MINUTE
        ):
            schedule_errors.append(trip.trip_id)

    unknown_places = sorted(used_places - set(PLACES))
    report.check(not unknown_places and not place_errors, "lieux du catalogue, ville et rôle respectés", str((unknown_places + place_errors)[:4]))
    notes = "\n".join(cohort.catalog_adaptations())
    for city_name in ("Antsirabe", "Fianarantsoa", "Toamasina", "Mahajanga"):
        report.check(city_name in notes, f"adaptation documentée : {city_name}")
    report.check(
        cohort.anchor_role("antsirabe", "salarie") == "equipement"
        and cohort.anchor_role("fianarantsoa", "salarie") == "mixte"
        and cohort.anchor_role("toamasina", "etudiant") == "mixte"
        and cohort.anchor_role("mahajanga", "etudiant") == "emploi",
        "rôles d'ancrage Antsirabe, Fianarantsoa, Toamasina, Mahajanga",
    )
    mahajanga_students = [
        person for person in draft.persons
        if person.city_id == "mahajanga" and person.profile == "etudiant"
    ]
    airport = [
        person.person_id
        for person in mahajanga_students
        if PLACES[person.work_place_id]["id"] != "maja.aero"
    ]
    report.check(
        bool(mahajanga_students) and not airport,
        "étudiants de Mahajanga ancrés sur l'aéroport du catalogue",
        f"{len(mahajanga_students)} personnes ; limite connue du catalogue, pas un réalisme géographique",
    )
    thin_cities = {
        city["id"]
        for city in CITIES
        if sum(
            1
            for place in PLACES.values()
            if place["city_id"] == city["id"]
            and place["level"] == "quartier"
            and place["role"] in {"habitat", "mixte"}
        ) < 2
    }
    no_equipment = {
        city["id"]
        for city in CITIES
        if not any(
            place["city_id"] == city["id"] and place["level"] == "quartier" and place["role"] == "equipement"
            for place in PLACES.values()
        )
    }
    leaked_visite = [
        trip.trip_id
        for trip in draft.trips
        if trip.purpose_code == "visite" and persons[trip.person_id].city_id in thin_cities
    ]
    leaked_care = [
        trip.trip_id
        for trip in draft.trips
        if trip.purpose_code in {"sante", "culte"} and persons[trip.person_id].city_id in no_equipment
    ]
    report.check(not leaked_visite, "pas de visite là où le catalogue n'a qu'un quartier résidentiel", str(len(leaked_visite)))
    report.check(not leaked_care, "pas de santé ni de culte sans quartier équipement", str(len(leaked_care)))

    report.check(
        purposes <= CANONICAL_PURPOSES and purposes <= cohort.PURPOSES and "retour_domicile" in purposes,
        "motifs canoniques, dont retour_domicile",
        ",".join(sorted(purposes)),
    )
    report.check(
        "deplacement_professionnel" in purposes and "deplacement_professionnel" in CANONICAL_PURPOSES,
        "deplacement_professionnel est un code canonique déjà prévu",
    )
    report.check(purposes.isdisjoint(DIARY_PURPOSE_LABELS), "libellés historiques absents des motifs du brouillon")
    report.check(
        modes <= CANONICAL_MODES and modes <= frozenset(cohort.SPEED_KMH),
        "modes canoniques couverts par les vitesses du générateur",
        ",".join(sorted(modes)),
    )
    report.check(
        not distance_errors,
        "distances = orthodromie × 1,35, finies et positives ou nulles",
        f"écarts={len(distance_errors)} nulles={zero_distances}",
    )
    report.check(not duration_errors, "durées = max(1, round(km / vitesse du mode × 60))", str(len(duration_errors)))
    report.check(not schedule_errors, "horaires dans le jour civil, durée strictement positive", str(len(schedule_errors)))

    grouped: dict[tuple[str, date], list[cohort.TripDraft]] = defaultdict(list)
    for trip in draft.trips:
        grouped[(trip.person_id, trip.trip_date)].append(trip)
    return_errors: list[str] = []
    for (person_id, _day), items in grouped.items():
        ordered = sorted(items, key=lambda trip: (trip.depart_time, trip.trip_id))
        last = ordered[-1]
        home = persons[person_id].home_place_id
        if last.purpose_code != "retour_domicile" or last.destination_place_id != home:
            return_errors.append(last.trip_id)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.destination_place_id != current.origin_place_id or current.depart_time <= previous.arrive_time:
                return_errors.append(current.trip_id)
                break
    report.check(
        not return_errors and len(grouped) > 0,
        "journées actives : dernier motif retour_domicile vers le domicile",
        str(len(return_errors)),
    )
    report.check(
        empty_person_days(draft) == PERSONS_N * DAYS - len(grouped),
        "journées vides comptées par le calendrier, pas par un comptage brut de trips",
        str(empty_person_days(draft)),
    )


def check_rows(report: Report, draft: cohort.CohortDraft) -> dict:
    source = inspect.getsource(cohort.insertion_rows)
    report.check(
        "execute" not in source and "sqlalchemy" not in source and ".begin(" not in source,
        "insertion_rows ne contient aucun appel SQL",
    )
    report.check(draft.persisted is False, "brouillon persisted=False")
    rows = cohort.insertion_rows(draft)
    report.check(draft.persisted is False, "insertion_rows ne marque pas le brouillon persisté")
    report.check(set(rows["dataset"]) == set(cohort.DATASET_COLUMNS), "colonnes dataset", ",".join(sorted(rows["dataset"])))
    person_keys = [set(row) for row in rows["persons"]]
    trip_keys = [set(row) for row in rows["trips"]]
    report.check(
        bool(person_keys) and all(keys == set(cohort.PERSON_COLUMNS) for keys in person_keys),
        "colonnes persons, sans profile",
    )
    report.check(
        all("profile" not in row for row in rows["persons"]) and "profile" not in cohort.PERSON_COLUMNS,
        "le profil reste une donnée de contrôle du brouillon",
    )
    report.check(
        bool(trip_keys) and all(keys == set(cohort.TRIP_COLUMNS) for keys in trip_keys),
        "colonnes trips du contrat",
    )
    report.check(len(rows["persons"]) == len(draft.persons) == draft.spec.persons, "autant de lignes personnes que de personnes du brouillon", str(len(rows["persons"])))
    report.check(len(rows["trips"]) == len(draft.trips), "autant de lignes trajets que d'étapes du brouillon", str(len(rows["trips"])))
    allowed_sources = {"SIMULATED", "OBSERVED"}
    allowed_status = {"draft", "validated"}
    sources_ok = (
        rows["dataset"]["source"] == "SIMULATED"
        and rows["dataset"]["source"] in allowed_sources
        and all(row["source"] == "SIMULATED" for row in rows["persons"])
        and all(row["source"] == "SIMULATED" and row["validation_status"] == "validated" for row in rows["trips"])
        and all(row["validation_status"] in allowed_status for row in rows["trips"])
        and all(row["survey_id"] is None and row["import_batch_id"] is None for row in rows["trips"])
    )
    report.check(sources_ok, "sources SIMULATED et statut validated autorisés par le schéma")
    person_ids = {row["person_id"] for row in rows["persons"]}
    place_ids = set(PLACES)
    links_ok = all(row["person_id"] in person_ids for row in rows["trips"]) and all(
        row["origin_place_id"] in place_ids and row["destination_place_id"] in place_ids for row in rows["trips"]
    ) and all(row["purpose_code"] in CANONICAL_PURPOSES and row["mode_code"] in CANONICAL_MODES for row in rows["trips"])
    report.check(links_ok, "lignes d'insertion liées aux personnes, lieux, motifs et modes")
    return rows


def qident(name: str) -> str:
    if not IDENT.fullmatch(name):
        raise RuntimeError(f"Identifiant SQL refusé : {name}")
    return f'"{name}"'


def engine_for(db_name: str) -> Engine:
    from apply_sql_migration import connection_target

    if not IDENT.fullmatch(db_name):
        raise RuntimeError(f"Nom de base refusé : {db_name}")
    target = connection_target()
    url = (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{target['host']}:{target['port']}/{db_name}"
    )
    return create_engine(url, connect_args={"client_encoding": "utf8"}, pool_pre_ping=True)


def assert_isolated_name(name: str, working: str) -> None:
    if name != ISOLATED_DB or name == working or name in {"postgres", "template0", "template1", "mobilite"}:
        raise RuntimeError(f"Refus d'administrer la base {name}")


def columns_of(connection: Connection, table: str) -> list[tuple[str, str, str]]:
    rows = connection.execute(
        text(
            """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :table
            ORDER BY ordinal_position
            """
        ),
        {"table": table},
    ).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def primary_key(connection: Connection, table: str) -> list[str]:
    rows = connection.execute(
        text(
            """
            SELECT a.attname
            FROM pg_index AS i
            JOIN pg_attribute AS a
              ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
            WHERE i.indrelid = to_regclass(:regclass) AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """
        ),
        {"regclass": f"public.{table}"},
    ).scalars().all()
    return [name for name in rows if IDENT.fullmatch(name)]


def table_mark(connection: Connection, table: str) -> tuple[int, str]:
    """Empreinte déterministe. Les grandes tables utilisent un XOR de hachis."""
    table_sql = qident(table)
    specs = columns_of(connection, table)
    if table in LARGE_TABLES:
        pieces = []
        for name, data_type, _udt in specs:
            if data_type not in {"smallint", "integer", "bigint"} or not IDENT.fullmatch(name):
                continue
            quoted = qident(name)
            pieces.append(f"COALESCE({quoted}::text, '')")
        if not pieces:
            raise RuntimeError(f"{table} : aucune colonne entière pour l'empreinte")
        expr = " || '|' || ".join(pieces)
        count, mixed = connection.execute(
            text(
                f"SELECT COUNT(*), bit_xor(hashtextextended({expr}, 0)) FROM {table_sql}"
            )
        ).one()
        payload = f"{table}|count={int(count)}|xor={mixed}"
        return int(count), hashlib.sha256(payload.encode()).hexdigest()

    usable = []
    geometry = []
    for name, _data_type, udt in specs:
        if not IDENT.fullmatch(name):
            continue
        if udt == "geometry":
            geometry.append(name)
        else:
            usable.append(name)
    if not usable and not geometry:
        raise RuntimeError(f"{table} : colonnes non exploitables")
    expressions = [f"COALESCE({qident(name)}::text, '')" for name in usable]
    expressions.extend(
        f"COALESCE(md5(ST_AsEWKB({qident(name)})), '')" for name in geometry
    )
    order_cols = primary_key(connection, table) or usable[:1]
    order_sql = ", ".join(qident(name) for name in order_cols)
    joined = " || '|' || ".join(expressions)
    count, digest = connection.execute(
        text(
            f"""
            SELECT COUNT(*), md5(COALESCE(string_agg({joined}, ',' ORDER BY {order_sql}), ''))
            FROM {table_sql}
            """
        )
    ).one()
    return int(count), str(digest)


def protected_marks(connection: Connection, tables: tuple[str, ...]) -> dict[str, str]:
    present = set(connection.execute(
        text(
            """
            SELECT c.relname
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            """
        )
    ).scalars().all())
    marks: dict[str, str] = {}
    for table in tables:
        if table not in present:
            marks[table] = "ABSENTE"
            continue
        count, digest = table_mark(connection, table)
        marks[table] = f"{count}|{digest}"
    if "places" in present:
        count, digest = table_mark(connection, "places")
        marks["places"] = f"{count}|{digest}"
    else:
        marks["places"] = "ABSENTE"
    if "mobility_flows" in present:
        volume = connection.execute(text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")).scalar()
        marks["mobility_flows_volume"] = str(int(volume or 0))
    else:
        marks["mobility_flows_volume"] = "ABSENTE"
    return marks


def dataset_signature(connection: Connection, dataset_id: str) -> dict:
    dataset = connection.execute(
        text(
            """
            SELECT id, source, label, seed, anchor_monday::text
            FROM datasets
            WHERE id = :dataset_id
            """
        ),
        {"dataset_id": dataset_id},
    ).one_or_none()
    person_ids = list(connection.execute(
        text(
            """
            SELECT person_id FROM persons
            WHERE dataset_id = :dataset_id
            ORDER BY person_id
            """
        ),
        {"dataset_id": dataset_id},
    ).scalars().all())
    trip_ids = list(connection.execute(
        text(
            """
            SELECT trip_id FROM trips
            WHERE dataset_id = :dataset_id
            ORDER BY trip_id
            """
        ),
        {"dataset_id": dataset_id},
    ).scalars().all())
    person_hash = connection.execute(
        text(
            """
            SELECT md5(COALESCE(string_agg(
                person_id || '|' || dataset_id || '|' || COALESCE(display_name, '') || '|' ||
                city_id || '|' || home_place_id || '|' || COALESCE(work_place_id, '') || '|' ||
                COALESCE(activity, '') || '|' || source,
                E'\\n' ORDER BY person_id
            ), ''))
            FROM persons
            WHERE dataset_id = :dataset_id
            """
        ),
        {"dataset_id": dataset_id},
    ).scalar()
    trip_hash = connection.execute(
        text(
            """
            SELECT md5(COALESCE(string_agg(
                trip_id || '|' || dataset_id || '|' || person_id || '|' || trip_date::text || '|' ||
                depart_time::text || '|' || arrive_time::text || '|' ||
                origin_place_id || '|' || destination_place_id || '|' ||
                purpose_code || '|' || mode_code || '|' || distance_km::text || '|' ||
                duration_min::text || '|' || COALESCE(detail, '') || '|' || source || '|' ||
                validation_status || '|' || COALESCE(survey_id, '') || '|' ||
                COALESCE(import_batch_id::text, ''),
                E'\\n' ORDER BY trip_id
            ), ''))
            FROM trips
            WHERE dataset_id = :dataset_id
            """
        ),
        {"dataset_id": dataset_id},
    ).scalar()
    return {
        "dataset": None if dataset is None else tuple(dataset),
        "person_ids": person_ids,
        "trip_ids": trip_ids,
        "person_hash": person_hash,
        "trip_hash": trip_hash,
    }


def same_number(left, right) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return Decimal(str(left)) == Decimal(str(right))


def check_postgres_read(report: Report, connection: Connection, draft: cohort.CohortDraft) -> None:
    signature = dataset_signature(connection, cohort.DATASET_ID)
    dataset = signature["dataset"]
    report.check(
        dataset is not None and dataset[0] == "sim-cohort" and dataset[1] == "SIMULATED",
        "sim-cohort présent, source SIMULATED",
        "" if dataset is None else f"{dataset[1]} graine={dataset[3]} lundi={dataset[4]}",
    )
    report.check(
        dataset is not None and int(dataset[3]) == SEED and dataset[4] == START.isoformat(),
        "graine et lundi de la référence persistés",
        "" if dataset is None else f"{dataset[3]} {dataset[4]}",
    )
    report.check(
        len(signature["person_ids"]) == 75 and len(signature["trip_ids"]) == 3452,
        "effectifs persistés de la référence : 75 personnes et 3452 trajets",
        f"personnes={len(signature['person_ids'])} trajets={len(signature['trip_ids'])}",
    )
    bounds = connection.execute(
        text(
            """
            SELECT MIN(trip_date), MAX(trip_date), COUNT(*)
            FROM trips
            WHERE dataset_id = :dataset_id
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).one()
    report.check(
        bounds[0] == START and bounds[1] == HORIZON_END,
        "dates réellement stockées du 5 octobre au 1er novembre 2026",
        f"{bounds[0]} → {bounds[1]}",
    )
    outside = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips
            WHERE dataset_id = :dataset_id
              AND (trip_date < :start OR trip_date >= :horizon_end)
            """
        ),
        {
            "dataset_id": cohort.DATASET_ID,
            "start": START,
            "horizon_end": START + timedelta(days=DAYS),
        },
    ).scalar()
    report.check(int(outside or 0) == 0, "aucune étape de cohorte hors de la période", str(outside))

    duplicate_persons = len(signature["person_ids"]) - len(set(signature["person_ids"]))
    duplicate_trips = len(signature["trip_ids"]) - len(set(signature["trip_ids"]))
    report.check(duplicate_persons == 0 and duplicate_trips == 0, "identifiants persistés uniques")
    orphans = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips AS t
            LEFT JOIN persons AS p
              ON p.person_id = t.person_id AND p.dataset_id = t.dataset_id
            LEFT JOIN places AS origin ON origin.id = t.origin_place_id
            LEFT JOIN places AS destination ON destination.id = t.destination_place_id
            LEFT JOIN purposes ON purposes.code = t.purpose_code
            LEFT JOIN modes ON modes.code = t.mode_code
            WHERE t.dataset_id = :dataset_id
              AND (
                    p.person_id IS NULL OR origin.id IS NULL OR destination.id IS NULL
                 OR purposes.code IS NULL OR modes.code IS NULL
              )
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).scalar()
    report.check(int(orphans or 0) == 0, "clés étrangères personnes, lieux, motifs et modes", str(orphans))
    observed = connection.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM datasets WHERE source = 'OBSERVED')
              + (SELECT COUNT(*) FROM persons WHERE source = 'OBSERVED')
              + (SELECT COUNT(*) FROM trips WHERE source = 'OBSERVED')
            """
        )
    ).scalar()
    simulated_only = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips
            WHERE dataset_id = :dataset_id AND source <> 'SIMULATED'
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).scalar()
    report.check(
        int(observed or 0) == 0 and int(simulated_only or 0) == 0,
        "aucune ligne OBSERVED, et aucune étape de cohorte d'une autre source",
        f"observed={observed} autres={simulated_only}",
    )

    active = connection.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT person_id, trip_date
                FROM trips
                WHERE dataset_id = :dataset_id
            ) AS active_days
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).scalar()
    empty = PERSONS_N * DAYS - int(active or 0)
    report.check(
        empty == 516,
        "516 journées-personnes sans déplacement, calculées hors de trips",
        f"vides={empty} journées actives={active}",
    )

    db_purposes = set(connection.execute(text("SELECT code FROM purposes")).scalars().all())
    db_modes = set(connection.execute(text("SELECT code FROM modes")).scalars().all())
    report.check(db_purposes == CANONICAL_PURPOSES, "table purposes = codes canoniques audités")
    report.check(db_modes == CANONICAL_MODES, "table modes = codes canoniques audités")
    report.check(
        signature["person_ids"] == sorted(person.person_id for person in draft.persons)
        and signature["trip_ids"] == sorted(trip.trip_id for trip in draft.trips),
        "identifiants persistés égaux au brouillon régénéré",
    )

    stored_persons = connection.execute(
        text(
            """
            SELECT person_id, dataset_id, display_name, city_id, home_place_id,
                   work_place_id, activity, source
            FROM persons
            WHERE dataset_id = :dataset_id
            ORDER BY person_id
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).mappings().all()
    stored_trips = connection.execute(
        text(
            """
            SELECT trip_id, person_id, trip_date, depart_time, arrive_time,
                   origin_place_id, destination_place_id, purpose_code, mode_code,
                   distance_km, duration_min, detail, source, validation_status,
                   survey_id, import_batch_id
            FROM trips
            WHERE dataset_id = :dataset_id
            ORDER BY trip_id
            """
        ),
        {"dataset_id": cohort.DATASET_ID},
    ).mappings().all()
    person_mismatch = ""
    expected_persons = sorted(draft.persons, key=lambda person: person.person_id)
    if len(stored_persons) != len(expected_persons):
        person_mismatch = f"effectifs {len(stored_persons)}/{len(expected_persons)}"
    else:
        for stored, person in zip(stored_persons, expected_persons):
            expected = person.row()
            if any(stored[column] != expected[column] for column in cohort.PERSON_COLUMNS):
                person_mismatch = person.person_id
                break
    trip_mismatch = ""
    expected_trips = sorted(draft.trips, key=lambda trip: trip.trip_id)
    compared = (
        "person_id", "trip_date", "depart_time", "arrive_time",
        "origin_place_id", "destination_place_id", "purpose_code", "mode_code",
        "detail", "source", "validation_status", "survey_id", "import_batch_id",
    )
    if len(stored_trips) != len(expected_trips):
        trip_mismatch = f"effectifs {len(stored_trips)}/{len(expected_trips)}"
    else:
        for stored, trip in zip(stored_trips, expected_trips):
            if stored["trip_id"] != trip.trip_id:
                trip_mismatch = stored["trip_id"]
                break
            if any(stored[column] != getattr(trip, column) for column in compared):
                trip_mismatch = trip.trip_id
                break
            if not same_number(stored["distance_km"], trip.distance_km) or not same_number(stored["duration_min"], trip.duration_min):
                trip_mismatch = f"{trip.trip_id} km/min"
                break
    report.check(person_mismatch == "", "personnes persistées égales au brouillon", person_mismatch or "ok")
    report.check(trip_mismatch == "", "trajets persistés égaux au brouillon", trip_mismatch or "ok")


def expected_diary_trips() -> list[dict]:
    payload = []
    for person in PERSONS:
        for weekday in range(7):
            for trip in _scripted_day_trips(person, weekday):
                trip_date = ANCHOR_MONDAY + timedelta(days=weekday)
                depart = hour_to_time(trip["depart_hour"])
                arrive = (datetime.combine(trip_date, depart) + timedelta(minutes=int(trip["minutes"]))).time()
                payload.append({
                    "trip_id": trip["id"],
                    "person_id": person["id"],
                    "trip_date": trip_date,
                    "depart_time": depart,
                    "arrive_time": arrive,
                    "origin_place_id": trip["origin_id"],
                    "destination_place_id": trip["destination_id"],
                    "purpose_code": DIARY_TO_CODE[trip["purpose"]],
                    "mode_code": trip["mode"],
                    "distance_km": trip["km"],
                    "duration_min": int(trip["minutes"]),
                    "detail": trip["detail"],
                })
    return payload


def check_diary(report: Report, connection: Connection, label: str) -> dict:
    signature = dataset_signature(connection, DIARY_DATASET_ID)
    ids = signature["person_ids"]
    expected_ids = sorted(person["id"] for person in PERSONS)
    report.check(
        ids == expected_ids and len(ids) == 8 and len(signature["trip_ids"]) == 130,
        f"{label} : 8 personnes et 130 trajets",
        f"personnes={len(ids)} trajets={len(signature['trip_ids'])}",
    )
    stored = connection.execute(
        text(
            """
            SELECT trip_id, person_id, trip_date, depart_time, arrive_time,
                   origin_place_id, destination_place_id, purpose_code, mode_code,
                   distance_km, duration_min, detail
            FROM trips
            WHERE dataset_id = :dataset_id
            ORDER BY trip_id
            """
        ),
        {"dataset_id": DIARY_DATASET_ID},
    ).mappings().all()
    expected = sorted(expected_diary_trips(), key=lambda row: row["trip_id"])
    mismatch = ""
    if len(stored) != len(expected):
        mismatch = f"effectifs {len(stored)}/{len(expected)}"
    else:
        fields = (
            "person_id", "trip_date", "depart_time", "arrive_time",
            "origin_place_id", "destination_place_id", "purpose_code", "mode_code", "detail",
        )
        for left, right in zip(stored, expected):
            if left["trip_id"] != right["trip_id"]:
                mismatch = left["trip_id"]
                break
            if any(left[field] != right[field] for field in fields):
                mismatch = left["trip_id"]
                break
            if not same_number(left["distance_km"], right["distance_km"]) or not same_number(left["duration_min"], right["duration_min"]):
                mismatch = f"{left['trip_id']} km/min"
                break
    report.check(mismatch == "", f"{label} : données métier du journal de référence", mismatch or "ok")
    return signature


def check_reference_tables(report: Report, marks: dict[str, str], tables: tuple[str, ...]) -> None:
    missing = [table for table in tables if marks.get(table) == "ABSENTE"]
    report.check(
        not missing and len(tables) == 14,
        "14 tables protégées du lot C présentes",
        "ok" if not missing else ", ".join(missing),
    )
    for table in tables:
        mark = marks.get(table, "ABSENTE")
        if mark == "ABSENTE":
            report.skip(f"empreinte {table}", "table absente, empreinte non calculée")
            continue
        count = mark.split("|", 1)[0]
        report.check(True, f"empreinte initiale {table}", f"{count} lignes")
    flows = marks.get("mobility_flows", "ABSENTE")
    volume = marks.get("mobility_flows_volume", "ABSENTE")
    flow_count = None if flows == "ABSENTE" else int(flows.split("|", 1)[0])
    report.check(
        flow_count == 162 and volume == "8637",
        "mobility_flows : 162 lignes, volume 8637",
        f"lignes={flow_count} volume={volume}",
    )
    roads = marks.get("roads_network", "ABSENTE")
    road_count = None if roads == "ABSENTE" else int(roads.split("|", 1)[0])
    report.check(road_count == 1_043_643, "roads_network : 1043643 lignes", str(road_count))
    places = marks.get("places", "ABSENTE")
    place_count = None if places == "ABSENTE" else int(places.split("|", 1)[0])
    report.check(
        place_count == 66 and place_count == len(PLACES),
        "places : 66 lieux, égal au catalogue",
        f"{place_count}/{len(PLACES)}",
    )


def compare_marks(report: Report, before: dict[str, str], after: dict[str, str]) -> None:
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    report.check(not changed, "empreintes protégées identiques après les tests", "ok" if not changed else ", ".join(changed))


def working_quick_mark(connection: Connection) -> dict[str, str]:
    cohort_sig = dataset_signature(connection, cohort.DATASET_ID)
    diary_sig = dataset_signature(connection, DIARY_DATASET_ID)
    places = int(connection.execute(text("SELECT COUNT(*) FROM places")).scalar() or 0)
    flows = connection.execute(
        text("SELECT COUNT(*), COALESCE(SUM(trip_count), 0) FROM mobility_flows")
    ).one()
    sim_counts = {}
    for table in AUDITED_REFERENCE_TABLES:
        if table.startswith("sim_"):
            sim_counts[table] = int(connection.execute(text(f"SELECT COUNT(*) FROM {qident(table)}")).scalar() or 0)
    return {
        "cohort_persons": str(len(cohort_sig["person_ids"])),
        "cohort_trips": str(len(cohort_sig["trip_ids"])),
        "cohort_person_hash": str(cohort_sig["person_hash"]),
        "cohort_trip_hash": str(cohort_sig["trip_hash"]),
        "diary_persons": str(len(diary_sig["person_ids"])),
        "diary_trips": str(len(diary_sig["trip_ids"])),
        "diary_person_hash": str(diary_sig["person_hash"]),
        "diary_trip_hash": str(diary_sig["trip_hash"]),
        "places": str(places),
        "flows": f"{int(flows[0])}|{int(flows[1])}",
        "sim": str(sim_counts),
    }


def reflected_table(metadata: MetaData, name: str):
    for key in (name, f"public.{name}"):
        if key in metadata.tables:
            return metadata.tables[key]
    raise KeyError(name)


def copy_contract(source: Engine, dest: Engine) -> None:
    metadata = MetaData()
    metadata.reflect(bind=source, only=list(CONTRACT_TABLES), resolve_fks=True)
    metadata.create_all(bind=dest)
    with source.connect() as src, dest.begin() as dst:
        for name in CONTRACT_TABLES:
            table = reflected_table(metadata, name)
            payload = [dict(row) for row in src.execute(table.select()).mappings().all()]
            if not payload:
                continue
            if name == "places":
                payload.sort(key=lambda row: (PLACE_LEVELS.get(row["level"], 9), row["id"]))
                for level in ("city", "commune", "quartier"):
                    batch = [row for row in payload if row["level"] == level]
                    if batch:
                        dst.execute(table.insert(), batch)
                continue
            dst.execute(table.insert(), payload)
        checks = src.execute(
            text(
                """
                SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE contype = 'c'
                  AND connamespace = 'public'::regnamespace
                  AND conrelid::regclass::text = ANY (:tables)
                """
            ),
            {"tables": list(CONTRACT_TABLES)},
        ).fetchall()
        existing = set(dst.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'")).scalars().all())
        for table_name, constraint, definition in checks:
            short = table_name.split(".")[-1]
            if constraint in existing or not IDENT.fullmatch(constraint) or not IDENT.fullmatch(short):
                continue
            if not definition.startswith("CHECK "):
                continue
            dst.execute(text(f"ALTER TABLE {qident(short)} ADD CONSTRAINT {qident(constraint)} {definition}"))


def drop_isolated(admin: Engine, working: str) -> None:
    assert_isolated_name(ISOLATED_DB, working)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(
            text(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :name AND pid <> pg_backend_pid()
                """
            ),
            {"name": ISOLATED_DB},
        )
        connection.execute(text(f"DROP DATABASE IF EXISTS {qident(ISOLATED_DB)}"))


def create_isolated(admin: Engine, working: str) -> None:
    assert_isolated_name(ISOLATED_DB, working)
    drop_isolated(admin, working)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"CREATE DATABASE {qident(ISOLATED_DB)}"))


def run_seed(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_simulated_cohort.py"), *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
        check=False,
    )


def seed_output(completed: subprocess.CompletedProcess[str]) -> str:
    text_out = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    lines = text_out.strip().splitlines()
    return " | ".join(lines[-8:])


def skip_writes(report: Report, reason: str) -> None:
    for label in WRITE_CHECKS:
        report.skip(label, reason)


def check_isolated(
    report: Report,
    working_engine: Engine,
    working_name: str,
    guard_before: dict[str, str],
) -> None:
    from seed_simulated_cohort import SeedAbort, _persist

    admin = engine_for("postgres")
    isolated: Engine | None = None
    try:
        print("Création de la base isolée mobilite_lotd_cohort.", flush=True)
        create_isolated(admin, working_name)
        isolated = engine_for(ISOLATED_DB)
        with working_engine.connect() as source_connection:
            current = source_connection.execute(text("SELECT current_database()")).scalar()
        if current != working_name:
            raise RuntimeError(f"Connexion de travail inattendue : {current}")
        copy_contract(working_engine, isolated)
        with isolated.connect() as connection:
            located = connection.execute(text("SELECT current_database()")).scalar()
            diary_persons = connection.execute(
                text("SELECT COUNT(*) FROM persons WHERE dataset_id = :dataset_id"),
                {"dataset_id": DIARY_DATASET_ID},
            ).scalar()
            diary_trips = connection.execute(
                text("SELECT COUNT(*) FROM trips WHERE dataset_id = :dataset_id"),
                {"dataset_id": DIARY_DATASET_ID},
            ).scalar()
            has_check = connection.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'trips_duration_check'
                    """
                )
            ).scalar()
        if located != ISOLATED_DB or int(diary_persons or 0) != 8 or int(diary_trips or 0) != 130:
            raise RuntimeError(
                f"Copie isolée inexploitable : base={located} "
                f"journal={diary_persons}/{diary_trips}"
            )
        with isolated.connect() as connection:
            diary_before = dataset_signature(connection, DIARY_DATASET_ID)

        env = os.environ.copy()
        env["DB_NAME"] = ISOLATED_DB
        env["PYTHONIOENCODING"] = "utf-8"
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path[:0]=['.', 'scripts']; "
                "from apply_sql_migration import load_env, connection_target; "
                "load_env(); print(connection_target()['name'])",
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        seen = probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else ""
        report.check(
            probe.returncode == 0 and seen == ISOLATED_DB and seen != working_name,
            "seed isolé : la connexion vise mobilite_lotd_cohort",
            seen or seed_output(probe),
        )
        if seen != ISOLATED_DB:
            skip_writes(report, "la sonde n'a pas confirmé la base isolée, aucun seed lancé")
            # The probe check above was already recorded. Remove the duplicate skip of that label.
            report.items[:] = [
                item for item in report.items
                if not (item[0] == "SKIP" and item[1] == WRITE_CHECKS[0])
            ]
            return

        reference_args = ["--persons", "75", "--seed", "20261005", "--start", "2026-10-05", "--days", "28"]
        print("Seed isolé, première référence.", flush=True)
        first = run_seed(reference_args, env)
        with working_engine.connect() as connection:
            guard_mid = working_quick_mark(connection)
        if guard_mid != guard_before:
            report.check(False, "idempotence : effectifs stables", "la base de travail a changé, arrêt des seeds")
            report.skip("idempotence : identifiants stables", "base de travail modifiée")
            report.skip("idempotence : empreintes métier stables", "base de travail modifiée")
            report.skip(WRITE_CHECKS[4], "base de travail modifiée")
            report.skip(WRITE_CHECKS[5], "base de travail modifiée")
            report.skip(WRITE_CHECKS[6], "base de travail modifiée")
            return
        if first.returncode != 0:
            report.check(False, "idempotence : effectifs stables", seed_output(first))
            report.skip("idempotence : identifiants stables", "premier seed en échec")
            report.skip("idempotence : empreintes métier stables", "premier seed en échec")
            report.skip(WRITE_CHECKS[4], "premier seed en échec")
            report.skip(WRITE_CHECKS[5], "premier seed en échec")
            report.skip(WRITE_CHECKS[6], "premier seed en échec")
            return

        with isolated.connect() as connection:
            left = dataset_signature(connection, cohort.DATASET_ID)
        print("Seed isolé, seconde référence.", flush=True)
        second = run_seed(reference_args, env)
        with isolated.connect() as connection:
            right = dataset_signature(connection, cohort.DATASET_ID)
            diary_after = dataset_signature(connection, DIARY_DATASET_ID)
        report.check(
            second.returncode == 0
            and len(left["person_ids"]) == len(right["person_ids"]) == 75
            and len(left["trip_ids"]) == len(right["trip_ids"]) == 3452,
            "idempotence : effectifs stables",
            f"personnes={len(right['person_ids'])} trajets={len(right['trip_ids'])} exit={second.returncode}",
        )
        report.check(
            left["person_ids"] == right["person_ids"] and left["trip_ids"] == right["trip_ids"],
            "idempotence : identifiants stables",
        )
        report.check(
            left["dataset"] == right["dataset"]
            and left["person_hash"] == right["person_hash"]
            and left["trip_hash"] == right["trip_hash"]
            and diary_before == diary_after,
            "idempotence : empreintes métier stables",
            f"personnes={left['person_hash']} trajets={left['trip_hash']}",
        )
        if second.returncode != 0 or left["trip_hash"] != right["trip_hash"]:
            report.skip(WRITE_CHECKS[4], "empreinte de référence instable")
            report.skip(WRITE_CHECKS[5], "empreinte de référence instable")
            report.skip(WRITE_CHECKS[6], "empreinte de référence instable")
            return

        print("Seed isolé, remplacement 50 personnes / 14 jours.", flush=True)
        replaced = run_seed(
            ["--persons", "50", "--seed", "20261005", "--start", "2026-10-05", "--days", "14"],
            env,
        )
        draft50 = cohort.generate_cohort(persons=50, seed=SEED, start=START, days=14)
        with isolated.connect() as connection:
            current50 = dataset_signature(connection, cohort.DATASET_ID)
            outside = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM trips
                    WHERE dataset_id = :dataset_id
                      AND (trip_date < :start OR trip_date >= :horizon_end)
                    """
                ),
                {
                    "dataset_id": cohort.DATASET_ID,
                    "start": START,
                    "horizon_end": START + timedelta(days=14),
                },
            ).scalar()
        expected_persons = sorted(person.person_id for person in draft50.persons)
        expected_trips = sorted(trip.trip_id for trip in draft50.trips)
        report.check(
            replaced.returncode == 0
            and current50["person_ids"] == expected_persons
            and current50["trip_ids"] == expected_trips
            and int(outside or 0) == 0,
            "remplacement : 50 personnes sur 14 jours remplace le jeu",
            f"personnes={len(current50['person_ids'])} trajets={len(current50['trip_ids'])} hors_période={outside}",
        )
        print("Seed isolé, retour à la référence.", flush=True)
        restored = run_seed(reference_args, env)
        with isolated.connect() as connection:
            back = dataset_signature(connection, cohort.DATASET_ID)
            diary_back = dataset_signature(connection, DIARY_DATASET_ID)
        report.check(
            restored.returncode == 0
            and back["person_ids"] == right["person_ids"]
            and back["trip_ids"] == right["trip_ids"]
            and back["person_hash"] == right["person_hash"]
            and back["trip_hash"] == right["trip_hash"]
            and diary_back == diary_before,
            "remplacement : le retour à la référence restaure les empreintes",
            f"exit={restored.returncode}",
        )

        if has_check is None:
            report.skip(
                WRITE_CHECKS[6],
                "trips_duration_check absente de la base isolée : le seed n'a pas de commutateur d'erreur, "
                "et provoquer le rejet sans cette contrainte écrirait une durée négative",
            )
            return
        bad_rows = cohort.insertion_rows(
            cohort.generate_cohort(persons=PERSONS_N, seed=SEED, start=START, days=DAYS)
        )
        bad_rows["trips"][0]["duration_min"] = -1
        if isolated.url.database != ISOLATED_DB:
            raise RuntimeError("Refus d'exécuter le rollback hors de la base isolée")
        print("Rollback isolé : durée négative.", flush=True)
        try:
            _persist(isolated, bad_rows, START, DAYS)
        except SeedAbort as exc:
            rolled = f"SeedAbort: {exc}"
            raised = True
        except Exception as exc:
            rolled = f"{type(exc).__name__}: {exc}"
            raised = True
        else:
            rolled = "la transaction a validé la durée négative"
            raised = False
        with isolated.connect() as connection:
            after_rollback = dataset_signature(connection, cohort.DATASET_ID)
            diary_rollback = dataset_signature(connection, DIARY_DATASET_ID)
        report.check(
            raised
            and after_rollback["person_ids"] == back["person_ids"]
            and after_rollback["trip_ids"] == back["trip_ids"]
            and after_rollback["person_hash"] == back["person_hash"]
            and after_rollback["trip_hash"] == back["trip_hash"]
            and diary_rollback == diary_before,
            "rollback : une durée négative annule la transaction du seed",
            rolled.splitlines()[0][:240],
        )
    finally:
        if isolated is not None:
            isolated.dispose()
        try:
            drop_isolated(admin, working_name)
            print("Base isolée supprimée.", flush=True)
        finally:
            admin.dispose()


def check_postgres(report: Report, draft: cohort.CohortDraft) -> None:
    from apply_sql_migration import connection_target, load_env
    from seed_simulated_cohort import REFERENCE_TABLES

    load_env()
    print("Lecture de PostgreSQL.", flush=True)
    working_name = connection_target()["name"]
    engine = engine_for(working_name)
    try:
        with engine.connect() as connection:
            report.check(
                tuple(REFERENCE_TABLES) == AUDITED_REFERENCE_TABLES,
                "liste des tables protégées reprise du seed du lot C",
                str(len(REFERENCE_TABLES)),
            )
            print("Empreintes des tables protégées (lecture).", flush=True)
            before = protected_marks(connection, tuple(REFERENCE_TABLES))
            guard_before = working_quick_mark(connection)
            quick_before = connection.execute(
                text("SELECT COUNT(*) FROM trips WHERE dataset_id = :dataset_id"),
                {"dataset_id": cohort.DATASET_ID},
            ).scalar()
            check_postgres_read(report, connection, draft)
            check_diary(report, connection, "diary-week")
            check_reference_tables(report, before, tuple(REFERENCE_TABLES))
            rows = cohort.insertion_rows(draft)
            quick_after = connection.execute(
                text("SELECT COUNT(*) FROM trips WHERE dataset_id = :dataset_id"),
                {"dataset_id": cohort.DATASET_ID},
            ).scalar()
            report.check(
                int(quick_before or 0) == int(quick_after or 0) == len(rows["trips"]),
                "insertion_rows n'écrit rien dans PostgreSQL",
                f"trajets avant={quick_before} après={quick_after}",
            )

        try:
            check_isolated(report, engine, working_name, guard_before)
        except Exception as exc:
            report.check(False, "section base isolée", f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
            pending = [label for label in WRITE_CHECKS if not any(item[1] == label for item in report.items)]
            for label in pending:
                report.skip(label, f"section interrompue : {type(exc).__name__}")

        print("Relecture des empreintes protégées.", flush=True)
        with engine.connect() as connection:
            after = protected_marks(connection, tuple(REFERENCE_TABLES))
            guard_after = working_quick_mark(connection)
            diary_after = dataset_signature(connection, DIARY_DATASET_ID)
        compare_marks(report, before, after)
        report.check(
            guard_before == guard_after,
            "sim-cohort, diary-week, places, flux et sim_* inchangés sur la base de travail",
        )
        report.check(
            diary_after["person_ids"] == sorted(person["id"] for person in PERSONS)
            and len(diary_after["trip_ids"]) == 130,
            "diary-week toujours à 8 personnes et 130 trajets en fin de script",
        )
    finally:
        engine.dispose()


def skip_postgres(report: Report, reason: str) -> None:
    labels = [
        "sim-cohort présent, source SIMULATED",
        "effectifs persistés de la référence : 75 personnes et 3452 trajets",
        "dates réellement stockées du 5 octobre au 1er novembre 2026",
        "clés étrangères personnes, lieux, motifs et modes",
        "aucune ligne OBSERVED, et aucune étape de cohorte d'une autre source",
        "516 journées-personnes sans déplacement, calculées hors de trips",
        "diary-week : 8 personnes et 130 trajets",
        "14 tables protégées du lot C présentes",
        "mobility_flows : 162 lignes, volume 8637",
        "roads_network : 1043643 lignes",
        "places : 66 lieux, égal au catalogue",
        "empreintes protégées identiques après les tests",
        *WRITE_CHECKS,
    ]
    for label in labels:
        report.skip(label, reason)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    report = Report()
    saved_random = random.getstate()
    draft = None
    try:
        try:
            draft = check_generator(report)
            if draft is None:
                report.skip("contrôles du brouillon", "générateur de référence indisponible")
            else:
                cohort.validate_cohort(draft)
                report.check(True, "validate_cohort accepte le brouillon de référence")
                check_identity_and_calendar(report, draft)
                check_trips(report, draft)
                check_rows(report, draft)
                print(
                    "Rappel : un mois ou une année de sim-cohort se calcule sur les dates "
                    "réellement stockées. La semaine diary-week ne se répète pas pour "
                    "fabriquer ces statistiques.",
                    flush=True,
                )
            if draft is None:
                skip_postgres(report, "brouillon de référence indisponible")
            else:
                check_postgres(report, draft)
        except (Exception, SystemExit) as exc:
            report.check(False, "erreur inattendue", f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
            if not any(item[1] == "sim-cohort présent, source SIMULATED" for item in report.items):
                skip_postgres(report, f"PostgreSQL indisponible : {type(exc).__name__}: {exc}")
    finally:
        random.setstate(saved_random)

    print()
    for status, label, detail in report.items:
        print(_detail(status, label, detail))
    totals = report.counts()
    print()
    print(f"Vérifications exécutées : {totals['executed']}")
    print(f"Réussies : {totals['passed']}")
    print(f"Échouées : {totals['failed']}")
    print(f"Non exécutées : {totals['skipped']}")
    print("Lots E, F et G : non commencés.")
    if draft_available(report):
        print(
            "Les journées sans déplacement ne sont pas des lignes de trips. "
            "Les totaux mensuels ou annuels de sim-cohort partent des dates stockées."
        )
    return 1 if totals["failed"] else 0


def draft_available(report: Report) -> bool:
    return any(status == "PASS" and label == "validate_cohort accepte le brouillon de référence" for status, label, _detail in report.items)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERREUR {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
