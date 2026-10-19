import maplibregl from "maplibre-gl";
import { arcLineString, lineEndpoints } from "./geoArc";

const ZONES = "scenario-zones";
const ZONE_FILL = "scenario-zones-fill";
const ZONE_LINE = "scenario-zones-line";
const FLOWS = "scenario-flows";
const FLOW_LINE = "scenario-flows-line";
const SITES = "scenario-sites";
const SITE_CIRCLE = "scenario-sites-circle";
const bound = new WeakSet<maplibregl.Map>();

type FeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: string; coordinates?: unknown };
    properties: Record<string, unknown> | null;
  }>;
};

export type Indicator = {
  key: string;
  label: string;
  unit: string;
  before: number;
  after: number;
  delta: number;
  higher_is_better: boolean;
};

export type ScenarioPayload = {
  action: string;
  action_label: string;
  question: string;
  disclaimer: string;
  note: string;
  assumptions: string[];
  indicators: Record<string, Indicator>;
  zone_effects: {
    improved: number;
    worsened: number;
    neutral: number;
    improved_names: string[];
    worsened_names: string[];
  };
  zones: FeatureCollection;
  flows: FeatureCollection;
  sites: FeatureCollection;
  company: {
    name: string;
    employee_share: number;
    employee_count: number;
    concerned: number;
    relocated: number;
    work_zone_name: string;
    satellite_name: string | null;
  } | null;
  comparison: {
    trips: { ref: number; scenario: number; delta: number };
    km: { ref: number; scenario: number; delta: number };
    avg_time_min: { ref: number; scenario: number; delta: number };
    co2_t: { ref: number; scenario: number; delta: number };
  };
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

function arcedFlows(data: FeatureCollection): FeatureCollection {
  const features = data.features.flatMap((feature) => {
    const ends = lineEndpoints(feature.geometry as { type: string; coordinates?: unknown });
    if (!ends) return [];
    return [
      {
        ...feature,
        geometry: arcLineString(ends.start, ends.end),
      },
    ];
  });
  return { type: "FeatureCollection", features };
}

function bindPopups(map: maplibregl.Map) {
  if (bound.has(map)) return;
  bound.add(map);
  map.on("click", ZONE_FILL, (event) => {
    const feature = event.features?.[0];
    const props = feature?.properties;
    if (!props) return;
    const name = escapeHtml(String(props.name ?? ""));
    const label = escapeHtml(String(props.effect_label ?? ""));
    new maplibregl.Popup({ offset: 12 })
      .setLngLat(event.lngLat)
      .setHTML(
        `<strong>${name}</strong><br/>${label}<br/>Emploi-habitat ${props.eh_before} → ${props.eh_after}`
      )
      .addTo(map);
  });
  map.on("click", FLOW_LINE, (event) => {
    const props = event.features?.[0]?.properties;
    if (!props) return;
    new maplibregl.Popup({ offset: 8 })
      .setLngLat(event.lngLat)
      .setHTML(
        `<strong>${escapeHtml(String(props.origin_name))} → ${escapeHtml(String(props.dest_name))}</strong><br/>Avant ${props.volume_before} · Après ${props.volume_after}`
      )
      .addTo(map);
  });
  for (const layer of [ZONE_FILL, FLOW_LINE, SITE_CIRCLE]) {
    map.on("mouseenter", layer, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layer, () => {
      map.getCanvas().style.cursor = "";
    });
  }
}

function upsert(
  map: maplibregl.Map,
  sourceId: string,
  data: FeatureCollection,
  addLayers: () => void
) {
  const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
  if (source) {
    source.setData(data);
    return;
  }
  map.addSource(sourceId, { type: "geojson", data });
  addLayers();
}

export function showScenario(map: maplibregl.Map, payload: ScenarioPayload) {
  upsert(map, ZONES, payload.zones, () => {
    map.addLayer({
      id: ZONE_FILL,
      type: "fill",
      source: ZONES,
      paint: {
        "fill-color": [
          "match",
          ["get", "effect"],
          "improved",
          "#16a34a",
          "worsened",
          "#dc2626",
          "#64748b",
        ],
        "fill-opacity": ["match", ["get", "effect"], "neutral", 0.06, 0.42],
      },
    });
    map.addLayer({
      id: ZONE_LINE,
      type: "line",
      source: ZONES,
      paint: {
        "line-color": [
          "match",
          ["get", "effect"],
          "improved",
          "#86efac",
          "worsened",
          "#fecaca",
          "#94a3b8",
        ],
        "line-width": 1.4,
      },
    });
  });

  upsert(map, FLOWS, arcedFlows(payload.flows), () => {
    map.addLayer({
      id: FLOW_LINE,
      type: "line",
      source: FLOWS,
      paint: {
        "line-color": [
          "match",
          ["get", "effect"],
          "improved",
          "#4ade80",
          "worsened",
          "#f87171",
          "#cbd5e1",
        ],
        "line-width": [
          "interpolate",
          ["linear"],
          ["coalesce", ["get", "volume_after"], 0],
          0,
          1.2,
          80,
          2.5,
          400,
          6,
        ],
        "line-opacity": 0.9,
      },
    });
  });

  upsert(map, SITES, payload.sites, () => {
    map.addLayer({
      id: SITE_CIRCLE,
      type: "circle",
      source: SITES,
      paint: {
        "circle-radius": 8,
        "circle-color": "#f8fafc",
        "circle-stroke-color": "#0f172a",
        "circle-stroke-width": 2,
      },
    });
  });

  bindPopups(map);
  setScenarioVisible(map, true);
}

export function setScenarioVisible(map: maplibregl.Map, visible: boolean) {
  const value = visible ? "visible" : "none";
  for (const id of [ZONE_FILL, ZONE_LINE, FLOW_LINE, SITE_CIRCLE]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", value);
  }
}

export function setOdVisible(map: maplibregl.Map, visible: boolean) {
  const value = visible ? "visible" : "none";
  for (const id of ["od-flows-line", "od-flows-line-halo", "od-nodes-circle"]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", value);
  }
}
