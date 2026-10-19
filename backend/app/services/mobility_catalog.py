"""
Catalogue de mobilité simulée — une seule source pour les décideurs.

Les organisations, les personnes et les trajets viennent des fichiers
`territory`, `organizations` et `persons`. Les volumes OSM gravitaires
(`mobility_flows`) restent une autre couche, nommée à part.

Tant qu'aucune enquête n'est collectée, chaque chiffre exposé ici est une
estimation simulée.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from app.data.organizations import ORGANIZATIONS
from app.data.persons import PERSONS
from app.data.territory import CITIES, PLACES, ROLES, places_of
from app.services.lens import (
    HOST_ROLES,
    _circle,
    _edges,
    _expand,
    _km,
    resolve_city,
)

SPEED_KMH = 18.0
KMEANS_SEED = 42
FREQUENCIES = {
    "quotidien",
    "5 jours/semaine",
    "3 jours/semaine",
    "hebdomadaire",
    "occasionnel",
}
SOURCE = (
    "Effectifs simulés par organisation (groupes de 20 personnes et plus). "
    "Aucune enquête ménage n'a été collectée."
)
METHOD = (
    "Somme des groupes dont le domicile ou le lieu de travail tombe dans le périmètre. "
    "La distance est une orthodromie × 1,35. Le temps utilise 18 km/h, "
    "vitesse de pointe urbaine supposée, pas un temps pgRouting."
)


def _time_min(km: float) -> int:
    return int(round(km / SPEED_KMH * 60))


def _frequency(cadence: str) -> str:
    text = cadence.lower()
    if "ouvr" in text or "quotid" in text:
        return "5 jours/semaine"
    if "3 jours" in text:
        return "3 jours/semaine"
    if "chaque" in text or "hebdo" in text:
        return "hebdomadaire"
    if "occasion" in text:
        return "occasionnel"
    return "5 jours/semaine"


def _period(purpose: str, direction: str) -> str:
    if purpose != "travail":
        return "journee"
    return "matin" if direction == "aller" else "soir"


def _level_label(place: dict) -> str:
    if place["level"] == "quartier":
        return "quartier"
    if "arrondissement" in place["name"].lower():
        return "arrondissement"
    if place["level"] == "commune":
        return "commune"
    return place["level"]


def _city(label: str) -> dict:
    return resolve_city(label)


def _work_groups(city_id: str) -> list[dict]:
    return [row for row in _edges(city_id) if row["purpose"] == "travail"]


def _errand_groups(city_id: str) -> list[dict]:
    return [row for row in _edges(city_id) if row["purpose"] != "travail"]


def _zone_ids(city_id: str, raw: str) -> list[str] | None:
    if not raw or not raw.strip():
        return None
    found = _expand(city_id, raw)
    if found:
        return found
    direct = []
    for token in raw.split(","):
        token = token.strip()
        place = PLACES.get(token)
        if place and place["city_id"] == city_id and place["level"] == "quartier":
            direct.append(token)
    return direct or None


def _scope_places(city_id: str, zone: str) -> tuple[str, str, list[str] | None]:
    """Nom du cadre, niveau, identifiants de quartiers (None = toute la ville)."""
    city = next(item for item in CITIES if item["id"] == city_id)
    ids = _zone_ids(city_id, zone)
    if not ids:
        return city["name"], "ville", None
    if len(ids) == 1:
        place = PLACES[ids[0]]
        parent = place["parent_name"] or city["name"]
        label = f"{parent} → {place['name']}" if place["level"] == "quartier" else place["name"]
        return label, _level_label(place), ids
    names = [PLACES[item]["name"] for item in ids]
    return ", ".join(names), "selection", ids


def persons_of_city(city_id: str) -> list[dict]:
    """Une ligne par employé simulé. Les fiches du journal restent à part."""
    rows: list[dict] = []
    for group in _work_groups(city_id):
        home = PLACES[group["origin_id"]]
        for index in range(int(group["headcount"])):
            rows.append(
                {
                    "person_id": f"{group['organization_id']}:{group['origin_id']}:{index + 1:03d}",
                    "city_id": city_id,
                    "residence_id": group["origin_id"],
                    "arrondissement_id": home["parent_id"],
                    "company_id": group["organization_id"],
                    "job_label": group["organization_kind"],
                    "sector": group["organization_kind"],
                    "mode": group["mode"],
                    "work_id": group["destination_id"],
                    "distance_km": group["km"],
                    "time_min": _time_min(group["km"]),
                    "frequency": _frequency(group["cadence"]),
                    "purpose": "travail",
                    "source": "organisation",
                }
            )
    return rows


def trip_rows(city_id: str) -> list[dict]:
    """Aller, retour, et déplacements réguliers hors travail. Agrégés par groupe."""
    rows: list[dict] = []
    for group in _work_groups(city_id):
        base = {
            "city_id": city_id,
            "person_id": None,
            "group_size": int(group["headcount"]),
            "purpose": "travail",
            "frequency": _frequency(group["cadence"]),
            "distance_km": group["km"],
            "duration_min": _time_min(group["km"]),
            "mode": group["mode"],
            "company_id": group["organization_id"],
            "synthetic": True,
        }
        rows.append(
            {
                **base,
                "trip_id": f"aller:{group['organization_id']}:{group['origin_id']}",
                "origin_id": group["origin_id"],
                "destination_id": group["destination_id"],
                "period": "matin",
            }
        )
        rows.append(
            {
                **base,
                "trip_id": f"retour:{group['organization_id']}:{group['origin_id']}",
                "origin_id": group["destination_id"],
                "destination_id": group["origin_id"],
                "period": "soir",
            }
        )
    for index, group in enumerate(_errand_groups(city_id)):
        rows.append(
            {
                "trip_id": f"hors-travail:{city_id}:{index}",
                "city_id": city_id,
                "person_id": None,
                "group_size": int(group["headcount"]),
                "origin_id": group["origin_id"],
                "destination_id": group["destination_id"],
                "purpose": group["purpose"],
                "frequency": _frequency(group["cadence"]),
                "distance_km": group["km"],
                "duration_min": _time_min(group["km"]),
                "period": "journee",
                "mode": group["mode"],
                "company_id": None,
                "synthetic": True,
            }
        )
    return rows


def _public_flow(group: dict, city_total: int) -> dict:
    origin = PLACES[group["origin_id"]]
    dest = PLACES[group["destination_id"]]
    share = round(group["headcount"] / city_total, 3) if city_total else 0
    return {
        "origin_id": group["origin_id"],
        "origin_name": origin["name"],
        "origin_parent": origin["parent_name"],
        "destination_id": group["destination_id"],
        "destination_name": dest["name"],
        "destination_parent": dest["parent_name"],
        "headcount": group["headcount"],
        "share": share,
        "purpose": group["purpose"],
        "purpose_label": group["purpose_label"],
        "frequency": _frequency(group["cadence"]),
        "cadence": group["cadence"],
        "distance_km": group["km"],
        "time_min": _time_min(group["km"]),
        "mode": group["mode"],
        "period": "matin" if group["purpose"] == "travail" else "journee",
        "organization_id": group["organization_id"],
        "organization_name": group["organization_name"],
        "sector": group["organization_kind"],
        "why": group["why"],
        "synthetic": True,
    }


def list_flows(
    city_label: str,
    *,
    origin: str = "",
    destination: str = "",
    purpose: str = "",
    period: str = "",
    company: str = "",
    frequency: str = "",
) -> dict:
    city = _city(city_label)
    groups = _edges(city["id"])
    work_total = sum(row["headcount"] for row in groups if row["purpose"] == "travail") or 1
    if origin.strip() and _zone_ids(city["id"], origin) is None:
        raise ValueError(f"Origine inconnue : {origin}")
    if destination.strip() and _zone_ids(city["id"], destination) is None:
        raise ValueError(f"Destination inconnue : {destination}")
    origin_ids = set(_zone_ids(city["id"], origin) or [])
    dest_ids = set(_zone_ids(city["id"], destination) or [])
    kept = []
    for group in groups:
        if origin_ids and group["origin_id"] not in origin_ids:
            continue
        if dest_ids and group["destination_id"] not in dest_ids:
            continue
        if purpose and purpose not in {"all", "tous"} and group["purpose"] != purpose:
            continue
        if company and company not in {"all", "toutes"} and group["organization_id"] != company:
            continue
        freq = _frequency(group["cadence"])
        if frequency and frequency not in {"all", "toutes"}:
            if frequency == "quotidien" and freq not in {"quotidien", "5 jours/semaine"}:
                continue
            if frequency == "regulier" and freq == "occasionnel":
                continue
            if frequency not in {"quotidien", "regulier"} and freq != frequency:
                continue
        flow = _public_flow(group, work_total)
        if period and period not in {"all", "journee", "jour"} and flow["period"] != period:
            if not (period == "matin" and group["purpose"] == "travail"):
                continue
        kept.append(flow)
    kept.sort(key=lambda item: item["headcount"], reverse=True)
    scope, level, _ids = _scope_places(city["id"], origin or destination)
    return {
        "city": city["name"],
        "level": level,
        "scope": scope,
        "period": period or "jour ouvré",
        "synthetic": True,
        "note": SOURCE,
        "count": len(kept),
        "flows": kept,
    }


def list_destinations(city_label: str, origin: str = "") -> dict:
    data = list_flows(city_label, origin=origin, purpose="travail")
    buckets: dict[str, dict] = {}
    total = sum(item["headcount"] for item in data["flows"]) or 1
    for flow in data["flows"]:
        bucket = buckets.setdefault(
            flow["destination_id"],
            {
                "id": flow["destination_id"],
                "name": flow["destination_name"],
                "parent": flow["destination_parent"],
                "headcount": 0,
            },
        )
        bucket["headcount"] += flow["headcount"]
    rows = sorted(buckets.values(), key=lambda item: item["headcount"], reverse=True)
    for row in rows:
        row["share"] = round(row["headcount"] / total, 3)
    return {
        "city": data["city"],
        "mode": "origine",
        "question": "Où vont les personnes qui habitent dans ce cadre ?",
        "synthetic": True,
        "destinations": rows,
    }


def list_origins(city_label: str, destination: str = "") -> dict:
    data = list_flows(city_label, destination=destination, purpose="travail")
    buckets: dict[str, dict] = {}
    total = sum(item["headcount"] for item in data["flows"]) or 1
    for flow in data["flows"]:
        bucket = buckets.setdefault(
            flow["origin_id"],
            {
                "id": flow["origin_id"],
                "name": flow["origin_name"],
                "parent": flow["origin_parent"],
                "headcount": 0,
            },
        )
        bucket["headcount"] += flow["headcount"]
    rows = sorted(buckets.values(), key=lambda item: item["headcount"], reverse=True)
    for row in rows:
        row["share"] = round(row["headcount"] / total, 3)
    return {
        "city": data["city"],
        "mode": "destination",
        "question": "D'où viennent les personnes qui arrivent dans ce cadre ?",
        "synthetic": True,
        "origins": rows,
    }


def _card(
    *,
    indicator_id: str,
    name: str,
    value: float | int | None,
    unit: str,
    definition: str,
    formula: str,
    interpretation: str,
    limit: str,
) -> dict:
    return {
        "id": indicator_id,
        "name": name,
        "value": value,
        "unit": unit,
        "definition": definition,
        "formula": formula,
        "source": SOURCE,
        "method": METHOD,
        "interpretation": interpretation,
        "limit": limit,
    }


def indicators(city_label: str, zone: str = "", mode: str = "territoire") -> dict:
    city = _city(city_label)
    city_id = city["id"]
    if zone and zone.strip() and _zone_ids(city_id, zone) is None:
        raise ValueError(f"Zone inconnue pour {city['name']} : {zone}")
    scope_name, level, ids = _scope_places(city_id, zone)
    selected = set(ids or [])
    work = _work_groups(city_id)
    city_people = sum(row["headcount"] for row in work) or 1

    if selected:
        residents_rows = [row for row in work if row["origin_id"] in selected]
        job_rows = [row for row in work if row["destination_id"] in selected]
    else:
        residents_rows = work
        job_rows = work

    residents = sum(row["headcount"] for row in residents_rows)
    jobs = sum(row["headcount"] for row in job_rows)
    outside = [
        row
        for row in residents_rows
        if row["destination_id"] not in (selected or {row["origin_id"]})
    ]
    if not selected:
        outside = [row for row in work if row["origin_id"] != row["destination_id"]]
    outbound_people = sum(row["headcount"] for row in outside) if selected else sum(
        row["headcount"] for row in work if row["origin_id"] != row["destination_id"]
    )

    dest_counts: dict[str, int] = defaultdict(int)
    km_sum = 0.0
    car_people = 0
    for row in residents_rows:
        dest_counts[row["destination_id"]] += row["headcount"]
        km_sum += row["km"] * row["headcount"]
        if row["mode"] in {"taxi", "car"}:
            car_people += row["headcount"]
    total_res = residents or 1
    shares = [count / total_res for count in dest_counts.values()] if residents else []
    herfindahl = sum(share * share for share in shares) if shares else None
    top_share = max(shares) if shares else None
    mean_km = round(km_sum / residents, 1) if residents else None
    mean_min = _time_min(mean_km) if mean_km is not None else None
    car_share = round(car_people / residents, 3) if residents else None
    outbound_share = round(outbound_people / residents, 3) if residents else None
    eh_ratio = round(jobs / residents, 2) if residents else None
    eh_balance = None
    if residents + jobs > 0:
        eh_balance = round(1 - abs(jobs - residents) / (jobs + residents), 2)
    imbalance = jobs - residents
    generation = round(residents / city_people, 3)
    attractiveness = round(jobs / city_people, 3)
    dispersion = round(1 - herfindahl, 3) if herfindahl is not None else None
    concentration = round(top_share, 3) if top_share is not None else None
    pressure = None
    if outbound_share is not None and mean_km is not None and car_share is not None:
        pressure = int(
            round(
                100
                * (
                    0.35 * outbound_share
                    + 0.35 * min(mean_km / 25, 1)
                    + 0.30 * car_share
                )
            )
        )

    if eh_ratio is None:
        eh_read = "Pas d'effectif simulé dans ce cadre."
    elif eh_ratio < 0.8:
        eh_read = "Plus d'habitants que d'emplois sur place : les départs domicile-travail sont probables."
    elif eh_ratio > 1.25:
        eh_read = "Plus d'emplois que d'habitants : les arrivées domicile-travail sont probables."
    else:
        eh_read = "Emplois et habitants du cadre sont du même ordre. Cela ne dit pas que les trajets sont courts."

    cards = [
        _card(
            indicator_id="generation",
            name="Indice de génération",
            value=generation,
            unit="part des navetteurs de la ville",
            definition="Part des déplacements domicile-travail de la ville qui partent de ce cadre.",
            formula="habitants qui travaillent et résident dans le cadre / navetteurs de la ville",
            interpretation="Un quartier résidentiel périphérique génère une part élevée s'il loge beaucoup d'employés.",
            limit="Ne compte que les groupes simulés domicile-travail, pas les déplacements occasionnels.",
        ),
        _card(
            indicator_id="attractiveness",
            name="Indice d'attractivité",
            value=attractiveness,
            unit="part des navetteurs de la ville",
            definition="Part des déplacements domicile-travail de la ville qui arrivent dans ce cadre.",
            formula="emplois simulés du cadre / navetteurs de la ville",
            interpretation="Un centre administratif attire une part élevée des arrivées du matin.",
            limit="Dans ce jeu, l'emploi est le siège des organisations, pas un recensement des postes.",
        ),
        _card(
            indicator_id="emploi_habitat",
            name="Indice emploi-habitat",
            value=eh_ratio,
            unit="emplois / habitant actif simulé",
            definition="Rapport entre les emplois du cadre et les actifs qui y résident.",
            formula="emplois du cadre / population active résidente du cadre",
            interpretation=eh_read,
            limit="Facteur territorial parmi d'autres. Il n'explique pas à lui seul les flux.",
        ),
        _card(
            indicator_id="equilibre",
            name="Indice d'équilibre",
            value=eh_balance,
            unit="score de 0 à 1",
            definition="Proximité entre le nombre d'emplois et le nombre d'actifs résidents.",
            formula="1 - |emplois - actifs| / (emplois + actifs)",
            interpretation="Proche de 1 : les deux comptages se rapprochent. Proche de 0 : un seul des deux domine.",
            limit="Un score élevé peut coexister avec de longs trajets si les gens ne travaillent pas sur place.",
        ),
        _card(
            indicator_id="desequilibre",
            name="Déséquilibre territorial",
            value=imbalance,
            unit="personnes (emplois − actifs résidents)",
            definition="Écart signé entre emplois disponibles dans le jeu et actifs qui habitent le cadre.",
            formula="emplois - population active résidente",
            interpretation="Négatif : excédent d'habitants. Positif : excédent d'emplois.",
            limit="Ce n'est pas un solde migratoire ni une file d'attente à l'emploi.",
        ),
        _card(
            indicator_id="concentration",
            name="Concentration des flux",
            value=concentration,
            unit="part vers la destination principale",
            definition="Part des actifs du cadre qui vont vers la même destination.",
            formula="max(effectifs par destination) / actifs résidents",
            interpretation="Une valeur haute désigne un corridor dominant.",
            limit="Calculée sur les groupes simulés, pas sur des individus observés.",
        ),
        _card(
            indicator_id="dispersion",
            name="Indice de dispersion",
            value=dispersion,
            unit="score de 0 à 1",
            definition="Les destinations sont-elles réparties ou concentrées ?",
            formula="1 - somme des parts de destination au carré",
            interpretation="Proche de 0 : une destination absorbe les départs. Plus haut : plusieurs directions.",
            limit="Sensible au découpage en quartiers du catalogue.",
        ),
        _card(
            indicator_id="auto",
            name="Dépendance aux modes individuels motorisés",
            value=car_share,
            unit="part des actifs (taxi ou voiture)",
            definition="Part des actifs du cadre dont le mode simulé est le taxi ou la voiture.",
            formula="actifs en taxi ou voiture / actifs résidents",
            interpretation="Le taxi sert ici de proxy du mode individuel motorisé.",
            limit="Aucun comptage de voitures particulières n'a été fait.",
        ),
        _card(
            indicator_id="distance",
            name="Distance moyenne",
            value=mean_km,
            unit="km",
            definition="Distance moyenne domicile-travail des actifs qui habitent le cadre.",
            formula="somme(distance × effectif) / effectif",
            interpretation="Une périphérie éloignée du siège allonge cette moyenne.",
            limit="Orthodromie × 1,35. Ce n'est pas la distance sur le réseau routier.",
        ),
        _card(
            indicator_id="temps",
            name="Temps moyen estimé",
            value=mean_min,
            unit="minutes",
            definition="Temps moyen d'un trajet domicile-travail, à vitesse urbaine supposée.",
            formula="distance moyenne / 18 km/h",
            interpretation="Ordre de grandeur d'un trajet en heure de pointe, pas une mesure embarquée.",
            limit="La vitesse de 18 km/h est une hypothèse, pas une observation.",
        ),
        _card(
            indicator_id="pression",
            name="Pression de mobilité",
            value=pressure,
            unit="score de 0 à 100",
            definition="Combinaison du taux de sortie, de la distance et du mode motorisé individuel.",
            formula="100 × (0,35 × part qui quitte le cadre + 0,35 × min(km/25, 1) + 0,30 × part taxi ou voiture)",
            interpretation="Un score haut signale un cadre qui envoie loin, et souvent en mode individuel, ses habitants.",
            limit="Les poids sont un choix de lecture, pas une loi physique. À ne pas publier comme un indice officiel.",
        ),
    ]
    return {
        "context": {
            "city": city["name"],
            "scope": scope_name,
            "level": level,
            "mode": mode,
            "period": "jour ouvré",
            "purpose": "travail en priorité",
            "synthetic": True,
        },
        "residents": residents,
        "jobs": jobs,
        "outbound_share": outbound_share,
        "indicators": cards,
        "note": "Estimation simulée. L'indice emploi-habitat est un facteur parmi d'autres, pas la cause unique des déplacements.",
    }


def _scale(rows: list[list[float]]) -> list[list[float]]:
    if not rows:
        return []
    dim = len(rows[0])
    lows = [min(row[d] for row in rows) for d in range(dim)]
    highs = [max(row[d] for row in rows) for d in range(dim)]
    scaled = []
    for row in rows:
        point = []
        for d, value in enumerate(row):
            span = highs[d] - lows[d]
            point.append(0.0 if span == 0 else (value - lows[d]) / span)
        scaled.append(point)
    return scaled


def _kmeans(vectors: list[list[float]], k: int) -> list[int]:
    rng = random.Random(KMEANS_SEED)
    labels = [0] * len(vectors)
    centroids = [vectors[index][:] for index in rng.sample(range(len(vectors)), k)]
    for _ in range(40):
        changed = False
        for index, vector in enumerate(vectors):
            best, best_d = 0, 1e18
            for center, centroid in enumerate(centroids):
                dist = sum((a - b) ** 2 for a, b in zip(vector, centroid))
                if dist < best_d:
                    best, best_d = center, dist
            if labels[index] != best:
                labels[index] = best
                changed = True
        grouped: list[list[list[float]]] = [[] for _ in range(k)]
        for index, label in enumerate(labels):
            grouped[label].append(vectors[index])
        for center, members in enumerate(grouped):
            if not members:
                centroids[center] = vectors[rng.randrange(len(vectors))][:]
                continue
            centroids[center] = [
                sum(member[dim] for member in members) / len(members)
                for dim in range(len(vectors[0]))
            ]
        if not changed:
            break
    return labels


def _silhouette(vectors: list[list[float]], labels: list[int]) -> float | None:
    count = len(vectors)
    if count < 2 or len(set(labels)) < 2:
        return None
    dist = [[0.0] * count for _ in range(count)]
    for left in range(count):
        for right in range(left + 1, count):
            delta = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(vectors[left], vectors[right]))
            )
            dist[left][right] = dist[right][left] = delta
    scores = []
    for index in range(count):
        own = labels[index]
        same = [dist[index][other] for other in range(count) if labels[other] == own and other != index]
        a_mean = sum(same) / len(same) if same else 0.0
        b_mean = None
        for cluster in set(labels):
            if cluster == own:
                continue
            others = [dist[index][other] for other in range(count) if labels[other] == cluster]
            if not others:
                continue
            mean = sum(others) / len(others)
            b_mean = mean if b_mean is None else min(b_mean, mean)
        if b_mean is None:
            continue
        denom = max(a_mean, b_mean)
        scores.append(0.0 if denom == 0 else (b_mean - a_mean) / denom)
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def _cluster_label(mean_km: float, work_name: str) -> str:
    if mean_km < 4:
        return f"Habitent près de {work_name}"
    if mean_km < 9:
        return f"Navette courte vers {work_name}"
    if mean_km >= 14:
        return f"Longue navette vers {work_name}"
    return f"Distance moyenne vers {work_name}"


MODE_SCORE = {"marche": 0.0, "velo": 0.15, "bus": 0.35, "taxi": 0.75, "car": 1.0}


def _profile_units(city_id: str) -> list[dict]:
    """Un point par groupe d'employés : ils partagent distance, mode et fréquence."""
    units = []
    for group in _work_groups(city_id):
        units.append(
            {
                "headcount": int(group["headcount"]),
                "distance_km": float(group["km"]),
                "mode": group["mode"],
                "sector": group["organization_kind"] or "",
                "residence_id": group["origin_id"],
                "work_id": group["destination_id"],
                "company_id": group["organization_id"],
                "vector": [
                    float(group["km"]),
                    MODE_SCORE.get(group["mode"], 0.5),
                    5.0,
                ],
            }
        )
    return units


