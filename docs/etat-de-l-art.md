# État de l’art — Plateforme d’aide à la décision « Mobilité Urbaine »

**Mémoire de stage M2 professionnel**  
**Projet :** MobilitySmart / Mobilité Urbaine (lot 1 : modules M1, M2, M5, M6)  
**Cadre :** 88 jours · cahier des charges `specification_mobilite_urbaine-stage.pdf`  
**Nature du chapitre :** veille technologique argumentée (pas une revue de littérature scientifique)  
**Grille suivie :** 20 axes en 5 blocs — *Grille d’analyse pour l’état de l’art — Projet informatique de stage, Master 2 professionnel* (consultée le 1er septembre 2026)  
**Date de rédaction :** 1er septembre 2026

---

## Comment lire ce chapitre

En master professionnel, l’état de l’art sert à **justifier des choix** que l’équipe pourra encore maintenir après le stage. Chaque affirmation technique est sourcée et datée. Les sources éditeurs (FastAPI, PostGIS, MapLibre, OSM) sont légitimes ; leur biais commercial éventuel est signalé.

La question que le jury pose en soutenance est toujours la même : **pourquoi ce choix, et pas l’autre ?** L’axe 19 rassemble la réponse. Les axes 1 (existant interne) et 14 (faisabilité Madagascar) empêchent de confondre ce mémoire avec un exposé générique sur les « smart cities ».

**Périmètre volontairement refusé.** Ce n’est pas un GPS temps réel, ni un concurrent de Waze / Google Maps, ni une plateforme IoT / Big Data. Le produit est une **aide à la décision territoriale** : flux domicile–travail agrégés, zones clés, indice emploi-habitat.

**Volume.** Ce chapitre est calé pour 8 à 15 pages imprimées (~15–20 % d’un mémoire). La contribution personnelle (implémentation, résultats, limites) reste la partie dominante du rapport.

---

# Bloc A — Cadrage du besoin et de la démarche

## Axe 0 — Démarche de veille et traçabilité des sources

**Période couverte :** mai 2026 – 1er septembre 2026 (cadrage, développement, clôture du lot 1).

**Mots-clés utilisés (FR / EN) :** aide à la décision urbaine, matrice origine-destination, desire lines, modèle gravitaire, emploi-habitat, k-anonymité, PostGIS, pgRouting, MapLibre, FastAPI GeoJSON, clustering spatial K-means vs DBSCAN, 2SFCA, OpenStreetMap Madagascar, loi 2014-038, OWASP Top 10 2025.

**Types de sources, par ordre de poids dans ce stage :**

| Type | Rôle | Biais à signaler |
|------|------|------------------|
| Documentation officielle (FastAPI, PostgreSQL/PostGIS, pgRouting, MapLibre, osm2pgsql, Docker, OSM) | Source de vérité technique | Éditeur : décrit le produit sous son meilleur jour |
| Cahier des charges et vision produit du stage | Imposé / négociable | Document interne de cadrage, pas une évaluation neutre |
| Dépôts publics et guides de praticiens (OWASP, CNIL, ThoughtWorks Radar, Stack Overflow Survey) | Maturité, risques, compétences marché | Enquêtes auto-déclaratives ; Radar = opinion d’un cabinet |
| Articles fondateurs (Wilson 1971, Luo & Wang 2003, Sweeney 2002, Ester et al. 1996) | Ancrer un algorithme, pas « faire de la recherche » | Âge : on les cite pour le **principe**, pas comme état 2026 |
| Fiches commerciales (ArcGIS, Google Maps Platform, Carto, Kepler.gl) | Benchmark « faire vs acheter » | Biais commercial fort |

**Ce qui n’a pas été fait.** Une revue systématique Scopus/IEEE sur la *smart mobility*. Ce n’aurait pas aidé à choisir entre PostGIS et un GeoJSON statique pour un prototype de 88 jours.

**Outil de traçabilité.** Bibliographie en fin de chapitre, avec date de consultation de chaque URL. Constitution au fil de l’eau (recommandation de la grille : ne pas reconstruire en fin de stage).

**Livrable de l’axe :** 18 références tracées (cible 12–20).

---

## Axe 1 — Entreprise d’accueil, commanditaire et existant interne

Le stage s’inscrit dans un **projet informatique de master professionnel** (cadre BIHAR, étudiant ETU001083), commandité par le cahier des charges *Spécification mobilité urbaine — stage* et la vision produit associée. Il n’existe **pas** de système d’information métier déjà en production à étendre : le livrable est un **prototype greenfield** démontrable, pas une évolution d’un SI legacy.

### Ce qui s’impose (non négociable)

| Contrainte | Origine | Conséquence |
|------------|---------|-------------|
| Durée ~ 88 jours ouvrés (~ 4 mois) | Estimation de charge stage | Lot 1 = Must (M1, M2, M5, M6) ; M3/M4 reportés |
| Aide à la décision, pas le temps réel | CDC + vision produit | Écarte Kafka, capteurs, SLA trafic |
| Agrégation zone→zone, k-anonymité k ≥ 5 | CDC + RGPD / éthique mobilité | Pas de traces individuelles, pas de GPS usager |
| Stack cadrée : Python, API, carte web, spatial | CDC / estimation | FastAPI, PostGIS, MapLibre — pas un choix « au hasard » |
| Démo soutenance reproductible | Attendu M2 | Docker Compose + runbook + smoke QA |

### Ce qui est négociable (et a été négocié)

