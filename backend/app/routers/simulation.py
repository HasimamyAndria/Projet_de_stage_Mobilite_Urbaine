from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from app.database import get_db
from app.services.simulation import simulate, ACTIONS

router = APIRouter(prefix="/api", tags=["Simulation M4"])


class SimulateBody(BaseModel):
    action: str = Field("add_tc_stop")
    zone_id: int | None = None
    intensity: float = Field(0.25, ge=0.05, le=1.0)
    telework_rate: float = Field(0.15, ge=0.0, le=0.8)
    telework_pattern: str = "hybrid_1_2"


def _run(db: Session, body: SimulateBody):
    try:
        return simulate(
            db,
            action=body.action,
            zone_id=body.zone_id,
            intensity=body.intensity,
            telework_rate=body.telework_rate,
            telework_pattern=body.telework_pattern,
        )
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Données OD/zones absentes. Detail: {exc}",
        ) from exc


@router.get("/simulate")
def simulate_get(
    action: str = Query("add_tc_stop"),
    zone_id: int | None = Query(None),
    intensity: float = Query(0.25, ge=0.05, le=1.0),
    telework_rate: float = Query(0.15, ge=0.0, le=0.8),
    telework_pattern: str = Query("hybrid_1_2"),
    db: Session = Depends(get_db),
):
    if action not in ACTIONS:
        raise HTTPException(status_code=400, detail=f"action inconnue. {list(ACTIONS)}")
    return _run(
        db,
        SimulateBody(
            action=action,
            zone_id=zone_id,
            intensity=intensity,
            telework_rate=telework_rate,
            telework_pattern=telework_pattern,
        ),
    )


@router.post("/simulate")
def simulate_post(body: SimulateBody, db: Session = Depends(get_db)):
    if body.action not in ACTIONS:
        raise HTTPException(status_code=400, detail=f"action inconnue. {list(ACTIONS)}")
    return _run(db, body)
