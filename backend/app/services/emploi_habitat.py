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

from app.services.provenance import get_data_provenance


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
            "data_source": "none",
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
                    "eh_index_100": (
                        int(round(score * 100)) if score is not None else None
                    ),
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
    provenance = get_data_provenance(db)

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
        "synthetic": provenance["synthetic"],
        "data_source": provenance["data_source"],
        "note": (
            "Indice proxy intra-zone (pas de 2SFCA). "
            "1 = équilibre emplois/population, 0 = déséquilibre fort. "
            + provenance["note"]
        ),
    }

def _parse_grid_name(name: str) -> tuple[int, int] | None:
    """Zone A1 → (col=0, row=0). A=ouest, 1=sud."""
    parts = (name or "").split()
    if len(parts) < 2:
        return None
    token = parts[-1]
    if len(token) < 2:
        return None
    col = ord(token[0].upper()) - 65
    try:
        row = int(token[1:]) - 1
    except ValueError:
        return None
    if col < 0 or row < 0:
        return None
    return col, row


def get_diagnostic(db: Session) -> dict:
    """Déséquilibres N/S, E/O, centre/périphérie + secteurs d'activité synthétiques."""
    data = get_emploi_habitat(db)
    features = data.get("features") or []
    if not features:
        return {
            "axes": {},
            "dormitories": [],
            "disconnected_jobs": [],
            "sectors": [],
            "synthetic": True,
            "note": "Aucune zone.",
        }

    def _avg(subset: list[dict]) -> float | None:
        scores = [
            f["properties"]["eh_index"]
            for f in subset
            if f["properties"].get("eh_index") is not None
        ]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 3)

    north, south, east, west, center, peri = [], [], [], [], [], []
    dormitories = []
    disconnected = []

    for f in features:
        p = f["properties"]
        parsed = _parse_grid_name(p.get("name") or "")
        col, row = parsed if parsed else (1, 1)
        if row >= 2:
            north.append(f)
        else:
            south.append(f)
        if col >= 2:
            east.append(f)
        else:
            west.append(f)
        if col in (1, 2) and row in (1, 2):
            center.append(f)
        else:
            peri.append(f)

        pop, jobs = p.get("population_proxy") or 0, p.get("jobs_proxy") or 0
        if pop > jobs * 1.4:
            dormitories.append(
                {"id": p["id"], "name": p["name"], "population": pop, "jobs": jobs}
            )
        if jobs > pop * 1.4:
            disconnected.append(
                {"id": p["id"], "name": p["name"], "population": pop, "jobs": jobs}
            )

    sectors_def = [
        ("tertiaire", 0.40, "centre"),
        ("tech", 0.20, "centre"),
        ("soin", 0.15, "mixte"),
        ("admin", 0.15, "centre"),
        ("industrie", 0.10, "peri"),
    ]
    sectors = []
    for sector, share, loc in sectors_def:
        live = sorted(dormitories, key=lambda z: z["population"], reverse=True)[:3]
        work_src = center if loc == "centre" else peri
        work = [
            {
                "id": f["properties"]["id"],
                "name": f["properties"]["name"],
                "jobs_est": int(round((f["properties"]["jobs_proxy"] or 0) * share)),
            }
            for f in work_src[:4]
        ]
        sectors.append(
            {
                "sector": sector,
                "share": share,
                "live_zones": live,
                "work_zones": work,
                "note": "Répartition synthétique des proxies emplois.",
            }
        )

    return {
        "eh_index_100_avg": (
            round((data["summary"]["avg_score"] or 0) * 100)
            if data.get("summary", {}).get("avg_score") is not None
            else None
        ),
        "axes": {
            "north_south": {
                "north": _avg(north),
                "south": _avg(south),
                "label": "Nord / Sud",
            },
            "east_west": {
                "east": _avg(east),
                "west": _avg(west),
                "label": "Est / Ouest",
            },
            "center_periphery": {
                "center": _avg(center),
                "periphery": _avg(peri),
                "label": "Centre / périphérie",
            },
        },
        "dormitories": dormitories,
        "disconnected_jobs": disconnected,
        "sectors": sectors,
        "formula": data.get("formula"),
        "synthetic": True,
        "note": data.get("note"),
    }