| Sujet | Décision lot 1 | Motif |
|-------|----------------|-------|
| OD réelle (MOBPRO / enquête) vs estimée | **Estimée** (gravité OSM) + disclaimer UI | Pas de matrice officielle Antananarivo dans le délai |
| Clustering « ML » vs règles métier | **Les deux niveaux** : heuristiques lisibles + regroupement spatial simple | Un élu doit comprendre le label « dortoir » |
| Auth JWT dès le jour 1 | **Reportée** | Démo réseau contrôlé ; Must métier d’abord |
| Multi-villes industrialisé | Presets + import OSM, pas un SaaS | Extract PBF hors image Docker |

### Compétences et maintenance après le stage

L’équipe de reprise n’est pas une DSI de 20 personnes. Le critère retenu : **un autre stagiaire ou un tuteur Python/SQL doit pouvoir relancer la démo**. D’où :

- trois conteneurs (`frontend`, `backend`, `db`), pas de microservices ;
- SQL paramétré plutôt qu’un ORM géospatial lourd ;
- documentation dans `docs/` (architecture, méthodes, runbook, sécurité) ;
- secrets hors Git (`.env`).

Une architecture « élégante » que personne ne saura relancer dans un an serait un **mauvais choix**, quelles que soient ses qualités (note d’utilisation de la grille, axes 1 et 14).

**Livrable de l’axe :** contraintes imposées vs négociables (tableaux ci-dessus).

---

## Axe 2 — Besoin métier, domaine et cadre réglementaire

### Problème réel

Les décisions d’urbanisme mobilité (où concentrer l’attention : déséquilibre emploi-habitat, corridors de demande) se font trop souvent à partir de cartes statiques, d’intuitions et de données éclatées. Le commanditaire veut **une vue unique**, compréhensible en moins de deux minutes par un urbaniste et un élu.

Personas lot 1 : **urbaniste** (couches, fiche zone, corridors) et **élu** (KPI, top flux, message simple). Le persona DRH (sites candidats) relève du module M3, **hors lot 1**.

### Ce que le processus TO-BE doit produire

1. Une carte des **flux OD agrégés** (desire lines : demande quartier → quartier, **pas** un itinéraire rue).
2. Des **points clés** : zone dortoir, pôle d’emploi, zone mixte, corridors de volume.
3. Un **indice emploi-habitat** intra-zone (proxy), coloré, avec ses limites affichées.
4. Un socle cartographique OSM (voirie, bâti, bus) et un itinéraire A→B sur le graphe réel (pgRouting), pour **contraster** demande et réseau.

### Règles métier incontournables (extrait)

- Aucune donnée individuelle ; agrégation zone→zone.
- Seuil k-anonymité k ≥ 5 (défaut d’exposition souvent 20).
- Desire line ≠ itinéraire routier.
- Volumes du seed OSM = **estimés**, pas une enquête ménage.
- Indice M6 ≠ accessibilité 2SFCA.
- Produit ≠ surveillance ni pilotage trafic live.

### Cadre réglementaire applicable

| Texte | Portée pour ce prototype |
|-------|--------------------------|
| Loi malgache n° 2014-038 relative à la protection des données personnelles + CMIL | Applicable dès qu’on traiterait des données personnelles ; le MVP **évite** ce traitement (OSM public + agrégats synthétiques) |
| RGPD (UE) | Applicable si hébergement / responsable UE ou personnes UE ; principe de minimisation repris même en démo |
| CNIL — géolocalisation | Interdit le tracking individuel « pour voir » ; conforte l’agrégation |
| Licence OSM Open Database License (ODbL) | Attribution obligatoire ; dérivés de la base à partager sous ODbL |
| Politique d’usage Nominatim | Rate-limit ; pas un geocoder de production sans instance dédiée |

**Livrable de l’axe :** cartographie processus + règles + parties prenantes (urbaniste, élu, tuteur, stagiaire ; pas l’usager GPS).

---

# Bloc B — Analyse de l’existant et des utilisateurs

## Axe 3 — Solutions existantes et benchmark (faire vs acheter)

Le piège classique est de comparer le projet à **Google Maps** ou **Waze**. Ces produits optimisent le **trajet d’un usager en temps réel**. Notre besoin est un **diagnostic territorial agrégé**. Le benchmark utile est donc : SIG décisionnel, visualisation OD, accessibilité, pas la navigation grand public.

### Tableau comparatif multicritères

Critères (pondération indicative, total 100) : adéquation au diagnostic OD/emploi-habitat (25), coût 3 ans / licences (20), données Madagascar / OSM (15), maintenabilité par un profil Python (15), délai 88 jours (15), souveraineté / pas de lock-in API payante (10).

| Solution | Type | Licence / coût | Couvre OD agrégé + labels métier + indice EH ? | Madagascar | Verdict stage |
|----------|------|----------------|-----------------------------------------------|------------|---------------|
| Google Maps Platform | Navigation / fond de carte | Payant à l’usage (biais éditeur) | Non (pas de M2/M6 métier) | Oui, mais TOS + facture | **Écarté** comme cœur ; fond payant inutile |
| Waze / Citymapper / Moovit | Info voyageur | SaaS grand public | Non | Couverture inégale, transport informel mal décrit | **Mauvais analogue** |
| ArcGIS Online / Urban | SIG commercial | Licences élevées | Oui en théorie (Spatial Analyst, Urban) | Oui si on paie | **Acheter** = hors budget stage + lock-in |
| QGIS | SIG desktop | GPL, gratuit | Oui pour un expert, non pour un élu en 60 s | Oui (OSM) | **Complément** hors ligne, pas le livrable web |
| Carto / Felt | SaaS carto analytics | Abonnement | Visualisation forte, métier M2/M6 à reconstruire | Oui | Coût récurrent en devises + dépendance |
| Kepler.gl | Lib visuel (Uber) | MIT | Superbe pour desire lines, **pas** d’API métier ni RGPD k | Oui | **Écarté** comme produit ; idée UX retenue (arcs) |
| OpenTripPlanner / r5 / Conveyal | Accessibilité / GTFS | Open source | Accessibilité ≠ OD emploi-habitat du CDC | GTFS Tana quasi absent | **Écarté** (pas de GTFS fiable) |
| Prototype dédié (ce stage) | Web FastAPI + PostGIS + MapLibre | Stack libre | Oui, calé CDC | OSM Geofabrik Madagascar | **Retenu** |

