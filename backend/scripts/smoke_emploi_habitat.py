# -*- coding: utf-8 -*-
"""Smoke test M6 — GET /api/emploi-habitat"""
import json
import urllib.request

url = "http://127.0.0.1:8000/api/emploi-habitat"
print("GET", url)
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.load(resp)

features = data.get("features", [])
summary = data.get("summary", {})
print("features", len(features))
print("summary", summary)
print("formula", data.get("formula"))
print("note", data.get("note"))

for f in features[:5]:
    p = f["properties"]
    print(
        f"  {p['name']}: eh_index={p['eh_index']} "
        f"({p['imbalance_fr']}) pop={p['population_proxy']} jobs={p['jobs_proxy']}"
    )

assert data.get("type") == "FeatureCollection"
assert "summary" in data
assert summary.get("avg_score") is not None
print("OK emploi-habitat")
