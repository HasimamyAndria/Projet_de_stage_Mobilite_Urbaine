"""Analyse des profils, concentrations et scénarios sur le catalogue simulé."""
from fastapi import APIRouter, HTTPException, Query

from app.services import mobility_intelligence as intelligence

router = APIRouter(tags=["Analyse mobilité"])


@router.get("/api/mobility/analysis")
def mobility_analysis(city: str = Query("Antananarivo")):
    try:
        return intelligence.analyze(city)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
