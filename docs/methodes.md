# Méthodes analytiques — MVP

## M5 — KPI / Dashboard

**Objectif :** donner une lecture décideur des flux OD sans ouvrir la console.

**Sources :**
- `mobility_zones` (nombre de zones)
- `mobility_flows` / vue `v_od_desire_lines` (volumes)

**Indicateurs affichés :**
- nombre de zones
- nombre de flux OD
- volume total (`SUM(trip_count)`)
- flux max / moyenne
- top 5 desire lines (origine → destination + volume)

**Endpoint :** `GET /api/od/summary?top_n=5`

**Limite affichée dans l’UI :** volumes synthétiques (modèle gravitaire), agrégés zone→zone.

**RGPD / k-anonymité :** aucun flux avec `passenger_count < 5` n’est exposé (`K_ANONYMITY_MIN` dans `backend/app/privacy.py` ; défaut UI = 20). Voir `docs/securite-rgpd.md`.

## M6 — Indice emploi-habitat (proxy)

**Objectif :** objectiver l’équilibre (ou le déséquilibre) emplois / habitat **par zone**, pour alimenter le diagnostic territorial (pas un modèle d’accessibilité complet).

**Sources :**
- `mobility_zones.population_proxy`
- `mobility_zones.jobs_proxy`

**Formule (par zone) :**

```text
eh_index = 1 - |jobs_proxy - population_proxy| / (jobs_proxy + population_proxy)
```

avec `eh_index ∈ [0, 1]` (si `population + jobs = 0` → score non défini).

| Valeur | Lecture |
|--------|---------|
| ≈ 1.0 | équilibre (emplois ≈ population dans la zone) |
| ≈ 0.0 | déséquilibre fort (presque uniquement emplois **ou** habitat) |

**Sens du déséquilibre (propriété `imbalance`) :**
- `jobs_surplus` si emplois > population
- `housing_surplus` si population > emplois
- `balanced` si égalité

**Agrégats panneau KPI :** moyenne, minimum, maximum (+ noms des zones extrêmes).

**Endpoint :** `GET /api/emploi-habitat`  
→ FeatureCollection GeoJSON (`properties.eh_index`) + `summary` + `formula` + `note`.

**Couche carte :** fill coloré (rouge → orange → vert) selon `eh_index`.

**Limites (à dire en soutenance) :**
- **Proxy intra-zone uniquement** : on ne mesure pas l’accès aux emplois des zones voisines.
- Ce n’est **pas** un **2SFCA** (Two-Step Floating Catchment Area) ni un temps de trajet réel.
- Proxies `population_proxy` / `jobs_proxy` synthétiques (seed démo), pas INSEE/SIRENE.
- Un score élevé ne garantit pas de courts trajets domicile–travail (polycentrisme, modes, capacité réseau hors scope).
- Évolution possible : 2SFCA + réseau / isochrones + données emplois réelles.

## M2 — Points clés

**Objectif :** prioriser les zones d’intérêt urbanistique.

**Règles MVP (heuristiques) :**

| Label | Condition |
|-------|-----------|
| Zone dortoir | `population >= 0.9×médiane` ET `emplois/(pop+emplois) <= 0.38` |
| Pôle emploi | `emplois >= médiane` ET `emplois/(pop+emplois) >= 0.45` |
| Zone mixte | sinon |
| Corridor | top N flux OD par `trip_count` (proxy saturation) |

**Endpoint :** `GET /api/keypoints?corridor_top_n=5`

**Limites :**
- proxies synthétiques population/emplois
- un “corridor” ici = gros volume desire line, pas une mesure de capacité d’axe routier
- pas encore de clustering ML (K-means/DBSCAN) — possible évolution

## M1 — Desire lines (rappel)

Trait droit centroïde→centroïde. Ce n’est **pas** un itinéraire routier (`/api/route` + pgRouting).
