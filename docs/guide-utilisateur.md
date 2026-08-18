# Guide utilisateur — MobilitySmart

**Pour qui :** quelqu’un qui n’a jamais vu la plateforme et veut comprendre
ce qu’on a construit, ce que l’écran montre, et comment s’en servir.

**Promesse :** on explique comme à un enfant curieux. D’abord une image simple,
ensuite le vrai nom, ensuite le calcul.

**Ouvrir l’app :** `http://localhost:5173` (développement) ou
`http://localhost:8080` (Docker). Ville de démo : **Antananarivo**.

---

## 1. L’histoire en une minute

Imagine une ville découpée en **quartiers**, comme les pièces d’un puzzle.

Dans chaque pièce, on ne suit **personne**. On fait deux tas :

- un tas **« maisons »** (à peu près combien de gens y vivent) ;
- un tas **« bureaux / commerces »** (à peu près combien d’emplois il y a).

Ensuite on dessine des **flèches** d’un quartier vers un autre :
« beaucoup de monde **d’ici** irait **là-bas** travailler ».

La plateforme sert à un **urbaniste** ou un **élu** pour se poser une question
simple :

> Où concentrer l’attention ? Où les gens habitent loin des emplois ?
> Où les flux sont les plus gros ?

Ce n’est **pas** un GPS qui suit les voitures en direct.
Ce n’est **pas** un outil pour surveiller des personnes.

---

## 2. Ce qu’on a fait dans le projet (lot 1)

On a livré une **carte décisionnelle** + des indicateurs. En jargon interne,
ce sont les modules **Must** :

| Module | Nom simple | Ce que tu vois |
|--------|------------|----------------|
| **M1** | Carte des flux | Arcs colorés d’un quartier vers un autre + heatmap |
| **M2** | Points clés | Quartiers **dortoir** / **pôle emploi** / **mixte** + 5 gros corridors |
| **M5** | Tableau de bord | Les chiffres en haut et le panneau à droite |
| **M6** | Emploi-habitat | Carte rouge → vert : déséquilibre ou équilibre |
| Socle | Carte OSM + itinéraire | Rues, bâtiments, bus, recherche, trajet A→B sur le **vrai réseau** |

**Pas encore dans cette version :** recommandations de sites (M3), simulation
« et si on changeait ça ? » (M4), export, compte utilisateur.

**D’où viennent les données :**

1. **OpenStreetMap (OSM)** : rues, bâtiments, arrêts, noms de lieux.
2. Un **modèle gravitaire** : il *estime* les flux domicile → travail à partir
   des tas « maisons » et « bureaux », et de la distance. Ce n’est **pas** une
   enquête auprès des habitants.

---

## 3. La métaphore de l’école (à garder en tête)

Pense à **plusieurs écoles** dans une ville.

- Chaque **quartier** = une école + son quartier.
- **Population** = nombre d’enfants qui **dorment** dans le quartier.
- **Emplois** = nombre de **places** (classe, cantine, bureau) dans le quartier.
- **Flux OD** = « combien d’enfants du quartier A iraient à l’école du
  quartier B ».
- **Desire line** = un **élastique** tendu entre les deux écoles. Ce n’est pas
  le chemin dans les rues.
- **Itinéraire A→B** = le **chemin réel** rue par rue (comme Google Maps).
- **Zone dortoir** = beaucoup d’enfants, peu de places → ils partent ailleurs.
- **Pôle emploi** = beaucoup de places, peu d’enfants sur place → les autres
  viennent ici.
- **Indice M6** = « est-ce que ce quartier a autant de places que d’enfants ? »
  1 = oui, 0 = non, c’est très déséquilibré.

---

## 4. Tour de l’écran (ce que tu vois)

```text
┌─────────────┬──────────────────────────────────────┬──────────────┐
│ MobilitySmart│  Titre de la vue                     │              │
│ Carte        │  4 gros chiffres (M5 / M6)           │  Panneau     │
│ Flux OD      ├──────────────────────────────────────┤  Zones clés  │
│ Zones clés   │  [Recherche] [Ville] [Couches]       │  & flux      │
│ Indicateurs  │                                      │              │
│              │              LA CARTE                │  Top 5       │
│ OSM · OD     │  légende · Itinéraire · GPS          │  desire lines│
└─────────────┴──────────────────────────────────────┴──────────────┘
```

### Menu de gauche (4 vues)

Chaque bouton **allume les bonnes couches** pour un job :

