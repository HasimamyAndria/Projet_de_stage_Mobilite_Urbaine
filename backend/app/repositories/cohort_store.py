"""Lecture SQL de la cohorte simulée.

Seules les tables du contrat sont lues : datasets, persons, trips, places,
purposes, modes. Aucune requête ne touche mobility_flows, sim_trips,
roads_network, mobility_zones ni les tables OSM.

Les valeurs viennent de paramètres liés. Les agrégations restent dans
PostgreSQL. Les index déjà présents sur trips suffisent pour ce volume :
trips_dataset_date_idx, trips_person_date_idx, trips_origin_idx,
trips_destination_idx, trips_mode_idx, trips_purpose_idx.
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Connection

DATASET_ID = "sim-cohort"
SOURCE = "SIMULATED"

# Étapes publiables du jeu. Le filtre de source est redondant avec la clé
# étrangère (dataset_id, source), et il est écrit quand même.
_TRIP_GUARD = """
    t.dataset_id = :dataset_id
    AND t.source = :source
    AND t.validation_status = 'validated'
    AND t.survey_id IS NULL
    AND t.import_batch_id IS NULL
"""


def _base_params() -> dict:
    return {"dataset_id": DATASET_ID, "source": SOURCE}


def _attribute_clause(filters: dict, params: dict) -> str:
    parts: list[str] = []
    if filters.get("date_from") is not None:
        parts.append("t.trip_date >= :date_from")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to") is not None:
        parts.append("t.trip_date <= :date_to")
        params["date_to"] = filters["date_to"]
    if filters.get("mode_code"):
        parts.append("t.mode_code = :mode_code")
        params["mode_code"] = filters["mode_code"]
    if filters.get("purpose_code"):
        parts.append("t.purpose_code = :purpose_code")
        params["purpose_code"] = filters["purpose_code"]
    if filters.get("origin_place_id"):
        parts.append("t.origin_place_id = :origin_place_id")
        params["origin_place_id"] = filters["origin_place_id"]
    if filters.get("destination_place_id"):
        parts.append("t.destination_place_id = :destination_place_id")
        params["destination_place_id"] = filters["destination_place_id"]
    if filters.get("person_id"):
        parts.append("t.person_id = :person_id")
        params["person_id"] = filters["person_id"]
    if not parts:
        return ""
    return " AND " + " AND ".join(parts)


def fetch_dataset(connection: Connection) -> dict | None:
    row = connection.execute(
        text(
            """
            SELECT id, source, label, seed, anchor_monday
            FROM datasets
            WHERE id = :dataset_id
            """
        ),
        _base_params(),
    ).mappings().first()
    return None if row is None else dict(row)


def count_persons(connection: Connection) -> int:
    value = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM persons
            WHERE dataset_id = :dataset_id
              AND source = :source
            """
        ),
        _base_params(),
    ).scalar()
    return int(value or 0)


def trip_bounds(connection: Connection) -> tuple[date | None, date | None, int]:
    row = connection.execute(
        text(
            f"""
            SELECT MIN(t.trip_date), MAX(t.trip_date), COUNT(*)
            FROM trips AS t
            WHERE {_TRIP_GUARD}
            """
        ),
        _base_params(),
    ).one()
    return row[0], row[1], int(row[2] or 0)


def label_map(connection: Connection, kind: str) -> dict[str, str]:
    if kind not in {"modes", "purposes"}:
        raise ValueError(f"Référentiel refusé : {kind}")
    rows = connection.execute(text(f"SELECT code, label_fr FROM {kind}")).all()
    return {code: label for code, label in rows}


def mode_exists(connection: Connection, code: str) -> bool:
    found = connection.execute(
        text("SELECT 1 FROM modes WHERE code = :code"),
        {"code": code},
    ).scalar()
    return found is not None


def purpose_exists(connection: Connection, code: str) -> bool:
    found = connection.execute(
        text("SELECT 1 FROM purposes WHERE code = :code"),
        {"code": code},
    ).scalar()
    return found is not None


def place_exists(connection: Connection, place_id: str) -> bool:
    found = connection.execute(
        text("SELECT 1 FROM places WHERE id = :place_id"),
        {"place_id": place_id},
    ).scalar()
    return found is not None


def person_in_cohort(connection: Connection, person_id: str) -> bool:
    found = connection.execute(
        text(
            """
            SELECT 1
            FROM persons
            WHERE person_id = :person_id
              AND dataset_id = :dataset_id
              AND source = :source
            """
        ),
        {**_base_params(), "person_id": person_id},
    ).scalar()
    return found is not None


