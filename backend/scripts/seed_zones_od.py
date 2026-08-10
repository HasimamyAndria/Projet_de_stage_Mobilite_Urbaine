# -*- coding: utf-8 -*-
"""Run demo seed SQL for mobility_zones + mobility_flows."""
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = Path(__file__).resolve().parent / "sql" / "19_seed_zones_od_demo.sql"

load_dotenv(ROOT / ".env")

url = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

raw = SQL_PATH.read_text(encoding="utf-8")
statements = [s.strip() for s in raw.split(";") if s.strip()]

engine = create_engine(url)

with engine.begin() as conn:
    for stmt in statements:
        body = "\n".join(
            line
            for line in stmt.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ).strip()
        if not body:
            continue
        conn.execute(text(body))

    zones = conn.execute(
        text("SELECT COUNT(*) FROM mobility_zones WHERE zone_type = 'grid_demo'")
    ).scalar()
    flows = conn.execute(text("SELECT COUNT(*) FROM mobility_flows")).scalar()
    total = conn.execute(
        text("SELECT COALESCE(SUM(trip_count), 0) FROM mobility_flows")
    ).scalar()

print(f"OK seed -> zones={zones}, flows={flows}, trips={total}")
print(f"SQL: {SQL_PATH}")
