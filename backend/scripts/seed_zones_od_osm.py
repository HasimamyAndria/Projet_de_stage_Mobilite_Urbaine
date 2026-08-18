# -*- coding: utf-8 -*-
"""
Peuplement OD à partir d'OSM réel (Antananarivo).

- Zones : Voronoi sur lieux OSM (suburb / quarter), emprise bbox urbaine
- population_proxy : bâtiments OSM dans la zone (× facteur habitants)
- jobs_proxy : POI emploi OSM (office / shop / amenity) + landuse commercial
- Flux OD : modèle gravitaire calibré sur ces proxies réels (k >= 5)

Prérequis : tables planet_osm_* déjà importées (osm2pgsql).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

# Bbox urbaine Antananarivo (même emprise que l'ancienne grille démo)
XMIN, YMIN, XMAX, YMAX = 47.450, -18.950, 47.565, -18.820
ZONE_TYPE = "osm_suburb"
POP_PER_BUILDING = 4
JOB_WEIGHT_POI = 8
JOB_WEIGHT_LANDUSE = 25
DEFAULT_TOP_N = 36
GRAVITY_SCALE = 0.045
GRAVITY_EXP = 1.35
MIN_TRIP_KEEP = 20  # aligné seuil UI / k-anonymité métier


def _db_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    # Hors Docker : le hostname "db" du compose ne résout pas
    if host == "db" and not Path("/.dockerenv").exists():
        host = "localhost"
    return (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{host}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


def _ensure_schema(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS mobility_zones (
                id SERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                geometry geometry(MultiPolygon, 4326)
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS mobility_flows (
                id SERIAL PRIMARY KEY,
                origin_zone_id INTEGER NOT NULL,
                destination_zone_id INTEGER NOT NULL,
                trip_count INTEGER DEFAULT 0,
                average_distance NUMERIC,
                average_time NUMERIC
            )
            """
        )
    )
    for stmt in (
        "ALTER TABLE mobility_zones ADD COLUMN IF NOT EXISTS zone_type VARCHAR(50)",
        "ALTER TABLE mobility_zones ADD COLUMN IF NOT EXISTS population_proxy INTEGER DEFAULT 0",
        "ALTER TABLE mobility_zones ADD COLUMN IF NOT EXISTS jobs_proxy INTEGER DEFAULT 0",
        "ALTER TABLE mobility_flows ADD COLUMN IF NOT EXISTS mode VARCHAR(30) DEFAULT 'all'",
        "ALTER TABLE mobility_flows ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        """
        CREATE INDEX IF NOT EXISTS mobility_zones_geometry_idx
        ON mobility_zones USING GIST (geometry)
        """,
    ):
        conn.execute(text(stmt))


def _require_osm(conn) -> None:
    n = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'planet_osm_point'
            """
        )
    ).scalar()
    if not n:
        raise RuntimeError(
            "Tables OSM absentes (planet_osm_*). Importer d'abord le PBF "
            "avec osm2pgsql, puis relancer ce script."
        )
    pts = conn.execute(text("SELECT COUNT(*) FROM planet_osm_point")).scalar()
    if not pts:
        raise RuntimeError("planet_osm_point est vide — import OSM requis.")


