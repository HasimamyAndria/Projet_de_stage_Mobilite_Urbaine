import maplibregl from "maplibre-gl";
import api from "../../services/api";

const SRC = "satellites-src";
const FILL = "satellites-fill";
const POINT = "satellites-point";

export type AnnexesGeoJSON = {
  type: "FeatureCollection";
  features: Array<Record<string, unknown>>;
};

export async function loadSatellites(
  map: maplibregl.Map,
  zoneId?: number | null,
  geojson?: AnnexesGeoJSON | null
) {
  let data: AnnexesGeoJSON;
  if (geojson) {
    data = geojson;
  } else {
    const response = await api.get("/api/emploi-habitat/satellites", {
      params: zoneId ? { zone_id: zoneId, k: 5 } : { k: 5 },
    });
    data = response.data.geojson ?? {
      type: "FeatureCollection",
      features: [],
    };
  }

  const source = map.getSource(SRC) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
    return { geojson: data };
  }

  map.addSource(SRC, { type: "geojson", data });
  map.addLayer({
    id: FILL,
    type: "fill",
    source: SRC,
    filter: ["==", "$type", "Polygon"],
    paint: { "fill-color": "#38bdf8", "fill-opacity": 0.2 },
  });
  map.addLayer({
    id: POINT,
    type: "circle",
    source: SRC,
    filter: ["==", "$type", "Point"],
    paint: {
      "circle-radius": [
        "case",
        ["==", ["get", "type"], "barycenter"],
        11,
        8,
      ],
      "circle-color": [
        "case",
        ["==", ["get", "type"], "barycenter"],
        "#f43f5e",
        "#38bdf8",
      ],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#0f172a",
    },
  });
  return { geojson: data };
}