def clusters(city_label: str) -> dict:
    city = _city(city_label)
    units = _profile_units(city["id"])
    people = sum(unit["headcount"] for unit in units)
    justification = (
        "K-means est retenu : la distance, le mode et la fréquence sont numériques, "
        "et les employés d'un même groupe partagent ces variables. "
        "Le calcul porte donc sur les groupes, et la taille du profil est la somme des effectifs. "
        "k est choisi entre 2 et 4 en maximisant la silhouette, graine 42. "
        "DBSCAN demanderait un rayon sans densité observée. "
        "Le clustering hiérarchique n'apporte pas une lecture plus claire sur ce petit nombre de groupes. "
        "Ce classement décrit des employés simulés, pas des habitants réels."
    )
    empty = {
        "city": city["name"],
        "method": "k-means",
        "justification": justification,
        "k": 0,
        "silhouette": None,
        "seed": KMEANS_SEED,
        "clusters": [],
        "synthetic": True,
        "limit": "Effectif trop faible pour séparer des profils.",
    }
    if people < 20 or len(units) < 2:
        return empty
    scaled = _scale([unit["vector"] for unit in units])
    best_k = 2
    best_score = -1.0
    best_labels: list[int] = []
    upper = 4 if len(units) >= 8 else min(3, len(units))
    for k in range(2, min(upper, len(units)) + 1):
        labels = _kmeans(scaled, k)
        if len(set(labels)) < 2:
            continue
        score = _silhouette(scaled, labels)
        if score is None:
            continue
        if score > best_score:
            best_k = k
            best_score = score
            best_labels = labels
    if not best_labels:
        return empty
    grouped: dict[int, list[dict]] = defaultdict(list)
    for unit, label in zip(units, best_labels):
        grouped[int(label)].append(unit)
    cards = []
    for label, members in sorted(grouped.items(), key=lambda item: -sum(unit["headcount"] for unit in item[1])):
        size = sum(unit["headcount"] for unit in members)
        mean_km = sum(unit["distance_km"] * unit["headcount"] for unit in members) / size
        sectors: dict[str, int] = defaultdict(int)
        homes: dict[str, int] = defaultdict(int)
        works: dict[str, int] = defaultdict(int)
        for unit in members:
            sectors[unit["sector"]] += unit["headcount"]
            homes[unit["residence_id"]] += unit["headcount"]
            works[unit["work_id"]] += unit["headcount"]
        sector = max(sectors, key=sectors.get)
        top_homes = sorted(homes, key=homes.get, reverse=True)[:3]
        top_works = sorted(works, key=works.get, reverse=True)[:2]
        work_name = PLACES[top_works[0]]["name"] if top_works else "leur lieu de travail"
        cards.append(
            {
                "id": int(label),
                "label": _cluster_label(mean_km, work_name),
                "size": size,
                "mean_km": round(mean_km, 1),
                "mean_min": _time_min(mean_km),
                "sector": sector,
                "homes": [
                    {"id": item, "name": PLACES[item]["name"], "headcount": homes[item]}
                    for item in top_homes
                ],
                "works": [
                    {"id": item, "name": PLACES[item]["name"], "headcount": works[item]}
                    for item in top_works
                ],
            }
        )
    return {
        "city": city["name"],
        "method": "k-means",
        "justification": justification,
        "k": best_k,
        "silhouette": None if best_score < 0 else best_score,
        "seed": KMEANS_SEED,
        "clusters": cards,
        "synthetic": True,
        "limit": (
            "Profils de navette domicile-travail uniquement. "
            "Les courses et le culte ne sont pas dans le classement."
        ),
    }


