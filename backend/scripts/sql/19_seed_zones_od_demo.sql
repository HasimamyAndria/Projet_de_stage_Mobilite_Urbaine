-- ============================================================
-- 19_seed_zones_od_demo.sql
-- Peuplement MVP : grille de zones + flux OD gravitaires
-- Aligné sur le schéma réel :
--   mobility_zones(id, name, geometry MultPolygon 4326, ...)
--   mobility_flows(origin_zone_id, destination_zone_id, trip_count, ...)
-- Idempotent : crée les tables si absentes (ex. Docker DB neuve)
-- ============================================================

-- Schéma de base (si base vide / compose)
CREATE TABLE IF NOT EXISTS mobility_zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    geometry geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS mobility_flows (
    id SERIAL PRIMARY KEY,
    origin_zone_id INTEGER NOT NULL,
    destination_zone_id INTEGER NOT NULL,
    trip_count INTEGER DEFAULT 0,
    average_distance NUMERIC,
    average_time NUMERIC
);

-- Enrichir mobility_zones (idempotent)
ALTER TABLE mobility_zones
    ADD COLUMN IF NOT EXISTS zone_type VARCHAR(50);

ALTER TABLE mobility_zones
    ADD COLUMN IF NOT EXISTS population_proxy INTEGER DEFAULT 0;

ALTER TABLE mobility_zones
    ADD COLUMN IF NOT EXISTS jobs_proxy INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS mobility_zones_geometry_idx
ON mobility_zones
USING GIST (geometry);

-- Enrichir mobility_flows
ALTER TABLE mobility_flows
    ADD COLUMN IF NOT EXISTS mode VARCHAR(30) DEFAULT 'all';

ALTER TABLE mobility_flows
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Reset données démo
TRUNCATE TABLE mobility_flows RESTART IDENTITY;
DELETE FROM mobility_zones WHERE zone_type = 'grid_demo' OR zone_type IS NULL;

-- Bbox urbaine Antananarivo (fixe) - evite l'emprise pays de l'extract OSM
-- Centre approx 47.508, -18.879 - emprise ~12km x 14km
WITH box AS (
    SELECT
        47.450::float8 AS xmin,
        -18.950::float8 AS ymin,
        47.565::float8 AS xmax,
        -18.820::float8 AS ymax
),
grid AS (
    SELECT
        gi.i,
        gj.j,
        ST_MakeEnvelope(
            box.xmin + (box.xmax - box.xmin) * gi.i / 4.0,
            box.ymin + (box.ymax - box.ymin) * gj.j / 4.0,
            box.xmin + (box.xmax - box.xmin) * (gi.i + 1) / 4.0,
            box.ymin + (box.ymax - box.ymin) * (gj.j + 1) / 4.0,
            4326
        ) AS cell
    FROM box
    CROSS JOIN generate_series(0, 3) AS gi(i)
    CROSS JOIN generate_series(0, 3) AS gj(j)
),
named AS (
    SELECT
        ('Zone ' || chr(65 + i) || (j + 1)::text) AS name,
        'grid_demo' AS zone_type,
        (8000 + 12000 * (1.0 - abs(i - 1.5) / 2.0) * (1.0 - abs(j - 1.5) / 2.0))::int
            AS population_proxy,
        (3000 + 15000 * (1.0 - abs(i - 2.0) / 2.5) * (1.0 - abs(j - 1.5) / 2.0))::int
            AS jobs_proxy,
        ST_Multi(cell)::geometry(MultiPolygon, 4326) AS geometry
    FROM grid
)
INSERT INTO mobility_zones (name, zone_type, population_proxy, jobs_proxy, geometry)
SELECT name, zone_type, population_proxy, jobs_proxy, geometry
FROM named;

-- Flux OD synthétiques (gravitaire), coefficient calibré pour échelle urbaine
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
                    ST_DistanceSphere(ST_Centroid(o.geometry), ST_Centroid(d.geometry)),
                    500.0
                ),
                1.35
            ) * 0.06
        )::int
    ) AS trip_count,
    ROUND(
        (ST_DistanceSphere(ST_Centroid(o.geometry), ST_Centroid(d.geometry)) / 1000.0)::numeric,
        2
    ) AS average_distance,
    ROUND(
        (ST_DistanceSphere(ST_Centroid(o.geometry), ST_Centroid(d.geometry)) / 1000.0 / 22.0 * 60.0)::numeric,
        1
    ) AS average_time,
    'all' AS mode
FROM mobility_zones o
CROSS JOIN mobility_zones d
WHERE o.zone_type = 'grid_demo'
  AND d.zone_type = 'grid_demo'
  AND o.id <> d.id
  AND (
        (o.population_proxy::float * d.jobs_proxy::float)
        / POWER(
            GREATEST(
                ST_DistanceSphere(ST_Centroid(o.geometry), ST_Centroid(d.geometry)),
                500.0
            ),
            1.35
        ) * 0.06
      ) >= 20;

DROP VIEW IF EXISTS v_od_desire_lines;
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
JOIN mobility_zones dz ON dz.id = f.destination_zone_id;

SELECT COUNT(*) AS nb_zones FROM mobility_zones WHERE zone_type = 'grid_demo';
SELECT COUNT(*) AS nb_flows FROM mobility_flows;
SELECT COALESCE(SUM(trip_count), 0) AS total_trips FROM mobility_flows;
