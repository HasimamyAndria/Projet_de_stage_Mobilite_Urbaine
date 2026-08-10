# Checklist J-1 / Jour J — Soutenance

## J-1 (veille)

### Technique

- [ ] Docker Desktop démarré
- [ ] `Copy-Item .env.example .env` (si besoin) ; `DB_PASSWORD` OK machine
- [ ] `APP_ENV=development` pour garder `/docs` en secours (ou prod si vous assumez sans Swagger)
- [ ] `docker compose up --build -d`
- [ ] `docker compose ps` → services healthy
- [ ] Seed : `docker compose exec backend python scripts/seed_zones_od.py`
- [ ] Smoke : `python backend/scripts/smoke_mvp_qa.py` → **19/19 OK**
- [ ] Ouvrir http://localhost:8080 : carte + KPI + desire lines + M6 + route visibles
- [ ] Brancher OSM si la démo doit montrer routes/bus (sinon assumer « analytics only » à l’oral)
- [ ] Chronométrer `script-demo.md` une fois (< 4 min)

### Plan B

- [ ] 4–6 captures PNG (carte, KPI, M6, route, desire lines, keypoints)
- [ ] PDF/slides exportés (clé USB + cloud)
- [ ] Copie locale de `docs/qa-rapport.md` et `docs/securite-rgpd.md`

### Contenu oral

- [ ] Remplir `[Étudiant]` / tuteurs dans slides
- [ ] Relire `plan-oral.md` à voix haute une fois
- [ ] Choisir **la** phrase « décision métier » du script
- [ ] Relire 5 Q&R sensibles (temps réel, k-anonymité, M6≠2SFCA, OD synthétique, auth)

### Matériel

- [ ] PC chargé + chargeur
- [ ] Adaptateur HDMI / USB-C vidéo testé sur la salle (ou Zoom partagé)
- [ ] Résolution / zoom navigateur 100–110 % (lisibilité)
- [ ] Notifications OFF, VPN OK si requis, Wi-Fi salle testé
- [ ] Mode avion données mobiles en secours hotspot

---

## Jour J — T-30 min

- [ ] `docker compose ps` healthy
- [ ] Smoke rapide : `GET http://127.0.0.1:8000/health`
- [ ] Front ouvert, onglet unique, F11 prêt
- [ ] Captures plan B ouvertes dans un second onglet (caché)
- [ ] Eau / timer 15 min visible

## Jour J — Juste avant l’oral

- [ ] Recentrer la carte Antananarivo
- [ ] Vérifier panneau KPI non en erreur
- [ ] Respirer ; ouvrir sur slide titre

## Jour J — Après

- [ ] Noter questions du jury non anticipées
- [ ] `docker compose down` si machine de démo partagée

---

## Commandes utiles

```powershell
cd Projet_de_stage_Mobilité_Urbaine
docker compose up --build -d
docker compose exec backend python scripts/seed_zones_od.py
cd backend
.\venv\Scripts\python.exe scripts\smoke_mvp_qa.py
```

| URL | Rôle |
|-----|------|
| http://localhost:8080 | Démo front |
| http://localhost:8000/health | Santé API |
| http://localhost:8000/docs | Swagger (si `APP_ENV=development`) |

---

## Critères « prêt à soutenir »

```text
[ ] 5 fichiers docs/soutenance/ présents
[ ] Démo chronométrée une fois
[ ] 10+ Q&R relues
[ ] Smoke 19/19 le matin J
```
