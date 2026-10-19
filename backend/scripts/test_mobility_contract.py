# -*- coding: utf-8 -*-
"""Vérifie la migration 30 sur la base pointée par backend/.env.

Deux applications, tables déjà peuplées inchangées, contraintes, rejets,
sources SIMULATED / OBSERVED. Les lignes de test sont annulées.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_mobility_contract.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply_sql_migration import (  # noqa: E402
    SQL_DIR,
    apply_migration,
    execute_sql_script,
    load_env,
    make_engine,
)

VERSION = "30_mobility_contract"
PROTECTED = (
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
    "cities",
    "arrondissements",
    "quartiers",
    "zones",
    "organizations",
    "employee_groups",
    "od_matrix",
    "data_sources",
    "ref_modes",
    "ref_purposes",
    "ref_periods",
    "ref_sectors",
    "app_active_city",
)

EXPECTED_INDEXES = {
    "places_city_level_idx",
    "places_parent_idx",
    "persons_dataset_idx",
    "persons_home_idx",
    "surveys_dataset_idx",
    "import_batches_survey_idx",
    "import_batches_dataset_idx",
    "import_rows_batch_idx",
    "trips_dataset_date_idx",
    "trips_person_date_idx",
    "trips_origin_idx",
    "trips_destination_idx",
    "trips_purpose_idx",
    "trips_mode_idx",
    "trips_survey_idx",
    "trips_import_batch_idx",
}

EXPECTED_CONSTRAINTS = {
    "datasets_source_check",
    "datasets_anchor_monday_check",
    "datasets_id_source_unique",
    "places_level_check",
    "places_role_check",
    "places_boundary_kind_check",
    "places_level_parent_check",
    "places_parent_fkey",
    "places_city_fkey",
    "persons_source_check",
    "persons_dataset_source_fkey",
    "purposes_pkey",
    "modes_pkey",
    "trips_source_check",
    "trips_validation_status_check",
    "trips_observed_provenance_check",
    "trips_distinct_places_check",
    "trips_dataset_source_fkey",
    "trips_person_dataset_fkey",
    "trips_purpose_fkey",
    "trips_mode_fkey",
    "trips_survey_fkey",
    "trips_import_batch_fkey",
    "surveys_status_check",
    "import_batches_source_check",
    "import_batches_status_check",
    "import_rows_batch_fkey",
    "import_rows_batch_row_unique",
}

PURPOSES = {
    "travail": "Travail",
    "retour_domicile": "Retour au domicile",
    "courses_supermarche": "Courses au supermarché",
    "courses_marche": "Courses au marché",
    "courses": "Courses",
    "ecole": "École",
    "sante": "Santé",
    "loisirs": "Loisirs",
    "culte": "Culte",
    "visite": "Visite",
    "autre": "Autre",
    "deplacement_professionnel": "Déplacement professionnel",
    "service_public": "Service public",
}

MODES = {
    "marche": "Marche",
    "velo": "Vélo",
    "bus": "Bus",
    "voiture": "Voiture",
    "taxi": "Taxi",
}

FORBIDDEN_TRIP_TARGETS = {"mobility_zones", "mobility_flows", "zones", "sim_trips", "sim_zones"}


def _columns(connection) -> dict[str, tuple[str, ...]]:
    rows = connection.execute(
        text(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
    ).fetchall()
    grouped: dict[str, list[str]] = {}
    for table_name, column_name, data_type in rows:
        if table_name in PROTECTED:
            grouped.setdefault(table_name, []).append(f"{column_name}:{data_type}")
    return {name: tuple(columns) for name, columns in grouped.items()}


def _counts(connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in PROTECTED:
        counts[table] = int(
            connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
        )
    return counts


def _flow_volume(connection) -> int:
    value = connection.execute(
        text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")
    ).scalar()
    return int(value)


def _desire_lines(connection) -> int:
    return int(connection.execute(text("SELECT COUNT(*) FROM v_od_desire_lines")).scalar())


def _names(connection, sql: str) -> set[str]:
    return {str(row[0]) for row in connection.execute(text(sql))}


def _expect_reject(connection, statement: str, params: dict) -> bool:
    try:
        with connection.begin_nested():
            connection.execute(text(statement), params)
    except IntegrityError:
        return True
    return False


def _run_constraint_cases(connection) -> list[str]:
    failures: list[str] = []
    connection.execute(
        text(
            """
            INSERT INTO places
                (id, parent_id, city_id, name, level, role, lon, lat)
            VALUES
                (:id, NULL, :id, 'Ville test contrat', 'city', 'ville', 47.5, -18.9)
            """
        ),
        {"id": "__contract_test_city"},
    )
    connection.execute(
        text(
            """
            INSERT INTO places
                (id, parent_id, city_id, name, level, role, lon, lat)
            VALUES
                (:id, :parent, :city, 'Quartier test contrat', 'quartier', 'habitat', 47.51, -18.91)
            """
        ),
        {
            "id": "__contract_test_q",
            "parent": "__contract_test_city",
            "city": "__contract_test_city",
        },
    )
    connection.execute(
        text(
            """
            INSERT INTO datasets (id, source, label, seed, anchor_monday)
            VALUES (:id, 'SIMULATED', 'Jeu de test du contrat', 30, DATE '2026-10-05')
            """
        ),
        {"id": "__contract_test_sim"},
    )
    connection.execute(
        text(
            """
            INSERT INTO persons
                (person_id, dataset_id, city_id, home_place_id, activity, source)
            VALUES
                (:person, :dataset, :city, :home, 'activite de test', 'SIMULATED')
            """
        ),
        {
            "person": "__contract_test_person",
            "dataset": "__contract_test_sim",
            "city": "__contract_test_city",
            "home": "__contract_test_q",
        },
    )
    trip = {
        "trip_id": "__contract_test_trip",
        "dataset_id": "__contract_test_sim",
        "person_id": "__contract_test_person",
        "origin": "__contract_test_q",
        "destination": "__contract_test_city",
        "purpose": "travail",
        "mode": "bus",
        "source": "SIMULATED",
        "status": "validated",
        "survey_id": None,
        "batch_id": None,
        "distance": 3.2,
    }
    insert_trip = """
        INSERT INTO trips (
            trip_id, dataset_id, person_id, trip_date, depart_time, arrive_time,
            origin_place_id, destination_place_id, purpose_code, mode_code,
            distance_km, duration_min, source, validation_status, survey_id, import_batch_id
        ) VALUES (
            :trip_id, :dataset_id, :person_id, DATE '2026-10-05', TIME '07:00', TIME '07:30',
            :origin, :destination, :purpose, :mode,
            :distance, 30, :source, :status, :survey_id, :batch_id
        )
    """
    connection.execute(text(insert_trip), trip)

    rejected = {
        "source inconnue": {**trip, "trip_id": "__contract_test_bad_source", "source": "REAL"},
        "statut inconnu": {**trip, "trip_id": "__contract_test_bad_status", "status": "published"},
        "motif hors contrat": {**trip, "trip_id": "__contract_test_bad_purpose", "purpose": "domicile"},
        "distance negative": {**trip, "trip_id": "__contract_test_bad_distance", "distance": -1},
        "meme lieu": {
            **trip,
            "trip_id": "__contract_test_same_place",
            "destination": "__contract_test_q",
        },
    }
    for label, params in rejected.items():
        if not _expect_reject(connection, insert_trip, params):
            failures.append(f"insertion acceptée à tort : {label}")

    if not _expect_reject(
        connection,
        """
        INSERT INTO datasets (id, source, label, anchor_monday)
        VALUES ('__contract_test_tuesday', 'SIMULATED', 'Mauvais lundi', DATE '2026-10-06')
        """,
        {},
    ):
        failures.append("lundi d'ancrage un mardi accepté à tort")

    connection.execute(
        text(
            """
            INSERT INTO datasets (id, source, label)
            VALUES ('__contract_test_obs', 'OBSERVED', 'Enquete de test')
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO persons
                (person_id, dataset_id, city_id, home_place_id, activity, source)
            VALUES
                ('__contract_test_obs_person', '__contract_test_obs',
                 '__contract_test_city', '__contract_test_q', 'activite de test', 'OBSERVED')
            """
        )
    )
    observed = {
        **trip,
        "trip_id": "__contract_test_observed",
        "dataset_id": "__contract_test_obs",
        "person_id": "__contract_test_obs_person",
        "source": "OBSERVED",
        "survey_id": None,
        "batch_id": None,
    }
    if not _expect_reject(connection, insert_trip, observed):
        failures.append("OBSERVED sans enquête ni import accepté à tort")

    mixed = {**trip, "trip_id": "__contract_test_mixed", "source": "OBSERVED"}
    if not _expect_reject(connection, insert_trip, mixed):
        failures.append("trip OBSERVED dans un jeu SIMULATED accepté à tort")

    connection.execute(
        text(
            """
            INSERT INTO surveys (id, dataset_id, title, validation_status)
            VALUES ('__contract_test_survey', '__contract_test_obs', 'Questionnaire test', 'draft')
            """
        )
    )
    observed_ok = {**observed, "trip_id": "__contract_test_observed_ok", "survey_id": "__contract_test_survey"}
    connection.execute(text(insert_trip), observed_ok)

    if not _expect_reject(
        connection,
        """
        INSERT INTO import_batches (source, status)
        VALUES ('OBSERVED', 'loaded')
        """,
        {},
    ):
        failures.append("statut d'import hors contrat accepté à tort")

    return failures


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    engine = make_engine()
    results: list[str] = []

    def record(ok: bool, label: str, detail: str = "") -> None:
        suffix = f" — {detail}" if detail else ""
        results.append(f"{'PASS' if ok else 'FAIL'} {label}{suffix}")

    try:
        with engine.connect() as connection:
            before_counts = _counts(connection)
            before_columns = _columns(connection)
            before_volume = _flow_volume(connection)
            before_lines = _desire_lines(connection)

        first = apply_migration(VERSION, engine)
        second = apply_migration(VERSION, engine)
        record(first["status"] in {"applied", "skipped"}, "première application", str(first["status"]))
        record(second["status"] == "skipped", "seconde application ignorée", str(second["status"]))
        record(first["checksum"] == second["checksum"], "même empreinte", str(second["checksum"]))

        script = (SQL_DIR / "30_mobility_contract.sql").read_text(encoding="utf-8")
        with engine.begin() as connection:
            execute_sql_script(connection, script)

        with engine.connect() as connection:
            after_counts = _counts(connection)
            after_columns = _columns(connection)
            after_volume = _flow_volume(connection)
            after_lines = _desire_lines(connection)
            versions = connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM schema_migrations
                    WHERE version = :version
                    """
                ),
                {"version": VERSION},
            ).scalar()
            purpose_rows = connection.execute(
                text("SELECT code, label_fr FROM purposes ORDER BY code")
            ).fetchall()
            mode_rows = connection.execute(
                text("SELECT code, label_fr FROM modes ORDER BY code")
            ).fetchall()
            indexes = _names(
                connection,
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename IN (
                    'places', 'persons', 'trips', 'surveys',
                    'import_batches', 'import_rows'
                  )
                """,
            )
            constraints = _names(
                connection,
                """
                SELECT c.conname
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public'
                  AND t.relname IN (
                    'datasets', 'places', 'persons', 'purposes', 'modes',
                    'trips', 'surveys', 'import_batches', 'import_rows'
                  )
                """,
            )
            trip_targets = _names(
                connection,
                """
                SELECT ft.relname
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_class ft ON ft.oid = c.confrelid
                WHERE c.contype = 'f' AND t.relname = 'trips'
                """,
            )
            observed = connection.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM datasets WHERE source = 'OBSERVED')
                      + (SELECT COUNT(*) FROM persons WHERE source = 'OBSERVED')
                      + (SELECT COUNT(*) FROM trips WHERE source = 'OBSERVED')
                      + (SELECT COUNT(*) FROM import_batches WHERE source = 'OBSERVED')
                    """
                )
            ).scalar()
            empty_facts = connection.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM trips)
                      + (SELECT COUNT(*) FROM persons)
                      + (SELECT COUNT(*) FROM places)
                      + (SELECT COUNT(*) FROM datasets)
                      + (SELECT COUNT(*) FROM surveys)
                      + (SELECT COUNT(*) FROM import_batches)
                    """
                )
            ).scalar()

            changed = [name for name in PROTECTED if before_counts[name] != after_counts[name]]
            record(not changed, "comptages des tables existantes", "inchangés" if not changed else ", ".join(changed))
            record(before_columns == after_columns, "colonnes des tables existantes")
            record(before_volume == after_volume, "volume mobility_flows", str(after_volume))
            record(before_lines == after_lines, "lignes v_od_desire_lines", str(after_lines))
            record(int(versions) == 1, "une seule ligne de version", str(versions))
            record(dict(purpose_rows) == PURPOSES, "motifs canoniques", f"{len(purpose_rows)} lignes")
            record(dict(mode_rows) == MODES, "modes canoniques", f"{len(mode_rows)} lignes")
            missing_indexes = EXPECTED_INDEXES - indexes
            missing_constraints = EXPECTED_CONSTRAINTS - constraints
            record(not missing_indexes, "index attendus", "ok" if not missing_indexes else ", ".join(sorted(missing_indexes)))
            record(
                not missing_constraints,
                "contraintes attendues",
                "ok" if not missing_constraints else ", ".join(sorted(missing_constraints)),
            )
            linked = FORBIDDEN_TRIP_TARGETS & trip_targets
            record(not linked, "trips sans clé vers les zones recréées", "ok" if not linked else ", ".join(sorted(linked)))
            record(int(observed) == 0, "aucune ligne OBSERVED engagée", str(observed))
            record(int(empty_facts) == 0, "aucun déplacement de démonstration chargé", str(empty_facts))

        with engine.connect() as connection:
            outer = connection.begin()
            try:
                case_failures = _run_constraint_cases(connection)
            finally:
                outer.rollback()
        record(not case_failures, "insertions invalides rejetées", "ok" if not case_failures else "; ".join(case_failures))

        with engine.connect() as connection:
            still_empty = connection.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM trips)
                      + (SELECT COUNT(*) FROM persons WHERE starts_with(person_id, '__contract_test_'))
                      + (SELECT COUNT(*) FROM datasets WHERE starts_with(id, '__contract_test_'))
                      + (SELECT COUNT(*) FROM places WHERE starts_with(id, '__contract_test_'))
                    """
                )
            ).scalar()
            still_observed = connection.execute(
                text("SELECT COUNT(*) FROM trips WHERE source = 'OBSERVED'")
            ).scalar()
        record(int(still_empty) == 0, "lignes de test annulées", str(still_empty))
        record(int(still_observed) == 0, "les tests n'ont pas laissé d'observation", str(still_observed))
    finally:
        engine.dispose()

    print("\n".join(results))
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
