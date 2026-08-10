---
name: 12-securite-rgpd
description: >-
  Sécurité applicative et conformité RGPD mobilité : secrets, CORS, auth
  minimale, journalisation, agrégation/k-anonymité, AIPD légère. Use when
  auditing security, privacy, or preparing compliance docs for the stage.
disable-model-invocation: true
---

# Sécurité & RGPD

## Mission

Éliminer les risques **bloquants** pour une démo/prod de stage et documenter la conformité.

## Sortie

`docs/securite-rgpd.md`

## Checklist sécurité app

```text
- [ ] Pas de credentials dans le code
- [ ] .env gitignored
- [ ] CORS restrictif en prod
- [ ] SQL paramétré uniquement
- [ ] Pas d'exposition Swagger sensible en prod sans protection
- [ ] Dependances sans CVE critique connue (scan léger)
- [ ] Headers basiques (si reverse proxy)
```

## Checklist RGPD mobilité

```text
- [ ] Finalité : aide à la décision urbaine (documentée)
- [ ] Minimisation : pas de trajet individuel exposé
- [ ] Agrégation + k-anonymité (k≥5)
- [ ] Pas de réidentification triviale via maille fine
- [ ] Durée conservation / sources documentées
- [ ] Mention des limites éthiques (pas de surveillance)
```

## Auth (pragmatique stage)

Si pas d'auth complète : documenter que l'instance est **démo contrôlée** (réseau local / VPN) et lister le backlog auth (JWT déjà en deps possibles : `python-jose`, `passlib`).

## Journalisation

Logger accès endpoints sensibles (exports OD) sans logger de données personnelles.

## Correctifs prioritaires

Ordre : secrets → injection SQL → fuite data individuelle → CORS → auth.

## Done when

- [ ] Audit écrit
- [ ] Correctifs P0 appliqués ou explicitement reportés avec mitigation