| Bouton | Allumé sur la carte | Question à se poser |
|--------|---------------------|---------------------|
| **Carte interactive** | Flux OD + heatmap | Vue d’ensemble |
| **Flux OD** | Flux OD + heatmap | Où vont les plus gros volumes ? |
| **Zones clés** | Dortoirs / pôles / mixtes + corridors rouges | Quels quartiers sont « spéciaux » ? |
| **Indicateurs** | Indice emploi-habitat coloré | Quels quartiers sont déséquilibrés ? |

### Quatre chiffres en haut

| Carte | Signifie | Analogie |
|-------|----------|----------|
| **Zones OD** | Nombre de pièces du puzzle | Combien d’écoles / quartiers |
| **Flux OD agrégés** | Combien de flèches (volumes assez gros) | Combien de liaisons « A → B » |
| **Corridors M2** | Les **5 plus gros** flux | Les 5 couloirs les plus fréquentés de la récré |
| **Indice emploi-habitat** | Moyenne de l’équilibre (0 à 1) | Note moyenne de « équilibre » de la ville |

Sur la démo Antananarivo (contrôle qualité du 18 août 2026) : **36** zones,
indice moyen environ **0,16** (beaucoup de quartiers assez déséquilibrés —
c’est normal avec des proxies OSM, ce n’est pas « la note de la ville réelle »).

### Barre sur la carte

- **Rechercher un lieu…** : tape un nom OSM, Entrée, clique le résultat → la
  carte vole vers ce point.
- **Ville** (souvent « Antananarivo ») : presets (Tana, et Paris / Madrid si
  OSM a été importé). Sans extract OSM, un bandeau dit que OSM manque.
- **Couches** : cases à cocher. Groupe **Analyse** (le métier) et **Fond OSM**
  (rues, bâtiments, bus).

### Boutons en bas de carte

| Bouton | Effet |
|--------|--------|
| **Itinéraire démo** | Trace un trajet **rue par rue** entre deux points déjà testés |
| **Choisir A et B** | 1er clic = départ (vert), 2e clic = arrivée (rouge) |
| **Ma position** | GPS du navigateur (souvent imprécis sur PC) |

### Panneau de droite

C’est le **cahier du maître** :

- synthèse (zones, flux, volume total, flux max) ;
- emploi-habitat (score moyen, min, max + noms des zones extrêmes) ;
- points clés (combien de dortoirs, pôles, mixtes, corridors) ;
- **Top 5 desire lines** : les 5 plus gros « A → B » ;
- une **note** : données OSM + volumes *estimés*.

### Clic sur un quartier

Si la vue **Zones clés** ou **Indicateurs** est active, un clic ouvre une
fiche : nom, label M2, cluster, population proxy, emplois proxy, indice M6.

---

## 5. Guide pas à pas (première visite, ~8 minutes)

Fais les étapes **dans l’ordre**. À chaque fois, dis à voix haute ce que tu vois.

### Étape 1 — Respire

Tu arrives sur **Carte interactive**. Des **arcs** (traits courbes) relient des
points blancs. Une **tache de chaleur** (bleu → rouge) montre où il y a le plus
de « maisons + bureaux ».

Les arcs **verts** sont des petits volumes, les arcs **rouges** des gros
volumes (légende : moins de 50 → plus de 200).

### Étape 2 — Lis les 4 chiffres

Sans zoomer. « Combien de quartiers ? Combien de flux ? Combien de corridors ?
Quelle note d’équilibre moyenne ? »

### Étape 3 — Vue Flux OD

Même carte, focus métier. Dans le panneau, lis le **n° 1 du Top 5**.
C’est le couple origine → destination le plus chargé (volume estimé).

**Piège :** ce trait **ne suit pas les rues**. C’est un élastique entre les
centres des deux quartiers (légèrement courbé pour qu’on le lise mieux).

### Étape 4 — Compare avec un vrai chemin

Clique **Itinéraire démo**. Une ligne **bleue** apparaît sur le réseau routier.

Tu as maintenant les deux objets à ne jamais confondre :

| Objet | Couleur typique | C’est… | Ce n’est pas… |
|-------|-----------------|--------|----------------|
| Desire line (flux OD) | vert → rouge selon volume | Un volume **quartier → quartier** | Un itinéraire |
| Route A→B | bleu clair | Le plus court chemin **sur les rues OSM** | Un flux de voyageurs |

### Étape 5 — Vue Zones clés

