# -*- coding: utf-8 -*-
"""Vérifie l'API de lecture de la cohorte simulée.

La base de travail est lue, jamais réécrite. Le jeu absent, le jeu non
simulé et la cohorte vide sont exercés sur ``mobilite_lote_api``, créée
puis supprimée par ce script. Elle ne reçoit que le contrat SQL.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_cohort_api.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from apply_sql_migration import load_env  # noqa: E402

load_env()

from fastapi import HTTPException  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import cohort as cohort_router  # noqa: E402
from app.services import cohort as cohort_service  # noqa: E402
from app.services.cohort import (  # noqa: E402
    CohortNotFound,
    CohortNotSimulated,
    CohortValidationError,
)

ISOLATED_DB = "mobilite_lote_api"
HTTP_PORT = 8765
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
START = date(2026, 10, 5)
END = date(2026, 11, 1)
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
TRIP_INDEXES = (
    "trips_dataset_date_idx",
    "trips_person_date_idx",
    "trips_origin_idx",
    "trips_destination_idx",
    "trips_mode_idx",
    "trips_purpose_idx",
)
FORBIDDEN_SQL = (
    "mobility_flows",
    "sim_trips",
    "sim_persons",
    "sim_zones",
    "roads_network",
    "mobility_zones",
    "planet_osm",
    "diary-week",
)


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.items.append(("PASS" if ok else "FAIL", label, detail))

    def counts(self) -> dict[str, int]:
        passed = sum(1 for status, _label, _detail in self.items if status == "PASS")
        failed = sum(1 for status, _label, _detail in self.items if status == "FAIL")
        return {"passed": passed, "failed": failed, "executed": passed + failed}


def q2(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def close(left, right) -> bool:
    return abs(q2(left) - q2(right)) <= Decimal("0.01")


def qident(name: str) -> str:
    if not IDENT.fullmatch(name):
        raise RuntimeError(f"Nom refusé : {name}")
    return f'"{name}"'


def engine_for(name: str) -> Engine:
    if not IDENT.fullmatch(name):
        raise RuntimeError(f"Base refusée : {name}")
    url = (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{name}"
    )
    return create_engine(url, connect_args={"client_encoding": "utf8"})


def table_exists(connection: Connection, table: str) -> bool:
    found = connection.execute(
        text("SELECT to_regclass(:name)"),
        {"name": f"public.{table}"},
    ).scalar()
    return found is not None


def fingerprint(connection: Connection) -> dict:
    marks: dict[str, str] = {
        "database": str(connection.execute(text("SELECT current_database()")).scalar())
    }
    for table in REFERENCE_TABLES:
        if not table_exists(connection, table):
            marks[table] = "ABSENTE"
            continue
        marks[table] = str(int(connection.execute(text(f"SELECT COUNT(*) FROM {qident(table)}")).scalar() or 0))
    if table_exists(connection, "mobility_flows"):
        volume = connection.execute(text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")).scalar()
        marks["mobility_flows_volume"] = str(int(volume or 0))
    else:
        marks["mobility_flows_volume"] = "ABSENTE"
    marks["places"] = str(int(connection.execute(text("SELECT COUNT(*) FROM places")).scalar() or 0))
    for dataset_id, prefix in (("diary-week", "diary"), ("sim-cohort", "cohort")):
        row = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM persons WHERE dataset_id = :dataset_id),
                    (SELECT COUNT(*) FROM trips WHERE dataset_id = :dataset_id),
                    (
                        SELECT md5(COALESCE(string_agg(person_id, ',' ORDER BY person_id), ''))
                        FROM persons WHERE dataset_id = :dataset_id
                    ),
                    (
                        SELECT md5(COALESCE(string_agg(trip_id, ',' ORDER BY trip_id), ''))
                        FROM trips WHERE dataset_id = :dataset_id
                    )
                """
            ),
            {"dataset_id": dataset_id},
        ).one()
        marks[f"{prefix}_persons"] = str(int(row[0] or 0))
        marks[f"{prefix}_trips"] = str(int(row[1] or 0))
        marks[f"{prefix}_person_md5"] = row[2] or ""
        marks[f"{prefix}_trip_md5"] = row[3] or ""
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


