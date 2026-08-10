---
name: 00-pipeline-stage
description: >-
  Orchestre le pipeline complet du stage Mobilité Urbaine (cadrage → MVP →
  production → soutenance). Use when the user asks how to chain skills, which
  skill to run next, the project roadmap, or starts a new work phase.
disable-model-invocation: true
---

# Pipeline Stage → Production → Soutenance

## Objectif

Guider l'agent et l'étudiant sur **l'ordre des skills**, les **livrables** et les **critères de passage** d'une phase à la suivante.

## Ordre obligatoire

| # | Skill | Phase | Livrable de sortie |
|---|-------|-------|--------------------|
| 01 | `01-project-context` | Toujours | Contexte stack / périmètre lu |
| 02 | `02-ba-vision-exigences` | Cadrage | Vision, EF, règles métier |
| 03 | `03-po-backlog-mvp` | Cadrage | Backlog priorisé + US + DoD |
| 04 | `04-ux-carto-decision` | Conception | Parcours + wireframes / specs UI |
| 05 | `05-architecture-systeme` | Conception | Archi C4 / contrats API |
| 06 | `06-data-postgis` | Fondations | Modèle PostGIS + import data |
| 07 | `07-backend-fastapi-geo` | Build | Endpoints GeoJSON stables |
| 08 | `08-frontend-maplibre` | Build | Carte interactive + couches |
| 09 | `09-analytics-modules` | Build | M1/M2/M5/M6 (MVP) |
| 10 | `10-qa-qualite` | Qualité | Plan de tests + preuves |
| 11 | `11-devops-production` | Prod | Docker / env / runbook |
| 12 | `12-securite-rgpd` | Conformité | Checklist sécu + anonymisation |
| 13 | `13-soutenance-stage` | Soutenance | Slides + démo + Q&R |

## Règles d'enchaînement

1. **Toujours** commencer une session de build par `01-project-context`.
2. Ne pas coder un module analytique (09) sans contrats API (05) et schéma data (06).
3. Ne pas déployer (11) sans QA minimale (10) et garde-fous RGPD (12).
4. La soutenance (13) consomme les livrables réels : démo live, métriques, décisions de scope.
5. Une phase est **terminée** seulement si son livrable de sortie existe dans le repo (fichier ou code).

## Périmètre MVP stage (rappel)

**Inclus (Must)** : M1 flux/carte, M2 points clés (clustering basique), M5 KPI, M6 indice emploi-habitat (proxy), socle OSM/PostGIS/routing.

**Reportable (Should/Could)** : M3 reco avancées, M4 simulation what-if complète, multi-tenant, export PPT.

## Fichier prompts

Pour les prompts prêts à coller, lire [PROMPTS.md](PROMPTS.md).

## Comportement agent

- Si l'utilisateur demande "par où commencer" → proposer la prochaine phase non terminée.
- Si une phase saute → signaler le risque et proposer le skill manquant.
- Produire un mini statut en fin de réponse :

```text
Phase: <n>
Skill: <name>
Livrable: <path ou statut>
Next: <skill suivant>
```
