import maplibregl from "maplibre-gl";
import api from "../../services/api";

const SOURCE_ID = "route-source";
export const ROUTE_LAYER_ID = "route-layer";

export const DEMO_ROUTE = {
  startLon: 47.52928,
  startLat: -18.903276,
  endLon: 47.5160582,
  endLat: -18.8680788,
} as const;

export type RouteResult = {
  count: number;
  adjusted: boolean;
  detail: string;
  snappedStart: { lon: number; lat: number } | null;
  snappedEnd: { lon: number; lat: number } | null;
};

export async function loadRoute(
  map: maplibregl.Map,
  startLon: number,
  startLat: number,
  endLon: number,
  endLat: number,
  visible = true
): Promise<RouteResult> {
  const response = await api.get("/api/route", {
    params: { startLon, startLat, endLon, endLat },
    timeout: 60000,
  });

  const data = response.data;
  const count = Array.isArray(data?.features) ? data.features.length : 0;

  if (map.getLayer(ROUTE_LAYER_ID)) {
    map.removeLayer(ROUTE_LAYER_ID);
  }
  if (map.getSource(SOURCE_ID)) {
    map.removeSource(SOURCE_ID);
  }

  map.addSource(SOURCE_ID, {
    type: "geojson",
    data,
  });

  map.addLayer({
    id: ROUTE_LAYER_ID,
    type: "line",
    source: SOURCE_ID,
    layout: {
      "line-cap": "round",
      "line-join": "round",
      visibility: visible ? "visible" : "none",
    },
    paint: {
      "line-color": "#38bdf8",
      "line-width": 5,
      "line-opacity": 0.92,
    },
  });

  return {
    count,
    adjusted: Boolean(data?.adjusted),
    detail: String(data?.detail || ""),
    snappedStart: data?.snapped_start ?? null,
    snappedEnd: data?.snapped_end ?? null,
  };
}
