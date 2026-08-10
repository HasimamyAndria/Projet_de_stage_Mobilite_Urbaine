---
name: 09-analytics-modules
description: >-
  Modules analytiques M1–M6 : OD/flux, clustering points clés, KPI, indice
  emploi-habitat, reco/simulation si scope. Use when implementing mobility
  analytics, clustering, indicators, or scoring.
disable-model-invocation: true
---

# Analytics — Modules M1–M6

## Mission

Implémenter la **valeur métier démontrable** avec méthodes transparentes et limites affichées.

## Priorité stage

| Module | Contenu MVP | Reportable |
|--------|-------------|------------|
| M1 | Couches + desire lines / heatmap si data OD | — |
| M2 | Clustering (K-means ou DBSCAN) + labels zones | HDBSCAN avancé |
| M5 | KPI (volumes, top OD, % couverture) | séries temporelles riches |
| M6 | Indice proximité proxy documenté | 2SFCA complet |
| M3 | Top sites score simple | optimisation p-médianes |
| M4 | Scénario paramétrique léger | simulateur complet |

## Règles scientifiques / produit

1. Documenter formule, paramètres, hypothèses dans `docs/methodes.md`.
2. Afficher **limites** dans l'UI (tooltip / panneau).
3. Données **agrégées** seulement.
4. Évaluer clustering (silhouette ou stabilité qualitative).
5. Reproductibilité : seed / version paramètres.

## Implémentation technique

Préférer :

```text
PostGIS / SQL agrégats
  → service Python (GeoPandas / scikit-learn si besoin)
  → endpoint GeoJSON + métriques JSON
  → couche MapLibre + panneau
```

Jobs longs (>30s) : endpoint async + statut (même simple).

## Labels métiers M2 (exemples)

- Corridor saturé
- Désert de mobilité
- Zone dortoir
- Nœud / cluster d'activité

Chaque label = règle RM documentée (même heuristique).

## Done when

- [ ] Méthode écrite
- [ ] API + couche ou panneau
- [ ] Démo < 2 min compréhensible par un non-dev