def _company(company_id: str) -> dict:
    found = next((org for org in ORGANIZATIONS if org["id"] == company_id), None)
    if found is None:
        raise ValueError(f"Organisation inconnue : {company_id}")
    return found


def list_companies(city_label: str, kind: str = "") -> dict:
    city = _city(city_label)
    rows = []
    for org in ORGANIZATIONS:
        if org["city_id"] != city["id"]:
            continue
        if kind and kind not in {"all", "toutes"} and org["kind"] != kind:
            continue
        employees = sum(cluster["headcount"] for cluster in org["clusters"])
        seat = PLACES[org["seat_id"]]
        rows.append(
            {
                "id": org["id"],
                "name": org["name"],
                "kind": org["kind"],
                "kind_label": org["kind_label"],
                "city": city["name"],
                "seat_id": org["seat_id"],
                "seat_name": seat["name"],
                "arrondissement": seat["parent_name"],
                "activity": org["activity"],
                "employees": employees,
            }
        )
    rows.sort(key=lambda item: item["employees"], reverse=True)
    return {"city": city["name"], "synthetic": True, "companies": rows}


def company_mobility(company_id: str) -> dict:
    org = _company(company_id)
    city = next(item for item in CITIES if item["id"] == org["city_id"])
    seat = PLACES[org["seat_id"]]
    homes = []
    employees = 0
    km_sum = 0.0
    for cluster in org["clusters"]:
        home = PLACES[cluster["home_id"]]
        distance = _km(home["lon"], home["lat"], seat["lon"], seat["lat"])
        count = int(cluster["headcount"])
        employees += count
        km_sum += distance * count
        homes.append(
            {
                "id": home["id"],
                "name": home["name"],
                "arrondissement": home["parent_name"],
                "headcount": count,
                "mode": cluster["mode"],
                "distance_km": distance,
                "time_min": _time_min(distance),
                "frequency": "5 jours/semaine",
            }
        )
    homes.sort(key=lambda item: item["headcount"], reverse=True)
    for home in homes:
        home["share"] = round(home["headcount"] / employees, 3) if employees else 0
    top = homes[0] if homes else None
    corridor = ""
    if top and top["distance_km"] >= 8:
        corridor = (
            f"Une concentration part de {top['name']} ({top['arrondissement']}) "
            f"vers {seat['name']} : {top['headcount']} employés, {top['distance_km']} km."
        )
    return {
        "city": city["name"],
        "company": {
            "id": org["id"],
            "name": org["name"],
            "kind_label": org["kind_label"],
            "activity": org["activity"],
            "seat_name": seat["name"],
            "arrondissement": seat["parent_name"],
            "employees": employees,
        },
        "mean_km": round(km_sum / employees, 1) if employees else None,
        "homes": homes,
        "corridor": corridor,
        "synthetic": True,
        "note": SOURCE,
    }


