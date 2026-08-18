import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.privacy import K_ANONYMITY_MIN, OD_MIN_PASSENGERS_DEFAULT
from app.services.provenance import get_data_provenance

logger = logging.getLogger("mobilite.od")


def _clamp_min_passengers(min_passengers: int) -> int:
    """Plancher k-anonymité : jamais exposer un volume < k."""
    return max(int(min_passengers), K_ANONYMITY_MIN)


def get_zones_geojson(db: Session, limit: int = 200) -> dict:
    sql = text(
        """
        SELECT
            id,
            name,
            zone_type,
            COALESCE(population_proxy, 0) AS population_proxy,
            COALESCE(jobs_proxy, 0) AS jobs_proxy,
            ST_AsGeoJSON(geometry)::json AS geometry
        FROM mobility_zones
        ORDER BY name
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"limit": limit}).fetchall()
    features = [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {
                "id": row.id,
                "name": row.name,
                "zone_type": row.zone_type,
                "population_proxy": row.population_proxy,
                "jobs_proxy": row.jobs_proxy,
            },
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}


def get_od_desire_lines_geojson(
    db: Session,
    min_passengers: int = OD_MIN_PASSENGERS_DEFAULT,
    limit: int = 300,
) -> dict:
    min_passengers = _clamp_min_passengers(min_passengers)
    sql = text(
        """
        SELECT
            id,
            origin_zone_id,
            destination_zone_id,
            origin_name,
            destination_name,
            passenger_count,
            mode,
            average_distance,
            average_time,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM v_od_desire_lines
        WHERE passenger_count >= :min_passengers
        ORDER BY passenger_count DESC
        LIMIT :limit
        """
    )
    rows = db.execute(
        sql,
        {"min_passengers": min_passengers, "limit": limit},
    ).fetchall()

    features = [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {
                "id": row.id,
                "origin_zone_id": row.origin_zone_id,
                "destination_zone_id": row.destination_zone_id,
                "origin_name": row.origin_name,
                "destination_name": row.destination_name,
                "passenger_count": row.passenger_count,
                "mode": row.mode,
                "average_distance_km": (
                    float(row.average_distance)
                    if row.average_distance is not None
                    else None
                ),
                "average_time_min": (
                    float(row.average_time)
                    if row.average_time is not None
                    else None
                ),
            },
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}


def get_od_summary(db: Session, top_n: int = 5) -> dict:
    """
    KPI M5 : totaux + top flux OD.
    Sert le panneau latéral du frontend (aide à la décision).
    """
    # --- Totaux globaux (agrégats uniquement) ---
    sql = text(
        """
        SELECT
            COUNT(*) AS flow_count,
            COALESCE(SUM(trip_count), 0) AS total_passengers,
            COALESCE(MAX(trip_count), 0) AS max_flow,
            COALESCE(AVG(trip_count), 0) AS avg_flow
        FROM mobility_flows
        WHERE trip_count >= :k
        """
    )
    row = db.execute(sql, {"k": K_ANONYMITY_MIN}).fetchone()
    zones = db.execute(text("SELECT COUNT(*) FROM mobility_zones")).scalar()

    # --- Top N desire lines (volumes >= k) ---
    top_sql = text(
        """
        SELECT
            origin_name,
            destination_name,
            passenger_count,
            average_distance,
            average_time
        FROM v_od_desire_lines
        WHERE passenger_count >= :k
        ORDER BY passenger_count DESC
        LIMIT :top_n
        """
    )
    top_rows = db.execute(
        top_sql,
        {"top_n": top_n, "k": K_ANONYMITY_MIN},
    ).fetchall()

    top_flows = [
        {
            "origin_name": r.origin_name,
            "destination_name": r.destination_name,
            "passenger_count": int(r.passenger_count),
            "average_distance_km": (
                float(r.average_distance) if r.average_distance is not None else None
            ),
            "average_time_min": (
                float(r.average_time) if r.average_time is not None else None
            ),
        }
        for r in top_rows
    ]

    provenance = get_data_provenance(db)

    logger.info(
        "od_summary zones=%s flow_count=%s top_n=%s source=%s",
        zones,
        int(row.flow_count),
        len(top_flows),
        provenance["data_source"],
    )

    return {
        "zones": zones,
        "flow_count": int(row.flow_count),
        "total_passengers": int(row.total_passengers),
        "max_flow": int(row.max_flow),
        "avg_flow": round(float(row.avg_flow), 1),
        "top_flows": top_flows,
        "k_anonymity_min": K_ANONYMITY_MIN,
        "source_table": "mobility_flows",
        "synthetic": provenance["synthetic"],
        "data_source": provenance["data_source"],
        "note": provenance["note"],
    }
