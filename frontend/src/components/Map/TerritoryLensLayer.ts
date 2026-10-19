import maplibregl from "maplibre-gl";
import type { LensCommune, LensFlow, LensPayload } from "../../lensTypes";
import { importantIds, zoneFlags } from "../../lensReading";
import { arcLineString, arrowHead } from "./geoArc";

const COMMUNES = "lens-communes";
const QUARTIERS = "lens-quartiers";
const FLOWS = "lens-flows";
const ARROWS = "lens-flow-arrows";
const ARROW_ID = "lens-flows-arrow";

const FILL_ID = "lens-communes-fill";
const LINE_ID = "lens-communes-line";
const COMMUNE_LABEL_ID = "lens-commune-labels";
const QUARTIER_ID = "lens-quartiers";
const QUARTIER_HALO_ID = "lens-quartier-halo";
const QUARTIER_FOCUS_ID = "lens-quartiers-focus";
const QUARTIER_ROLE_ID = "lens-quartier-role";
const QUARTIER_SELECTED_LABEL_ID = "lens-quartier-selected-labels";
const QUARTIER_LABEL_ID = "lens-quartier-labels";
const FLOW_HALO_ID = "lens-flows-halo";
const FLOW_ID = "lens-flows-line";

export const TERRITORY_LAYER_IDS = [
  FILL_ID,
  LINE_ID,
  COMMUNE_LABEL_ID,
  FLOW_HALO_ID,
  FLOW_ID,
  ARROW_ID,
  QUARTIER_HALO_ID,
  QUARTIER_FOCUS_ID,
  QUARTIER_ID,
  QUARTIER_ROLE_ID,
  QUARTIER_SELECTED_LABEL_ID,
  QUARTIER_LABEL_ID,
];

/** Vert = départ, orange = arrivée. La pointe du flux est toujours orange. */
const FLOW_GRADIENT: maplibregl.ExpressionSpecification = [
  "interpolate",
  ["linear"],
  ["line-progress"],
  0,
  "#0f766e",
  0.55,
  "#0284c7",
  1,
  "#c2410c",
];

const FLOW_WIDTH: maplibregl.ExpressionSpecification = [
  "interpolate",
  ["linear"],
  ["get", "headcount"],
  10,
  1.8,
  40,
  4,
  80,
  7,
  160,
  12,
  320,
  18,
];

const LABEL_COLOR: maplibregl.ExpressionSpecification = [
  "match",
  ["get", "mark"],
  "origin",
  "#0f766e",
  "destination",
  "#9a3412",
  "both",
  "#a16207",
  "#0f172a",
];

const LABEL_TEXT: maplibregl.ExpressionSpecification = [
  "case",
  ["==", ["get", "roleWord"], ""],
  ["get", "name"],
  ["concat", ["get", "name"], "\n", ["get", "roleWord"]],
];

const NODE_COLOR: maplibregl.ExpressionSpecification = [
  "case",
  ["==", ["get", "mark"], "origin"],
  "#0f766e",
  ["==", ["get", "mark"], "destination"],
  "#c2410c",
  ["==", ["get", "mark"], "both"],
  "#a16207",
  ["==", ["get", "critical"], 1],
  "#b91c1c",
  ["==", ["get", "desert"], 1],
  "#94a3b8",
  "#475569",
];

/** Le zoom doit rester l'entrée du interpolate racine, sinon MapLibre refuse le calque. */
function circleRadius(extra: number): maplibregl.ExpressionSpecification {
  return [
    "interpolate",
    ["linear"],
    ["zoom"],
    10,
    [
      "case",
      ["==", ["get", "emphasis"], "selected"],
      11 + extra,
      ["==", ["get", "emphasis"], "linked"],
      8 + extra,
      ["==", ["get", "important"], 1],
      6.5 + extra,
      3.5 + extra,
    ],
    15,
    [
      "+",
      extra,
      [
        "+",
        ["case", ["==", ["get", "emphasis"], "selected"], 6, ["==", ["get", "emphasis"], "linked"], 3, 0],
        ["interpolate", ["linear"], ["get", "weight"], 0, 5, 60, 9, 180, 14, 400, 18],
      ],
    ],
  ];
}

const NODE_RADIUS = circleRadius(0);
const HALO_RADIUS = circleRadius(7);

