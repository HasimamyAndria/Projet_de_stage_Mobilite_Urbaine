# Runbook démo — Mobilité Urbaine

Checklist opérationnelle pour une **démo soutenance** reproductible.

## Ports

| Port | Service |
|------|---------|
| 8080 | Frontend (nginx Docker) |
| 8000 | API FastAPI |
| 5432 | PostGIS (compose) — ou 5433 si conflit |
| 5173 | Vite (dev only) |

## J-1 (préparation)

1. Vérifier Docker Desktop démarré
2. `Copy-Item .env.example .env` et **changer** `DB_PASSWORD` si machine partagée
3. Pour une « prod » stage hors localhost : `APP_ENV=production` (désactive `/docs`)
4. `docker compose up --build -d`
5. Attendre healthy : `docker compose ps`
6. Seed OD : `docker compose exec backend python scripts/seed_zones_od.py`
7. Smoke : `python backend/scripts/smoke_mvp_qa.py` (API sur :8000)
8. Ouvrir http://localhost:8080 (+ `/docs` seulement si `APP_ENV=development`)
9. (Option) Brancher base OSM locale : `DB_HOST=host.docker.internal` dans `.env`, rebuild backend only
10. Conformité : voir `docs/securite-rgpd.md`

## Jour J — smoke 5 min

```text
[ ] GET /health → {"status":"ok"}
[ ] Carte charge (fond MapLibre)
[ ] Panneau KPI : zones, top OD, score M6
[ ] Couche M6 colorée + desire lines
[ ] Search basique
[ ] Route A→B visible (points démo MapView)
```

Script automatisé :

```powershell
cd backend
.\venv\Scripts\python.exe scripts\smoke_mvp_qa.py
```

Attendu : **19/19 OK** (voir `docs/qa-rapport.md`).

## Rollback simple

```powershell
docker compose down
docker compose up --build -d
docker compose exec backend python scripts/seed_zones_od.py
```

Reset volume DB (⚠️ efface les données compose) :

```powershell
docker compose down -v
docker compose up --build -d
```

## Backup / restore minimal

Backup :

```powershell
.\scripts\backup_postgis.ps1
```

Restore (exemple) :

```powershell
Get-Content .\backups\mobilite_YYYYMMDD_HHMM.dump -Encoding Byte |
  docker compose exec -T db pg_restore -U mobilite -d mobilite --clean --if-exists
```

## Incidents courants

| Problème | Cause probable | Fix |
|----------|----------------|----|
| 503 sur `/api/od/*` | Tables absentes | Seed OD |
| CORS bloqué | Origine absente | Ajouter l’URL dans `CORS_ORIGINS` |
| Route 0 segment | Graphe fragmenté | Points connectés (déjà calés en MapView) |
| `db` unhealthy | Port 5432 pris | `DB_PORT=5433` + adapter mapping compose |
| Front appelle mauvais host | Build sans `VITE_API_URL` | Rebuild front avec arg |

## Contact / ownership (stage)

| Rôle | Responsable |
|------|-------------|
| Démo live | Stagiaire |
| DB / seed | Stagiaire |
| Encadrement | Tuteur entreprise / académique |

## Hors-scope prod

Pas de K8s, pas de CI complète, pas d’observabilité avancée : logs stdout Docker suffisent pour le stage.
