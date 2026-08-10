from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services import keypoints as keypoints_service

router = APIRouter(
    prefix="/api",
    tags=["Key Points M2"],
)


@router.get("/keypoints")
def list_keypoints(
    corridor_top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    M2 — Points clés :
    zones dortoir / pôle emploi / mixte + corridors OD.
    """
    print(f"[API] GET /api/keypoints (corridor_top_n={corridor_top_n})")
    try:
        data = keypoints_service.get_keypoints(db, corridor_top_n=corridor_top_n)
        print("[API] keypoints OK")
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
