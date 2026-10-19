from fastapi import APIRouter, HTTPException, Query

from app.services.spec_process import list_cases, run_case

router = APIRouter(prefix="/api/spec", tags=["Demarche spec"])


@router.get("/cases")
def spec_cases():
    return {"cases": list_cases()}


@router.get("/cases/{case_id}")
def spec_case(
    case_id: str,
    adoption: float = Query(0.6, ge=0.2, le=1.0),
    telework: float = Query(0.0, ge=0.0, le=0.8),
    horizon: int = Query(1),
):
    try:
        return run_case(
            case_id,
            adoption=adoption,
            telework=telework,
            horizon_years=horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
