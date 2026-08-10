"""
M6 — Indice emploi-habitat (proxy documenté).

Formule (par zone) :
    eh_index = 1 - |jobs_proxy - population_proxy| / (jobs_proxy + population_proxy)

Interprétation :
    - 1.0  → équilibre parfait (emplois ≈ population)
    - ~0.0 → déséquilibre fort (presque uniquement emplois OU habitat)

Ce n'est PAS un 2SFCA (pas d'accessibilité spatiale inter-zones).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def _eh_index(population: int, jobs: int) -> float | None:
    """Calcule l'indice d'équilibre emploi-habitat [0, 1]."""
    total = population + jobs
    if total <= 0:
        return None
    return 1.0 - abs(jobs - population) / total


def _imbalance_label(population: int, jobs: int) -> tuple[str, str]:
    """Direction du déséquilibre (utile pour la légende / tooltip)."""
    if population == 0 and jobs == 0:
        return "empty", "Zone vide"
    if jobs > population:
        return "jobs_surplus", "Surplus d'emplois"
    if population > jobs:
        return "housing_surplus", "Surplus d'habitat"
    return "balanced", "Équilibré"


def get_emploi_habitat(db: Session) -> dict:
    """
    Retourne :
    - GeoJSON des zones avec score
    - résumé (moyenne + extrêmes)
    """
    print("===== EMPLOI-HABITAT M6 =====")
    print("Formule : eh_index = 1 - |J - P| / (J + P)")

    rows = db.execute(
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

    if not rows:
        print("Aucune zone — peupler avec seed_zones_od.py")
        return {
            "type": "FeatureCollection",
            "features": [],
            "summary": {
                "zone_count": 0,
                "scored_count": 0,
                "avg_score": None,
                "min_score": None,
                "max_score": None,
                "min_zone_name": None,
                "max_zone_name": None,
            },
            "formula": "eh_index = 1 - |jobs - population| / (jobs + population)",
            "synthetic": True,
            "note": "Aucune zone disponible.",
        }

    features = []
    scores: list[tuple[float, str]] = []  # (score, zone_name)

    for r in rows:
        pop = int(r.population_proxy)
        jobs = int(r.jobs_proxy)
        score = _eh_index(pop, jobs)
        direction, direction_fr = _imbalance_label(pop, jobs)

        score_rounded = round(score, 3) if score is not None else None
        print(
            f"Zone {r.name}: pop={pop}, jobs={jobs}, "
            f"eh_index={score_rounded}, sens={direction_fr}"
        )

        if score is not None:
            scores.append((score, r.name))

        features.append(
            {
                "type": "Feature",
                "geometry": r.geometry,
                "properties": {
                    "id": r.id,
                    "name": r.name,
                    "population_proxy": pop,
                    "jobs_proxy": jobs,
                    "eh_index": score_rounded,
                    "imbalance": direction,
                    "imbalance_fr": direction_fr,
                },
            }
        )

    # --- Agrégats pour le panneau KPI ---
    if scores:
        values = [s for s, _ in scores]
        avg_score = round(sum(values) / len(values), 3)
        min_score, min_zone = min(scores, key=lambda x: x[0])
        max_score, max_zone = max(scores, key=lambda x: x[0])
        min_score = round(min_score, 3)
        max_score = round(max_score, 3)
    else:
        avg_score = min_score = max_score = None
        min_zone = max_zone = None

    print(
        f"Résumé M6 : n={len(scores)}, "
        f"avg={avg_score}, min={min_score} ({min_zone}), "
        f"max={max_score} ({max_zone})"
    )

    return {
        "type": "FeatureCollection",
        "features": features,
        "summary": {
            "zone_count": len(rows),
            "scored_count": len(scores),
            "avg_score": avg_score,
            "min_score": min_score,
            "max_score": max_score,
            "min_zone_name": min_zone,
            "max_zone_name": max_zone,
        },
        "formula": "eh_index = 1 - |jobs - population| / (jobs + population)",
        "synthetic": True,
        "note": (
            "Indice proxy intra-zone (pas de 2SFCA). "
            "1 = équilibre emplois/population, 0 = déséquilibre fort. "
            "Proxies synthétiques population_proxy / jobs_proxy."
        ),
    }
