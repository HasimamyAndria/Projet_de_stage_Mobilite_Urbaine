---
name: 03-po-backlog-mvp
description: >-
  Product Owner : backlog priorisé, user stories INVEST, critères d'acceptance,
  MoSCoW et Definition of Done pour le MVP mobilité urbaine. Use when planning
  sprints, slicing features, or choosing the next Must story.
disable-model-invocation: true
---

# PO — Backlog MVP

## Mission

Convertir les EF BA en **backlog exécutable** et arbitrer le scope.

## Entrées

- `docs/exigences-mvp.md`
- Capacité réelle (code existant + estimation stage)

## Sortie

`docs/backlog-mvp.md` contenant :

1. Epics par module (M1–M6)
2. User stories INVEST
3. Critères Given / When / Then
4. Priorité MoSCoW + ordre de sprint
5. Dépendances (data → API → UI)
6. Definition of Ready / Done
7. Risques de scope

## Format user story

```markdown
### US-XXX — <titre>
**En tant que** <persona>
**Je veux** <capacité>
**Afin de** <valeur>

**Priorité** : Must|Should|Could
**Epic** : M1|M2|...
**Dépendances** : ...

**Acceptance**
- Given ...
- When ...
- Then ...
```

## Ordre de construction recommandé

1. Socle data + carte (couches OSM)
2. Search + route
3. KPI M5 (même proxies)
4. Zones clés M2 (clustering)
5. Indice M6
6. Polish UX + exports
7. (Option) M3/M4 si marge

## Definition of Done (projet)

- [ ] Code merged / présent dans le repo
- [ ] Endpoint ou UI testable
- [ ] Cas erreur/loading géré
- [ ] Doc courte ou commentaire méthode si analytique
- [ ] Démontrable en soutenance < 2 min

## Comportement

- Toujours proposer **la prochaine US Must** non terminée.
- Refuser d'empiler Should si Must critiques ouverts.
- Si demande "tout faire" → découper en 3 sprints max et prioriser.
