"""
Individus simulés — substitut d'une enquête ménage-déplacements.

Chaque personne a une semaine type (lundi = 0 … dimanche = 6).
Une journée est une suite de lieux :

    - le premier lieu a une heure de départ (`leave`)
    - chaque lieu suivant a une heure d'arrivée (`arrive`)
    - un lieu intermédiaire a aussi une heure de départ (`leave`)

Le trajet mesure le temps entre le départ du lieu précédent et l'arrivée
au lieu suivant. Le temps passé au travail ou au supermarché n'est pas
compté comme un déplacement.

Hors travail, `detail` est la phrase que la personne aurait écrite
dans le questionnaire (« courses au supermarché Jumbo », « visite famille »).

Ces personnes sont inventées. Elles ne décrivent pas des habitants réels.
"""
from __future__ import annotations

from app.data.territory import PLACES


def _stop(
    place_id: str,
    purpose: str,
    detail: str,
    *,
    leave: float | None = None,
    arrive: float | None = None,
    mode: str | None = None,
) -> dict:
    return {
        "place_id": place_id,
        "purpose": purpose,
        "detail": detail,
        "leave": leave,
        "arrive": arrive,
        "mode": mode,
    }


def _person(
    *,
    pid: str,
    name: str,
    age: int,
    job: str,
    city_id: str,
    home_id: str,
    work_id: str,
    blurb: str,
    days: list[list[dict]],
    organization_id: str | None = None,
) -> dict:
    if len(days) != 7:
        raise ValueError(f"{name} : une semaine type compte 7 jours.")
    return {
        "id": pid,
        "name": name,
        "age": age,
        "job": job,
        "city_id": city_id,
        "home_id": home_id,
        "work_id": work_id,
        "organization_id": organization_id,
        "blurb": blurb,
        "days": days,
    }


def _office(home: str, work: str, detail: str, mode: str, start: float, arrive: float, back: float) -> list[dict]:
    """Aller-retour domicile ↔ travail, sans autre motif."""
    travel = max(0.25, arrive - start)
    return [
        _stop(home, "domicile", "Départ du domicile", leave=start),
        _stop(work, "travail", detail, arrive=arrive, leave=round(back - travel, 2), mode=mode),
        _stop(home, "domicile", "Retour au domicile", arrive=back, mode=mode),
    ]


# --- Antananarivo -----------------------------------------------------------

_hery_home = "tana.anosy"
_hery_work = "tana.analakely"
_hery_plain = _office(
    _hery_home, _hery_work, "Bureau du cabinet de finance, Analakely", "bus", 6.7, 7.5, 18.1
)

_lala_home = "tana.isotry"
_lala_work = "tana.analakely"
_lala_plain = _office(
    _lala_home, _lala_work, "Étal au marché d'Analakely", "marche", 6.2, 7.0, 17.2
)

_mamy_home = "tana.ambohimanarina"
_mamy_work = "tana.ankatso"
_mamy_plain = _office(
    _mamy_home, _mamy_work, "Cours au lycée d'Ankatso", "bus", 6.4, 7.3, 17.6
)

_voah_home = "tana.talatamaty-centre"
_voah_work = "tana.ankatso"
_voah_plain = _office(
    _voah_home, _voah_work, "Cours à l'université d'Ankatso", "bus", 5.8, 7.4, 18.4
)

# --- Autres villes ----------------------------------------------------------

_jp_home = "toam.tanambao-q"
_jp_work = "toam.port"
_jp_plain = _office(_jp_home, _jp_work, "Vacation au port", "marche", 5.5, 6.2, 15.6)

_santatra_school = [
    _stop("ants.ambohimena", "domicile", "Départ du domicile", leave=6.0),
    _stop("ants.antsenakely", "ecole", "Dépose de l'enfant à l'école", arrive=6.4, leave=6.45, mode="marche"),
    _stop("ants.hopital", "travail", "Garde à l'hôpital", arrive=6.9, leave=15.0, mode="marche"),
    _stop("ants.antsenakely", "ecole", "Récupération de l'enfant à la sortie", arrive=15.3, leave=15.4, mode="marche"),
    _stop("ants.ambohimena", "domicile", "Retour au domicile", arrive=15.8, mode="marche"),
]


