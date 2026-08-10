# -*- coding: utf-8 -*-
import json
import urllib.request

url = "http://127.0.0.1:8000/api/od/summary?top_n=5"
print("GET", url)
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.load(resp)

print("zones", data.get("zones"))
print("flow_count", data.get("flow_count"))
print("total_passengers", data.get("total_passengers"))
print("top_flows", len(data.get("top_flows", [])))
for i, f in enumerate(data.get("top_flows", []), 1):
    print(
        f"  {i}. {f['origin_name']} -> {f['destination_name']} "
        f"= {f['passenger_count']}"
    )
print("OK KPI summary")