const NODE_OPACITY: maplibregl.ExpressionSpecification = [
  "case",
  ["==", ["get", "emphasis"], "selected"],
  1,
  ["==", ["get", "emphasis"], "linked"],
  0.95,
  ["==", ["get", "important"], 1],
  0.8,
  0.28,
];

type Feature = {
  type: "Feature";
  geometry: { type: string; coordinates: unknown };
  properties: Record<string, string | number>;
};

type Collection = { type: "FeatureCollection"; features: Feature[] };

const boundMaps = new WeakSet<maplibregl.Map>();
let onPick: ((id: string, level: "quartier" | "commune", quartierIds: string) => void) | null =
  null;
let clicksBlocked = false;

export function setTerritoryPick(
  handler: (id: string, level: "quartier" | "commune", quartierIds: string) => void
) {
  onPick = handler;
}

export function setTerritoryClicksBlocked(blocked: boolean) {
  clicksBlocked = blocked;
}

function empty(): Collection {
  return { type: "FeatureCollection", features: [] };
}

function communeMark(commune: LensCommune, origins: Set<string>, dests: Set<string>): string {
  const origin = commune.quartier_ids.some((id) => origins.has(id));
  const dest = commune.quartier_ids.some((id) => dests.has(id));
  if (origin && dest) return "both";
  if (origin) return "origin";
  if (dest) return "destination";
  return "idle";
}

function aggregate(flows: LensFlow[], communes: LensCommune[]): Feature[] {
  const byId = new Map(communes.map((commune) => [commune.id, commune]));
  const groups = new Map<string, Feature>();
  for (const flow of flows) {
    if (flow.origin_parent_id === flow.destination_parent_id) continue;
    const key = `${flow.origin_parent_id}|${flow.destination_parent_id}|${flow.purpose}`;
    const existing = groups.get(key);
    if (existing) {
      existing.properties.headcount = Number(existing.properties.headcount) + flow.headcount;
      continue;
    }
    const origin = byId.get(flow.origin_parent_id);
    const dest = byId.get(flow.destination_parent_id);
    if (!origin || !dest) continue;
    const line = arcLineString([origin.lon, origin.lat], [dest.lon, dest.lat]);
    groups.set(key, {
      type: "Feature",
      geometry: line,
      properties: {
        headcount: flow.headcount,
        purpose: flow.purpose,
      },
    });
  }
  return [...groups.values()].sort(
    (a, b) => Number(a.properties.headcount) - Number(b.properties.headcount)
  );
}

function detailed(flows: LensFlow[]): Feature[] {
  const lines: Feature[] = flows.map((flow) => ({
    type: "Feature",
    geometry: arcLineString(
      [flow.origin_lon, flow.origin_lat],
      [flow.destination_lon, flow.destination_lat]
    ),
    properties: {
      headcount: flow.headcount,
      purpose: flow.purpose,
    },
  }));
  lines.sort((a, b) => Number(a.properties.headcount) - Number(b.properties.headcount));
  return lines;
}

function arrowsFor(lines: Feature[]): Feature[] {
  return lines.map((feature) => ({
    type: "Feature",
    geometry: arrowHead(feature.geometry as { type: "LineString"; coordinates: [number, number][] }),
    properties: {
      headcount: feature.properties.headcount,
    },
  }));
}

function visibleFlows(flows: LensFlow[], zoom: number): LensFlow[] {
  const ranked = [...flows].sort((a, b) => b.headcount - a.headcount);
  if (zoom < 11.2) return ranked.slice(0, 5);
  if (zoom < 13.2) return ranked.slice(0, 12);
  return ranked.slice(0, 30);
}

const STYLE_REV = 3;
const styledMaps = new WeakMap<maplibregl.Map, number>();

/** O et D uniquement après un clic. Rien n’est coché tant que l’utilisateur n’a pas choisi. */
function readingOf(
  id: string,
  origins: Set<string>,
  dests: Set<string>
): { mark: string; emphasis: string; roleWord: string } {
  const selectedOrigin = origins.has(id);
  const selectedDest = dests.has(id);
  let mark = "idle";
  let emphasis = "idle";
  if (selectedOrigin && selectedDest) {
    mark = "both";
    emphasis = "selected";
  } else if (selectedOrigin) {
    mark = "origin";
    emphasis = "selected";
  } else if (selectedDest) {
    mark = "destination";
    emphasis = "selected";
  }
  const roleWord =
    mark === "origin"
      ? "ORIGINE"
      : mark === "destination"
        ? "DESTINATION"
        : mark === "both"
          ? "O + D"
          : "";
  return { mark, emphasis, roleWord };
}

