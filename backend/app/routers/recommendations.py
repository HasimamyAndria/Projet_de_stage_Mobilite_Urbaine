from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services import recommendations as reco_service

router = APIRouter(prefix="/api", tags=["Recommendations M3"])


@router.get("/recommendations")
def list_recommendations(
    corridor_top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    try:
        return reco_service.get_recommendations(db, corridor_top_n=corridor_top_n)
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Données OD/zones absentes. Detail: {exc}",
        ) from exc
