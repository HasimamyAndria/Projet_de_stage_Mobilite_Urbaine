# Data model — Mobilité Urbaine (MVP OD)

Trois provenances coexistent. Une requête ne les joint pas sans le dire.

| Provenance | Tables | Grain |
|------------|--------|-------|
| Gravitaire OSM | `mobility_zones`, `mobility_flows` | Volume zone → zone, mode `all`, sans date ni personne |
| Prototype entier et catalogue `sim_*` | `cities`, `arrondissements`, `quartiers`, `zones`, `organizations`, `employee_groups`, `od_matrix`, `data_sources`, `ref_*`, et `sim_*` | Groupes ou matrices. `data_sources.code = SIMULATED_PROTOTYPE_TANA` |
| Contrat individuel | migration `30_mobility_contract` | Une étape, une personne, une date, `SIMULATED` ou `OBSERVED` |

Les fichiers `backend/scripts/sql/21_mobility_schema.sql` et `22_seed_antananarivo_simulated.sql` sont absents du dépôt. Les tables du prototype entier sont présentes dans la base locale consultée le 12 octobre 2026. La migration 30 ne les modifie pas. L'API ne les lit pas. `sim_persons` n'alimente pas `persons` ni `trips`. `ref_purposes` (`domicile_travail`, `achats`…) et `ref_modes` (`taxi_be`…) restent le vocabulaire de `od_matrix`. Les codes canoniques du contrat sont dans `purposes` et `modes`.



## Stratégie de peuplement

Territoire carte : **Antananarivo**.

| Approche | Statut | Contenu |
|----------|--------|---------|
| **B — OSM réel** | **Active (défaut)** | Quartiers OSM (`suburb` / `quarter`) → Voronoi ; proxies bâti + POI ; OD gravitaire |
| A — Démo grille | Repli `--demo` | Grille 4×4 synthétique (tests sans OSM) |
| C — Enquête OD | Plus tard | Shapefile / matrice zone→zone officielle |

Volumes **agrégés zone→zone** uniquement.

## Schéma réel (base `mobilite`)

### `mobility_zones`

| Colonne | Type | Rôle |
|---------|------|------|
| `id` | serial | PK |
| `name` | varchar | Nom OSM (quartier) |
| `geometry` | MultiPolygon **4326** | Cellule Voronoi clipée bbox |
| `zone_type` | varchar | `osm_suburb` (ou `grid_demo`) |
| `population_proxy` | int | Bâtiments OSM × facteur |
| `jobs_proxy` | int | POI + landuse emplois OSM |

### `mobility_flows` (équivalent OD)

| Colonne | Type | Rôle |
|---------|------|------|
| `origin_zone_id` | int | Origine |
| `destination_zone_id` | int | Destination |
| `trip_count` | int | Volume agrégé (estimé) |
| `average_distance` | numeric | km (proxy distance sphérique) |
| `average_time` | numeric | min (proxy ~22 km/h) |
| `mode` | varchar | `all` |

### Vue `v_od_desire_lines`

LineString 4326 centroïde→centroïde + `passenger_count` (= `trip_count`).

## Scripts

```powershell
cd backend
# Défaut : OSM réel (planet_osm_* requis)
.\venv\Scripts\python.exe scripts\seed_zones_od.py

# Option : plus / moins de quartiers
.\venv\Scripts\python.exe scripts\seed_zones_od.py --top-n 40

# Repli grille synthétique
.\venv\Scripts\python.exe scripts\seed_zones_od.py --demo
```

Implémentation OSM : `backend/scripts/seed_zones_od_osm.py`

## API

- `GET /api/od/zones` → polygones GeoJSON
- `GET /api/od/flows?min_passengers=50` → desire lines
- `GET /api/od/summary` → KPI (`synthetic: false` si `zone_type` OSM)
- `GET /api/keypoints` → labels M2 + corridors
- `GET /api/emploi-habitat` → indice M6

## Multi-villes

Pipeline portable :

