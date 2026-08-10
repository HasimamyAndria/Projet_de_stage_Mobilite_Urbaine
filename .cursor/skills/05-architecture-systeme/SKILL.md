---
name: 05-architecture-systeme
description: >-
  Architecture logicielle du système mobilité urbaine (C4, contrats API GeoJSON,
  flux data PostGIS → FastAPI → MapLibre, perf). Use when designing system
  architecture, API contracts, or technical decisions.
disable-model-invocation: true
---

# Architecture système

## Mission

Définir une architecture **simple, soutenable en stage**, alignée sur le code existant.

## Stack cible (figée sauf justification)

```text
Sources (OSM/INSEE/GTFS)
  → PostGIS
  → FastAPI (routers + services)
  → React/MapLibre
```

## Sortie

`docs/architecture.md` :

1. Contexte & conteneurs (C4 léger)
2. Modules code (`routers`, `services`, `schemas`)
3. Contrats API (méthode, query, réponse GeoJSON)
4. Modèle data (référence vers skill data)
5. Perf : bbox, LIMIT, indexes GIST, tuiles si besoin
6. Asynchronisme : jobs analytics si > quelques secondes
7. Décisions ADR courtes (pourquoi pas X)

## Contrats API (règles)

- Préfixe `/api`
- Bbox : `minLon,minLat,maxLon,maxLat`
- Réponse spatiale : GeoJSON `FeatureCollection`
- Erreurs : HTTP status + `{"detail": "..."}`
- Pas de logique métier lourde dans le router → `services/`

## Contraintes perf stage

| Opération | Objectif |
|-----------|----------|
| Couche carte bbox | < 1–2 s |
| Search | < 500 ms |
| Route | < 3 s |
| Clustering / indice | < 30 s (sinon async) |

## Non-objectifs

- Kafka / microservices
- Multi-tenant industriel
- Spark (sauf justification volume)

## Done when

- [ ] Contrats des endpoints Must listés
- [ ] Découpage services clair
- [ ] Risques perf documentés
