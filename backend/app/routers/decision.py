from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import decision_ai

router = APIRouter(prefix="/api", tags=["Decision IA"])


class CompareRequest(BaseModel):
    home_name: str = Field(..., min_length=1, max_length=80)
    work_name: str = Field(..., min_length=1, max_length=80)
    employees: int = Field(80, ge=1, le=5000)
    work_label: str = Field("Domaine Finance", max_length=120)
    include_deepseek: bool = True


@router.get("/decision/places")
def decision_places():
    return {"places": decision_ai.list_places()}


@router.post("/decision/compare")
def decision_compare(body: CompareRequest):
    try:
        return decision_ai.compare_decision(
            home_name=body.home_name,
            work_name=body.work_name,
            employees=body.employees,
            work_label=body.work_label,
            include_deepseek=body.include_deepseek,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