def _groups_of(org: dict) -> list[dict]:
    seat = PLACES[org["seat_id"]]
    rows = []
    for cluster in org["clusters"]:
        home = PLACES[cluster["home_id"]]
        distance = _km(home["lon"], home["lat"], seat["lon"], seat["lat"])
        rows.append(
            {
                "home": home,
                "seat": seat,
                "headcount": int(cluster["headcount"]),
                "mode": cluster["mode"],
                "km": distance,
            }
        )
    return rows


def _day_totals(rows: list[dict], km_of, factor) -> dict:
    trips = 0.0
    km = 0.0
    people = 0
    for row in rows:
        weight = row["headcount"] * factor(row)
        people += row["headcount"]
        dist = km_of(row)
        trips += 2 * weight
        km += 2 * weight * dist
    hours = km / SPEED_KMH if km else 0
    return {
        "employees": people,
        "trips_per_working_day": round(trips, 1),
        "km_per_working_day": round(km, 1),
        "hours_per_working_day": round(hours, 1),
        "mean_km": round((km / trips), 1) if trips else 0,
    }


def _best_annex(org: dict, row: dict) -> dict | None:
    if row["km"] < 6:
        return None
    home = row["home"]
    best = None
    for place in places_of(org["city_id"]):
        if place["level"] != "quartier" or place["role"] not in HOST_ROLES:
            continue
        if place["id"] in {home["id"], row["seat"]["id"]}:
            continue
        annex_km = _km(home["lon"], home["lat"], place["lon"], place["lat"])
        gain = round(row["km"] - annex_km, 1)
        if annex_km > 8 or gain < 4:
            continue
        if best is None or gain > best["gain_km"]:
            best = {"place": place, "annex_km": annex_km, "gain_km": gain}
    return best


