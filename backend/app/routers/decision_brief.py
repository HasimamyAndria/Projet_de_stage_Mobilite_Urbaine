from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services.decision_brief import build_decision_brief

router = APIRouter(prefix="/api", tags=["Dossier décideur"])


class DecisionBriefBody(BaseModel):
    anchor_zone_id: int | None = None
    organization: str = "Direction des finances"
    sector: str = "admin"
    headcount: int = Field(800, ge=1, le=100_000)
    share_must_be_present: float = Field(0.35, ge=0.0, le=1.0)
    telework_rate_max: float = Field(0.40, ge=0.0, le=0.8)
    telework_pattern: str = "hybrid_1_2"
    max_annexes: int = Field(3, ge=3, le=5)
    peak_hours: list[int] = Field(default_factory=lambda: [7, 8, 9])


@router.post("/decision-brief")
def decision_brief(body: DecisionBriefBody, db: Session = Depends(get_db)):
    try:
        return build_decision_brief(db, body.model_dump())
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Données OD/zones absentes. "
                "Exécuter: python backend/scripts/seed_zones_od.py. "
                f"Detail: {exc}"
            ),
        ) from exc
