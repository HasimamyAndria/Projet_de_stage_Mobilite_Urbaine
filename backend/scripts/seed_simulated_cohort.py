# -*- coding: utf-8 -*-
"""Insère le brouillon sim-cohort dans PostgreSQL.

Le générateur reste en mémoire (`persisted=False`). Ce script est le seul
écrivain. Il remplace les personnes et les étapes de `sim-cohort`, puis
valide la transaction. `diary-week`, les tables OSM, `mobility_flows`,
`roads_network` et `sim_*` ne sont pas modifiés.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\seed_simulated_cohort.py
    venv\\Scripts\\python.exe scripts\\seed_simulated_cohort.py --persons 75 --seed 20261005 --start 2026-10-05 --days 28
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from apply_sql_migration import load_env, make_engine  # noqa: E402

load_env()

from app.services.cohort_generator import (  # noqa: E402
    DATASET_ID,
    SOURCE,
    generate_cohort,
    insertion_rows,
    validate_cohort,
)
from app.services.diary_contract import DATASET_ID as DIARY_DATASET_ID  # noqa: E402

# Mêmes tables que seed_diary_trips.py. Une table absente est signalée,
# elle n'est pas comptée comme vérifiée.
REFERENCE_TABLES = (
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


class SeedAbort(RuntimeError):
    """Échec avant le commit. La transaction est annulée."""


def _parse_start(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("format attendu YYYY-MM-DD") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Insère ou remplace la cohorte fictive sim-cohort (source SIMULATED)."
    )
    parser.add_argument("--persons", type=int, default=75, help="50, 75 ou 100 (défaut 75)")
    parser.add_argument("--seed", type=int, default=20261005, help="graine entière >= 0")
    parser.add_argument("--start", type=_parse_start, default=date(2026, 10, 5), help="lundi YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=28, help="nombre de jours >= 1")
    return parser


def _md5(values: list[str]) -> str:
    payload = ",".join(sorted(values)).encode()
    return hashlib.md5(payload).hexdigest()


def _existing_tables(connection: Connection) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT c.relname
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            """
        )
    ).scalars()
    return set(rows)


def _table_count(connection: Connection, table: str) -> int:
    if not table.isidentifier():
        raise SeedAbort(f"Nom de table refusé : {table}")
    return int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)