SCENARIOS = {
    "annex": "Site secondaire plus proche du domicile",
    "decentralize": "Site décentralisé sur le principal bassin d'habitation",
    "telework": "Télétravail partiel pour les longues navettes",
    "collective": "Transport collectif d'organisation",
    "hours": "Décalage des horaires",
}


def simulate_organization(company_id: str, scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"Scénario inconnu. Valeurs : {', '.join(SCENARIOS)}.")
    org = _company(company_id)
    rows = _groups_of(org)
    baseline = _day_totals(rows, lambda row: row["km"], lambda _row: 1)
    moves: list[dict] = []
    relieved: dict[str, int] = defaultdict(int)
    loaded: dict[str, int] = defaultdict(int)

    if scenario == "annex":
        def km_of(row: dict) -> float:
            annex = _best_annex(org, row)
            if annex is None:
                return row["km"]
            moves.append(row)
            relieved[row["seat"]["name"]] += row["headcount"]
            loaded[annex["place"]["name"]] += row["headcount"]
            return annex["annex_km"]

        result = _day_totals(rows, km_of, lambda _row: 1)
        concerned = sum(row["headcount"] for row in moves)
        justification = (
            f"{concerned} employés peuvent être rattachés à un quartier d'accueil "
            "déjà orienté vers l'emploi, à moins de 8 km du domicile et avec au moins 4 km de gain. "
            "L'organisation ne décide pas à leur place : c'est un scénario à chiffrer."
        )
    elif scenario == "decentralize":
        eligible = [row for row in rows if row["km"] >= 8]
        target = max(eligible, key=lambda row: row["headcount"]) if eligible else None

        def km_of(row: dict) -> float:
            if target is None or row["home"]["id"] != target["home"]["id"]:
                return row["km"]
            moves.append(row)
            relieved[row["seat"]["name"]] += row["headcount"]
            loaded[row["home"]["name"]] += row["headcount"]
            return 1.5

        result = _day_totals(rows, km_of, lambda _row: 1)
        concerned = target["headcount"] if target else 0
        where = target["home"]["name"] if target else "aucun quartier"
        justification = (
            f"Le plus grand bassin éloigné est {where} ({concerned} employés). "
            "Un site sur place ramène leur trajet simulé à 1,5 km. "
            "Les autres employés restent au siège."
        )
    elif scenario == "telework":
        def factor(row: dict) -> float:
            if row["km"] < 15:
                return 1
            moves.append(row)
            relieved[row["seat"]["name"]] += row["headcount"]
            return 0.2

        result = _day_totals(rows, lambda row: row["km"], factor)
        concerned = sum(row["headcount"] for row in moves)
        justification = (
            f"{concerned} employés à 15 km ou plus ne viendraient qu'un jour ouvré sur cinq. "
            "Les quatre autres jours, leur navette est évitée dans le scénario. "
            "Le poste doit pouvoir se faire à distance : ce n'est pas vérifié ici."
        )
    elif scenario == "collective":
        result = dict(baseline)
        taxi_people = sum(row["headcount"] for row in rows if row["mode"] == "taxi" and row["headcount"] >= 20)
        bus_people = sum(row["headcount"] for row in rows if row["mode"] == "bus" and row["headcount"] >= 20)
        concerned = taxi_people + bus_people
        avoided = sum(
            row["headcount"] - 1
            for row in rows
            if row["mode"] == "taxi" and row["headcount"] >= 20
        )
        result["vehicle_trips_avoided"] = avoided
        justification = (
            f"{concerned} employés habitent déjà en groupes de 20 ou plus. "
            f"Passer les groupes en taxi à un bus d'organisation éviterait environ {avoided} "
            "véhicules individuels par sens, sans raccourcir la distance parcourue par les personnes. "
            f"{bus_people} employés sont déjà en bus : le gain est alors l'horaire commun, pas les kilomètres."
        )
    else:
        result = {
            **baseline,
            "hours_per_working_day": round(baseline["hours_per_working_day"] * SPEED_KMH / 22, 1),
        }
        concerned = baseline["employees"]
        justification = (
            "Décaler les arrivées hors du pic fait passer la vitesse supposée de 18 à 22 km/h. "
            "La distance ne change pas. Ce n'est pas un modèle de congestion."
        )

    def _drop(before: float, after: float) -> float:
        if before <= 0:
            return 0
        return round((before - after) / before * 100, 1)

    impact = {
        "employees_concerned": concerned,
        "trips_avoided_per_working_day": round(
            baseline["trips_per_working_day"] - result["trips_per_working_day"], 1
        ),
        "km_reduction_pct": _drop(baseline["km_per_working_day"], result["km_per_working_day"]),
        "time_reduction_pct": _drop(
            baseline["hours_per_working_day"], result["hours_per_working_day"]
        ),
        "zones_relieved": [
            {"name": name, "employees": count}
            for name, count in sorted(relieved.items(), key=lambda item: -item[1])
        ],
        "zones_loaded": [
            {"name": name, "employees": count}
            for name, count in sorted(loaded.items(), key=lambda item: -item[1])
        ],
        "vehicle_trips_avoided": result.get("vehicle_trips_avoided"),
    }
    return {
        "synthetic": True,
        "estimation_label": "estimation simulée",
        "company": {"id": org["id"], "name": org["name"], "employees": baseline["employees"]},
        "scenario": {"id": scenario, "label": SCENARIOS[scenario], "justification": justification},
        "baseline": baseline,
        "scenario_result": result,
        "impact": impact,
        "limits": [
            "Estimation simulée : aucune enquête ni badge d'accès n'a été utilisé.",
            "La distance n'est pas calculée sur le graphe routier.",
            "Le scénario ne décide pas. Il chiffre une hypothèse pour la comparer à la situation actuelle.",
            "Les emplois hors travail (courses, culte) ne sont pas dans ce calcul.",
        ],
    }


