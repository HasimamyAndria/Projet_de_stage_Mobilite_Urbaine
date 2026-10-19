"""
Aide à la décision pour les grands employeurs.

Chaque groupe relie une organisation, un quartier de domicile, un lieu de
travail et une fonction. À partir de 8 km et de 20 personnes, plusieurs
hypothèses sont chiffrées : louer une annexe, la construire, une navette,
ou du télétravail. Aucune n'est une décision déjà prise.
"""
from __future__ import annotations

from app.data.organizations import ORGANIZATIONS, REGULAR_ERRANDS
from app.data.persons import PERSONS
from app.data.territory import PLACES, city_by_id
from app.services import diary as diary_service
from app.services.lens import _km

FAR_KM = 8.0
MIN_GAIN_KM = 4.0
BUILD_PEOPLE = 45
TARGET_KINDS = {"ministere", "entreprise"}

MODE_LABEL = {
    "marche": "Marche",
    "velo": "Vélo",
    "bus": "Bus",
    "voiture": "Voiture",
    "taxi": "Taxi",
    "car": "Voiture",
}
SPEED_KMH = {
    "marche": 4.5,
    "velo": 15.0,
    "bus": 16.0,
    "voiture": 22.0,
    "taxi": 20.0,
    "car": 22.0,
}

GRADE_LABEL = {
    "considerable": "poste considérable",
    "bureau": "poste de bureau",
    "terrain": "poste sur site",
}


def board(city_id: str) -> dict:
    city = city_by_id(city_id)
    if city is None:
        raise ValueError("Ville inconnue, ou sous le seuil de 200 000 habitants.")
    employers = [_employer(org) for org in ORGANIZATIONS if org["city_id"] == city_id]
    employers.sort(
        key=lambda item: (
            item["kind"] in TARGET_KINDS,
            item["considerable_far_count"],
            item["far_count"],
        ),
        reverse=True,
    )
    focus = next(
        (item["id"] for item in employers if item["considerable_far_count"] >= 20),
        employers[0]["id"] if employers else None,
    )
    return {
        "synthetic": True,
        "city_id": city_id,
        "city_name": city["name"],
        "focus_id": focus,
        "far_km": FAR_KM,
        "note": (
            "Groupes simulés d'au moins 20 employés qui partagent le même domicile, "
            "le même lieu de travail et la même fonction. "
            f"« Loin » veut dire au moins {FAR_KM:.0f} km de trajet. "
            "Les possibilités se comparent ; aucune n'est décidée."
        ),
        "employers": employers,
    }


def detail(organization_id: str) -> dict:
    org = next((item for item in ORGANIZATIONS if item["id"] == organization_id), None)
    if org is None:
        raise ValueError("Organisation inconnue.")
    return _employer(org)


def _employer(org: dict) -> dict:
    seat = PLACES[org["seat_id"]]
    clusters = [_cluster(org, cluster, seat) for cluster in org["clusters"]]
    clusters.sort(key=lambda item: (item["far"], item["considerable"], item["headcount"]), reverse=True)
    far = [item for item in clusters if item["far"]]
    considerable_far = [item for item in far if item["considerable"]]
    samples = _samples(org["id"], clusters)
    headline = _headline(considerable_far or far or clusters, seat["name"])
    return {
        "id": org["id"],
        "name": org["name"],
        "kind": org["kind"],
        "kind_label": org["kind_label"],
        "decision_target": org["kind"] in TARGET_KINDS,
        "activity": org["activity"],
        "seat_id": seat["id"],
        "seat_name": seat["name"],
        "employee_count": sum(item["headcount"] for item in clusters),
        "far_count": sum(item["headcount"] for item in far),
        "considerable_far_count": sum(item["headcount"] for item in considerable_far),
        "cluster_count": len(clusters),
        "headline": headline,
        "clusters": clusters,
        "options": _options(org, clusters, seat),
        "samples": samples,
    }


def _cluster(org: dict, cluster: dict, seat: dict) -> dict:
    home = PLACES[cluster["home_id"]]
    distance = _km(home["lon"], home["lat"], seat["lon"], seat["lat"])
    mode = cluster["mode"]
    minutes = _minutes(distance, mode)
    far = distance >= FAR_KM
    considerable = cluster["grade"] == "considerable"
    grade = GRADE_LABEL.get(cluster["grade"], cluster["grade"])
    count = cluster["headcount"]
    if far and considerable:
        reading = (
            f"{count} {cluster['function_plural']} habitent {home['name']} "
            f"et travaillent à {seat['name']}, à {_fr(distance)} km. "
            "Ce sont des postes considérables : le bureau peut se rapprocher de ce domicile."
        )
    elif far and cluster["relocatable"]:
        reading = (
            f"{count} {cluster['function_plural']} habitent {home['name']} "
            f"et travaillent à {seat['name']}, à {_fr(distance)} km."
        )
    elif far:
        reading = (
            f"{count} {cluster['function_plural']} habitent {home['name']} "
            f"et travaillent à {seat['name']}, à {_fr(distance)} km. "
            "Ce poste se fait sur le site : une annexe ne le déplace pas."
        )
    else:
        reading = (
            f"{count} {cluster['function_plural']} habitent {home['name']}, "
            f"près du lieu de travail ({seat['name']}, {_fr(distance)} km)."
        )
    return {
        "id": f"{org['id']}:{home['id']}:{cluster['function_id']}",
        "home_id": home["id"],
        "home_name": home["name"],
        "home_parent": home.get("parent_name"),
        "work_id": seat["id"],
        "work_name": seat["name"],
        "lon": home["lon"],
        "lat": home["lat"],
        "headcount": count,
        "mode": mode,
        "mode_label": MODE_LABEL.get(mode, mode),
        "function": cluster["function"],
        "function_plural": cluster["function_plural"],
        "grade": cluster["grade"],
        "grade_label": grade,
        "considerable": considerable,
        "relocatable": cluster["relocatable"],
        "km": distance,
        "minutes": minutes,
        "far": far,
        "reading": reading,
        "rhythm": _rhythm(home["name"], seat["name"], cluster["function"], mode, distance, minutes, count),
    }


