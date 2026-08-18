---
name: 01-project-context
description: >-
  Contexte technique et métier du projet stage Mobilité Urbaine (FastAPI,
  PostGIS/OSM, pgRouting, React, MapLibre). Use at session start, when exploring
  the repo, estimating remaining work, or before any feature implementation.
---

# Project Context — Mobilité Urbaine

## Produit

Plateforme d'**aide à la décision** pour la mobilité urbaine et l'équilibre emploi-habitat (pas de pilotage trafic temps réel).

Sources de vérité :
- `D:\BIHAR\Sujet\specification_mobilite_urbaine-stage.pdf`
- `docs/Vision_Produit_Mobilite_Urbaine.pdf`
- Livrables phase : `docs/exigences-mvp.md`, `docs/backlog-mvp.md`, `docs/ux-mvp.md`, `docs/architecture.md`

## Stack réelle (repo)

| Couche | Techno |
|--------|--------|
| API | FastAPI (`backend/app/main.py`) |
| DB | PostgreSQL + PostGIS (`DB_*` via `.env`) |
| OSM | Tables `planet_osm_line/point/polygon/roads` |
| Routing | `roads_network` + `pgr_dijkstra` |
| Front | React 19 + Vite + MapLibre GL |
| HTTP | axios |

## Structure

```text
backend/app/
  main.py, database.py, privacy.py
  routers/  map, zones, od, keypoints, emploi_habitat, cities
  services/ od, keypoints, emploi_habitat, city_service, provenance
frontend/src/
  components/Map/  MapView, *Layer, SearchBar, CitySelector,
                   LayerPanel, KpiPanel, stageViews
  services/api.ts
```

## Endpoints Must

- `GET /api/roads|buildings|bus-stops|bus-lines` (bbox → GeoJSON)
- `GET /api/search?q=`
- `GET /api/route` (pgRouting, sous-graphe bbox)
- `GET /api/zones/bounds`
- `GET /api/od/zones|flows|summary`
- `GET /api/keypoints` (labels + K-means)
- `GET /api/emploi-habitat`
- `GET|POST /api/cities/*`

## Modules produit

| ID | Nom | MVP stage |
|----|-----|-----------|
| M1 | Cartographie des flux | Must (livré) |
| M2 | Points clés / clustering | Must (heuristiques + K-means) |
| M3 | Recommandations | Should (reportable — ne pas coder tant que Must clos) |
| M4 | Simulation what-if | Should (reportable) |
| M5 | Dashboard KPI | Must (panneau + métriques header) |
| M6 | Emploi-habitat | Must (indice proxy) |

## Conventions agent

1. Lire le code existant avant d'ajouter une lib.
2. Réponses GeoJSON : `FeatureCollection` + `features[]`.
3. Requêtes spatiales : bbox + `LIMIT` ; SRID 3857 en base, 4326 en sortie.
4. Ne jamais committer `.env` / secrets.
5. Français pour docs métier ; code/idents en anglais.
6. Préférer étendre `routers/` et `components/Map/` plutôt que tout réécrire.
7. M3/M4 / auth / export client : seulement après clôture du lot 1 stage.

## Checklist état projet

```text
- [x] Backend démarre (uvicorn)
- [x] Front démarre (vite :5173)
- [x] PostGIS joignable
- [x] Couches carte OK
- [x] Route A→B UI (démo + clic A/B)
- [x] Analytics M2/M5/M6
- [x] Docker / runbook
- [x] Docs cadrage 02–05 + soutenance
- [x] Smoke QA rejoué 2026-08-18 (24/24, preuve `_smoke_mvp_qa_last.json`)
```

## Additional resources

- Pipeline : skill `00-pipeline-stage`
- Prompts : `../00-pipeline-stage/PROMPTS.md`
