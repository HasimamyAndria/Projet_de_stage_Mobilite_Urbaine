# Sécurité & RGPD — MVP Mobilité Urbaine

**Date :** 2026-08-10  
**Périmètre :** instance de stage / démo contrôlée (réseau local ou VPN)  
**Finalité :** aide à la décision urbaine (flux agrégés, points clés, indice emploi-habitat) — **pas** de surveillance individuelle ni de tracking usager.

---

## Verdict

| Domaine | Statut | Commentaire |
|---------|--------|-------------|
| Secrets | **OK** après correctifs | `.env` gitignored ; pas de credentials hardcodés dans l’API |
| CORS | **OK** | Origines explicites ; méthodes GET/OPTIONS ; `*` rejeté |
| Injection SQL | **OK** | Requêtes `text()` + paramètres nommés côté API |
| Agrégation / k-anonymité | **OK** | Plancher `k≥5` sur OD (API + services) |
| Logs | **OK** (MVP) | Accès OD journalisés sans dump de volumes nominatifs |
| Auth | **Reporté** | Démo contrôlée ; backlog JWT documenté |
| Swagger prod | **OK** | Désactivé si `APP_ENV=production` |

**Bloquants ouverts :** 0  
**Accepté pour démo soutenance :** oui, sous contrainte « réseau contrôlé ».

---

## 1. Checklist sécurité applicative

| Contrôle | Statut | Preuve / mitigation |
|----------|--------|---------------------|
| Pas de credentials dans le code | OK | `database.py` lit `DB_*` depuis l’env ; scripts seed/probe idem |
| `.env` gitignored | OK | `.gitignore` : `.env` + `!.env.example` |
| Mot de passe par défaut documenté | OK | `mobilite_change_me` dans `.env.example` — à changer hors machine perso |
| CORS restrictif | OK | `CORS_ORIGINS` listée ; rejet de `*` ; `allow_credentials=False` |
| SQL paramétré | OK | Routers/services API : `:param` ; pas de concat user input |
| Swagger sensible en prod | OK | `docs_url` / `redoc` / `openapi` = `None` si `APP_ENV=production` |
| Headers basiques (reverse proxy) | OK | nginx : `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` |
| Dépendances CVE critiques | À rejouer avant livrable externe | Stack courte (`fastapi`, `uvicorn`, `SQLAlchemy`, `psycopg2`, `pydantic`) — scan `pip-audit` recommandé hors MVP |

### Auth (pragmatique stage)

Pas d’authentification applicative dans le MVP.

| Contexte | Règle |
|----------|-------|
| Démo soutenance | Machine locale / Docker Desktop ; ports non exposés Internet |
| Prod réelle | **Bloquant** sans auth + TLS + restriction réseau |

**Backlog auth (hors MVP stage) :** JWT (`python-jose` / `passlib`), rôles lecture (urbaniste / admin), HTTPS reverse-proxy, rate-limit sur `/api/od/*`.

---

## 2. Checklist RGPD mobilité

| Contrôle | Statut | Détail |
|----------|--------|--------|
| Finalité documentée | OK | Aide à la décision urbaine (M1/M2/M5/M6) |
| Minimisation | OK | Pas de trajet individuel, pas d’identifiant usager, pas de GPS personnel |
| Agrégation zone→zone | OK | Tables `mobility_zones` / `mobility_flows` ; API OD sans `user_id` / `trip_id` |
| k-anonymité `k≥5` | OK | `app/privacy.py` → `K_ANONYMITY_MIN = 5` ; filtre SQL + `Query(ge=5)` |
| Réidentification maille fine | Mitigé MVP | Zones grille démo (~km) ; proxies synthétiques ; pas d’IRIS réel |
| Durée / sources | OK | OSM public ; OD **synthétiques** (seed gravitaire) — pas de conservation de données personnelles |
| Limites éthiques | OK | Produit ≠ surveillance trafic temps réel ; volumes démo non opérationnels |

### Règle d’exposition OD

