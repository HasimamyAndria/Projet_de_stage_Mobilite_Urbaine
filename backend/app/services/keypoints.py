"""
M2 — Points clés (heuristiques métier + clustering spatial).

Labels de zones :
- dormitory  : beaucoup d'habitants, peu d'emplois
- employment : beaucoup d'emplois, peu d'habitants
- balanced   : ratio intermédiaire

Clustering :
- K-means sur centroïdes (lon, lat) min-max, seed fixe.

Corridors :
- desire lines parmi le top des volumes OD
"""
from __future__ import annotations

import math
import random
from collections import Counter

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.privacy import K_ANONYMITY_MIN
from app.services.provenance import get_data_provenance

KMEANS_SEED = 42
LABEL_FR = {
    "dormitory": "Zone dortoir",
    "employment": "Pôle emploi",
    "balanced": "Zone mixte",
}


def _dist(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _minmax_scale(points: list[list[float]]) -> list[list[float]]:
    if not points:
        return []
    dims = len(points[0])
    mins = [min(p[d] for p in points) for d in range(dims)]
    maxs = [max(p[d] for p in points) for d in range(dims)]
    scaled = []
    for p in points:
        row = []
        for d in range(dims):
            span = maxs[d] - mins[d]
            row.append(0.0 if span == 0 else (p[d] - mins[d]) / span)
        scaled.append(row)
    return scaled


def _kmeans(
    points: list[list[float]], k: int, seed: int = KMEANS_SEED, max_iter: int = 40
) -> tuple[list[int], float]:
    """K-means 2D (ou nD) pur Python. Retourne labels + silhouette moyenne."""
    n = len(points)
    if n == 0:
        return [], 0.0
    k = max(1, min(k, n))
    rng = random.Random(seed)
    order = list(range(n))
    rng.shuffle(order)
    centroids = [points[i][:] for i in order[:k]]
    labels = [0] * n

    for _ in range(max_iter):
        changed = False
        for i, point in enumerate(points):
            best = min(range(k), key=lambda c: _dist(point, centroids[c]))
            if labels[i] != best:
                labels[i] = best
                changed = True
        for c in range(k):
            members = [points[i] for i, lab in enumerate(labels) if lab == c]
            if members:
                centroids[c] = [
                    sum(m[d] for m in members) / len(members)
                    for d in range(len(members[0]))
                ]
        if not changed:
            break

    return labels, round(_mean_silhouette(points, labels, k), 3)


def _mean_silhouette(points: list[list[float]], labels: list[int], k: int) -> float:
    n = len(points)
    if n < 2 or k < 2:
        return 0.0
    scores: list[float] = []
    for i, point in enumerate(points):
        same = [j for j, lab in enumerate(labels) if lab == labels[i] and j != i]
        if not same:
            scores.append(0.0)
            continue
        a = sum(_dist(point, points[j]) for j in same) / len(same)
        b = None
        for c in range(k):
            if c == labels[i]:
                continue
            others = [j for j, lab in enumerate(labels) if lab == c]
            if not others:
                continue
            mean_c = sum(_dist(point, points[j]) for j in others) / len(others)
            b = mean_c if b is None else min(b, mean_c)
        if b is None:
            scores.append(0.0)
            continue
        denom = max(a, b) or 1.0
        scores.append((b - a) / denom)
    return sum(scores) / len(scores) if scores else 0.0


def _cluster_caption(labels_in_cluster: list[str], cluster_id: int) -> str:
    if not labels_in_cluster:
        return f"Groupe {cluster_id + 1}"
    majority, _ = Counter(labels_in_cluster).most_common(1)[0]
    return f"Groupe {cluster_id + 1} — {LABEL_FR.get(majority, majority)}"


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
                ST_X(ST_Centroid(geometry)) AS lon,
                ST_Y(ST_Centroid(geometry)) AS lat,
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
            "clustering": {
                "method": "kmeans",
                "k": 0,
                "seed": KMEANS_SEED,
                "silhouette": 0.0,
                "features": "centroid lon/lat min-max scaled",
                "note": "Aucune zone à clusteriser.",
            },
            "rules": {},
            "synthetic": True,
            "data_source": "none",
            "note": "Aucune zone disponible.",
        }

    populations = [int(r.population_proxy) for r in zone_rows]
    jobs_list = [int(r.jobs_proxy) for r in zone_rows]
    pop_med = sorted(populations)[len(populations) // 2]
    jobs_med = sorted(jobs_list)[len(jobs_list) // 2]

    print(f"Médiane population = {pop_med}, médiane emplois = {jobs_med}")

    counts = {"dormitory": 0, "employment": 0, "balanced": 0}
    classified: list[tuple] = []
    centroids: list[list[float]] = []

    for r in zone_rows:
        pop = int(r.population_proxy)
        jobs = int(r.jobs_proxy)
        classif = _classify_zone(pop, jobs, pop_med, jobs_med)
        counts[classif["label"]] += 1
        classified.append((r, pop, jobs, classif))
        lon = float(r.lon) if r.lon is not None else 0.0
        lat = float(r.lat) if r.lat is not None else 0.0
        centroids.append([lon, lat])
        print(
            f"Zone {r.name}: pop={pop}, jobs={jobs}, "
            f"ratio={classif['pop_jobs_ratio']}, "
            f"job_share={classif.get('job_share')} -> {classif['label_fr']}"
        )

    n_zones = len(classified)
    k = 1 if n_zones < 2 else max(2, min(4, n_zones // 3 or 2))
    cluster_labels, silhouette = _kmeans(_minmax_scale(centroids), k)
    members_by_cluster: dict[int, list[str]] = {}
    for idx, classif in enumerate(c[3] for c in classified):
        cid = cluster_labels[idx] if cluster_labels else 0
        members_by_cluster.setdefault(cid, []).append(classif["label"])
    cluster_captions = {
        cid: _cluster_caption(labs, cid) for cid, labs in members_by_cluster.items()
    }

    zone_features = []
    for idx, (r, pop, jobs, classif) in enumerate(classified):
        cid = cluster_labels[idx] if cluster_labels else 0
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
                    "cluster_id": cid,
                    "cluster_label": cluster_captions.get(cid, f"Groupe {cid + 1}"),
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
        "clustering": "K-means centroïdes lon/lat (minmax), seed=42",
        "pop_median": pop_med,
        "jobs_median": jobs_med,
    }

    clustering = {
        "method": "kmeans",
        "k": k,
        "seed": KMEANS_SEED,
        "silhouette": silhouette,
        "features": "centroid lon/lat min-max scaled",
        "note": (
            "Regroupement spatial des zones (pas un clustering d'individus). "
            "Les labels métier restent les heuristiques dortoir / pôle / mixte."
        ),
    }

    print(f"Counts M2 : {counts} ; kmeans k={k} silhouette={silhouette}")
    provenance = get_data_provenance(db)

    return {
        "zones": {"type": "FeatureCollection", "features": zone_features},
        "corridors": {"type": "FeatureCollection", "features": corridor_features},
        "counts": counts,
        "clustering": clustering,
        "rules": rules,
        "synthetic": provenance["synthetic"],
        "data_source": provenance["data_source"],
        "note": (
            "Classification heuristique MVP sur proxies population/emplois OSM. "
            "Clustering K-means spatial (centroïdes). "
            "Corridors = plus gros volumes OD (pas une saturation réseau mesurée). "
            + provenance["note"]
        ),
    }