PERSONS: list[dict] = [
    _person(
        pid="hery",
        name="Hery Rakotoarisoa",
        age=36,
        job="Comptable",
        city_id="tana",
        home_id=_hery_home,
        work_id=_hery_work,
        blurb="Habite Anosy, travaille dans un cabinet à Analakely. Courses le vendredi, marché le samedi, culte le dimanche.",
        days=[
            _hery_plain,
            _hery_plain,
            [
                _stop(_hery_home, "domicile", "Départ du domicile", leave=6.7),
                _stop(_hery_work, "travail", "Bureau du cabinet de finance, Analakely", arrive=7.5, leave=16.0, mode="bus"),
                _stop("tana.ampefiloha", "sante", "Consultation au dispensaire d'Ampefiloha", arrive=16.4, leave=17.1, mode="bus"),
                _stop(_hery_home, "domicile", "Retour au domicile après la consultation", arrive=17.6, mode="taxi"),
            ],
            _hery_plain,
            [
                _stop(_hery_home, "domicile", "Départ du domicile", leave=6.7),
                _stop(_hery_work, "travail", "Bureau du cabinet de finance, Analakely", arrive=7.5, leave=17.0, mode="bus"),
                _stop("tana.ankorondrano", "supermarche", "Courses de la semaine au supermarché Jumbo", arrive=17.4, leave=18.1, mode="taxi"),
                _stop(_hery_home, "domicile", "Retour au domicile avec les courses", arrive=18.6, mode="taxi"),
            ],
            [
                _stop(_hery_home, "domicile", "Départ du domicile", leave=8.0),
                _stop(_hery_work, "marche", "Marché du samedi : légumes et viande", arrive=8.5, leave=10.2, mode="marche"),
                _stop(_hery_home, "domicile", "Retour au domicile", arrive=10.7, mode="taxi"),
            ],
            [
                _stop(_hery_home, "domicile", "Départ du domicile", leave=8.5),
                _stop("tana.ambohijatovo", "culte", "Culte du dimanche", arrive=9.1, leave=11.0, mode="marche"),
                _stop(_hery_home, "domicile", "Retour au domicile", arrive=11.5, mode="marche"),
            ],
        ],
    ),
    _person(
        pid="lala",
        name="Lala Rasoanirina",
        age=29,
        job="Vendeuse au marché",
        city_id="tana",
        home_id=_lala_home,
        work_id=_lala_work,
        blurb="Habite Isotry, tient un étal à Analakely. Courses le samedi, visite sa famille à Itaosy le dimanche.",
        days=[
            _lala_plain,
            _lala_plain,
            _lala_plain,
            _lala_plain,
            _lala_plain,
            [
                _stop(_lala_home, "domicile", "Départ du domicile", leave=6.2),
                _stop(_lala_work, "travail", "Étal au marché d'Analakely", arrive=7.0, leave=12.2, mode="marche"),
                _stop("tana.andohatapenaka", "supermarche", "Courses au supermarché d'Andohatapenaka", arrive=12.7, leave=13.4, mode="taxi"),
                _stop(_lala_home, "domicile", "Retour au domicile", arrive=13.9, mode="taxi"),
            ],
            [
                _stop(_lala_home, "domicile", "Départ du domicile", leave=9.0),
                _stop("tana.itaosy-centre", "visite", "Visite de la famille à Itaosy", arrive=10.2, leave=15.5, mode="bus"),
                _stop(_lala_home, "domicile", "Retour au domicile", arrive=16.6, mode="bus"),
            ],
        ],
    ),
    _person(
        pid="mamy",
        name="Mamy Andrianjafy",
        age=41,
        job="Enseignant",
        city_id="tana",
        home_id=_mamy_home,
        work_id=_mamy_work,
        blurb="Habite Ambohimanarina, enseigne à Ankatso. Courses le mercredi, rendez-vous médical le samedi.",
        days=[
            _mamy_plain,
            _mamy_plain,
            [
                _stop(_mamy_home, "domicile", "Départ du domicile", leave=6.4),
                _stop(_mamy_work, "travail", "Cours au lycée d'Ankatso", arrive=7.3, leave=16.3, mode="bus"),
                _stop("tana.ivandry", "supermarche", "Courses après les cours, supermarché d'Ivandry", arrive=16.8, leave=17.5, mode="bus"),
                _stop(_mamy_home, "domicile", "Retour au domicile", arrive=18.2, mode="bus"),
            ],
            _mamy_plain,
            _mamy_plain,
            [
                _stop(_mamy_home, "domicile", "Départ du domicile", leave=8.5),
                _stop("tana.ambatomaro", "sante", "Rendez-vous médical à Ambatomaro", arrive=9.3, leave=10.6, mode="taxi"),
                _stop(_mamy_home, "domicile", "Retour au domicile", arrive=11.3, mode="taxi"),
            ],
            [
                _stop(_mamy_home, "domicile", "Départ du domicile", leave=9.0),
                _stop("tana.ambatomaro", "culte", "Culte du dimanche", arrive=9.5, leave=11.2, mode="marche"),
                _stop(_mamy_home, "domicile", "Retour au domicile", arrive=11.8, mode="marche"),
            ],
        ],
    ),
    _person(
        pid="voahangy",
        name="Voahangy Raharinosy",
        age=23,
        job="Étudiante",
        city_id="tana",
        home_id=_voah_home,
        work_id=_voah_work,
        blurb="Habite Talatamaty, étudie à Ankatso. Long trajet en bus. Sortie le vendredi, courses le samedi.",
        days=[
            _voah_plain,
            _voah_plain,
            _voah_plain,
            _voah_plain,
            [
                _stop(_voah_home, "domicile", "Départ du domicile", leave=5.8),
                _stop(_voah_work, "travail", "Cours à l'université d'Ankatso", arrive=7.4, leave=16.6, mode="bus"),
                _stop("tana.ivandry", "loisirs", "Sortie au centre commercial d'Ivandry", arrive=17.1, leave=19.0, mode="bus"),
                _stop(_voah_home, "domicile", "Retour au domicile", arrive=19.8, mode="taxi"),
            ],
            [
                _stop(_voah_home, "domicile", "Départ du domicile", leave=9.0),
                _stop("tana.ankorondrano", "supermarche", "Courses au supermarché Jumbo", arrive=10.1, leave=11.4, mode="bus"),
                _stop(_voah_home, "domicile", "Retour au domicile", arrive=12.6, mode="bus"),
            ],
            [
                _stop(_voah_home, "domicile", "Départ du domicile", leave=10.0),
                _stop("tana.ambohibao", "visite", "Déjeuner chez une amie à Ambohibao", arrive=10.4, leave=13.6, mode="taxi"),
                _stop(_voah_home, "domicile", "Retour au domicile", arrive=14.1, mode="taxi"),
            ],
        ],
    ),
    _person(
        pid="aina",
        name="Aina Rakotomalala",
        age=44,
        job="Cadre de direction",
        city_id="tana",
        home_id="tana.talatamaty-centre",
        work_id="tana.ankorondrano",
        organization_id="drf-ankorondrano",
        blurb=(
            "Habite Talatamaty, cadre à la Direction régionale des Finances à Ankorondrano. "
            "Elle illustre le groupe de 30 cadres qui font ce trajet en bus les jours ouvrés."
        ),
        days=[
            _office(
                "tana.talatamaty-centre",
                "tana.ankorondrano",
                "Bureau de direction, Ankorondrano",
                "bus",
                6.1,
                7.5,
                18.4,
            ),
            _office(
                "tana.talatamaty-centre",
                "tana.ankorondrano",
                "Bureau de direction, Ankorondrano",
                "bus",
                6.1,
                7.5,
                18.4,
            ),
            _office(
                "tana.talatamaty-centre",
                "tana.ankorondrano",
                "Bureau de direction, Ankorondrano",
                "bus",
                6.1,
                7.5,
                18.4,
            ),
            _office(
                "tana.talatamaty-centre",
                "tana.ankorondrano",
                "Bureau de direction, Ankorondrano",
                "bus",
                6.1,
                7.5,
                18.4,
            ),
            [
                _stop("tana.talatamaty-centre", "domicile", "Départ du domicile", leave=6.1),
                _stop(
                    "tana.ankorondrano",
                    "travail",
                    "Bureau de direction, Ankorondrano",
                    arrive=7.5,
                    leave=16.8,
                    mode="bus",
                ),
                _stop(
                    "tana.ivandry",
                    "supermarche",
                    "Courses de la semaine au centre commercial d'Ivandry",
                    arrive=17.4,
                    leave=18.2,
                    mode="bus",
                ),
                _stop("tana.talatamaty-centre", "domicile", "Retour au domicile", arrive=19.1, mode="taxi"),
            ],
            [
                _stop("tana.talatamaty-centre", "domicile", "Départ du domicile", leave=9.0),
                _stop(
                    "tana.ambohibao",
                    "visite",
                    "Visite familiale à Ambohibao",
                    arrive=9.4,
                    leave=12.5,
                    mode="taxi",
                ),
                _stop("tana.talatamaty-centre", "domicile", "Retour au domicile", arrive=13.0, mode="taxi"),
            ],
            [
                _stop("tana.talatamaty-centre", "domicile", "Départ du domicile", leave=8.5),
                _stop("tana.ambohibao", "culte", "Culte du dimanche à Ambohibao", arrive=9.0, leave=11.2, mode="bus"),
                _stop("tana.talatamaty-centre", "domicile", "Retour au domicile", arrive=11.7, mode="bus"),
            ],
        ],
    ),
    _person(
        pid="hanta",
        name="Hanta Randrianarisoa",
        age=38,
        job="Cheffe de service",
        city_id="tana",
        home_id="tana.ambohibao",
        work_id="tana.ankorondrano",
        organization_id="drf-ankorondrano",
        blurb=(
            "Habite Ambohibao, cheffe de service à Ankorondrano. "
            "Elle illustre le groupe de 22 chefs de service qui font ce trajet en taxi."
        ),
        days=[
            _office(
                "tana.ambohibao",
                "tana.ankorondrano",
                "Service de l'inspection, Ankorondrano",
                "taxi",
                6.4,
                7.4,
                18.0,
            ),
            _office(
                "tana.ambohibao",
                "tana.ankorondrano",
                "Service de l'inspection, Ankorondrano",
                "taxi",
                6.4,
                7.4,
                18.0,
            ),
            _office(
                "tana.ambohibao",
                "tana.ankorondrano",
                "Service de l'inspection, Ankorondrano",
                "taxi",
                6.4,
                7.4,
                18.0,
            ),
            _office(
                "tana.ambohibao",
                "tana.ankorondrano",
                "Service de l'inspection, Ankorondrano",
                "taxi",
                6.4,
                7.4,
                18.0,
            ),
            _office(
                "tana.ambohibao",
                "tana.ankorondrano",
                "Service de l'inspection, Ankorondrano",
                "taxi",
                6.4,
                7.4,
                18.0,
            ),
            [
                _stop("tana.ambohibao", "domicile", "Départ du domicile", leave=8.5),
                _stop(
                    "tana.talatamaty-centre",
                    "supermarche",
                    "Courses au marché de Talatamaty",
                    arrive=9.0,
                    leave=10.2,
                    mode="taxi",
                ),
                _stop("tana.ambohibao", "domicile", "Retour au domicile", arrive=10.7, mode="taxi"),
            ],
            [
                _stop("tana.ambohibao", "domicile", "Départ du domicile", leave=9.0),
                _stop("tana.ivato-centre", "visite", "Visite de la famille à Ivato", arrive=9.6, leave=14.5, mode="bus"),
                _stop("tana.ambohibao", "domicile", "Retour au domicile", arrive=15.2, mode="bus"),
            ],
        ],
    ),
    _person(
        pid="jeanpierre",
        name="Jean Pierre Rakotobe",
        age=48,
        job="Docker",
        city_id="toamasina",
        home_id=_jp_home,
        work_id=_jp_work,
        blurb="Habite Tanambao, travaille au port à pied. Marché le samedi, culte le dimanche.",
        days=[
            _jp_plain,
            _jp_plain,
            _jp_plain,
            _jp_plain,
            _jp_plain,
            [
                _stop(_jp_home, "domicile", "Départ du domicile", leave=7.5),
                _stop("toam.bazary", "marche", "Marché de Bazary Be : riz et poisson", arrive=8.1, leave=9.4, mode="marche"),
                _stop(_jp_home, "domicile", "Retour au domicile", arrive=10.0, mode="marche"),
            ],
            [
                _stop(_jp_home, "domicile", "Départ du domicile", leave=8.0),
                _stop("toam.tanamakoa", "culte", "Culte du dimanche", arrive=8.6, leave=10.8, mode="marche"),
                _stop(_jp_home, "domicile", "Retour au domicile", arrive=11.4, mode="marche"),
            ],
        ],
    ),
    _person(
        pid="santatra",
        name="Santatra Razafindrakoto",
        age=34,
        job="Infirmière",
        city_id="antsirabe",
        home_id="ants.ambohimena",
        work_id="ants.hopital",
        blurb="Habite Ambohimena. Dépose son enfant avant la garde à l'hôpital. Courses le mercredi et le samedi.",
        days=[
            _santatra_school,
            _santatra_school,
            [
                _stop("ants.ambohimena", "domicile", "Départ du domicile", leave=6.0),
                _stop("ants.antsenakely", "ecole", "Dépose de l'enfant à l'école", arrive=6.4, leave=6.45, mode="marche"),
                _stop("ants.hopital", "travail", "Garde à l'hôpital", arrive=6.9, leave=14.8, mode="marche"),
                _stop("ants.antsenakely", "ecole", "Récupération de l'enfant à la sortie", arrive=15.1, leave=15.2, mode="marche"),
                _stop("ants.mahazoarivo", "supermarche", "Courses au supermarché de Mahazoarivo", arrive=15.6, leave=16.3, mode="marche"),
                _stop("ants.ambohimena", "domicile", "Retour au domicile", arrive=16.9, mode="taxi"),
            ],
            _santatra_school,
            _santatra_school,
            [
                _stop("ants.ambohimena", "domicile", "Départ du domicile", leave=8.0),
                _stop("ants.mahazoarivo", "supermarche", "Courses de la semaine au supermarché", arrive=8.5, leave=9.6, mode="marche"),
                _stop("ants.ambohimena", "domicile", "Retour au domicile", arrive=10.1, mode="marche"),
            ],
            [
                _stop("ants.ambohimena", "domicile", "Départ du domicile", leave=8.5),
                _stop("ants.antsenakely", "culte", "Culte du dimanche", arrive=9.0, leave=11.0, mode="marche"),
                _stop("ants.ambohimena", "domicile", "Retour au domicile", arrive=11.5, mode="marche"),
            ],
        ],
    ),
    _person(
        pid="fara",
        name="Fara Abdallah",
        age=39,
        job="Commerçante",
        city_id="mahajanga",
        home_id="maja.tsaramandroso",
        work_id="maja.bazary",
        blurb="Habite Tsaramandroso, vend au bazary. Visite sa famille à Amborovy le dimanche.",
        days=[
            _office("maja.tsaramandroso", "maja.bazary", "Étal au bazary", "marche", 6.5, 7.0, 17.0),
            _office("maja.tsaramandroso", "maja.bazary", "Étal au bazary", "marche", 6.5, 7.0, 17.0),
            [
                _stop("maja.tsaramandroso", "domicile", "Départ du domicile", leave=6.5),
                _stop("maja.bazary", "travail", "Étal au bazary", arrive=7.0, leave=12.0, mode="marche"),
                _stop("maja.amborovy-q", "sante", "Consultation au centre de santé d'Amborovy", arrive=12.6, leave=13.8, mode="taxi"),
                _stop("maja.tsaramandroso", "domicile", "Retour au domicile", arrive=14.5, mode="taxi"),
            ],
            _office("maja.tsaramandroso", "maja.bazary", "Étal au bazary", "marche", 6.5, 7.0, 17.0),
            _office("maja.tsaramandroso", "maja.bazary", "Étal au bazary", "marche", 6.5, 7.0, 17.0),
            _office("maja.tsaramandroso", "maja.bazary", "Étal au bazary", "marche", 6.5, 7.0, 16.2),
            [
                _stop("maja.tsaramandroso", "domicile", "Départ du domicile", leave=9.0),
                _stop("maja.amborovy-q", "visite", "Visite de la famille à Amborovy", arrive=9.6, leave=15.0, mode="bus"),
                _stop("maja.tsaramandroso", "domicile", "Retour au domicile", arrive=15.7, mode="bus"),
            ],
        ],
    ),
    _person(
        pid="tiana",
        name="Tiana Rasolo",
        age=26,
        job="Étudiante",
        city_id="fianarantsoa",
        home_id="fian.haute-q",
        work_id="fian.anjoma",
        blurb="Habite la haute-ville, suit des cours à Anjoma. Marché le samedi, culte le dimanche.",
        days=[
            _office("fian.haute-q", "fian.anjoma", "Cours à Anjoma", "marche", 6.8, 7.3, 17.4),
            _office("fian.haute-q", "fian.anjoma", "Cours à Anjoma", "marche", 6.8, 7.3, 17.4),
            _office("fian.haute-q", "fian.anjoma", "Cours à Anjoma", "marche", 6.8, 7.3, 17.4),
            _office("fian.haute-q", "fian.anjoma", "Cours à Anjoma", "marche", 6.8, 7.3, 17.4),
            [
                _stop("fian.haute-q", "domicile", "Départ du domicile", leave=6.8),
                _stop("fian.anjoma", "travail", "Cours à Anjoma", arrive=7.3, leave=16.0, mode="marche"),
                _stop("fian.basse-q", "supermarche", "Courses au supermarché de la basse-ville", arrive=16.3, leave=17.0, mode="marche"),
                _stop("fian.haute-q", "domicile", "Retour au domicile", arrive=17.5, mode="marche"),
            ],
            [
                _stop("fian.haute-q", "domicile", "Départ du domicile", leave=8.0),
                _stop("fian.anjoma", "marche", "Marché de la basse-ville", arrive=8.5, leave=10.2, mode="marche"),
                _stop("fian.haute-q", "domicile", "Retour au domicile", arrive=10.8, mode="marche"),
            ],
            [
                _stop("fian.haute-q", "domicile", "Départ du domicile", leave=8.2),
                _stop("fian.ambalapaiso", "culte", "Culte à Ambalapaiso", arrive=8.6, leave=10.8, mode="marche"),
                _stop("fian.haute-q", "domicile", "Retour au domicile", arrive=11.2, mode="marche"),
            ],
        ],
    ),
]


