# -*- coding: utf-8 -*-
"""La démarche du PDF (chapitre 6) sur les trois cas locaux.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_spec_process.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.spec_process import WEIGHTS, list_cases, run_case  # noqa: E402


def main() -> None:
    cases = list_cases()
    assert [item["id"] for item in cases] == ["entreprise", "collectivite", "multi"]
    weights = [item[2] for item in WEIGHTS]
    assert abs(sum(weights) - 1.0) < 1e-9
    assert weights == [0.30, 0.25, 0.20, 0.15, 0.10]

    company = run_case("entreprise")
    assert company["steps"][0]["title"].startswith("Cartographie")
    assert len(company["steps"]) == 5
    assert company["candidates"]
    assert company["candidates"][0]["impact_score"] > 0
    assert company["candidates"][0]["rank"] == 1
    assert "Antaninarenina" in company["steps"][0]["lines"][0]
    reference = company["scenarios"][0]
    assert reference["id"] == "reference"
    assert reference["trips_captured"] == 0
    assert any(item["minutes_per_person"] > 0 for item in company["scenarios"])
    assert company["geojson"]["type"] == "FeatureCollection"

    city = run_case("collectivite", adoption=0.6)
    by_id = {item["id"]: item for item in city["scenarios"]}
    assert by_id["logements"]["trips_captured"] == 0
    assert by_id["mixte"]["trips_captured"] >= by_id["activites"]["trips_captured"]
    assert by_id["mixte"]["basins"] >= 2

    shared = run_case("multi")
    assert shared["scenarios"][2]["employers"] >= 2
    assert shared["scenarios"][2]["people"] >= 20

    print("spec_process OK")
    for case_id in ("entreprise", "collectivite", "multi"):
        page = run_case(case_id)
        top = page["candidates"][0]
        print(
            case_id,
            top["name"],
            top["impact_score"],
            [(item["id"], item["people"], item["minutes_per_person"], item["co2_t_year"]) for item in page["scenarios"]],
        )


if __name__ == "__main__":
    main()
