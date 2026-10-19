"""
Effectifs simulés par organisation.

Aucune enquête n'a encore été collectée. Chaque groupe compte au moins
20 personnes qui partagent le même quartier de domicile, le même lieu
de travail et la même fonction (ministère, université, marché, hôpital, aéroport).

Les déplacements hors travail ne sont retenus que s'ils reviennent
chaque semaine au même endroit.
"""
from __future__ import annotations

from app.data.territory import PLACES

MIN_HEADCOUNT = 20

KINDS = {
    "ministere": "ministère",
    "universite": "université",
    "sante": "santé",
    "commerce": "commerce",
    "entreprise": "entreprise",
}

# Postes de bureau déplaçables vers une annexe, ou postes qui exigent le site.
FUNCTIONS = {
    "cadre": {
        "label": "cadre de direction",
        "plural": "cadres de direction",
        "grade": "considerable",
        "relocatable": True,
    },
    "chef": {
        "label": "chef de service",
        "plural": "chefs de service",
        "grade": "considerable",
        "relocatable": True,
    },
    "charge": {
        "label": "chargé de mission",
        "plural": "chargés de mission",
        "grade": "considerable",
        "relocatable": True,
    },
    "responsable": {
        "label": "responsable de pôle",
        "plural": "responsables de pôle",
        "grade": "considerable",
        "relocatable": True,
    },
    "agent": {
        "label": "agent administratif",
        "plural": "agents administratifs",
        "grade": "bureau",
        "relocatable": True,
    },
    "enseignant": {
        "label": "enseignant",
        "plural": "enseignants",
        "grade": "terrain",
        "relocatable": False,
    },
    "soignant": {
        "label": "soignant",
        "plural": "soignants",
        "grade": "terrain",
        "relocatable": False,
    },
    "vendeur": {
        "label": "vendeur",
        "plural": "vendeurs",
        "grade": "terrain",
        "relocatable": False,
    },
    "exploitation": {
        "label": "poste d'exploitation sur site",
        "plural": "postes d'exploitation sur site",
        "grade": "terrain",
        "relocatable": False,
    },
}

DEFAULT_FUNCTION = {
    "ministere": "agent",
    "entreprise": "exploitation",
    "universite": "enseignant",
    "sante": "soignant",
    "commerce": "vendeur",
}


def _org(
    *,
    oid: str,
    name: str,
    kind: str,
    city_id: str,
    seat_id: str,
    activity: str,
    clusters: list[tuple],
) -> dict:
    return {
        "id": oid,
        "name": name,
        "kind": kind,
        "kind_label": KINDS[kind],
        "city_id": city_id,
        "seat_id": seat_id,
        "activity": activity,
        "clusters": [_cluster_row(row, kind) for row in clusters],
    }


def _cluster_row(row: tuple, kind: str) -> dict:
    if len(row) == 3:
        home_id, headcount, mode = row
        function_id = DEFAULT_FUNCTION[kind]
    elif len(row) == 4:
        home_id, headcount, mode, function_id = row
    else:
        raise ValueError("Un groupe d'employés attend domicile, effectif, mode et, au besoin, la fonction.")
    function = FUNCTIONS[function_id]
    return {
        "home_id": home_id,
        "headcount": int(headcount),
        "mode": mode,
        "function_id": function_id,
        "function": function["label"],
        "function_plural": function["plural"],
        "grade": function["grade"],
        "relocatable": function["relocatable"],
    }


def _errand(
    *,
    city_id: str,
    home_id: str,
    dest_id: str,
    purpose: str,
    detail: str,
    headcount: int,
    cadence: str,
    mode: str,
) -> dict:
    return {
        "city_id": city_id,
        "home_id": home_id,
        "dest_id": dest_id,
        "purpose": purpose,
        "detail": detail,
        "headcount": headcount,
        "cadence": cadence,
        "mode": mode,
    }


