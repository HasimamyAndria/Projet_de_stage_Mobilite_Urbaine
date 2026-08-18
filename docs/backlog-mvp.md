# Backlog MVP — Mobilité Urbaine (stage)

**Date :** 2026-08-18  
**Entrée :** `docs/exigences-mvp.md`  
**Skill :** `03-po-backlog-mvp`  
**Lot 1 Must :** **CLOS** — smoke QA 24/24 (`docs/qa-rapport.md`, 2026-08-18)

## Definition of Ready

US Must prête si : persona claire, dépendances data/API connues, critère Given/When/Then, démontrable en soutenance < 2 min.

## Definition of Done (projet)

- [x] Code présent dans le repo
- [x] Endpoint ou UI testable
- [x] Cas erreur / loading géré
- [x] Doc courte ou `docs/methodes.md` si analytique
- [x] Démontrable en soutenance < 2 min
- [x] Smoke QA rejoué en local (2026-08-18, 24/24, clustering M2 + villes)

## Epics

| Epic | Module | Priorité | Statut lot 1 |
|------|--------|----------|--------------|
| E1 Socle carte OSM + search | M1 | Must | Fait |
| E2 Route A→B pgRouting | Socle | Must | Fait (API + UI démo / clic) |
| E3 Desire lines + heatmap | M1 | Must | Fait |
| E4 KPI M5 | M5 | Must | Fait |
| E5 Points clés + clustering M2 | M2 | Must | Fait |
| E6 Indice M6 | M6 | Must | Fait |
| E7 Multi-villes | Socle | Must | Fait (OSM requis) |
| E8 Docker / sécu démo | — | Must | Fait |
| E9 Reco M3 | M3 | Should | Reporté |
| E10 Simulation M4 | M4 | Should | Reporté |

## Ordre de construction (rappel)

1. Socle data + carte OSM  
2. Search + route  
3. KPI M5  
4. Zones clés M2 (labels + clustering)  
5. Indice M6  
6. Polish UX stage (toggles, fiche zone, menu = modules livrés)  
7. M3/M4 seulement si marge — **non ouvert tant que Must ouverts**

---

### US-010 — Couches OSM par bbox
**En tant que** urbaniste  
**Je veux** voir routes, bâtiments, arrêts et lignes de bus  
**Afin de** lire le territoire sans tout charger

**Priorité** : Must · **Epic** : E1 · **Dépendances** : PostGIS `planet_osm_*`

**Acceptance**
- Given une bbox urbaine et un zoom ≥ 11
- When la carte s’arrête de bouger
- Then les couches OSM se chargent en GeoJSON avec LIMIT

**Statut :** Done

---

### US-020 — Search lieu
**En tant que** urbaniste  
**Je veux** rechercher un nom de lieu OSM  
**Afin de** recentrer la vue

**Priorité** : Must · **Epic** : E1

**Acceptance**
- Given une requête non vide
- When je valide la recherche
- Then la carte vole vers le lieu choisi ; requête vide documentée (`[]`)

**Statut :** Done

---

### US-030 — Itinéraire A→B
**En tant que** urbaniste  
**Je veux** tracer un chemin réseau entre deux points  
**Afin de** distinguer graphe routier et desire lines

**Priorité** : Must · **Epic** : E2 · **Dépendances** : `roads_network`, pgRouting

**Acceptance**
- Given les points démo connectés (QA)
- When je lance « Itinéraire démo » ou je clique A puis B
- Then une polyligne s’affiche **ou** un message « pas de chemin »
- And le toggle « Route A→B » masque la couche

**Statut :** Done

---

### US-040 — Desire lines OD
**En tant que** élu  
**Je veux** voir les principaux flux zone→zone  
**Afin de** prioriser les corridors

**Priorité** : Must · **Epic** : E3

**Acceptance**
- Given un seed OD
- When j’ouvre la carte
- Then les arcs OD et la heatmap sont visibles, volumes ≥ k, disclaimer synthétique / gravitaire

**Statut :** Done

---

### US-050 — KPI M5
**En tant que** élu  
**Je veux** une synthèse chiffrée sans ouvrir la console  
**Afin de** parler volumes et top OD

**Priorité** : Must · **Epic** : E4

**Acceptance**
- Given l’API `/api/od/summary`
- When le panneau charge
- Then zones, flux, volume, top 5 ; si API down, message d’erreur

**Statut :** Done

---

### US-060 — Labels zones + corridors M2
**En tant que** urbaniste  
**Je veux** distinguer dortoirs, pôles d’emploi et corridors  
**Afin de** cibler le diagnostic

**Priorité** : Must · **Epic** : E5

**Acceptance**
- Given des zones peuplées
- When j’active « Zones clés »
- Then couleurs par label + top corridors ; règles dans l’API / méthodes

**Statut :** Done (toggle « Zones clés (M2) »)

---

### US-065 — Clustering K-means M2
**En tant que** urbaniste  
**Je veux** un regroupement spatial des zones  
**Afin de** voir des grappes territoriales au-delà des labels

**Priorité** : Must · **Epic** : E5

**Acceptance**
- Given n≥2 zones
- When `/api/keypoints` répond
- Then chaque zone a `cluster_id`, k et silhouette (ou N/A) documentés, seed fixe

**Statut :** Done

---

### US-070 — Indice emploi-habitat M6
**En tant que** urbaniste  
**Je veux** colorer les zones selon l’équilibre emplois / habitat  
**Afin de** objectiver les déséquilibres intra-zone

**Priorité** : Must · **Epic** : E6

**Acceptance**
- Given proxies OSM
- When j’active l’indice M6
- Then fill rouge→vert, scores [0,1], limites « pas 2SFCA » visibles

**Statut :** Done

---

### US-080 — Fiche zone au clic
**En tant que** urbaniste  
**Je veux** inspecter une zone  
**Afin de** relier carte et KPI

**Priorité** : Must · **Epic** : E5/E6

**Acceptance**
- Given une couche zone visible (M2 ou M6)
- When je clique une zone
- Then une fiche affiche nom, pop/emplois, label, cluster, indice si connu

**Statut :** Done

---

### US-090 — Menu = modules livrés
**En tant que** élu  
**Je veux** une navigation qui correspond au lot 1  
**Afin de** ne pas croire que Simulation / Reco sont cassés

**Priorité** : Must · **Epic** : polish

**Acceptance**
- Given l’app ouverte
- When je parcours le menu
- Then seuls Carte, Flux OD, Zones clés, Indicateurs sont cliquables et changent la vue (couches)
- And M3/M4 n’apparaissent pas comme fonctionnalités mortes

**Statut :** Done

---

### US-100 — Ville + OSM manquant
**En tant que** démo  
**Je veux** un message si l’extract OSM n’est pas là  
**Afin de** ne pas montrer une carte analytique silencieuse

**Priorité** : Must · **Epic** : E7

**Acceptance**
- Given une bbox sans `planet_osm_*`
- When j’active la ville
- Then message « OSM à importer » (déjà partiel via `osm_ready`)

**Statut :** Done

---

### US-110 — Reco M3 / simulation M4
**Priorité** : Should · **Statut :** Reporté — **Must lot 1 clos** (QA 2026-08-18). Ouvrir seulement si marge avant soutenance.

## Prochaine story

Aucune US **Must** ouverte. Prochaine action : **soutenance (skill 13)** — rejouer le parcours clic J-1. M3/M4 seulement si marge.

## Risques de scope

- Sur-promettre M3/M4 dans l’UI.
- Ajouter sklearn / jobs lourds alors que n zones est petit (K-means pur Python).
- OD « réelle » : hors lot 1, disclaimer obligatoire.