def _check() -> None:
    for person in PERSONS:
        for key in ("home_id", "work_id"):
            if person[key] not in PLACES:
                raise ValueError(f"{person['id']} : lieu inconnu {person[key]}")
            if PLACES[person[key]]["city_id"] != person["city_id"]:
                raise ValueError(f"{person['id']} : {key} hors de sa ville")
        for weekday, stops in enumerate(person["days"]):
            if len(stops) < 1:
                raise ValueError(f"{person['id']} jour {weekday} vide")
            previous = -1.0
            for index, stop in enumerate(stops):
                if stop["place_id"] not in PLACES:
                    raise ValueError(f"{person['id']} : lieu inconnu {stop['place_id']}")
                if index == 0 and stop["leave"] is None:
                    raise ValueError(f"{person['id']} jour {weekday} : départ manquant")
                if index > 0 and stop["arrive"] is None:
                    raise ValueError(f"{person['id']} jour {weekday} : arrivée manquante")
                if index < len(stops) - 1 and stop["leave"] is None:
                    raise ValueError(f"{person['id']} jour {weekday} : heure de départ manquante")
                for mark in (stop["arrive"], stop["leave"]):
                    if mark is None:
                        continue
                    if mark < previous:
                        raise ValueError(f"{person['id']} jour {weekday} : heures dans le désordre")
                    previous = mark


_check()


def person_by_id(person_id: str) -> dict | None:
    return next((person for person in PERSONS if person["id"] == person_id), None)


def persons_of(city_id: str) -> list[dict]:
    return [person for person in PERSONS if person["city_id"] == city_id]