function upsert(map: maplibregl.Map, id: string, data: Collection, lineMetrics = false) {
  const source = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
  if (source) source.setData(data as never);
  else map.addSource(id, { type: "geojson", data: data as never, lineMetrics });
}

/** Recrée les flux une fois, pour pouvoir peindre le dégradé origine → destination. */
function retireFlowStyle(map: maplibregl.Map) {
  if (styledMaps.get(map) === STYLE_REV) return;
  for (const id of [FLOW_HALO_ID, FLOW_ID, ARROW_ID, QUARTIER_HALO_ID]) {
    if (map.getLayer(id)) map.removeLayer(id);
  }
  if (map.getSource(FLOWS)) map.removeSource(FLOWS);
  if (map.getSource(ARROWS)) map.removeSource(ARROWS);
  if (map.getLayer(QUARTIER_SELECTED_LABEL_ID)) {
    map.setLayoutProperty(QUARTIER_SELECTED_LABEL_ID, "text-field", LABEL_TEXT);
    map.setPaintProperty(QUARTIER_SELECTED_LABEL_ID, "text-color", LABEL_COLOR);
    map.setFilter(QUARTIER_SELECTED_LABEL_ID, ["==", ["get", "showLabel"], 1]);
  }
  if (map.getLayer(QUARTIER_LABEL_ID)) {
    map.setLayoutProperty(QUARTIER_LABEL_ID, "text-field", LABEL_TEXT);
    map.setPaintProperty(QUARTIER_LABEL_ID, "text-color", LABEL_COLOR);
  }
  for (const id of [QUARTIER_ID, QUARTIER_FOCUS_ID]) {
    if (!map.getLayer(id)) continue;
    map.setPaintProperty(id, "circle-radius", NODE_RADIUS);
    map.setPaintProperty(id, "circle-opacity", NODE_OPACITY);
  }
  styledMaps.set(map, STYLE_REV);
}

function ensureLayer(map: maplibregl.Map, layer: maplibregl.AddLayerObject, beforeId?: string) {
  if (map.getLayer(layer.id)) return;
  if (beforeId && map.getLayer(beforeId)) map.addLayer(layer, beforeId);
  else map.addLayer(layer);
}

const QUARTIER_PICK_LAYERS = [
  QUARTIER_ROLE_ID,
  QUARTIER_SELECTED_LABEL_ID,
  QUARTIER_LABEL_ID,
  QUARTIER_ID,
  QUARTIER_FOCUS_ID,
  QUARTIER_HALO_ID,
];
const COMMUNE_PICK_LAYERS = [COMMUNE_LABEL_ID, FILL_ID, LINE_ID];

