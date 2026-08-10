# Rapport QA — MVP Mobilité Urbaine

**Date :** 2026-08-10  
**Périmètre :** Must stage (M1 flux/carte, M2 points clés, M5 KPI, M6 emploi-habitat + socle OSM/route)  
**Environnement :** API `http://127.0.0.1:8000`, PostGIS local, seed OD démo Antananarivo  
**Exécuteur :** `python backend/scripts/smoke_mvp_qa.py`  
**Preuve machine :** `backend/scripts/_smoke_mvp_qa_last.json`

## Verdict

| Critère | Statut |
|---------|--------|
| Smoke API Must | **19/19 OK** |
| Bloquants ouverts | **0** |
| Données individuelles dans OD | **Non** (agrégats zone→zone) |
| Démo soutenance | **OK** après correctif route |

## Résultats smoke API

| Cas | Attendu | Résultat |
|-----|---------|----------|
| `GET /health` | 200 ok | OK |
| `GET /api/roads` bbox dense | FeatureCollection | OK (3589) |
| `GET /api/buildings` bbox dense | FeatureCollection + LIMIT | OK (3000 = LIMIT) |
| `GET /api/bus-stops` bbox dense | FeatureCollection | OK (347) |
| `GET /api/bus-lines` bbox dense | FeatureCollection | OK (202) |
| roads bbox périphérie | 200 + FC | OK (235) |
| roads bbox hors zone | 200 + 0 features | OK |
| `GET /api/search?q=Antananarivo` | 200 liste | OK |
| `GET /api/search?q=` | 200/400/422 documenté | OK (200 → `[]`) |
| `GET /api/route` A→B | géométrie non vide | OK (40 segments) |
| `GET /api/zones/bounds` | xmin…ymax | OK |
| `GET /api/od/zones` | FC zones | OK (16) |
| `GET /api/od/flows` | FC desire lines | OK (164 ≤ 300) |
| anonymisation OD | pas d’ids individuels | OK |
| `GET /api/od/summary` (M5) | totaux + top | OK |
| `GET /api/keypoints` (M2) | zones + corridors | OK |
| `GET /api/emploi-habitat` (M6) | FC + summary | OK (avg 0.782) |
| scores M6 ∈ [0, 1] | bornes | OK (0.6–0.983) |

## Checklist E2E carte (manuel)

À rejouer avant soutenance (navigateur `http://localhost:5173`) :

- [ ] Chargement map MapLibre
- [ ] Couches OSM (routes / bâtiments / bus) après zoom ≥ 11
- [ ] Desire lines OD visibles
- [ ] Couche M6 colorée (rouge→vert) + corridors M2
- [ ] Panneau KPI : synthèse + M6 avg/min/max + top OD
- [ ] Search centre la vue
- [ ] Route A→B visible (points démo connectés)
- [ ] Message d’erreur panneau si API down

> Note : pas de toggles couches UI pour l’instant (hors Must QA ; polish).

## Data / conformité

| Contrôle | Résultat |
|----------|----------|
| OD agrégé zone→zone uniquement | OK (`origin_zone_id`, `passenger_count`, pas de `user_id` / `trip_id`) |
| Volumes synthétiques signalés | OK (`synthetic: true` + note UI) |
| LIMIT respectés | OK (buildings 3000, flows ≤ 300, search 20) |
| Mailles sous seuil masquées | OK — API refuse `min_passengers < 5` ; services OD/M2 filtrent `>= k` (`docs/securite-rgpd.md`) |

## Bugs trouvés / traités

| Sévérité | Description | Statut |
|----------|-------------|--------|
| **Bloquant** | `GET /api/route` renvoyait FC vide : points démo sur **composantes déconnectées** du graphe `roads_network` | **Corrigé** — points démo remplacés + Dijkstra sur **sous-graphe bbox** (`map.py`, `MapView.tsx`) |
| Majeur | Dijkstra sur tout Madagascar trop lourd / fragile | **Corrigé** — filtre spatial autour de A/B |
| Mineur | `search?q=` renvoie `[]` (200) plutôt que 400 | Accepté / documenté |
| Mineur | Pas de toggles couches carte | Ouvert (polish UX) |

## Preuves / logs

```text
Resultat : 19/19 OK
Aucun echec.
Preuve JSON : scripts/_smoke_mvp_qa_last.json
Date UTC : 2026-08-10T14:54:16Z
```

Scripts utiles :

```bash
cd backend
.\venv\Scripts\python.exe scripts\smoke_mvp_qa.py
.\venv\Scripts\python.exe scripts\smoke_kpi.py
.\venv\Scripts\python.exe scripts\smoke_keypoints.py
.\venv\Scripts\python.exe scripts\smoke_emploi_habitat.py
```

## Risques restants (non bloquants)

1. Réseau routier **fragmenté** : certains couples A/B restent sans chemin → message console + FC vide.
2. Données OD / population / emplois **synthétiques** (à rappeler en soutenance).
3. Pas encore de tests pytest CI / Docker (phase 11 devops).

## Next

- Phase 11 — `11-devops-production` (Docker Compose, `.env.example`, runbook)
- Optionnel : toggles couches + checklist E2E cochée avec captures