def _rhythm(
    home: str,
    work: str,
    function: str,
    mode: str,
    km: float,
    minutes: int,
    headcount: int,
) -> dict:
    leave = 7.5 - minutes / 60
    back_leave = 17.0
    back_arrive = back_leave + minutes / 60
    mode_label = MODE_LABEL.get(mode, mode)
    return {
        "label": "Jours ouvrés",
        "km_one_way": km,
        "minutes_one_way": minutes,
        "mode_label": mode_label,
        "note": (
            f"Rythme type des {headcount} personnes de ce groupe. "
            "Ce n'est pas le journal d'une seule personne."
        ),
        "steps": [
            {"when": _clock(leave), "text": f"Départ du domicile, {home}", "mode": mode_label},
            {
                "when": _clock(7.5),
                "text": f"Arrivée au travail, {work} — {function}",
                "mode": mode_label,
            },
            {"when": _clock(back_leave), "text": f"Départ du travail, {work}", "mode": mode_label},
            {"when": _clock(back_arrive), "text": f"Retour au domicile, {home}", "mode": mode_label},
        ],
    }


def _options(org: dict, clusters: list[dict], seat: dict) -> list[dict]:
    movable = [item for item in clusters if item["relocatable"]]
    candidates = _sites(movable)
    options: list[dict] = []
    if candidates:
        primary = candidates[0]
        options.append(_lease(org, primary))
        options.append(_build(org, primary))
        for other in candidates[1:]:
            if other["place_id"] == primary["place_id"]:
                continue
            if other["people"] < 20:
                continue
            options.append(_lease(org, other, alternative=True))
            break
    else:
        terrain = [item for item in clusters if item["far"] and not item["relocatable"]]
        if terrain:
            names = _who_phrase(terrain)
            options.append(
                {
                    "id": f"{org['id']}:pas-annexe",
                    "kind": "pas_annexe",
                    "title": "Une annexe ne déplace pas ces postes",
                    "people": sum(item["headcount"] for item in terrain),
                    "site_name": None,
                    "km_saved_per_working_day": 0,
                    "reading": (
                        f"{names} ont un poste sur site ({org['activity']}). "
                        f"Le lieu de travail reste {seat['name']}."
                    ),
                    "who": [_who_row(item, item["km"]) for item in terrain],
                    "assumptions": "Le métier exige la présence sur le site actuel.",
                    "limits": [
                        "La distance domicile–travail ne change pas.",
                        "Une navette peut seulement rendre le même trajet plus régulier.",
                    ],
                }
            )

    shuttle = _shuttle(org, clusters, seat)
    if shuttle is not None:
        options.append(shuttle)
    remote = _remote(org, clusters)
    if remote is not None:
        options.append(remote)
    if not options:
        options.append(
            {
                "id": f"{org['id']}:rien",
                "kind": "rien",
                "title": "Pas d'éloignement à traiter",
                "people": 0,
                "site_name": seat["name"],
                "km_saved_per_working_day": 0,
                "reading": (
                    f"À {org['name']}, les groupes habitent à moins de {FAR_KM:.0f} km "
                    f"du siège ({seat['name']})."
                ),
                "who": [],
                "assumptions": f"Seuil d'éloignement : {FAR_KM:.0f} km.",
                "limits": ["En dessous de ce seuil, une annexe ne se justifie pas dans ce catalogue."],
            }
        )
    return options


def _sites(clusters: list[dict]) -> list[dict]:
    found = []
    seen: set[str] = set()
    for origin in clusters:
        if origin["home_id"] in seen:
            continue
        seen.add(origin["home_id"])
        helped = []
        for cluster in clusters:
            after = _km(cluster["lon"], cluster["lat"], origin["lon"], origin["lat"])
            gain = cluster["km"] - after
            if gain < MIN_GAIN_KM:
                continue
            helped.append({**cluster, "after_km": round(after, 1), "gain": gain})
        if not helped:
            continue
        people = sum(item["headcount"] for item in helped)
        if people < 20:
            continue
        saved = sum(2 * item["gain"] * item["headcount"] for item in helped)
        found.append(
            {
                "place_id": origin["home_id"],
                "place_name": origin["home_name"],
                "parent": origin["home_parent"],
                "people": people,
                "saved_person_km": saved,
                "helped": sorted(helped, key=lambda item: -item["headcount"]),
            }
        )
    found.sort(key=lambda item: item["saved_person_km"], reverse=True)
    # À gain proche, l'annexe se pose là où le plus gros groupe habite déjà.
    if len(found) >= 2:
        lead = found[0]
        for index, other in enumerate(found[1:], start=1):
            if other["saved_person_km"] < lead["saved_person_km"] * 0.92:
                break
            if _onsite(other) > _onsite(lead):
                found.insert(0, found.pop(index))
                break
    return found


