# -*- coding: utf-8 -*-
"""Compare le journal PostgreSQL à la semaine type Python.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_diary_seed.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from apply_sql_migration import load_env, make_engine  # noqa: E402

load_env()

from app.data.persons import PERSONS  # noqa: E402
from app.data.territory import PLACES  # noqa: E402
from app.repositories.diary_store import clear_cache  # noqa: E402
from app.services import diary  # noqa: E402
from app.services.diary_contract import DATASET_ID  # noqa: E402

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

UI_TRIP_FIELDS = (
    "id",
    "weekday_label",
    "origin_name",
    "destination_name",
    "purpose_label",
    "purpose_color",
    "detail",
    "mode_label",
    "depart_label",
    "minutes",
    "km",
    "source",
    "origin",
    "destination",
)


def _counts(connection) -> dict[str, int]:
    totals = {}
    for table in PROTECTED:
        totals[table] = int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar())
    return totals


def _reference(person: dict) -> dict:
    steps = []
    for weekday in range(7):
        steps.extend(diary._scripted_day_trips(person, weekday))
    return {
        "steps": len(steps),
        "km": round(sum(trip["km"] for trip in steps), 2),
        "minutes": sum(trip["minutes"] for trip in steps),
        "returns": sum(1 for trip in steps if trip["purpose"] == "domicile"),
        "empty_days": [
            weekday
            for weekday in range(7)
            if not diary._scripted_day_trips(person, weekday)
        ],
        "ids": [trip["id"] for trip in steps],
    }


def _seed() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_diary_trips.py")],
        cwd=str(ROOT),
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"seed exit {completed.returncode}")


def _diary(person_id: str, backend: str) -> dict:
    os.environ["DIARY_READ"] = backend
    clear_cache()
    return diary.person_diary(person_id, "week", 0)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    results: list[str] = []

    def record(ok: bool, label: str, detail: str = "") -> None:
        suffix = f" — {detail}" if detail else ""
        results.append(f"{'PASS' if ok else 'FAIL'} {label}{suffix}")

    engine = make_engine()
    try:
        with engine.connect() as connection:
            before = _counts(connection)
        _seed()
        _seed()
        with engine.connect() as connection:
            after = _counts(connection)
            changed = [name for name in PROTECTED if before[name] != after[name]]
            record(not changed, "tables OSM et sim intactes", "ok" if not changed else ", ".join(changed))

            persons = connection.execute(
                text(
                    """
                    SELECT person_id FROM persons
                    WHERE dataset_id = :dataset_id AND source = 'SIMULATED'
                    ORDER BY person_id
                    """
                ),
                {"dataset_id": DATASET_ID},
            ).scalars().all()
            expected_ids = sorted(person["id"] for person in PERSONS)
            record(list(persons) == expected_ids, "huit personnes SIMULATED", str(len(persons)))

            source = connection.execute(
                text("SELECT source, label FROM datasets WHERE id = :dataset_id"),
                {"dataset_id": DATASET_ID},
            ).first()
            label = "" if source is None else str(source[1])
            record(
                source is not None
                and source[0] == "SIMULATED"
                and "SIMULATED" in label
                and "inventées" in label,
                "dataset de démonstration",
                "" if source is None else source[0],
            )
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
            record(int(observed) == 0, "aucune ligne OBSERVED", str(observed))

            broken = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM trips AS t
                    LEFT JOIN persons AS p
                      ON p.person_id = t.person_id AND p.dataset_id = t.dataset_id
                    LEFT JOIN places AS origin ON origin.id = t.origin_place_id
                    LEFT JOIN places AS destination ON destination.id = t.destination_place_id
                    WHERE t.dataset_id = :dataset_id
                      AND (
                        p.person_id IS NULL
                        OR origin.id IS NULL
                        OR destination.id IS NULL
                        OR t.trip_date IS NULL
                        OR t.source <> 'SIMULATED'
                        OR t.validation_status <> 'validated'
                        OR t.survey_id IS NOT NULL
                      )
                    """
                ),
                {"dataset_id": DATASET_ID},
            ).scalar()
            record(int(broken) == 0, "étapes liées, datées, simulées", str(broken))

            dup = connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT trip_id FROM trips
                        WHERE dataset_id = :dataset_id
                        GROUP BY trip_id
                        HAVING COUNT(*) > 1
                    ) AS doubled
                    """
                ),
                {"dataset_id": DATASET_ID},
            ).scalar()
            record(int(dup) == 0, "aucun doublon de trajet", str(dup))

            place_count = connection.execute(text("SELECT COUNT(*) FROM places")).scalar()
            record(int(place_count) == len(PLACES), "lieux du catalogue", f"{place_count}/{len(PLACES)}")

            canonical = connection.execute(
                text(
                    """
                    SELECT purpose_code, COUNT(*)
                    FROM trips
                    WHERE dataset_id = :dataset_id
                    GROUP BY purpose_code
                    """
                ),
                {"dataset_id": DATASET_ID},
            ).fetchall()
            codes = {row[0] for row in canonical}
            record("retour_domicile" in codes, "retours au domicile en code canonique")
            record("courses_supermarche" in codes, "courses au supermarché")
            record("courses_marche" in codes, "courses au marché")
            record("domicile" not in codes and "supermarche" not in codes, "anciens codes absents de trips")

            flow_mode = connection.execute(
                text("SELECT COUNT(*) FROM mobility_flows WHERE mode IS DISTINCT FROM 'all'")
            ).scalar()
            record(int(flow_mode) == 0, "flux OSM toujours en mode all", str(flow_mode))

        mismatches = []
        for person in PERSONS:
            ref = _reference(person)
            memory = _diary(person["id"], "memory")
            stored = _diary(person["id"], "postgres")
            if ref["empty_days"]:
                mismatches.append(f"{person['id']} jours vides {ref['empty_days']}")
            mem_trips = memory["trips"]
            db_trips = stored["trips"]
            if len(db_trips) != ref["steps"] or len(mem_trips) != ref["steps"]:
                mismatches.append(f"{person['id']} effectif {len(db_trips)} != {ref['steps']}")
                continue
            mem_km = round(sum(trip["km"] for trip in mem_trips), 2)
            db_km = round(sum(trip["km"] for trip in db_trips), 2)
            mem_min = sum(trip["minutes"] for trip in mem_trips)
            db_min = sum(trip["minutes"] for trip in db_trips)
            if mem_km != ref["km"] or db_km != ref["km"] or mem_min != ref["minutes"] or db_min != ref["minutes"]:
                mismatches.append(
                    f"{person['id']} km/min mem {mem_km}/{mem_min} db {db_km}/{db_min} ref {ref['km']}/{ref['minutes']}"
                )
            returns = sum(1 for trip in db_trips if trip["purpose"] == "domicile")
            if returns != ref["returns"]:
                mismatches.append(f"{person['id']} retours {returns} != {ref['returns']}")
            for left, right in zip(mem_trips, db_trips):
                if any(field not in right for field in UI_TRIP_FIELDS):
                    mismatches.append(f"{person['id']} champ UI manquant")
                    break
                if left["id"] != right["id"] or left["purpose"] != right["purpose"]:
                    mismatches.append(f"{person['id']} id/motif {left['id']}")
                    break
                if left["km"] != right["km"] or left["minutes"] != right["minutes"]:
                    mismatches.append(f"{person['id']} distance {left['id']}")
                    break
                if left["depart_label"] != right["depart_label"] or left["detail"] != right["detail"]:
                    mismatches.append(f"{person['id']} horaire {left['id']}")
                    break
                if right["source"] != "simulated":
                    mismatches.append(f"{person['id']} source {right['source']}")
                    break
            if memory["stats"] != stored["stats"]:
                mismatches.append(f"{person['id']} stats")
            if memory["purposes"] != stored["purposes"] or memory["modes"] != stored["modes"]:
                mismatches.append(f"{person['id']} barres")
            if not stored.get("synthetic"):
                mismatches.append(f"{person['id']} synthetic")
        record(not mismatches, "équivalence semaine mémoire / PostgreSQL", "ok" if not mismatches else "; ".join(mismatches))
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
