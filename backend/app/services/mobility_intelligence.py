"""
Analyse des profils de mobilité sur des groupes déjà agrégés.

Chaque point du clustering est un groupe d'employés simulés qui partagent
origine, destination, distance, mode et fréquence. L'organisation est lue
à part : la mettre dans le vecteur collerait un groupe par organisme.

Les scénarios sont des hypothèses chiffrées. Ils ne sont pas une solution
optimale certaine.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

from app.data.organizations import ORGANIZATIONS
from app.data.territory import CITIES, PLACES, places_of
from app.services.lens import _km, resolve_city

SPEED_KMH = 18.0
KMEANS_SEED = 42
EXAMPLE_ORG_ID = "exemple-bassin-nord"
SOURCE = (
    "Groupes d'employés simulés (au moins 20 personnes par quartier). "
    "Aucune enquête ménage ni badge d'accès."
)

MODE_SCORE = {"marche": 0.0, "velo": 0.2, "bus": 0.45, "taxi": 0.8, "car": 1.0}
SECTOR_SCORE = {
    "ministere": 0.0,
    "universite": 0.25,
    "sante": 0.5,
    "commerce": 0.75,
    "entreprise": 1.0,
}
# kg CO₂ / voyageur-km — mêmes ordres de grandeur que le tableau de bord.
CO2_KG_PER_PKM = {"marche": 0.0, "velo": 0.0, "bus": 0.08, "taxi": 0.18, "car": 0.18}

PROFILE_TITLES = {
    "peripherie_centre": "Périphérie → centre",
    "proche": "Résidence proche de l'emploi",
    "convergence": "Plusieurs zones résidentielles → même pôle d'emploi",
}


def _status(recommended: bool) -> dict:
    if recommended:
        return {
            "status": "scenario_recommande",
            "status_label": "scénario recommandé",
        }
    return {
        "status": "scenario_potentiellement_pertinent",
        "status_label": "scénario potentiellement pertinent",
    }


def _round1(value: float) -> float:
    return round(value, 1)


def _co2(mode: str) -> float:
    return CO2_KG_PER_PKM.get(mode, 0.12)


def _groups(city_id: str) -> list[dict]:
    city = next(item for item in CITIES if item["id"] == city_id)
    rows = []
    for org in ORGANIZATIONS:
        if org["city_id"] != city_id:
            continue
        seat = PLACES[org["seat_id"]]
        for cluster in org["clusters"]:
            home = PLACES[cluster["home_id"]]
            distance = _km(home["lon"], home["lat"], seat["lon"], seat["lat"])
            rows.append(
                {
                    "organization_id": org["id"],
                    "organization_name": org["name"],
                    "sector": org["kind"],
                    "sector_label": org["kind_label"],
                    "activity": org["activity"],
                    "example": org["id"] == EXAMPLE_ORG_ID,
                    "home": home,
                    "seat": seat,
                    "headcount": int(cluster["headcount"]),
                    "mode": cluster["mode"],
                    "km": distance,
                    "frequency_days": 5.0,
                    "vector": [
                        float(home["lon"]),
                        float(home["lat"]),
                        float(seat["lon"]),
                        float(seat["lat"]),
                        float(distance),
                        5.0,
                        MODE_SCORE.get(cluster["mode"], 0.5),
                        SECTOR_SCORE.get(org["kind"], 0.5),
                    ],
                    "city_lon": city["lon"],
                    "city_lat": city["lat"],
                }
            )
    return rows


def _tag(group: dict) -> str:
    if group["km"] < 4:
        return "proche"
    home_centre = _km(
        group["home"]["lon"], group["home"]["lat"], group["city_lon"], group["city_lat"]
    )
    work_centre = _km(
        group["seat"]["lon"], group["seat"]["lat"], group["city_lon"], group["city_lat"]
    )
    if group["km"] >= 8 and home_centre >= work_centre + 3:
        return "peripherie_centre"
    return "intermediaire"


def _scale(rows: list[list[float]]) -> list[list[float]]:
    if not rows:
        return []
    width = len(rows[0])
    lows = [min(row[dim] for row in rows) for dim in range(width)]
    highs = [max(row[dim] for row in rows) for dim in range(width)]
    scaled = []
    for row in rows:
        point = []
        for dim, value in enumerate(row):
            span = highs[dim] - lows[dim]
            point.append(0.0 if span == 0 else (value - lows[dim]) / span)
        scaled.append(point)
    return scaled


def _euclidean(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _pairwise(vectors: list[list[float]]) -> list[list[float]]:
    count = len(vectors)
    dist = [[0.0] * count for _ in range(count)]
    for left in range(count):
        for right in range(left + 1, count):
            delta = _euclidean(vectors[left], vectors[right])
            dist[left][right] = dist[right][left] = delta
    return dist


def _silhouette(vectors: list[list[float]], labels: list[int]) -> float | None:
    usable = [label for label in labels if label >= 0]
    if len(usable) < 3 or len(set(usable)) < 2:
        return None
    dist = _pairwise(vectors)
    scores = []
    for index, own in enumerate(labels):
        if own < 0:
            continue
        same = [
            dist[index][other]
            for other, label in enumerate(labels)
            if label == own and other != index
        ]
        if not same:
            continue
        a_mean = sum(same) / len(same)
        b_mean = None
        for cluster in set(usable):
            if cluster == own:
                continue
            others = [
                dist[index][other]
                for other, label in enumerate(labels)
                if label == cluster
            ]
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


def _ward(vectors: list[list[float]], k: int) -> list[int]:
    clusters: list[set[int]] = [{index} for index in range(len(vectors))]
    while len(clusters) > k:
        means = []
        for cluster in clusters:
            members = [vectors[index] for index in cluster]
            means.append(
                [
                    sum(member[dim] for member in members) / len(members)
                    for dim in range(len(vectors[0]))
                ]
            )
        best = None
        best_d = 1e18
        for left in range(len(clusters)):
            for right in range(left + 1, len(clusters)):
                size_left = len(clusters[left])
                size_right = len(clusters[right])
                gap = _euclidean(means[left], means[right])
                dist = math.sqrt(2 * size_left * size_right / (size_left + size_right)) * gap
                if dist < best_d:
                    best = (left, right)
                    best_d = dist
        if best is None:
            break
        left, right = best
        clusters[left] = clusters[left] | clusters[right]
        del clusters[right]
    labels = [0] * len(vectors)
    for cluster_id, cluster in enumerate(clusters):
        for index in cluster:
            labels[index] = cluster_id
    return labels


def _dbscan(vectors: list[list[float]], eps: float, min_samples: int) -> list[int]:
    count = len(vectors)
    dist = _pairwise(vectors)
    neighbors = [
        [other for other in range(count) if other != index and dist[index][other] <= eps]
        for index in range(count)
    ]
    labels = [-1] * count
    visited = [False] * count
    cluster_id = 0
    for index in range(count):
        if visited[index]:
            continue
        visited[index] = True
        if len(neighbors[index]) + 1 < min_samples:
            continue
        labels[index] = cluster_id
        seeds = list(neighbors[index])
        cursor = 0
        while cursor < len(seeds):
            point = seeds[cursor]
            cursor += 1
            if not visited[point]:
                visited[point] = True
                if len(neighbors[point]) + 1 >= min_samples:
                    for other in neighbors[point]:
                        if other not in seeds:
                            seeds.append(other)
            if labels[point] == -1:
                labels[point] = cluster_id
        cluster_id += 1
    return labels


def _pack_method(
    method: str,
    label: str,
    labels: list[int],
    vectors: list[list[float]],
    *,
    k: int | None = None,
    eps: float | None = None,
    min_samples: int | None = None,
) -> dict:
    noise = sum(1 for item in labels if item < 0)
    cluster_ids = {item for item in labels if item >= 0}
    score = _silhouette(vectors, labels)
    noise_share = round(noise / len(labels), 3) if labels else 1
    eligible = (
        score is not None
        and 2 <= len(cluster_ids) <= 4
        and noise_share <= 0.35
    )
    return {
        "method": method,
        "label": label,
        "k": k if k is not None else len(cluster_ids),
        "eps": eps,
        "min_samples": min_samples,
        "silhouette": score,
        "clusters": len(cluster_ids),
        "noise_share": noise_share,
        "eligible": eligible,
        "labels": labels,
    }


def _best_k(vectors: list[list[float]], assign) -> tuple[list[int], int, float | None]:
    best_labels: list[int] = []
    best_k = 2
    best_score = -1.0
    upper = min(4, len(vectors) - 1)
    for k in range(2, upper + 1):
        labels = assign(vectors, k)
        if len(set(labels)) < 2:
            continue
        score = _silhouette(vectors, labels)
        if score is None:
            continue
        if score > best_score:
            best_k = k
            best_score = score
            best_labels = labels
    if not best_labels:
        return [0] * len(vectors), 1, None
    return best_labels, best_k, round(best_score, 3)


def _compare(vectors: list[list[float]]) -> tuple[dict, list[dict]]:
    k_labels, k_value, _k_score = _best_k(vectors, _kmeans)
    ward_labels, ward_k, _ward_score = _best_k(vectors, _ward)
    kmeans = _pack_method(
        "k-means",
        "K-means",
        k_labels,
        vectors,
        k=k_value,
    )
    ward = _pack_method(
        "hierarchique",
        "Clustering hiérarchique (Ward)",
        ward_labels,
        vectors,
        k=ward_k,
    )
    db_best = None
    for eps in (0.28, 0.40, 0.55, 0.75):
        for min_samples in (2, 3):
            labels = _dbscan(vectors, eps, min_samples)
            packed = _pack_method(
                "dbscan",
                "DBSCAN",
                labels,
                vectors,
                eps=eps,
                min_samples=min_samples,
            )
            if db_best is None:
                db_best = packed
                continue
            if packed["eligible"] and not db_best["eligible"]:
                db_best = packed
            elif packed["eligible"] == db_best["eligible"]:
                left = packed["silhouette"] if packed["silhouette"] is not None else -1
                right = db_best["silhouette"] if db_best["silhouette"] is not None else -1
                if left > right:
                    db_best = packed
    assert db_best is not None
    candidates = [kmeans, ward, db_best]
    eligible = [item for item in candidates if item["eligible"]]
    pool = eligible or candidates
    chosen = max(
        pool,
        key=lambda item: item["silhouette"] if item["silhouette"] is not None else -1,
    )
    kmeans_score = kmeans["silhouette"] if kmeans["silhouette"] is not None else -1
    chosen_score = chosen["silhouette"] if chosen["silhouette"] is not None else -1
    if kmeans["eligible"] and chosen_score - kmeans_score <= 0.02:
        chosen = kmeans
    return chosen, candidates


def _why_method(chosen: dict, candidates: list[dict]) -> str:
    by_method = {item["method"]: item for item in candidates}
    kmeans = by_method["k-means"]
    ward = by_method["hierarchique"]
    dbscan = by_method["dbscan"]

    def _score(item: dict) -> str:
        if item["silhouette"] is None:
            return "silhouette non calculable"
        return f"silhouette {item['silhouette']}"

    def _value(item: dict) -> float:
        if item["silhouette"] is None:
            return -1.0
        return float(item["silhouette"])

    scores = (
        f"Sur les mêmes vecteurs mis à l'échelle : "
        f"K-means k={kmeans['k']} ({_score(kmeans)}, {kmeans['clusters']} groupes) ; "
        f"Ward k={ward['k']} ({_score(ward)}, {ward['clusters']} groupes) ; "
        f"DBSCAN eps={dbscan['eps']}, minPts={dbscan['min_samples']} "
        f"({_score(dbscan)}, {dbscan['clusters']} groupes, "
        f"{round(dbscan['noise_share'] * 100)} % de bruit)."
    )
    db_close = dbscan["eligible"] and abs(_value(chosen) - _value(dbscan)) <= 0.02
    parts = [scores]
    if chosen["method"] == "k-means":
        parts.append(
            "K-means est retenu. Les variables sont numériques "
            "(position d'origine, position de destination, distance, fréquence, mode, secteur) "
            "et chaque point est déjà un groupe, pas une trace GPS. "
            "La graine 42 rend le découpage reproductible."
        )
        if ward["eligible"] and _value(chosen) + 0.02 >= _value(ward):
            parts.append(
                f"Ward ({_score(ward)}) ne dépasse pas K-means de plus de 0,02 : "
                "l'écart ne justifie pas de changer de méthode."
            )
        if not dbscan["eligible"]:
            parts.append(
                "DBSCAN n'est pas retenu. Il cherche une densité : "
                f"le meilleur essai (eps={dbscan['eps']}, minPts={dbscan['min_samples']}) "
                f"laisse {round(dbscan['noise_share'] * 100)} % de bruit "
                "ou ne donne pas entre 2 et 4 profils."
            )
        elif db_close:
            parts.append(
                "DBSCAN atteint un score proche, mais eps est une grille d'essais, "
                "pas une distance observée. Il n'y a pas ici de nuage de traces GPS."
            )
    elif chosen["method"] == "hierarchique":
        parts.append(
            "Le clustering hiérarchique de Ward est retenu : sa silhouette dépasse "
            "K-means de plus de 0,02. Les navettes s'emboîtent (courtes, puis longues) "
            "mieux qu'en paquets sphériques."
        )
        if db_close:
            parts.append(
                f"DBSCAN est au même niveau ({_score(dbscan)}, "
                f"{round(dbscan['noise_share'] * 100)} % de bruit, "
                f"eps={dbscan['eps']}, minPts={dbscan['min_samples']}). "
                "Il n'est pas retenu : ces points sont des groupes déjà agrégés, "
                "pas une densité de traces, et le rayon eps est cherché. "
                "Ward n'a pas besoin d'une classe de bruit."
            )
        elif not dbscan["eligible"]:
            parts.append(
                "DBSCAN n'est pas retenu : trop de bruit, ou un nombre de groupes hors de 2 à 4."
            )
    else:
        parts.append(
            "DBSCAN est retenu : des groupes denses se séparent du reste, "
            "avec une part de bruit inférieure à 35 % et 2 à 4 agrégats. "
            "Ce cas est rare sur des effectifs déjà agrégés ; le paramètre eps reste une hypothèse."
        )
    if not chosen["eligible"]:
        parts.append("La séparation est faible : le classement est indicatif.")
    return " ".join(parts)


def _cluster_cards(groups: list[dict], labels: list[int]) -> list[dict]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for group, label in zip(groups, labels):
        if label < 0:
            continue
        grouped[int(label)].append(group)
    cards = []
    for label, members in sorted(
        grouped.items(),
        key=lambda item: -sum(group["headcount"] for group in item[1]),
    ):
        size = sum(group["headcount"] for group in members)
        mean_km = sum(group["km"] * group["headcount"] for group in members) / size
        tags: dict[str, int] = defaultdict(int)
        homes: dict[str, int] = defaultdict(int)
        works: dict[str, int] = defaultdict(int)
        for group in members:
            tags[_tag(group)] += group["headcount"]
            homes[group["home"]["id"]] += group["headcount"]
            works[group["seat"]["id"]] += group["headcount"]
        dominant = max(tags, key=tags.get)
        title = {
            "proche": "Résidence proche de l'emploi",
            "peripherie_centre": "Périphérie → centre",
        }.get(dominant, "Navette intermédiaire")
        cards.append(
            {
                "id": int(label),
                "label": title,
                "profile": dominant,
                "size": size,
                "mean_km": _round1(mean_km),
                "mean_min": int(round(mean_km / SPEED_KMH * 60)),
                "homes": [
                    {"id": item, "name": PLACES[item]["name"], "headcount": homes[item]}
                    for item in sorted(homes, key=homes.get, reverse=True)[:4]
                ],
                "works": [
                    {"id": item, "name": PLACES[item]["name"], "headcount": works[item]}
                    for item in sorted(works, key=works.get, reverse=True)[:2]
                ],
            }
        )
    return cards


def _place_brief(place: dict, headcount: int, km: float | None = None) -> dict:
    row = {
        "id": place["id"],
        "name": place["name"],
        "parent": place.get("parent_name"),
        "headcount": headcount,
    }
    if km is not None:
        row["distance_km"] = km
    return row


def _profiles(groups: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {"peripherie_centre": [], "proche": []}
    for group in groups:
        tag = _tag(group)
        if tag in buckets:
            buckets[tag].append(group)
    cards = []
    readings = {
        "peripherie_centre": (
            "Domicile éloigné du centre, lieu de travail plus central, distance élevée. "
            "Lecture des groupes simulés, pas un classement d'individus."
        ),
        "proche": (
            "Le quartier de résidence et le lieu de travail sont proches. "
            "La distance simulée reste inférieure à 4 km."
        ),
    }
    for key in ("peripherie_centre", "proche"):
        members = buckets[key]
        people = sum(group["headcount"] for group in members)
        homes: dict[str, int] = defaultdict(int)
        works: dict[str, int] = defaultdict(int)
        for group in members:
            homes[group["home"]["id"]] += group["headcount"]
            works[group["seat"]["id"]] += group["headcount"]
        mean_km = (
            sum(group["km"] * group["headcount"] for group in members) / people if people else None
        )
        cards.append(
            {
                "id": key,
                "title": PROFILE_TITLES[key],
                "people": people,
                "mean_km": None if mean_km is None else _round1(mean_km),
                "reading": readings[key],
                "homes": [
                    _place_brief(PLACES[item], homes[item])
                    for item in sorted(homes, key=homes.get, reverse=True)[:5]
                ],
                "works": [
                    _place_brief(PLACES[item], works[item])
                    for item in sorted(works, key=works.get, reverse=True)[:4]
                ],
            }
        )
    return cards


def _convergences(groups: list[dict]) -> list[dict]:
    by_org: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        by_org[group["organization_id"]].append(group)
    rows = []
    for members in by_org.values():
        homes = {group["home"]["id"] for group in members}
        if len(homes) < 3:
            continue
        people = sum(group["headcount"] for group in members)
        seat = members[0]["seat"]
        mean_km = sum(group["km"] * group["headcount"] for group in members) / people
        rows.append(
            {
                "organization_id": members[0]["organization_id"],
                "organization_name": members[0]["organization_name"],
                "example": members[0]["example"],
                "people": people,
                "home_zones": len(homes),
                "mean_km": _round1(mean_km),
                "work": {"id": seat["id"], "name": seat["name"]},
                "homes": [
                    _place_brief(group["home"], group["headcount"], group["km"])
                    for group in sorted(members, key=lambda item: -item["headcount"])
                ],
            }
        )
    rows.sort(key=lambda item: (item["example"], item["home_zones"], item["people"]), reverse=True)
    return rows


def _bearing(origin: dict, dest: dict) -> float:
    lon1, lat1 = math.radians(origin["lon"]), math.radians(origin["lat"])
    lon2, lat2 = math.radians(dest["lon"]), math.radians(dest["lat"])
    dlon = lon1 - lon2
    y_value = math.sin(dlon) * math.cos(lat1)
    x_value = math.cos(lat2) * math.sin(lat1) - math.sin(lat2) * math.cos(lat1) * math.cos(dlon)
    return (math.degrees(math.atan2(y_value, x_value)) + 360) % 360


def _join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return names[0] if names else ""
    if len(names) == 2:
        return f"{names[0]} et {names[1]}"
    return ", ".join(names[:-1]) + " et " + names[-1]


def _angular_bundles(origins: list[dict]) -> list[list[dict]]:
    if not origins:
        return []
    ordered = sorted(origins, key=lambda item: item["bearing"])
    bundles = [[ordered[0]]]
    for item in ordered[1:]:
        if item["bearing"] - bundles[-1][-1]["bearing"] <= 40:
            bundles[-1].append(item)
        else:
            bundles.append([item])
    if len(bundles) > 1:
        gap = (bundles[0][0]["bearing"] + 360) - bundles[-1][-1]["bearing"]
        if gap <= 40:
            bundles[0] = bundles[-1] + bundles[0]
            bundles.pop()
    return bundles


def _detections(groups: list[dict]) -> dict:
    inbound: dict[str, int] = defaultdict(int)
    outbound: dict[str, int] = defaultdict(int)
    origins_of: dict[str, set[str]] = defaultdict(set)
    km_out: dict[str, float] = defaultdict(float)
    by_dest: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        inbound[group["seat"]["id"]] += group["headcount"]
        outbound[group["home"]["id"]] += group["headcount"]
        origins_of[group["seat"]["id"]].add(group["home"]["id"])
        km_out[group["home"]["id"]] += group["km"] * group["headcount"]
        by_dest[group["seat"]["id"]].append(group)

    nodes = []
    for dest_id, people in inbound.items():
        if people < 50 or len(origins_of[dest_id]) < 3:
            continue
        place = PLACES[dest_id]
        nodes.append(
            {
                "id": dest_id,
                "name": place["name"],
                "people": people,
                "origin_zones": len(origins_of[dest_id]),
                "reading": (
                    f"{people} employés simulés arrivent à {place['name']} "
                    f"depuis {len(origins_of[dest_id])} quartiers."
                ),
            }
        )
    nodes.sort(key=lambda item: -item["people"])

    corridors = []
    for dest_id, members in by_dest.items():
        far = [group for group in members if group["km"] >= 6]
        pointed = []
        for group in far:
            pointed.append({**group, "bearing": _bearing(group["home"], group["seat"])})
        for bundle in _angular_bundles(pointed):
            people = sum(group["headcount"] for group in bundle)
            zone_ids = {group["home"]["id"] for group in bundle}
            if people < 40 or len(zone_ids) < 2:
                continue
            names = []
            seen = set()
            for group in sorted(bundle, key=lambda item: -item["headcount"]):
                if group["home"]["id"] in seen:
                    continue
                seen.add(group["home"]["id"])
                names.append(group["home"]["name"])
            dest = PLACES[dest_id]
            mean_km = sum(group["km"] * group["headcount"] for group in bundle) / people
            by_home: dict[str, dict] = {}
            for group in bundle:
                slot = by_home.setdefault(
                    group["home"]["id"],
                    {"place": group["home"], "headcount": 0},
                )
                slot["headcount"] += group["headcount"]
            origins = [
                {
                    "id": home_id,
                    "name": slot["place"]["name"],
                    "lon": slot["place"]["lon"],
                    "lat": slot["place"]["lat"],
                    "headcount": slot["headcount"],
                }
                for home_id, slot in sorted(by_home.items(), key=lambda item: -item[1]["headcount"])
            ]
            corridors.append(
                {
                    "destination_id": dest_id,
                    "destination_name": dest["name"],
                    "destination": {
                        "id": dest_id,
                        "name": dest["name"],
                        "lon": dest["lon"],
                        "lat": dest["lat"],
                    },
                    "origins": origins,
                    "people": people,
                    "origin_zones": len(zone_ids),
                    "mean_km": _round1(mean_km),
                    "label": f"{_join_names(names[:4])} → {dest['name']}",
                }
            )
    corridors.sort(key=lambda item: -item["people"])

    generation = []
    attraction = []
    deserts = []
    imbalances = []
    zone_ids = set(outbound) | set(inbound)
    for zone_id in zone_ids:
        place = PLACES[zone_id]
        residents = outbound[zone_id]
        jobs = inbound[zone_id]
        total = residents + jobs
        if residents >= 40:
            generation.append(
                {
                    "id": zone_id,
                    "name": place["name"],
                    "people": residents,
                    "mean_km": _round1(km_out[zone_id] / residents) if residents else None,
                }
            )
        if jobs >= 50:
            attraction.append({"id": zone_id, "name": place["name"], "people": jobs})
        mean_km = (km_out[zone_id] / residents) if residents else 0
        if residents >= 20 and jobs == 0 and mean_km >= 10:
            deserts.append(
                {
                    "id": zone_id,
                    "name": place["name"],
                    "people": residents,
                    "mean_km": _round1(mean_km),
                    "reading": (
                        f"{place['name']} envoie {residents} employés simulés "
                        f"à { _round1(mean_km) } km en moyenne, sans siège d'organisation dans le jeu."
                    ),
                }
            )
        if total >= 40:
            score = round(1 - abs(jobs - residents) / total, 2)
            if score < 0.45:
                kind = "excédent d'habitat" if residents > jobs else "excédent d'emplois"
                imbalances.append(
                    {
                        "id": zone_id,
                        "name": place["name"],
                        "residents": residents,
                        "jobs": jobs,
                        "eh_index": score,
                        "kind": kind,
                    }
                )
    generation.sort(key=lambda item: -item["people"])
    attraction.sort(key=lambda item: -item["people"])
    deserts.sort(key=lambda item: -item["people"])
    imbalances.sort(key=lambda item: item["eh_index"])
    return {
        "critical_nodes": nodes[:6],
        "corridors": corridors[:6],
        "generation_zones": generation[:6],
        "attraction_zones": attraction[:6],
        "mobility_deserts": deserts[:6],
        "emploi_habitat_imbalances": imbalances[:6],
        "thresholds": {
            "critical_node": "au moins 50 arrivées et 3 quartiers d'origine",
            "corridor": "au moins 2 origines dans un secteur de 40°, 40 personnes, 6 km ou plus",
            "generation": "au moins 40 départs domicile-travail",
            "attraction": "au moins 50 arrivées",
            "desert": "au moins 20 départs, aucun emploi simulé sur place, 10 km ou plus",
            "imbalance": "indice emploi-habitat inférieur à 0,45 et au moins 40 personnes",
        },
    }


def _limits(*extra: str) -> list[str]:
    base = [
        "Estimation simulée : aucune enquête n'a été collectée.",
        "La distance est une orthodromie × 1,35, pas un itinéraire pgRouting.",
        "Le CO₂ utilise 0,08 kg/voyageur-km en bus et 0,18 en taxi ou voiture. Ce sont des ordres de grandeur.",
        "Ce scénario est isolé : il ne s'additionne pas aux autres.",
        "Ce n'est pas une décision. L'organisation peut l'écarter.",
    ]
    return [*extra, *base]


def _impact(
    *,
    people: int,
    km_saved: float,
    trips_reduced: float,
    co2_saved: float,
    assumptions: str,
    time_saved_h: float | None = None,
) -> dict:
    if time_saved_h is None:
        minutes = km_saved / SPEED_KMH * 60 if km_saved else 0
    else:
        minutes = time_saved_h * 60
    return {
        "people_concerned": people,
        "distance_saved_km_per_working_day": _round1(km_saved),
        "time_saved_min_per_person": int(round(minutes / people)) if people else 0,
        "time_saved_h_per_working_day": _round1(minutes / 60),
        "trips_reduced_per_working_day": _round1(trips_reduced),
        "co2_saved_kg_per_working_day": _round1(co2_saved),
        "assumptions": assumptions,
    }


def _scenario(
    *,
    kind: str,
    title: str,
    recommended: bool,
    why: str,
    data: str,
    people: int,
    km_saved: float,
    trips_reduced: float,
    co2_saved: float,
    assumptions: str,
    limits: list[str],
    organization_id: str | None = None,
    site_name: str | None = None,
    time_saved_h: float | None = None,
    groups: list[dict] | None = None,
    site: dict | None = None,
    seat: dict | None = None,
    example: bool = False,
) -> dict:
    row = {
        "kind": kind,
        "title": title,
        "synthetic": True,
        "example": example,
        "organization_id": organization_id,
        "site_name": site_name,
        **_status(recommended),
        "why": why,
        "data": data,
        "impact": _impact(
            people=people,
            km_saved=km_saved,
            trips_reduced=trips_reduced,
            co2_saved=co2_saved,
            assumptions=assumptions,
            time_saved_h=time_saved_h,
        ),
        "limits": limits,
    }
    if groups:
        row["groups"] = groups
    if site:
        row["site"] = site
    if seat:
        row["seat"] = seat
    return row


def _best_satellite(city_id: str, members: list[dict]) -> dict | None:
    seat_id = members[0]["seat"]["id"]
    quartiers = [
        place
        for place in places_of(city_id)
        if place["level"] == "quartier" and place["id"] != seat_id
    ]
    best = None
    for place in quartiers:
        moved = []
        saved_km = 0.0
        for group in members:
            new_km = _km(group["home"]["lon"], group["home"]["lat"], place["lon"], place["lat"])
            gain = group["km"] - new_km
            if gain < 4:
                continue
            moved.append({**group, "new_km": new_km, "gain": gain})
            saved_km += gain * group["headcount"]
        if not moved or saved_km <= 0:
            continue
        if best is None or saved_km > best["saved_person_km"]:
            best = {"place": place, "moved": moved, "saved_person_km": saved_km}
    return best


def _satellite_scenario(city_id: str, members: list[dict], *, force: bool = False) -> dict | None:
    found = _best_satellite(city_id, members)
    if found is None:
        return None
    moved = found["moved"]
    people = sum(group["headcount"] for group in moved)
    homes = {group["home"]["id"] for group in moved}
    if people < 1 or ((people < 20 or len(homes) < 2) and not force):
        return None
    km_saved = 2 * found["saved_person_km"]
    baseline = 2 * sum(group["km"] * group["headcount"] for group in moved)
    share = km_saved / baseline if baseline else 0
    co2_saved = sum(2 * group["gain"] * group["headcount"] * _co2(group["mode"]) for group in moved)
    ordered = sorted(moved, key=lambda item: -item["headcount"])
    names = _join_names(
        [f"{group['headcount']} à {group['home']['name']}" for group in ordered]
    )
    seat_place = members[0]["seat"]
    seat = seat_place["name"]
    site_place = found["place"]
    site = site_place["name"]
    org_name = members[0]["organization_name"]
    recommended = people >= 50 and len(homes) >= 3 and share >= 0.25
    onsite = sum(group["headcount"] for group in moved if group["new_km"] < 1)
    onsite_text = ""
    if onsite:
        onsite_text = (
            f" {onsite} personnes habitent déjà {site} : "
            f"pour elles, la navette vers {seat} disparaît dans ce scénario."
        )
    detail = [
        {
            "home": group["home"]["name"],
            "home_id": group["home"]["id"],
            "lon": group["home"]["lon"],
            "lat": group["home"]["lat"],
            "headcount": group["headcount"],
            "mode": group["mode"],
            "before_km": group["km"],
            "after_km": _round1(group["new_km"]),
            "saved_km_per_working_day": _round1(2 * group["gain"] * group["headcount"]),
        }
        for group in ordered
    ]
    return _scenario(
        kind="bureau_satellite",
        title=f"Bureau satellite à {site}",
        recommended=recommended,
        example=members[0]["organization_id"] == EXAMPLE_ORG_ID,
        why=(
            f"{org_name} concentre {names}, tous vers {seat}. "
            f"Un site à {site} raccourcirait ces navettes d'au moins 4 km par trajet."
            f"{onsite_text} "
            f"C'est un {('scénario recommandé' if recommended else 'scénario potentiellement pertinent')} "
            "à chiffrer, pas une implantation décidée."
        ),
        data=(
            f"{SOURCE} Organisation {org_name}. "
            f"Groupes : {names}. Siège actuel : {seat}."
        ),
        people=people,
        km_saved=km_saved,
        trips_reduced=2 * people,
        co2_saved=co2_saved,
        assumptions=(
            "Aller-retour ouvré. Les trajets longs vers le siège sont remplacés "
            "par le trajet vers le site proposé. Les employés qui n'y gagnent pas 4 km restent au siège. "
            "Vitesse supposée 18 km/h."
        ),
        limits=_limits(
            "Le site est le quartier du catalogue qui réduit le plus les kilomètres, pas une parcelle disponible.",
            "Les déplacements comptés comme réduits sont les allers-retours vers le siège d'origine. "
            "Un trajet court vers le satellite reste.",
            "La distance économisée est une somme de voyageurs-km, pas la longueur d'un seul axe.",
        ),
        organization_id=members[0]["organization_id"],
        site_name=site,
        groups=detail,
        site={"id": site_place["id"], "name": site, "lon": site_place["lon"], "lat": site_place["lat"]},
        seat={
            "id": seat_place["id"],
            "name": seat,
            "lon": seat_place["lon"],
            "lat": seat_place["lat"],
        },
    )


def _recommendations(city_id: str, groups: list[dict], detections: dict) -> tuple[list[dict], list[dict]]:
    scenarios: list[dict] = []
    skipped: list[dict] = []
    by_org: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        by_org[group["organization_id"]].append(group)

    satellites = []
    for members in by_org.values():
        if len({group["home"]["id"] for group in members}) < 2:
            continue
        scenario = _satellite_scenario(city_id, members)
        if scenario is not None:
            satellites.append(scenario)
    satellites.sort(
        key=lambda item: (
            item["organization_id"] == EXAMPLE_ORG_ID,
            item["impact"]["distance_saved_km_per_working_day"],
        ),
        reverse=True,
    )
    if satellites:
        scenarios.extend(satellites[:2])
    else:
        skipped.append(
            {
                "kind": "bureau_satellite",
                "reason": "Aucun groupe ne gagne 4 km ou plus en étant rattaché à un autre quartier.",
            }
        )

    covered = {
        item["organization_id"]
        for item in scenarios
        if item["kind"] == "bureau_satellite" and item["status"] == "scenario_recommande"
    }
    long_by_home: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        if group["km"] < 12 or group["organization_id"] in covered:
            continue
        long_by_home[group["home"]["id"]].append(group)
    tiers = None
    if long_by_home:
        home_id = max(long_by_home, key=lambda item: sum(group["headcount"] for group in long_by_home[item]))
        members = long_by_home[home_id]
        people = sum(group["headcount"] for group in members)
        if people >= 20:
            home = PLACES[home_id]
            found = _best_satellite(city_id, members)
            if found is not None:
                moved = found["moved"]
                people = sum(group["headcount"] for group in moved)
                km_saved = 2 * 0.6 * found["saved_person_km"]
                co2_saved = sum(
                    2 * 0.6 * group["gain"] * group["headcount"] * _co2(group["mode"])
                    for group in moved
                )
                tiers = _scenario(
                    kind="tiers_lieu",
                    title=f"Tiers-lieu près de {home['name']}",
                    recommended=False,
                    why=(
                        f"{people} employés simulés habitent {home['name']} et parcourent au moins 12 km, "
                        "sans qu'un bureau satellite d'organisation soit déjà le scénario retenu. "
                        "Un tiers-lieu partagé, trois jours sur cinq, est une hypothèse."
                    ),
                    data=f"{SOURCE} Quartier {home['name']}, navettes d'au moins 12 km.",
                    people=people,
                    km_saved=km_saved,
                    trips_reduced=2 * people * 0.6,
                    co2_saved=co2_saved,
                    assumptions=(
                        "Trois jours ouvrés sur cinq au tiers-lieu, deux jours au siège. "
                        "Le gain du site n'est donc compté qu'à 60 %."
                    ),
                    limits=_limits(
                        "Le métier doit pouvoir se faire hors du siège. Ce n'est pas vérifié.",
                    ),
                    site_name=found["place"]["name"],
                )
    if tiers:
        scenarios.append(tiers)
    else:
        skipped.append(
            {
                "kind": "tiers_lieu",
                "reason": "Pas assez de navettes d'au moins 12 km hors des scénarios de bureau satellite.",
            }
        )

    remote = [group for group in groups if group["km"] >= 15]
    if remote:
        people = sum(group["headcount"] for group in remote)
        km_saved = 0.8 * 2 * sum(group["km"] * group["headcount"] for group in remote)
        co2_saved = 0.8 * 2 * sum(
            group["km"] * group["headcount"] * _co2(group["mode"]) for group in remote
        )
        scenarios.append(
            _scenario(
                kind="teletravail",
                title="Télétravail partiel sur les longues navettes",
                recommended=False,
                why=(
                    f"{people} employés simulés ont une navette d'au moins 15 km. "
                    "Venir un jour ouvré sur cinq éviterait les quatre autres dans le scénario."
                ),
                data=f"{SOURCE} Seuil : distance simulée ≥ 15 km.",
                people=people,
                km_saved=km_saved,
                trips_reduced=0.8 * 2 * people,
                co2_saved=co2_saved,
                assumptions="Présence sur site un jour ouvré sur cinq pour ces groupes seulement.",
                limits=_limits("Le poste doit être télétravaillable. Le catalogue ne le dit pas."),
            )
        )
    else:
        skipped.append(
            {
                "kind": "teletravail",
                "reason": "Aucune navette simulée n'atteint 15 km.",
            }
        )

    motor = [
        group
        for group in groups
        if group["mode"] in {"taxi", "car"} and group["headcount"] >= 20
    ]
    if motor:
        group = max(motor, key=lambda item: item["headcount"])
        people = group["headcount"]
        avoided_vehicles = (people - 1) * 2
        co2_saved = 2 * people * group["km"] * (_co2(group["mode"]) - _co2("bus"))
        scenarios.append(
            _scenario(
                kind="transport_collectif",
                title=f"Transport collectif {group['home']['name']} → {group['seat']['name']}",
                recommended=False,
                why=(
                    f"{people} employés simulés de {group['organization_name']} "
                    f"font déjà le même trajet en {group['mode']}, "
                    f"de {group['home']['name']} vers {group['seat']['name']}."
                ),
                data=(
                    f"{SOURCE} Un seul groupe origine-destination, mode {group['mode']}, "
                    f"{group['km']} km."
                ),
                people=people,
                km_saved=0,
                trips_reduced=avoided_vehicles,
                co2_saved=max(0.0, co2_saved),
                assumptions=(
                    "Un bus d'organisation remplace les véhicules individuels. "
                    "La distance parcourue par les personnes ne change pas. "
                    "Les déplacements réduits sont des véhicules, pas des personnes. "
                    "Le CO₂ passe du facteur taxi/voiture (0,18) au facteur bus (0,08)."
                ),
                limits=_limits("L'horaire commun et le nombre de places ne sont pas vérifiés."),
                organization_id=group["organization_id"],
            )
        )
    else:
        skipped.append(
            {
                "kind": "transport_collectif",
                "reason": "Aucun groupe d'au moins 20 personnes n'est en taxi ou en voiture sur le même trajet.",
            }
        )

    relay = [group for group in groups if group["mode"] in {"taxi", "car"} and group["km"] >= 10]
    if relay:
        people = sum(group["headcount"] for group in relay)
        car_km = sum(group["km"] * group["headcount"] for group in relay)
        km_shifted = 0.4 * 2 * car_km
        co2_saved = 0.4 * 2 * sum(
            group["km"] * group["headcount"] * (_co2(group["mode"]) - _co2("bus"))
            for group in relay
        )
        scenarios.append(
            _scenario(
                kind="parking_relais",
                title="Parking relais en entrée de ville",
                recommended=False,
                why=(
                    f"{people} employés simulés arrivent de la périphérie en taxi ou en voiture, "
                    "sur 10 km ou plus. Un relais couperait la fin du trajet en transport collectif."
                ),
                data=f"{SOURCE} Mode taxi ou voiture, distance ≥ 10 km.",
                people=people,
                km_saved=0,
                trips_reduced=0,
                co2_saved=max(0.0, co2_saved),
                assumptions=(
                    "40 % de la distance, côté centre, passerait du véhicule individuel au bus. "
                    "Le kilométrage des personnes ne baisse pas : seul le mode de la dernière partie change. "
                    f"Environ {_round1(km_shifted)} voyageurs-km motorisés seraient concernés par jour ouvré."
                ),
                limits=_limits("L'emplacement du relais et la fréquence du bus ne sont pas dimensionnés."),
            )
        )
    else:
        skipped.append(
            {
                "kind": "parking_relais",
                "reason": "Pas de navette périphérique simulée en taxi ou en voiture d'au moins 10 km.",
            }
        )

    short = [group for group in groups if 2 <= group["km"] <= 6 and group["mode"] in {"bus", "taxi", "car"}]
    if short:
        people = sum(group["headcount"] for group in short)
        shifted = int(round(people * 0.15))
        co2_saved = 0.15 * 2 * sum(
            group["km"] * group["headcount"] * _co2(group["mode"]) for group in short
        )
        label = _join_names(
            sorted({f"{group['home']['name']} → {group['seat']['name']}" for group in short})[:3]
        )
        scenarios.append(
            _scenario(
                kind="piste_cyclable",
                title="Piste cyclable sur les courtes navettes",
                recommended=False,
                why=(
                    f"{people} employés simulés font 2 à 6 km en bus, taxi ou voiture ({label}). "
                    "Une piste pourrait en reporter une partie vers le vélo."
                ),
                data=f"{SOURCE} Distance entre 2 et 6 km, mode motorisé.",
                people=shifted,
                km_saved=0,
                trips_reduced=0,
                co2_saved=co2_saved,
                assumptions=(
                    "Hypothèse de report : 15 % de ces employés passeraient au vélo. "
                    "Les personnes concernées affichées sont cette part, pas le flux entier. "
                    "La distance ne baisse pas ; le CO₂ de la part reportée est mis à zéro."
                ),
                limits=_limits("15 % est un ordre de grandeur, pas une enquête de pratique du vélo."),
            )
        )
    else:
        skipped.append(
            {
                "kind": "piste_cyclable",
                "reason": "Aucun groupe simulé ne combine 2 à 6 km et un mode motorisé.",
            }
        )

    if detections["critical_nodes"]:
        node = detections["critical_nodes"][0]
        arriving = [
            group for group in groups if group["seat"]["id"] == node["id"]
        ]
        people = sum(group["headcount"] for group in arriving)
        hours = 2 * sum(group["km"] * group["headcount"] for group in arriving) / SPEED_KMH
        saved_hours = hours * (1 - SPEED_KMH / 22)
        scenarios.append(
            _scenario(
                kind="horaires",
                title=f"Décalage des horaires à {node['name']}",
                recommended=False,
                why=(
                    f"{node['name']} est un nœud d'arrivée : {node['people']} employés simulés, "
                    f"{node['origin_zones']} quartiers d'origine. Étaler les arrivées viserait le pic, pas le tracé."
                ),
                data=f"{SOURCE} Arrivées domicile-travail vers {node['name']}.",
                people=people,
                km_saved=0,
                trips_reduced=0,
                co2_saved=0,
                time_saved_h=saved_hours,
                assumptions=(
                    "La vitesse supposée passe de 18 à 22 km/h si le pic est évité. "
                    f"Temps estimé en moins : {_round1(saved_hours)} h par jour ouvré, tous employés confondus. "
                    "La distance et le CO₂ ne changent pas. Ce n'est pas un modèle de congestion."
                ),
                limits=_limits("22 km/h est une hypothèse, pas une mesure de trafic."),
            )
        )
    else:
        skipped.append(
            {
                "kind": "horaires",
                "reason": "Aucun lieu de travail ne réunit 50 arrivées depuis au moins 3 quartiers.",
            }
        )
    return scenarios, skipped


def _organizations(groups: list[dict]) -> list[dict]:
    by_org: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        by_org[group["organization_id"]].append(group)
    rows = []
    for members in by_org.values():
        people = sum(group["headcount"] for group in members)
        seat = members[0]["seat"]
        homes = [
            {
                "id": group["home"]["id"],
                "name": group["home"]["name"],
                "parent": group["home"]["parent_name"],
                "headcount": group["headcount"],
                "mode": group["mode"],
                "distance_km": group["km"],
                "lon": group["home"]["lon"],
                "lat": group["home"]["lat"],
                "share": round(group["headcount"] / people, 3) if people else 0,
            }
            for group in sorted(members, key=lambda item: -item["headcount"])
        ]
        top = homes[0]
        concentration = (
            f"{top['name']} réunit {round(top['share'] * 100)} % des employés simulés "
            f"({top['headcount']} personnes, {top['distance_km']} km)."
        )
        corridor = ""
        if len(homes) >= 3:
            corridor = (
                f"{len(homes)} quartiers de résidence convergent vers {seat['name']}."
            )
        rows.append(
            {
                "id": members[0]["organization_id"],
                "name": members[0]["organization_name"],
                "example": members[0]["example"],
                "sector": members[0]["sector_label"],
                "seat_id": seat["id"],
                "seat_name": seat["name"],
                "seat_lon": seat["lon"],
                "seat_lat": seat["lat"],
                "employees": people,
                "mean_km": _round1(sum(group["km"] * group["headcount"] for group in members) / people),
                "homes": homes,
                "work_zones": [{"id": seat["id"], "name": seat["name"], "people": people}],
                "concentration": concentration,
                "corridor": corridor,
            }
        )
    rows.sort(key=lambda item: (item["example"], item["employees"]), reverse=True)
    return rows


def _worked_example(city_id: str, groups: list[dict], corridors: list[dict]) -> dict | None:
    members = [group for group in groups if group["organization_id"] == EXAMPLE_ORG_ID]
    if not members:
        return None
    scenario = _satellite_scenario(city_id, members, force=True)
    seat = members[0]["seat"]
    names = [group["home"]["name"] for group in members]
    matching = [
        item
        for item in corridors
        if item["destination_id"] == seat["id"] and item["people"] >= sum(group["headcount"] for group in members) - 5
    ]
    corridor_label = matching[0]["label"] if matching else (
        f"{_join_names(names)} → {seat['name']}"
    )
    return {
        "synthetic": True,
        "title": "Même siège, trois quartiers de résidence",
        "organization_id": EXAMPLE_ORG_ID,
        "organization_name": members[0]["organization_name"],
        "note": (
            "Jeu d'exemple simulé : 30 employés à Ivato, 25 à Talatamaty, 20 à Ambohibao. "
            "Ce ne sont pas des effectifs observés."
        ),
        "seat_name": seat["name"],
        "seat": {
            "id": seat["id"],
            "name": seat["name"],
            "lon": seat["lon"],
            "lat": seat["lat"],
        },
        "homes": [
            {
                "name": group["home"]["name"],
                "headcount": group["headcount"],
                "mode": group["mode"],
                "distance_km": group["km"],
                "lon": group["home"]["lon"],
                "lat": group["home"]["lat"],
            }
            for group in sorted(members, key=lambda item: -item["headcount"])
        ],
        "corridor": corridor_label,
        "scenario": scenario,
    }


def analyze(city_label: str) -> dict:
    city = resolve_city(city_label)
    groups = _groups(city["id"])
    empty_clustering = {
        "chosen": None,
        "comparison": [],
        "why": "Moins de quatre groupes : les trois méthodes ne peuvent pas être départagées.",
        "variables": [],
        "clusters": [],
    }
    clustering = empty_clustering
    if len(groups) >= 4:
        scaled = _scale([group["vector"] for group in groups])
        chosen, candidates = _compare(scaled)
        public = []
        for item in candidates:
            public.append(
                {
                    "method": item["method"],
                    "label": item["label"],
                    "k": item["k"],
                    "eps": item["eps"],
                    "min_samples": item["min_samples"],
                    "silhouette": item["silhouette"],
                    "clusters": item["clusters"],
                    "noise_share": item["noise_share"],
                    "eligible": item["eligible"],
                    "retained": item["method"] == chosen["method"]
                    and item.get("eps") == chosen.get("eps")
                    and item.get("min_samples") == chosen.get("min_samples"),
                }
            )
        clustering = {
            "chosen": {
                "method": chosen["method"],
                "label": chosen["label"],
                "k": chosen["k"],
                "silhouette": chosen["silhouette"],
                "seed": KMEANS_SEED if chosen["method"] == "k-means" else None,
            },
            "comparison": public,
            "why": _why_method(chosen, candidates),
            "variables": [
                "origine (longitude, latitude)",
                "destination (longitude, latitude)",
                "distance",
                "fréquence (5 jours/semaine sur ce jeu, donc peu discriminante)",
                "mode",
                "secteur",
            ],
            "organization_note": (
                "L'organisation n'est pas dans le vecteur. "
                "Elle sert à lire les concentrations : sinon chaque organisme formerait son propre groupe."
            ),
            "clusters": _cluster_cards(groups, chosen["labels"]),
            "unit": "Un point = un groupe d'employés simulés. La taille du profil est la somme des effectifs.",
        }
    profiles = _profiles(groups)
    convergences = _convergences(groups)
    profiles.append(
        {
            "id": "convergence",
            "title": PROFILE_TITLES["convergence"],
            "people": sum(item["people"] for item in convergences),
            "mean_km": None,
            "reading": (
                "Plusieurs quartiers de résidence alimentent le même lieu de travail. "
                "C'est le profil le plus utile pour une organisation : le siège draine un bassin, "
                "pas un seul quartier."
            ),
            "organizations": convergences,
        }
    )
    detections = _detections(groups)
    scenarios, skipped = _recommendations(city["id"], groups, detections)
    return {
        "synthetic": True,
        "estimation_label": "estimation simulée",
        "disclaimer": (
            "Tous les effectifs de cet écran sont simulés. "
            "Un scénario recommandé ou potentiellement pertinent est une hypothèse à discuter. "
            "Ce n'est pas une solution optimale certaine."
        ),
        "source": SOURCE,
        "city": city["name"],
        "clustering": clustering,
        "profiles": profiles,
        "organizations": _organizations(groups),
        "detections": detections,
        "recommendations": scenarios,
        "not_proposed": skipped,
        "worked_example": _worked_example(city["id"], groups, detections["corridors"]),
    }
