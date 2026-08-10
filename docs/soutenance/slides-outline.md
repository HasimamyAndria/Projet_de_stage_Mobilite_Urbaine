# Outline slides — Soutenance Mobilité Urbaine

12 slides max. Une idée par slide. Pas de wall of text.

> Remplir les crochets avant export PowerPoint / Google Slides / Beamer.

---

## 1. Titre

- **Titre :** Plateforme d’aide à la décision — Mobilité urbaine & équilibre emploi-habitat
- **Sous-titre :** Stage M2 — MVP cartographique et analytique
- `[Étudiant]` — `[Organisme / entreprise]` — `[Tuteur entreprise]` — `[Tuteur académique]`
- Date soutenance

## 2. Problématique

- Déséquilibres emploi / habitat → pression sur les déplacements
- Décideurs : besoin d’une **vue synthétique** spatiale
- Contrainte : données agrégées, pas de surveillance individuelle

## 3. Vision produit (1 phrase)

> « Aider urbanistes et élus à localiser flux majeurs et déséquilibres territoriaux pour prioriser diagnostics et investissements. »

## 4. Périmètre MVP vs cible

| Must livré | Reporté (Should) |
|------------|------------------|
| M1 Flux / carte / desire lines | M3 Recommandations |
| M2 Points clés (heuristiques) | M4 Simulation what-if |
| M5 KPI / dashboard | Multi-tenant, export PPT |
| M6 Indice emploi-habitat (proxy) | Clustering ML avancé |
| Socle OSM + routing | Auth complète / SaaS |

## 5. Architecture (C4 simple)

```text
[ Urbaniste / Élu ]
        │
   React + MapLibre
        │  GeoJSON / HTTP
     FastAPI
        │
  PostGIS + pgRouting
   (OSM + zones/flux OD)
```

## 6. Stack

| Couche | Techno |
|--------|--------|
| Front | React, MapLibre GL, axios |
| API | FastAPI, SQLAlchemy |
| Data | PostgreSQL / PostGIS, OSM, pgRouting |
| Run | Docker Compose, nginx |

## 7. Démo / captures

- Emplacement pour 2–3 captures : carte globale, KPI + desire lines, M6 coloré
- Mention : démo live prévue (sinon plan B)

## 8. Méthode analytique

- **M2 :** dortoir / pôle emploi / mixte + corridors = top volumes OD
- **M6 :** `eh_index = 1 − |J−P|/(J+P)` ∈ [0,1]
- **M1 :** desire lines ≠ itinéraire routier
- Limite assumée : proxies synthétiques en démo

## 9. Qualité & conformité

- QA smoke API : **19/19 OK** (`docs/qa-rapport.md`)
- RGPD : agrégation zone→zone, **k-anonymité ≥ 5**, pas d’IDs individuels
- Sécu MVP : secrets en `.env`, CORS restrictif, Swagger off en prod (`docs/securite-rgpd.md`)

## 10. Difficultés & apprentissages

- Graphe routier fragmenté → route démo sur composante connectée + Dijkstra bbox
- Perf spatiale → bbox + LIMIT
- Scope : résister à la tentation M3/M4 non Must

## 11. Perspectives

- Brancher OD / population / emplois **réels** (pré-agrégés)
- M6 → accessibilité type 2SFCA / isochrones
- M2 → clustering (K-means / DBSCAN) si validation métier
- M3/M4 + auth JWT pour une vraie prod

## 12. Merci / Q&R

- Contact / lien repo (si autorisé)
- « Questions ? »

---

## Notes design slides

- Une phrase max sous le titre
- Schéma architecture : 4 boîtes max
- Chiffres réels uniquement (19/19, k=5, eh_index exemple ~0.78 avg QA)

## Export prêt à projeter

| Fichier | Usage |
|---------|--------|
| [`slides.html`](slides.html) | Diaporama navigateur (← →, `F` plein écran, `P` → PDF) |
| [`repetition-demo.md`](repetition-demo.md) | Fiche chrono 1 page pour répéter la démo |

Ouvrir :

```powershell
start docs\soutenance\slides.html
```

