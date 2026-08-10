---
name: 06-data-postgis
description: >-
  Modélisation et pipelines PostGIS pour OSM, réseau routable pgRouting, OD/IRIS,
  GTFS et indices mobilité. Use when designing schemas, imports, spatial SQL,
  indexes, or preparing mobility datasets.
disable-model-invocation: true
---

# Data — PostGIS & géospatial

## Mission

Fiabiliser le socle data : OSM existant + extensions OD / zones / indices pour le MVP.

## État actuel

- Tables OSM : `planet_osm_line`, `planet_osm_point`, `planet_osm_polygon`, `planet_osm_roads`
- Réseau : `roads_network`, `roads_network_vertices_pgr`
- SRID stockage typique : **3857** ; API : **4326** via `ST_Transform`

## Sortie

- `docs/data-model.md`
- Scripts dans `backend/scripts/` (SQL ou Python GeoPandas) si besoin

## Checklist modèle MVP

```text
- [ ] Indexes GIST sur géométries interrogées
- [ ] roads_network source/target/cost cohérents
- [ ] Table zones (IRIS ou grille) si OD
- [ ] Table od_flows agrégée (origine, destination, volume, mode?)
- [ ] Table zone_metrics (indice, cluster_id, labels)
- [ ] Vue ou materialised view pour KPI
```

## Règles SQL spatial

1. Filtrer d'abord par `&&` / `ST_MakeEnvelope` transformé.
2. Toujours `LIMIT` sur couches densées.
3. Paramètres bindés (`:minLon`…) — jamais de f-string SQL.
4. Valider bbox (min < max, plage lon/lat).

## Import recommandé

| Source | Usage MVP |
|--------|-----------|
| OSM (osm2pgsql) | Fond de carte, TC, buildings |
| INSEE MOBPRO / IRIS | OD agrégée |
| GTFS | Score desserte (option) |
| SIRENE / emplois | Indice M6 (option) |

## Qualité data

Documenter : date d'import, couverture territoire, taux de géocodage, limites connues.

## Done when

- [ ] Schéma documenté
- [ ] Indexes listés
- [ ] Script d'import reproductible ou procédure claire
