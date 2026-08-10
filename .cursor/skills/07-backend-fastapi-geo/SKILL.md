---
name: 07-backend-fastapi-geo
description: >-
  Implémentation FastAPI géospatiale : routers, services, Pydantic schemas,
  GeoJSON, bbox, pgRouting, connexion PostGIS. Use when coding or refactoring
  backend API endpoints for the mobility project.
disable-model-invocation: true
---

# Backend — FastAPI géospatial

## Mission

Livrer des endpoints **stables, documentés, performants** pour la carte et l'analytique.

## Structure cible

```text
backend/app/
  main.py          # app + CORS + include_router
  database.py      # engine + get_db
  routers/         # HTTP only
  services/        # SQL + métier
  schemas/         # Pydantic
  models/          # SQLAlchemy si ORM
```

## Règles d'implémentation

1. Router mince → appeler `services/`.
2. Réponses spatiales = GeoJSON FeatureCollection.
3. CORS : origines configurables (dev `localhost:5173`, prod via env).
4. Secrets uniquement via `.env` / variables d'environnement.
5. Retirer les `print` de debug bruyants en chemins stables (logger).
6. Valider query params (bbox, q non vide).
7. Gestion d'erreur : 400 validation, 404 ressource, 500 logué.

## Pattern endpoint bbox

```python
@router.get("/feature")
def get_feature(minLon: float, minLat: float, maxLon: float, maxLat: float, db: Session = Depends(get_db)):
    return service.get_features(db, minLon, minLat, maxLon, maxLat)
```

## Smoke test obligatoire

Après chaque endpoint :

```bash
# exemple
curl "http://127.0.0.1:8000/api/roads?minLon=...&minLat=...&maxLon=...&maxLat=..."
```

Vérifier : status 200, `type=FeatureCollection`, `features` liste.

## Refactors autorisés

- Extraire SQL de `map.py` vers `services/`
- Ajouter schemas de réponse
- Ajouter router `analytics` / `kpi` / `od`

## Interdit

- Hardcoder credentials
- Renvoyer des lignes individuelles non agrégées (flux personne)
- Charger toute la métropole sans bbox/LIMIT

## Done when

- [ ] Endpoint testé
- [ ] Contrat aligné `docs/architecture.md`
- [ ] Pas de secret dans le diff
