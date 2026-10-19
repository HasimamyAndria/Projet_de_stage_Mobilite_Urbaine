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

**Limite affichée dans l’UI :** zones/proxies OSM réels ; volumes OD estimés (modèle gravitaire), agrégés zone→zone.

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
- Proxies `population_proxy` / `jobs_proxy` dérivés d’OSM (bâtiments / POI), pas d’enquête officielle.
- Un score élevé ne garantit pas de courts trajets domicile–travail (polycentrisme, modes, capacité réseau hors scope).
- Évolution possible : 2SFCA + réseau / isochrones + données emplois réelles.

## M2 — Points clés

**Objectif :** prioriser les zones d’intérêt urbanistique.

**Règles MVP (heuristiques métier) :**

| Label | Condition |
|-------|-----------|
| Zone dortoir | `population >= 0.9×médiane` ET `emplois/(pop+emplois) <= 0.38` |
| Pôle emploi | `emplois >= médiane` ET `emplois/(pop+emplois) >= 0.45` |
| Zone mixte | sinon |
| Corridor | top N flux OD par `trip_count` (proxy saturation) |

**Clustering spatial (K-means) :**

- Entrée : centroïdes des zones (`lon`, `lat`), mis à l’échelle min-max
- `k = max(2, min(4, n//3))` (borné par n)
- Seed fixe `42` (reproductible)
- Silhouette moyenne renvoyée dans `clustering.silhouette`
- Nom de groupe = majorité des labels métier dans le cluster
- **Ce n’est pas** un clustering d’individus ni HDBSCAN

**Endpoint :** `GET /api/keypoints?corridor_top_n=5`  
Propriétés zone : `label`, `cluster_id`, `cluster_label`

**Limites :**
- proxies OSM population/emplois (pas d’enquête)
- un “corridor” ici = gros volume desire line, pas une mesure de capacité d’axe routier
- K-means sphérique / euclidien sur lon-lat : approximation locale (ville ~20 km)

## M1 — Desire lines (rappel)

Trait droit centroïde→centroïde. Ce n’est **pas** un itinéraire routier (`/api/route` + pgRouting).

## Catalogue simulé (organisations)

Couche distincte de la matrice gravitaire OSM (`mobility_flows`).

Source : groupes d'employés simulés (`organizations.py`), rattachés aux quartiers de `territory.py`. Une enquête réelle remplace ces tables sans changer les endpoints.

Vitesse supposée : **18 km/h**. Distance : orthodromie × 1,35.

| Indice | Formule |
|--------|---------|
| Génération | actifs résidant dans le cadre / navetteurs de la ville |
| Attractivité | emplois du cadre / navetteurs de la ville |
| Emploi-habitat | emplois / actifs résidents |
| Équilibre | `1 - \|emplois - actifs\| / (emplois + actifs)` |
| Déséquilibre | emplois − actifs résidents |
| Concentration | part de la destination principale |
| Dispersion | `1 - somme des parts²` |
| Mode individuel | part taxi ou voiture |
| Distance moyenne | somme(km × effectif) / effectif |
| Temps moyen | distance / 18 km/h |
| Pression | `100 × (0,35 sortie + 0,35 min(km/25, 1) + 0,30 mode individuel)` |

Profils : K-means, k = 2 à 4, graine 42, k retenu par silhouette maximale. Les employés d'un même groupe partagent les variables, donc le calcul porte sur les groupes.

Chaque fiche d'indice renvoyée par `GET /api/mobility/indicators` contient définition, formule, unité, source, méthode, interprétation et limite. Les scénarios `POST /api/simulation` sont des estimations simulées : ils ne décident pas.

## Analyse des profils (`GET /api/mobility/analysis`)

Même catalogue simulé. Un point = un groupe d'employés (origine, destination, distance, fréquence, mode, secteur). L'organisation est lue à part.

Trois méthodes sont calculées sur les vecteurs mis à l'échelle min-max :

| Méthode | Réglage |
|---------|---------|
| K-means | k de 2 à 4, graine 42, k = silhouette maximale |
| Hiérarchique | lien de Ward, même choix de k |
| DBSCAN | eps 0,28 / 0,40 / 0,55 / 0,75 et minPts 2 ou 3, meilleur couple retenu |

Est retenue la méthode éligible (2 à 4 groupes, au plus 35 % de bruit, silhouette calculable) dont la silhouette est la plus haute. Si K-means est à 0,02 ou moins du meilleur score, il est gardé : les variables sont numériques et les points sont déjà agrégés. DBSCAN sert surtout à constater qu'il n'y a pas de nuage GPS.

Les trois profils métier (périphérie → centre, résidence proche de l'emploi, plusieurs quartiers → même pôle) sont une lecture des groupes, pas la sortie brute de l'algorithme. Le troisième profil est le plus utile aux organisations.

Chaque scénario (bureau satellite, tiers-lieu, télétravail, transport collectif, parking relais, piste cyclable, horaires) indique pourquoi, sur quelles données, combien de personnes, l'impact estimé et les limites. Le libellé est « scénario recommandé » ou « scénario potentiellement pertinent ». Le jeu d'exemple Ivato 30 / Talatamaty 25 / Ambohibao 20 est identifié comme simulé.

## Démarche du chapitre 6 — optimisation des sites

Endpoint : `GET /api/spec/cases` puis `GET /api/spec/cases/{entreprise|collectivite|multi}`.

Les trois cas suivent la structure de la spécification §6.5, sur Antananarivo et les groupes simulés (au moins 20 personnes). Les effectifs d'illustration du PDF (3 000 salariés, 2 800 trajets, 500 postes) ne sont pas recopiés.

1. Demande : domicile, siège, mode, temps, km, CO₂. Distance = orthodromie × 1,35. Vitesse selon le mode (bus 16 km/h, voiture 22 km/h).
2. Candidats : quartiers du catalogue gardés si au moins 30 % des salariés ciblés sont à moins de 30 minutes.
3. Choix : p-médianes glouton. Objectif = minimiser le temps aller-retour pondéré par l'effectif. Capacité hypothétique : 500 postes.
4. Score : temps 30 %, km 25 %, CO₂ 20 % (220 jours), desserte 15 %, faisabilité 10 %. Desserte et faisabilité = rôle du quartier.
5. Restitution : top 5 sur la carte, référence toujours affichée, hypothèses d'adoption (20–100 %) et de télétravail.

La bascule d'un groupe suit un logit sur les minutes gagnées, plafonné par le taux d'adoption. Ce n'est pas un logit calibré sur une enquête, ni un programme linéaire.

