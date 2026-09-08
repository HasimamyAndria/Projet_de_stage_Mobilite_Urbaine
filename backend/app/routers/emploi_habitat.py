from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services import contributions as contrib_service
from app.services import emploi_habitat as eh_service

router = APIRouter(
    prefix="/api",
    tags=["Emploi-Habitat M6"],
)


class ContributionBody(BaseModel):
    kind: str = Field("suggestion")
    message: str
    zone_id: int | None = None
    zone_name: str | None = None


def _missing(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "Données OD/zones absentes. "
            "Exécuter: python backend/scripts/seed_zones_od.py. "
            f"Detail: {exc}"
        ),
    )


@router.get("/emploi-habitat")
def list_emploi_habitat(db: Session = Depends(get_db)):
    """
    M6 — Indice emploi-habitat :
    GeoJSON des zones + score (eh_index) + résumé (moyenne / extrêmes).
    """
    try:
        return eh_service.get_emploi_habitat(db)
    except ProgrammingError as exc:
        raise _missing(exc) from exc


@router.get("/emploi-habitat/diagnostic")
def diagnostic(db: Session = Depends(get_db)):
    try:
        return eh_service.get_diagnostic(db)
    except ProgrammingError as exc:
        raise _missing(exc) from exc


@router.get("/emploi-habitat/satellites")
def satellites(
    zone_id: int | None = Query(None),
    k: int = Query(5, ge=3, le=5),
    db: Session = Depends(get_db),
):
    try:
        data = eh_service.get_satellite_sites(db, zone_id=zone_id, k=k)
        data["geojson"] = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": c["geometry"],
                    "properties": {
                        key: val for key, val in c.items() if key != "geometry"
                    },
                }
                for c in data.get("candidates") or []
                if c.get("geometry")
            ],
        }
        bary = data.get("barycenter")
        if bary:
            data["geojson"]["features"].append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [bary["lon"], bary["lat"]],
                    },
                    "properties": {
                        "rank": 0,
                        "name": "Barycentre résidentiel distant",
                        "type": "barycenter",
                        "type_label": "Barycentre pondéré",
                    },
                }
            )
        return data
    except ProgrammingError as exc:
        raise _missing(exc) from exc


@router.get("/emploi-habitat/telework")
def telework(
    rate: float = Query(0.20, ge=0.0, le=0.8),
    pattern: str = Query("hybrid_1_2"),
    combine_satellite: bool = Query(False),
    satellite_zone_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        return eh_service.get_telework_impact(
            db,
            rate=rate,
            pattern=pattern,
            combine_satellite=combine_satellite,
            satellite_zone_id=satellite_zone_id,
        )
    except ProgrammingError as exc:
        raise _missing(exc) from exc


@router.get("/contributions")
def list_contributions():
    return contrib_service.list_contributions()


@router.post("/contributions")
def create_contribution(body: ContributionBody):
    try:
        item = contrib_service.add_contribution(
            kind=body.kind,
            message=body.message,
            zone_id=body.zone_id,
            zone_name=body.zone_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return item
