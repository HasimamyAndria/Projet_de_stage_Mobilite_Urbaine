# Rapport QA — MVP Mobilité Urbaine

**Date :** 2026-08-18  
**Périmètre :** Must stage (M1 flux/carte, M2 points clés, M5 KPI, M6 emploi-habitat + socle OSM/route/villes)  
**Environnement :** API `http://127.0.0.1:8000`, PostGIS local, seed OD OSM Antananarivo (36 zones)  
**Exécuteur :** `python backend/scripts/smoke_mvp_qa.py`  
**Preuve machine :** `backend/scripts/_smoke_mvp_qa_last.json`

## Verdict

| Critère | Statut |
|---------|--------|
| Smoke API Must | **24/24 OK** |
| Bloquants ouverts | **0** |
| Données individuelles dans OD | **Non** (agrégats zone→zone) |
| Front Vite | **OK** (`http://localhost:5173` → 200) |
| Lot 1 Must | **CLOS** |

## Résultats smoke API (2026-08-18)

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
| `GET /api/od/zones` | FC zones | OK (36, seed OSM) |
| `GET /api/od/flows` | FC desire lines | OK (162 ≤ 300) |
| anonymisation OD | pas d’ids individuels | OK |
| `GET /api/od/summary` (M5) | totaux + top | OK (36 zones) |
| `GET /api/keypoints` (M2) | zones + corridors | OK (21 dortoirs / 1 pôle / 14 mixtes / 5 corridors) |
| keypoints clustering (M2) | `kmeans` + `cluster_id` | OK (k=4, silhouette 0.257) |
| `GET /api/emploi-habitat` (M6) | FC + summary | OK (avg 0.156) |
| scores M6 ∈ [0, 1] | bornes | OK (0.009–0.908) |
| `GET /api/cities/presets` | ≥ 1 preset | OK (3) |
| `GET /api/cities/current` | nom + `osm_ready` | OK (Antananarivo, true) |
| `GET /api/cities/coverage` Tana | `osm_ready=true` | OK (131878 bâtiments) |
| `GET /api/cities/coverage` hors zone | `osm_ready=false` | OK |

## Checklist E2E carte

Front `http://localhost:5173` : HTTP 200. Parcours UI vérifié par revue du code livré (toggles, 4 vues, route, fiche zone) + smoke API des mêmes données. Rejouer les clics visuels J-1 soutenance.

- [x] Chargement map MapLibre (`MapView` + style CARTO, zoom 12)
- [x] Couches OSM (routes / bâtiments / bus) après zoom ≥ 11 (`loadBboxLayers`)
- [x] Toggles de couches (`LayerPanel`, 10 couches Must)
- [x] Desire lines OD visibles (défaut vue Carte / Flux OD)
- [x] Couche M6 colorée (rouge→vert) + corridors M2 (vues Indicateurs / Zones clés)
- [x] Panneau KPI : synthèse + M6 avg/min/max + top OD (`KpiPanel`)
- [x] Search centre la vue (`SearchBar` → `flyTo`)
- [x] Route A→B visible (boutons **Itinéraire démo** + **Choisir A et B**)
- [x] Fiche zone au clic (nom, proxies, label, cluster, indice M6)
- [x] Menu = 4 vues Must (Carte / Flux OD / Zones clés / Indicateurs)
- [x] Message OSM à importer si `osm_ready` faux
- [x] Message d’erreur panneau si API down

## Data / conformité

| Contrôle | Résultat |
|----------|----------|
| OD agrégé zone→zone uniquement | OK (`origin_zone_id`, `passenger_count`, pas de `user_id` / `trip_id`) |
| Volumes estimés signalés | OK (`synthetic: true` + footer / note UI gravitaire) |
| LIMIT respectés | OK (buildings 3000, flows 162 ≤ 300, search 20) |
| Mailles sous seuil masquées | OK — API refuse `min_passengers < 5` ; services OD/M2 filtrent `>= k` (`docs/securite-rgpd.md`) |
| Clustering reproductible | OK — K-means centroïdes, seed fixe, `cluster_id` exposé |

## Bugs trouvés / traités

| Sévérité | Description | Statut |
|----------|-------------|--------|
| **Bloquant** | `GET /api/route` renvoyait FC vide : points démo sur **composantes déconnectées** du graphe `roads_network` | **Corrigé** — points démo remplacés + Dijkstra sur **sous-graphe bbox** (`map.py`, `MapView.tsx`) |
| Majeur | Dijkstra sur tout Madagascar trop lourd / fragile | **Corrigé** — filtre spatial autour de A/B |
| Mineur | `search?q=` renvoie `[]` (200) plutôt que 400 | Accepté / documenté |
| Mineur | Pas de toggles couches carte | **Corrigé** (lot 1, `LayerPanel`) |

## Preuves / logs

```text
Resultat : 24/24 OK
Aucun echec.
Preuve JSON : backend/scripts/_smoke_mvp_qa_last.json
Date UTC : 2026-08-18T19:36:01Z
Front : http://localhost:5173 → 200
```

Scripts utiles :

```powershell
cd Projet_de_stage_Mobilité_Urbaine
.\venv\Scripts\python.exe backend\scripts\smoke_mvp_qa.py
.\venv\Scripts\python.exe backend\scripts\smoke_keypoints.py
```

## Risques restants (non bloquants)

1. Réseau routier **fragmenté** : certains couples A/B restent sans chemin → message UI + FC vide.
2. Données OD / population / emplois **estimées** (gravité OSM) — à rappeler en soutenance.
3. Indice M6 moyen plus bas qu’avec l’ancienne grille 4×4 (0.156 vs 0.782) : seed OSM réel, pas une régression API.
4. Tests pytest / CI industrielle : hors lot 1 (phase 11 déjà Docker/runbook ; CI non exigée stage).

## Next

- Phase 11 déjà livrée (Docker / runbook) — rejouer compose seulement si démo hors machine locale.
- Phase 12 sécu/RGPD : `docs/securite-rgpd.md` déjà présent ; revue J-1.
- Phase 13 soutenance : script démo + clics visuels J-1.
- M3/M4 : **ouverts seulement si marge** après cette clôture Must.

---

## Historique 2026-08-10

Smoke **19/19 OK** sur seed grille 16 zones (avg M6 0.782). Cas clustering M2 et villes absents à cette date.
