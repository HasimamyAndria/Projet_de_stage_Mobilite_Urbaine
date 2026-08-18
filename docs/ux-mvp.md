# UX MVP — Cartographie décisionnelle

**Date :** 2026-08-18  
**Skill :** `04-ux-carto-decision`  
**Alignement :** `frontend/src/components/Map/`

## Principes

1. Un job par vue : carte + un focus (flux, zones, indicateurs).
2. Carte full-bleed ; panneau KPI à droite (lecture élu).
3. Pas de pages vides ni de menus « bientôt » pour M3/M4.
4. Couches toggleables ; légende contextuelle.
5. États : loading, empty, error, OSM manquant.

## Sitemap lot 1

```text
MobilitySmart
 ├─ Carte interactive     (vue par défaut — OD + heatmap)
 ├─ Flux OD               (preset couches M1)
 ├─ Zones clés            (preset M2 labels + corridors)
 └─ Indicateurs           (preset M6 + focus panneau KPI)
```

Hors écran : Simulation, Recommandations, Dashboard SaaS, login.

## Wireframe vue principale

```text
[ Nav : modules Must ]  [ Titre vue | métriques M5/M6     ]
                        [ Search | Ville | Couches         ]
                        [              MAP                 ] [ KPI
                        [ Légende | GPS | Route A→B        ]   M2/M5/M6 ]
                        [ Footer : source OSM · OD gravitaire · ville ]
```

## Couches et légendes

| Couche | Défaut « Carte » | Légende |
|--------|------------------|---------|
| Flux OD | on | volume faible → fort |
| Heatmap densité | on | faible → forte |
| Zones clés M2 | off | dortoir / pôle / mixte |
| Corridors M2 | off | trait rouge |
| Indice M6 | off | déséquilibre → équilibre |
| Route A→B | off jusqu’à calcul | — |
| OSM (routes, bâtis, bus) | off | — |

## Parcours

### Urbaniste (90 s)

1. Ouvrir la carte (ville active, disclaimer OD).
2. Search d’un lieu.
3. Itinéraire démo A→B (ou deux clics) — « ce n’est pas une desire line ».
4. Vue **Zones clés** → clic zone → fiche (label, cluster, proxies).
5. Vue **Indicateurs** → M6 coloré, relier au KPI min/max.

### Élu (60 s)

1. Lire les 4 métriques du header.
2. Vue **Flux OD** : top desire lines dans le panneau.
3. Une phrase de décision (corridor + zone déséquilibrée).

## Microcopy

| Situation | Texte |
|-----------|--------|
| Loading KPI | « Chargement des KPI… » |
| API down | « Impossible de charger les indicateurs. Vérifie le backend (port 8000). » |
| OSM manquant | « OSM à importer pour cette ville (extract Geofabrik + osm2pgsql). » |
| Route vide | « Aucun chemin sur le réseau (points hors composante connectée). » |
| Pick A/B | « Cliquez le départ, puis l’arrivée. » |
| OD | « Volumes estimés (modèle gravitaire), agrégés zone→zone. » |
| M6 | « Proxy intra-zone — pas un 2SFCA. » |

## Interactions carte

- Clic zone (M2 ou M6 visible) → popup fiche.
- Bouton **Itinéraire démo** : points QA Antananarivo.
- Bouton **Choisir A et B** : deux clics carte.
- GPS : inchangé (position + hors ville).

## Accessibilité minimale

- Labels `aria-label` search / GPS / fermeture messages.
- Contraste panneaux sombre existant.
- Pas d’information uniquement par la couleur : popup + panneau KPI reprennent les labels.

## Hors-scope UX stage

Filtres période/mode (pas de série temporelle), export, onboarding multi-pages, dark/light toggle.