def _dist_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    # approx degrés → km (lat Tana ~ -18.9)
    dlon = (a[0] - b[0]) * 111.32 * 0.95
    dlat = (a[1] - b[1]) * 110.57
    return (dlon**2 + dlat**2) ** 0.5


def get_satellite_sites(db: Session, zone_id: int | None = None, k: int = 5) -> dict:
    """
    Candidats bureaux satellites : barycentre pondéré des bassins résidentiels
    + greedy p-médianes simplifié.
    """
    from sqlalchemy import text

    k = max(3, min(5, int(k)))
    zone_rows = db.execute(
        text(
            """
            SELECT
                id, name,
                COALESCE(population_proxy, 0) AS population_proxy,
                COALESCE(jobs_proxy, 0) AS jobs_proxy,
                ST_X(ST_Centroid(geometry)) AS lon,
                ST_Y(ST_Centroid(geometry)) AS lat,
                ST_AsGeoJSON(geometry)::json AS geometry
            FROM mobility_zones
            ORDER BY jobs_proxy DESC
            """
        )
    ).fetchall()
    if not zone_rows:
        return {"candidates": [], "note": "Aucune zone.", "synthetic": True}

    zones = {int(z.id): z for z in zone_rows}
    if zone_id is None or int(zone_id) not in zones:
        anchor = zone_rows[0]
    else:
        anchor = zones[int(zone_id)]
    aid = int(anchor.id)
    axy = (float(anchor.lon), float(anchor.lat))

    flows = db.execute(
        text(
            """
            SELECT origin_zone_id, passenger_count, average_distance
            FROM v_od_desire_lines
            WHERE destination_zone_id = :zid AND passenger_count >= 5
            ORDER BY passenger_count DESC
            """
        ),
        {"zid": aid},
    ).fetchall()

    basins = []
    wlon = wlat = wsum = 0.0
    for f in flows:
        oz = zones.get(int(f.origin_zone_id))
        if not oz:
            continue
        dist = float(f.average_distance or 0)
        vol = int(f.passenger_count)
        item = {
            "zone_id": int(oz.id),
            "name": oz.name,
            "volume": vol,
            "distance_km": dist,
            "lon": float(oz.lon),
            "lat": float(oz.lat),
            "costly": dist >= 6.0,
        }
        basins.append(item)
        if item["costly"]:
            wlon += oz.lon * vol
            wlat += oz.lat * vol
            wsum += vol

    if wsum > 0:
        bary = (wlon / wsum, wlat / wsum)
    else:
        bary = axy

    # greedy : choisir k zones (hors ancre) minimisant somme volume*dist au site
    remaining = [z for z in zone_rows if int(z.id) != aid]
    chosen: list = []
    for _ in range(min(k, len(remaining))):
        best = None
        best_score = None
        for z in remaining:
            zxy = (float(z.lon), float(z.lat))
            # score = proximité barycentre + desserte proxy (jobs faibles = foncier) + pop
            d_bar = _dist_km(zxy, bary)
            foncier = 1.0 / (1.0 + (z.jobs_proxy or 0) / 8000.0)
            tc = 1.0 if (z.jobs_proxy or 0) > 5000 else 0.6
            impact = 0.0
            for b in basins:
                if not b["costly"]:
                    continue
                d_now = _dist_km((b["lon"], b["lat"]), axy)
                d_new = _dist_km((b["lon"], b["lat"]), zxy)
                impact += b["volume"] * max(0.0, d_now - d_new)
            score = impact * 0.7 + (8.0 - min(d_bar, 8.0)) * 40 + foncier * 80 + tc * 30
            if best_score is None or score > best_score:
                best_score = score
                best = z
        if best is None:
            break
        remaining = [z for z in remaining if int(z.id) != int(best.id)]
        chosen.append((best, best_score))

    types = [
        "bureau_satellite",
        "tiers_lieu",
        "zone_activites",
        "pole_tertiaire",
        "hub_gare",
        "mixite",
    ]
    type_labels = {
        "bureau_satellite": "Bureau satellite d'entreprise",
        "tiers_lieu": "Tiers-lieu mutualisé",
        "zone_activites": "Zone d'activités décentralisée",
        "pole_tertiaire": "Pôle tertiaire de proximité",
        "hub_gare": "Hub d'entreprises en gare",
        "mixite": "Mixité fonctionnelle",
    }

    candidates = []
    for i, (z, score) in enumerate(chosen):
        t = types[i % len(types)]
        km_saved = round((score or 0) * 0.08, 1)
        candidates.append(
            {
                "rank": i + 1,
                "zone_id": int(z.id),
                "name": z.name,
                "type": t,
                "type_label": type_labels[t],
                "impact_score": int(max(10, min(98, (score or 0) / 80))),
                "km_saved_proxy": km_saved,
                "constraints": {
                    "foncier": "disponible (proxy)" if (z.jobs_proxy or 0) < 12000 else "tendu",
                    "desserte_tc": "correcte (proxy centre)" if (z.jobs_proxy or 0) > 6000 else "à renforcer",
                    "plu": "compatible (hypothèse démo)",
                    "prix_tertiaire": round(0.55 + (z.jobs_proxy or 0) / 40000.0, 2),
                },
                "lon": float(z.lon),
                "lat": float(z.lat),
                "geometry": z.geometry,
            }
        )

    return {
        "anchor": {
            "id": aid,
            "name": anchor.name,
            "jobs_proxy": int(anchor.jobs_proxy or 0),
            "lon": float(anchor.lon),
            "lat": float(anchor.lat),
        },
        "residential_basins": basins[:12],
        "barycenter": {"lon": round(bary[0], 6), "lat": round(bary[1], 6)},
        "candidates": candidates,
        "method": (
            "Barycentre pondéré des bassins distants (>= 6 km) puis greedy "
            "type p-médianes (k=3..5). Contraintes foncier/TC/PLU = proxies."
        ),
        "synthetic": True,
        "note": (
            "Probabilité de relocalisation non calibrée sur enquête salariés. "
            "Classement par impact mobilité estimé."
        ),
    }


