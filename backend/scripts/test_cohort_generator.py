# -*- coding: utf-8 -*-
"""Contrôle le générateur de cohorte, sans base et sans les tests existants.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_cohort_generator.py
"""
from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.data.persons import PERSONS  # noqa: E402
from app.data.territory import PLACES  # noqa: E402
from app.services import cohort_generator as cohort  # noqa: E402
from app.services.diary import ROAD_FACTOR, SPEED_KMH, _route_km  # noqa: E402

CANONICAL_PURPOSES = {
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
}
CANONICAL_MODES = {"marche", "velo", "bus", "voiture", "taxi"}
START = date(2026, 10, 5)
SEED = 20261005

EXPECTED_PROFILES = {
    50: {"salarie": 23, "etudiant": 8, "commercant": 7, "professionnel": 5, "foyer": 7},
    75: {"salarie": 34, "etudiant": 11, "commercant": 11, "professionnel": 8, "foyer": 11},
    100: {"salarie": 45, "etudiant": 15, "commercant": 15, "professionnel": 10, "foyer": 15},
}
EXPECTED_CITIES = {
    50: {"tana": 33, "toamasina": 6, "antsirabe": 3, "mahajanga": 5, "fianarantsoa": 3},
    75: {"tana": 50, "toamasina": 9, "antsirabe": 4, "mahajanga": 8, "fianarantsoa": 4},
    100: {"tana": 67, "toamasina": 11, "antsirabe": 6, "mahajanga": 11, "fianarantsoa": 5},
}


def _draft(persons: int, *, seed: int = SEED, start: date = START, days: int = 28):
    return cohort.generate_cohort(persons=persons, seed=seed, start=start, days=days)


def _by_day(draft):
    grouped = defaultdict(list)
    for trip in draft.trips:
        grouped[(trip.person_id, trip.trip_date)].append(trip)
    return grouped