Les polygones se colorent :

- **violet** = zone dortoir (on habite ici, on travaille ailleurs) ;
- **orange** = pôle emploi (on vient travailler ici) ;
- **bleu** = zone mixte ;
- **traits rouges épais** = les 5 corridors (plus gros volumes).

Clique un polygone. Lis la fiche. Relie-la au panneau (comptages dortoirs / pôles).

### Étape 6 — Vue Indicateurs

Même puzzle, autre peinture :

- **rouge** = déséquilibre fort (presque que des maisons, **ou** presque que
  des emplois) ;
- **orange** = milieu ;
- **vert** = emplois ≈ population **dans ce quartier**.

Le vert ne veut **pas** dire « les gens mettent 5 minutes pour aller au
travail ». On n’a pas mesuré les temps vers les quartiers voisins.

### Étape 7 — Une phrase de décision

Exemple (à adapter aux noms affichés) :

> Ce quartier rouge a un surplus d’habitat. Un gros corridor part vers un pôle
> orange. Pour un élu, ça oriente la discussion : rapprocher emplois et
> logements, ou renforcer le transport sur ce couple — pas contrôler les gens.

---

## 6. Toutes les couches (bouton Couches)

### Analyse (cœur métier)

| Case | Défaut vue Carte | Lecture |
|------|------------------|---------|
| Flux OD | allumé | Arcs volume ; points blancs = centres de zones |
| Heatmap densité | allumé | Plus c’est chaud, plus `population + emplois` est élevé au centroïde |
| Zones clés (M2) | éteint | Polygones violet / orange / bleu |
| Indice M6 | éteint | Polygones rouge → vert |
| Corridors (zones clés) | éteint | 5 plus gros flux, en rouge |
| Route A→B | éteint jusqu’au calcul | Itinéraire réseau |

### Fond OSM (décor géographique)

S’affichent surtout si tu **zoomes** assez (≥ 11) : la carte ne charge que ce
qui est **dans la fenêtre** (bbox), pour rester rapide.

| Case | Contenu |
|------|---------|
| Routes | Voirie OSM |
| Bâtiments | Emprises de bâtiments |
| Arrêts de bus | Points OSM |
| Lignes de bus | Tracés OSM (pas un GTFS horaire) |

---

## 7. Tous les calculs (avec exemples)

Les nombres ci-dessous sont des **exemples pédagogiques**. Les vrais totaux
de la démo sont ceux du panneau.

### 7.1 Découpage en zones

On prend les lieux OSM du type quartier / suburb dans la boîte de la ville.
On dessine des polygones (Voronoi) pour que **tout le territoire** soit dans
une pièce du puzzle. En démo Tana : jusqu’à **36** zones.

### 7.2 Tas « maisons » et tas « emplois » (proxies)

On n’a pas le recensement. On **devine** à partir d’OSM :

```text
population_proxy = max( nombre_de_bâtiments × 4 , 50 )
jobs_proxy       = max( nombre_de_POI_emploi × 8
                       + parcelles_commerciales × 25 , 20 )
```

**Pourquoi 4, 8, 25 ?** Ce sont des **poids** choisis pour la démo, pas une
mesure officielle. « Proxy » = « à la place de ».

**Exemple :**

Un quartier a **120 bâtiments**, **15 commerces/bureaux** OSM, **2** grandes
parcelles commerciales.

```text
population = max(120 × 4, 50) = max(480, 50) = 480
emplois    = max(15 × 8 + 2 × 25, 20) = max(120 + 50, 20) = 170
```

Lecture enfant : « Environ 480 habitants et 170 emplois — surtout un quartier
où l’on habite. »

### 7.3 Flux OD — modèle gravitaire (M1)

Idée de Newton, version « déplacements » :

> Plus il y a d’habitants **au départ** et d’emplois **à l’arrivée**, plus le
> flux est gros. Plus c’est **loin**, plus le flux fond.

Formule réelle du seed :

```text
distance_m = max( distance entre les deux centres , 500 mètres )
volume     = (population_origine × emplois_destination)
             / (distance_m ^ 1.35)
             × 0.045
```

On **jette** les tout petits flux (volume brut **< 20**), pour ne pas montrer
des filets ridicules et pour respecter un seuil d’anonymat.

Le temps affiché n’est **pas** un temps GPS. On suppose **22 km/h** en moyenne :

```text
temps_min = (distance_km / 22) × 60
```

**Exemple (nombres ronds) :**