ORGANIZATIONS: list[dict] = [
    _org(
        oid="min-finances",
        name="Ministère des Finances",
        kind="ministere",
        city_id="tana",
        seat_id="tana.analakely",
        activity="bureaux et guichets de l'administration fiscale",
        clusters=[
            ("tana.anosy", 28, "bus", "agent"),
            ("tana.isotry", 22, "bus", "agent"),
            ("tana.ivato-centre", 24, "bus", "cadre"),
            ("tana.anosizato", 20, "bus", "chef"),
            ("tana.talatamaty-centre", 20, "bus", "cadre"),
        ],
    ),
    _org(
        oid="drf-ankorondrano",
        name="Direction régionale des Finances — Ankorondrano",
        kind="ministere",
        city_id="tana",
        seat_id="tana.ankorondrano",
        activity="branche d'État : direction, inspection et encadrement",
        clusters=[
            ("tana.talatamaty-centre", 30, "bus", "cadre"),
            ("tana.ambohibao", 22, "taxi", "chef"),
            ("tana.ivato-centre", 24, "bus", "charge"),
            ("tana.ambatomaro", 20, "bus", "responsable"),
            ("tana.behoririka", 20, "bus", "agent"),
        ],
    ),
    _org(
        oid="holding-ivandry",
        name="Holding Rasoanaivo — siège Ivandry",
        kind="entreprise",
        city_id="tana",
        seat_id="tana.ivandry",
        activity="siège d'un groupe privé : direction et fonctions support",
        clusters=[
            ("tana.talatamaty-centre", 26, "bus", "cadre"),
            ("tana.ambohibao", 20, "taxi", "chef"),
            ("tana.itaosy-centre", 22, "bus", "charge"),
        ],
    ),
    _org(
        oid="marche-analakely",
        name="Marché d'Analakely",
        kind="commerce",
        city_id="tana",
        seat_id="tana.analakely",
        activity="étals et commerce de détail",
        clusters=[
            ("tana.isotry", 30, "marche"),
            ("tana.andohatapenaka", 22, "taxi"),
            ("tana.anosibe", 20, "bus"),
        ],
    ),
    _org(
        oid="univ-ankatso",
        name="Université d'Ankatso",
        kind="universite",
        city_id="tana",
        seat_id="tana.ankatso",
        activity="cours et campus",
        clusters=[
            ("tana.ambohimanarina", 26, "bus"),
            ("tana.talatamaty-centre", 30, "bus"),
            ("tana.ambohibao", 22, "bus"),
            ("tana.ambatomaro", 20, "bus"),
        ],
    ),
    _org(
        oid="aeroport-ivato",
        name="Aéroport d'Ivato",
        kind="entreprise",
        city_id="tana",
        seat_id="tana.aeroport",
        activity="emplois aéroportuaires",
        clusters=[
            ("tana.ivato-centre", 32, "marche"),
            ("tana.ambohibao", 20, "bus"),
        ],
    ),
    _org(
        oid="min-sante",
        name="Ministère de la Santé",
        kind="sante",
        city_id="tana",
        seat_id="tana.ampefiloha",
        activity="administration sanitaire et dispensaire",
        clusters=[
            ("tana.andavamamba", 24, "bus"),
            ("tana.anosizato", 22, "bus"),
            ("tana.anosy", 20, "bus"),
        ],
    ),
    _org(
        oid="centre-ivandry",
        name="Centre commercial d'Ivandry",
        kind="commerce",
        city_id="tana",
        seat_id="tana.ivandry",
        activity="commerces et loisirs",
        clusters=[
            ("tana.ambatomaro", 20, "bus"),
            ("tana.ankorondrano", 24, "marche"),
            ("tana.ambohijatovo", 20, "taxi"),
        ],
    ),
    _org(
        oid="exemple-bassin-nord",
        name="Cabinet du centre (exemple simulé)",
        kind="entreprise",
        city_id="tana",
        seat_id="tana.antaninarenina",
        activity=(
            "jeu d'exemple explicite : 30 employés à Ivato, 25 à Talatamaty "
            "et 20 à Ambohibao, tous vers le même siège. Données simulées."
        ),
        clusters=[
            ("tana.ivato-centre", 30, "bus", "cadre"),
            ("tana.talatamaty-centre", 25, "bus", "cadre"),
            ("tana.ambohibao", 20, "taxi", "chef"),
        ],
    ),
    _org(
        oid="port-toamasina",
        name="Port de Toamasina",
        kind="entreprise",
        city_id="toamasina",
        seat_id="toam.port",
        activity="manutention et activités portuaires",
        clusters=[
            ("toam.tanambao-q", 30, "marche"),
            ("toam.mangarivotra-q", 22, "bus"),
        ],
    ),
    _org(
        oid="hopital-antsirabe",
        name="Hôpital d'Antsirabe",
        kind="sante",
        city_id="antsirabe",
        seat_id="ants.hopital",
        activity="soins et gardes",
        clusters=[
            ("ants.ambohimena", 28, "marche"),
            ("ants.mahazoarivo", 20, "marche"),
        ],
    ),
    _org(
        oid="bazary-majunga",
        name="Bazary de Mahajanga",
        kind="commerce",
        city_id="mahajanga",
        seat_id="maja.bazary",
        activity="commerce de détail",
        clusters=[
            ("maja.tsaramandroso", 26, "marche"),
            ("maja.amborovy-q", 20, "bus"),
        ],
    ),
    _org(
        oid="campus-anjoma",
        name="Campus d'Anjoma",
        kind="universite",
        city_id="fianarantsoa",
        seat_id="fian.anjoma",
        activity="cours",
        clusters=[
            ("fian.haute-q", 24, "marche"),
            ("fian.basse-q", 20, "marche"),
        ],
    ),
]