def quality_report(city_label: str | None = None) -> dict:
    """Contrôles sur le catalogue simulé. Les anomalies bloquantes doivent rester à zéro."""
    cities = CITIES if not city_label else [_city(city_label)]
    anomalies: list[dict] = []
    checked = 0
    missing = 0

    def flag(level: str, code: str, message: str) -> None:
        anomalies.append({"level": level, "code": code, "message": message})

    seen_persons: set[str] = set()
    seen_trips: set[str] = set()
    person_count = 0
    trip_count = 0
    company_count = 0
    for city in cities:
        bbox = city["bbox"]
        company_ids = set()
        for org in ORGANIZATIONS:
            if org["city_id"] != city["id"]:
                continue
            company_count += 1
            company_ids.add(org["id"])
            checked += 4
            if not org["name"] or not org["seat_id"] or not org["city_id"]:
                missing += 1
                flag("erreur", "company-incomplete", f"{org['id']} : champ manquant")
            seat = PLACES.get(org["seat_id"])
            if seat is None:
                flag("erreur", "company-zone", f"{org['name']} : siège sans quartier")
            elif seat["city_id"] != org["city_id"]:
                flag("erreur", "company-city", f"{org['name']} : siège hors de la ville")
        for person in persons_of_city(city["id"]):
            person_count += 1
            checked += 6
            if person["person_id"] in seen_persons:
                flag("erreur", "person-duplicate", person["person_id"])
            seen_persons.add(person["person_id"])
            if not person["company_id"]:
                missing += 1
                flag("erreur", "person-company", f"{person['person_id']} sans organisation")
            elif person["company_id"] not in company_ids:
                flag("erreur", "person-company", f"{person['person_id']} : organisation inconnue")
            for key in ("residence_id", "work_id"):
                place = PLACES.get(person[key])
                if place is None:
                    missing += 1
                    flag("erreur", "person-zone", f"{person['person_id']} : {key} inconnu")
                elif not (bbox[0] <= place["lon"] <= bbox[2] and bbox[1] <= place["lat"] <= bbox[3]):
                    flag("erreur", "coords", f"{place['name']} hors emprise de {city['name']}")
            if person["distance_km"] < 0 or person["time_min"] < 0:
                flag("erreur", "distance", f"{person['person_id']} : distance négative")
            if person["frequency"] not in FREQUENCIES:
                flag("erreur", "frequency", f"{person['person_id']} : fréquence {person['frequency']}")
            if person["residence_id"] == person["work_id"] and person["distance_km"] > 1:
                flag("avertissement", "od", f"{person['person_id']} : même zone mais distance > 1 km")
        for trip in trip_rows(city["id"]):
            trip_count += 1
            checked += 4
            if trip["trip_id"] in seen_trips:
                flag("erreur", "trip-duplicate", trip["trip_id"])
            seen_trips.add(trip["trip_id"])
            if trip["origin_id"] not in PLACES or trip["destination_id"] not in PLACES:
                flag("erreur", "trip-zone", trip["trip_id"])
            if trip["distance_km"] < 0:
                flag("erreur", "distance", trip["trip_id"])
            if trip["frequency"] not in FREQUENCIES:
                flag("erreur", "frequency", trip["trip_id"])
        for person in PERSONS:
            if person["city_id"] != city["id"]:
                continue
            flag(
                "info",
                "journal",
                f"{person['name']} est une fiche de journal, sans effectif d'organisation, hors des totaux.",
            )
    errors = [item for item in anomalies if item["level"] == "erreur"]
    completeness = 1.0 if checked == 0 else round(1 - missing / checked, 3)
    return {
        "synthetic": True,
        "records": {
            "companies": company_count,
            "persons": person_count,
            "trips": trip_count,
            "journal_persons": len(PERSONS) if not city_label else len(
                [person for person in PERSONS if person["city_id"] == cities[0]["id"]]
            ),
        },
        "checked_fields": checked,
        "missing_fields": missing,
        "completeness": completeness,
        "anomalies": anomalies[:40],
        "error_count": len(errors),
        "note": (
            "Contrôle du catalogue simulé avant remplacement par une enquête. "
            "Les fiches de journal sont des exemples, elles ne s'additionnent pas aux organisations."
        ),
    }


