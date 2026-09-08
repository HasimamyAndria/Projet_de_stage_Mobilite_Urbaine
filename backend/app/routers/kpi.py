from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services import kpi as kpi_service

router = APIRouter(prefix="/api", tags=["Dashboard M5"])


@router.get("/kpi/dashboard")
def dashboard(db: Session = Depends(get_db)):
    try:
        return kpi_service.get_dashboard(db)
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Données OD/zones absentes. Detail: {exc}",
        ) from exc