def _onsite(site: dict) -> int:
    return next(
        (item["headcount"] for item in site["helped"] if item["home_id"] == site["place_id"]),
        0,
    )


def _lease(org: dict, site: dict, *, alternative: bool = False) -> dict:
    who = _who_phrase(site["helped"])
    prefix = "Autre possibilité : louer" if alternative else "Louer"
    considerable = sum(item["headcount"] for item in site["helped"] if item["considerable"])
    focus = (
        f" Dont {considerable} sur un poste considérable."
        if considerable and considerable != site["people"]
        else ""
    )
    return {
        "id": f"{org['id']}:louer:{site['place_id']}",
        "kind": "louer",
        "title": f"{prefix} un bureau annexe à {site['place_name']}",
        "people": site["people"],
        "site_name": site["place_name"],
        "km_saved_per_working_day": round(site["saved_person_km"], 0),
        "reading": (
            f"{org['name']} : {who}, aujourd'hui vers {site['helped'][0]['work_name']}. "
            f"Un bail à {site['place_name']} rapproche ces postes de leur domicile.{focus} "
            "Le siège actuel reste pour les groupes qui n'y gagnent pas 4 km."
        ),
        "who": [_who_row(item, item["after_km"]) for item in site["helped"]],
        "assumptions": (
            "Aller-retour ouvré. Le trajet vers le siège est remplacé par le trajet vers l'annexe. "
            "Un gain inférieur à 4 km n'est pas compté."
        ),
        "limits": [
            "Le quartier est un point du catalogue, pas un local disponible.",
            "La location se compare à la construction : elle engage moins longtemps.",
            "Les effectifs sont simulés, pas un fichier du personnel.",
        ],
    }


def _build(org: dict, site: dict) -> dict:
    who = _who_phrase(site["helped"])
    enough = site["people"] >= BUILD_PEOPLE
    weight = (
        f"L'effectif groupé ({site['people']} personnes) est assez grand pour comparer une construction."
        if enough
        else (
            f"{site['people']} personnes : la construction est plus lourde qu'une location "
            "pour cet effectif. Elle reste une possibilité à chiffrer."
        )
    )
    return {
        "id": f"{org['id']}:construire:{site['place_id']}",
        "kind": "construire",
        "title": f"Construire un bureau annexe à {site['place_name']}",
        "people": site["people"],
        "site_name": site["place_name"],
        "km_saved_per_working_day": round(site["saved_person_km"], 0),
        "reading": (
            f"Même bassin que la location : {who}. {weight} "
            f"Le gain de distance est le même ; ce qui change, c'est l'engagement."
        ),
        "who": [_who_row(item, item["after_km"]) for item in site["helped"]],
        "assumptions": "Même hypothèse de distance que la location, sur le même quartier.",
        "limits": [
            "Construire demande un foncier et un délai que ce catalogue ne connaît pas.",
            "En dessous d'environ 45 personnes regroupées, la location est en général plus souple.",
            "Ce n'est pas un choix déjà fait.",
        ],
    }


def _shuttle(org: dict, clusters: list[dict], seat: dict) -> dict | None:
    far = [item for item in clusters if item["far"]]
    if not far:
        return None
    by_parent: dict[str, list[dict]] = {}
    for item in far:
        by_parent.setdefault(item["home_parent"] or item["home_name"], []).append(item)
    parent = max(by_parent, key=lambda key: sum(item["headcount"] for item in by_parent[key]))
    members = by_parent[parent]
    people = sum(item["headcount"] for item in members)
    if people < 20:
        return None
    homes = _join([item["home_name"] for item in sorted(members, key=lambda item: -item["headcount"])])
    return {
        "id": f"{org['id']}:navette:{parent}",
        "kind": "navette",
        "title": f"Navette {parent} → {seat['name']}",
        "people": people,
        "site_name": parent,
        "km_saved_per_working_day": 0,
        "reading": (
            f"{people} employés de {homes} vont déjà à {seat['name']} "
            f"({org['name']}). Une navette ne raccourcit pas le trajet : "
            "elle le rend commun, à heure fixe, à la place du bus ou du taxi de chacun."
        ),
        "who": [_who_row(item, item["km"]) for item in members],
        "assumptions": "Même domicile–travail. Seul le mode change, pas la distance.",
        "limits": [
            "L'horaire commun et le nombre de places ne sont pas vérifiés.",
            "Les postes sur site comme les postes de bureau peuvent la prendre.",
        ],
    }