### Argumentaire « développer » plutôt qu’« acquérir »

1. **Aucune offre du marché ne livre** les règles métier du CDC (dortoir / pôle / mixte + indice intra-zone + k-anonymité) clés en main pour Antananarivo.
2. **MOBPRO / IRIS** (France) n’existent pas à Madagascar : un achat « stack INSEE » serait un faux ami.
3. Le stage a une **valeur pédagogique** : concevoir le pipeline, pas paramétrer ArcGIS.
4. Le coût d’un SaaS carto en devises (axe 16) n’est pas soutenable pour un prototype de soutenance, et crée une dépendance après le départ du stagiaire.

Ce que le « faire » **ne justifie pas** : réécrire un moteur de tuiles, un geocoder mondial, ou un simulateur what-if (M4) — on **consomme** OSM, Carto CDN (fond), Nominatim (recherche de ville), pgRouting (Dijkstra).

**Livrable de l’axe :** tableau + argumentaire faire / acheter.

---

## Axe 4 — Utilisateurs, usages et expérience

| Persona | Matériel réel | Contexte | Exigence UX |
|---------|---------------|----------|-------------|
| Urbaniste | PC de bureau, navigateur récent, écran ≥ 14" | Analyse 90 s : search, couches, fiche zone | Carte full-bleed, toggles, légende, popup |
| Élu | PC ou visio, peu de temps | Lecture 60 s : 4 chiffres + top flux | Pas de jargon non traduit ; limites visibles |
| Reprise technique | PC + Docker Desktop | Relancer la démo | Runbook, pas un wizard SaaS |

**Parcours cibles** (déjà spécifiés dans `docs/ux-mvp.md`) : quatre vues = quatre jobs (Carte, Flux OD, Zones clés, Indicateurs). Pas de pages « bientôt » pour M3/M4.

**Accessibilité (WCAG 2.2).** Lot 1 : contraste des couches (rouge/vert M6 **doublé** d’un libellé texte dans le panneau — on ne s’appuie pas sur la seule couleur), focus clavier partiel, pas d’audit RGAA formel. **Écart accepté** : un audit WCAG complet dépasse 88 jours ; c’est un risque résiduel (axe 19).

**Localisation.** Interface **française**. Malgache : hors lot 1 (public décideur francophone). Pas d’app mobile native : le besoin n’est pas le terrain piéton, c’est le poste de travail.

**Équipement et réseau.** Voir axe 14 : le parcours élu suppose une connexion pour les tuiles Carto ; la démo Docker locale reste possible une fois les images tirées. Pas d’offline-first carte (PWA tuiles) — écart conscient.

**Livrable de l’axe :** personas + parcours + exigences d’ergonomie (lot 1 vs reporté).

---

# Bloc C — Analyse technique

## Axe 5 — Paradigmes et architectures logicielles

### Options envisagées

| Style | Coût de complexité | Adéquation 88 j / 1 développeur |
|-------|--------------------|----------------------------------|
| Monolithe modulaire (API + front + SGBD) | Faible | **Retenu** |
| Microservices (OD, carte, auth, jobs) | Élevé (réseau, observabilité, versions) | Rejeté : sur-ingénierie |
| Event-driven (Kafka, Spark) | Très élevé | Rejeté : pas de flux temps réel |
| Serverless multi-cloud | Moyen-élevé + coût | Rejeté : devises + reprise |
| Hexagonal / clean architecture stricte | Moyen | Rejeté : volume de code vs valeur ; **séparation router / service** suffit |
| Offline-first (sync CRDT) | Élevé | Rejeté ; mitigation : Docker local (axe 14) |

L’architecture livrée est un **monolithe modulaire en 3 conteneurs** :

```text
[Urbaniste / Élu]
        │  HTTP localhost
        ▼
[React + MapLibre] ──REST JSON / GeoJSON──► [FastAPI]
                                               │ SQL paramétré
                                               ▼
                                        [PostgreSQL + PostGIS + pgRouting]
```

Pas de bus de messages. Front et API découplés par contrat REST (OpenAPI en développement). Côté code : routeurs minces, logique dans `services/`.

**Motif du rejet des microservices.** Fowler rappelle qu’il faut d’abord un monolithe qui fonctionne ; le Radar ThoughtWorks a longtemps classé la « microservices envy » comme un risque. Avec un stagiaire, le coût de complexité l’emporte.

**Livrable de l’axe :** architecture cible + alternatives écartées.

---

## Axe 6 — Écosystème technologique (stack)

### Matrice de sélection (pondération explicite)

Critères : maturité 2026 (20), licence compatible usage académique / commercial ultérieur (15), compétences trouvables (Python/JS/SQL à Antananarivo et en M2) (20), adéquation géospatiale (25), pérennité 3 ans (10), documentation (10).

