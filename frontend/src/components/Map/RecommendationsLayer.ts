import maplibregl from "maplibre-gl";
import api from "../../services/api";

const SRC = "reco-src";
const FILL = "reco-fill";
const LINE = "reco-line";
const POINT = "reco-point";

export async function loadRecommendations(map: maplibregl.Map) {
  const response = await api.get("/api/recommendations");
  const data = response.data.geojson ?? {
    type: "FeatureCollection",
    features: [],
  };

  const source = map.getSource(SRC) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
    return response.data;
  }

  map.addSource(SRC, { type: "geojson", data });
  map.addLayer({
    id: FILL,
    type: "fill",
    source: SRC,
    filter: ["==", "$type", "Polygon"],
    paint: { "fill-color": "#14b8a6", "fill-opacity": 0.22 },
  });
  map.addLayer({
    id: LINE,
    type: "line",
    source: SRC,
    filter: ["==", "$type", "LineString"],
    paint: { "line-color": "#14b8a6", "line-width": 3 },
  });
  map.addLayer({
    id: POINT,
    type: "circle",
    source: SRC,
    filter: ["==", "$type", "Point"],
    paint: {
      "circle-radius": 8,
      "circle-color": "#2dd4bf",
      "circle-stroke-width": 2,
      "circle-stroke-color": "#042f2e",
    },
  });
  return response.data;
}
