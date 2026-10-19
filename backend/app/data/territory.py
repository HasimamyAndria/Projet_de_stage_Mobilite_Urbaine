"""
Territoire utilisable par l'application.

Règle produit : une ville entre dans le catalogue si sa population est
d'au moins 200 000 habitants. Pour en ajouter une, il suffit d'une entrée
dans CITY_SOURCES : des sous-villes (communes ou arrondissements), puis
des quartiers avec un point (longitude, latitude).

Le zoom de la carte suit cette hiérarchie :
    ville  →  sous-ville  →  quartier

Les populations sont des ordres de grandeur d'agglomération, à remplacer
par le recensement. Toliara (~170 000) reste hors catalogue.
"""
from __future__ import annotations

MIN_CITY_POPULATION = 200_000

ROLES = {
    "ville": "ville",
    "habitat": "habitat",
    "emploi": "emploi",
    "commerce": "commerce",
    "equipement": "équipement",
    "mixte": "mixte",
}


def _q(qid: str, name: str, lon: float, lat: float, role: str) -> dict:
    return {"id": qid, "name": name, "lon": lon, "lat": lat, "role": role}


def _c(cid: str, name: str, lon: float, lat: float, quartiers: list[dict]) -> dict:
    return {"id": cid, "name": name, "lon": lon, "lat": lat, "quartiers": quartiers}


# id, nom, surnom, population, longitude, latitude, sous-villes
CITY_SOURCES: list[dict] = [
    {
        "id": "tana",
        "name": "Antananarivo",
        "aka": "Tanà",
        "population": 2_300_000,
        "lon": 47.521,
        "lat": -18.910,
        "communes": [
            _c("tana.arr1", "1er arrondissement", 47.522, -18.911, [
                _q("tana.analakely", "Analakely", 47.5214, -18.9089, "mixte"),
                _q("tana.antaninarenina", "Antaninarenina", 47.5268, -18.9096, "emploi"),
                _q("tana.isoraka", "Isoraka", 47.5165, -18.9128, "mixte"),
                _q("tana.ambohijatovo", "Ambohijatovo", 47.5308, -18.9052, "equipement"),
                _q("tana.anosy", "Anosy", 47.5198, -18.9158, "habitat"),
            ]),
            _c("tana.arr2", "2e arrondissement", 47.540, -18.912, [
                _q("tana.ankadifotsy", "Ankadifotsy", 47.5365, -18.9075, "habitat"),
                _q("tana.ambatonakanga", "Ambatonakanga", 47.5285, -18.9190, "habitat"),
                _q("tana.ankatso", "Ankatso", 47.5588, -18.9138, "emploi"),
            ]),
            _c("tana.arr3", "3e arrondissement", 47.525, -18.888, [
                _q("tana.behoririka", "Behoririka", 47.5238, -18.8972, "mixte"),
                _q("tana.andravoahangy", "Andravoahangy", 47.5330, -18.8902, "commerce"),
                _q("tana.ankorondrano", "Ankorondrano", 47.5342, -18.8778, "commerce"),
                _q("tana.antanimena", "Antanimena", 47.5148, -18.8905, "mixte"),
            ]),
            _c("tana.arr4", "4e arrondissement", 47.500, -18.910, [
                _q("tana.isotry", "Isotry", 47.5072, -18.9108, "habitat"),
                _q("tana.andohatapenaka", "Andohatapenaka", 47.4898, -18.9032, "commerce"),
                _q("tana.anosibe", "Anosibe", 47.4975, -18.9225, "habitat"),
            ]),
            _c("tana.arr5", "5e arrondissement", 47.550, -18.870, [
                _q("tana.ivandry", "Ivandry", 47.5445, -18.8682, "commerce"),
                _q("tana.ambohimanarina", "Ambohimanarina", 47.5535, -18.8475, "habitat"),
                _q("tana.ambatomaro", "Ambatomaro", 47.5610, -18.8845, "equipement"),
            ]),
            _c("tana.arr6", "6e arrondissement", 47.515, -18.935, [
                _q("tana.anosizato", "Anosizato", 47.5155, -18.9485, "habitat"),
                _q("tana.ampefiloha", "Ampefiloha", 47.5272, -18.9238, "equipement"),
                _q("tana.andavamamba", "Andavamamba", 47.5045, -18.9360, "habitat"),
            ]),
            _c("tana.ivato", "Ivato", 47.478, -18.800, [
                _q("tana.ivato-centre", "Ivato centre", 47.4810, -18.8055, "habitat"),
                _q("tana.aeroport", "Aéroport", 47.4788, -18.7965, "emploi"),
            ]),
            _c("tana.talatamaty", "Talatamaty", 47.455, -18.845, [
                _q("tana.talatamaty-centre", "Talatamaty centre", 47.4515, -18.8490, "habitat"),
                _q("tana.ambohibao", "Ambohibao", 47.4688, -18.8375, "habitat"),
            ]),
            _c("tana.itaosy", "Itaosy", 47.470, -18.968, [
                _q("tana.itaosy-centre", "Itaosy centre", 47.4715, -18.9665, "habitat"),
            ]),
        ],
    },
    {
        "id": "toamasina",
        "name": "Toamasina",
        "aka": "Tamatave",
        "population": 326_000,
        "lon": 49.395,
        "lat": -18.149,
        "communes": [
            _c("toam.centre", "Centre-ville", 49.398, -18.149, [
                _q("toam.tanamakoa", "Tanamakoa", 49.401, -18.149, "mixte"),
                _q("toam.bazary", "Bazary Be", 49.395, -18.155, "commerce"),
            ]),
            _c("toam.tanambao", "Tanambao", 49.383, -18.156, [
                _q("toam.tanambao-q", "Tanambao", 49.382, -18.158, "habitat"),
                _q("toam.port", "Port", 49.402, -18.163, "emploi"),
            ]),
            _c("toam.mangarivotra", "Mangarivotra", 49.378, -18.140, [
                _q("toam.mangarivotra-q", "Mangarivotra", 49.376, -18.142, "habitat"),
            ]),
        ],
    },
    {
        "id": "antsirabe",
        "name": "Antsirabe",
        "aka": "Antsirabe",
        "population": 265_000,
        "lon": 47.034,
        "lat": -19.866,
        "communes": [
            _c("ants.centre", "Centre-ville", 47.034, -19.866, [
                _q("ants.antsenakely", "Antsenakely", 47.037, -19.862, "equipement"),
                _q("ants.hopital", "Hôpital", 47.032, -19.870, "equipement"),
            ]),
            _c("ants.sud", "Sud", 47.030, -19.878, [
                _q("ants.ambohimena", "Ambohimena", 47.028, -19.876, "habitat"),
                _q("ants.mahazoarivo", "Mahazoarivo", 47.040, -19.874, "commerce"),
            ]),
        ],
    },
    {
        "id": "mahajanga",
        "name": "Mahajanga",
        "aka": "Majunga",
        "population": 246_000,
        "lon": 46.316,
        "lat": -15.717,
        "communes": [
            _c("maja.centre", "Centre-ville", 46.316, -15.717, [
                _q("maja.tsaramandroso", "Tsaramandroso", 46.314, -15.720, "habitat"),
                _q("maja.bazary", "Bazary", 46.318, -15.716, "commerce"),
            ]),
            _c("maja.amborovy", "Amborovy", 46.350, -15.670, [
                _q("maja.amborovy-q", "Amborovy", 46.352, -15.668, "habitat"),
                _q("maja.aero", "Aéroport", 46.351, -15.667, "emploi"),
            ]),
        ],
    },
    {
        "id": "fianarantsoa",
        "name": "Fianarantsoa",
        "aka": "Fianara",
        "population": 210_000,
        "lon": 47.085,
        "lat": -21.453,
        "communes": [
            _c("fian.haute", "Haute-ville", 47.086, -21.450, [
                _q("fian.haute-q", "Haute-ville", 47.085, -21.452, "habitat"),
                _q("fian.ambalapaiso", "Ambalapaiso", 47.090, -21.448, "equipement"),
            ]),
            _c("fian.basse", "Basse-ville", 47.083, -21.458, [
                _q("fian.anjoma", "Anjoma", 47.082, -21.460, "commerce"),
                _q("fian.basse-q", "Basse-ville", 47.084, -21.456, "mixte"),
            ]),
        ],
    },
]