- Quartier A : 2000 habitants  
- Quartier B : 2000 emplois  
- Distance des centres : **500 m** (le plancher)

```text
500 ^ 1,35  ≈  4395
volume      =  (2000 × 2000) / 4395 × 0,045
            =  4 000 000 / 4395 × 0,045
            ≈  41
```

On affiche environ **41** « voyageurs » estimés A → B.
Temps : 0,5 km / 22 × 60 ≈ **1,4 minute**.

Si A et B sont beaucoup plus loin, le dénominateur explose : le volume chute.
C’est voulu : on voyage moins volontiers très loin (dans ce modèle simple).

**Desire line à l’écran :** une ligne (ensuite **courbée** pour la lisibilité)
du centre de A au centre de B. Épaisseur et couleur suivent le volume
(vert ≈ 20, rouge ≈ 220).

### 7.4 Heatmap

Pour chaque zone, un point au centre avec un poids :

```text
poids = population_proxy + jobs_proxy
```

La tache est **chaude** là où les deux tas ensemble sont gros. Ce n’est pas
un trafic horaire.

### 7.5 Labels M2 (dortoir / pôle / mixte)

On calcule d’abord les **médianes** de la ville (la valeur du milieu si on
range tous les quartiers).

```text
part_emplois = emplois / (population + emplois)
```

Règles :

```text
Pôle emploi  :  emplois ≥ médiane_emplois   ET  part_emplois ≥ 0,45
Zone dortoir :  population ≥ 0,9 × médiane_pop  ET  part_emplois ≤ 0,38
Zone mixte   :  tout le reste
```

**Exemple.** Cinq quartiers, médiane population = **300**, médiane emplois = **200**.

| Quartier | Pop | Emplois | Part emplois | Label |
|----------|-----|---------|--------------|--------|
| Maisons | 500 | 50 | 50/550 ≈ **0,09** | **Dortoir** (pop haute, peu d’emplois) |
| Bureaux | 200 | 400 | 400/600 ≈ **0,67** | **Pôle** (beaucoup d’emplois) |
| Centre | 300 | 200 | 200/500 = **0,40** | **Mixte** (entre 0,38 et 0,45) |

Sur la démo QA Tana : **21** dortoirs, **1** pôle, **14** mixtes. Un seul gros
pôle, beaucoup de quartiers surtout résidentiels : lecture typique d’une
estimation OSM, pas un verdict urbanistique définitif.

### 7.6 Corridors M2

Les **5** desire lines avec le plus gros volume (au-dessus du seuil d’anonymat).

Ce n’est **pas** un capteur qui dit « cette avenue est saturée ». C’est
« ces **couples de quartiers** ont le plus gros volume estimé ».

### 7.7 Clustering K-means (M2)

On prend le **centre** de chaque quartier (longitude, latitude), on met les
valeurs entre 0 et 1, et on fait des **groupes spatiaux** (quartiers proches
ensemble).

Nombre de groupes :

```text
k = max(2, min(4, nombre_de_zones ÷ 3))
```

36 zones → k = **4**. Le tirage de départ est **fixe** (graine 42) : le résultat
est reproductible.

Le **silhouette** (0 à 1) dit si les groupes sont bien séparés. En QA : **0,257**
= séparation moyenne, pas un clustering « parfait ». Le nom du groupe est
surtout le **label M2 majoritaire** dans le paquet (ex. « Groupe 2 — Zone dortoir »).

Ce n’est **pas** un regroupement de personnes.

### 7.8 Indice emploi-habitat M6

Pour **un** quartier seulement (on ne regarde pas les voisins) :

```text
indice = 1 − |emplois − population| / (emplois + population)
```

Toujours entre **0** et **1**. Si pop et jobs sont à 0 : pas de score.

**Exemples :**

| Pop | Emplois | Calcul | Indice | Couleur | Sens |
|-----|---------|--------|--------|---------|------|
| 400 | 400 | 1 − 0/800 | **1,00** | Vert | Équilibré |
| 900 | 100 | 1 − 800/1000 | **0,20** | Rouge | Surplus d’habitat |
| 200 | 800 | 1 − 600/1000 | **0,40** | Orangé | Surplus d’emplois |

Le panneau affiche la **moyenne**, le **min** (le plus déséquilibré) et le **max**
(le plus équilibré), avec les noms des zones.

