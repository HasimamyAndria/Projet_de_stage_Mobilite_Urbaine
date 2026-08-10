from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services import emploi_habitat as eh_service

router = APIRouter(
    prefix="/api",
    tags=["Emploi-Habitat M6"],
)


@router.get("/emploi-habitat")
def list_emploi_habitat(db: Session = Depends(get_db)):
    """
    M6 — Indice emploi-habitat :
    GeoJSON des zones + score (eh_index) + résumé (moyenne / extrêmes).
    """
    print("[API] GET /api/emploi-habitat")
    try:
        data = eh_service.get_emploi_habitat(db)
        n = len(data.get("features", []))
        print(f"[API] emploi-habitat features = {n}")
        return data
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Données OD/zones absentes. "
                "Exécuter: python backend/scripts/seed_zones_od.py. "
                f"Detail: {exc}"
            ),
        ) from exc
