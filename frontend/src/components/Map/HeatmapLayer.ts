import maplibregl from "maplibre-gl";
import api from "../../services/api";
import type { OdFilters } from "../../types";

type HeatKind = "activity" | "origin" | "destination";

const LAYER_BY_KIND: Record<HeatKind, { source: string; layer: string }> = {
  activity: { source: "od-heatmap", layer: "od-heatmap-layer" },
  origin: { source: "od-heatmap-origin", layer: "od-heatmap-origin" },
  destination: { source: "od-heatmap-dest", layer: "od-heatmap-dest" },
};

function heatmapPaint(kind: HeatKind): maplibregl.HeatmapLayerSpecification["paint"] {
  const dest = kind === "destination";
  return {
    "heatmap-weight": [
      "interpolate",
      ["linear"],
      ["get", "weight"],
      0, 0,
      500, 0.35,
      5000, 0.7,
      20000, 1,
    ],
    "heatmap-intensity": 1.15,
    "heatmap-radius": [
      "interpolate",
      ["linear"],
      ["zoom"],
      10, 28,
      13, 48,
    ],
    "heatmap-opacity": 0.55,
    "heatmap-color": dest
      ? [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0, "rgba(0,0,0,0)",
          0.15, "rgba(76,29,149,0.3)",
          0.4, "rgba(124,58,237,0.5)",
          0.7, "rgba(244,114,182,0.7)",
          1, "rgba(225,29,72,0.85)",
        ]
      : [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0, "rgba(0,0,0,0)",
          0.15, "rgba(30,64,175,0.35)",
          0.35, "rgba(34,197,94,0.45)",
          0.55, "rgba(234,179,8,0.55)",
          0.75, "rgba(249,115,22,0.7)",
          1, "rgba(220,38,38,0.85)",
        ],
  };
}

export async function loadHeatmap(
  map: maplibregl.Map,
  kind: HeatKind = "activity",
  filters?: OdFilters
) {
  const ids = LAYER_BY_KIND[kind];
  const params: Record<string, string | number> = { kind };
  if (filters?.weekday != null) params.weekday = filters.weekday;
  if (filters?.mode && filters.mode !== "all") params.mode = filters.mode;
  if (filters?.hour != null) params.hour = filters.hour;

  const response = await api.get("/api/od/heatmap", { params });
  const fc = {
    type: "FeatureCollection" as const,
    features: response.data.features ?? [],
  };

  const source = map.getSource(ids.source) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(fc as never);
    return;
  }

  map.addSource(ids.source, { type: "geojson", data: fc as never });
  map.addLayer({
    id: ids.layer,
    type: "heatmap",
    source: ids.source,
    paint: heatmapPaint(kind),
  });
}
