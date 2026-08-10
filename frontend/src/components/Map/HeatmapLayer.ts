import maplibregl from "maplibre-gl";
import api from "../../services/api";

const SOURCE_ID = "od-heatmap";
const LAYER_ID = "od-heatmap-layer";

type ZoneFeature = {
  type: "Feature";
  geometry?: {
    type: string;
    coordinates?: unknown;
  } | null;
  properties?: Record<string, unknown> | null;
};

type ZoneCollection = {
  type: "FeatureCollection";
  features: ZoneFeature[];
};

type PointFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: { weight: number; name: string };
};

function polygonCentroid(coords: number[][]): [number, number] | null {
  if (!coords.length) return null;
  let sx = 0;
  let sy = 0;
  let n = 0;
  for (const c of coords) {
    if (c.length < 2) continue;
    sx += c[0];
    sy += c[1];
    n += 1;
  }
  if (!n) return null;
  return [sx / n, sy / n];
}

function featureCentroid(feature: ZoneFeature): [number, number] | null {
  const g = feature.geometry;
  if (!g) return null;
  if (g.type === "Point") return g.coordinates as [number, number];
  if (g.type === "Polygon") {
    return polygonCentroid((g.coordinates as number[][][])[0] as number[][]);
  }
  if (g.type === "MultiPolygon") {
    return polygonCentroid(
      (g.coordinates as number[][][][])[0]?.[0] as number[][]
    );
  }
  return null;
}

/**
 * Heatmap densité (proxy population+emplois) — style maquette Carte interactive.
 */
export async function loadHeatmap(map: maplibregl.Map) {
  const response = await api.get("/api/od/zones");
  const data = response.data as ZoneCollection;

  const points: PointFeature[] = [];
  for (const feature of data.features) {
    const center = featureCentroid(feature);
    if (!center) continue;
    const props = feature.properties ?? {};
    const weight =
      Number(props.population_proxy ?? 0) + Number(props.jobs_proxy ?? 0);
    points.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: center },
      properties: {
        weight: Math.max(weight, 1),
        name: String(props.name ?? ""),
      },
    });
  }

  const fc = {
    type: "FeatureCollection" as const,
    features: points,
  };

  const source = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(fc as never);
    return;
  }

  map.addSource(SOURCE_ID, { type: "geojson", data: fc as never });
  map.addLayer({
    id: LAYER_ID,
    type: "heatmap",
    source: SOURCE_ID,
    paint: {
      "heatmap-weight": [
        "interpolate",
        ["linear"],
        ["get", "weight"],
        0, 0,
        5000, 0.4,
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
      "heatmap-color": [
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
    },
  });
}
