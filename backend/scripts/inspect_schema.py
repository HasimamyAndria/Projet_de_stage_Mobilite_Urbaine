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
    for table in ["mobility_zones", "mobility_flows", "od_flows"]:
        print("====", table)
        rows = c.execute(text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=:t
            ORDER BY ordinal_position
        """), {"t": table}).fetchall()
        if not rows:
            print("(missing)")
            continue
        for r in rows:
            print(r.column_name, r.data_type, r.udt_name)
        n = c.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
        print("count", n)
        # geometry metadata
        meta = c.execute(text("""
            SELECT f_geometry_column, type, srid
            FROM geometry_columns
            WHERE f_table_name = :t
        """), {"t": table}).fetchall()
        for m in meta:
            print("geom_meta", m)
