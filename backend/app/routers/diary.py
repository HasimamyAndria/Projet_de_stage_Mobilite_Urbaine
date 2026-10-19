"""Déplacements individuels simulés (enquête pas encore réalisée)."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import diary, employer_decision

router = APIRouter(prefix="/api/mobility", tags=["Deplacements individuels"])


class TripBody(BaseModel):
    person_id: str = Field(min_length=1, max_length=40)
    weekday: int = Field(ge=0, le=6)
    origin_id: str
    destination_id: str
    purpose: str
    detail: str = ""
    mode: str
    depart_hour: float = Field(ge=0, lt=24)


def _bad(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/meta")
def meta():
    """Villes, quartiers, personnes simulées, motifs et modes."""
    return diary.catalog()


@router.get("/diary")
def person_diary(
    person_id: str = Query(...),
    period: str = Query("week"),
    weekday: int = Query(0, ge=0, le=6),
):
    """Trajets, graphs et totaux d'une personne (jour, semaine, mois, année)."""
    try:
        return diary.person_diary(person_id, period, weekday)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/employers")
def employers(city_id: str = Query(...)):
    """Groupes domicile–travail des grands employeurs, et possibilités à comparer."""
    try:
        return employer_decision.board(city_id)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/employers/{organization_id}/movements")
def employer_movements(
    organization_id: str,
    period: str = Query("week"),
    weekday: int = Query(0, ge=0, le=6),
    person_id: str | None = Query(None),
):
    """Ensemble des trajets d'une organisation, ou la semaine d'un de ses employés."""
    try:
        return employer_decision.movements(
            organization_id,
            period,
            weekday,
            person_id or None,
        )
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/employers/{organization_id}")
def employer(organization_id: str):
    """Une organisation : clusters, fonctions, options et rythme type."""
    try:
        return employer_decision.detail(organization_id)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.get("/overview")
def city_overview(
    city_id: str = Query(...),
    period: str = Query("week"),
    weekday: int = Query(0, ge=0, le=6),
):
    """Couples d'indicateurs et pistes pour les décideurs, à l'échelle de la ville."""
    try:
        return diary.city_overview(city_id, period, weekday)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.post("/trips")
def add_trip(body: TripBody):
    """Saisie d'un trajet A → B. Hors travail, le motif écrit est obligatoire."""
    try:
        trip = diary.add_manual_trip(
            person_id=body.person_id,
            weekday=body.weekday,
            origin_id=body.origin_id,
            destination_id=body.destination_id,
            purpose=body.purpose,
            detail=body.detail,
            mode=body.mode,
            depart_hour=body.depart_hour,
        )
    except ValueError as exc:
        raise _bad(exc) from exc
    return {"trip": trip}


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: str):
    try:
        diary.delete_manual_trip(trip_id)
    except ValueError as exc:
        raise _bad(exc) from exc
    return {"deleted": trip_id}
