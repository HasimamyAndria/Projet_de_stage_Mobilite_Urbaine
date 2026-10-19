# -*- coding: utf-8 -*-
"""Charge le journal des personnes du catalogue dans le contrat PostgreSQL.

Le calcul des étapes est celui de diary._scripted_day_trips, sans les
saisies manuelles. Une seconde exécution met à jour les mêmes identifiants.

Ne touche pas à mobility_flows, planet_osm_*, roads_network ni sim_*.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\seed_diary_trips.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from apply_sql_migration import load_env, make_engine  # noqa: E402

load_env()

from app.data.persons import PERSONS  # noqa: E402
from app.data.territory import PLACES  # noqa: E402
from app.services.diary import _scripted_day_trips  # noqa: E402
from app.services.diary_contract import (  # noqa: E402
    ANCHOR_MONDAY,
    DATASET_ID,
    DATASET_LABEL,
    DATASET_SEED,
    DIARY_TO_CODE,
    hour_to_time,
)
from app.services.diary import MODES  # noqa: E402

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
)

LEVEL_ORDER = {"city": 0, "commune": 1, "quartier": 2}


def _counts(connection) -> dict[str, int]:
    totals = {}
    for table in PROTECTED:
        totals[table] = int(
            connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
        )
    return totals


def _places() -> list[dict]:
    rows = []
    for place in PLACES.values():
        level = place["level"]
        if level not in LEVEL_ORDER:
            raise SystemExit(f"Niveau de lieu inconnu : {place['id']} {level}")
        role = place["role"]
        rows.append(
            {
                "id": place["id"],
                "parent_id": place["parent_id"],
                "city_id": place["city_id"],
                "name": place["name"],
                "level": level,
                "level_label": place.get("level_label"),
                "role": role,
                "lon": place["lon"],
                "lat": place["lat"],
            }
        )
    rows.sort(key=lambda row: (LEVEL_ORDER[row["level"]], row["id"]))
    return rows


def _trips() -> list[dict]:
    payload = []
    for person in PERSONS:
        for weekday in range(7):
            for trip in _scripted_day_trips(person, weekday):
                purpose = trip["purpose"]
                mode = trip["mode"]
                if purpose not in DIARY_TO_CODE:
                    raise SystemExit(
                        f"Motif sans traduction canonique : {person['id']} {purpose}"
                    )
                if mode not in MODES:
                    raise SystemExit(f"Mode hors contrat : {person['id']} {mode}")
                trip_date = ANCHOR_MONDAY + timedelta(days=weekday)
                depart = hour_to_time(trip["depart_hour"])
                arrive = (
                    datetime.combine(trip_date, depart) + timedelta(minutes=int(trip["minutes"]))
                ).time()
                payload.append(
                    {
                        "trip_id": trip["id"],
                        "dataset_id": DATASET_ID,
                        "person_id": person["id"],
                        "trip_date": trip_date,
                        "depart_time": depart,
                        "arrive_time": arrive,
                        "origin_place_id": trip["origin_id"],
                        "destination_place_id": trip["destination_id"],
                        "purpose_code": DIARY_TO_CODE[purpose],
                        "mode_code": mode,
                        "distance_km": trip["km"],
                        "duration_min": int(trip["minutes"]),
                        "detail": trip["detail"],
                    }
                )
    return payload


def main() -> int:
    if ANCHOR_MONDAY.weekday() != 0:
        raise SystemExit("ANCHOR_MONDAY n'est pas un lundi.")
    places = _places()
    trips = _trips()
    engine = make_engine()
    try:
        with engine.begin() as connection:
            before = _counts(connection)
            connection.execute(
                text(
                    """
                    INSERT INTO datasets (id, source, label, seed, anchor_monday)
                    VALUES (:id, 'SIMULATED', :label, :seed, :anchor_monday)
                    ON CONFLICT (id) DO UPDATE SET
                        source = EXCLUDED.source,
                        label = EXCLUDED.label,
                        seed = EXCLUDED.seed,
                        anchor_monday = EXCLUDED.anchor_monday
                    """
                ),
                {
                    "id": DATASET_ID,
                    "label": DATASET_LABEL,
                    "seed": DATASET_SEED,
                    "anchor_monday": ANCHOR_MONDAY,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO places (
                        id, parent_id, city_id, name, level, level_label, role, lon, lat, boundary_kind
                    ) VALUES (
                        :id, :parent_id, :city_id, :name, :level, :level_label, :role, :lon, :lat,
                        'point_catalog'
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        parent_id = EXCLUDED.parent_id,
                        city_id = EXCLUDED.city_id,
                        name = EXCLUDED.name,
                        level = EXCLUDED.level,
                        level_label = EXCLUDED.level_label,
                        role = EXCLUDED.role,
                        lon = EXCLUDED.lon,
                        lat = EXCLUDED.lat,
                        boundary_kind = EXCLUDED.boundary_kind
                    """
                ),
                places,
            )
            connection.execute(
                text(
                    """
                    INSERT INTO persons (
                        person_id, dataset_id, display_name, city_id, home_place_id,
                        work_place_id, activity, source
                    ) VALUES (
                        :person_id, :dataset_id, :display_name, :city_id, :home_place_id,
                        :work_place_id, :activity, 'SIMULATED'
                    )
                    ON CONFLICT (person_id) DO UPDATE SET
                        dataset_id = EXCLUDED.dataset_id,
                        display_name = EXCLUDED.display_name,
                        city_id = EXCLUDED.city_id,
                        home_place_id = EXCLUDED.home_place_id,
                        work_place_id = EXCLUDED.work_place_id,
                        activity = EXCLUDED.activity,
                        source = EXCLUDED.source
                    """
                ),
                [
                    {
                        "person_id": person["id"],
                        "dataset_id": DATASET_ID,
                        "display_name": person["name"],
                        "city_id": person["city_id"],
                        "home_place_id": person["home_id"],
                        "work_place_id": person["work_id"],
                        "activity": person["job"],
                    }
                    for person in PERSONS
                ],
            )
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
                        :distance_km, :duration_min, :detail, 'SIMULATED', 'validated',
                        NULL, NULL
                    )
                    ON CONFLICT (trip_id) DO UPDATE SET
                        dataset_id = EXCLUDED.dataset_id,
                        person_id = EXCLUDED.person_id,
                        trip_date = EXCLUDED.trip_date,
                        depart_time = EXCLUDED.depart_time,
                        arrive_time = EXCLUDED.arrive_time,
                        origin_place_id = EXCLUDED.origin_place_id,
                        destination_place_id = EXCLUDED.destination_place_id,
                        purpose_code = EXCLUDED.purpose_code,
                        mode_code = EXCLUDED.mode_code,
                        distance_km = EXCLUDED.distance_km,
                        duration_min = EXCLUDED.duration_min,
                        detail = EXCLUDED.detail,
                        source = EXCLUDED.source,
                        validation_status = EXCLUDED.validation_status,
                        survey_id = EXCLUDED.survey_id,
                        import_batch_id = EXCLUDED.import_batch_id
                    """
                ),
                trips,
            )
            after = _counts(connection)
            changed = [name for name in PROTECTED if before[name] != after[name]]
            if changed:
                raise RuntimeError("Tables protégées modifiées : " + ", ".join(changed))
        print(
            f"dataset={DATASET_ID} source=SIMULATED anchor={ANCHOR_MONDAY.isoformat()} "
            f"places={len(places)} persons={len(PERSONS)} trips={len(trips)}"
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERREUR {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
