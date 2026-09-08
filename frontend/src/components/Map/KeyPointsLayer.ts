import maplibregl from "maplibre-gl";
import api from "../../services/api";

const ZONES_SOURCE = "keypoints-zones";
const ZONES_FILL = "keypoints-zones-fill";
const ZONES_LINE = "keypoints-zones-line";
const CORRIDORS_SOURCE = "keypoints-corridors";
const CORRIDORS_LINE = "keypoints-corridors-line";
const CONV_SOURCE = "keypoints-convergence-src";
const CONV_LAYER = "keypoints-convergence";
const DESERT_SOURCE = "keypoints-deserts";
const DESERT_FILL = "keypoints-deserts-fill";
const DESERT_LINE = "keypoints-deserts-line";
const CARPOOL_SOURCE = "keypoints-carpool";
const CARPOOL_LINE = "keypoints-carpool-line";
const UNB_SOURCE = "keypoints-unbalanced";
const UNB_LINE = "keypoints-unbalanced-line";

function setOrAdd(
  map: maplibregl.Map,
  sourceId: string,
  data: unknown,
  addLayers: () => void
) {
  const source = map.getSource(sourceId);
  if (source) {
    (source as maplibregl.GeoJSONSource).setData(data as never);
    return;
  }
  map.addSource(sourceId, { type: "geojson", data: data as never });
  addLayers();
}

export async function loadKeyPoints(map: maplibregl.Map) {
  const response = await api.get("/api/keypoints", {
    params: { corridor_top_n: 5 },
  });
  const data = response.data;
  const empty = { type: "FeatureCollection", features: [] };

  setOrAdd(map, ZONES_SOURCE, data.zones ?? empty, () => {
    map.addLayer({
      id: ZONES_FILL,
      type: "fill",
      source: ZONES_SOURCE,
      paint: {
        "fill-color": [
          "match",
          ["get", "label"],
          "dormitory", "#7c3aed",
          "employment", "#ea580c",
          "balanced", "#38bdf8",
          "#94a3b8",
        ],
        "fill-opacity": 0.28,
      },
    });
    map.addLayer({
      id: ZONES_LINE,
      type: "line",
      source: ZONES_SOURCE,
      paint: {
        "line-color": [
          "match",
          ["get", "label"],
          "dormitory", "#5b21b6",
          "employment", "#c2410c",
          "balanced", "#0284c7",
          "#64748b",
        ],
        "line-width": 2,
      },
    });
  });

  setOrAdd(map, CORRIDORS_SOURCE, data.corridors ?? empty, () => {
    map.addLayer({
      id: CORRIDORS_LINE,
      type: "line",
      source: CORRIDORS_SOURCE,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": "#dc2626", "line-width": 5, "line-opacity": 0.9 },
    });
  });

  setOrAdd(map, CONV_SOURCE, data.convergence ?? empty, () => {
    map.addLayer({
      id: CONV_LAYER,
      type: "circle",
      source: CONV_SOURCE,
      paint: {
        "circle-radius": 10,
        "circle-color": "#fbbf24",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#78350f",
        "circle-opacity": 0.9,
      },
    });
  });

  setOrAdd(map, DESERT_SOURCE, data.deserts ?? empty, () => {
    map.addLayer({
      id: DESERT_FILL,
      type: "fill",
      source: DESERT_SOURCE,
      paint: { "fill-color": "#64748b", "fill-opacity": 0.28 },
    });
    map.addLayer({
      id: DESERT_LINE,
      type: "line",
      source: DESERT_SOURCE,
      paint: {
        "line-color": "#94a3b8",
        "line-width": 2,
        "line-dasharray": [2, 1],
      },
    });
  });

  setOrAdd(map, CARPOOL_SOURCE, data.carpool ?? empty, () => {
    map.addLayer({
      id: CARPOOL_LINE,
      type: "line",
      source: CARPOOL_SOURCE,
      layout: { "line-cap": "round" },
      paint: {
        "line-color": "#22d3ee",
        "line-width": 3.5,
        "line-dasharray": [2, 1],
        "line-opacity": 0.85,
      },
    });
  });

  setOrAdd(map, UNB_SOURCE, data.unbalanced_pairs ?? empty, () => {
    map.addLayer({
      id: UNB_LINE,
      type: "line",
      source: UNB_SOURCE,
      layout: { "line-cap": "round" },
      paint: {
        "line-color": "#c084fc",
        "line-width": 3,
        "line-opacity": 0.8,
      },
    });
  });

  return data;
}