def seed(
    top_n: int = DEFAULT_TOP_N,
    xmin: float | None = None,
    ymin: float | None = None,
    xmax: float | None = None,
    ymax: float | None = None,
) -> dict:
    """
    Peuple mobility_zones / mobility_flows pour une bbox urbaine.
    Retourne un dict de stats (zones, flows, trips, bbox).
    """
    xmin = float(XMIN if xmin is None else xmin)
    ymin = float(YMIN if ymin is None else ymin)
    xmax = float(XMAX if xmax is None else xmax)
    ymax = float(YMAX if ymax is None else ymax)
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("Bbox invalide (xmax<=xmin ou ymax<=ymin).")

    engine = create_engine(_db_url())
    print(f"Seed OSM réel — top_n={top_n}, bbox=({xmin},{ymin})-({xmax},{ymax})")

    with engine.begin() as conn:
        _ensure_schema(conn)
        _require_osm(conn)

        # Reset analytics (changement de ville / nouveau peuplement)
        conn.execute(text("TRUNCATE TABLE mobility_flows RESTART IDENTITY"))
        conn.execute(text("DELETE FROM mobility_zones"))

        # Centroïdes bâtiments (une fois, indexés)
        print("… extraction bâtiments OSM (bbox)")
        conn.execute(text("DROP TABLE IF EXISTS tmp_osm_build_pts"))
        conn.execute(
            text(
                """
                CREATE TEMP TABLE tmp_osm_build_pts AS
                SELECT ST_Transform(ST_PointOnSurface(way), 4326) AS geom
                FROM planet_osm_polygon
                WHERE building IS NOT NULL
                  AND way && ST_Transform(
                      ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326),
                      3857
                  )
                """
            ),
            {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        )
        conn.execute(
            text("CREATE INDEX tmp_osm_build_pts_gix ON tmp_osm_build_pts USING GIST (geom)")
        )
        n_build = conn.execute(text("SELECT COUNT(*) FROM tmp_osm_build_pts")).scalar()
        print(f"   bâtiments = {n_build}")
        if int(n_build or 0) < 50:
            raise RuntimeError(
                "Trop peu de bâtiments OSM dans cette bbox — "
                "importer un extract OSM de la ville (osm2pgsql)."
            )

        # POI emplois
        print("… extraction POI emplois OSM")
        conn.execute(text("DROP TABLE IF EXISTS tmp_osm_job_pts"))
        conn.execute(
            text(
                """
                CREATE TEMP TABLE tmp_osm_job_pts AS
                SELECT ST_Transform(way, 4326) AS geom, 1 AS w
                FROM planet_osm_point
                WHERE (
                        office IS NOT NULL
                        OR shop IS NOT NULL
                        OR amenity IN (
                            'townhall', 'university', 'hospital', 'school',
                            'college', 'bank', 'marketplace', 'restaurant',
                            'cafe', 'fuel', 'bus_station', 'police',
                            'post_office', 'clinic', 'pharmacy'
                        )
                      )
                  AND ST_Transform(way, 4326) &&
                      ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326)
                """
            ),
            {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        )
        conn.execute(
            text("CREATE INDEX tmp_osm_job_pts_gix ON tmp_osm_job_pts USING GIST (geom)")
        )
        n_jobs = conn.execute(text("SELECT COUNT(*) FROM tmp_osm_job_pts")).scalar()
        print(f"   POI emplois = {n_jobs}")

        # Landuse commercial / industriel (centroïdes)
        conn.execute(text("DROP TABLE IF EXISTS tmp_osm_land_jobs"))
        conn.execute(
            text(
                """
                CREATE TEMP TABLE tmp_osm_land_jobs AS
                SELECT ST_Transform(ST_PointOnSurface(way), 4326) AS geom
                FROM planet_osm_polygon
                WHERE landuse IN ('commercial', 'industrial', 'retail')
                  AND way && ST_Transform(
                      ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326),
                      3857
                  )
                """
            ),
            {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        )
        conn.execute(
            text("CREATE INDEX tmp_osm_land_jobs_gix ON tmp_osm_land_jobs USING GIST (geom)")
        )

        # Sélection des lieux OSM les plus denses (réels)
        print("… ranking lieux OSM (suburb/quarter)")
        conn.execute(text("DROP TABLE IF EXISTS tmp_osm_place_seeds"))
        conn.execute(
            text(
                """
                CREATE TEMP TABLE tmp_osm_place_seeds AS
                WITH places AS (
                    SELECT
                        osm_id,
                        name,
                        place,
                        ST_Transform(way, 4326) AS geom
                    FROM planet_osm_point
                    WHERE place IN ('suburb', 'quarter')
                      AND name IS NOT NULL
                      AND ST_Transform(way, 4326) &&
                          ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326)
                ),
                scored AS (
                    SELECT
                        p.osm_id,
                        p.name,
                        p.place,
                        p.geom,
                        (
                            SELECT COUNT(*)
                            FROM tmp_osm_build_pts b
                            WHERE b.geom && ST_Expand(p.geom, 0.0065)
                        ) AS nearby_buildings
                    FROM places p
                ),
                ranked AS (
                    SELECT
                        osm_id,
                        name,
                        place,
                        geom,
                        nearby_buildings,
                        ROW_NUMBER() OVER (
                            ORDER BY nearby_buildings DESC, name
                        ) AS rn
                    FROM scored
                    WHERE nearby_buildings > 0
                )
                SELECT osm_id, name, place, geom, nearby_buildings
                FROM ranked
                WHERE rn <= :top_n
                """
            ),
            {
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "top_n": top_n,
            },
        )
        n_seeds = conn.execute(text("SELECT COUNT(*) FROM tmp_osm_place_seeds")).scalar()
        if n_seeds < 3:
            raise RuntimeError(
                f"Pas assez de lieux OSM densés dans la bbox (n={n_seeds}). "
                "Importer un extract OSM de la ville, ou élargir la bbox."
            )
        print(f"   graines retenues = {n_seeds}")

        # Voronoi clipé à la bbox
        print("… Voronoi + proxies par zone")
        conn.execute(text("DROP TABLE IF EXISTS tmp_osm_zones"))
        conn.execute(
            text(
                """
                CREATE TEMP TABLE tmp_osm_zones AS
                WITH envelope AS (
                    SELECT ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326) AS geom
                ),
                vor AS (
                    SELECT (ST_Dump(
                        ST_VoronoiPolygons(
                            (SELECT ST_Collect(geom) FROM tmp_osm_place_seeds),
                            0.0,
                            (SELECT geom FROM envelope)
                        )
                    )).geom AS cell
                ),
                assigned AS (
                    SELECT
                        s.osm_id,
                        s.name,
                        s.place,
                        ST_Multi(
                            ST_CollectionExtract(
                                ST_Intersection(v.cell, e.geom),
                                3
                            )
                        )::geometry(MultiPolygon, 4326) AS geometry
                    FROM vor v
                    JOIN tmp_osm_place_seeds s ON ST_Intersects(v.cell, s.geom)
                    CROSS JOIN envelope e
                    WHERE NOT ST_IsEmpty(
                        ST_Intersection(v.cell, e.geom)
                    )
                ),
                dedup AS (
                    SELECT DISTINCT ON (osm_id)
                        osm_id,
                        name,
                        place,
                        geometry
                    FROM assigned
                    WHERE geometry IS NOT NULL
                      AND NOT ST_IsEmpty(geometry)
                    ORDER BY osm_id, ST_Area(geometry::geography) DESC
                )
                SELECT
                    osm_id,
                    CASE
                        WHEN COUNT(*) OVER (PARTITION BY name) > 1
                        THEN name || ' (' || place || ')'
                        ELSE name
                    END AS name,
                    place,
                    geometry,
                    (
                        SELECT COUNT(*)
                        FROM tmp_osm_build_pts b
                        WHERE ST_Contains(d.geometry, b.geom)
                    ) AS building_count,
                    (
                        SELECT COUNT(*)
                        FROM tmp_osm_job_pts j
                        WHERE ST_Contains(d.geometry, j.geom)
                    ) AS job_poi_count,
                    (
                        SELECT COUNT(*)
                        FROM tmp_osm_land_jobs l
                        WHERE ST_Contains(d.geometry, l.geom)
                    ) AS landuse_job_count
                FROM dedup d
                """
            ),
            {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        )

        inserted = conn.execute(
            text(
                """
                INSERT INTO mobility_zones (
                    name, zone_type, population_proxy, jobs_proxy, geometry
                )
                SELECT
                    LEFT(name, 150),
                    :zt,
                    GREATEST(building_count * :pop_factor, 50)::int,
                    GREATEST(
                        job_poi_count * :job_poi + landuse_job_count * :job_land,
                        20
                    )::int,
                    geometry
                FROM tmp_osm_zones
                WHERE geometry IS NOT NULL
                  AND NOT ST_IsEmpty(geometry)
                RETURNING id, name, population_proxy, jobs_proxy
                """
            ),
            {
                "zt": ZONE_TYPE,
                "pop_factor": POP_PER_BUILDING,
                "job_poi": JOB_WEIGHT_POI,
                "job_land": JOB_WEIGHT_LANDUSE,
            },
        ).fetchall()
        print(f"   zones insérées = {len(inserted)}")
        for row in inserted[:8]:
            print(
                f"      {row.name}: pop~{row.population_proxy}, "
                f"jobs~{row.jobs_proxy}"
            )
        if len(inserted) > 8:
            print(f"      … +{len(inserted) - 8} zones")

        # Flux gravitaires (structure spatiale réelle)
        print("… flux OD gravitaires (proxies OSM)")
        flows = conn.execute(
            text(
                """
                INSERT INTO mobility_flows (
                    origin_zone_id,
                    destination_zone_id,
                    trip_count,
                    average_distance,
                    average_time,
                    mode
                )
                SELECT
                    o.id,
                    d.id,
                    GREATEST(
                        15,
                        ROUND(
                            (o.population_proxy::float * d.jobs_proxy::float)
                            / POWER(
                                GREATEST(
                                    ST_DistanceSphere(
                                        ST_Centroid(o.geometry),
                                        ST_Centroid(d.geometry)
                                    ),
                                    500.0
                                ),
                                :exp
                            ) * :scale
                        )::int
                    ) AS trip_count,
                    ROUND(
                        (
                            ST_DistanceSphere(
                                ST_Centroid(o.geometry),
                                ST_Centroid(d.geometry)
                            ) / 1000.0
                        )::numeric,
                        2
                    ) AS average_distance,
                    ROUND(
                        (
                            ST_DistanceSphere(
                                ST_Centroid(o.geometry),
                                ST_Centroid(d.geometry)
                            ) / 1000.0 / 22.0 * 60.0
                        )::numeric,
                        1
                    ) AS average_time,
                    'all' AS mode
                FROM mobility_zones o
                CROSS JOIN mobility_zones d
                WHERE o.zone_type = :zt
                  AND d.zone_type = :zt
                  AND o.id <> d.id
                  AND (
                        (o.population_proxy::float * d.jobs_proxy::float)
                        / POWER(
                            GREATEST(
                                ST_DistanceSphere(
                                    ST_Centroid(o.geometry),
                                    ST_Centroid(d.geometry)
                                ),
                                500.0
                            ),
                            :exp
                        ) * :scale
                      ) >= :min_keep
                RETURNING id
                """
            ),
            {
                "zt": ZONE_TYPE,
                "exp": GRAVITY_EXP,
                "scale": GRAVITY_SCALE,
                "min_keep": MIN_TRIP_KEEP,
            },
        ).fetchall()
        print(f"   flux OD = {len(flows)}")

        conn.execute(text("DROP VIEW IF EXISTS v_od_desire_lines"))
        conn.execute(
            text(
                """
                CREATE VIEW v_od_desire_lines AS
                SELECT
                    f.id,
                    f.origin_zone_id,
                    f.destination_zone_id,
                    oz.name AS origin_name,
                    dz.name AS destination_name,
                    f.trip_count AS passenger_count,
                    COALESCE(f.mode, 'all') AS mode,
                    f.average_distance,
                    f.average_time,
                    ST_MakeLine(
                        ST_Centroid(oz.geometry),
                        ST_Centroid(dz.geometry)
                    )::geometry(LineString, 4326) AS geom
                FROM mobility_flows f
                JOIN mobility_zones oz ON oz.id = f.origin_zone_id
                JOIN mobility_zones dz ON dz.id = f.destination_zone_id
                """
            )
        )

        zones = conn.execute(
            text("SELECT COUNT(*) FROM mobility_zones WHERE zone_type = :zt"),
            {"zt": ZONE_TYPE},
        ).scalar()
        trips = conn.execute(
            text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")
        ).scalar()

    stats = {
        "zones": int(zones or 0),
        "flows": len(flows),
        "trips": int(trips or 0),
        "buildings": int(n_build or 0),
        "job_pois": int(n_jobs or 0),
        "bbox": {
            "west": xmin,
            "south": ymin,
            "east": xmax,
            "north": ymax,
        },
    }
    print(
        f"OK seed OSM -> zones={stats['zones']}, "
        f"flows={stats['flows']}, trips={stats['trips']}"
    )
    print("Source : OpenStreetMap (batiments + POI + lieux) — OD estimee (gravitaire).")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OD depuis OSM réel")
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Nombre de quartiers OSM retenus (défaut {DEFAULT_TOP_N})",
    )
    parser.add_argument("--xmin", type=float, default=None)
    parser.add_argument("--ymin", type=float, default=None)
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ymax", type=float, default=None)
    args = parser.parse_args()
    try:
        seed(
            top_n=max(3, args.top_n),
            xmin=args.xmin,
            ymin=args.ymin,
            xmax=args.xmax,
            ymax=args.ymax,
        )
    except Exception as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
