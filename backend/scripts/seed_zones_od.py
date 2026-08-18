# -*- coding: utf-8 -*-
"""
Point d'entrée seed analytics.

Par défaut : peuplement **OSM réel** (quartiers + proxies bâti/POI).
Option démo grille : ``python scripts/seed_zones_od.py --demo``.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
SQL_DEMO = SCRIPTS / "sql" / "19_seed_zones_od_demo.sql"

load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")


def _db_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    if host == "db" and not Path("/.dockerenv").exists():
        host = "localhost"
    return (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{host}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


def seed_demo_grid() -> None:
    """Ancienne grille 4×4 synthétique (repli / tests)."""
    raw = SQL_DEMO.read_text(encoding="utf-8")
    statements = [s.strip() for s in raw.split(";") if s.strip()]
    engine = create_engine(_db_url())

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

    print(f"OK seed démo grille -> zones={zones}, flows={flows}, trips={total}")
    print(f"SQL: {SQL_DEMO}")


def seed_osm(top_n: int) -> None:
    script = SCRIPTS / "seed_zones_od_osm.py"
    cmd = [sys.executable, str(script), "--top-n", str(top_n)]
    subprocess.check_call(cmd, cwd=str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed zones / flux OD")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Utiliser la grille synthétique 4×4 (au lieu d'OSM)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=36,
        help="Nombre de quartiers OSM (seed réel, défaut 36)",
    )
    args = parser.parse_args()

    if args.demo:
        seed_demo_grid()
    else:
        seed_osm(top_n=args.top_n)


if __name__ == "__main__":
    main()
