"""Référentiel simulé : zones, flux, indices, profils, organisations."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import mobility_catalog as catalog

router = APIRouter(tags=["Catalogue mobilité simulée"])


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


class SimulationBody(BaseModel):
    organization_id: str = Field(min_length=1, max_length=80)
    scenario: str = Field(min_length=1, max_length=40)


@router.get("/api/zones")
def zones(city: str = Query("Antananarivo")):
    try:
        return catalog.zones_geojson(city)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/arrondissements")
def arrondissements(city: str = Query("Antananarivo")):
    try:
        return catalog.list_arrondissements(city)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/quartiers")
def quartiers(
    city: str = Query("Antananarivo"),
    arrondissement: str = Query(""),
):
    try:
        return catalog.list_quartiers(city, arrondissement)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/flows")
def flows(
    city: str = Query("Antananarivo"),
    origin: str = Query(""),
    destination: str = Query(""),
    purpose: str = Query(""),
    period: str = Query(""),
    company: str = Query(""),
    frequency: str = Query(""),
):
    try:
        return catalog.list_flows(
            city,
            origin=origin,
            destination=destination,
            purpose=purpose,
            period=period,
            company=company,
            frequency=frequency,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/origins")
def origins(
    city: str = Query("Antananarivo"),
    destination: str = Query(""),
):
    try:
        return catalog.list_origins(city, destination)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/destinations")
def destinations(
    city: str = Query("Antananarivo"),
    origin: str = Query(""),
):
    try:
        return catalog.list_destinations(city, origin)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/indicators")
def mobility_indicators(
    city: str = Query("Antananarivo"),
    zone: str = Query(""),
    mode: str = Query("territoire"),
):
    try:
        return catalog.indicators(city, zone, mode)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/clusters")
def mobility_clusters(city: str = Query("Antananarivo")):
    try:
        return catalog.clusters(city)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/mobility/quality")
def mobility_quality(city: str = Query("")):
    try:
        return catalog.quality_report(city or None)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/companies")
def companies(
    city: str = Query("Antananarivo"),
    kind: str = Query(""),
):
    try:
        return catalog.list_companies(city, kind)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.get("/api/companies/{company_id}/mobility")
def company_mobility(company_id: str):
    try:
        return catalog.company_mobility(company_id)
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.post("/api/simulation")
def simulation(body: SimulationBody):
    try:
        result = catalog.simulate_organization(body.organization_id, body.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _remember(result)
    return result


def _remember(result: dict) -> None:
    """Archive le scénario si les tables simulées existent. Le calcul n'en dépend pas."""
    try:
        from sqlalchemy import text

        from app.database import engine
        import json

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sim_scenarios (organization_id, scenario, payload)
                    VALUES (:org, :scenario, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "org": result["company"]["id"],
                    "scenario": result["scenario"]["id"],
                    "payload": json.dumps(result, ensure_ascii=False),
                },
            )
    except Exception:
        return