def _build() -> tuple[list[dict], dict[str, dict]]:
    cities: list[dict] = []
    places: dict[str, dict] = {}

    for source in CITY_SOURCES:
        if source["population"] < MIN_CITY_POPULATION:
            raise ValueError(
                f"{source['name']} est sous le seuil de {MIN_CITY_POPULATION} habitants."
            )

        lons = [source["lon"]]
        lats = [source["lat"]]
        city_id = source["id"]
        places[city_id] = {
            "id": city_id,
            "name": source["name"],
            "level": "city",
            "role": "ville",
            "parent_id": None,
            "parent_name": None,
            "city_id": city_id,
            "lon": source["lon"],
            "lat": source["lat"],
        }

        for commune in source["communes"]:
            places[commune["id"]] = {
                "id": commune["id"],
                "name": commune["name"],
                "level": "commune",
                "role": "mixte",
                "parent_id": city_id,
                "parent_name": source["name"],
                "city_id": city_id,
                "lon": commune["lon"],
                "lat": commune["lat"],
            }
            lons.append(commune["lon"])
            lats.append(commune["lat"])
            for quartier in commune["quartiers"]:
                if quartier["id"] in places:
                    raise ValueError(f"Lieu en double : {quartier['id']}")
                places[quartier["id"]] = {
                    **quartier,
                    "level": "quartier",
                    "parent_id": commune["id"],
                    "parent_name": commune["name"],
                    "city_id": city_id,
                }
                lons.append(quartier["lon"])
                lats.append(quartier["lat"])

        pad = 0.03
        cities.append(
            {
                "id": city_id,
                "name": source["name"],
                "aka": source["aka"],
                "population": source["population"],
                "lon": source["lon"],
                "lat": source["lat"],
                "bbox": [min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad],
            }
        )

    return cities, places


CITIES, PLACES = _build()


def city_by_id(city_id: str) -> dict | None:
    return next((city for city in CITIES if city["id"] == city_id), None)


def places_of(city_id: str) -> list[dict]:
    return [place for place in PLACES.values() if place["city_id"] == city_id]