| Couche | Candidats | Retenu | Écarté | Pourquoi |
|--------|-----------|--------|--------|----------|
| Backend | FastAPI, Django, Flask, Express, Spring | **FastAPI 0.136** | Django (batteries mais lourd pour API geo), Node (moins de GeoPandas/PostGIS en CDC), Spring (courbe Java) | OpenAPI natif, typage Pydantic, CDC Python |
| Front | React, Vue, Svelte, Angular | **React 19 + Vite** | Angular (surdimensionné), Svelte (moins de profils locaux) | Écosystème, compétences M2 |
| Carte | MapLibre GL, Leaflet, Mapbox GL payant, OpenLayers | **MapLibre GL 5** | Leaflet (raster, moins fluide pour beaucoup de GeoJSON), Mapbox token | Fork libre de Mapbox GL ; pas de facture |
| SGBD | PostGIS, SpatiaLite, Mongo + GeoJSON, fichiers | **PostgreSQL 16 + PostGIS + pgRouting** | Fichiers (pas de Dijkstra ni bbox SQL), Mongo (moins d’outil métier SIG) | Déjà le standard SIG ; image `pgrouting/pgrouting:16-3.4-3.6.1` |
| HTTP client | axios, fetch | **axios** | — | Déjà en place |
| Conteneurs | Docker Compose, K8s, Vagrant | **Compose v2** | K8s (sur-ingénierie) | Démo J-1 en une commande |
| Import OSM | osm2pgsql, osmium+imposm, GeoJSON pré-découpés | **osm2pgsql** | Imposm (moins documenté dans le CDC) | Pipeline officiel OSM → `planet_osm_*` |

**Licences.** FastAPI (MIT), React (MIT), MapLibre (BSD), PostgreSQL (PostgreSQL Licence), osm2pgsql (GPL) : compatibles avec un prototype académique et une éventuelle suite interne. OSM : ODbL (attribution).

**Compétences locales.** Python, JavaScript et PostgreSQL sont les profils les plus enseignés / demandés en développement web à Antananarivo, contrairement à Scala/Spark ou à un stack ArcGIS sous licence.

**Pérennité 3 ans.** PostGIS et PostgreSQL sont des piliers SIG depuis plus de quinze ans. MapLibre est le successeur communautaire de Mapbox GL JS v1 (sortie de Mapbox du 100 % open source : biais éditeur Mapbox). FastAPI est devenu un standard d’API Python (enquête développeurs : Python reste dans le peloton de tête des langages backend).

**Livrable de l’axe :** matrice ci-dessus.

---

## Axe 7 — Données et flux d’information

### Persistance

- **SRID 3857** en tables OSM (`planet_osm_*`), **4326** en sortie API et pour `mobility_zones` / desire lines.
- Tables métier : `mobility_zones` (polygones, proxies population/emplois), `mobility_flows` (couplets O→D, `trip_count`), vue `v_od_desire_lines`.
- Graphe : `roads_network` + vertices, Dijkstra (`pgr_dijkstra`) sur **sous-graphe bbox** (~5 km autour de A/B).

### Échange

| Sujet | Choix | Alternative écartée |
|-------|-------|---------------------|
| API | REST + JSON / GeoJSON `FeatureCollection` | GraphQL (pas de graphe de ressources profond), WebSocket (pas de live) |
| Contrat | OpenAPI (Swagger **off** si `APP_ENV=production`) | WSDL, gRPC |
| Volumétrie | Bbox + LIMIT (routes 5000, bâtiments 3000, flows ≤ 300–1000) | Tout charger côté client |
| Sync | Requête à la demande (debounce carte 450 ms) | MQTT / cache Redis (hors scope) |

**Volumétrie à 3 ans.** Si l’on passe d’une ville (Tana, ~16–40 zones) à une métropole IRIS, le goulot sera le **GeoJSON OSM au zoom trop large**, pas le JSON des flux. Repli documenté : tuiles vectorielles MVT — **non fait** au lot 1 (axe 11).

**Perte de connexion.** L’API et la carte tuiles échouent de façon visible (message panneau). Pas de file offline. Mitigation : instance Docker locale (axe 14).

**Cycle de vie.** OSM se rafraîchit par ré-import PBF (pas de réplication osm2pgsql-replication en prod stage). OD seed : script `seed_zones_od.py` reproductible. Pas d’archivage légal : pas de données personnelles.

**Livrable de l’axe :** paradigme de persistance PostGIS + REST GeoJSON.

---

## Axe 8 — Briques algorithmiques et services d’IA *(selon projet)*

Le CDC parle d’analyse spatiale, pas d’un LLM ni d’une API d’IA payante. **Aucune brique IA tierce n’est consommée** (pas d’OpenAI, pas de Hugging Face en production). Coût récurrent d’API : zéro. Risque « le fournisseur ferme l’API » : **non applicable**.

### Algorithmes réellement en jeu

| Brique | Rôle | Faire vs consommer |
|--------|------|--------------------|
| Modèle **gravitaire** (principe Wilson 1971) | Estimer `trip_count` ∝ pop_i × jobs_j / f(distance) | **Implémenté** en SQL/Python de seed ; pas un SaaS |
| **Heuristiques M2** | Labels dortoir / pôle / mixte (médianes) | **Implémenté** (`keypoints.py`) — lisible en soutenance |
| **K-means** (centroïdes de zones) | Regroupement spatial optionnel / cible architecture | n petit (~16–40) ; sklearn **non** imposé dans l’image Docker minimale |
| Dijkstra **pgRouting** | Itinéraire A→B | **Consommer** la bibliothèque C/SQL, pas réécrire A* |
| Indice **M6** | `1 − \|E−H\|/(E+H)` | Formule maison documentée ; **pas** un 2SFCA |
| 2SFCA (Luo & Wang 2003) | Accessibilité aux emplois | **Écarté** : pas de temps de trajet emplois réels |
| DBSCAN / HDBSCAN (Ester 1996 et suite) | Clusters de traces GPS | **Écarté** : pas de traces ; n zones trop petit ; moins lisible pour un élu |
| p-médianes | Localisation de sites (M3) | **Reporté** avec M3 |

