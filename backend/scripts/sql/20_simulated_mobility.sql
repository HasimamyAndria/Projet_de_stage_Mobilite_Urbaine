-- Catalogue simulé, séparé des tables OSM et de la matrice gravitaire.
-- Les géométries sont des emprises de travail (cercles), pas un cadastre.
-- SRID 4326, comme les sorties de l'API.

CREATE TABLE IF NOT EXISTS sim_zones (
    id text PRIMARY KEY,
    city_id text NOT NULL,
    name text NOT NULL,
    level text NOT NULL,
    level_label text,
    parent_id text,
    role text,
    lon double precision,
    lat double precision,
    geometry geometry(Polygon, 4326)
);

CREATE INDEX IF NOT EXISTS sim_zones_gix ON sim_zones USING GIST (geometry);
CREATE INDEX IF NOT EXISTS sim_zones_city_idx ON sim_zones (city_id, level);

CREATE TABLE IF NOT EXISTS sim_companies (
    id text PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL,
    kind_label text,
    city_id text NOT NULL,
    seat_id text NOT NULL,
    activity text,
    employee_count integer NOT NULL
);

CREATE TABLE IF NOT EXISTS sim_persons (
    person_id text PRIMARY KEY,
    city_id text NOT NULL,
    residence_id text NOT NULL,
    arrondissement_id text,
    company_id text,
    job_label text,
    sector text,
    mode text,
    work_id text,
    distance_km numeric,
    time_min numeric,
    frequency text,
    purpose text,
    source text NOT NULL
);

CREATE INDEX IF NOT EXISTS sim_persons_company_idx ON sim_persons (company_id);
CREATE INDEX IF NOT EXISTS sim_persons_home_idx ON sim_persons (residence_id);

CREATE TABLE IF NOT EXISTS sim_trips (
    trip_id text PRIMARY KEY,
    city_id text NOT NULL,
    person_id text,
    group_size integer NOT NULL,
    origin_id text NOT NULL,
    destination_id text NOT NULL,
    purpose text NOT NULL,
    frequency text NOT NULL,
    distance_km numeric NOT NULL,
    duration_min numeric NOT NULL,
    period text NOT NULL,
    mode text NOT NULL,
    company_id text,
    synthetic boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS sim_trips_od_idx ON sim_trips (origin_id, destination_id);

CREATE TABLE IF NOT EXISTS sim_indicators (
    city_id text NOT NULL,
    zone_id text NOT NULL,
    indicator_id text NOT NULL,
    value numeric,
    unit text,
    PRIMARY KEY (city_id, zone_id, indicator_id)
);

CREATE TABLE IF NOT EXISTS sim_clusters (
    person_id text PRIMARY KEY,
    city_id text NOT NULL,
    cluster_id integer NOT NULL,
    cluster_label text NOT NULL
);

CREATE TABLE IF NOT EXISTS sim_scenarios (
    id bigserial PRIMARY KEY,
    organization_id text,
    scenario text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL
);
