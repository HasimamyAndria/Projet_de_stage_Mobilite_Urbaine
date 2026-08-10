# Plan oral — Soutenance stage Mobilité Urbaine

**Durée cible :** 12–15 min (+ Q&R)  
**Message central :** une plateforme d’**aide à la décision** (pas de pilotage trafic temps réel) pour visualiser flux OD, points clés et équilibre emploi-habitat sur un socle OSM/PostGIS.

> Remplacer `[Étudiant]`, `[Tuteur]`, `[Organisme]` avant le jour J.

---

## Timing (12–15 min)

| Min | Bloc | Contenu à dire | Support |
|-----|------|----------------|---------|
| 0–1 | Accroche | Contexte métropole (ex. Antananarivo) : déséquilibre emploi-habitat → trajets longs, saturation. Besoin d’un outil de **diagnostic territorial**. | Slide 1–2 |
| 1–3 | Objectifs & scope | Objectif stage : livrer un **MVP Must** (M1 carte/flux, M2 points clés, M5 KPI, M6 indice). Hors scope assumé : M3 reco, M4 what-if, multi-tenant. | Slide 3–4 |
| 3–5 | Architecture | Navigateur MapLibre → FastAPI GeoJSON → PostGIS (+ pgRouting). Données : OSM + zones/flux OD synthétiques pour la démo. | Slide 5–6 |
| **5–10** | **Démo live** | Suivre `script-demo.md` (~4 min). Une décision métier en fin de démo. | App live / plan B captures |
| 10–12 | Méthodes + RGPD | M2 heuristiques (dortoir / emploi / corridor). M6 formule `eh_index`. Agrégation zone→zone + **k≥5**. | Slide 8–9 |
| 12–14 | Résultats & limites | QA **19/19**. Limites : OD synthétiques, M6 = proxy intra-zone (≠ 2SFCA), corridors ≠ capacité route. Perspectives M3/M4. | Slide 10–11 |
| 14–15 | Conclusion | Livrable démo-ready (Docker + runbook). Ouverture Q&R. | Slide 12 |

---

## Structure narrative (à mémoriser)

```text
Problème → Périmètre MVP → Architecture → Démo → Méthode → Limites → Suite
```

**Phrase d’ouverture (30 s) :**  
« Le stage porte sur une plateforme d’aide à la décision pour la mobilité urbaine : comprendre où se situent les déséquilibres emploi-habitat et les principaux flux, à partir de données spatiales agrégées, sans surveillance individuelle. »

**Phrase de clôture (20 s) :**  
« Le MVP Must est opérationnel en démo : carte, KPI, points clés, indice emploi-habitat, avec garde-fous RGPD. Les modules M3/M4 restent des perspectives documentées, pas des promesses livrées. »

---

## Ce qu’il ne faut pas dire

- « On fait du temps réel / du tracking GPS. »
- « L’indice M6 mesure l’accessibilité complète. »
- « Les volumes OD sont des données terrain réelles » (ce sont des **synthétiques** gravitaire).
- « K-means / DBSCAN sont déjà en prod » (heuristiques M2 uniquement).

---

## Enchaînement avec les autres fichiers

| Avant | Pendant | Après |
|-------|---------|-------|
| `checklist-j1.md` | `script-demo.md` + ce plan | `questions-reponses.md` |
| Captures plan B | `slides-outline.md` | — |
