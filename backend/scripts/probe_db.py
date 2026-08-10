# -*- coding: utf-8 -*-
"""Probe PostGIS connection and existing OD tables."""
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

url = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(url)

with engine.connect() as c:
    print("ok", c.execute(text("SELECT 1")).scalar())
    for t in ["mobility_zones", "od_flows", "planet_osm_point", "planet_osm_line"]:
        try:
            n = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(t, n)
        except Exception as ex:
            print(t, "ERR", type(ex).__name__, str(ex)[:120])

    bbox = c.execute(
        text(
            """
            SELECT
                ST_XMin(ST_Extent(ST_Transform(way, 4326))) AS xmin,
                ST_YMin(ST_Extent(ST_Transform(way, 4326))) AS ymin,
                ST_XMax(ST_Extent(ST_Transform(way, 4326))) AS xmax,
                ST_YMax(ST_Extent(ST_Transform(way, 4326))) AS ymax
            FROM planet_osm_line
            WHERE highway IS NOT NULL
            """
        )
    ).fetchone()
    print("bbox", tuple(bbox) if bbox else None)

    places = c.execute(
        text(
            """
            SELECT COUNT(*)
            FROM planet_osm_point
            WHERE place IN ('suburb', 'neighbourhood', 'quarter', 'town', 'city')
              AND name IS NOT NULL
            """
        )
    ).scalar()
    print("places", places)

    sample = c.execute(
        text(
            """
            SELECT name, place,
                   ST_X(ST_Transform(way, 4326)) AS lon,
                   ST_Y(ST_Transform(way, 4326)) AS lat
            FROM planet_osm_point
            WHERE place IN ('suburb', 'neighbourhood', 'quarter', 'town', 'city')
              AND name IS NOT NULL
            ORDER BY
              CASE place
                WHEN 'city' THEN 1
                WHEN 'town' THEN 2
                WHEN 'suburb' THEN 3
                WHEN 'neighbourhood' THEN 4
                ELSE 5
              END
            LIMIT 15
            """
        )
    ).fetchall()
    for row in sample:
        print("place", row.name, row.place, round(row.lon, 5), round(row.lat, 5))
