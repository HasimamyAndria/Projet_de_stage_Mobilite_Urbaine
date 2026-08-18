# Architecture — Mobilité Urbaine (lot 1 stage)

**Date :** 2026-08-18  
**Skill :** `05-architecture-systeme`  
**Data :** voir `docs/data-model.md`

## 1. Contexte (C4 léger)

```text
[Urbaniste / Élu]
        │  HTTPS ou HTTP localhost
        ▼
[Navigateur React + MapLibre] ──REST/JSON──► [FastAPI]
                                                │ SQL
                                                ▼
                                         [PostgreSQL
                                          PostGIS
                                          pgRouting]
        OSM PBF ──osm2pgsql──► planet_osm_*
        seed gravitaire ─────► mobility_zones / mobility_flows
```

Pas de bus de messages, pas de microservices, pas de Kafka.

## 2. Conteneurs

| Conteneur | Image / runtime | Port |
|-----------|-----------------|------|
| frontend | nginx (Docker) ou Vite 5173 | 8080 |
| backend | uvicorn FastAPI | 8000 |
| db | `pgrouting/pgrouting:16-3.4-3.6.1` | 5432 |

`docker-compose.yml` : healthchecks, volume `mobilite_postgis_data`.

## 3. Modules code

```text
backend/app/
  main.py          CORS, /health, include_router
  database.py      SQLAlchemy + env DB_*
  privacy.py       K_ANONYMITY_MIN
  routers/         HTTP : map, zones, od, keypoints, emploi_habitat, cities
  services/        SQL + métier (od, keypoints, emploi_habitat, city, provenance)
frontend/src/
  components/Map/  MapView + *Layer.ts + panneaux
  services/api.ts  axios, VITE_API_URL
```

Règle : router mince → `services/`. Pas de secrets dans le code.

## 4. Contrats API (Must)

Préfixe `/api`. Erreurs : HTTP + `{"detail":"..."}`. Spatial : GeoJSON `FeatureCollection`. Bbox : `minLon,minLat,maxLon,maxLat`. SRID sortie 4326.

| Méthode | Chemin | Query | Réponse |
|---------|--------|-------|---------|
| GET | `/health` | — | `{status, env}` |
| GET | `/api/roads` | bbox | FC, LIMIT 5000 |
| GET | `/api/buildings` | bbox | FC, LIMIT 3000 |
| GET | `/api/bus-stops` | bbox | FC |
| GET | `/api/bus-lines` | bbox | FC, LIMIT 1000 |
| GET | `/api/search` | `q` | liste `{name,lon,lat,place}` ; `q` vide → `[]` |
| GET | `/api/route` | `startLon,startLat,endLon,endLat` | FC segments ; vide si pas de chemin |
| GET | `/api/zones/bounds` | — | xmin…ymax |
| GET | `/api/od/zones` | — | FC polygones |
| GET | `/api/od/flows` | `min_passengers≥5`, `limit≤1000` | FC desire lines |
| GET | `/api/od/summary` | `top_n` | totaux + top_flows + `synthetic` |
| GET | `/api/keypoints` | `corridor_top_n` | `{zones, corridors, counts, clustering, rules, note}` |
| GET | `/api/emploi-habitat` | — | FC + `summary` + `formula` + `note` |
| GET | `/api/cities/presets` | — | presets |
| GET | `/api/cities/search` | `q` | Nominatim |
| GET | `/api/cities/current` | — | ville active |
| GET | `/api/cities/coverage` | bbox | osm_ready |
| POST | `/api/cities/activate` | body bbox | seed OD si OSM présent |

503 si tables OD absentes → lancer `scripts/seed_zones_od.py`.

## 5. Flux data

```text
PBF → osm2pgsql → planet_osm_* (3857)
                → roads_network + vertices (pgRouting)
seed_zones_od.py → quartiers OSM / Voronoi → mobility_zones
                 → modèle gravitaire → mobility_flows
                 → vue v_od_desire_lines
API services → GeoJSON 4326 → MapLibre sources
```

## 6. Performance

| Opération | Objectif | Mitigation |
|-----------|----------|------------|
| Couche OSM bbox | < 2 s | envelope `&&`, LIMIT, zoom ≥ 11, debounce 450 ms |
| Search | < 500 ms | ILIKE + LIMIT 20 |
| Route | < 3 s (idéal) | Dijkstra sur **sous-graphe bbox** (~5 km) |
| Keypoints / M6 / OD | < 2 s | n zones ~ 16–40, agrégats SQL |
| Clustering | inclus keypoints | K-means Python, n petit, pas de job async |

Hors-scope : tuiles vectorielles MVT, cache Redis.

## 7. ADR courts

| Décision | Pourquoi |
|----------|----------|
| PostGIS + pgRouting | Déjà en place ; spatial + plus court chemin sans moteur externe |
| OD gravitaire OSM | Pas d’enquête ; pipeline reproductible ; disclaimer obligatoire |
| K-means pur Python | n petit ; `requirements-docker.txt` sans numpy/sklearn |
| Auth reportée | Démo localhost ; CORS strict, Swagger off si `APP_ENV=production` |
| Pas de schemas/ ORM models | SQL `text()` paramétré suffisant au volume stage |

## 8. Risques

- Import OSM hors Docker → démo « analytics only » si oubli.
- Graphe fragmenté → route vide.
- Nominatim rate-limit → search villes.
- Front build figé `VITE_API_URL` (rebuild si host change).