def _remote(org: dict, clusters: list[dict]) -> dict | None:
    members = [item for item in clusters if item["far"] and item["considerable"]]
    if not members:
        return None
    people = sum(item["headcount"] for item in members)
    saved = 0.4 * 2 * sum(item["km"] * item["headcount"] for item in members)
    return {
        "id": f"{org['id']}:teletravail",
        "kind": "teletravail",
        "title": "Télétravail deux jours sur cinq",
        "people": people,
        "site_name": None,
        "km_saved_per_working_day": round(saved, 0),
        "reading": (
            f"{people} postes considérables de {org['name']} sont à {FAR_KM:.0f} km ou plus. "
            "Rester chez soi deux jours ouvrés sur cinq évite ces navettes ces jours-là, "
            "sans ouvrir d'annexe. Les trois autres jours, le siège reste le lieu de travail."
        ),
        "who": [_who_row(item, item["km"]) for item in members],
        "assumptions": "Deux jours sur cinq sans déplacement domicile–travail. Le gain est donc de 40 %.",
        "limits": [
            "Réservé aux postes considérables de ce catalogue.",
            "Le métier doit pouvoir se faire à distance. Ce n'est pas vérifié.",
        ],
    }


def _samples(organization_id: str, clusters: list[dict]) -> list[dict]:
    by_home = {item["home_id"]: item["id"] for item in clusters}
    rows = []
    for person in PERSONS:
        if person.get("organization_id") != organization_id:
            continue
        home = PLACES[person["home_id"]]
        work = PLACES[person["work_id"]]
        rows.append(
            {
                "id": person["id"],
                "name": person["name"],
                "job": person["job"],
                "home": home["name"],
                "work": work["name"],
                "cluster_id": by_home.get(person["home_id"]),
                "blurb": person["blurb"],
            }
        )
    return rows


def _headline(clusters: list[dict], seat_name: str) -> str:
    if not clusters:
        return f"Aucun groupe vers {seat_name}."
    top = clusters[0]
    return (
        f"{top['headcount']} {top['function_plural']} : {top['home_name']} → {seat_name}, "
        f"{_fr(top['km'])} km"
    )


def _who_phrase(members: list[dict]) -> str:
    parts = [
        f"{item['headcount']} {item['function_plural']} à {item['home_name']}"
        for item in members
    ]
    return _join(parts)


def _who_row(item: dict, after_km: float) -> dict:
    return {
        "home": item["home_name"],
        "work": item["work_name"],
        "headcount": item["headcount"],
        "function": item["function_plural"],
        "grade_label": item["grade_label"],
        "before_km": item["km"],
        "after_km": after_km,
        "mode_label": item["mode_label"],
    }


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return names[0] if names else ""
    if len(names) == 2:
        return f"{names[0]} et {names[1]}"
    return ", ".join(names[:-1]) + " et " + names[-1]


def _minutes(km: float, mode: str) -> int:
    speed = SPEED_KMH.get(mode, 16.0)
    return max(5, round(km / speed * 60))


_CADENCE_DAY = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}
# Motif du catalogue, motif d'écran, jour par défaut, heure, temps sur place.
_ERRAND_SHAPE = {
    "courses": ("supermarche", 5, 9.0, 0.9),
    "culte": ("culte", 6, 8.5, 1.8),
    "visite": ("visite", 6, 14.0, 2.0),
}
_AMENITY = {
    "supermarche": ("commerce", "Supermarché", "courses"),
    "culte": ("equipement", "Culte", "culte"),
}


def _cadence_day(cadence: str, default: int) -> int:
    text = cadence.lower()
    for name, index in _CADENCE_DAY.items():
        if name in text:
            return index
    return default


def _nearest_role(home: dict, role: str) -> dict | None:
    candidates = [
        place
        for place in PLACES.values()
        if place["city_id"] == home["city_id"]
        and place["level"] == "quartier"
        and place["role"] == role
        and place["id"] != home["id"]
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda place: _km(home["lon"], home["lat"], place["lon"], place["lat"]),
    )


def _usual_shop(city_id: str, home_id: str) -> dict | None:
    """Supermarché déjà décrit pour la ville, sinon le commerce le plus proche."""
    scores: dict[str, int] = {}
    for errand in REGULAR_ERRANDS:
        if errand["city_id"] == city_id and errand["purpose"] == "courses":
            scores[errand["dest_id"]] = scores.get(errand["dest_id"], 0) + errand["headcount"]
    ranked = sorted(scores, key=lambda place_id: scores[place_id], reverse=True)
    for place_id in ranked:
        place = PLACES[place_id]
        if place_id != home_id and place["role"] == "commerce":
            return place
    return _nearest_role(PLACES[home_id], "commerce")


def _regular_errands(city_id: str, home_id: str) -> list[dict]:
    """Courses, culte et visites qui reviennent chaque semaine au même endroit."""
    home = PLACES[home_id]
    rows: list[dict] = []
    seen: set[str] = set()
    for errand in REGULAR_ERRANDS:
        if errand["city_id"] != city_id or errand["home_id"] != home_id:
            continue
        if errand["purpose"] not in _ERRAND_SHAPE or errand["dest_id"] == home_id:
            continue
        diary_purpose, default_day, depart, dwell = _ERRAND_SHAPE[errand["purpose"]]
        rows.append(
            {
                "purpose": errand["purpose"],
                "diary_purpose": diary_purpose,
                "dest_id": errand["dest_id"],
                "detail": errand["detail"],
                "mode": errand["mode"] if errand["mode"] in diary_service.MODES else "bus",
                "weekday": _cadence_day(errand["cadence"], default_day),
                "depart": depart,
                "dwell": dwell,
            }
        )
        seen.add(errand["purpose"])
    if "courses" not in seen:
        shop = _usual_shop(city_id, home_id)
        if shop is not None:
            km = _km(home["lon"], home["lat"], shop["lon"], shop["lat"])
            rows.append(
                {
                    "purpose": "courses",
                    "diary_purpose": "supermarche",
                    "dest_id": shop["id"],
                    "detail": f"Courses de la semaine au supermarché de {shop['name']}",
                    "mode": "marche" if km < 2 else "bus",
                    "weekday": 5,
                    "depart": 9.0,
                    "dwell": 0.9,
                }
            )
    if "culte" not in seen:
        church = _nearest_role(home, "equipement")
        if church is not None:
            km = _km(home["lon"], home["lat"], church["lon"], church["lat"])
            rows.append(
                {
                    "purpose": "culte",
                    "diary_purpose": "culte",
                    "dest_id": church["id"],
                    "detail": f"Culte du dimanche à {church['name']}",
                    "mode": "marche" if km < 2 else "bus",
                    "weekday": 6,
                    "depart": 8.5,
                    "dwell": 1.8,
                }
            )
    rows.sort(key=lambda item: (item["weekday"], item["depart"]))
    return rows


