# Exemples chiffrés (code réel)

Ne pas arrondir autrement. Constantes : `seed_zones_od_osm.py`, `keypoints.py`, `emploi_habitat.py`.

## Proxies OSM

```text
population_proxy = max(nb_bâtiments × 4, 50)
jobs_proxy       = max(nb_POI × 8 + nb_landuse_commercial × 25, 20)
```

Exemple : 120 bâtiments, 15 POI, 2 parcelles commerciales  
→ pop = max(480, 50) = **480**  
→ jobs = max(120 + 50, 20) = **170**

## Gravité OD (A → B)

```text
dist_m = max(distance_centroïdes_m, 500)
brut   = (pop_A × jobs_B) / (dist_m ^ 1.35) × 0.045
on garde le flux si brut ≥ 20
trip_count = max(15, round(brut))
temps_min  = (dist_m / 1000) / 22 × 60     # 22 km/h
```

Exemple : pop_A = 2000, jobs_B = 2000, dist = 500 m  
→ 500^1.35 ≈ 4395  
→ brut = (4 000 000 / 4395) × 0.045 ≈ **41**  
→ volume affiché ≈ **41** ; temps ≈ 0,5 / 22 × 60 ≈ **1,4 min**

## M2 labels

```text
part_emplois = jobs / (pop + jobs)
pôle    si jobs ≥ médiane_jobs ET part ≥ 0.45
dortoir si pop ≥ 0.9 × médiane_pop ET part ≤ 0.38
mixte   sinon
corridor = top 5 flux OD (volume), pas une saturation de rue
```

Exemple médianes pop=300, jobs=200 :

| Zone | pop | jobs | part | Label |
|------|-----|------|------|--------|
| Maisons | 500 | 50 | 0,09 | Dortoir |
| Bureaux | 200 | 400 | 0,67 | Pôle |
| Centre | 300 | 200 | 0,40 | Mixte |

## M6

```text
eh_index = 1 - |jobs - pop| / (jobs + pop)     ∈ [0, 1]
```

| pop | jobs | eh | Sens |
|-----|------|----|------|
| 400 | 400 | 1,00 | Équilibré |
| 900 | 100 | 0,20 | Surplus d’habitat |
| 200 | 800 | 0,40 | Surplus d’emplois |
| 0 | 0 | — | Non défini |

## K-means

```text
k = 1 si n<2 sinon max(2, min(4, n//3))
n=36 → k=4 ; seed=42 ; silhouette QA = 0.257
```

## k-anonymité

Aucun flux avec volume < **5**. UI carte OD : min **50** passagers (`loadOdFlows`).

## QA démo Tana (2026-08-18)

36 zones · 21 dortoirs · 1 pôle · 14 mixtes · 5 corridors · M6 avg **0,156** (min 0,009 / max 0,908).