```text
passenger_count / trip_count  ≥  K_ANONYMITY_MIN (= 5)
défaut UI / API                 =  20  (OD_MIN_PASSENGERS_DEFAULT)
```

Endpoints concernés :

- `GET /api/od/flows?min_passengers=` (plancher 5)
- `GET /api/od/summary` (totaux et top filtrés `>= k`)
- corridors M2 (`keypoints`) filtrés `>= k`

### Journalisation

| Endpoint | Log | Contenu interdit |
|----------|-----|------------------|
| `/api/od/zones` | accès | géométries / listes nominatives |
| `/api/od/flows` | accès + `feature_count` | dump des couplets O→D |
| `/api/od/summary` | accès + comptes agrégés | détails individuels (n/a) |

Logger : module `logging` (`mobilite.api`, `mobilite.od`) — stdout Docker suffisant pour le stage.

---

## 3. Correctifs appliqués (P0)

Ordre suivi : secrets → fuite data individuelle → CORS → docs prod → logs → headers.

| # | Correctif | Fichiers |
|---|-----------|----------|
| 1 | Constante `K_ANONYMITY_MIN` + clamp service | `backend/app/privacy.py`, `services/od.py`, `services/keypoints.py` |
| 2 | Validation API `min_passengers >= 5` | `backend/app/routers/od.py` |
| 3 | Échec explicite si `DB_*` manquants | `backend/app/database.py` |
| 4 | CORS durci (GET/OPTIONS, no credentials, no `*`) | `backend/app/main.py` |
| 5 | Swagger off en `APP_ENV=production` | `main.py`, `.env.example`, `docker-compose.yml` |
| 6 | Logs d’accès OD sans dump métier | `routers/od.py`, `services/od.py` |
| 7 | Headers sécu nginx | `frontend/nginx.conf` |

### Reporté (mitigation)

| Item | Mitigation stage | Prod cible |
|------|------------------|------------|
| Auth JWT | Réseau local / VPN | Auth + RBAC |
| TLS | HTTP localhost | HTTPS (cert) |
| Scan CVE automatisé | Revue manuelle stack courte | CI `pip-audit` / Dependabot |
| AIPD formelle | AIPD légère ci-dessous | AIPD CNIL si données réelles |

---

## 4. AIPD légère (stage)

| Question | Réponse MVP |
|----------|-------------|
| Traitement de données personnelles ? | **Non** en l’état : OSM + agrégats synthétiques zone→zone |
| Si OD réels demain ? | Importer uniquement des comptes agrégés pré-anonymisés (`k≥5`), jamais de traces individuelles |
| Risque principal | Réidentification par croisement zone fine × volume faible → **contrôlé** par plancher k + maille large |
| Mesures | Minimisation, agrégation, seuil k, pas d’export brut individuel, instance non publique |
| Droits personnes | N/A tant que pas de données personnelles ; sinon base légale + registre à créer avant import réel |

---

## 5. Checklist opérateur (avant démo / « prod » stage)

```text
[ ] .env présent, non commit ; DB_PASSWORD changé si machine partagée
[ ] APP_ENV=production si exposition hors localhost → /docs inaccessible
[ ] CORS_ORIGINS limité aux URLs front réelles (pas *)
[ ] Ports 5432/8000/8080 non ouverts sur Internet
[ ] Seed OD uniquement (pas d’import de traces individuelles)
[ ] Smoke QA : python backend/scripts/smoke_mvp_qa.py
```

---

## 6. Références code

| Sujet | Emplacement |
|-------|-------------|
| k-anonymité | `backend/app/privacy.py` |
| CORS / env / docs | `backend/app/main.py` |
| OD API | `backend/app/routers/od.py`, `services/od.py` |
| Headers front | `frontend/nginx.conf` |
| Secrets modèle | `.env.example` |

---

## Done when (skill 12)

- [x] Audit écrit (`docs/securite-rgpd.md`)
- [x] Correctifs P0 appliqués (secrets, CORS, agrégation OD, logs, headers)
- [x] Auth reportée avec mitigation « démo contrôlée »
