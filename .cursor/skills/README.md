# Skills projet — Mobilité Urbaine

Skills Cursor du stage, du cadrage à la **production** et à la **soutenance**.

## Démarrage rapide

1. Ouvrir une conversation Agent dans ce repo.
2. Copier un prompt depuis [`00-pipeline-stage/PROMPTS.md`](00-pipeline-stage/PROMPTS.md).
3. Respecter l'ordre des phases (ne pas sauter data/archi avant analytics).

## Catalogue

| Skill | Rôle |
|-------|------|
| `00-pipeline-stage` | Orchestration + critères de passage |
| `01-project-context` | Contexte stack / MVP (auto utile en session) |
| `02-ba-vision-exigences` | Vision & exigences |
| `03-po-backlog-mvp` | Backlog & user stories |
| `04-ux-carto-decision` | UX carte décisionnelle |
| `05-architecture-systeme` | Architecture & contrats API |
| `06-data-postgis` | PostGIS / imports |
| `07-backend-fastapi-geo` | API FastAPI |
| `08-frontend-maplibre` | UI MapLibre |
| `09-analytics-modules` | Modules M1–M6 |
| `10-qa-qualite` | Tests & preuves |
| `11-devops-production` | Docker / runbook |
| `12-securite-rgpd` | Sécu & conformité |
| `13-soutenance-stage` | Oral, démo, Q&R |

## Enchaînement express

```text
01 → 02 → 03 → 04 → 05 → 06 → (07 ↔ 08) → 09 → 10 → 11+12 → 13
```

Build itératif recommandé : boucler `03 → 07 → 08 → 09 → 10` par user story Must.
