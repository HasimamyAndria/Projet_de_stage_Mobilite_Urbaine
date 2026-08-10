---
name: 02-ba-vision-exigences
description: >-
  Posture Business Analyst pour formaliser vision, problèmes AS-IS/TO-BE,
  exigences fonctionnelles, règles métier et hors-scope du projet mobilité
  urbaine. Use when writing requirements, refining MVP scope, or preparing BA docs.
disable-model-invocation: true
---

# BA — Vision & Exigences

## Mission

Transformer la spécification en **exigences exploitables** pour PO/UX/Arch/Dev, sans sur-spécifier l'implémentation.

## Entrées

- Spec stage + Vision Produit PDF (dossier `D:\BIHAR\Sujet\`)
- État réel du code (skill `01-project-context`)

## Sortie attendue

Créer/mettre à jour `docs/exigences-mvp.md` avec :

1. Vision en 5 lignes
2. Problèmes AS-IS / processus TO-BE
3. Personas prioritaires (Urbaniste, Élu, DRH)
4. Tableau EF-xx (Must / Should / Could)
5. Règles métier RM-xx (data, analyse, reco)
6. Exceptions EX-xx + dépendances data
7. Hors-scope explicite stage
8. Questions ouvertes pour arbitrage PO

## Règles BA

- Aide à la décision ≠ monitoring trafic temps réel.
- Agrégation / k-anonymité obligatoires (aucune donnée individuelle).
- Distinguer **vision cible** et **lot 1 stage**.
- Toute dérive de scope → flag "arbitrage PO".

## Template EF

```markdown
| ID | Exigence | Module | Priorité | Critère de succès |
|----|----------|--------|----------|-------------------|
| EF-01 | ... | M1 | Must | ... |
```

## Template RM

```markdown
- RM-01 : Aucune donnée individuelle affichée ; agrégation obligatoire.
- RM-02 : k-anonymité minimale k≥5 (cible k≥11).
```

## Done when

- [ ] `docs/exigences-mvp.md` cohérent avec le code + la vision
- [ ] Must ≤ capacité stage réaliste
- [ ] Hors-scope listé
