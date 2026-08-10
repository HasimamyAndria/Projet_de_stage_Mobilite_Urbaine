# Prompts d'enchaînement — Mobilité Urbaine

Copier-coller **un prompt à la fois**. Mentionner le skill au début (`@` ou nom exact).

---

## Phase 0 — Contexte

```text
Utilise le skill 01-project-context.
Analyse l'état actuel du repo (backend FastAPI, frontend MapLibre, PostGIS).
Donne-moi : ce qui est déjà livré, les gaps vs MVP stage (M1/M2/M5/M6), et la prochaine action concrète.
```

---

## Phase 1 — Business Analyst

```text
Utilise le skill 02-ba-vision-exigences.
À partir de specification_mobilite_urbaine-stage.pdf et Vision_Produit_Mobilite_Urbaine.pdf,
produis/mets à jour docs/exigences-mvp.md : vision courte, personas, EF Must/Should/Could,
règles métier RM-xx, hors-scope explicite pour le stage.
```

---

## Phase 2 — Product Owner

```text
Utilise le skill 03-po-backlog-mvp.
Transforme docs/exigences-mvp.md en backlog sprintable :
epics M1–M6, user stories INVEST, critères d'acceptance Given/When/Then,
priorisation MoSCoW, Definition of Done. Écris docs/backlog-mvp.md.
```

---

## Phase 3 — UX

```text
Utilise le skill 04-ux-carto-decision.
Conçois le parcours Urbaniste + Élu pour le MVP analytique (carte + KPI + zones clés).
Livrable : docs/ux-mvp.md (écrans, couches carte, états vides/erreurs, microcopy).
Pas de surcharge SaaS ; UI orientée décision.
```

---

## Phase 4 — Architecture

```text
Utilise le skill 05-architecture-systeme.
Propose l'architecture cible alignée sur le code existant (FastAPI + PostGIS + React/MapLibre).
Livrable : docs/architecture.md (C4 context/container, contrats API GeoJSON, flux data, limites perf).
```

---

## Phase 5 — Data / PostGIS

```text
Utilise le skill 06-data-postgis.
Audit le schéma actuel (planet_osm_*, roads_network, pgRouting).
Propose le modèle pour OD/IRIS/GTFS/indices MVP + scripts d'import.
Livrable : docs/data-model.md + scripts SQL/Python prêts à exécuter.
```

---

## Phase 6 — Backend

```text
Utilise le skill 07-backend-fastapi-geo.
Implémente/renforce les endpoints du sprint courant selon docs/architecture.md et le backlog.
Contraintes : GeoJSON FeatureCollection, bbox, LIMIT raisonnables, pas de secrets hardcodés,
routers propres, schemas Pydantic. Tests smoke sur chaque endpoint.
```

---

## Phase 7 — Frontend

```text
Utilise le skill 08-frontend-maplibre.
Implémente l'UI carte du sprint (couches, toggles, search, route, panneaux KPI)
selon docs/ux-mvp.md et les contrats API. Code TypeScript propre, états loading/error/empty.
```

---

## Phase 8 — Analytics (modules)

```text
Utilise le skill 09-analytics-modules.
Implémente le module analytique prioritaire du backlog (ex. clustering zones clés OU indice emploi-habitat).
Documente la méthode, les paramètres, les limites. Expose via API + couche carte.
```

---

## Phase 9 — QA

```text
Utilise le skill 10-qa-qualite.
Écris/exécute le plan de tests du MVP : API, SQL spatiaux, anonymisation, E2E carte.
Livrable : docs/qa-rapport.md avec résultats et bugs bloquants.
```

---

## Phase 10 — Production

```text
Utilise le skill 11-devops-production.
Prépare la mise en production du stage : Docker Compose, .env.example, README run,
healthchecks, backup PostGIS minimal. Pas de secrets dans le git.
```

---

## Phase 11 — Sécurité / RGPD

```text
Utilise le skill 12-securite-rgpd.
Audit sécu + conformité MVP : secrets, CORS, agrégation/k-anonymité, logs.
Livrable : docs/securite-rgpd.md + correctifs prioritaires.
```

---

## Phase 12 — Soutenance

```text
Utilise le skill 13-soutenance-stage.
Prépare une soutenance solide : plan 12–15 min, script de démo live, slides outline,
Q&R jury (tech + métier + limites), checklist matérielle. Livrable docs/soutenance/.
```

---

## Prompt multi-sprint (récurrent)

```text
Utilise 01-project-context puis 03-po-backlog-mvp.
Quelle est la prochaine user story Must non terminée ?
Implémente-la de bout en bout (data si besoin → API → UI → smoke test).
Termine par : statut, fichiers touchés, risque, next story.
```

## Prompt "je suis bloqué"

```text
Utilise 00-pipeline-stage + 01-project-context.
Voici mon blocage : <décrire>.
Dis-moi dans quelle phase je suis, quel skill appliquer, et les 3 actions concrètes pour débloquer.
```
