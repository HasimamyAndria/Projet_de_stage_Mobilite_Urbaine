---
name: 08-frontend-maplibre
description: >-
  Frontend React + MapLibre pour la plateforme mobilité : MapView, layers,
  search, routing, panneaux KPI, états UI. Use when implementing or fixing the
  map UI, layers, or frontend API integration.
disable-model-invocation: true
---

# Frontend — React MapLibre

## Mission

Construire l'expérience carte décisionnelle branchée sur l'API FastAPI.

## Structure

```text
frontend/src/
  components/Map/
    MapView.tsx
    *Layer.ts
    SearchBar.tsx
  services/api.ts
  App.tsx
```

## Règles UI/code

1. Une couche = un module (`RoadsLayer`, `BusStopsLayer`, …).
2. Fetch bbox sur `moveend` / debounce — ne pas spammer l'API.
3. Gérer `loading` / `error` / `empty` explicitement.
4. Types TS pour FeatureCollection.
5. Ne pas casser le style MapLibre existant sans raison.
6. Accessibilité basique : labels boutons, contraste panneaux.

## Intégration API

Centraliser les appels dans `services/api.ts` (base URL via `import.meta.env`).

## Couches MVP

| Couche | Source API | Toggle |
|--------|------------|--------|
| Routes | `/api/roads` | oui |
| Buildings | `/api/buildings` | oui |
| Bus stops/lines | `/api/bus-*` | oui |
| Route A→B | `/api/route` | action |
| Clusters / zones | analytics | oui |
| Indice M6 | analytics | oui |

## Perf front

- Éviter re-render complets de la map
- Diff layers via `map.getSource` / `setData` si possible
- Limiter features affichées

## Alignement UX

Suivre `docs/ux-mvp.md` : carte dominante, panneau KPI, pas de clutter.

## Done when

- [ ] Feature visible sur la carte
- [ ] Toggle / interaction OK
- [ ] Erreur API affichée proprement