function bind(map: maplibregl.Map) {
  if (boundMaps.has(map)) return;
  boundMaps.add(map);
  // Un seul clic : le quartier gagne sur la commune dessous.
  // Deux handlers enchaînés ré-cochaient l’origine qu’on venait de retirer.
  map.on("click", (event) => {
    if (clicksBlocked || !onPick) return;
    const quartierLayers = QUARTIER_PICK_LAYERS.filter((id) => map.getLayer(id));
    if (quartierLayers.length) {
      const hit = map.queryRenderedFeatures(event.point, { layers: quartierLayers })[0];
      const id = hit?.properties?.id;
      if (typeof id === "string" && id) {
        onPick(id, "quartier", id);
        return;
      }
    }
    const communeLayers = COMMUNE_PICK_LAYERS.filter((id) => map.getLayer(id));
    if (!communeLayers.length) return;
    const hit = map.queryRenderedFeatures(event.point, { layers: communeLayers })[0];
    const id = hit?.properties?.id;
    if (typeof id !== "string" || !id) return;
    const raw =
      typeof hit.properties?.quartier_ids === "string" ? hit.properties.quartier_ids : id;
    onPick(id, "commune", raw);
  });
  for (const layerId of [FILL_ID, QUARTIER_ID, QUARTIER_FOCUS_ID, QUARTIER_HALO_ID]) {
    map.on("mouseenter", layerId, () => {
      if (!clicksBlocked) map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layerId, () => {
      if (!clicksBlocked) map.getCanvas().style.cursor = "";
    });
  }
}

export function paintTerritory(
  map: maplibregl.Map,
  lens: LensPayload,
  originIds: string[],
  destIds: string[]
) {
  const origins = new Set(originIds);
  const dests = new Set(destIds);
  const zoom = map.getZoom();
  const hasSelection = originIds.length > 0 || destIds.length > 0;
  const scoped = lens.flows.filter(
    (flow) =>
      (originIds.length === 0 || originIds.includes(flow.origin_id)) &&
      (destIds.length === 0 || destIds.includes(flow.destination_id))
  );
  const ranked = [...scoped].sort((a, b) => b.headcount - a.headcount);
  const shownFlows = hasSelection
    ? ranked.slice(0, zoom < 11.2 ? 8 : zoom < 13.2 ? 16 : 30)
    : visibleFlows(lens.flows, zoom);
  const detailedView = hasSelection || zoom >= 11.2;
  const majors = importantIds(lens.quartiers);
  const labeled = new Set<string>([...originIds, ...destIds]);
  const volume = new Map<string, number>();
  for (const flow of shownFlows) {
    volume.set(flow.origin_id, (volume.get(flow.origin_id) ?? 0) + flow.headcount);
    volume.set(flow.destination_id, (volume.get(flow.destination_id) ?? 0) + flow.headcount);
  }
  const extraLabels = [...volume.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id)
    .filter((id) => !labeled.has(id))
    .slice(0, zoom < 12.6 ? 4 : 10);
  for (const id of extraLabels) labeled.add(id);

  const communeFeatures: Feature[] = lens.communes.map((commune) => ({
    type: "Feature",
    geometry: commune.geometry,
    properties: {
      id: commune.id,
      name: commune.name,
      mark: communeMark(commune, origins, dests),
      quartier_ids: commune.quartier_ids.join(","),
    },
  }));

  const quartierFeatures: Feature[] = lens.quartiers.map((quartier) => {
    const flags = zoneFlags(quartier);
    const reading = readingOf(quartier.id, origins, dests);
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [quartier.lon, quartier.lat] },
      properties: {
        id: quartier.id,
        name: quartier.name,
        mark: reading.mark,
        emphasis: reading.emphasis,
        roleWord: reading.roleWord,
        showLabel: labeled.has(quartier.id) ? 1 : 0,
        role: quartier.role,
        quartier_ids: quartier.id,
        weight: flags.weight,
        important: majors.has(quartier.id) ? 1 : 0,
        critical: flags.critical ? 1 : 0,
        desert: flags.desert ? 1 : 0,
      },
    };
  });

  const flowFeatures = detailedView
    ? detailed(shownFlows)
    : aggregate(shownFlows, lens.communes);
  const arrowFeatures = arrowsFor(flowFeatures);

  retireFlowStyle(map);
  upsert(map, COMMUNES, { type: "FeatureCollection", features: communeFeatures });
  upsert(map, QUARTIERS, { type: "FeatureCollection", features: quartierFeatures });
  upsert(map, FLOWS, { type: "FeatureCollection", features: flowFeatures }, true);
  upsert(map, ARROWS, { type: "FeatureCollection", features: arrowFeatures });

  const zoneFill: maplibregl.ExpressionSpecification = [
    "interpolate",
    ["linear"],
    ["zoom"],
    10,
    ["match", ["get", "mark"], "idle", 0.02, 0.08],
    13.5,
    ["match", ["get", "mark"], "idle", 0.012, 0.045],
  ];
  const nodeStrokeColor: maplibregl.ExpressionSpecification = [
    "case",
    ["==", ["get", "critical"], 1],
    "#dc2626",
    ["==", ["get", "desert"], 1],
    "#475569",
    "#ffffff",
  ];
  const nodeStrokeWidth: maplibregl.ExpressionSpecification = [
    "case",
    ["==", ["get", "critical"], 1],
    3.5,
    ["!=", ["get", "mark"], "idle"],
    2.6,
    1.4,
  ];

  if (!map.getLayer(FILL_ID)) {
    ensureLayer(map, {
      id: FILL_ID,
      type: "fill",
      source: COMMUNES,
      paint: {
        "fill-color": [
          "match",
          ["get", "mark"],
          "origin",
          "#0f766e",
          "destination",
          "#c2410c",
          "both",
          "#a16207",
          "#64748b",
        ],
        "fill-opacity": zoneFill,
      },
    });
    ensureLayer(map, {
      id: LINE_ID,
      type: "line",
      source: COMMUNES,
      paint: {
        "line-color": [
          "match",
          ["get", "mark"],
          "origin",
          "#0f766e",
          "destination",
          "#c2410c",
          "both",
          "#a16207",
          "#475569",
        ],
        "line-width": ["match", ["get", "mark"], "idle", 1.1, 2.6],
        "line-opacity": 0.9,
      },
    });
    ensureLayer(map, {
      id: COMMUNE_LABEL_ID,
      type: "symbol",
      source: COMMUNES,
      maxzoom: 12.3,
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Noto Sans Regular"],
        "text-size": 13,
      },
      paint: {
        "text-color": "#0f172a",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4,
      },
    });
    ensureLayer(map, {
      id: FLOW_HALO_ID,
      type: "line",
      source: FLOWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#ffffff",
        "line-width": ["+", FLOW_WIDTH, 3],
        "line-opacity": 0.92,
      },
    });
    ensureLayer(map, {
      id: FLOW_ID,
      type: "line",
      source: FLOWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-gradient": FLOW_GRADIENT,
        "line-width": FLOW_WIDTH,
        "line-opacity": 0.95,
      },
    });
    ensureLayer(map, {
      id: ARROW_ID,
      type: "line",
      source: ARROWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#c2410c",
        "line-width": ["interpolate", ["linear"], ["get", "headcount"], 10, 2.4, 80, 4.2, 200, 6],
        "line-opacity": 0.98,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_HALO_ID,
      type: "circle",
      source: QUARTIERS,
      filter: ["==", ["get", "emphasis"], "selected"],
      paint: {
        "circle-radius": HALO_RADIUS,
        "circle-color": "#ffffff",
        "circle-opacity": 0,
        "circle-stroke-opacity": 1,
        "circle-stroke-width": 3,
        "circle-stroke-color": NODE_COLOR,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_FOCUS_ID,
      type: "circle",
      source: QUARTIERS,
      maxzoom: 12.2,
      filter: ["any", ["!=", ["get", "mark"], "idle"], ["==", ["get", "important"], 1]],
      paint: {
        "circle-radius": NODE_RADIUS,
        "circle-color": NODE_COLOR,
        "circle-opacity": NODE_OPACITY,
        "circle-stroke-width": nodeStrokeWidth,
        "circle-stroke-color": nodeStrokeColor,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_ID,
      type: "circle",
      source: QUARTIERS,
      minzoom: 12.2,
      paint: {
        "circle-radius": NODE_RADIUS,
        "circle-color": NODE_COLOR,
        "circle-opacity": NODE_OPACITY,
        "circle-stroke-width": nodeStrokeWidth,
        "circle-stroke-color": nodeStrokeColor,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_ROLE_ID,
      type: "symbol",
      source: QUARTIERS,
      filter: ["!=", ["get", "mark"], "idle"],
      layout: {
        "text-field": ["match", ["get", "mark"], "origin", "O", "destination", "D", "both", "OD", ""],
        "text-font": ["Noto Sans Regular"],
        "text-size": 11,
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-color": "#0f172a",
        "text-halo-width": 0.6,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_SELECTED_LABEL_ID,
      type: "symbol",
      source: QUARTIERS,
      maxzoom: 12.6,
      filter: ["==", ["get", "showLabel"], 1],
      layout: {
        "text-field": LABEL_TEXT,
        "text-font": ["Noto Sans Regular"],
        "text-size": 12,
        "text-line-height": 1.15,
        "text-offset": [0, 1.2],
        "text-anchor": "top",
        "text-allow-overlap": true,
        "symbol-sort-key": ["case", ["==", ["get", "emphasis"], "selected"], 0, 1],
      },
      paint: {
        "text-color": LABEL_COLOR,
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4,
      },
    });
    ensureLayer(map, {
      id: QUARTIER_LABEL_ID,
      type: "symbol",
      source: QUARTIERS,
      minzoom: 12.6,
      layout: {
        "text-field": LABEL_TEXT,
        "text-font": ["Noto Sans Regular"],
        "text-size": 12,
        "text-line-height": 1.15,
        "text-offset": [0, 1.2],
        "text-anchor": "top",
        "symbol-sort-key": ["case", ["==", ["get", "emphasis"], "selected"], 0, 1],
      },
      paint: {
        "text-color": LABEL_COLOR,
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.4,
      },
    });
  } else if (map.getLayer(FILL_ID)) {
    map.setPaintProperty(FILL_ID, "fill-opacity", zoneFill);
  }

  const underNodes = QUARTIER_FOCUS_ID;
  ensureLayer(
    map,
    {
      id: FLOW_HALO_ID,
      type: "line",
      source: FLOWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#ffffff",
        "line-width": ["+", FLOW_WIDTH, 3.5],
        "line-opacity": 0.92,
      },
    },
    underNodes
  );
  ensureLayer(
    map,
    {
      id: FLOW_ID,
      type: "line",
      source: FLOWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-gradient": FLOW_GRADIENT,
        "line-width": FLOW_WIDTH,
        "line-opacity": 0.95,
      },
    },
    underNodes
  );
  ensureLayer(
    map,
    {
      id: ARROW_ID,
      type: "line",
      source: ARROWS,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#c2410c",
        "line-width": ["interpolate", ["linear"], ["get", "headcount"], 10, 2.4, 80, 4.2, 200, 6],
        "line-opacity": 0.98,
      },
    },
    underNodes
  );
  ensureLayer(
    map,
    {
      id: QUARTIER_HALO_ID,
      type: "circle",
      source: QUARTIERS,
      filter: ["==", ["get", "emphasis"], "selected"],
      paint: {
        "circle-radius": HALO_RADIUS,
        "circle-color": "#ffffff",
        "circle-opacity": 0,
        "circle-stroke-opacity": 1,
        "circle-stroke-width": 3,
        "circle-stroke-color": NODE_COLOR,
      },
    },
    underNodes
  );

  if (!map.getLayer(QUARTIER_FOCUS_ID) && map.getLayer(FILL_ID)) {
    ensureLayer(map, {
      id: QUARTIER_FOCUS_ID,
      type: "circle",
      source: QUARTIERS,
      maxzoom: 12.2,
      filter: ["any", ["!=", ["get", "mark"], "idle"], ["==", ["get", "important"], 1]],
      paint: {
        "circle-radius": NODE_RADIUS,
        "circle-color": NODE_COLOR,
        "circle-stroke-width": nodeStrokeWidth,
        "circle-stroke-color": nodeStrokeColor,
      },
    });
  }
  if (!map.getLayer(QUARTIER_ROLE_ID) && map.getSource(QUARTIERS)) {
    ensureLayer(map, {
      id: QUARTIER_ROLE_ID,
      type: "symbol",
      source: QUARTIERS,
      filter: ["!=", ["get", "mark"], "idle"],
      layout: {
        "text-field": ["match", ["get", "mark"], "origin", "O", "destination", "D", "both", "OD", ""],
        "text-font": ["Noto Sans Regular"],
        "text-size": 11,
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-color": "#0f172a",
        "text-halo-width": 0.6,
      },
    });
  }
  if (!map.getLayer(QUARTIER_SELECTED_LABEL_ID) && map.getSource(QUARTIERS)) {
    ensureLayer(map, {
      id: QUARTIER_SELECTED_LABEL_ID,
      type: "symbol",
      source: QUARTIERS,
      maxzoom: 12.6,
      filter: ["!=", ["get", "mark"], "idle"],
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Noto Sans Regular"],
        "text-size": 12,
        "text-offset": [0, 1.15],
        "text-anchor": "top",
        "text-allow-overlap": true,
      },
      paint: {
        "text-color": "#0f172a",
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.3,
      },
    });
  }

  bind(map);
}

export function clearTerritory(map: maplibregl.Map) {
  for (const id of [COMMUNES, QUARTIERS, FLOWS, ARROWS]) {
    const source = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
    if (source) source.setData(empty() as never);
  }
}
