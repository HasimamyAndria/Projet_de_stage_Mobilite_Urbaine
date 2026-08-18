# -*- coding: utf-8 -*-
"""API multi-villes : recherche Nominatim + activation + couverture OSM."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import city_service as svc

router = APIRouter(prefix="/api/cities", tags=["Cities"])


class ActivateCityBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    display_name: str | None = None
    country: str | None = None
    lon: float
    lat: float
    west: float
    south: float
    east: float
    north: float
    top_n: int = Field(36, ge=3, le=80)


@router.get("/presets")
def list_presets():
    return {"presets": svc.CITY_PRESETS}


@router.get("/search")
def search_cities(q: str = Query(..., min_length=2), limit: int = Query(6, ge=1, le=10)):
    try:
        results = svc.nominatim_search_cities(q, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Nominatim indisponible : {exc}",
        ) from exc
    return {"query": q, "results": results}


@router.get("/coverage")
def coverage(
    west: float,
    south: float,
    east: float,
    north: float,
    db: Session = Depends(get_db),
):
    return svc.check_osm_coverage(db, west, south, east, north)


@router.get("/current")
def current_city(db: Session = Depends(get_db)):
    return svc.get_active_city(db)


@router.post("/activate")
def activate_city(body: ActivateCityBody, db: Session = Depends(get_db)):
    try:
        return svc.activate_city(
            db,
            name=body.name,
            display_name=body.display_name,
            country=body.country,
            lon=body.lon,
            lat=body.lat,
            west=body.west,
            south=body.south,
            east=body.east,
            north=body.north,
            top_n=body.top_n,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