1. Choisir / rechercher une ville (`GET /api/cities/search`, presets)
2. Activer (`POST /api/cities/activate`) → bbox clampée ~20 km
3. Si OSM présent dans la bbox → seed zones + OD gravitaire
4. Sinon → message « importer extract Geofabrik + osm2pgsql »

Antananarivo fonctionne dès que `planet_osm_*` Madagascar est chargé.  
Paris / Madrid : même code, dès qu’un extract OSM de la ville est importé.

## Limites (à dire en soutenance)

- Géométries / densités : **réelles OSM**
- Volumes OD : **estimés** (gravité), pas une enquête ménage
- Suffisant pour simuler M1/M2/M5/M6 sur un territoire réel
- Évolution : matrice OD officielle (approche C) par connecteur local

## Catalogue simulé (séparé d'OSM)

Tables créées par `backend/scripts/sql/20_simulated_mobility.sql` et remplies par `backend/scripts/seed_simulated_mobility.py`.

| Table | Contenu |
|-------|---------|
| `sim_zones` | Arrondissements / communes et quartiers du catalogue, polygone circulaire 4326 |
| `sim_companies` | Organisations (ministère, université, commerce…) |
| `sim_persons` | Employés simulés, un par personne du groupe |
| `sim_trips` | Aller, retour, hors-travail, agrégés par groupe |
| `sim_indicators` | Instantané des indices par ville et par zone |
| `sim_clusters` | Profil K-means de chaque employé simulé |
| `sim_scenarios` | Archives des scénarios lancés depuis l'interface |

`mobility_zones` et `mobility_flows` restent l'estimation gravitaire OSM. Elles ne sont pas mélangées à ce catalogue.

L'API de lecture (`/api/zones`, `/api/mobility/indicators`, `/api/companies`, `/api/simulation`) calcule depuis les fichiers Python, pour rester disponible même avant le seed. Le seed fige le même calcul dans PostGIS.

## Contrat des déplacements individuels (migration 30)

Script : `backend/scripts/sql/30_mobility_contract.sql`.  
Application : `backend/scripts/apply_sql_migration.py`.  
La version et l'empreinte SHA-256 du fichier sont écrites dans `schema_migrations` dans la même transaction. Une seconde application de la même empreinte ne rejoue pas le SQL. Le script est aussi idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`).

```powershell
cd backend
.\venv\Scripts\python.exe scripts\apply_sql_migration.py 30_mobility_contract
.\venv\Scripts\python.exe scripts\test_mobility_contract.py
```

Le script lit `backend/.env` en premier. Sur la machine de développement, cette base est PostgreSQL local (`DB_HOST=localhost`). Le `.env` de la racine vise le service Compose `db`, qui n'est pas l'instance déjà peuplée.

La migration 30 ne charge que les codes canoniques. Les huit personnes du journal sont chargées ensuite par le seed, dans le jeu `diary-week`.

### Seed du journal

```powershell
cd backend
.\venv\Scripts\python.exe scripts\seed_diary_trips.py
.\venv\Scripts\python.exe scripts\test_diary_seed.py
```

Le seed relit la semaine type de `persons.py` (fonction `_scripted_day_trips`). Il écrit les lieux de `territory.py`, les huit personnes et leurs étapes. Les identifiants de trajet sont `sim-{personne}-{jour}-{index}`. Une seconde exécution met à jour ces lignes. Elle ne vide pas `mobility_flows`, les tables OSM ni `sim_*`.

| Élément | Valeur |
|---------|--------|
| Jeu | `diary-week` |
| Source | `SIMULATED` |
| Lundi d'ancrage | 2026-10-05 |
| Graine | 8, les personnes sont écrites, pas tirées au sort |
| Statut des étapes | `validated` |
| Enquête | aucune (`survey_id` nul) |

Vérifier le jeu :

```sql
SELECT source, label FROM datasets WHERE id = 'diary-week';
SELECT person_id, source FROM persons WHERE dataset_id = 'diary-week' ORDER BY 1;
SELECT purpose_code, COUNT(*) FROM trips WHERE dataset_id = 'diary-week' GROUP BY 1 ORDER BY 1;
```