def _depart_hour(weekday: int, preferred: float, travel_h: float, dwell: float) -> float:
    start = max(preferred, 18.0) if weekday <= 4 else preferred
    span = travel_h + dwell + travel_h
    if start + span > 22.5:
        start = max(18.0 if weekday <= 4 else 6.0, 22.5 - span)
    return round(start, 2)


def _errand_loop(person_id: str, home: dict, errand: dict) -> list[tuple[int, dict]]:
    dest = PLACES[errand["dest_id"]]
    mode = errand["mode"]
    km = diary_service._route_km(home["lon"], home["lat"], dest["lon"], dest["lat"])
    minutes = _minutes(km, mode)
    weekday = errand["weekday"]
    depart = _depart_hour(weekday, errand["depart"], minutes / 60, errand["dwell"])
    outbound = diary_service._make_trip(
        trip_id=f"{person_id}-{weekday}-{errand['diary_purpose']}-aller",
        person_id=person_id,
        weekday=weekday,
        origin=home,
        destination=dest,
        purpose=errand["diary_purpose"],
        detail=errand["detail"],
        mode=mode,
        depart_hour=depart,
        minutes=minutes,
        source="simulated",
    )
    back = depart + minutes / 60 + errand["dwell"]
    inbound = diary_service._make_trip(
        trip_id=f"{person_id}-{weekday}-{errand['diary_purpose']}-retour",
        person_id=person_id,
        weekday=weekday,
        origin=dest,
        destination=home,
        purpose="domicile",
        detail="Retour au domicile",
        mode=mode,
        depart_hour=round(back, 2),
        minutes=minutes,
        source="simulated",
    )
    return [(weekday, outbound), (weekday, inbound)]


def _regular_trips(person_id: str, city_id: str, home_id: str) -> list[tuple[int, dict]]:
    home = PLACES[home_id]
    legs: list[tuple[int, dict]] = []
    for errand in _regular_errands(city_id, home_id):
        legs.extend(_errand_loop(person_id, home, errand))
    return legs


def _home_headcount(org: dict, home_id: str) -> int:
    return sum(cluster["headcount"] for cluster in org["clusters"] if cluster["home_id"] == home_id)


def _closer_amenity(home: dict, current_id: str, role: str) -> dict | None:
    current = PLACES.get(current_id)
    nearer = _nearest_role(home, role)
    if current is None or nearer is None or nearer["id"] == current["id"]:
        return None
    current_km = _km(home["lon"], home["lat"], current["lon"], current["lat"])
    nearer_km = _km(home["lon"], home["lat"], nearer["lon"], nearer["lat"])
    if nearer_km + 0.4 >= current_km:
        return None
    return {
        "current_name": current["name"],
        "current_km": round(current_km, 1),
        "suggested_id": nearer["id"],
        "suggested_name": nearer["name"],
        "suggested_km": round(nearer_km, 1),
        "saved_km": round(current_km - nearer_km, 1),
    }


def _suggestion_row(
    *,
    home: dict,
    purpose: str,
    people: int,
    who: str,
    plural: bool,
    closer: dict,
) -> dict:
    label = _AMENITY[purpose][1]
    own = "leurs" if plural else "ses"
    if purpose == "supermarche":
        verb = "font" if plural else "fait"
        reading = (
            f"{who} {verb} {own} courses à {closer['current_name']} "
            f"({_fr(closer['current_km'])} km). "
            f"Un supermarché plus proche du domicile : {closer['suggested_name']}, "
            f"à {_fr(closer['suggested_km'])} km "
            f"({_fr(closer['saved_km'])} km en moins à chaque aller)."
        )
    else:
        verb = "se rendent" if plural else "se rend"
        reading = (
            f"{who} {verb} à {closer['current_name']} pour le culte "
            f"({_fr(closer['current_km'])} km). "
            f"{closer['suggested_name']} est à {_fr(closer['suggested_km'])} km du domicile : "
            f"{_fr(closer['saved_km'])} km en moins à chaque aller."
        )
    return {
        "id": f"{home['id']}:{purpose}",
        "purpose": purpose,
        "purpose_label": label,
        "home_name": home["name"],
        "people": people,
        "reading": reading,
        **{key: closer[key] for key in (
            "current_name",
            "current_km",
            "suggested_name",
            "suggested_km",
            "saved_km",
        )},
    }


