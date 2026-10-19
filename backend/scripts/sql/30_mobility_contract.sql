-- Migration 30_mobility_contract
-- Contrat des déplacements individuels. Additive et idempotente.
-- Aucun DROP, DELETE, TRUNCATE, ni mise à jour des tables déjà peuplées.
--
-- Ne référence pas mobility_zones, mobility_flows, zones, ni sim_*.
-- Leurs identifiants entiers sont recréés par les seeds existants.
--
-- La ligne de version est insérée par backend/scripts/apply_sql_migration.py
-- dans la même transaction que ce script.
--
-- Référentiels distincts, à ne pas fusionner :
--   ref_purposes / ref_modes  vocabulaire du prototype entier (od_matrix)
--   purposes / modes          vocabulaire canonique de ce contrat

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    label TEXT NOT NULL,
    seed INTEGER,
    anchor_monday DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT datasets_id_source_unique UNIQUE (id, source),
    CONSTRAINT datasets_source_check CHECK (source IN ('SIMULATED', 'OBSERVED')),
    CONSTRAINT datasets_label_check CHECK (char_length(btrim(label)) > 0),
    CONSTRAINT datasets_seed_check CHECK (seed IS NULL OR seed >= 0),
    CONSTRAINT datasets_anchor_monday_check CHECK (
        anchor_monday IS NULL OR EXTRACT(ISODOW FROM anchor_monday) = 1
    )
);

CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    city_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL,
    level_label TEXT,
    role TEXT NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    boundary_kind TEXT NOT NULL DEFAULT 'point_catalog',
    CONSTRAINT places_parent_fkey
        FOREIGN KEY (parent_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT places_city_fkey
        FOREIGN KEY (city_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT places_name_check CHECK (char_length(btrim(name)) > 0),
    CONSTRAINT places_level_check CHECK (level IN ('city', 'commune', 'quartier')),
    CONSTRAINT places_role_check CHECK (
        role IN ('ville', 'habitat', 'emploi', 'commerce', 'equipement', 'mixte')
    ),
    CONSTRAINT places_boundary_kind_check CHECK (boundary_kind = 'point_catalog'),
    CONSTRAINT places_lon_check CHECK (lon >= -180 AND lon <= 180),
    CONSTRAINT places_lat_check CHECK (lat >= -90 AND lat <= 90),
    CONSTRAINT places_level_parent_check CHECK (
        (level = 'city' AND parent_id IS NULL AND city_id = id)
        OR (level IN ('commune', 'quartier') AND parent_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS places_city_level_idx ON places (city_id, level);
CREATE INDEX IF NOT EXISTS places_parent_idx ON places (parent_id);

CREATE TABLE IF NOT EXISTS purposes (
    code TEXT PRIMARY KEY,
    label_fr TEXT NOT NULL,
    CONSTRAINT purposes_label_check CHECK (char_length(btrim(label_fr)) > 0)
);

CREATE TABLE IF NOT EXISTS modes (
    code TEXT PRIMARY KEY,
    label_fr TEXT NOT NULL,
    CONSTRAINT modes_label_check CHECK (char_length(btrim(label_fr)) > 0)
);

CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    display_name TEXT,
    city_id TEXT NOT NULL,
    home_place_id TEXT NOT NULL,
    work_place_id TEXT,
    activity TEXT,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT persons_person_dataset_unique UNIQUE (person_id, dataset_id),
    CONSTRAINT persons_dataset_source_fkey
        FOREIGN KEY (dataset_id, source) REFERENCES datasets (id, source)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT persons_city_fkey
        FOREIGN KEY (city_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT persons_home_fkey
        FOREIGN KEY (home_place_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT persons_work_fkey
        FOREIGN KEY (work_place_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT persons_source_check CHECK (source IN ('SIMULATED', 'OBSERVED')),
    CONSTRAINT persons_display_name_check CHECK (
        display_name IS NULL OR char_length(btrim(display_name)) > 0
    )
);

CREATE INDEX IF NOT EXISTS persons_dataset_idx ON persons (dataset_id);
CREATE INDEX IF NOT EXISTS persons_home_idx ON persons (home_place_id);

CREATE TABLE IF NOT EXISTS surveys (
    id TEXT PRIMARY KEY,
    dataset_id TEXT,
    title TEXT NOT NULL,
    period_start DATE,
    period_end DATE,
    questionnaire_version TEXT,
    validation_status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT surveys_dataset_fkey
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT surveys_title_check CHECK (char_length(btrim(title)) > 0),
    CONSTRAINT surveys_status_check CHECK (
        validation_status IN ('draft', 'validated', 'closed')
    ),
    CONSTRAINT surveys_period_check CHECK (
        period_start IS NULL OR period_end IS NULL OR period_end >= period_start
    )
);

CREATE INDEX IF NOT EXISTS surveys_dataset_idx ON surveys (dataset_id);

CREATE TABLE IF NOT EXISTS import_batches (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT,
    dataset_id TEXT,
    source TEXT NOT NULL,
    filename TEXT,
    status TEXT NOT NULL DEFAULT 'received',
    error_report JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT import_batches_survey_fkey
        FOREIGN KEY (survey_id) REFERENCES surveys (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT import_batches_dataset_fkey
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT import_batches_source_check CHECK (source IN ('SIMULATED', 'OBSERVED')),
    CONSTRAINT import_batches_status_check CHECK (
        status IN ('received', 'rejected', 'validated', 'cancelled')
    )
);

CREATE INDEX IF NOT EXISTS import_batches_survey_idx ON import_batches (survey_id);
CREATE INDEX IF NOT EXISTS import_batches_dataset_idx ON import_batches (dataset_id);

CREATE TABLE IF NOT EXISTS import_rows (
    id BIGSERIAL PRIMARY KEY,
    batch_id BIGINT NOT NULL,
    row_number INTEGER NOT NULL,
    raw JSONB NOT NULL,
    CONSTRAINT import_rows_batch_fkey
        FOREIGN KEY (batch_id) REFERENCES import_batches (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT import_rows_batch_row_unique UNIQUE (batch_id, row_number),
    CONSTRAINT import_rows_row_number_check CHECK (row_number > 0)
);

CREATE INDEX IF NOT EXISTS import_rows_batch_idx ON import_rows (batch_id);

CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    trip_date DATE NOT NULL,
    depart_time TIME NOT NULL,
    arrive_time TIME NOT NULL,
    origin_place_id TEXT NOT NULL,
    destination_place_id TEXT NOT NULL,
    purpose_code TEXT NOT NULL,
    mode_code TEXT NOT NULL,
    distance_km NUMERIC NOT NULL,
    duration_min NUMERIC NOT NULL,
    detail TEXT,
    source TEXT NOT NULL,
    validation_status TEXT NOT NULL DEFAULT 'draft',
    survey_id TEXT,
    import_batch_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT trips_dataset_source_fkey
        FOREIGN KEY (dataset_id, source) REFERENCES datasets (id, source)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_person_dataset_fkey
        FOREIGN KEY (person_id, dataset_id) REFERENCES persons (person_id, dataset_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_origin_fkey
        FOREIGN KEY (origin_place_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_destination_fkey
        FOREIGN KEY (destination_place_id) REFERENCES places (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_purpose_fkey
        FOREIGN KEY (purpose_code) REFERENCES purposes (code)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_mode_fkey
        FOREIGN KEY (mode_code) REFERENCES modes (code)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_survey_fkey
        FOREIGN KEY (survey_id) REFERENCES surveys (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_import_batch_fkey
        FOREIGN KEY (import_batch_id) REFERENCES import_batches (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT trips_source_check CHECK (source IN ('SIMULATED', 'OBSERVED')),
    CONSTRAINT trips_validation_status_check CHECK (
        validation_status IN ('draft', 'validated')
    ),
    CONSTRAINT trips_observed_provenance_check CHECK (
        source <> 'OBSERVED'
        OR survey_id IS NOT NULL
        OR import_batch_id IS NOT NULL
    ),
    CONSTRAINT trips_distance_check CHECK (distance_km >= 0),
    CONSTRAINT trips_duration_check CHECK (duration_min >= 0),
    CONSTRAINT trips_distinct_places_check CHECK (origin_place_id <> destination_place_id)
);

CREATE INDEX IF NOT EXISTS trips_dataset_date_idx ON trips (dataset_id, trip_date);
CREATE INDEX IF NOT EXISTS trips_person_date_idx ON trips (person_id, trip_date);
CREATE INDEX IF NOT EXISTS trips_origin_idx ON trips (origin_place_id);
CREATE INDEX IF NOT EXISTS trips_destination_idx ON trips (destination_place_id);
CREATE INDEX IF NOT EXISTS trips_purpose_idx ON trips (purpose_code);
CREATE INDEX IF NOT EXISTS trips_mode_idx ON trips (mode_code);
CREATE INDEX IF NOT EXISTS trips_survey_idx ON trips (survey_id);
CREATE INDEX IF NOT EXISTS trips_import_batch_idx ON trips (import_batch_id);

COMMENT ON TABLE datasets IS
    'Jeu de déplacements. SIMULATED ou OBSERVED. Le gravitaire OSM n''entre pas ici.';
COMMENT ON TABLE places IS
    'Lieux du catalogue territory.py. Point, pas une limite administrative officielle.';
COMMENT ON TABLE purposes IS
    'Motifs canoniques des étapes individuelles. Distinct de ref_purposes.';
COMMENT ON TABLE modes IS
    'Modes canoniques des étapes individuelles. Distinct de ref_modes et du mode all des flux OSM.';
COMMENT ON TABLE persons IS
    'Pseudonymes rattachés à un jeu. display_name est un libellé de démo, pas une identité observée.';
COMMENT ON TABLE trips IS
    'Une étape, une personne, une date. survey_id reste nul pour le fictif. Pas de clé vers mobility_zones.';
COMMENT ON TABLE surveys IS
    'Enquête future. Vide tant qu''aucun questionnaire n''est chargé.';
COMMENT ON TABLE import_batches IS
    'Lot d''import. received, rejected, validated ou cancelled. Ne mélange pas les sources.';
COMMENT ON TABLE import_rows IS
    'Lignes brutes d''un lot, conservées pour la traçabilité.';

INSERT INTO purposes (code, label_fr) VALUES
    ('travail', 'Travail'),
    ('retour_domicile', 'Retour au domicile'),
    ('courses_supermarche', 'Courses au supermarché'),
    ('courses_marche', 'Courses au marché'),
    ('courses', 'Courses'),
    ('ecole', 'École'),
    ('sante', 'Santé'),
    ('loisirs', 'Loisirs'),
    ('culte', 'Culte'),
    ('visite', 'Visite'),
    ('autre', 'Autre'),
    ('deplacement_professionnel', 'Déplacement professionnel'),
    ('service_public', 'Service public')
ON CONFLICT (code) DO NOTHING;

INSERT INTO modes (code, label_fr) VALUES
    ('marche', 'Marche'),
    ('velo', 'Vélo'),
    ('bus', 'Bus'),
    ('voiture', 'Voiture'),
    ('taxi', 'Taxi')
ON CONFLICT (code) DO NOTHING;
