import maplibregl from "maplibre-gl";
import { arcLineString } from "./geoArc";

const SRC = "analysis-scenario-src";
const LINE = "analysis-scenario-line";
const SITE_LINE = "analysis-scenario-site-line";
const POINT = "analysis-scenario-point";
const boundMaps = new WeakSet<maplibregl.Map>();

export type LngPlace = {
  name: string;
  lon: number;
  lat: number;
  headcount?: number;
};

export type ScenarioDraw = {
  title: string;
  note: string;
  origins: LngPlace[];
  destination: LngPlace;
  site?: LngPlace | null;
};

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (ch) => {
    if (ch === "&") return "&amp;";
    if (ch === "<") return "&lt;";
    if (ch === ">") return "&gt;";
    if (ch === '"') return "&quot;";
    return "&#39;";
  });
}

function collection(draw: ScenarioDraw) {
  const features: Array<{
    type: "Feature";
    geometry:
      | { type: "LineString"; coordinates: [number, number][] }
      | { type: "Point"; coordinates: [number, number] };
    properties: { role: string; label: string; headcount: number };
  }> = [];
  const dest: [number, number] = [draw.destination.lon, draw.destination.lat];
  for (const origin of draw.origins) {
    const start: [number, number] = [origin.lon, origin.lat];
    features.push({
      type: "Feature",
      geometry: arcLineString(start, dest),
      properties: {
        role: "corridor",
        label: `${origin.name} → ${draw.destination.name}`,
        headcount: origin.headcount ?? 0,
      },
    });
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: start },
      properties: {
        role: "origin",
        label: origin.name,
        headcount: origin.headcount ?? 0,
      },
    });
    if (draw.site) {
      features.push({
        type: "Feature",
        geometry: arcLineString(start, [draw.site.lon, draw.site.lat]),
        properties: {
          role: "vers_site",
          label: `${origin.name} → ${draw.site.name} (site proposé)`,
          headcount: origin.headcount ?? 0,
        },
      });
    }
  }
  features.push({
    type: "Feature",
    geometry: { type: "Point", coordinates: dest },
    properties: { role: "seat", label: draw.destination.name, headcount: 0 },
  });
  if (draw.site) {
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [draw.site.lon, draw.site.lat] },
      properties: { role: "site", label: `${draw.site.name} — site proposé`, headcount: 0 },
    });
  }
  return { type: "FeatureCollection" as const, features };
}

export function scenarioBounds(draw: ScenarioDraw) {
  const bounds = new maplibregl.LngLatBounds();
  for (const origin of draw.origins) bounds.extend([origin.lon, origin.lat]);
  bounds.extend([draw.destination.lon, draw.destination.lat]);
  if (draw.site) bounds.extend([draw.site.lon, draw.site.lat]);
  return bounds;
}

function bindPopups(map: maplibregl.Map) {
  if (boundMaps.has(map)) return;
  boundMaps.add(map);
  const open = (
    event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }
  ) => {
    const label = event.features?.[0]?.properties?.label;
    if (!label) return;
    new maplibregl.Popup({ offset: 12 })
      .setLngLat(event.lngLat)
      .setHTML(
        `<strong>${escapeHtml(String(label))}</strong><p>Estimation simulée</p>`
      )
      .addTo(map);
  };
  for (const id of [LINE, SITE_LINE, POINT]) {
    map.on("click", id, open);
    map.on("mouseenter", id, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", id, () => {
      map.getCanvas().style.cursor = "";
    });
  }
}

export function showAnalysisScenario(map: maplibregl.Map, draw: ScenarioDraw) {
  const data = collection(draw);
  const source = map.getSource(SRC) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
    return;
  }
  map.addSource(SRC, { type: "geojson", data });
  map.addLayer({
    id: LINE,
    type: "line",
    source: SRC,
    filter: ["==", ["get", "role"], "corridor"],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": "#c2410c",
      "line-width": ["interpolate", ["linear"], ["coalesce", ["get", "headcount"], 0], 10, 2, 80, 7],
      "line-opacity": 0.9,
    },
  });
  map.addLayer({
    id: SITE_LINE,
    type: "line",
    source: SRC,
    filter: ["==", ["get", "role"], "vers_site"],
    layout: { "line-cap": "round" },
    paint: {
      "line-color": "#14b8a6",
      "line-width": 2,
      "line-dasharray": [1.4, 1.2],
      "line-opacity": 0.95,
    },
  });
  map.addLayer({
    id: POINT,
    type: "circle",
    source: SRC,
    filter: ["==", "$type", "Point"],
    paint: {
      "circle-radius": ["match", ["get", "role"], "seat", 8, "site", 9, 5],
      "circle-color": ["match", ["get", "role"], "seat", "#c2410c", "site", "#14b8a6", "#2563eb"],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#0f172a",
    },
  });
  bindPopups(map);
}

export function clearAnalysisScenario(map: maplibregl.Map) {
  const source = map.getSource(SRC) as maplibregl.GeoJSONSource | undefined;
  if (!source) return;
  source.setData({ type: "FeatureCollection", features: [] });
}
