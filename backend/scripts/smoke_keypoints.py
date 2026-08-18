# -*- coding: utf-8 -*-
import json
import urllib.request

url = "http://127.0.0.1:8000/api/keypoints?corridor_top_n=5"
print("GET", url)
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.load(resp)

print("counts", data.get("counts"))
print("clustering", data.get("clustering"))
print("rules", data.get("rules"))
print("zones", len(data.get("zones", {}).get("features", [])))
print("corridors", len(data.get("corridors", {}).get("features", [])))
for f in data.get("zones", {}).get("features", [])[:5]:
    p = f["properties"]
    print(
        f"  {p['name']}: {p['label_fr']} "
        f"(ratio={p['pop_jobs_ratio']}, cluster={p.get('cluster_label')})"
    )
print("OK keypoints")
