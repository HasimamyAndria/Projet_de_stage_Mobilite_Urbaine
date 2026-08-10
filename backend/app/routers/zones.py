from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/zones",
    tags=["Mobility Zones"]
)

@router.get("/bounds")
def get_city_bounds(db: Session = Depends(get_db)):

    sql = text("""
        SELECT
            ST_XMin(ST_Extent(way)) AS xmin,
            ST_YMin(ST_Extent(way)) AS ymin,
            ST_XMax(ST_Extent(way)) AS xmax,
            ST_YMax(ST_Extent(way)) AS ymax
        FROM planet_osm_roads;
    """)

    result = db.execute(sql).fetchone()

    return {
        "xmin": result.xmin,
        "ymin": result.ymin,
        "xmax": result.xmax,
        "ymax": result.ymax
    }