**Pourquoi pas DBSCAN « parce que c’est plus scientifique ».** DBSCAN brille sur des nuages GPS bruités. Ici les objets sont des **zones déjà agrégées**. Un clustering densité sur 16 polygones est du théâtre méthodologique. Les heuristiques sur médianes sont **évaluables** (on peut contester le seuil 0,38) ; un epsilon DBSCAN ne l’est pas par un élu.

**Pourquoi pas un service d’IA générative** pour « recommander des sites ». Hors lot 1 (M3), coût, non-reproductibilité, et hallucination sur du spatial.

**Protocole d’évaluation (lot 1) :** smoke QA (bornes M6 ∈ [0,1], pas d’id individuels, LIMIT) ; silhouette K-means si clustering exposé ; lecture métier qualitative (top 5 OD). Pas de vérité terrain enquête — limite assumée.

**Livrable de l’axe :** comparatif briques + protocole d’évaluation.

---

## Axe 9 — Interopérabilité et intégration au SI

**Constat.** Pas d’API métier préexistante, pas d’annuaire d’entreprise, pas de SSO. L’intégration, c’est **ouvrir le prototype vers des données et des fonds publics**.

| Système externe | Mode | Stratégie de reprise |
|-----------------|------|----------------------|
| OpenStreetMap (PBF Geofabrik Madagascar) | Import batch osm2pgsql | Ré-import ; pas de CDC incremental au lot 1 |
| Nominatim (recherche de ville) | HTTP GET | Presets locaux si 502 / rate-limit |
| Fond de carte Carto Voyager (OSM) | Tuiles raster HTTPS | Attribution OSM + CARTO ; repli visuel si CDN down |
| Matrice OD officielle (futur) | Import table `mobility_flows` pré-agrégée k ≥ 5 | **Conçu pour** : le schéma ne stocke pas de `user_id` |
| GTFS | — | **Pas repris** : offre informelle Tana mal numérisée |
| MOBPRO / IRIS | — | **Pas repris** : référentiel français |

Authentification centralisée : **absente** (axe 10). Reprise des données « existantes » = OSM + seed, pas une migration d’un entrepôt interne.

**Livrable de l’axe :** schéma d’intégration ci-dessus.

---

## Axe 10 — Sécurité et conformité

Référentiel : **OWASP Top 10:2025** (A01 contrôle d’accès cassé, A02 mauvaise config, A03 supply chain, A05 injection, A07 auth, A09 journalisation).

| Risque OWASP 2025 | Exposition du prototype | Mesure lot 1 | Écart / repli |
|-------------------|-------------------------|--------------|---------------|
| A01 Broken Access Control | API ouverte sur le LAN | Démo **réseau contrôlé** ; pas d’Internet | JWT + RBAC en prod réelle |
| A02 Misconfiguration | Swagger exposé | `APP_ENV=production` → `/docs` off ; CORS **sans** `*` | — |
| A03 Supply chain | Images Docker + pip | Versions pinnées (`requirements.txt`) ; scan CVE reporté | `pip-audit` en CI future |
| A05 Injection | Requêtes spatiales | SQL `text()` + paramètres nommés ; pas de concat |
| A07 Auth failures | Pas d’auth | Accepté en démo ; **bloquant** hors localhost | Backlog JWT |
| A09 Logging | Accès OD | Logs d’accès **sans** dump des couplets nominatifs | — |

