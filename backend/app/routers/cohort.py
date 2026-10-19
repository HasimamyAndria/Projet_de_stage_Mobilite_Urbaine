"""Lecture agrégée de la cohorte simulée sim-cohort.

Ces routes ne lisent pas diary-week, mobility_flows, sim_trips, le réseau
routier ni les zones. Les étapes individuelles sont paginées et ne portent
pas de nom affichable.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import ProgrammingError

from app.schemas.cohort import CohortFlows, CohortMeta, CohortOverview, CohortTrips
from app.services import cohort as cohort_service
from app.services.cohort import (
    DEFAULT_FLOW_PAGE,
    DEFAULT_TRIP_PAGE,
    MAX_FLOW_PAGE,
    MAX_TRIP_PAGE,
    CohortNotFound,
    CohortNotSimulated,
    CohortValidationError,
)

router = APIRouter(prefix="/api/mobility/cohort", tags=["Cohorte simulée"])


def _respond(fn):
    try:
        return fn()
    except CohortNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CohortNotSimulated as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CohortValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail="Tables du contrat de mobilité inaccessibles.",
        ) from exc


@router.get(
    "/meta",
    response_model=CohortMeta,
    summary="Métadonnées du jeu simulé sim-cohort",
    responses={
        404: {"description": "datasets ne contient pas sim-cohort"},
        409: {"description": "La ligne existe mais source n'est pas SIMULATED"},
        503: {"description": "Tables du contrat inaccessibles"},
    },
)
def cohort_meta():
    """Effectifs et dates lus dans PostgreSQL. `horizon_days` reste null : la durée de génération n'est pas une colonne."""
    return _respond(cohort_service.get_meta)


@router.get(
    "/overview",
    response_model=CohortOverview,
    summary="Vue agrégée de la cohorte simulée",
    responses={
        400: {"description": "Période ou code de mode/motif refusé"},
        404: {"description": "Jeu sim-cohort absent"},
        409: {"description": "Jeu non simulé"},
        503: {"description": "Tables du contrat inaccessibles"},
    },
)
def cohort_overview(
    date_from: date | None = Query(None, description="Début inclusif. Défaut : première date de trajet stockée."),
    date_to: date | None = Query(None, description="Fin inclusive. Défaut : dernière date de trajet stockée."),
    mode: str | None = Query(None, max_length=40, description="Code de la table modes, par exemple bus."),
    purpose: str | None = Query(None, max_length=40, description="Code de la table purposes, par exemple travail."),
):
    """Totaux, moyennes et répartitions. Les moyennes sont nulles s'il n'y a aucun trajet."""
    return _respond(
        lambda: cohort_service.get_overview(
            date_from=date_from,
            date_to=date_to,
            mode=mode,
            purpose=purpose,
        )
    )


@router.get(
    "/flows",
    response_model=CohortFlows,
    summary="Flux origine-destination de la cohorte simulée",
    responses={
        400: {"description": "Filtre ou pagination refusé"},
        404: {"description": "Jeu sim-cohort absent"},
        409: {"description": "Jeu non simulé"},
        503: {"description": "Tables du contrat inaccessibles"},
    },
)
def cohort_flows(
    date_from: date | None = Query(None, description="Début inclusif."),
    date_to: date | None = Query(None, description="Fin inclusive."),
    mode: str | None = Query(None, max_length=40, description="Code de mode. Agrège ce mode seulement."),
    purpose: str | None = Query(None, max_length=40, description="Code de motif. Agrège ce motif seulement."),
    origin_id: str | None = Query(None, max_length=80, description="Identifiant places de l'origine."),
    destination_id: str | None = Query(None, max_length=80, description="Identifiant places de la destination."),
    limit: int = Query(DEFAULT_FLOW_PAGE, ge=1, le=MAX_FLOW_PAGE, description="Taille de page, maximum 500."),
    offset: int = Query(0, ge=0, description="Décalage de pagination."),
):
    """Couples de lieux résolus dans places. Source distincte de /api/od/flows et de sim_trips."""
    return _respond(
        lambda: cohort_service.get_flows(
            date_from=date_from,
            date_to=date_to,
            mode=mode,
            purpose=purpose,
            origin_id=origin_id,
            destination_id=destination_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/trips",
    response_model=CohortTrips,
    summary="Étapes simulées filtrées et paginées",
    responses={
        400: {"description": "Filtre ou pagination refusé"},
        404: {"description": "Jeu sim-cohort absent"},
        409: {"description": "Jeu non simulé"},
        422: {"description": "Paramètre de type ou de borne invalide"},
        503: {"description": "Tables du contrat inaccessibles"},
    },
)
def cohort_trips(
    date_from: date | None = Query(None, description="Début inclusif."),
    date_to: date | None = Query(None, description="Fin inclusive."),
    person_id: str | None = Query(None, max_length=40, description="Pseudonyme interne de sim-cohort."),
    mode: str | None = Query(None, max_length=40, description="Code de mode."),
    purpose: str | None = Query(None, max_length=40, description="Code de motif."),
    origin_id: str | None = Query(None, max_length=80, description="Identifiant places de l'origine."),
    destination_id: str | None = Query(None, max_length=80, description="Identifiant places de la destination."),
    limit: int = Query(
        DEFAULT_TRIP_PAGE,
        ge=1,
        le=MAX_TRIP_PAGE,
        description="Taille de page. Défaut 50, maximum 100. Aucun appel ne renvoie tout le jeu.",
    ),
    offset: int = Query(0, ge=0, description="Décalage de pagination."),
):
    """Usage contrôlé : pseudonymes du jeu simulé, sans nom affichable ni texte libre."""
    return _respond(
        lambda: cohort_service.get_trips(
            date_from=date_from,
            date_to=date_to,
            mode=mode,
            purpose=purpose,
            origin_id=origin_id,
            destination_id=destination_id,
            person_id=person_id,
            limit=limit,
            offset=offset,
        )
    )