**Limite d’enfant :** si tout le monde habite à gauche et travaille à droite,
**chaque** quartier peut être rouge, même si la ville « fonctionne » grâce aux
trajets. L’indice ne voit **pas** ça. Ce n’est pas un 2SFCA (accessibilité
aux emplois des autres zones).

### 7.9 KPI M5 (chiffres)

```text
volume total = somme des trip_count des flux gardés
flux max     = le plus gros trip_count
flux moyen   = moyenne des trip_count
top 5        = les 5 plus gros, avec km et minutes estimées
```

### 7.10 Itinéraire A→B (réseau)

Dijkstra (plus court chemin) sur les **rues** OSM, dans un rectangle autour
de A et B. Coût = longueur en mètres. Si A ou B est mal accroché au graphe
(impasse isolée), l’app cherche un sommet **atteignable** tout près.

Si rien n’est trouvé : message
« Pas d’itinéraire : cliquez plus près d’une rue du réseau OSM. »

Points de la démo (ne pas en inventer d’autres en live sans test) :

```text
A : 47,52928    -18,903276
B : 47,5160582  -18,8680788
```

### 7.11 Vie privée (k-anonymité)

On n’affiche **jamais** un flux de moins de **5** « voyageurs ». Sur la carte
des arcs, le front demande même un minimum de **50**, pour ne garder que les
traits lisibles.

Aucune identité, aucun trajet individuel.

---

## 8. Messages à l’écran (que faire)

| Tu lis… | Ça veut dire | Que faire |
|---------|--------------|-----------|
| Chargement des KPI… | Le panneau attend l’API | Attendre quelques secondes |
| Impossible de charger les indicateurs… | Backend down | Vérifier que l’API tourne (port **8000**) |
| OSM à importer / OSM manquant | Pas d’extract pour cette ville | Rester sur Antananarivo, ou importer un PBF |
| Cliquez le départ, puis l’arrivée | Mode A/B | Deux clics sur la carte, près des rues |
| Aucun chemin / Pas d’itinéraire | Graphe coupé ou clic trop loin d’une rue | Reprendre **Itinéraire démo** |
| Volumes estimés (gravitaire) | Rappel de méthode | C’est normal, ce n’est pas une enquête |

---

## 9. Ce que tu peux conclure (et ce que tu ne peux pas)

**Oui, utile pour :**

- voir **où** les volumes estimés sont les plus gros ;
- repérer des quartiers **surtout habitat** ou **surtout emplois** ;
- montrer en 2 minutes une carte + 4 chiffres à un élu ;
- distinguer **flux agrégé** et **chemin routier**.

**Non, tu ne peux pas dire :**

- « Exactement 41 personnes font ce trajet chaque matin » ;
- « Cette rue est bouchée » (pas de capteur) ;
- « Ce quartier vert a de courts trajets domicile-travail » ;
- « Voici le meilleur endroit pour un nouvel hôpital / un nouveau BHNS »
  (module recommandations non livré).

---

## 10. Mini-quiz (pour vérifier que tu maîtrises)

1. Un trait courbe rouge entre deux points blancs : **rue** ou **flux quartier → quartier** ?
2. La ligne bleue après « Itinéraire démo » : **desire line** ou **chemin OSM** ?
3. Un polygone violet : **dortoir**, **pôle**, ou **équilibre M6** ?
4. Un polygone rouge en vue Indicateurs : trop de volume OD, ou **déséquilibre** emplois/habitat **dans** la zone ?
5. L’indice 1,0 : tout le monde travaille à 5 minutes, ou **autant d’emplois que d’habitants dans ce quartier** ?

Réponses : 1 flux · 2 chemin OSM · 3 dortoir · 4 déséquilibre M6 · 5 autant d’emplois que d’habitants.

---

## 11. Pour aller plus loin (docs projet)

| Document | Contenu |
|----------|---------|
| `docs/exigences-mvp.md` | Vision, personas, ce qui est Must / reporté |
| `docs/methodes.md` | Formules M2 / M5 / M6 plus denses |
| `docs/ux-mvp.md` | Intentions d’écran |
| `docs/architecture.md` | FastAPI, PostGIS, pgRouting, MapLibre |
| `docs/soutenance/script-demo.md` | Démo orale < 4 min |
| `docs/qa-rapport.md` | Preuve smoke 24/24 |

Si tu es **dans Cursor** et que tu bloques encore : demande à l’agent
d’utiliser le skill **guide utilisateur plateforme** — il est fait pour
t’expliquer l’écran, pas pour modifier le code.