Secrets : variables `DB_*`, `.env` gitignored. Headers nginx (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`). Méthodes CORS limitées à GET/OPTIONS.

**Habilitations lot 1.** Un seul rôle implicite : lecteur. Matrice prod cible : urbaniste (lecture) / admin (seed, villes) — non implémentée.

**Livrable de l’axe :** checklist `docs/securite-rgpd.md` (preuve projet).

---

## Axe 11 — Performance et passage à l’échelle

| Opération | Seuil acceptable (décideur devant la carte) | Mitigation réelle |
|-----------|---------------------------------------------|-------------------|
| Couches OSM bbox | < 2 s | Index gist / `&&`, LIMIT, zoom ≥ 11, debounce 450 ms |
| Search lieu | < 500 ms | `ILIKE` + LIMIT 20 |
| Route A→B | < 3 s | Dijkstra sur **sous-graphe**, pas tout Madagascar |
| OD / M2 / M6 | < 2 s | n zones petit, agrégats SQL |
| Carte tuiles | Core Web Vitals secondaires (app interne) | Raster 256 px, pas un site marketing |

**Si la charge × 10** (plusieurs villes, milliers d’IRIS) : le goulot probable est le **GeoJSON bâtiments** au zoom trop faible, puis Dijkstra. Repli : MVT, cache, jobs async. **Non implémenté** — risque résiduel accepté (prototype, pas SaaS).

**Connexion dégradée.** Tuiles Carto et Nominatim souffrent. L’analytique (zones OD) tient si l’API locale tourne.

Tests de charge JMeter/k6 : **non faits** (88 j). Protocole retenu : smoke fonctionnel reproductible (`smoke_mvp_qa.py`), pas un rapport 10 000 VU.

**Livrable de l’axe :** exigences chiffrées + mitigation ; protocole de charge reporté.

---

## Axe 12 — Qualité logicielle et stratégie de test

Référentiel ISO/IEC 25010 (aptitude fonctionnelle, fiabilité, maintenabilité, sécurité) — utilisé comme **checklist**, pas comme certification.

| Type de test | Lot 1 | Couverture réaliste |
|--------------|-------|---------------------|
| Smoke API | **Oui** (`smoke_mvp_qa.py`, 19 puis 24 cas selon millésime) | Tous les Must exposés |
| Unitaire | Ponctuel | Pas d’objectif 80 % : trop coûteux vs démo |
| E2E navigateur | Checklist manuelle runbook | Pas Cypress/Playwright (temps) |
| Analyse statique | ESLint front | Pas SonarQube |
| Revue | Auto-revue + tuteur | Pas de CI GitHub Actions industrielle |

**Documentation de reprise :** `README.md`, `docs/runbook.md`, `docs/methodes.md`, `docs/architecture.md`, `.env.example`. C’est le vrai livrable qualité d’un stage solo : **pouvoir relancer sans le stagiaire**.

**Livrable de l’axe :** stratégie de test ci-dessus.

---

## Axe 13 — Déploiement et exploitation

```text
Git → build images Docker → compose up
        ├─ db (volume persisté mobilite_postgis_data)
        ├─ backend uvicorn :8000
        └─ frontend nginx :8080
Seed OD → smoke → démo
```

| Sujet | Choix | Écarté |
|-------|-------|--------|
| Hébergement | **On-premise / laptop** Docker Desktop | AWS/GCP/Azure (coût USD, carte bancaire, latence) |
| CI/CD | Scripts manuels documentés | GitHub Actions + prod auto (pas d’environnement cible) |
| Sauvegarde | `scripts/backup_postgis.ps1` / `.sh` → `backups/` gitignored | S3, PITR |
| Restauration | Recréer le volume + ré-import OSM + seed | Testée comme **procédure écrite** ; un restore fire-drill complet dépend de la machine |
| Supervision | `docker compose ps` + `/health` | Prometheus (sur-ingénierie) |
| Rollback | Redeploy image précédente / git checkout | Blue-green |

Qui exploite après le stage ? Le tuteur ou le prochain étudiant, **localement**. Ce n’est pas un service 24/7.

**Livrable de l’axe :** chaîne Compose + backup documenté.

---

# Bloc D — Contraintes de réalisation et de valeur

## Axe 14 — Contexte local et faisabilité terrain

Antananarivo : congestion, urbanisation rapide, **transport largement informel** (taxis-be) peu présent en GTFS. Une copie d’un pipeline Île-de-France (IRIS + MOBPRO + GTFS RATP) **ne se déploie pas**. OSM est la seule base cartographique libre suffisamment dense pour un prototype.

**Connectivité et électricité.** Coupures et débit irrégulier. Conséquences de conception :

| Contrainte locale | Choix induit |
|-------------------|--------------|
| Facture API Google Maps / Mapbox en devises | Fond **OSM + Carto CDN** ; pas de clé payante obligatoire |
| Cloud USD/EUR | **Pas de cloud** au lot 1 |
| Internet intermittent | Démo **entièrement locale** une fois images + OSM importés ; Nominatim / tuiles = dépendance résiduelle |
| PC de bureau décideur, pas smartphone grand public | SPA desktop, pas d’app Flutter |
| Compétences Python/SQL plus fréquentes qu’ArcPy | Stack retenue (axe 6) |
| Maintenance « sur place » | Compose + docs FR, pas un cluster EKS |

**Offline-first complet** (tuiles empaquetées, service worker) : non livré. C’est un **écart** par rapport à un idéal axe 14. Le repli concret est : copier le dossier Docker + dump PostGIS sur une clé, lancer hors-ligne **sauf** fond raster Carto (fond gris acceptable en soutenance si le CDN tombe — plan B captures).

**Livrable de l’axe :** contraintes de conception (tableau).

---

## Axe 15 — Conduite de projet et organisation du stage

| Élément | Retenu | Écarté | Motif |
|---------|--------|--------|-------|
| Cycle | **Itératif type Kanban / lots Must** (pas un Scrum 8 personnes) | Scrum cérémonial complet | 1 stagiaire : daily avec soi-même = théâtre |
| Priorisation | **MoSCoW** (Must M1/M2/M5/M6) | Cycle en V figé 88 j | Le CDC trop large (M3/M4) devait pouvoir **rétrécir** |
| Modélisation | Schémas C4 légers, tables SQL, GeoJSON | Merise complet, 40 diagrammes UML | Rapport lisible, pas un dossier Afnor |
| Versions | **Git** | Copies datées | Reprise |
| Jalons | Cadrage → socle carte → OD/KPI → M2/M6 → Docker/sécu → docs soutenance | « Tout le CDC » | Temps manquant → M3/M4 **écrits** au rapport, pas codés |
| Validation tuteur | Démo carte + smoke | Spécification gelée J1 | Preuve dans `docs/qa-rapport.md` |

Périmètre minimal viable identifié dès le cadrage : **carte + desire lines + labels + indice + démo reproductible**. C’est exactement ce que la grille demande : « que livrer si le temps manque ? »

**Livrable de l’axe :** démarche + MVP.

---

## Axe 16 — Coûts, licences et soutenabilité

**Coût total de possession sur 3 ans (ordre de grandeur, prototype interne).**

| Poste | Lot 1 | Si l’on avait choisi l’alternative |
|-------|-------|-------------------------------------|
| Licences logicielles | ~ 0 € (stack libre + OSM) | ArcGIS / Google Maps : centaines à milliers €/an |
| Cloud | 0 € | 20–200 €/mois selon VM + bande passante |
| Fond de carte | 0 € (Carto public tiles — usage raisonnable ; pas un SLA) | Mapbox : quota puis facture |
| Main d’œuvre reprise | Quelques jours/an (ré-import OSM, seed) | Idem + admin licences |
| Données | OSM (temps d’import) | Enquête OD : plusieurs mois et un budget collectivité |

**Propriété intellectuelle.** Code du stage : selon convention de stage (à rappeler dans le mémoire administratif). Données OSM : ODbL. **Ne pas publier** de dump qui mélangerait un jour des données internes du commanditaire.

**Qui finance la maintenance ?** Personne n’a budgété un SaaS. D’où l’obsession du **zéro abonnement**.

**Livrable de l’axe :** TCO qualitatif ci-dessus (pas de devis fournisseur signé : N/A).

---

## Axe 17 — Protection des données et cadre juridique

| Question | Réponse MVP (1er septembre 2026) |
|----------|----------------------------------|
| Données personnelles traitées ? | **Non** : OSM public + volumes **synthétiques** agrégés |
| Base légale | N/A tant que pas de personnes identifiables |
| Minimisation | Schéma sans `user_id` / `trip_id` / GPS |
| k-anonymité | Plancher API k = 5 (`privacy.py`) ; défaut UI = 20 |
| Localisation des données | Laptop / Docker local — **pas de cloud extra-UE imposé** |
| Durée de conservation | Seed reproductible ; pas d’historique usager |
| Confidentialité commanditaire | Pas de secret d’entreprise dans le repo ; mot de passe DB hors Git |

**Si demain une OD réelle arrive.** N’importer que des comptes **pré-agrégés** k ≥ 5. Jamais de traces individuelles. AIPD / registre à faire **avant** l’import (loi 2014-038, et RGPD si rattachement UE).

**Quoi publier dans le mémoire.** Captures d’écran de **données synthétiques** ou OSM ; pas de fichier nominatif. Formules et architecture : publiables.

Textes : loi n° 2014-038 ; lignes directrices CNIL géolocalisation ; RGPD art. 5 (minimisation) comme **boussole** même hors champ strict.

**Livrable de l’axe :** cadre juridique + règles de publication du mémoire.

---

## Axe 18 — Sobriété numérique et écoconception *(optionnel)*

Traité brièvement : le sujet s’y prête (carte web) mais n’est pas le cœur du CDC.

Principes retenus, alignés RGESN / GreenIT (esprit, pas un audit) :

- **Ne pas charger** le bâti OSM avant le zoom 11 ;
- LIMIT serveur plutôt que tout envoyer au navigateur ;
- pas de vidéo de fond, pas de framework CSS énorme ;
- Dijkstra borné spatialement (CPU) ;
- pas de cluster GPU / modèle de deep learning.

Indicateur suivi : temps de réponse et taille de FeatureCollection (LIMIT), pas de kgCO₂ mesuré. Matériel ancien : SPA React 19 peut être lourde sur un PC 2015 — **écart** ; le public cible a un poste de travail correct.

**Livrable de l’axe :** principes + non-mesuré assumé.

---

# Bloc E — Synthèse et décision

## Axe 19 — Synthèse comparative et justification des choix

C’est l’axe que le jury note le plus sévèrement. Les choix ne sont pas « les technologies à la mode », ils relient **besoin du commanditaire**, **88 jours**, **Madagascar**, et **reprise**.

### Matrice de décision

| Décision | Retenu | Principal concurrent écarté | Critère décisif | Risque résiduel | Plan de repli |
|----------|--------|-----------------------------|-----------------|-----------------|---------------|
| Positionnement produit | Aide à la décision agrégée | App GPS / trafic live | CDC + personas élu/urbaniste | On peut être comparé à Google Maps à l’oral | Phrase d’ouverture : « ce n’est pas un GPS » |
| Faire vs acheter | Prototype dédié | ArcGIS / Carto SaaS | Coût, Madagascar, pédagogie, règles M2/M6 | Moins « beau » qu’un SaaS | QGIS en complément expert |
| Architecture | 3 conteneurs, monolithe modulaire | Microservices / Kafka | 1 personne, 88 j | Montée en charge limitée | MVT / split plus tard |
| Backend | FastAPI | Django / Node / Spring | CDC Python, OpenAPI, geo | Écosystème JS full-stack non unifié | — |
| Carte | MapLibre + tuiles Carto OSM | Mapbox payant / Leaflet seul | Licence + perf + pas de token | CDN tuiles = Internet | Captures ; fond gris |
| Données OD | Gravité OSM + disclaimer | MOBPRO / traces GPS | Disponibilité Tana + RGPD | Volumes **non opérationnels** | Brancher une matrice pré-agrégée |
| M2 | Heuristiques médianes (+ clustering spatial simple) | DBSCAN sur GPS, HDBSCAN | Lisibilité élu, n petit | Seuils discutables | Recaler les seuils avec un urbaniste |
| M6 | Indice intra-zone | 2SFCA | Pas de temps/emplois réels | Ignore l’accès aux zones voisines | 2SFCA en perspective |
| M3 / M4 | Reportés | Tout coder | MoSCoW | CDC incomplet vis-à-vis de la vision longue | Écrits au rapport |
| Auth | Reportée | JWT J1 | Temps + démo locale | A01 OWASP si exposition Internet | Ne pas ouvrir les ports |
| Hébergement | Docker local | Cloud | Devises, reprise, axe 14 | Pas de SLA | Clé USB + Compose |
| Qualité | Smoke + docs | Couverture 80 % + k6 | Budget temps | Régressions UI | Checklist J-1 |

### Fil conducteur (à dire en une minute)

> On n’a pas choisi PostGIS « parce que c’est un SIG ». On l’a choisi parce que le commanditaire veut des **requêtes spatiales et un plus court chemin** sans moteur externe, que l’équipe de reprise sait du SQL, et qu’on ne paie pas de licence. On n’a pas choisi un modèle gravitaire « parce que Wilson 1971 est célèbre ». On l’a choisi parce qu’**aucune enquête OD** n’était disponible à Antananarivo dans le délai, et que le schéma reste prêt pour une vraie matrice agrégée. On n’a pas écarté DBSCAN par ignorance : on n’a **pas de traces GPS** à clusteriser. On n’a pas écarté le cloud par idéologie : un abonnement en devises **tuerait** la soutenabilité après le stage.

### Risques acceptés en connaissance de cause

1. Fidélité des volumes OD (proxy).
2. Absence d’authentification.
3. Dépendance tuiles / Nominatim au réseau.
4. OSM incomplet (bus informels).
5. Indice M6 intra-zone seulement.
6. Pas de tests de charge instrumentés.

Aucun de ces risques n’est caché : ils sont dans l’UI (`synthetic`, notes M6) et dans `docs/methodes.md`.

---

## Conclusion du chapitre

L’état de l’art d’un stage M2 n’est pas une collection de définitions *smart city*. C’est une **veille datée** qui aboutit à un système **maintenable à Madagascar**, **conforme à un CDC trop large qu’on a volontairement coupé**, et **honnête** sur ce que les chiffres représentent.

Les travaux personnels (implémentation, démo, mesures QA, limites) commencent **après** ce chapitre — et doivent en occuper la plus grande part du mémoire.

---

# Bibliographie et webographie

Dates de consultation des URL : **1er septembre 2026**, sauf mention.

1. *Grille d’analyse pour l’état de l’art — Projet informatique de stage, Master 2 professionnel*. Document de consignes (20 axes). Consulté le 1er septembre 2026.
2. Spécification du stage *Mobilité urbaine* et *Vision produit Mobilité Urbaine* (cadrage interne). 2026.
3. OpenStreetMap Foundation. *Open Database License (ODbL) 1.0*. https://opendatacommons.org/licenses/odbl/ — licence des données cartographiques utilisées.
4. FastAPI. *Documentation*. https://fastapi.tiangolo.com/ — éditeur ; biais : promotion du framework.
5. PostgreSQL Global Development Group / PostGIS. *PostGIS documentation*. https://postgis.net/documentation/
6. pgRouting Community. *pgRouting documentation* (Dijkstra). https://docs.pgrouting.org/
7. MapLibre. *MapLibre GL JS*. https://maplibre.org/ — fork libre ; contexte : Mapbox GL JS n’est plus 100 % open source depuis 2020 (biais historique Mapbox).
8. osm2pgsql. *Documentation*. https://osm2pgsql.org/
9. Geofabrik. *Download server* (extracts OSM Madagascar). https://download.geofabrik.de/
10. OpenStreetMap Nominatim. *Usage policy*. https://operations.osmfoundation.org/policies/nominatim/
11. OWASP. *OWASP Top 10:2025*. https://owasp.org/Top10/2025/ (publication novembre 2025).
12. CNIL. Guides et fiches sur la géolocalisation et le RGPD. https://www.cnil.fr/ — autorité ; pas un éditeur logiciel.
13. République de Madagascar. *Loi n° 2014-038* relative à la protection des données à caractère personnel ; textes CMIL.
14. Règlement (UE) 2016/679 (RGPD), notamment art. 5 (minimisation).
15. Wilson, A. G. (1971). *A family of spatial interaction models, and associated developments*. Environment and Planning. — **principe** du modèle gravitaire ; source ancienne, citée comme fondement, pas comme « état 2026 ».
16. Luo, W. & Wang, F. (2003). *Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region*. Environment and Planning B. — 2SFCA ; **écarté** au lot 1.
17. Sweeney, L. (2002). *k-anonymity: a model for protecting privacy*. International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems.
18. Ester, M., Kriegel, H.-P., Sander, J. & Xu, X. (1996). *A density-based algorithm for discovering clusters in large spatial databases with noise* (DBSCAN). KDD. — **écarté** (pas de traces GPS).
19. Docker Inc. *Docker Compose documentation*. https://docs.docker.com/compose/ — éditeur.
20. W3C. *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/
21. ISO/IEC 25010:2023. *Systems and software Quality Requirements and Evaluation (SQuaRE)*.
22. ThoughtWorks. *Technology Radar* (éditions récentes : microservices, observabilité). https://www.thoughtworks.com/radar — opinion de cabinet, pas une norme.
23. Stack Overflow. *Developer Survey* (éditions 2024–2025). https://survey.stackoverflow.co/ — auto-déclaratif.
24. Direction interministérielle du numérique (France). *Référentiel général d’écoconception de services numériques (RGESN)*. https://ecoresponsable.numerique.gouv.fr/
25. CARTO. *Basemap tiles* (Voyager). https://carto.com/ — **biais commercial** ; utilisé uniquement comme fond raster OSM, pas comme SaaS analytics.

**Sources projet (preuves, pas « littérature ») :** `docs/architecture.md`, `docs/methodes.md`, `docs/data-model.md`, `docs/securite-rgpd.md`, `docs/exigences-mvp.md`, `docs/ux-mvp.md`, `docs/qa-rapport.md`, `docs/runbook.md`.