`retour_domicile` est le retour à la maison. `courses_supermarche` et `courses_marche` sont les courses. L'API continue d'afficher `domicile`, `supermarche` et `marche`, les codes historiques de l'écran.

Le mois et l'année restent des répétitions de cette semaine. Ils n'ajoutent pas de lignes. Aucune des huit semaines types n'a de jour sans étape. Un jour sans déplacement sera l'absence de ligne, pas une ligne vide.

L'âge et le texte de présentation ne sont pas des colonnes du contrat. La fiche affichée les relit encore dans `persons.py`. Les trajets, les dates et les lieux viennent de PostgreSQL.

Les saisies faites dans l'écran (`POST /api/mobility/trips`) restent en mémoire du processus, avec `source = saisie`. Elles disparaissent au redémarrage. Le seed ne les enregistre pas et ne les présente pas comme des observations.

Lecture par défaut : PostgreSQL. Pour revenir au calcul Python :

```powershell
$env:DIARY_READ = "memory"
```

Retirer la variable, ou la poser à `postgres`, rend la base à nouveau prioritaire. Les saisies manuelles de la session sont ajoutées dans les deux modes.

### Tables

| Table | Rôle |
|-------|------|
| `schema_migrations` | `version`, `description`, `checksum`, `applied_at` |
| `datasets` | Jeu `SIMULATED` ou `OBSERVED`, libellé, graine, `anchor_monday` (un lundi) |
| `places` | Identifiant texte, parent, ville, niveau `city` / `commune` / `quartier`, rôle, longitude, latitude, `boundary_kind = point_catalog` |
| `persons` | Pseudonyme, jeu, ville, domicile, travail facultatif, activité, source |
| `purposes`, `modes` | Codes canoniques et libellés français |
| `trips` | Étape datée : heures, lieux, motif, mode, distance, durée, source, `validation_status` |
| `surveys` | Période, version de questionnaire, statut `draft` / `validated` / `closed` |
| `import_batches` | Fichier, source, statut `received` / `rejected` / `validated` / `cancelled`, rapport JSON |
| `import_rows` | JSON brut, une ligne par couple (`batch_id`, `row_number`) |

`trips.survey_id` et `trips.import_batch_id` sont nuls pour un déplacement fictif. Un déplacement `OBSERVED` exige une enquête ou un lot d'import. La source d'une personne et d'une étape doit être celle de son jeu (`UNIQUE (id, source)` sur `datasets`).

Aucune clé étrangère de `trips` vers `mobility_zones`, `mobility_flows` ou `zones`.

### Codes canoniques

Motifs : `travail`, `retour_domicile`, `courses_supermarche`, `courses_marche`, `courses`, `ecole`, `sante`, `loisirs`, `culte`, `visite`, `autre`, `deplacement_professionnel`, `service_public`.

Correspondance de lecture, plus tard, avec le journal en mémoire : `domicile` → `retour_domicile`, `supermarche` → `courses_supermarche`, `marche` (motif) → `courses_marche`.

Modes : `marche`, `velo`, `bus`, `voiture`, `taxi`. Le mode `all` reste une colonne de `mobility_flows`. Les parts `car` / `walk` / `bike` de la désagrégation OD ne sont pas des lignes de `modes`.

Statut d'une étape : `draft` ou `validated`.

### Index

- `places (city_id, level)` et `places (parent_id)`
- `persons (dataset_id)` et `persons (home_place_id)`
- `trips (dataset_id, trip_date)` et `trips (person_id, trip_date)`
- index sur les clés étrangères de `trips`, `surveys`, `import_batches`, `import_rows`

La géométrie de `places` est le couple longitude / latitude. Un index spatial sera ajouté le jour où une géométrie PostGIS existera. `boundary_kind = point_catalog` indique que ce n'est pas une limite officielle.

