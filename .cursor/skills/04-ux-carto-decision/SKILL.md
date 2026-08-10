---
name: 04-ux-carto-decision
description: >-
  UX Designer pour interface cartographique d'aide à la décision (MapLibre) :
  parcours Urbaniste/Élu, couches, KPI, états UI. Use when designing screens,
  map layers, filters, or decision-oriented UI for the mobility MVP.
disable-model-invocation: true
---

# UX — Cartographie décisionnelle

## Mission

Concevoir une UI **orientée décision** : carte + indicateurs + zones clés, sans dashboard surchargé.

## Principes

1. Un job par écran / panneau.
2. Carte = plan dominant (full-bleed), pas carte en carte.
3. Hero budget MVP : marque/titre app, filtres essentiels, carte, 1 panneau KPI.
4. Pas de cards décoratives ; panneaux seulement pour interaction.
5. Couches toggleables : routes, TC, OD/heatmap, clusters, indice.
6. États : loading, empty, error, degraded (ex. GTFS absent).

## Personas prioritaires

| Persona | Besoin UI |
|---------|-----------|
| Urbaniste | Couches + détail zone + export |
| Élu | KPI + top zones + message simple |
| DRH (si temps) | Sites candidats / impact trajets |

## Sortie

`docs/ux-mvp.md` :

- Sitemap / écrans
- Wireframe textuel de la vue principale
- Liste des couches + légendes
- Microcopy (tooltips, empty states)
- Parcours démo 90 secondes

## Wireframe textuel (template)

```text
[ Header: titre | filtres période/mode ]
[ Sidebar couches ] [ MAP full ] [ Panneau KPI / détail ]
[ Footer statut data / source ]
```

## Alignement front

Respecter `frontend/src/components/Map/` existant. Étendre `MapView` + layers plutôt que recréer une app.

## Done when

- [ ] Parcours Urbaniste + Élu décrits
- [ ] Couches MVP listées
- [ ] Spec compréhensible par frontend skill
