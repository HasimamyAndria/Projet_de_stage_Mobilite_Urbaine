# -*- coding: utf-8 -*-
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
    b = c.execute(
        text(
            """
            SELECT
                ST_XMin(ST_Extent(geometry)),
                ST_YMin(ST_Extent(geometry)),
                ST_XMax(ST_Extent(geometry)),
                ST_YMax(ST_Extent(geometry))
            FROM mobility_zones
            """
        )
    ).fetchone()
    print("bbox_zones", [round(float(x), 4) for x in b])
    print(
        "zones",
        c.execute(text("SELECT COUNT(*) FROM mobility_zones")).scalar(),
    )
    print(
        "flows",
        c.execute(text("SELECT COUNT(*) FROM mobility_flows")).scalar(),
    )
    print(
        "max_flow",
        c.execute(text("SELECT COALESCE(MAX(trip_count),0) FROM mobility_flows")).scalar(),
    )