REGULAR_ERRANDS: list[dict] = [
    _errand(
        city_id="tana",
        home_id="tana.anosy",
        dest_id="tana.ankorondrano",
        purpose="courses",
        detail="Courses de la semaine au supermarché d'Ankorondrano",
        headcount=20,
        cadence="chaque vendredi",
        mode="taxi",
    ),
    _errand(
        city_id="tana",
        home_id="tana.ivato-centre",
        dest_id="tana.ankorondrano",
        purpose="courses",
        detail="Courses de la semaine au supermarché d'Ankorondrano",
        headcount=20,
        cadence="chaque samedi",
        mode="bus",
    ),
    _errand(
        city_id="tana",
        home_id="tana.talatamaty-centre",
        dest_id="tana.ankorondrano",
        purpose="courses",
        detail="Courses de la semaine au supermarché d'Ankorondrano",
        headcount=22,
        cadence="chaque samedi",
        mode="bus",
    ),
    _errand(
        city_id="tana",
        home_id="tana.isotry",
        dest_id="tana.andohatapenaka",
        purpose="courses",
        detail="Courses au supermarché d'Andohatapenaka",
        headcount=20,
        cadence="chaque samedi",
        mode="taxi",
    ),
    _errand(
        city_id="tana",
        home_id="tana.ambohimanarina",
        dest_id="tana.ambatomaro",
        purpose="culte",
        detail="Culte du dimanche à Ambatomaro",
        headcount=20,
        cadence="chaque dimanche",
        mode="bus",
    ),
    _errand(
        city_id="tana",
        home_id="tana.anosizato",
        dest_id="tana.ambohijatovo",
        purpose="culte",
        detail="Culte du dimanche à Ambohijatovo",
        headcount=20,
        cadence="chaque dimanche",
        mode="bus",
    ),
    _errand(
        city_id="toamasina",
        home_id="toam.tanambao-q",
        dest_id="toam.bazary",
        purpose="courses",
        detail="Marché de Bazary Be",
        headcount=20,
        cadence="chaque samedi",
        mode="marche",
    ),
    _errand(
        city_id="antsirabe",
        home_id="ants.ambohimena",
        dest_id="ants.mahazoarivo",
        purpose="courses",
        detail="Courses au supermarché de Mahazoarivo",
        headcount=20,
        cadence="chaque mercredi",
        mode="marche",
    ),
    _errand(
        city_id="mahajanga",
        home_id="maja.tsaramandroso",
        dest_id="maja.amborovy-q",
        purpose="visite",
        detail="Visite hebdomadaire de la famille à Amborovy",
        headcount=20,
        cadence="chaque dimanche",
        mode="bus",
    ),
    _errand(
        city_id="fianarantsoa",
        home_id="fian.haute-q",
        dest_id="fian.ambalapaiso",
        purpose="culte",
        detail="Culte à Ambalapaiso",
        headcount=20,
        cadence="chaque dimanche",
        mode="marche",
    ),
]


def _check() -> None:
    seen: set[str] = set()
    for org in ORGANIZATIONS:
        if org["id"] in seen:
            raise ValueError(f"Organisation en double : {org['id']}")
        seen.add(org["id"])
        seat = PLACES.get(org["seat_id"])
        if seat is None or seat["level"] != "quartier":
            raise ValueError(f"{org['id']} : siège inconnu")
        if seat["city_id"] != org["city_id"]:
            raise ValueError(f"{org['id']} : siège hors de la ville")
        if org["kind"] not in KINDS:
            raise ValueError(f"{org['id']} : type inconnu")
        for cluster in org["clusters"]:
            home = PLACES.get(cluster["home_id"])
            if home is None or home["level"] != "quartier":
                raise ValueError(f"{org['id']} : domicile inconnu {cluster['home_id']}")
            if home["city_id"] != org["city_id"]:
                raise ValueError(f"{org['id']} : domicile hors de la ville")
            if cluster["headcount"] < MIN_HEADCOUNT:
                raise ValueError(f"{org['id']} : groupe sous {MIN_HEADCOUNT}")
            if cluster["function_id"] not in FUNCTIONS:
                raise ValueError(f"{org['id']} : fonction inconnue")
    for errand in REGULAR_ERRANDS:
        if errand["purpose"] == "travail":
            raise ValueError("Un trajet hors travail ne peut pas avoir le motif travail")
        if errand["headcount"] < MIN_HEADCOUNT:
            raise ValueError("Course régulière sous le seuil de groupe")
        for key in ("home_id", "dest_id"):
            place = PLACES.get(errand[key])
            if place is None or place["city_id"] != errand["city_id"]:
                raise ValueError(f"Course régulière : lieu invalide {errand[key]}")


_check()