def _weekdays(draft, person_id: str) -> set[int]:
    return {trip.trip_date.weekday() for trip in draft.trips if trip.person_id == person_id}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    results: list[str] = []

    def record(ok: bool, label: str, detail: str = "") -> None:
        suffix = f" — {detail}" if detail else ""
        results.append(f"{'PASS' if ok else 'FAIL'} {label}{suffix}")

    places_before = tuple(sorted(PLACES))
    state = random.getstate()
    try:
        cohort.generate_cohort(persons=49, seed=SEED, start=START, days=7)
        record(False, "rejette 49 personnes")
    except ValueError:
        record(True, "rejette 49 personnes")
    try:
        cohort.generate_cohort(persons=True, seed=SEED, start=START, days=7)  # type: ignore[arg-type]
        record(False, "rejette un booléen")
    except ValueError:
        record(True, "rejette un booléen")
    try:
        cohort.generate_cohort(persons=75, seed=-1, start=START, days=7)
        record(False, "rejette une graine négative")
    except ValueError:
        record(True, "rejette une graine négative")
    try:
        cohort.generate_cohort(persons=75, seed=SEED, start=date(2026, 10, 6), days=7)
        record(False, "rejette un départ qui n'est pas un lundi")
    except ValueError:
        record(True, "rejette un départ qui n'est pas un lundi")
    try:
        cohort.generate_cohort(persons=75, seed=SEED, start=START, days=0)
        record(False, "rejette une durée nulle")
    except ValueError:
        record(True, "rejette une durée nulle")

    record(random.getstate() == state, "état aléatoire global inchangé")
    record(tuple(sorted(PLACES)) == places_before, "catalogue de lieux non muté")

    record(cohort.ROAD_FACTOR == ROAD_FACTOR, "facteur 1,35 aligné sur le journal")
    record(cohort.SPEED_KMH == SPEED_KMH, "vitesses alignées sur le journal")
    sample = cohort.route_km(47.5214, -18.9089, 47.5198, -18.9158)
    record(sample == _route_km(47.5214, -18.9089, 47.5198, -18.9158), "orthodromie identique", str(sample))
    record(
        cohort.duration_minutes(sample, "bus") == max(1, round(sample / SPEED_KMH["bus"] * 60)),
        "durée = distance / vitesse",
    )
    record(cohort.modes_for_distance(1.0) == ("marche", "velo"), "modes sous 1,5 km")
    record(cohort.modes_for_distance(8) == ("bus", "velo", "taxi"), "modes jusqu'à 8 km")
    record(cohort.modes_for_distance(8.01) == ("bus", "voiture", "taxi"), "modes au-delà de 8 km")

    source = Path(cohort.__file__).read_text(encoding="utf-8")
    record("sqlalchemy" not in source and "psycopg" not in source and "pgr_dijkstra" not in source, "aucun accès base ni routage")
    record("random.seed" not in source and "random.random(" not in source, "pas d'aléa global")

    adaptations = " ".join(cohort.catalog_adaptations())
    record("Antsirabe" in adaptations and "emploi" in adaptations, "Antsirabe signalé sans emploi")
    record("Fianarantsoa" in adaptations and "mixte" in adaptations, "Fianarantsoa ancré sur mixte")
    record("Mahajanga" in adaptations and "Toamasina" in adaptations, "villes sans équipement signalées")
    record("visite" in adaptations, "visite adaptée quand un seul quartier résidentiel")

    for count in (50, 75, 100):
        draft = _draft(count, days=14)
        record(len(draft.persons) == count, f"{count} personnes", str(len(draft.persons)))
        record(
            cohort.planned_profile_counts(count) == EXPECTED_PROFILES[count],
            f"profils {count}",
            str(cohort.planned_profile_counts(count)),
        )
        record(
            cohort.planned_city_counts(count) == EXPECTED_CITIES[count],
            f"villes {count}",
            str(cohort.planned_city_counts(count)),
        )
        record(draft == _draft(count, days=14), f"reproductible {count}")

    left = _draft(75, seed=1, days=7)
    right = _draft(75, seed=2, days=7)
    record(left != right, "deux graines donnent deux cohortes")
    record(
        {person.person_id for person in left.persons}.isdisjoint(person.person_id for person in right.persons),
        "identifiants distincts selon la graine",
    )

    draft = _draft(75, days=28)
    cohort.validate_cohort(draft)
    record(draft.persisted is False, "brouillon non persisté")
    record(draft.dataset.id == "sim-cohort" and draft.dataset.source == "SIMULATED", "jeu sim-cohort SIMULATED")
    rows = cohort.insertion_rows(draft)
    record("profile" not in rows["persons"][0], "profile absent de la ligne SQL")
    record(set(rows["trips"][0]) == set(cohort.TRIP_COLUMNS), "colonnes trips du contrat")
    record(all(row["survey_id"] is None and row["import_batch_id"] is None for row in rows["trips"]), "sans enquête ni import")
    record(all(row["source"] == "SIMULATED" for row in rows["persons"] + rows["trips"]), "source SIMULATED partout")

    purposes = {trip.purpose_code for trip in draft.trips}
    modes = {trip.mode_code for trip in draft.trips}
    record(purposes <= CANONICAL_PURPOSES and "retour_domicile" in purposes, "motifs canoniques", ",".join(sorted(purposes)))
    record(modes <= CANONICAL_MODES and len(modes) == 5, "cinq modes canoniques", ",".join(sorted(modes)))
    record(
        {person.person_id for person in draft.persons}.isdisjoint(person["id"] for person in PERSONS),
        "les huit personnes initiales ne sont pas réécrites",
    )

    grouped = _by_day(draft)
    sizes = Counter(len(items) for items in grouped.values())
    empty = 0
    horizon = {START + timedelta(days=offset) for offset in range(28)}
    for person in draft.persons:
        travelled = {trip.trip_date for trip in draft.trips if trip.person_id == person.person_id}
        empty += len(horizon - travelled)
    record(empty > 0, "journées sans déplacement", str(empty))
    record(max(sizes) >= 3 and sizes[2] > 0, "journées à plusieurs étapes", str(dict(sizes)))

    one_day = _draft(75, days=1)
    one_empty = sum(
        1
        for person in one_day.persons
        if not any(trip.person_id == person.person_id for trip in one_day.trips)
    )
    record(one_empty > 0, "un lundi isolé contient des personnes sans déplacement", str(one_empty))
    friday = START + timedelta(days=4)
    friday_empty = sum(
        1
        for person in draft.persons
        if not any(trip.person_id == person.person_id and trip.trip_date == friday for trip in draft.trips)
    )
    record(friday.weekday() == 4 and friday_empty > 0, "le vendredi de la première semaine a des journées vides", str(friday_empty))

    pattern_ok = True
    pattern_detail = ""
    for person in draft.persons:
        present = _weekdays(draft, person.person_id)
        if person.profile == "salarie":
            missing = [day for day in range(5) if day not in present]
            if len(missing) != 1 or 5 not in present:
                pattern_ok = False
                pattern_detail = f"salarie {person.person_id} {sorted(present)}"
                break
        elif person.profile == "etudiant":
            if 2 in present or any(day not in present for day in (0, 1, 3, 4, 5)):
                pattern_ok = False
                pattern_detail = f"etudiant {person.person_id} {sorted(present)}"
                break
        elif person.profile == "commercant":
            missing = [day for day in range(4) if day not in present]
            if len(missing) != 1 or 6 in present or 4 not in present or 5 not in present:
                pattern_ok = False
                pattern_detail = f"commercant {person.person_id} {sorted(present)}"
                break
        elif person.profile == "professionnel":
            if any(day in present for day in (2, 5, 6)) or any(day not in present for day in (0, 1, 3, 4)):
                pattern_ok = False
                pattern_detail = f"professionnel {person.person_id} {sorted(present)}"
                break
        elif person.profile == "foyer":
            if any(day in present for day in (0, 2)) or any(day not in present for day in (4, 5)):
                pattern_ok = False
                pattern_detail = f"foyer {person.person_id} {sorted(present)}"
                break
    record(pattern_ok, "calendrier des profils sur 28 jours", pattern_detail or "ok")

    antsirabe_roles = {
        PLACES[person.work_place_id]["role"]
        for person in draft.persons
        if person.city_id == "antsirabe" and person.profile in {"salarie", "professionnel"}
    }
    record(antsirabe_roles == {"equipement"}, "Antsirabe salarié sur equipement", str(antsirabe_roles))
    student_roles = {
        (person.city_id, PLACES[person.work_place_id]["role"])
        for person in draft.persons
        if person.profile == "etudiant" and person.city_id in {"mahajanga", "toamasina", "fianarantsoa"}
    }
    record(
        ("mahajanga", "emploi") in student_roles and ("toamasina", "mixte") in student_roles,
        "étudiants adaptés sans équipement",
        str(sorted(student_roles)),
    )
    no_equip = {"mahajanga", "toamasina"}
    leaked = [
        trip.purpose_code
        for trip in draft.trips
        if trip.purpose_code in {"sante", "culte"}
        and next(person.city_id for person in draft.persons if person.person_id == trip.person_id) in no_equip
    ]
    record(not leaked, "pas de santé ni de culte sans équipement")
    visite_antsirabe = [
        trip.trip_id
        for trip in draft.trips
        if trip.purpose_code == "visite"
        and next(person.city_id for person in draft.persons if person.person_id == trip.person_id) == "antsirabe"
    ]
    record(not visite_antsirabe, "pas de visite inventée à Antsirabe")

    bad_chain = []
    for (person_id, _day), items in grouped.items():
        home = next(person.home_place_id for person in draft.persons if person.person_id == person_id)
        ordered = sorted(items, key=lambda trip: trip.depart_time)
        if ordered[0].origin_place_id != home or ordered[-1].destination_place_id != home:
            bad_chain.append(person_id)
        if ordered[-1].purpose_code != "retour_domicile":
            bad_chain.append(ordered[-1].trip_id)
    record(not bad_chain, "chaque journée active revient au domicile", str(len(bad_chain)))

    print("\n".join(results))
    print("Adaptations :")
    for note in draft.adaptations:
        print(f"- {note}")
    print(
        f"Exemple seed={SEED} personnes={len(draft.persons)} "
        f"étapes={len(draft.trips)} journées_vides={empty} persisted={draft.persisted}"
    )
    failed = sum(1 for line in results if line.startswith("FAIL"))
    print(f"resultat {len(results) - failed}/{len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERREUR {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
