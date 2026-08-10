# Répétition démo — fiche chrono (1 page)

Imprimer ou garder à côté de l’écran. Chronométrer **une fois à voix haute**.

| T | Action | Dire |
|---|--------|------|
| 0:00 | Ouvrir http://localhost:8080 | Carte décisionnelle, pas du tracking |
| 0:30 | Zoom ≥ 11 (routes/bus) | Couches OSM par **bbox** |
| 1:00 | Search `Antananarivo` | Parcours urbaniste |
| 1:30 | Montrer route A→B | **pgRouting** ≠ desire lines |
| 2:00 | Desire lines + KPI | OD **agrégé** ; volumes démo synthétiques |
| 2:40 | Couleurs M6 + M2 | Vert ≈ équilibre ; rouge ≈ déséquilibre |
| 3:20 | **Décision métier** | Phrase ci-dessous |
| 3:50 | Stop | « Je reviens sur méthode et limites » |

## Phrase métier (choisir 1)

**Urbaniste :** zone rouge / surplus habitat + corridor OD → discuter densification d’emplois **ou** renforcement transport sur ce couple O→D — pas de contrôle individuel.

**Élu :** une vue pour prioriser l’attention budgétaire (corridors + déséquilibres) avant étude fine.

## Garde-fous à ne pas oublier

```text
OD synthétique · k≥5 · M6 ≠ 2SFCA · M2 ≠ ML · Auth = démo locale
```

## Si ça casse (< 30 s)

Captures plan B → « QA 19/19 validé ; je poursuis sur les captures. »

## Après la répétition

- [ ] Temps démo ≤ 4 min
- [ ] Phrase métier fluide
- [ ] Crochets slides remplis dans `slides.html`
- [ ] Export PDF : ouvrir `slides.html` → `P` (imprimer) → «Enregistrer au format PDF»