def zone_records() -> list[dict]:
    records = []
    for city in CITIES:
        local = places_of(city["id"])
        for place in local:
            if place["level"] == "city":
                continue
            radius = 450.0
            if place["level"] == "commune":
                radius = 700.0
                for child in local:
                    if child["parent_id"] != place["id"]:
                        continue
                    meters = _km(place["lon"], place["lat"], child["lon"], child["lat"]) * 1000 / 1.35
                    radius = max(radius, meters * 1.35)
            geometry = _circle(place["lon"], place["lat"], radius)
            records.append(
                {
                    "id": place["id"],
                    "city_id": city["id"],
                    "name": place["name"],
                    "level": place["level"],
                    "level_label": _level_label(place),
                    "parent_id": place["parent_id"],
                    "role": place.get("role"),
                    "role_label": ROLES.get(place.get("role"), place.get("role")),
                    "lon": place["lon"],
                    "lat": place["lat"],
                    "geometry": geometry,
                }
            )
    return records


def list_arrondissements(city_label: str) -> dict:
    city = _city(city_label)
    rows = [
        record
        for record in zone_records()
        if record["city_id"] == city["id"] and record["level"] == "commune"
    ]
    return {"city": city["name"], "arrondissements": rows}


def list_quartiers(city_label: str, arrondissement: str = "") -> dict:
    city = _city(city_label)
    rows = [
        record
        for record in zone_records()
        if record["city_id"] == city["id"] and record["level"] == "quartier"
    ]
    if arrondissement:
        rows = [row for row in rows if row["parent_id"] == arrondissement]
    return {"city": city["name"], "quartiers": rows}


