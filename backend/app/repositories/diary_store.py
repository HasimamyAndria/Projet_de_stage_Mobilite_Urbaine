"""Lecture du journal simulé dans les tables du contrat."""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import text

from app.database import engine
from app.services.diary_contract import DATASET_ID, time_to_hour

_CACHE: dict | None = None


def clear_cache() -> None:
    global _CACHE
    _CACHE = None


def _load() -> dict:
    with engine.connect() as connection:
        dataset = connection.execute(
            text(
                """
                SELECT id, source, anchor_monday
                FROM datasets
                WHERE id = :dataset_id
                """
            ),
            {"dataset_id": DATASET_ID},
        ).mappings().first()
        if dataset is None:
            raise ValueError(
                "Jeu diary-week absent. Exécuter scripts/seed_diary_trips.py "
                "ou définir DIARY_READ=memory."
            )
        if dataset["source"] != "SIMULATED":
            raise ValueError("Le jeu diary-week n'est pas marqué SIMULATED.")
        anchor = dataset["anchor_monday"]
        if not isinstance(anchor, date):
            raise ValueError("Le jeu diary-week n'a pas de lundi d'ancrage.")

        people = connection.execute(
            text(
                """
                SELECT person_id
                FROM persons
                WHERE dataset_id = :dataset_id AND source = 'SIMULATED'
                """
            ),
            {"dataset_id": DATASET_ID},
        ).scalars().all()

        rows = connection.execute(
            text(
                """
                SELECT
                    t.trip_id,
                    t.person_id,
                    t.trip_date,
                    t.depart_time,
                    t.purpose_code,
                    t.mode_code,
                    t.distance_km,
                    t.duration_min,
                    t.detail,
                    t.origin_place_id,
                    t.destination_place_id,
                    origin.name AS origin_name,
                    origin.lon AS origin_lon,
                    origin.lat AS origin_lat,
                    destination.name AS destination_name,
                    destination.lon AS destination_lon,
                    destination.lat AS destination_lat
                FROM trips AS t
                JOIN places AS origin ON origin.id = t.origin_place_id
                JOIN places AS destination ON destination.id = t.destination_place_id
                WHERE t.dataset_id = :dataset_id
                  AND t.source = 'SIMULATED'
                  AND t.validation_status = 'validated'
                  AND t.survey_id IS NULL
                  AND t.import_batch_id IS NULL
                ORDER BY t.person_id, t.trip_date, t.depart_time, t.trip_id
                """
            ),
            {"dataset_id": DATASET_ID},
        ).mappings().all()

    by_person: dict[str, dict[int, list[dict]]] = {person_id: {} for person_id in people}
    for row in rows:
        weekday = (row["trip_date"] - anchor).days
        if weekday < 0 or weekday > 6:
            raise ValueError(f"Trajet hors de la semaine d'ancrage : {row['trip_id']}")
        depart = row["depart_time"]
        if not isinstance(depart, time):
            raise ValueError(f"Heure de départ illisible : {row['trip_id']}")
        trip = {
            "trip_id": row["trip_id"],
            "weekday": weekday,
            "depart_hour": time_to_hour(depart),
            "origin_id": row["origin_place_id"],
            "origin_name": row["origin_name"],
            "origin_lon": float(row["origin_lon"]),
            "origin_lat": float(row["origin_lat"]),
            "destination_id": row["destination_place_id"],
            "destination_name": row["destination_name"],
            "destination_lon": float(row["destination_lon"]),
            "destination_lat": float(row["destination_lat"]),
            "purpose_code": row["purpose_code"],
            "mode_code": row["mode_code"],
            "km": round(float(row["distance_km"]), 2),
            "minutes": int(row["duration_min"]),
            "detail": row["detail"] or "",
        }
        by_person.setdefault(row["person_id"], {}).setdefault(weekday, []).append(trip)
    return by_person


def week_by_person() -> dict[str, dict[int, list[dict]]]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load()
    return _CACHE
