# Mobilité Urbaine — Quick start

Plateforme d’aide à la décision (flux OD, points clés, KPI, indice emploi-habitat)  
Stack : **FastAPI + PostGIS/pgRouting + React/MapLibre**.

## Prérequis

- Docker Desktop (Compose v2)
- **ou** Python 3.11 + Node 20+ + PostgreSQL/PostGIS local (dev)

## Démarrage Docker (recommandé démo)

```powershell
cd Projet_de_stage_Mobilité_Urbaine
Copy-Item .env.example .env
docker compose up --build
```

```bash
cd Projet_de_stage_Mobilité_Urbaine
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Carte (front) | http://localhost:8080 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

### Seed OD démo (M1/M2/M5/M6)

Après `compose up` (DB healthy) :

```powershell
docker compose exec backend python scripts/seed_zones_od.py
```

Puis smoke :

```powershell
# depuis l’hôte, API exposée sur :8000
cd backend
.\venv\Scripts\python.exe scripts\smoke_mvp_qa.py
```

> **OSM Madagascar** (routes/bâtiments/bus) n’est **pas** inclus dans l’image : import volumineux à part (`osm2pgsql`) ou brancher `DB_HOST=host.docker.internal` sur une base déjà peuplée.  
> Sans OSM, la démo analytics (zones OD, desire lines, KPI, M6) fonctionne après le seed.

## Dev local (sans Docker API)

1. Configurer `backend/.env` (`DB_HOST=localhost`, …)
2. Backend :

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

3. Frontend :

```powershell
cd frontend
npm install
npm run dev
```

Front : http://localhost:5173 — API : http://127.0.0.1:8000

## Variables d’environnement

Voir [`.env.example`](.env.example) :

| Variable | Rôle |
|----------|------|
| `DB_*` | Connexion PostGIS |
| `CORS_ORIGINS` | Origines front autorisées |
| `VITE_API_URL` | Base URL API (build front) |

**Ne jamais committer** `.env` ni mots de passe réels.

## Backup PostGIS minimal

```powershell
.\scripts\backup_postgis.ps1
```

```bash
./scripts/backup_postgis.sh
```

Fichiers dans `backups/` (gitignored).

## Docs projet

| Doc | Contenu |
|-----|---------|
| [docs/runbook.md](docs/runbook.md) | Démo J-1, dépannage, rollback |
| [docs/qa-rapport.md](docs/qa-rapport.md) | Preuves QA smoke |
| [docs/methodes.md](docs/methodes.md) | Formules M2/M5/M6 |
| [docs/data-model.md](docs/data-model.md) | Schéma OD |

## Dépannage rapide

| Symptôme | Action |
|----------|--------|
| Front CORS error | Vérifier `CORS_ORIGINS` inclut l’URL du front |
| `/api/od/*` 503 | Lancer le seed `seed_zones_od.py` |
| Route vide | Points hors composante connectée — voir runbook |
| Port 5432 occupé | Changer `DB_PORT` dans `.env` (ex. `5433:5432`) |
