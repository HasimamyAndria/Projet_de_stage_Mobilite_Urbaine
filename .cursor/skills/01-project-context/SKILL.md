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
- `D:\BIHAR\Sujet\Vision_Produit_Mobilite_Urbaine.pdf`

## Stack réelle (repo)

| Couche | Techno |
|--------|--------|
| API | FastAPI (`backend/app/main.py`) |
| DB | PostgreSQL + PostGIS (`DATABASE_URL` via `.env`) |
| OSM | Tables `planet_osm_line/point/polygon/roads` |
| Routing | `roads_network` + `pgr_dijkstra` |
| Front | React 19 + Vite + MapLibre GL |
| HTTP | axios |

## Structure

```text
backend/app/
  main.py, database.py
  routers/map.py, routers/zones.py
  models/, schemas/, services/
frontend/src/
  components/Map/ (MapView, layers, SearchBar)
  services/api.ts, api.ts
```

## Endpoints déjà présents

- `GET /api/roads|buildings|bus-stops|bus-lines` (bbox → GeoJSON)
- `GET /api/search?q=`
- `GET /api/route` (pgRouting)
- `GET /api/zones/bounds`

## Modules produit

| ID | Nom | MVP stage |
|----|-----|-----------|
| M1 | Cartographie des flux | Must (socle carte + couches) |
| M2 | Points clés / clustering | Must (basique) |
| M3 | Recommandations | Should (reportable) |
| M4 | Simulation what-if | Should (reportable) |
| M5 | Dashboard KPI | Must (synthèse) |
| M6 | Emploi-habitat | Must (indice proxy) |

## Conventions agent

1. Lire le code existant avant d'ajouter une lib.
2. Réponses GeoJSON : `FeatureCollection` + `features[]`.
3. Requêtes spatiales : bbox + `LIMIT` ; SRID 3857 en base, 4326 en sortie.
4. Ne jamais committer `.env` / secrets.
5. Français pour docs métier ; code/idents en anglais.
6. Préférer étendre `routers/` et `components/Map/` plutôt que tout réécrire.

## Checklist état projet

Quand on demande l'état :

```text
- [ ] Backend démarre (uvicorn)
- [ ] Front démarre (vite :5173)
- [ ] PostGIS joignable
- [ ] Couches carte OK
- [ ] Route A→B OK
- [ ] Analytics M2/M6
- [ ] Docker / prod
- [ ] Docs soutenance
```

## Additional resources

- Pipeline : skill `00-pipeline-stage`
- Prompts : `../00-pipeline-stage/PROMPTS.md`
