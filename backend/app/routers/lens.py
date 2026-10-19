"""Lecture origine / destination par quartier et arrondissement."""
from fastapi import APIRouter, HTTPException, Query

from app.services.lens import build_lens

router = APIRouter(prefix="/api/mobility", tags=["Lecture territoriale"])


@router.get("/lens")
def mobility_lens(
    city: str = Query(..., description="Nom ou identifiant de la ville active"),
    origins: str = Query("", description="Identifiants de quartiers ou d'arrondissements, séparés par des virgules"),
    destinations: str = Query("", description="Identifiants de quartiers ou d'arrondissements, séparés par des virgules"),
    purpose: str = Query("", description="Motif, par exemple travail. Vide : tous les motifs."),
):
    try:
        return build_lens(city, origins, destinations, purpose)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