def _reference(connection: Connection, tables: set[str]) -> dict[str, str]:
    marks: dict[str, str] = {}
    for table in REFERENCE_TABLES:
        if table not in tables:
            marks[table] = "ABSENTE"
            continue
        marks[table] = str(_table_count(connection, table))
    if "mobility_flows" in tables:
        volume = connection.execute(text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")).scalar()
        marks["mobility_flows_volume"] = str(int(volume or 0))
    else:
        marks["mobility_flows_volume"] = "ABSENTE"
    if "places" in tables:
        marks["places"] = str(_table_count(connection, "places"))
    else:
        marks["places"] = "ABSENTE"
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
    marks["observed_rows"] = str(int(observed or 0))
    return marks


def _diary_mark(connection: Connection) -> str | None:
    present = connection.execute(
        text("SELECT 1 FROM datasets WHERE id = :dataset_id"),
        {"dataset_id": DIARY_DATASET_ID},
    ).scalar()
    if present is None:
        return None
    row = connection.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM persons WHERE dataset_id = :dataset_id),
                (SELECT COUNT(*) FROM trips WHERE dataset_id = :dataset_id),
                (
                    SELECT md5(COALESCE(string_agg(person_id, ',' ORDER BY person_id), ''))
                    FROM persons
                    WHERE dataset_id = :dataset_id
                ),
                (
                    SELECT md5(COALESCE(string_agg(
                        trip_id || '|' || trip_date::text || '|' || depart_time::text || '|' ||
                        purpose_code || '|' || mode_code || '|' || distance_km::text || '|' ||
                        duration_min::text,
                        ',' ORDER BY trip_id
                    ), ''))
                    FROM trips
                    WHERE dataset_id = :dataset_id
                )
            """
        ),
        {"dataset_id": DIARY_DATASET_ID},
    ).one()
    return f"{int(row[0])}|{int(row[1])}|{row[2]}|{row[3]}"


def _other_datasets(connection: Connection) -> dict[str, tuple[int, int]]:
    rows = connection.execute(
        text(
            """
            SELECT
                d.id,
                (SELECT COUNT(*) FROM persons AS p WHERE p.dataset_id = d.id),
                (SELECT COUNT(*) FROM trips AS t WHERE t.dataset_id = d.id)
            FROM datasets AS d
            WHERE d.id <> :dataset_id
            ORDER BY d.id
            """
        ),
        {"dataset_id": DATASET_ID},
    )
    return {row[0]: (int(row[1]), int(row[2])) for row in rows}


def _require_same(before: dict, after: dict, label: str) -> None:
    if before != after:
        changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
        raise SeedAbort(f"{label} modifié : {', '.join(changed)}")


def _guard_rows(connection: Connection, rows: dict) -> None:
    dataset = rows["dataset"]
    persons = rows["persons"]
    trips = rows["trips"]
    if dataset["id"] != DATASET_ID or dataset["source"] != SOURCE:
        raise SeedAbort("Le brouillon ne cible pas sim-cohort / SIMULATED.")
    if DATASET_ID == DIARY_DATASET_ID:
        raise SeedAbort("Le jeu cohorte est identique à diary-week.")
    if any(row["source"] != SOURCE for row in persons + trips):
        raise SeedAbort("Une ligne du brouillon n'est pas SIMULATED.")

    existing = connection.execute(
        text("SELECT source FROM datasets WHERE id = :dataset_id"),
        {"dataset_id": DATASET_ID},
    ).scalar()
    if existing is not None and existing != SOURCE:
        raise SeedAbort(
            f"{DATASET_ID} existe déjà avec la source {existing}. "
            "Le seed ne convertit pas un jeu OBSERVED."
        )

    place_ids = {row[0] for row in connection.execute(text("SELECT id FROM places"))}
    needed = set()
    for person in persons:
        needed.add(person["city_id"])
        needed.add(person["home_place_id"])
        if person["work_place_id"]:
            needed.add(person["work_place_id"])
    for trip in trips:
        needed.add(trip["origin_place_id"])
        needed.add(trip["destination_place_id"])
    missing_places = sorted(needed - place_ids)
    if missing_places:
        preview = ", ".join(missing_places[:8])
        raise SeedAbort(f"Lieux absents du catalogue PostgreSQL : {preview}")

    purpose_codes = {row[0] for row in connection.execute(text("SELECT code FROM purposes"))}
    mode_codes = {row[0] for row in connection.execute(text("SELECT code FROM modes"))}
    missing_purposes = sorted({trip["purpose_code"] for trip in trips} - purpose_codes)
    missing_modes = sorted({trip["mode_code"] for trip in trips} - mode_codes)
    if missing_purposes or missing_modes:
        raise SeedAbort(
            "Codes absents du contrat : "
            f"motifs {missing_purposes or '-'} ; modes {missing_modes or '-'}."
        )

    other_persons = {
        row[0]
        for row in connection.execute(
            text("SELECT person_id FROM persons WHERE dataset_id <> :dataset_id"),
            {"dataset_id": DATASET_ID},
        )
    }
    other_trips = {
        row[0]
        for row in connection.execute(
            text("SELECT trip_id FROM trips WHERE dataset_id <> :dataset_id"),
            {"dataset_id": DATASET_ID},
        )
    }
    person_clash = sorted(other_persons & {person["person_id"] for person in persons})
    trip_clash = sorted(other_trips & {trip["trip_id"] for trip in trips})
    if person_clash or trip_clash:
        raise SeedAbort(
            "Identifiant déjà utilisé hors de sim-cohort : "
            f"personnes {person_clash[:4] or '-'} ; trajets {trip_clash[:4] or '-'}."
        )


def _replace(connection: Connection, rows: dict) -> None:
    connection.execute(
        text("DELETE FROM trips WHERE dataset_id = :dataset_id"),
        {"dataset_id": DATASET_ID},
    )
    connection.execute(
        text("DELETE FROM persons WHERE dataset_id = :dataset_id"),
        {"dataset_id": DATASET_ID},
    )
    connection.execute(
        text(
            """
            INSERT INTO datasets (id, source, label, seed, anchor_monday)
            VALUES (:id, :source, :label, :seed, :anchor_monday)
            ON CONFLICT (id) DO UPDATE SET
                source = EXCLUDED.source,
                label = EXCLUDED.label,
                seed = EXCLUDED.seed,
                anchor_monday = EXCLUDED.anchor_monday
            """
        ),
        rows["dataset"],
    )
    connection.execute(
        text(
            """
            INSERT INTO persons (
                person_id, dataset_id, display_name, city_id, home_place_id,
                work_place_id, activity, source
            ) VALUES (
                :person_id, :dataset_id, :display_name, :city_id, :home_place_id,
                :work_place_id, :activity, :source
            )
            """
        ),
        rows["persons"],
    )
    if rows["trips"]:
        connection.execute(
            text(
                """
                INSERT INTO trips (
                    trip_id, dataset_id, person_id, trip_date, depart_time, arrive_time,
                    origin_place_id, destination_place_id, purpose_code, mode_code,
                    distance_km, duration_min, detail, source, validation_status,
                    survey_id, import_batch_id
                ) VALUES (
                    :trip_id, :dataset_id, :person_id, :trip_date, :depart_time, :arrive_time,
                    :origin_place_id, :destination_place_id, :purpose_code, :mode_code,
                    :distance_km, :duration_min, :detail, :source, :validation_status,
                    :survey_id, :import_batch_id
                )
                """
            ),
            rows["trips"],
        )


def _verify(connection: Connection, rows: dict, start: date, days: int) -> dict:
    dataset = connection.execute(
        text(
            """
            SELECT source, seed, anchor_monday
            FROM datasets
            WHERE id = :dataset_id
            """
        ),
        {"dataset_id": DATASET_ID},
    ).one_or_none()
    if dataset is None:
        raise SeedAbort("sim-cohort absent après écriture.")
    if dataset[0] != SOURCE:
        raise SeedAbort(f"Source persistée inattendue : {dataset[0]}")
    if int(dataset[1]) != rows["dataset"]["seed"] or dataset[2] != start:
        raise SeedAbort("Graine ou lundi d'ancrage non enregistrés.")

    person_ids = list(
        connection.execute(
            text(
                """
                SELECT person_id
                FROM persons
                WHERE dataset_id = :dataset_id
                ORDER BY person_id
                """
            ),
            {"dataset_id": DATASET_ID},
        ).scalars()
    )
    trip_ids = list(
        connection.execute(
            text(
                """
                SELECT trip_id
                FROM trips
                WHERE dataset_id = :dataset_id
                ORDER BY trip_id
                """
            ),
            {"dataset_id": DATASET_ID},
        ).scalars()
    )
    expected_persons = [row["person_id"] for row in rows["persons"]]
    expected_trips = [row["trip_id"] for row in rows["trips"]]
    if person_ids != sorted(expected_persons) or len(person_ids) != len(set(person_ids)):
        raise SeedAbort(
            f"Personnes persistées {len(person_ids)}, brouillon {len(expected_persons)}."
        )
    if trip_ids != sorted(expected_trips) or len(trip_ids) != len(set(trip_ids)):
        raise SeedAbort(
            f"Trajets persistés {len(trip_ids)}, brouillon {len(expected_trips)}."
        )
    if len(person_ids) != len(rows["persons"]):
        raise SeedAbort("Le nombre de personnes ne correspond pas à --persons.")

    bounds = connection.execute(
        text(
            """
            SELECT MIN(trip_date), MAX(trip_date)
            FROM trips
            WHERE dataset_id = :dataset_id
            """
        ),
        {"dataset_id": DATASET_ID},
    ).one()
    draft_dates = [row["trip_date"] for row in rows["trips"]]
    if not draft_dates:
        raise SeedAbort("Le brouillon ne contient aucun trajet.")
    if bounds[0] != min(draft_dates) or bounds[1] != max(draft_dates):
        raise SeedAbort("Les dates min/max persistées diffèrent du brouillon.")
    horizon_end = start + timedelta(days=days)
    outside = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips
            WHERE dataset_id = :dataset_id
              AND (trip_date < :start OR trip_date >= :horizon_end)
            """
        ),
        {"dataset_id": DATASET_ID, "start": start, "horizon_end": horizon_end},
    ).scalar()
    if int(outside or 0) != 0:
        raise SeedAbort(f"{outside} trajets hors de la période demandée.")

    orphans = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips AS t
            LEFT JOIN persons AS p
              ON p.person_id = t.person_id AND p.dataset_id = t.dataset_id
            LEFT JOIN places AS origin ON origin.id = t.origin_place_id
            LEFT JOIN places AS destination ON destination.id = t.destination_place_id
            WHERE t.dataset_id = :dataset_id
              AND (p.person_id IS NULL OR origin.id IS NULL OR destination.id IS NULL)
            """
        ),
        {"dataset_id": DATASET_ID},
    ).scalar()
    if int(orphans or 0) != 0:
        raise SeedAbort(f"{orphans} trajets sans personne ou sans lieu.")

    invalid = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM trips
            WHERE dataset_id = :dataset_id
              AND (
                    source <> 'SIMULATED'
                 OR validation_status <> 'validated'
                 OR survey_id IS NOT NULL
                 OR import_batch_id IS NOT NULL
              )
            """
        ),
        {"dataset_id": DATASET_ID},
    ).scalar()
    if int(invalid or 0) != 0:
        raise SeedAbort(f"{invalid} trajets avec une source ou un statut inattendu.")
    bad_persons = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM persons
            WHERE dataset_id = :dataset_id AND source <> 'SIMULATED'
            """
        ),
        {"dataset_id": DATASET_ID},
    ).scalar()
    if int(bad_persons or 0) != 0:
        raise SeedAbort(f"{bad_persons} personnes dont la source n'est pas SIMULATED.")

    return {
        "persons": len(person_ids),
        "trips": len(trip_ids),
        "min_date": bounds[0].isoformat(),
        "max_date": bounds[1].isoformat(),
        "person_md5": _md5(person_ids),
        "trip_md5": _md5(trip_ids),
    }


def _persist(engine: Engine, rows: dict, start: date, days: int) -> dict:
    with engine.begin() as connection:
        tables = _existing_tables(connection)
        for required in ("datasets", "persons", "places", "trips", "purposes", "modes"):
            if required not in tables:
                raise SeedAbort(f"Table contractuelle absente : {required}")
        diary_before = _diary_mark(connection)
        if diary_before is None:
            raise SeedAbort(
                f"Jeu {DIARY_DATASET_ID} absent. Impossible de prouver qu'il reste intact."
            )
        reference_before = _reference(connection, tables)
        others_before = _other_datasets(connection)
        _guard_rows(connection, rows)
        _replace(connection, rows)
        verified = _verify(connection, rows, start, days)
        diary_after = _diary_mark(connection)
        reference_after = _reference(connection, tables)
        others_after = _other_datasets(connection)
        if diary_before != diary_after:
            raise SeedAbort(f"{DIARY_DATASET_ID} a changé pendant l'écriture.")
        _require_same(reference_before, reference_after, "Référence protégée")
        _require_same(others_before, others_after, "Autre jeu")
        absent = [name for name, mark in reference_before.items() if mark == "ABSENTE"]
        verified["diary"] = diary_after
        verified["absent"] = absent
        verified["reference_checked"] = [
            name for name, mark in reference_before.items() if mark != "ABSENTE"
        ]
    return verified


def _empty_days(rows: dict, persons: int, days: int) -> int:
    active = {(row["person_id"], row["trip_date"]) for row in rows["trips"]}
    return persons * days - len(active)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    print(
        "Paramètres : "
        f"personnes={args.persons} graine={args.seed} "
        f"début={args.start.isoformat()} jours={args.days}"
    )
    print(f"Jeu visé : {DATASET_ID} source={SOURCE}. Aucune écriture pour l'instant.")
    try:
        draft = generate_cohort(
            persons=args.persons,
            seed=args.seed,
            start=args.start,
            days=args.days,
        )
        validate_cohort(draft)
        rows = insertion_rows(draft)
    except ValueError as exc:
        print(f"Brouillon refusé : {exc}")
        print("Aucune transaction ouverte.")
        return 1

    empty_days = _empty_days(rows, args.persons, args.days)
    print(
        f"Brouillon validé : {len(rows['persons'])} personnes, "
        f"{len(rows['trips'])} trajets, {empty_days} journées-personnes sans déplacement."
    )
    print("Ouverture de la transaction.")
    engine = make_engine()
    try:
        verified = _persist(engine, rows, args.start, args.days)
    except SeedAbort as exc:
        print("Transaction annulée.")
        print(exc)
        return 1
    except Exception as exc:
        print("Transaction annulée.")
        print(f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        engine.dispose()

    diary_persons, diary_trips, _person_hash, _trip_hash = verified["diary"].split("|")
    print(f"Jeu : {DATASET_ID} source={SOURCE}")
    print(f"Personnes : {verified['persons']}")
    print(f"Trajets : {verified['trips']}")
    print(f"Dates des trajets présents : {verified['min_date']} → {verified['max_date']}")
    print(f"Journées-personnes sans déplacement : {empty_days}")
    print(
        "Intégrité : ok "
        f"(empreinte personnes {verified['person_md5']}, "
        f"empreinte trajets {verified['trip_md5']})"
    )
    print(
        "Non-régression : ok "
        f"({DIARY_DATASET_ID} {diary_persons} personnes, {diary_trips} trajets ; "
        f"{len(verified['reference_checked'])} mesures protégées inchangées)"
    )
    if verified["absent"]:
        print("Tables de référence absentes, non vérifiées : " + ", ".join(verified["absent"]))
    else:
        print("Tables de référence absentes : aucune")
    print("Transaction validée.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Transaction annulée : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
