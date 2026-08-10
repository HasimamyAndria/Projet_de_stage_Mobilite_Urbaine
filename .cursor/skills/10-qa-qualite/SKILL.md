---
name: 10-qa-qualite
description: >-
  Qualité et tests du MVP mobilité : API smoke, SQL spatial, anonymisation,
  non-régression carte, checklist E2E. Use when writing test plans, validating
  releases, or preparing QA evidence for defense.
disable-model-invocation: true
---

# QA — Qualité MVP

## Mission

Prouver que le MVP est **démontrable et fiable** (pas une couverture industrielle totale).

## Sortie

`docs/qa-rapport.md` + tests automatisés si faisables rapidement (`pytest`, scripts curl).

## Matrices de tests

### API

| Cas | Attendu |
|-----|---------|
| Bbox valide | 200 + FeatureCollection |
| Bbox invalide | 400 |
| Search vide | 400 ou [] documenté |
| Route points connus | géométrie non vide |
| DB down | 500 contrôlé |

### Carte E2E (manuel OK)

```text
- [ ] Chargement map
- [ ] Toggle chaque couche
- [ ] Search centre la vue
- [ ] Route A→B visible
- [ ] Panneau KPI/zones (si présent)
- [ ] Message d'erreur si API down
```

### Data / conformité

```text
- [ ] Aucune donnée individuelle dans réponses OD
- [ ] Mailles sous seuil masquées/fusionnées
- [ ] LIMIT respectés (pas de timeout navigateur)
```

## Sévérité bugs

- **Bloquant** : casse la démo soutenance
- **Majeur** : fausse métrique / couche absente
- **Mineur** : polish UI

## Stratégie stage

1. Smoke scripts sur endpoints Must
2. Parcours E2E filmable
3. 3 jeux de bbox (centre dense, périphérie, hors zone)

## Done when

- [ ] Rapport QA avec date
- [ ] 0 bloquant ouvert
- [ ] Preuves (captures ou logs) référencées
