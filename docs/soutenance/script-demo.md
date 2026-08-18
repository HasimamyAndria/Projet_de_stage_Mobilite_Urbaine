# Script démo live — Mobilité Urbaine

**Durée filmable :** < 4 min  
**URL :** http://localhost:8080 (Docker) ou http://localhost:5173 (Vite)  
**Prérequis :** `docker compose up` + seed OD + smoke OK (voir `checklist-j1.md`)

---

## Chrono (parler à voix haute)

| T | Action UI | Texte suggéré |
|---|-----------|---------------|
| 0:00–0:30 | Ouvrir la carte (Antananarivo déjà centré) | « Voici la carte décisionnelle. Fond MapLibre, données OSM et couches analytiques chargées au démarrage. » |
| 0:30–1:00 | Zoomer ≥ 11 si besoin ; montrer routes / bus | « Les couches OSM (routes, bâtiments, arrêts, lignes) se chargent par **bbox** pour rester performantes. » |
| 1:00–1:30 | Search : taper `Antananarivo` (ou un lieu connu) | « La recherche recentre la vue — parcours urbaniste classique. » |
| 1:30–2:00 | Bouton **Itinéraire démo** | « Une route **réseau** via pgRouting — distincte des desire lines OD. On peut aussi cliquer A puis B. » |
| 2:00–2:40 | Menu **Flux OD** + panneau **KPI** (M5) | « Les flux OD agrégés zone→zone : volumes, top origines-destinations. Volumes **estimés** (gravité), agrégés. » |
| 2:40–3:20 | Menu **Zones clés** : clic une zone, puis **Indicateurs** (M6) | « Labels dortoir / pôle, clustering K-means, indice emploi-habitat rouge→vert. » |
| 3:20–3:50 | **Décision métier** (obligatoire) | Voir phrase ci-dessous. |
| 3:50–4:00 | Recentrer / pause | « Fin de la démo technique — je reviens sur la méthode et les limites. » |

---

## Une décision métier (à dire à 3:20)

Choisir **une** phrase selon ce qui est visible à l’écran (adapter aux noms de zones du seed) :

> « Sur cette zone [nom / couleur rouge], on voit un surplus d’habitat par rapport aux emplois, et un corridor OD fort vers un pôle emploi. Pour un urbaniste, cela oriente la discussion vers : densifier l’emploi à proximité, ou renforcer l’offre de transport sur ce couple O→D — **pas** vers un contrôle individuel des trajets. »

Variante élu :

> « En une vue, un élu voit où concentrer l’attention budgétaire : corridors saturés (proxy volume) et zones déséquilibrées, avant toute étude fine. »

---

## Points route démo (référence code)

Validés QA (composante connectée du graphe) — bouton **Itinéraire démo** :

```text
A : 47.52928,  -18.903276
B : 47.5160582, -18.8680788
```

(`RouteLayer.ts` / `DEMO_ROUTE` — ne pas improviser d’autres points en live sans test.)

---

## Plan B (si API / DB tombe)

1. Garder 4–6 **captures d’écran** préparées J-1 (carte + KPI + M6 + route + desire lines).
2. Dire calmement : « Instance locale indisponible ; je poursuis sur les captures validées en QA (19/19). »
3. Montrer `docs/qa-rapport.md` / preuve smoke si demandé.
4. Ne **pas** debugger Docker devant le jury > 30 s.

---

## Répétition

- [ ] Chronométrer une fois à voix haute (< 4 min)
- [ ] Tester search + panneau KPI le matin J
- [ ] Vérifier que les desire lines et la couche M6 sont visibles sans zoomer au hasard
