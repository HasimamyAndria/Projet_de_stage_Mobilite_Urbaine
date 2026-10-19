"""Correspondance entre le journal historique et le contrat PostgreSQL.

Les codes renvoyés à l'écran restent ceux de `diary.PURPOSES`.
La base stocke les codes canoniques de la migration 30.
"""
from __future__ import annotations

from datetime import date, time

DATASET_ID = "diary-week"
DATASET_LABEL = (
    "Journal de démonstration — huit personnes inventées. "
    "Jeu SIMULATED, pas une enquête observée."
)
DATASET_SEED = 8
# Lundi fixe. La semaine type n'est pas un calendrier observé.
ANCHOR_MONDAY = date(2026, 10, 5)

# Motif d'arrivée du journal -> code canonique.
# `domicile` sur l'arrivée est un retour, pas le motif du lieu de départ.
DIARY_TO_CODE = {
    "travail": "travail",
    "domicile": "retour_domicile",
    "supermarche": "courses_supermarche",
    "marche": "courses_marche",
    "ecole": "ecole",
    "sante": "sante",
    "loisirs": "loisirs",
    "culte": "culte",
    "visite": "visite",
    "autre": "autre",
}

CODE_TO_DIARY = {code: diary for diary, code in DIARY_TO_CODE.items()}


def hour_to_time(value: float) -> time:
    """Heure décimale du journal (6.45 = 6 h + 0,45 h) vers une heure d'horloge."""
    value = value % 24
    hour = int(value)
    minute = int(round((value - hour) * 60))
    second = 0
    if minute == 60:
        hour = (hour + 1) % 24
        minute = 0
    return time(hour, minute, second)


def time_to_hour(value: time) -> float:
    return round(value.hour + value.minute / 60 + value.second / 3600, 2)