def get_telework_impact(
    db: Session,
    rate: float = 0.20,
    pattern: str = "hybrid_1_2",
    combine_satellite: bool = False,
    satellite_zone_id: int | None = None,
) -> dict:
    from app.services.simulation import simulate

    rate = max(0.0, min(0.8, float(rate)))
    result = simulate(
        db,
        action="telework",
        intensity=0.25,
        telework_rate=rate,
        telework_pattern=pattern,
    )
    combined = None
    if combine_satellite:
        sat = simulate(
            db,
            action="add_satellite_office",
            zone_id=satellite_zone_id,
            intensity=0.35,
        )
        combined = {
            "km": round(result["scenario"]["km"] * 0.92, 1),
            "co2_t": round(result["scenario"]["co2_t"] * 0.90, 2),
            "time_h": round(result["scenario"]["time_h"] * 0.90, 1),
            "note": "Synergie forfaitaire télétravail × bureau satellite (−8 à −10 % km restants).",
            "satellite_action": sat["action_label"],
        }

    return {
        "rate": rate,
        "pattern": pattern,
        "baseline": result["baseline"],
        "scenario": result["scenario"],
        "comparison": result["comparison"],
        "combined_satellite": combined,
        "sector_rates": {
            "tertiaire": round(rate * 1.2, 2),
            "tech": round(min(0.8, rate * 1.4), 2),
            "soin": round(rate * 0.4, 2),
            "admin": round(rate * 1.1, 2),
            "industrie": round(rate * 0.2, 2),
        },
        "synthetic": True,
        "note": (
            "Le télétravail seul peut, à moyen terme, favoriser des migrations "
            "résidentielles plus lointaines — non modélisées ici."
        ),
    }
