# -*- coding: utf-8 -*-
"""Écrit le catalogue simulé dans PostGIS, sans toucher aux tables OSM."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.database import engine  # noqa: E402
from app.services.mobility_catalog import seed_payload  # noqa: E402


def _wkt(geometry: dict) -> str:
    ring = geometry["coordinates"][0]
    body = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    return f"SRID=4326;POLYGON(({body}))"


def main() -> None:
    sql_path = Path(__file__).resolve().parent / "sql" / "20_simulated_mobility.sql"
    payload = seed_payload()
    with engine.begin() as connection:
        for statement in sql_path.read_text(encoding="utf-8").split(";"):
            cleaned = "\n".join(
                line for line in statement.splitlines() if not line.strip().startswith("--")
            ).strip()
            if cleaned:
                connection.execute(text(cleaned))
        for table in (
            "sim_clusters",
            "sim_indicators",
            "sim_trips",
            "sim_persons",
            "sim_companies",
            "sim_zones",
        ):
            connection.execute(text(f"DELETE FROM {table}"))
        for zone in payload["zones"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_zones
                        (id, city_id, name, level, level_label, parent_id, role, lon, lat, geometry)
                    VALUES
                        (:id, :city_id, :name, :level, :level_label, :parent_id, :role, :lon, :lat,
                         ST_GeomFromEWKT(:wkt))
                    """
                ),
                {
                    "id": zone["id"],
                    "city_id": zone["city_id"],
                    "name": zone["name"],
                    "level": zone["level"],
                    "level_label": zone["level_label"],
                    "parent_id": zone["parent_id"],
                    "role": zone["role"],
                    "lon": zone["lon"],
                    "lat": zone["lat"],
                    "wkt": _wkt(zone["geometry"]),
                },
            )
        for company in payload["companies"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_companies
                        (id, name, kind, kind_label, city_id, seat_id, activity, employee_count)
                    VALUES
                        (:id, :name, :kind, :kind_label, :city_id, :seat_id, :activity, :employee_count)
                    """
                ),
                company,
            )
        for person in payload["persons"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_persons (
                        person_id, city_id, residence_id, arrondissement_id, company_id,
                        job_label, sector, mode, work_id, distance_km, time_min,
                        frequency, purpose, source
                    ) VALUES (
                        :person_id, :city_id, :residence_id, :arrondissement_id, :company_id,
                        :job_label, :sector, :mode, :work_id, :distance_km, :time_min,
                        :frequency, :purpose, :source
                    )
                    """
                ),
                person,
            )
        for trip in payload["trips"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_trips (
                        trip_id, city_id, person_id, group_size, origin_id, destination_id,
                        purpose, frequency, distance_km, duration_min, period, mode,
                        company_id, synthetic
                    ) VALUES (
                        :trip_id, :city_id, :person_id, :group_size, :origin_id, :destination_id,
                        :purpose, :frequency, :distance_km, :duration_min, :period, :mode,
                        :company_id, :synthetic
                    )
                    """
                ),
                trip,
            )
        for row in payload["indicators"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_indicators (city_id, zone_id, indicator_id, value, unit)
                    VALUES (:city_id, :zone_id, :indicator_id, :value, :unit)
                    """
                ),
                row,
            )
        for row in payload["clusters"]:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_clusters (person_id, city_id, cluster_id, cluster_label)
                    VALUES (:person_id, :city_id, :cluster_id, :cluster_label)
                    """
                ),
                row,
            )
    print(
        "zones", len(payload["zones"]),
        "companies", len(payload["companies"]),
        "persons", len(payload["persons"]),
        "trips", len(payload["trips"]),
        "indicators", len(payload["indicators"]),
        "clusters", len(payload["clusters"]),
    )


if __name__ == "__main__":
    main()