def zones_geojson(city_label: str) -> dict:
    city = _city(city_label)
    features = []
    for record in zone_records():
        if record["city_id"] != city["id"]:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": record["geometry"],
                "properties": {
                    "id": record["id"],
                    "name": record["name"],
                    "level": record["level"],
                    "level_label": record["level_label"],
                    "parent_id": record["parent_id"],
                    "role": record["role"],
                    "synthetic": True,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "city": city["name"],
        "synthetic": True,
        "note": "Emprises circulaires du catalogue. Ce ne sont pas les limites administratives officielles.",
    }


def seed_payload() -> dict:
    """Lignes prêtes à écrire dans PostGIS. Le calcul reste dans ce module."""
    companies = []
    persons = []
    trips = []
    indicator_rows = []
    cluster_rows = []
    for city in CITIES:
        for org in ORGANIZATIONS:
            if org["city_id"] != city["id"]:
                continue
            companies.append(
                {
                    "id": org["id"],
                    "name": org["name"],
                    "kind": org["kind"],
                    "kind_label": org["kind_label"],
                    "city_id": city["id"],
                    "seat_id": org["seat_id"],
                    "activity": org["activity"],
                    "employee_count": sum(cluster["headcount"] for cluster in org["clusters"]),
                }
            )
        persons.extend(persons_of_city(city["id"]))
        trips.extend(trip_rows(city["id"]))
        pack = indicators(city["name"])
        for card in pack["indicators"]:
            indicator_rows.append(
                {
                    "city_id": city["id"],
                    "zone_id": city["id"],
                    "indicator_id": card["id"],
                    "value": card["value"],
                    "unit": card["unit"],
                }
            )
        for place in places_of(city["id"]):
            if place["level"] not in {"commune", "quartier"}:
                continue
            local = indicators(city["name"], zone=place["id"])
            for card in local["indicators"]:
                indicator_rows.append(
                    {
                        "city_id": city["id"],
                        "zone_id": place["id"],
                        "indicator_id": card["id"],
                        "value": card["value"],
                        "unit": card["unit"],
                    }
                )
        grouped = clusters(city["name"])
        cards = grouped["clusters"]
        for person in persons_of_city(city["id"]):
            chosen = None
            best = 1e9
            for card in cards:
                if person["residence_id"] not in {home["id"] for home in card["homes"]}:
                    continue
                gap = abs(float(person["distance_km"]) - float(card["mean_km"]))
                if gap < best:
                    best = gap
                    chosen = card
            if chosen is None and cards:
                chosen = min(cards, key=lambda card: abs(float(person["distance_km"]) - float(card["mean_km"])))
            if chosen is None:
                continue
            cluster_rows.append(
                {
                    "person_id": person["person_id"],
                    "city_id": city["id"],
                    "cluster_id": chosen["id"],
                    "cluster_label": chosen["label"],
                }
            )
    return {
        "zones": zone_records(),
        "companies": companies,
        "persons": persons,
        "trips": trips,
        "indicators": indicator_rows,
        "clusters": cluster_rows,
    }
