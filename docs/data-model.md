# Data model — Mobilité Urbaine (MVP OD)

## Stratégie de peuplement

Territoire carte : **Antananarivo**.

| Approche | Statut | Contenu |
|----------|--------|---------|
| **B — OSM réel** | **Active (défaut)** | Quartiers OSM (`suburb` / `quarter`) → Voronoi ; proxies bâti + POI ; OD gravitaire |
| A — Démo grille | Repli `--demo` | Grille 4×4 synthétique (tests sans OSM) |
| C — Enquête OD | Plus tard | Shapefile / matrice zone→zone officielle |

Volumes **agrégés zone→zone** uniquement.

## Schéma réel (base `mobilite`)

### `mobility_zones`

| Colonne | Type | Rôle |
|---------|------|------|
| `id` | serial | PK |
| `name` | varchar | Nom OSM (quartier) |
| `geometry` | MultiPolygon **4326** | Cellule Voronoi clipée bbox |
| `zone_type` | varchar | `osm_suburb` (ou `grid_demo`) |
| `population_proxy` | int | Bâtiments OSM × facteur |
| `jobs_proxy` | int | POI + landuse emplois OSM |

### `mobility_flows` (équivalent OD)

| Colonne | Type | Rôle |
|---------|------|------|
| `origin_zone_id` | int | Origine |
| `destination_zone_id` | int | Destination |
| `trip_count` | int | Volume agrégé (estimé) |
| `average_distance` | numeric | km (proxy distance sphérique) |
| `average_time` | numeric | min (proxy ~22 km/h) |
| `mode` | varchar | `all` |

### Vue `v_od_desire_lines`

LineString 4326 centroïde→centroïde + `passenger_count` (= `trip_count`).

## Scripts

```powershell
cd backend
# Défaut : OSM réel (planet_osm_* requis)
.\venv\Scripts\python.exe scripts\seed_zones_od.py

# Option : plus / moins de quartiers
.\venv\Scripts\python.exe scripts\seed_zones_od.py --top-n 40

# Repli grille synthétique
.\venv\Scripts\python.exe scripts\seed_zones_od.py --demo
```

Implémentation OSM : `backend/scripts/seed_zones_od_osm.py`

## API

- `GET /api/od/zones` → polygones GeoJSON
- `GET /api/od/flows?min_passengers=50` → desire lines
- `GET /api/od/summary` → KPI (`synthetic: false` si `zone_type` OSM)
- `GET /api/keypoints` → labels M2 + corridors
- `GET /api/emploi-habitat` → indice M6

## Multi-villes

Pipeline portable :

1. Choisir / rechercher une ville (`GET /api/cities/search`, presets)
2. Activer (`POST /api/cities/activate`) → bbox clampée ~20 km
3. Si OSM présent dans la bbox → seed zones + OD gravitaire
4. Sinon → message « importer extract Geofabrik + osm2pgsql »

Antananarivo fonctionne dès que `planet_osm_*` Madagascar est chargé.  
Paris / Madrid : même code, dès qu’un extract OSM de la ville est importé.

## Limites (à dire en soutenance)

- Géométries / densités : **réelles OSM**
- Volumes OD : **estimés** (gravité), pas une enquête ménage
- Suffisant pour simuler M1/M2/M5/M6 sur un territoire réel
- Évolution : matrice OD officielle (approche C) par connecteur local
