---
name: 13-soutenance-stage
description: >-
  Préparation de soutenance de stage solide : plan oral, script démo live,
  outline slides, Q&R jury tech/métier, checklist J-1. Use when preparing
  defense, presentation, demo script, or anticipated jury questions.
disable-model-invocation: true
---

# Soutenance stage — Mobilité Urbaine

## Mission

Préparer une soutenance **crédible** : problème → solution → démo → méthode → limites → perspectives.

## Sortie

```text
docs/soutenance/
  plan-oral.md
  script-demo.md
  slides-outline.md
  questions-reponses.md
  checklist-j1.md
```

## Plan oral type (12–15 min)

| Min | Contenu |
|-----|---------|
| 0–1 | Contexte métropole / problème emploi-habitat |
| 1–3 | Objectifs stage & périmètre MVP |
| 3–5 | Architecture (1 slide simple) |
| 5–10 | **Démo live** (cœur) |
| 10–12 | Méthodes (clustering / indice) + RGPD |
| 12–14 | Résultats, limites, perspectives M3/M4 |
| 14–15 | Conclusion |

## Script démo (obligatoire)

Enchaînement filmable < 4 min :

1. Ouvrir la carte, montrer fond OSM + couches
2. Search lieu
3. Calculer une route
4. Afficher KPI / zones clés / indice
5. Expliquer **une** décision métier possible à partir de l'écran

Prévoir plan B (captures) si réseau/DB tombe.

## Slides (outline)

1. Titre / étudiant / tuteur / organisme
2. Problématique
3. Vision produit (1 phrase)
4. Périmètre MVP vs cible
5. Architecture
6. Stack
7. Captures / démo
8. Méthode analytique
9. Qualité & conformité
10. Difficultés & apprentissages
11. Perspectives
12. Merci / Q&R

## Q&R à préparer

**Métier** : pourquoi pas temps réel ? valeur pour un élu ?
**Data** : sources, biais MOBPRO, k-anonymité ?
**Tech** : pourquoi PostGIS/MapLibre ? perf bbox ?
**ML** : choix K-means vs DBSCAN ? validation ?
**Prod** : comment déployer ? secrets ?
**Limites** : ce qui n'est pas fiable / hors scope ?

## Règles de discours

- Ne pas sur-promettre M3/M4 non livrés
- Assumer les limites (force, pas faiblesse)
- Chiffres / paramètres réels du projet uniquement

## Done when

- [ ] 5 fichiers soutenance présents
- [ ] Démo chronométrée une fois
- [ ] 10+ réponses Q&R rédigées
