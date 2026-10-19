"""Réponses de la cohorte simulée `sim-cohort`.

Les exemples OpenAPI sont illustratifs. Les effectifs réels sont calculés
dans PostgreSQL au moment de la requête.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CohortFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    mode: str | None = None
    purpose: str | None = None
    origin_id: str | None = None
    destination_id: str | None = None
    person_id: str | None = None


class CohortPeriod(BaseModel):
    date_from: date | None = Field(description="Début de calendrier inclusif, ou null si aucune période n'est définissable.")
    date_to: date | None = Field(description="Fin de calendrier inclusive.")
    calendar_days: int | None = Field(
        description="Nombre de dates inclusives. Null si le jeu n'a aucun trajet et qu'aucune période n'est demandée."
    )
    period_source: str = Field(
        description="stored_trip_dates, request, empty_window ou unavailable."
    )


class ModeShare(BaseModel):
    mode_code: str
    label: str
    trip_count: int
    distance_km: float
    duration_min: float


class PurposeShare(BaseModel):
    purpose_code: str
    label: str
    trip_count: int
    distance_km: float
    duration_min: float


class DateShare(BaseModel):
    trip_date: date
    trip_count: int
    distance_km: float
    duration_min: float


class CohortMeta(BaseModel):
    dataset_id: str
    source: str
    simulated: bool
    data_status: str = Field(description="simulated : ce n'est pas une observation.")
    seed: int | None = Field(description="Colonne datasets.seed. Null si la base ne la renseigne pas.")
    anchor_monday: date | None
    first_trip_date: date | None = Field(description="MIN(trip_date) des étapes retenues. Null si aucune étape.")
    last_trip_date: date | None = Field(description="MAX(trip_date) des étapes retenues.")
    person_count: int
    trip_count: int
    label: str
    horizon_days: None = Field(
        description="La durée de génération n'est pas une colonne. Valeur toujours null."
    )
    horizon_note: str
    distance_method: str
    caveat: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dataset_id": "sim-cohort",
                    "source": "SIMULATED",
                    "simulated": True,
                    "data_status": "simulated",
                    "seed": 20261005,
                    "anchor_monday": "2026-10-05",
                    "first_trip_date": "2026-10-05",
                    "last_trip_date": "2026-11-01",
                    "person_count": 75,
                    "trip_count": 3452,
                    "label": "Cohorte fictive. Jeu SIMULATED.",
                    "horizon_days": None,
                    "horizon_note": "La durée de génération n'est pas stockée.",
                    "distance_method": "orthodromie_km_x_1_35",
                    "caveat": "Distances et durées simulées, pas un itinéraire pgRouting.",
                }
            ]
        }
    )


class CohortOverview(BaseModel):
    dataset_id: str
    source: str
    simulated: bool
    data_status: str
    distance_unit: str
    duration_unit: str
    distance_method: str
    calendar_rule: str
    caveat: str
    filters: CohortFilters
    period: CohortPeriod
    person_count: int = Field(description="Personnes SIMULATED du jeu, sans filtre de mode ni de motif.")
    trip_count: int
    distance_km: float
    duration_min: float
    average_distance_km: float | None = Field(description="Null s'il n'y a aucun trajet. Pas de division par zéro.")
    average_duration_min: float | None
    by_mode: list[ModeShare]
    by_purpose: list[PurposeShare]
    by_date: list[DateShare] = Field(description="Dates qui ont au moins un trajet. Les dates vides n'y figurent pas.")
    active_person_days: int | None
    empty_person_days: int | None = Field(
        description="Personnes du jeu × dates du calendrier − journées avec au moins un trajet. Null si le calendrier est indéterminé."
    )
    empty_person_days_rule: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dataset_id": "sim-cohort",
                    "source": "SIMULATED",
                    "simulated": True,
                    "data_status": "simulated",
                    "distance_unit": "km",
                    "duration_unit": "min",
                    "distance_method": "orthodromie_km_x_1_35",
                    "calendar_rule": "stored_dates",
                    "caveat": "Simulation. Pas une enquête et pas une prévision de circulation.",
                    "filters": {"date_from": None, "date_to": None, "mode": None, "purpose": None, "origin_id": None, "destination_id": None, "person_id": None},
                    "period": {
                        "date_from": "2026-10-05",
                        "date_to": "2026-11-01",
                        "calendar_days": 28,
                        "period_source": "stored_trip_dates",
                    },
                    "person_count": 75,
                    "trip_count": 3452,
                    "distance_km": 0,
                    "duration_min": 0,
                    "average_distance_km": 0,
                    "average_duration_min": 0,
                    "by_mode": [],
                    "by_purpose": [],
                    "by_date": [],
                    "active_person_days": 1584,
                    "empty_person_days": 516,
                    "empty_person_days_rule": "calendrier × personnes − journées actives",
                }
            ]
        }
    )


class CohortFlow(BaseModel):
    origin_place_id: str
    origin_name: str
    origin_lon: float
    origin_lat: float
    destination_place_id: str
    destination_name: str
    destination_lon: float
    destination_lat: float
    trip_count: int
    distance_km: float
    duration_min: float


class CohortFlows(BaseModel):
    dataset_id: str
    source: str
    simulated: bool
    data_status: str
    distance_unit: str
    duration_unit: str
    distance_method: str
    caveat: str
    filters: CohortFilters
    pair_count: int
    limit: int
    offset: int
    returned: int
    flows: list[CohortFlow]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dataset_id": "sim-cohort",
                    "source": "SIMULATED",
                    "simulated": True,
                    "data_status": "simulated",
                    "distance_unit": "km",
                    "duration_unit": "min",
                    "distance_method": "orthodromie_km_x_1_35",
                    "caveat": "Flux agrégés de la cohorte simulée. Ce ne sont pas mobility_flows ni sim_trips.",
                    "filters": {"date_from": None, "date_to": None, "mode": "bus", "purpose": None, "origin_id": None, "destination_id": None, "person_id": None},
                    "pair_count": 1,
                    "limit": 100,
                    "offset": 0,
                    "returned": 1,
                    "flows": [
                        {
                            "origin_place_id": "tana.anosy",
                            "origin_name": "Anosy",
                            "origin_lon": 47.52,
                            "origin_lat": -18.91,
                            "destination_place_id": "tana.analakely",
                            "destination_name": "Analakely",
                            "destination_lon": 47.53,
                            "destination_lat": -18.90,
                            "trip_count": 4,
                            "distance_km": 12.5,
                            "duration_min": 48,
                        }
                    ],
                }
            ]
        }
    )


class CohortTrip(BaseModel):
    trip_id: str
    person_id: str = Field(description="Pseudonyme du jeu. Pas un nom affichable.")
    trip_date: date
    depart_time: str
    arrive_time: str
    origin_place_id: str
    origin_name: str
    destination_place_id: str
    destination_name: str
    purpose_code: str
    purpose_label: str
    mode_code: str
    mode_label: str
    distance_km: float
    duration_min: float
    source: str


class CohortTrips(BaseModel):
    dataset_id: str
    source: str
    simulated: bool
    data_status: str
    distance_unit: str
    duration_unit: str
    distance_method: str
    caveat: str
    exposure: str
    filters: CohortFilters
    limit: int
    offset: int
    total: int
    returned: int
    trips: list[CohortTrip]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "dataset_id": "sim-cohort",
                    "source": "SIMULATED",
                    "simulated": True,
                    "data_status": "simulated",
                    "distance_unit": "km",
                    "duration_unit": "min",
                    "distance_method": "orthodromie_km_x_1_35",
                    "caveat": "Étapes simulées paginées. Aucun nom affichable.",
                    "exposure": "pseudonyme et lieux seulement",
                    "filters": {"date_from": "2026-10-05", "date_to": "2026-10-05", "mode": None, "purpose": None, "origin_id": None, "destination_id": None, "person_id": None},
                    "limit": 50,
                    "offset": 0,
                    "total": 120,
                    "returned": 50,
                    "trips": [],
                }
            ]
        }
    )
