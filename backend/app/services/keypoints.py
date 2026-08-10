"""
M2 — Points clés (heuristiques métier).

Labels de zones :
- dormitory  : beaucoup d'habitants, peu d'emplois
- employment : beaucoup d'emplois, peu d'habitants
- balanced   : ratio intermédiaire

Corridors :
- desire lines parmi le top des volumes OD
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.privacy import K_ANONYMITY_MIN


def _classify_zone(population: int, jobs: int, pop_med: float, jobs_med: float) -> dict:
    """
    Règles simples (RM-12 style) pour le MVP.
    On utilise la part d'emplois : jobs / (pop + jobs).
    """
    total = max(population + jobs, 1)
    job_share = jobs / total
    ratio = population / max(jobs, 1)

    # Pôle emploi : part d'emplois élevée + emplois au-dessus de la médiane
    if jobs >= jobs_med and job_share >= 0.45:
        label = "employment"
        label_fr = "Pôle emploi"
    # Zone dortoir : pop significative + faible part d'emplois
    elif population >= pop_med * 0.9 and job_share <= 0.38:
        label = "dormitory"
        label_fr = "Zone dortoir"
    else:
        label = "balanced"
        label_fr = "Zone mixte"

    return {
        "label": label,
        "label_fr": label_fr,
        "pop_jobs_ratio": round(ratio, 2),
        "job_share": round(job_share, 2),
    }


def get_keypoints(db: Session, corridor_top_n: int = 5) -> dict:
    print("===== KEYPOINTS M2 =====")
    print(f"corridor_top_n = {corridor_top_n}")

    # --- Zones + proxies ---
    zone_rows = db.execute(
        text(
            """
            SELECT
                id,
                name,
                COALESCE(population_proxy, 0) AS population_proxy,
                COALESCE(jobs_proxy, 0) AS jobs_proxy,
                ST_AsGeoJSON(geometry)::json AS geometry
            FROM mobility_zones
            ORDER BY name
            """
        )
    ).fetchall()

    if not zone_rows:
        print("Aucune zone — peupler avec seed_zones_od.py")
        return {
            "zones": {"type": "FeatureCollection", "features": []},
            "corridors": {"type": "FeatureCollection", "features": []},
            "counts": {
                "dormitory": 0,
                "employment": 0,
                "balanced": 0,
                "corridors": 0,
            },
            "rules": {},
            "synthetic": True,
            "note": "Aucune zone disponible.",
        }

    populations = [int(r.population_proxy) for r in zone_rows]
    jobs_list = [int(r.jobs_proxy) for r in zone_rows]
    pop_med = sorted(populations)[len(populations) // 2]
    jobs_med = sorted(jobs_list)[len(jobs_list) // 2]

    print(f"Médiane population = {pop_med}, médiane emplois = {jobs_med}")

    counts = {"dormitory": 0, "employment": 0, "balanced": 0}
    zone_features = []

    for r in zone_rows:
        pop = int(r.population_proxy)
        jobs = int(r.jobs_proxy)
        classif = _classify_zone(pop, jobs, pop_med, jobs_med)
        counts[classif["label"]] += 1

        print(
            f"Zone {r.name}: pop={pop}, jobs={jobs}, "
            f"ratio={classif['pop_jobs_ratio']}, "
            f"job_share={classif.get('job_share')} -> {classif['label_fr']}"
        )

        zone_features.append(
            {
                "type": "Feature",
                "geometry": r.geometry,
                "properties": {
                    "id": r.id,
                    "name": r.name,
                    "population_proxy": pop,
                    "jobs_proxy": jobs,
                    "label": classif["label"],
                    "label_fr": classif["label_fr"],
                    "pop_jobs_ratio": classif["pop_jobs_ratio"],
                    "job_share": classif.get("job_share"),
                },
            }
        )

    # --- Corridors = top desire lines ---
    corridor_rows = db.execute(
        text(
            """
            SELECT
                id,
                origin_zone_id,
                destination_zone_id,
                origin_name,
                destination_name,
                passenger_count,
                average_distance,
                average_time,
                ST_AsGeoJSON(geom)::json AS geometry
            FROM v_od_desire_lines
            WHERE passenger_count >= :k
            ORDER BY passenger_count DESC
            LIMIT :n
            """
        ),
        {"n": corridor_top_n, "k": K_ANONYMITY_MIN},
    ).fetchall()

    corridor_features = []
    for r in corridor_rows:
        print(
            f"Corridor : {r.origin_name} -> {r.destination_name} "
            f"= {r.passenger_count}"
        )
        corridor_features.append(
            {
                "type": "Feature",
                "geometry": r.geometry,
                "properties": {
                    "id": r.id,
                    "origin_name": r.origin_name,
                    "destination_name": r.destination_name,
                    "passenger_count": int(r.passenger_count),
                    "label": "corridor",
                    "label_fr": "Corridor saturé (proxy volume)",
                    "average_distance_km": (
                        float(r.average_distance)
                        if r.average_distance is not None
                        else None
                    ),
                },
            }
        )

    counts["corridors"] = len(corridor_features)

    rules = {
        "dormitory": "population >= 0.9*médiane ET part_emplois <= 0.38",
        "employment": "emplois >= médiane ET part_emplois >= 0.45",
        "balanced": "sinon",
        "corridor": f"top {corridor_top_n} flux OD par volume",
        "pop_median": pop_med,
        "jobs_median": jobs_med,
    }

    print(f"Counts M2 : {counts}")

    return {
        "zones": {"type": "FeatureCollection", "features": zone_features},
        "corridors": {"type": "FeatureCollection", "features": corridor_features},
        "counts": counts,
        "rules": rules,
        "synthetic": True,
        "note": (
            "Classification heuristique MVP sur proxies population/emplois. "
            "Corridors = plus gros volumes OD (pas une saturation réseau mesurée)."
        ),
    }
