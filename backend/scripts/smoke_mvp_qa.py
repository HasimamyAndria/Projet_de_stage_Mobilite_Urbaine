# -*- coding: utf-8 -*-
"""
Smoke QA MVP — tous les endpoints Must (M1/M2/M5/M6 + socle carte).

Usage (backend déjà démarré sur :8000) :
    python scripts/smoke_mvp_qa.py

Sortie : résumé OK/FAIL + codes HTTP. Exit 1 si un cas bloquant échoue.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"

# Bbox Antananarivo (centre dense démo)
BBOX_DENSE = {
    "minLon": 47.48,
    "minLat": -18.92,
    "maxLon": 47.54,
    "maxLat": -18.86,
}
# Périphérie urbaine
BBOX_PERIPH = {
    "minLon": 47.45,
    "minLat": -18.95,
    "maxLon": 47.48,
    "maxLat": -18.92,
}
# Hors zone urbaine (océan / loin)
BBOX_OUT = {
    "minLon": 40.0,
    "minLat": -20.0,
    "maxLon": 40.1,
    "maxLat": -19.9,
}


def _qs(params: dict) -> str:
    return "&".join(f"{k}={v}" for k, v in params.items())


def fetch(path: str, timeout: float = 30) -> tuple[int, dict | list | str]:
    url = f"{BASE}{path}"
    print(f"\n>>> GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = body
            return resp.status, data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = body
        print(f"    HTTP {exc.code}")
        return exc.code, data
    except Exception as exc:  # noqa: BLE001 — smoke : tout logger
        print(f"    ERREUR reseau/timeout : {exc}")
        return 0, str(exc)


def is_fc(data) -> bool:
    return isinstance(data, dict) and data.get("type") == "FeatureCollection"


def n_features(data) -> int:
    if not isinstance(data, dict):
        return 0
    return len(data.get("features") or [])


results: list[dict] = []


def check(name: str, ok: bool, detail: str, severity: str = "bloquant"):
    status = "OK" if ok else "FAIL"
    # ASCII only : console Windows cp1252
    line = f"    [{status}] {name} - {detail}"
    print(line.encode("ascii", errors="replace").decode("ascii"))
    results.append(
        {
            "name": name,
            "ok": ok,
            "detail": detail,
            "severity": severity if not ok else "pass",
        }
    )


def main() -> int:
    print("=" * 60)
    print("SMOKE QA MVP - Mobilite Urbaine")
    print("Date UTC :", datetime.now(timezone.utc).isoformat())
    print("=" * 60)

    # --- Health ---
    code, data = fetch("/health")
    check("health", code == 200 and data.get("status") == "ok", f"code={code} body={data}")

    # --- Carte bbox dense ---
    for layer in ("roads", "buildings", "bus-stops", "bus-lines"):
        code, data = fetch(f"/api/{layer}?{_qs(BBOX_DENSE)}")
        ok = code == 200 and is_fc(data)
        # roads/buildings peuvent etre vides selon import OSM ; structure OK suffit
        check(
            f"{layer} bbox dense",
            ok,
            f"code={code} features={n_features(data) if ok else 'n/a'}",
        )

    # --- Bbox peripherie / hors zone (structure + LIMIT) ---
    code, data = fetch(f"/api/roads?{_qs(BBOX_PERIPH)}")
    check(
        "roads bbox peripherie",
        code == 200 and is_fc(data),
        f"code={code} features={n_features(data)}",
        severity="majeur",
    )
    code, data = fetch(f"/api/roads?{_qs(BBOX_OUT)}")
    check(
        "roads bbox hors zone",
        code == 200 and is_fc(data) and n_features(data) == 0,
        f"code={code} features={n_features(data)}",
        severity="majeur",
    )

    # --- Search ---
    code, data = fetch("/api/search?q=Antananarivo")
    # API peut renvoyer liste ou FC selon implémentation
    search_ok = code == 200 and (
        (isinstance(data, list) and len(data) >= 0)
        or is_fc(data)
        or isinstance(data, dict)
    )
    check("search q=Antananarivo", search_ok, f"code={code} type={type(data).__name__}")

    code, data = fetch("/api/search?q=")
    # vide : 400 ou [] documenté — les deux acceptés
    empty_ok = code in (200, 400, 422)
    check(
        "search q vide",
        empty_ok,
        f"code={code}",
        severity="mineur",
    )

    # --- Route A->B (points demo connectes, sous-graphe Tana) ---
    # Timeout plus large : pgRouting peut etre lent sur premier appel
    route_params = {
        "startLon": 47.52928,
        "startLat": -18.903276,
        "endLon": 47.5160582,
        "endLat": -18.8680788,
    }
    code, data = fetch(f"/api/route?{_qs(route_params)}", timeout=90)
    route_has_geom = False
    if code == 200:
        if is_fc(data) and n_features(data) > 0:
            route_has_geom = True
        elif isinstance(data, dict) and data.get("geometry"):
            route_has_geom = True
        elif (
            isinstance(data, dict)
            and data.get("type") == "Feature"
            and data.get("geometry")
        ):
            route_has_geom = True
    check(
        "route A->B",
        code == 200 and route_has_geom,
        f"code={code} geom={route_has_geom} features={n_features(data) if isinstance(data, dict) else 0}",
    )

    # --- Zones bounds ---
    code, data = fetch("/api/zones/bounds")
    check(
        "zones/bounds",
        code == 200 and isinstance(data, dict) and "xmin" in data,
        f"code={code}",
        severity="majeur",
    )

    # --- OD / analytics Must ---
    code, data = fetch("/api/od/zones")
    check(
        "od/zones",
        code == 200 and is_fc(data) and n_features(data) > 0,
        f"code={code} features={n_features(data)}",
    )

    code, data = fetch("/api/od/flows?min_passengers=20&limit=300")
    check(
        "od/flows",
        code == 200 and is_fc(data) and n_features(data) > 0,
        f"code={code} features={n_features(data)}",
    )
    # Anonymisation : pas de champs individuels
    if code == 200 and is_fc(data) and data["features"]:
        props = data["features"][0].get("properties") or {}
        forbidden = {"user_id", "person_id", "trip_id", "email", "phone", "name"}
        leaked = forbidden.intersection(props.keys())
        # "name" de zone OD autorisé via origin_name — on vérifie les clés strictes
        leaked = {"user_id", "person_id", "trip_id", "email", "phone"}.intersection(
            props.keys()
        )
        check(
            "od/flows anonymisation",
            len(leaked) == 0,
            f"props keys sample={sorted(props.keys())}",
        )
        check(
            "od/flows LIMIT<=300",
            n_features(data) <= 300,
            f"n={n_features(data)}",
            severity="majeur",
        )

    code, data = fetch("/api/od/summary?top_n=5")
    check(
        "od/summary (M5)",
        code == 200
        and isinstance(data, dict)
        and data.get("zones", 0) > 0
        and len(data.get("top_flows") or []) > 0,
        f"code={code} zones={data.get('zones') if isinstance(data, dict) else None}",
    )

    code, data = fetch("/api/keypoints?corridor_top_n=5")
    kp_ok = (
        code == 200
        and isinstance(data, dict)
        and is_fc(data.get("zones"))
        and is_fc(data.get("corridors"))
        and isinstance(data.get("counts"), dict)
    )
    check(
        "keypoints (M2)",
        kp_ok,
        f"code={code} counts={data.get('counts') if isinstance(data, dict) else None}",
    )

    code, data = fetch("/api/emploi-habitat")
    eh_ok = (
        code == 200
        and is_fc(data)
        and n_features(data) > 0
        and isinstance(data.get("summary"), dict)
        and data["summary"].get("avg_score") is not None
    )
    check(
        "emploi-habitat (M6)",
        eh_ok,
        f"code={code} avg={data.get('summary', {}).get('avg_score') if isinstance(data, dict) else None}",
    )
    if eh_ok:
        scores = [
            f["properties"].get("eh_index")
            for f in data["features"]
            if f.get("properties", {}).get("eh_index") is not None
        ]
        in_range = all(0 <= s <= 1 for s in scores)
        check(
            "emploi-habitat scores [0,1]",
            in_range and len(scores) > 0,
            f"n_scored={len(scores)} min={min(scores)} max={max(scores)}",
        )

    # --- Synthèse ---
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]
    blocking = [r for r in failed if r["severity"] == "bloquant"]
    print(f"Resultat : {passed}/{len(results)} OK")
    if failed:
        print("Echecs :")
        for r in failed:
            print(f"  - [{r['severity']}] {r['name']}: {r['detail']}")
    else:
        print("Aucun echec.")
    print("=" * 60)

    # Dump JSON pour le rapport QA
    out_path = "scripts/_smoke_mvp_qa_last.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "date_utc": datetime.now(timezone.utc).isoformat(),
                    "passed": passed,
                    "total": len(results),
                    "results": results,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"Preuve JSON : {out_path}")
    except OSError as exc:
        print(f"(pas de dump JSON : {exc})")

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
