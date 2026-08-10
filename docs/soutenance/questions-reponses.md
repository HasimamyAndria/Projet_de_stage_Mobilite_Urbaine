# Q&R jury — Anticipations

Réponses **courtes** (30–60 s). Chiffres / faits alignés sur le repo réel.

---

## Métier

**Pourquoi pas du temps réel / du trafic live ?**  
Le produit vise l’**aide à la décision** territoriale (diagnostic, priorisation), pas le pilotage opérationnel. Le temps réel change la stack (capteurs, latence, SLA) et sort du périmètre stage Must.

**Quelle valeur pour un élu ?**  
Une vue unique : où sont les gros flux OD, les zones dortoir vs pôles d’emploi, et les déséquilibres colorés (M6). Ça oriente le débat budgétaire avant une étude fine.

**Quelle valeur pour un urbaniste ?**  
Prioriser les zones à investiguer (M2) et croiser avec le réseau OSM / une route type (pgRouting), sans exporter de données individuelles.

**Pourquoi des desire lines et pas seulement le routing ?**  
Les desire lines montrent la **demande** O→D agrégée. Le routing montre un **chemin réseau** possible. Ce sont deux lectures complémentaires (M1 vs socle route).

---

## Data

**Quelles sources ?**  
OSM (voirie, bâti, bus) via PostGIS ; zones et flux OD de **démo synthétiques** (modèle gravitaire population × emplois / distance). Pas de MOBPRO réel dans le MVP.

**Biais si on branchait du MOBPRO / enquêtes ?**  
Sous-représentation de modes, maille administrative, date de millésime, secrets statistiques. D’où agrégation + seuil k avant exposition API.

**C’est quoi la k-anonymité ici ?**  
On n’expose pas de flux avec volume `< 5` (`K_ANONYMITY_MIN`). Défaut UI = 20. Pas d’identifiant trajet / usager dans l’API.

**Les volumes affichés sont-ils fiables opérationnellement ?**  
Non pour décider un budget seul : ce sont des **proxies démo**. Le pipeline (tables, API, carte) est prêt pour de l’OD pré-agrégé réel.

---

## Tech

**Pourquoi PostGIS plutôt qu’un fichier GeoJSON statique ?**  
Requêtes spatiales (bbox, indexes), jointures, vues OD, et **pgRouting** pour Dijkstra. Scalable vs tout charger côté navigateur.

**Pourquoi MapLibre ?**  
Rendu vectoriel performant, libre, adapté aux GeoJSON API ; pas de dépendance payante type Mapbox token pour le MVP.

**Comment gérez-vous la perf ?**  
Filtres **bbox** + **LIMIT** côté API ; couches OSM chargées seulement si zoom ≥ 11 ; Dijkstra sur **sous-graphe** autour de A/B (pas tout Madagascar).

**Pourquoi FastAPI ?**  
API typée rapide à exposer, docs OpenAPI en dev, bon fit SQLAlchemy/PostGIS pour un MVP geo.

---

## Analytics / « ML »

**Vous faites du clustering ?**  
Pas encore de K-means/DBSCAN en prod. M2 = **heuristiques métier** (seuils sur médianes population/emplois) + top corridors OD. Clustering = perspective si validation métier.

**Pourquoi pas K-means dès maintenant ?**  
Sans vérité terrain ni stabilité des clusters, on risque une « boîte noire ». Les règles lisibles sont préférables pour une soutenance décideur.

**L’indice M6, c’est un 2SFCA ?**  
Non. C’est un **proxy d’équilibre intra-zone** emplois vs population. Un 2SFCA mesurerait l’accès aux emplois via distances/temps — évolution documentée.

**Comment validez-vous M6 ?**  
Bornes QA `eh_index ∈ [0,1]` ; lecture relative (comparaison entre zones), pas une vérité absolue. Avg démo ~0.78 dans le rapport QA.

---

## Prod / sécu

**Comment déployer ?**  
`docker compose up --build` ; seed OD ; front :8080, API :8000. Runbook dans `docs/runbook.md`.

**Où sont les secrets ?**  
Variables `.env` (gitignored), modèle `.env.example`. Pas de password hardcodé dans l’API.

**Et l’auth ?**  
Absente du MVP : **démo contrôlée** (local/VPN). Prod réelle = JWT + TLS + CORS serré (backlog dans `docs/securite-rgpd.md`). Swagger désactivé si `APP_ENV=production`.

---

## Limites / scope

**Qu’est-ce qui n’est pas fiable ?**  
Volumes OD synthétiques ; corridors = proxy de volume, pas de capacité d’axe ; M6 ignore l’accès inter-zones ; graphe routier OSM peut être fragmenté.

**Pourquoi M3/M4 non livrés ?**  
Priorisation MoSCoW : Must d’abord (carte + analytics de base + qualité). M3/M4 demandent plus de data métier et de validation — explicitement hors MVP stage.

**Si le réseau tombe en démo ?**  
Plan B captures + rapport QA 19/19 — déjà prévu dans le script démo.

---

## Mini-checklist mentale avant Q&R

```text
[ ] OD = synthétique agrégé, k≥5
[ ] M6 = proxy équilibre, ≠ accessibilité
[ ] M2 = heuristiques, ≠ ML
[ ] Desire line ≠ route pgRouting
[ ] Auth = reportée, démo locale
```
