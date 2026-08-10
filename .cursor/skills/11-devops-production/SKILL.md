---
name: 11-devops-production
description: >-
  Mise en production du projet stage : Docker Compose, env, healthchecks,
  README run, backup PostGIS minimal, runbook. Use when containerizing,
  deploying, or preparing production/demo environment.
disable-model-invocation: true
---

# DevOps — Production stage

## Mission

Rendre le système **reproductible** : un tiers peut démarrer stack + démo.

## Sortie minimale

```text
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile (ou nginx)
.env.example
README.md (quick start)
docs/runbook.md
```

## Architecture déploiement stage

```text
[browser] → frontend (nginx/vite preview)
         → backend (uvicorn)
         → postgis
```

## Exigences

1. `.env.example` sans secrets ; `.env` gitignored
2. Healthcheck : `GET /health` (à ajouter si absent)
3. CORS prod configurable
4. Volumes PostGIS persistants
5. Commandes one-shot documentées (Windows PowerShell + bash)

## README quick start (sections)

1. Prérequis (Docker, keys éventuelles)
2. Copier `.env.example` → `.env`
3. `docker compose up --build`
4. URLs front/API/docs Swagger
5. Jeu de données / import
6. Dépannage courant

## Runbook démo

- Démarrage J-1
- Smoke 5 min
- Rollback simple (recreate containers)
- Contact / ports

## Hors-scope acceptable

- K8s, CI complète, multi-région
- Observabilité avancée (prévoir logs stdout)

## Done when

- [ ] `compose up` documenté et testé
- [ ] Aucun secret dans git
- [ ] Runbook démo prêt