def independent_totals(connection: Connection, clause: str = "", params: dict | None = None) -> tuple[int, Decimal, Decimal]:
    bound = {"dataset_id": "sim-cohort", **(params or {})}
    row = connection.execute(
        text(
            f"""
            SELECT COUNT(*), COALESCE(SUM(distance_km), 0), COALESCE(SUM(duration_min), 0)
            FROM trips AS t
            WHERE t.dataset_id = :dataset_id
              AND t.source = 'SIMULATED'
              AND t.validation_status = 'validated'
              AND t.survey_id IS NULL
              AND t.import_batch_id IS NULL
              {clause}
            """
        ),
        bound,
    ).one()
    return int(row[0] or 0), Decimal(row[1]), Decimal(row[2])


def active_days(connection: Connection, start: date, end: date) -> int:
    value = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT person_id, trip_date
                FROM trips
                WHERE dataset_id = 'sim-cohort'
                  AND source = 'SIMULATED'
                  AND validation_status = 'validated'
                  AND survey_id IS NULL
                  AND import_batch_id IS NULL
                  AND trip_date >= :start
                  AND trip_date <= :end
            ) AS active_days
            """
        ),
        {"start": start, "end": end},
    ).scalar()
    return int(value or 0)


def check_routes(report: Report) -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    for path in (
        "/api/mobility/cohort/meta",
        "/api/mobility/cohort/overview",
        "/api/mobility/cohort/flows",
        "/api/mobility/cohort/trips",
        "/api/mobility/overview",
        "/api/mobility/diary",
        "/api/od/flows",
        "/api/kpi/dashboard",
    ):
        report.check(path in paths, f"route enregistrée {path}")


def check_sql_texts(report: Report) -> None:
    source = (ROOT / "app" / "repositories" / "cohort_store.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    statements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "SELECT" in node.value:
            statements.append(node.value)
    report.check(len(statements) >= 8, "requêtes SQL de lecture présentes", str(len(statements)))
    leaked = sorted({name for sql in statements for name in FORBIDDEN_SQL if name in sql})
    report.check(not leaked, "le SQL de la cohorte ne lit pas les autres sources", ",".join(leaked))


def check_reference(report: Report, connection: Connection) -> None:
    meta = cohort_service.get_meta()
    report.check(
        meta["dataset_id"] == "sim-cohort" and meta["source"] == "SIMULATED" and meta["simulated"] is True,
        "métadonnées : jeu présent et simulé",
        meta["source"],
    )
    report.check(meta["data_status"] == "simulated", "métadonnées : statut simulated explicite")
    report.check(meta["seed"] == 20261005, "métadonnées : graine lue en base", str(meta["seed"]))
    report.check(meta["anchor_monday"] == START, "métadonnées : lundi d'ancrage", str(meta["anchor_monday"]))
    report.check(meta["horizon_days"] is None, "métadonnées : durée de génération non inventée")
    report.check(meta["person_count"] == 75 and meta["trip_count"] == 3452, "métadonnées : 75 personnes et 3452 trajets", f"{meta['person_count']}/{meta['trip_count']}")
    report.check(meta["first_trip_date"] == START and meta["last_trip_date"] == END, "métadonnées : dates min/max des trajets", f"{meta['first_trip_date']} → {meta['last_trip_date']}")
    report.check("pgRouting" in meta["caveat"] and "observ" in meta["caveat"], "métadonnées : limite de distance et de statut")

    overview = cohort_service.get_overview()
    trips, distance, duration = independent_totals(connection)
    report.check(overview["trip_count"] == trips == 3452, "agrégat : nombre de trajets", str(overview["trip_count"]))
    report.check(overview["person_count"] == 75, "agrégat : nombre de personnes")
    report.check(close(overview["distance_km"], distance), "agrégat : distance totale", f"api={overview['distance_km']} sql={q2(distance)}")
    report.check(close(overview["duration_min"], duration), "agrégat : durée totale", f"api={overview['duration_min']} sql={q2(duration)}")
    report.check(
        overview["average_distance_km"] is not None
        and close(overview["average_distance_km"], distance / trips),
        "agrégat : distance moyenne",
        str(overview["average_distance_km"]),
    )
    report.check(
        overview["average_duration_min"] is not None
        and close(overview["average_duration_min"], duration / trips),
        "agrégat : durée moyenne",
        str(overview["average_duration_min"]),
    )
    report.check(overview["distance_unit"] == "km" and overview["duration_unit"] == "min", "agrégat : unités explicites")
    report.check(overview["calendar_rule"] == "stored_dates", "agrégat : pas de répétition mensuelle du journal")
    mode_sum = sum(item["trip_count"] for item in overview["by_mode"])
    purpose_sum = sum(item["trip_count"] for item in overview["by_purpose"])
    date_sum = sum(item["trip_count"] for item in overview["by_date"])
    report.check(mode_sum == trips and purpose_sum == trips and date_sum == trips, "répartitions : les effectifs retombent sur le total", f"{mode_sum}/{purpose_sum}/{date_sum}")
    report.check(all(item["label"] and item["mode_code"] for item in overview["by_mode"]), "répartition par mode avec libellé")
    report.check(all(item["label"] and item["purpose_code"] for item in overview["by_purpose"]), "répartition par motif avec libellé")
    calendar_days = (END - START).days + 1
    active = active_days(connection, START, END)
    expected_empty = 75 * calendar_days - active
    report.check(calendar_days == 28 and expected_empty == 516, "journées vides de référence : 75 × 28 − actives = 516", f"actives={active} vides={expected_empty}")
    report.check(overview["empty_person_days"] == expected_empty, "journées vides calculées par le calendrier", str(overview["empty_person_days"]))
    report.check(overview["active_person_days"] == active, "journées actives distinctes", str(overview["active_person_days"]))
    report.check(overview["period"]["period_source"] == "stored_trip_dates", "période par défaut = dates stockées")

    partial = min(overview["by_mode"], key=lambda item: item["trip_count"])
    filtered = cohort_service.get_overview(mode=partial["mode_code"])
    mode_trips, mode_distance, _mode_duration = independent_totals(
        connection,
        "AND t.mode_code = :mode_code",
        {"mode_code": partial["mode_code"]},
    )
    report.check(filtered["trip_count"] == mode_trips == partial["trip_count"], "filtre mode : effectif", f"{filtered['trip_count']} contre {mode_trips}")
    report.check(close(filtered["distance_km"], mode_distance), "filtre mode : distance")
    report.check(filtered["empty_person_days"] == expected_empty, "filtre mode : les journées vides ne changent pas")
    report.check(filtered["trip_count"] < trips, "filtre mode : sous-ensemble strict")

    one_day = cohort_service.get_overview(date_from=START, date_to=START)
    day_trips, day_distance, day_duration = independent_totals(
        connection,
        "AND t.trip_date = :trip_date",
        {"trip_date": START},
    )
    day_active = active_days(connection, START, START)
    report.check(one_day["trip_count"] == day_trips and one_day["trip_count"] < trips, "filtre période : une journée", str(one_day["trip_count"]))
    report.check(close(one_day["distance_km"], day_distance) and close(one_day["duration_min"], day_duration), "filtre période : totaux du jour")
    report.check(one_day["period"]["calendar_days"] == 1, "filtre période : un jour de calendrier")
    report.check(one_day["empty_person_days"] == 75 - day_active, "filtre période : journées vides du jour", str(one_day["empty_person_days"]))

    vacant = cohort_service.get_overview(date_from=date(2020, 1, 1), date_to=date(2020, 1, 2))
    report.check(vacant["trip_count"] == 0 and vacant["by_mode"] == [] and vacant["by_date"] == [], "période vide : aucun trajet")
    report.check(vacant["average_distance_km"] is None and vacant["average_duration_min"] is None, "période vide : pas de division par zéro")
    report.check(vacant["distance_km"] == 0 and vacant["duration_min"] == 0, "période vide : totaux nuls")
    report.check(vacant["empty_person_days"] == 150 and vacant["person_count"] == 75, "période vide : 75 × 2 journées sans trajet", str(vacant["empty_person_days"]))

    outside = cohort_service.get_overview(date_from=date(2026, 12, 1))
    report.check(outside["period"]["calendar_days"] == 0 and outside["trip_count"] == 0, "borne après le dernier trajet : fenêtre vide")
    report.check(outside["empty_person_days"] == 0 and outside["average_distance_km"] is None, "fenêtre vide : moyennes nulles")

    flows = collect_flows()
    flow_trips = sum(item["trip_count"] for item in flows)
    report.check(flow_trips == trips, "flux : la somme des trajets égale l'agrégat", f"{flow_trips}/{trips}")
    report.check(all(item["origin_name"] and item["destination_name"] for item in flows), "flux : lieux résolus")
    names = {
        row[0]: row[1]
        for row in connection.execute(text("SELECT id, name FROM places")).all()
    }
    resolved = all(names.get(item["origin_place_id"]) == item["origin_name"] and names.get(item["destination_place_id"]) == item["destination_name"] for item in flows)
    report.check(resolved, "flux : noms identiques à places")
    report.check(all("person_id" not in item and "trip_id" not in item for item in flows), "flux : pas d'étape individuelle")
    bus_flows = collect_flows(mode=partial["mode_code"])
    report.check(sum(item["trip_count"] for item in bus_flows) == mode_trips, "flux filtrés par mode")
    purpose = overview["by_purpose"][0]["purpose_code"]
    purpose_trips, _purpose_distance, _purpose_duration = independent_totals(
        connection,
        "AND t.purpose_code = :purpose_code",
        {"purpose_code": purpose},
    )
    purpose_flows = collect_flows(purpose=purpose, date_from=START, date_to=END)
    report.check(sum(item["trip_count"] for item in purpose_flows) == purpose_trips, "flux filtrés par motif et par dates", str(purpose_trips))

    sample = connection.execute(
        text(
            """
            SELECT trip_id, person_id, trip_date, origin_place_id, destination_place_id,
                   purpose_code, mode_code
            FROM trips
            WHERE dataset_id = 'sim-cohort' AND source = 'SIMULATED'
            ORDER BY trip_id
            LIMIT 1
            """
        )
    ).mappings().one()
    origin_flows = cohort_service.get_flows(origin_id=sample["origin_place_id"], destination_id=sample["destination_place_id"], limit=500)
    report.check(
        origin_flows["pair_count"] >= 1
        and all(
            item["origin_place_id"] == sample["origin_place_id"]
            and item["destination_place_id"] == sample["destination_place_id"]
            for item in origin_flows["flows"]
        ),
        "flux filtrés par origine et destination",
    )

    page = cohort_service.get_trips(limit=50)
    report.check(page["limit"] == 50 and page["returned"] == 50 and page["total"] == 3452, "trajets : page par défaut bornée", f"{page['returned']}/{page['total']}")
    hidden = {"display_name", "detail", "activity", "age", "blurb", "home_place_id"}
    report.check(all(hidden.isdisjoint(trip) for trip in page["trips"]), "trajets : pas de nom ni de texte libre")
    report.check(all(trip["source"] == "SIMULATED" and trip["trip_id"].startswith("cohort-") for trip in page["trips"]), "trajets : uniquement sim-cohort")
    left = cohort_service.get_trips(limit=2, offset=0)
    right = cohort_service.get_trips(limit=2, offset=2)
    left_ids = {trip["trip_id"] for trip in left["trips"]}
    right_ids = {trip["trip_id"] for trip in right["trips"]}
    report.check(len(left_ids) == 2 and left_ids.isdisjoint(right_ids) and left["total"] == right["total"] == 3452, "trajets : pagination sans recouvrement")
    tail = cohort_service.get_trips(limit=2, offset=3452)
    report.check(tail["returned"] == 0 and tail["total"] == 3452, "trajets : offset au-delà du total")

    combined = cohort_service.get_trips(
        date_from=sample["trip_date"],
        date_to=sample["trip_date"],
        person_id=sample["person_id"],
        mode=sample["mode_code"],
        purpose=sample["purpose_code"],
        origin_id=sample["origin_place_id"],
        destination_id=sample["destination_place_id"],
        limit=100,
    )
    combined_ok = (
        combined["total"] >= 1
        and sample["trip_id"] in {trip["trip_id"] for trip in combined["trips"]}
        and all(
            trip["person_id"] == sample["person_id"]
            and trip["trip_date"] == sample["trip_date"]
            and trip["mode_code"] == sample["mode_code"]
            and trip["purpose_code"] == sample["purpose_code"]
            and trip["origin_place_id"] == sample["origin_place_id"]
            and trip["destination_place_id"] == sample["destination_place_id"]
            and trip["source"] == "SIMULATED"
            for trip in combined["trips"]
        )
    )
    report.check(combined_ok, "trajets : filtres combinés", f"total={combined['total']}")

    for limit, offset, label in ((0, 0, "limite nulle"), (101, 0, "limite au-dessus de 100"), (10, -1, "offset négatif")):
        try:
            cohort_service.get_trips(limit=limit, offset=offset)
            report.check(False, f"trajets : {label} refusée", "aucun rejet")
        except CohortValidationError as exc:
            report.check(True, f"trajets : {label} refusée", str(exc))
    try:
        cohort_service.get_trips(date_from=END, date_to=START)
        report.check(False, "trajets : période inversée refusée")
    except CohortValidationError:
        report.check(True, "trajets : période inversée refusée")
    try:
        cohort_service.get_trips(mode="bus' OR '1'='1")
        report.check(False, "trajets : mode injecté refusé")
    except CohortValidationError:
        report.check(True, "trajets : mode injecté refusé")
    try:
        cohort_service.get_trips(person_id="hery")
        report.check(False, "trajets : personne du journal refusée")
    except CohortValidationError as exc:
        report.check("diary-week" in str(exc), "trajets : personne du journal refusée", str(exc))
    try:
        cohort_service.get_flows(origin_id="lieu-inexistant")
        report.check(False, "flux : lieu inconnu refusé")
    except CohortValidationError:
        report.check(True, "flux : lieu inconnu refusé")

    indexes = set(connection.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'trips'")).scalars().all())
    missing = [name for name in TRIP_INDEXES if name not in indexes]
    report.check(not missing, "index de trips déjà présents, aucune migration ajoutée", ",".join(missing))


def collect_flows(**filters) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = cohort_service.get_flows(limit=500, offset=offset, **filters)
        rows.extend(page["flows"])
        if len(rows) >= page["pair_count"] or page["returned"] == 0:
            break
        offset += 500
    return rows


def check_guards(report: Report) -> None:
    try:
        cohort_service.assert_simulated(None)
        report.check(False, "jeu absent : exception")
    except CohortNotFound:
        report.check(True, "jeu absent : exception")
    try:
        cohort_service.assert_simulated({"id": "sim-cohort", "source": "OBSERVED"})
        report.check(False, "source OBSERVED : exception")
    except CohortNotSimulated:
        report.check(True, "source OBSERVED : exception")

    original = cohort_router.cohort_service.get_meta

    def raise_not_found():
        raise CohortNotFound("absent")

    def raise_not_simulated():
        raise CohortNotSimulated("observe")

    try:
        cohort_router.cohort_service.get_meta = raise_not_found
        try:
            cohort_router.cohort_meta()
            report.check(False, "route meta : 404 si le jeu est absent")
        except HTTPException as exc:
            report.check(exc.status_code == 404, "route meta : 404 si le jeu est absent", str(exc.status_code))
        cohort_router.cohort_service.get_meta = raise_not_simulated
        try:
            cohort_router.cohort_meta()
            report.check(False, "route meta : 409 si la source n'est pas SIMULATED")
        except HTTPException as exc:
            report.check(exc.status_code == 409, "route meta : 409 si la source n'est pas SIMULATED", str(exc.status_code))
    finally:
        cohort_router.cohort_service.get_meta = original


def drop_isolated(admin: Engine, working: str) -> None:
    if ISOLATED_DB == working:
        raise RuntimeError("Refus de supprimer la base de travail.")
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
    if ISOLATED_DB == working:
        raise RuntimeError("Refus de créer la base isolée sous le nom de travail.")
    drop_isolated(admin, working)
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"CREATE DATABASE {qident(ISOLATED_DB)}"))


def apply_contract(isolated: Engine) -> None:
    script = (ROOT / "scripts" / "sql" / "30_mobility_contract.sql").read_text(encoding="utf-8")
    with isolated.begin() as connection:
        connection.exec_driver_sql(script)


def check_isolated(report: Report, working_name: str) -> None:
    admin = engine_for("postgres")
    isolated: Engine | None = None
    try:
        create_isolated(admin, working_name)
        isolated = engine_for(ISOLATED_DB)
        apply_contract(isolated)
        with isolated.connect() as connection:
            located = connection.execute(text("SELECT current_database()")).scalar()
            present = connection.execute(
                text("SELECT COUNT(*) FROM datasets WHERE id = 'sim-cohort'")
            ).scalar()
        report.check(located == ISOLATED_DB and int(present or 0) == 0, "base isolée sans sim-cohort", str(located))
        try:
            cohort_service.get_meta(db=isolated)
            report.check(False, "SQL : jeu absent")
        except CohortNotFound:
            report.check(True, "SQL : jeu absent")
        with isolated.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO datasets (id, source, label, seed, anchor_monday)
                    VALUES ('sim-cohort', 'OBSERVED', 'Ligne de test isolée', NULL, NULL)
                    """
                )
            )
        try:
            cohort_service.get_overview(db=isolated)
            report.check(False, "SQL : source OBSERVED refusée")
        except CohortNotSimulated:
            report.check(True, "SQL : source OBSERVED refusée")
        with isolated.begin() as connection:
            connection.execute(text("DELETE FROM datasets WHERE id = 'sim-cohort'"))
            connection.execute(
                text(
                    """
                    INSERT INTO datasets (id, source, label, seed, anchor_monday)
                    VALUES ('sim-cohort', 'SIMULATED', 'Cohorte vide de test API', 1, DATE '2026-10-05')
                    """
                )
            )
        empty = cohort_service.get_meta(db=isolated)
        report.check(
            empty["person_count"] == 0 and empty["trip_count"] == 0 and empty["first_trip_date"] is None,
            "SQL : cohorte vide",
            f"{empty['person_count']}/{empty['trip_count']}",
        )
        bare = cohort_service.get_overview(db=isolated)
        report.check(
            bare["trip_count"] == 0
            and bare["average_distance_km"] is None
            and bare["empty_person_days"] is None,
            "SQL : calendrier indéterminé sans trajet ni période",
        )
        asked = cohort_service.get_overview(
            date_from=date(2026, 10, 5),
            date_to=date(2026, 10, 6),
            db=isolated,
        )
        report.check(
            asked["empty_person_days"] == 0 and asked["average_duration_min"] is None and asked["trip_count"] == 0,
            "SQL : période demandée sans personne et sans trajet",
        )
        listed = cohort_service.get_trips(db=isolated, limit=10)
        report.check(listed["total"] == 0 and listed["returned"] == 0, "SQL : page de trajets vide")
    finally:
        if isolated is not None:
            isolated.dispose()
        drop_isolated(admin, working_name)
        admin.dispose()


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def fetch(port: int, path: str) -> tuple[int, dict | list | str]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def wait_health(port: int, proc: subprocess.Popen[str]) -> bool:
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            code, payload = fetch(port, "/health")
        except Exception:
            time.sleep(0.3)
            continue
        if code == 200 and isinstance(payload, dict) and payload.get("status") == "ok":
            return True
        time.sleep(0.3)
    return False


def stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def remove_log(path: Path) -> None:
    last_error: PermissionError | None = None
    for _attempt in range(20):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.25)
    if last_error is not None:
        raise last_error


def check_http(report: Report) -> None:
    if not port_is_free(HTTP_PORT):
        report.check(False, "HTTP : port de test libre", str(HTTP_PORT))
        return
    log_path = ROOT / "scripts" / "_cohort_api_uvicorn.log"
    log_handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(HTTP_PORT)],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    try:
        ready = wait_health(HTTP_PORT, proc)
        report.check(ready, "HTTP : serveur de test démarré", str(HTTP_PORT))
        if not ready:
            return
        code, meta = fetch(HTTP_PORT, "/api/mobility/cohort/meta")
        report.check(
            code == 200 and isinstance(meta, dict) and meta.get("person_count") == 75 and meta.get("trip_count") == 3452,
            "HTTP meta",
            f"code={code}",
        )
        code, overview = fetch(HTTP_PORT, "/api/mobility/cohort/overview")
        report.check(
            code == 200 and isinstance(overview, dict) and overview.get("empty_person_days") == 516,
            "HTTP overview",
            f"code={code}",
        )
        code, flows = fetch(HTTP_PORT, "/api/mobility/cohort/flows?limit=1")
        report.check(
            code == 200 and isinstance(flows, dict) and flows.get("returned") == 1 and flows.get("simulated") is True,
            "HTTP flows",
            f"code={code}",
        )
        code, trips = fetch(HTTP_PORT, "/api/mobility/cohort/trips?limit=1")
        trip_ok = (
            code == 200
            and isinstance(trips, dict)
            and trips.get("returned") == 1
            and "display_name" not in trips["trips"][0]
        )
        report.check(trip_ok, "HTTP trips", f"code={code}")
        code, _payload = fetch(HTTP_PORT, "/api/mobility/cohort/trips?limit=101")
        report.check(code == 422, "HTTP : limite 101 refusée", str(code))
        code, _payload = fetch(HTTP_PORT, "/api/mobility/cohort/trips?limit=0")
        report.check(code == 422, "HTTP : limite 0 refusée", str(code))
        code, _payload = fetch(HTTP_PORT, "/api/mobility/cohort/trips?date_from=pas-une-date")
        report.check(code == 422, "HTTP : date illisible refusée", str(code))
        code, _payload = fetch(HTTP_PORT, "/api/mobility/cohort/trips?date_from=2026-11-02&date_to=2026-10-01")
        report.check(code == 400, "HTTP : période inversée refusée", str(code))
        code, _payload = fetch(HTTP_PORT, "/api/mobility/cohort/trips?person_id=hery")
        report.check(code == 400, "HTTP : personne hors cohorte refusée", str(code))
        code, spec = fetch(HTTP_PORT, "/openapi.json")
        encoded = json.dumps(spec) if isinstance(spec, dict) else ""
        documented = (
            code == 200
            and "/api/mobility/cohort/meta" in encoded
            and "/api/mobility/cohort/overview" in encoded
            and "/api/mobility/cohort/flows" in encoded
            and "/api/mobility/cohort/trips" in encoded
            and "/api/od/flows" in encoded
        )
        report.check(documented, "OpenAPI documente la cohorte sans retirer les flux OD", str(code))
    finally:
        stop_process(proc)
        log_handle.close()
        remove_log(log_path)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    report = Report()
    with engine.connect() as connection:
        before = fingerprint(connection)
        working = before["database"]
    print(f"Base de travail : {working}. Lecture seule.", flush=True)
    check_routes(report)
    check_sql_texts(report)
    check_guards(report)
    with engine.connect() as connection:
        check_reference(report, connection)
    print(f"Création de la base isolée {ISOLATED_DB}.", flush=True)
    check_isolated(report, working)
    check_http(report)
    with engine.connect() as connection:
        after = fingerprint(connection)
    changed = [key for key in before if before[key] != after.get(key)]
    report.check(not changed, "empreintes protégées inchangées", ",".join(changed))
    report.check(after.get("diary_persons") == "8" and after.get("diary_trips") == "130", "diary-week : 8 personnes et 130 trajets", f"{after.get('diary_persons')}/{after.get('diary_trips')}")
    report.check(after.get("cohort_persons") == "75" and after.get("cohort_trips") == "3452", "sim-cohort : 75 personnes et 3452 trajets", f"{after.get('cohort_persons')}/{after.get('cohort_trips')}")
    report.check(after.get("places") == "66", "places : 66 lieux", str(after.get("places")))
    report.check(after.get("observed_rows") == "0", "aucune ligne OBSERVED", str(after.get("observed_rows")))

    counts = report.counts()
    print("")
    for status, label, detail in report.items:
        suffix = f" — {detail}" if detail else ""
        print(f"{status} {label}{suffix}")
    print("")
    print(f"Résultat : {counts['passed']}/{counts['executed']} PASS, {counts['failed']} FAIL")
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        engine.dispose()
