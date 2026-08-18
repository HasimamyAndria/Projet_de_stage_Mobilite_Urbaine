# Exigences MVP — Mobilité Urbaine (stage)

**Date :** 2026-08-18  
**Sources :** `specification_mobilite_urbaine-stage.pdf`, `Vision_Produit_Mobilite_Urbaine.pdf`, code réel  
**Skill :** `02-ba-vision-exigences`

## 1. Vision (5 lignes)

Plateforme d’**aide à la décision** territoriale : visualiser les flux domicile–travail agrégés, les zones clés (dortoirs, pôles d’emploi, corridors) et un indice d’équilibre emploi-habitat, à partir d’OSM + d’une OD estimée (modèle gravitaire).

Ce n’est **pas** un outil de pilotage trafic temps réel, ni une surveillance individuelle des usagers.

Lot 1 stage = carte décisionnelle + KPI + points clés + indice proxy, démontrable en < 2 min.

Vision cible (hors stage) : OD d’enquête, recommandations de sites, simulation what-if, multi-territoires industrialisé.

Instance stage = démo contrôlée (localhost / Docker), pas un SaaS internet.

## 2. AS-IS / TO-BE

| AS-IS | TO-BE (lot 1) |
|-------|----------------|
| Décision mobilité souvent qualitative, cartes statiques, données éclatées | Une vue carte + indicateurs, même pipeline pour Tana (et une autre ville si OSM importé) |
| Pas de lecture rapide « où concentrer l’attention » | Zones labellisées + top OD + indice M6 coloré |
| Risque de données individuelles | Agrégats zone→zone, k-anonymité k≥5 |

## 3. Personas prioritaires

| Persona | Job to be done (lot 1) |
|---------|------------------------|
| Urbaniste | Couches, search, détail zone, corridors, indice |
| Élu | KPI lisibles, top flux, message simple (limites affichées) |
| DRH | Hors lot 1 (sites candidats = M3, reportable) |

## 4. Exigences fonctionnelles

| ID | Exigence | Module | Priorité | Critère de succès |
|----|----------|--------|----------|-------------------|
| EF-01 | Afficher un fond de carte + couches OSM (routes, bâtiments, bus) filtrées par bbox | M1 | Must | Zoom ≥ 11, FeatureCollection, LIMIT respectés |
| EF-02 | Afficher les desire lines OD agrégées (pas un itinéraire rue) | M1 | Must | Couche visible + légende volumes |
| EF-03 | Rechercher un lieu et recentrer la carte | M1 | Must | Résultat OSM → flyTo |
| EF-04 | Calculer un itinéraire A→B sur le graphe routier | Socle | Must | Géométrie non vide sur points démo connectés ; UI actionnable |
| EF-05 | Labelliser les zones (dortoir / pôle / mixte) et les corridors de volume | M2 | Must | API `/keypoints` + couche carte |
| EF-06 | Clustering spatial basique des zones (K-means) | M2 | Must | `cluster_id` exposé, méthode documentée |
| EF-07 | Panneau KPI : volumes, top OD, comptes M2, synthèse M6 | M5 | Must | Chargement / erreur API visibles |
| EF-08 | Indice emploi-habitat par zone (proxy intra-zone) | M6 | Must | Score ∈ [0,1], couche colorée, limites UI |
| EF-09 | Activer une ville (presets + recherche) et recharger l’analytique | Socle | Must | Message si OSM absent dans la bbox |
| EF-10 | Toggles de couches + légende | M1 | Must | Chaque couche Must masquable |
| EF-11 | Fiche zone au clic (nom, proxies, label, cluster, indice) | M2/M6 | Must | Popup ou panneau, 1 clic |
| EF-12 | Recommandations de sites | M3 | Should | Reporté (hors lot 1) |
| EF-13 | Simulation what-if | M4 | Should | Reporté (hors lot 1) |
| EF-14 | Export PPT / CSV | Polish | Could | Reporté |
| EF-15 | Auth JWT / multi-tenant | Prod | Could | Reporté — démo réseau contrôlé |

## 5. Règles métier

- RM-01 : Aucune donnée individuelle affichée ; agrégation zone→zone obligatoire.
- RM-02 : k-anonymité minimale k≥5 (défaut UI / API souvent 20).
- RM-03 : Desire line ≠ itinéraire pgRouting ; les deux doivent rester distincts dans l’UI.
- RM-04 : Volumes OD du seed OSM = **estimés** (gravité), pas une enquête ménage — mention UI obligatoire.
- RM-05 : Indice M6 = équilibre intra-zone emplois/population proxies ; ce n’est pas un 2SFCA.
- RM-06 : Un corridor M2 = gros volume OD, pas une saturation de capacité d’axe.
- RM-07 : Aide à la décision ≠ monitoring trafic temps réel.
- RM-08 : Labels M2 = heuristiques documentées (médianes pop/emplois).
- RM-09 : Clustering M2 = K-means sur centroïdes, seed reproductible.

## 6. Exceptions / dépendances data

- EX-01 : Sans tables `planet_osm_*`, couches OSM vides et seed réel impossible → repli `--demo` (grille).
- EX-02 : Graphe `roads_network` fragmenté → certains A/B sans chemin (FeatureCollection vide + message).
- EX-03 : Paris / Madrid : même code, mais extract OSM à importer (PBF hors image Docker).
- EX-04 : Nominatim indisponible → recherche de ville 502, presets restent utilisables.

## 7. Hors-scope stage (explicite)

- Temps réel, tracking GPS usager, GTFS complet, 2SFCA, p-médianes, HDBSCAN.
- Auth / TLS / SaaS multi-tenant / CI industrielle.
- M3 recommandations avancées, M4 simulateur complet, export PPT.
- Données individuelles, IRIS/MOBPRO officiels (connecteur prévu plus tard).

## 8. Questions ouvertes (arbitrage PO — déjà tranchées pour le lot 1)

| Question | Décision lot 1 |
|----------|----------------|
| OD réelle ou estimée ? | Estimée OSM + disclaimer |
| Clustering ML vs heuristiques seules ? | Les deux : heuristiques métier + K-means spatial |
| Combien de villes en démo ? | Tana Must ; Paris/Madrid si OSM importé |
| Auth ? | Non — réseau contrôlé |