def active_person_days(connection: Connection, date_from: date, date_to: date) -> int:
    value = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT t.person_id, t.trip_date
                FROM trips AS t
                WHERE {_TRIP_GUARD}
                  AND t.trip_date >= :date_from
                  AND t.trip_date <= :date_to
            ) AS active_days
            """
        ),
        {**_base_params(), "date_from": date_from, "date_to": date_to},
    ).scalar()
    return int(value or 0)


def aggregate_trips(connection: Connection, filters: dict) -> dict:
    """Un seul passage GROUPING SETS : total, mode, motif, date."""
    params = _base_params()
    where = _TRIP_GUARD + _attribute_clause(filters, params)
    rows = connection.execute(
        text(
            f"""
            SELECT
                t.mode_code,
                t.purpose_code,
                t.trip_date,
                GROUPING(t.mode_code) AS mode_grouped,
                GROUPING(t.purpose_code) AS purpose_grouped,
                GROUPING(t.trip_date) AS date_grouped,
                COUNT(*) AS trip_count,
                COALESCE(SUM(t.distance_km), 0) AS distance_km,
                COALESCE(SUM(t.duration_min), 0) AS duration_min
            FROM trips AS t
            WHERE {where}
            GROUP BY GROUPING SETS (
                (),
                (t.mode_code),
                (t.purpose_code),
                (t.trip_date)
            )
            """
        ),
        params,
    ).mappings().all()
    total = {"trip_count": 0, "distance_km": Decimal("0"), "duration_min": Decimal("0")}
    by_mode: list[dict] = []
    by_purpose: list[dict] = []
    by_date: list[dict] = []
    for row in rows:
        item = {
            "trip_count": int(row["trip_count"] or 0),
            "distance_km": Decimal(row["distance_km"]),
            "duration_min": Decimal(row["duration_min"]),
        }
        mode_grouped = int(row["mode_grouped"])
        purpose_grouped = int(row["purpose_grouped"])
        date_grouped = int(row["date_grouped"])
        if mode_grouped == 1 and purpose_grouped == 1 and date_grouped == 1:
            total = item
        elif mode_grouped == 0 and purpose_grouped == 1 and date_grouped == 1:
            by_mode.append({"mode_code": row["mode_code"], **item})
        elif purpose_grouped == 0 and mode_grouped == 1 and date_grouped == 1:
            by_purpose.append({"purpose_code": row["purpose_code"], **item})
        elif date_grouped == 0 and mode_grouped == 1 and purpose_grouped == 1:
            by_date.append({"trip_date": row["trip_date"], **item})
    return {
        "total": total,
        "by_mode": by_mode,
        "by_purpose": by_purpose,
        "by_date": by_date,
    }


def count_flows(connection: Connection, filters: dict) -> int:
    params = _base_params()
    where = _TRIP_GUARD + _attribute_clause(filters, params)
    value = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT t.origin_place_id, t.destination_place_id
                FROM trips AS t
                WHERE {where}
                GROUP BY t.origin_place_id, t.destination_place_id
            ) AS pairs
            """
        ),
        params,
    ).scalar()
    return int(value or 0)


def list_flows(connection: Connection, filters: dict, limit: int, offset: int) -> list[dict]:
    params = _base_params()
    where = _TRIP_GUARD + _attribute_clause(filters, params)
    params["limit"] = limit
    params["offset"] = offset
    rows = connection.execute(
        text(
            f"""
            SELECT
                t.origin_place_id,
                origin.name AS origin_name,
                origin.lon AS origin_lon,
                origin.lat AS origin_lat,
                t.destination_place_id,
                destination.name AS destination_name,
                destination.lon AS destination_lon,
                destination.lat AS destination_lat,
                COUNT(*) AS trip_count,
                COALESCE(SUM(t.distance_km), 0) AS distance_km,
                COALESCE(SUM(t.duration_min), 0) AS duration_min
            FROM trips AS t
            JOIN places AS origin ON origin.id = t.origin_place_id
            JOIN places AS destination ON destination.id = t.destination_place_id
            WHERE {where}
            GROUP BY
                t.origin_place_id,
                origin.name,
                origin.lon,
                origin.lat,
                t.destination_place_id,
                destination.name,
                destination.lon,
                destination.lat
            ORDER BY COUNT(*) DESC, t.origin_place_id, t.destination_place_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def count_filtered_trips(connection: Connection, filters: dict) -> int:
    params = _base_params()
    where = _TRIP_GUARD + _attribute_clause(filters, params)
    value = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM trips AS t
            WHERE {where}
            """
        ),
        params,
    ).scalar()
    return int(value or 0)


def list_trips(connection: Connection, filters: dict, limit: int, offset: int) -> list[dict]:
    params = _base_params()
    where = _TRIP_GUARD + _attribute_clause(filters, params)
    params["limit"] = limit
    params["offset"] = offset
    rows = connection.execute(
        text(
            f"""
            SELECT
                t.trip_id,
                t.person_id,
                t.trip_date,
                t.depart_time,
                t.arrive_time,
                t.origin_place_id,
                origin.name AS origin_name,
                t.destination_place_id,
                destination.name AS destination_name,
                t.purpose_code,
                purpose.label_fr AS purpose_label,
                t.mode_code,
                mode.label_fr AS mode_label,
                t.distance_km,
                t.duration_min,
                t.source
            FROM trips AS t
            JOIN places AS origin ON origin.id = t.origin_place_id
            JOIN places AS destination ON destination.id = t.destination_place_id
            JOIN purposes AS purpose ON purpose.code = t.purpose_code
            JOIN modes AS mode ON mode.code = t.mode_code
            WHERE {where}
            ORDER BY t.trip_date, t.depart_time, t.trip_id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    payload = []
    for row in rows:
        item = dict(row)
        depart = item["depart_time"]
        arrive = item["arrive_time"]
        item["depart_time"] = depart.isoformat() if isinstance(depart, time) else str(depart)
        item["arrive_time"] = arrive.isoformat() if isinstance(arrive, time) else str(arrive)
        payload.append(item)
    return payload