def _named_destinations(person: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for day in person["days"]:
        for stop in day:
            purpose = stop["purpose"]
            if purpose in _AMENITY and purpose not in found:
                found[purpose] = stop["place_id"]
    return found


def _suggestions(org: dict, employee: dict | None) -> list[dict]:
    """Commerce ou culte plus proche que le lieu habituel."""
    if employee is not None:
        homes = [employee["home_id"]]
        people_of = {employee["home_id"]: 1}
        who_of = {employee["home_id"]: employee["name"]}
    else:
        homes = []
        people_of = {}
        who_of = {}
        for cluster in org["clusters"]:
            home_id = cluster["home_id"]
            if home_id not in people_of:
                homes.append(home_id)
                people_of[home_id] = 0
                count = _home_headcount(org, home_id)
                home_name = PLACES[home_id]["name"]
                who_of[home_id] = (
                    f"L'employé qui habite {home_name}"
                    if count == 1
                    else f"Les {count} employés qui habitent {home_name}"
                )
            people_of[home_id] += cluster["headcount"]
    rows = []
    for home_id in homes:
        home = PLACES[home_id]
        person = None
        if employee is not None and employee["named"]:
            person = next((item for item in PERSONS if item["id"] == employee["id"]), None)
        observed = _named_destinations(person) if person else {}
        habitual = {
            errand["diary_purpose"]: errand["dest_id"]
            for errand in _regular_errands(org["city_id"], home_id)
        }
        for purpose, (role, _label, _kind) in _AMENITY.items():
            current_id = observed.get(purpose) or habitual.get(purpose)
            if current_id is None:
                continue
            closer = _closer_amenity(home, current_id, role)
            if closer is None:
                continue
            who = employee["name"] if employee is not None else who_of[home_id]
            rows.append(
                _suggestion_row(
                    home=home,
                    purpose=purpose,
                    people=people_of[home_id],
                    who=who,
                    plural=employee is None and people_of[home_id] > 1,
                    closer=closer,
                )
            )
    return rows


def _fr(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def movements(
    organization_id: str,
    period: str,
    weekday: int,
    person_id: str | None = None,
) -> dict:
    """Déplacements de l'organisation : tout l'effectif, ou une personne."""
    diary_service._check_period(period, weekday)
    org = next((item for item in ORGANIZATIONS if item["id"] == organization_id), None)
    if org is None:
        raise ValueError("Organisation inconnue.")
    employees = _roster(org)
    if person_id:
        employee = next((item for item in employees if item["id"] == person_id), None)
        if employee is None:
            raise ValueError("Cette personne ne fait pas partie de l'organisation.")
        if employee["named"]:
            payload = diary_service.person_diary(person_id, period, weekday)
            payload["note"] = (
                f"{employee['name']} travaille à {org['name']} "
                f"({employee['home']} → {employee['work']}). " + payload["note"]
            )
        else:
            payload = _one_employee(org, employee, period, weekday)
        payload["scope"] = "person"
    else:
        payload = _whole_staff(org, employees, period, weekday)
        payload["scope"] = "all"
    payload["employees"] = [
        {key: item[key] for key in ("id", "name", "job", "home", "work", "cluster_id", "named")}
        for item in employees
    ]
    payload["organization_id"] = org["id"]
    payload["organization_name"] = org["name"]
    payload["employee_count"] = len(employees)
    focus = None
    if person_id:
        focus = next(item for item in employees if item["id"] == person_id)
    payload["suggestions"] = _suggestions(org, focus)
    return payload


def _named_people(org: dict) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    for person in PERSONS:
        if person.get("organization_id") != org["id"]:
            continue
        if person["work_id"] != org["seat_id"]:
            continue
        found.setdefault(person["home_id"], []).append(person)
    return found


def _roster(org: dict) -> list[dict]:
    seat = PLACES[org["seat_id"]]
    named_by_home = _named_people(org)
    rows = []
    for cluster in org["clusters"]:
        home = PLACES[cluster["home_id"]]
        named = named_by_home.get(cluster["home_id"], [])
        cluster_id = f"{org['id']}:{home['id']}:{cluster['function_id']}"
        for person in named:
            rows.append(
                {
                    "id": person["id"],
                    "name": person["name"],
                    "job": person["job"],
                    "home": home["name"],
                    "work": seat["name"],
                    "home_id": home["id"],
                    "function_id": cluster["function_id"],
                    "cluster_id": cluster_id,
                    "named": True,
                }
            )
        extra = max(0, cluster["headcount"] - len(named))
        for offset in range(extra):
            number = len(named) + offset + 1
            rows.append(
                {
                    "id": f"grp-{org['id']}-{cluster['function_id']}-{number}-{home['id']}",
                    "name": f"{cluster['function'][:1].upper()}{cluster['function'][1:]} {number}",
                    "job": cluster["function"],
                    "home": home["name"],
                    "work": seat["name"],
                    "home_id": home["id"],
                    "function_id": cluster["function_id"],
                    "cluster_id": cluster_id,
                    "named": False,
                }
            )
    return rows


def _cluster_of(org: dict, employee: dict) -> dict:
    for cluster in org["clusters"]:
        if cluster["home_id"] == employee["home_id"] and cluster["function_id"] == employee["function_id"]:
            return cluster
    raise ValueError("Groupe de l'employé introuvable.")


def _commute_day(org: dict, cluster: dict, person_id: str, weekday: int) -> list[dict]:
    home = PLACES[cluster["home_id"]]
    seat = PLACES[org["seat_id"]]
    mode = cluster["mode"]
    speed = diary_service.SPEED_KMH.get(mode, 16.0)
    km = diary_service._route_km(home["lon"], home["lat"], seat["lon"], seat["lat"])
    minutes = max(5, round(km / speed * 60))
    leave = 7.5 - minutes / 60
    detail = f"{cluster['function']}, {seat['name']}"
    outbound = diary_service._make_trip(
        trip_id=f"{person_id}-{weekday}-aller",
        person_id=person_id,
        weekday=weekday,
        origin=home,
        destination=seat,
        purpose="travail",
        detail=detail,
        mode=mode,
        depart_hour=leave,
        minutes=minutes,
        source="simulated",
    )
    inbound = diary_service._make_trip(
        trip_id=f"{person_id}-{weekday}-retour",
        person_id=person_id,
        weekday=weekday,
        origin=seat,
        destination=home,
        purpose="domicile",
        detail="Retour au domicile",
        mode=mode,
        depart_hour=17.0,
        minutes=minutes,
        source="simulated",
    )
    return [outbound, inbound]


def _staff_events(org: dict) -> list[tuple[int, dict, int]]:
    named_by_home = _named_people(org)
    events: list[tuple[int, dict, int]] = []
    homes_seen: set[str] = set()
    for cluster in org["clusters"]:
        named = named_by_home.get(cluster["home_id"], [])
        remaining = max(0, cluster["headcount"] - len(named))
        marker = f"{org['id']}:{cluster['home_id']}:{cluster['function_id']}"
        if remaining:
            for day in range(5):
                for trip in _commute_day(org, cluster, marker, day):
                    events.append((day, trip, remaining))
        if cluster["home_id"] not in homes_seen:
            homes_seen.add(cluster["home_id"])
            unnamed = max(0, _home_headcount(org, cluster["home_id"]) - len(named))
            if unnamed:
                habit = f"{org['id']}:{cluster['home_id']}:habitudes"
                for day, trip in _regular_trips(habit, org["city_id"], cluster["home_id"]):
                    events.append((day, trip, unnamed))
        for person in named:
            for day in range(7):
                for trip in diary_service._day_trips(person, day):
                    events.append((day, trip, 1))
    return events


def _apply(events: list[tuple[int, dict, int]], period: str, weekday: int) -> dict:
    aggregate = diary_service._empty_agg()
    for day, weight in diary_service._weighted_days(period, weekday):
        for event_day, trip, people in events:
            if event_day == day:
                diary_service._add_trip(aggregate, trip, weight * people)
    return aggregate


def _volume(events: list[tuple[int, dict, int]], period: str, weekday: int) -> dict:
    def count_day(day: int) -> int:
        return int(sum(people for event_day, _trip, people in events if event_day == day))

    if period == "day":
        slots = (
            (5, 9, "5h–9h"),
            (9, 12, "9h–12h"),
            (12, 14, "12h–14h"),
            (14, 17, "14h–17h"),
            (17, 21, "17h–21h"),
            (21, 24, "21h–24h"),
        )
        points = []
        for start, end, label in slots:
            count = sum(
                people
                for event_day, trip, people in events
                if event_day == weekday and start <= trip["depart_hour"] < end
            )
            points.append({"label": label, "value": int(count)})
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    if period == "week":
        points = [
            {"label": diary_service.WEEKDAYS[day][:3], "value": count_day(day)} for day in range(7)
        ]
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    if period == "month":
        sequence = [day for _ in range(4) for day in range(7)] + [0, 1]
        points = [
            {"label": str(index), "value": count_day(day)}
            for index, day in enumerate(sequence, start=1)
        ]
        return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}

    points = []
    for name, factor in zip(diary_service.MONTHS, diary_service.MONTH_FACTORS):
        total = sum(count_day(day) * 4 * factor for day in range(7))
        points.append({"label": name, "value": diary_service._count(total)})
    return {"question": "Combien de déplacements ?", "unit": "trajets", "points": points}


def _charts(events: list[tuple[int, dict, int]], period: str, weekday: int) -> dict:
    aggregate = _apply(events, period, weekday)
    return {
        "stats": diary_service._stats(aggregate),
        "volume": _volume(events, period, weekday),
        "purposes": {
            "question": "Pourquoi se déplace-t-on ?",
            "items": diary_service._bars(aggregate["by_purpose"], diary_service.PURPOSES, aggregate["trips"]),
        },
        "modes": {
            "question": "Quel mode est utilisé ?",
            "items": diary_service._bars(aggregate["by_mode"], diary_service.MODES, aggregate["trips"]),
        },
    }


def _flow_geojson(events: list[tuple[int, dict, int]]) -> dict:
    flows: dict[tuple[str, str, str], dict] = {}
    for _day, trip, people in events:
        key = (trip["origin_id"], trip["destination_id"], trip["purpose"])
        slot = flows.setdefault(key, {"trip": trip, "owners": {}})
        slot["owners"][trip["person_id"]] = people
    features = []
    for slot in flows.values():
        trip = slot["trip"]
        weight = sum(slot["owners"].values())
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [trip["origin"], trip["destination"]],
                },
                "properties": {
                    "id": trip["id"],
                    "label": f"{trip['origin_name']} → {trip['destination_name']}",
                    "purpose": trip["purpose_label"],
                    "detail": trip["detail"],
                    "mode": trip["mode_label"],
                    "when": trip["depart_label"],
                    "km": trip["km"],
                    "color": trip["map_color"],
                    "weight": weight,
                    "people": f"{weight} employé" if weight == 1 else f"{weight} employés",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _whole_staff(org: dict, employees: list[dict], period: str, weekday: int) -> dict:
    events = _staff_events(org)
    charts = _charts(events, period, weekday)
    seat = PLACES[org["seat_id"]]
    listed = []
    for cluster in org["clusters"]:
        home = PLACES[cluster["home_id"]]
        marker = f"{org['id']}:{cluster['home_id']}:{cluster['function_id']}"
        outbound, inbound = _commute_day(org, cluster, marker, 0)
        for trip, sense in ((outbound, "aller"), (inbound, "retour")):
            row = dict(trip)
            row["id"] = f"{marker}-{sense}"
            row["weekday_label"] = "Lun–Ven"
            row["people"] = cluster["headcount"]
            row["detail"] = f"{cluster['headcount']} {cluster['function_plural']}"
            listed.append(row)
    named_by_home = _named_people(org)
    seen_homes: set[str] = set()
    for cluster in org["clusters"]:
        home_id = cluster["home_id"]
        if home_id in seen_homes:
            continue
        seen_homes.add(home_id)
        named = named_by_home.get(home_id, [])
        people = max(0, _home_headcount(org, home_id) - len(named))
        if people <= 0:
            continue
        habit = f"{org['id']}:{home_id}:habitudes"
        for day, trip in _regular_trips(habit, org["city_id"], home_id):
            if period == "day" and day != weekday:
                continue
            row = dict(trip)
            row["people"] = people
            row["weekday_label"] = diary_service.WEEKDAYS[day]
            row["detail"] = f"{people} employés — {trip['detail']}"
            listed.append(row)
    for person in PERSONS:
        if person.get("organization_id") != org["id"]:
            continue
        for day in range(7):
            if period == "day" and day != weekday:
                continue
            for trip in diary_service._day_trips(person, day):
                if trip["purpose"] in {"travail", "domicile"}:
                    continue
                row = dict(trip)
                row["people"] = 1
                row["detail"] = f"{person['name']} — {trip['detail']}"
                listed.append(row)
    count = len(employees)
    return {
        "synthetic": True,
        "period": period,
        "weekday": weekday,
        "note": (
            f"{count} employés de {org['name']}. "
            "Le graphique additionne leurs trajets. "
            "Du lundi au vendredi, chacun fait l'aller-retour entre son domicile et "
            f"{seat['name']}. Chaque semaine s'y ajoutent les courses et le culte, "
            "au même endroit."
        ),
        "listing_note": (
            "Une ligne de navette représente tout le groupe. "
            "Les courses, le culte et les visites sont les déplacements réguliers hors travail. "
            "Les lignes au nom d'une personne viennent d'une semaine écrite une par une."
        ),
        "person": {
            "id": org["id"],
            "name": org["name"],
            "age": None,
            "job": org["kind_label"],
            "city_id": org["city_id"],
            "home": "plusieurs quartiers",
            "work": seat["name"],
            "blurb": f"Ensemble des {count} employés.",
        },
        "trips": listed,
        "geojson": _flow_geojson(events if period != "day" else [item for item in events if item[0] == weekday]),
        **charts,
    }


def _one_employee(org: dict, employee: dict, period: str, weekday: int) -> dict:
    cluster = _cluster_of(org, employee)
    events = []
    for day in range(5):
        for trip in _commute_day(org, cluster, employee["id"], day):
            events.append((day, trip, 1))
    for day, trip in _regular_trips(employee["id"], org["city_id"], employee["home_id"]):
        events.append((day, trip, 1))
    charts = _charts(events, period, weekday)
    listed = []
    for day, trip, _people in events:
        if period == "day" and day != weekday:
            continue
        listed.append(trip)
    return {
        "synthetic": True,
        "period": period,
        "weekday": weekday,
        "note": (
            f"{employee['name']} habite {employee['home']} et travaille à {employee['work']}, "
            f"comme les autres {cluster['function_plural']} de ce groupe. "
            "La semaine type ajoute aux jours ouvrés les courses et le culte, toujours au même endroit."
        ),
        "listing_note": "Navette du groupe, plus les déplacements réguliers de la semaine : courses et culte.",
        "person": {
            "id": employee["id"],
            "name": employee["name"],
            "age": None,
            "job": employee["job"],
            "city_id": org["city_id"],
            "home": employee["home"],
            "work": employee["work"],
            "blurb": (
                f"Même trajet que les {cluster['headcount']} {cluster['function_plural']} "
                f"de {employee['home']} vers {employee['work']}."
            ),
        },
        "trips": listed,
        "geojson": _flow_geojson(events if period != "day" else [item for item in events if item[0] == weekday]),
        **charts,
    }


def _clock(hour: float) -> str:
    hour = hour % 24
    whole = int(hour)
    minutes = int(round((hour - whole) * 60))
    if minutes == 60:
        whole = (whole + 1) % 24
        minutes = 0
    return f"{whole:02d}:{minutes:02d}"
