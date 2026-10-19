# -*- coding: utf-8 -*-
"""Contrôle les groupes employeur et les possibilités d'annexe, sans base.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\test_employer_decision.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.employer_decision import board, detail, movements  # noqa: E402


def main() -> None:
    page = board("tana")
    assert page["focus_id"] == "drf-ankorondrano", page["focus_id"]
    org = detail("drf-ankorondrano")
    cluster = next(item for item in org["clusters"] if item["home_id"] == "tana.talatamaty-centre")
    assert cluster["headcount"] == 30
    assert cluster["work_name"] == "Ankorondrano"
    assert cluster["function"] == "cadre de direction"
    assert cluster["considerable"] is True
    assert cluster["far"] is True
    assert cluster["km"] >= 8
    assert len(cluster["rhythm"]["steps"]) == 4

    kinds = [item["kind"] for item in org["options"]]
    assert kinds.count("louer") >= 1
    assert "construire" in kinds
    assert "navette" in kinds
    assert "teletravail" in kinds
    assert len(org["options"]) >= 4
    lease = next(item for item in org["options"] if item["kind"] == "louer")
    assert lease["site_name"] == "Talatamaty centre"
    assert lease["people"] >= 30
    assert lease["km_saved_per_working_day"] > 0
    assert any(row["home"] == "Talatamaty centre" and row["before_km"] >= 8 for row in lease["who"])

    names = {item["id"] for item in org["samples"]}
    assert names == {"aina", "hanta"}

    airport = detail("aeroport-ivato")
    assert all(item["kind"] != "louer" for item in airport["options"])

    holding = detail("holding-ivandry")
    assert holding["kind"] == "entreprise"
    assert holding["considerable_far_count"] >= 20
    assert any(item["kind"] == "louer" for item in holding["options"])

    os.environ["DIARY_READ"] = "memory"
    staff = movements("drf-ankorondrano", "week", 0, None)
    assert len(staff["employees"]) == org["employee_count"] == 116
    assert staff["scope"] == "all"
    aina = next(item for item in staff["employees"] if item["id"] == "aina")
    assert aina["named"] is True
    assert aina["work"] == "Ankorondrano"
    monday = next(point for point in staff["volume"]["points"] if point["label"] == "Lun")
    assert monday["value"] == 116 * 2, monday
    saturday = next(point for point in staff["volume"]["points"] if point["label"] == "Sam")
    sunday = next(point for point in staff["volume"]["points"] if point["label"] == "Dim")
    assert saturday["value"] > 0, saturday
    assert sunday["value"] > 0, sunday
    purpose_ids = {item["id"] for item in staff["purposes"]["items"]}
    assert "supermarche" in purpose_ids
    assert "culte" in purpose_ids
    assert staff["suggestions"]
    assert all(item["suggested_km"] < item["current_km"] for item in staff["suggestions"])
    assert any(item["purpose"] == "supermarche" for item in staff["suggestions"])
    weights = {
        (feature["properties"]["label"], feature["properties"]["purpose"]): feature["properties"]["weight"]
        for feature in staff["geojson"]["features"]
    }
    assert weights[("Talatamaty centre → Ankorondrano", "Travail")] == 30
    assert weights[("Talatamaty centre → Ankorondrano", "Supermarché")] == 29

    generated = next(item for item in staff["employees"] if not item["named"] and item["home"] == "Talatamaty centre")
    alone = movements("drf-ankorondrano", "week", 0, generated["id"])
    assert alone["scope"] == "person"
    assert alone["stats"]["trip_count"] == 14, alone["stats"]
    alone_purposes = {trip["purpose"] for trip in alone["trips"]}
    assert {"travail", "supermarche", "culte"} <= alone_purposes
    assert alone["trips"][0]["destination_name"] == "Ankorondrano"
    assert any(item["purpose"] == "supermarche" and item["suggested_km"] < item["current_km"] for item in alone["suggestions"])

    print("ok", org["id"], "km", cluster["km"], "employes", len(staff["employees"]))
    for item in org["options"]:
        print("-", item["kind"], item["people"], item["site_name"], item["km_saved_per_working_day"])


if __name__ == "__main__":
    main()
