# Data model — Mobilité Urbaine (MVP OD)

## Stratégie de peuplement

Territoire carte : **Antananarivo**. Pour démarrer sans matrice OD officielle :

| Approche | Statut | Contenu |
|----------|--------|---------|
| **A — Démo crédible** | **Active** | Grille 4×4 sur **bbox urbaine Antananarivo** (47.45–47.565, -18.95–-18.82) + flux gravitaires |
| B — Semi-réel | Option | Quartiers OSM (`place=suburb…`) |
| C — Réel | Plus tard | Shapefile / enquête / OD locale |

Volumes **agrégés zone→zone** uniquement.

## Schéma réel (base `mobilite`)

### `mobility_zones`

| Colonne | Type | Rôle |
|---------|------|------|
| `id` | serial | PK |
| `name` | varchar | Ex. Zone B2 |
| `geometry` | MultiPolygon **4326** | Emprise |
| `zone_type` | varchar | `grid_demo` |
| `population_proxy` | int | Proxy population |
| `jobs_proxy` | int | Proxy emplois (M6) |

### `mobility_flows` (équivalent OD)

| Colonne | Type | Rôle |
|---------|------|------|
| `origin_zone_id` | int | Origine |
| `destination_zone_id` | int | Destination |
| `trip_count` | int | Volume agrégé |
| `average_distance` | numeric | km (proxy) |
| `average_time` | numeric | min (proxy) |
| `mode` | varchar | `all` |

> Note : le fichier historique `mobilite_urbaine_sql_scripts.sql` mentionnait `od_flows` / `geom`. En base, les tables s’appellent `mobility_flows` / `geometry`. L’API unifie via la vue.

### Vue `v_od_desire_lines`

LineString 4326 centroïde→centroïde + `passenger_count` (= `trip_count`).

## Scripts

```bash
cd backend
.\venv\Scripts\python.exe scripts\seed_zones_od.py
```

SQL source : `backend/scripts/sql/19_seed_zones_od_demo.sql`

## API

- `GET /api/od/zones` → polygones GeoJSON
- `GET /api/od/flows?min_passengers=50` → desire lines
- `GET /api/od/summary` → KPI rapides
- `GET /api/keypoints` → labels M2 + corridors
- `GET /api/emploi-habitat` → indice M6 (GeoJSON + summary)

## Limites (à dire en soutenance)

- Grille ≠ découpage administratif
- Volumes synthétiques (gravité population×emplois / distance)
- Suffisant pour M1 desire lines et socle M5/M2/M6
