import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.privacy import K_ANONYMITY_MIN, OD_MIN_PASSENGERS_DEFAULT
from app.services import od as od_service

logger = logging.getLogger("mobilite.api.od")

router = APIRouter(
    prefix="/api/od",
    tags=["Origin-Destination"],
)


def _missing_data(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "Tables OD absentes ou non peuplées. "
            "Exécuter: python backend/scripts/seed_zones_od.py. "
            f"Detail: {exc}"
        ),
    )


@router.get("/zones")
def list_zones(db: Session = Depends(get_db)):
    logger.info("access GET /api/od/zones")
    try:
        return od_service.get_zones_geojson(db)
    except ProgrammingError as exc:
        raise _missing_data(exc) from exc


@router.get("/flows")
def list_od_flows(
    min_passengers: int = Query(
        OD_MIN_PASSENGERS_DEFAULT,
        ge=K_ANONYMITY_MIN,
        description=f"Seuil minimal de volume (plancher k-anonymité = {K_ANONYMITY_MIN})",
    ),
    limit: int = Query(300, ge=1, le=1000),
    hour: int | None = Query(None, ge=0, le=23),
    weekday: int | None = Query(None, ge=1, le=7),
    mode: str | None = Query(None, description="all|car|bus|walk|bike"),
    db: Session = Depends(get_db),
):
    logger.info(
        "access GET /api/od/flows min_passengers=%s limit=%s hour=%s weekday=%s mode=%s",
        min_passengers,
        limit,
        hour,
        weekday,
        mode,
    )
    try:
        data = od_service.get_od_desire_lines_geojson(
            db,
            min_passengers=min_passengers,
            limit=limit,
            hour=hour,
            weekday=weekday,
            mode=mode,
        )
        logger.info("od_flows feature_count=%s", len(data.get("features", [])))
        return data
    except ProgrammingError as exc:
        raise _missing_data(exc) from exc


@router.get("/matrix")
def od_matrix(
    min_passengers: int = Query(OD_MIN_PASSENGERS_DEFAULT, ge=K_ANONYMITY_MIN),
    hour: int | None = Query(None, ge=0, le=23),
    weekday: int | None = Query(None, ge=1, le=7),
    mode: str | None = Query(None),
    db: Session = Depends(get_db),
):
    logger.info("access GET /api/od/matrix")
    try:
        return od_service.get_od_matrix(
            db,
            hour=hour,
            weekday=weekday,
            mode=mode,
            min_passengers=min_passengers,
        )
    except ProgrammingError as exc:
        raise _missing_data(exc) from exc


@router.get("/heatmap")
def od_heatmap(
    kind: str = Query("origin", description="origin|destination|activity"),
    hour: int | None = Query(None, ge=0, le=23),
    weekday: int | None = Query(None, ge=1, le=7),
    mode: str | None = Query(None),
    db: Session = Depends(get_db),
):
    logger.info("access GET /api/od/heatmap kind=%s", kind)
    try:
        return od_service.get_od_heatmap(
            db, kind=kind, hour=hour, weekday=weekday, mode=mode
        )
    except ProgrammingError as exc:
        raise _missing_data(exc) from exc


@router.get("/meta")
def od_meta():
    return od_service.get_od_meta()


@router.get("/summary")
def od_summary(
    top_n: int = Query(5, ge=1, le=20, description="Nombre de flux dans le top"),
    db: Session = Depends(get_db),
):
    """
    KPI M5 pour le panneau latéral :
    totaux + top N OD (agrégats, volumes >= k).
    """
    logger.info("access GET /api/od/summary top_n=%s", top_n)
    try:
        return od_service.get_od_summary(db, top_n=top_n)
    except ProgrammingError as exc:
        raise _missing_data(exc) from exc
