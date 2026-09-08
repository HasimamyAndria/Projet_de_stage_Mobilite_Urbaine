import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { OD_COLOR_STOPS, arcLineString, lineEndpoints } from "./geoArc";
import type { OdFilters } from "../../types";

const SOURCE_ID = "od-flows";
const NODES_SOURCE = "od-nodes";
const LAYER_ID = "od-flows-line";
const HALO_ID = "od-flows-line-halo";
const NODES_ID = "od-nodes-circle";

type OdProps = Record<string, unknown>;
type OdFeature = {
  type: "Feature";
  geometry: { type: string; coordinates?: unknown };
  properties: OdProps | null;
};
type OdCollection = {
  type: "FeatureCollection";
  features: OdFeature[];
  profiles?: { hourly?: number[] };
};

let cachedDaily: OdCollection | null = null;
let cachedHourly: number[] | null = null;

function toArcedCollection(data: OdCollection): {
  lines: OdCollection;
  nodes: OdCollection;
} {
  const lines: OdFeature[] = [];
  const nodeMap = new Map<string, OdFeature>();

  for (const feature of data.features) {
    const ends = lineEndpoints(feature.geometry);
    if (!ends) {
      lines.push(feature);
      continue;
    }
    lines.push({
      ...feature,
      geometry: arcLineString(ends.start, ends.end),
    });

    const pairs: Array<[string, [number, number], string]> = [
      [
        `o-${String(feature.properties?.origin_zone_id ?? "")}`,
        ends.start,
        "origin_name",
      ],
      [
        `d-${String(feature.properties?.destination_zone_id ?? "")}`,
        ends.end,
        "destination_name",
      ],
    ];

    for (const [key, coord, nameKey] of pairs) {
      if (!nodeMap.has(key)) {
        nodeMap.set(key, {
          type: "Feature",
          geometry: { type: "Point", coordinates: coord },
          properties: {
            name: feature.properties?.[nameKey] ?? "",
          },
        });
      }
    }
  }

  return {
    lines: { type: "FeatureCollection", features: lines },
    nodes: { type: "FeatureCollection", features: [...nodeMap.values()] },
  };
}

function scaleByHour(data: OdCollection, hour: number | null): OdCollection {
  if (hour == null || !cachedHourly) return data;
  const share = cachedHourly[hour] ?? 1 / 24;
  const factor = share * 24;
  return {
    ...data,
    features: data.features.map((f) => {
      const daily = Number(
        f.properties?.volume_daily ?? f.properties?.passenger_count ?? 0
      );
      return {
        ...f,
        properties: {
          ...f.properties,
          passenger_count: Math.max(1, Math.round(daily * factor)),
          hour,
        },
      };
    }),
  };
}

function paintFlows(map: maplibregl.Map, data: OdCollection) {
  const { lines, nodes } = toArcedCollection(data);
  const lineSource = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
  if (lineSource) {
    lineSource.setData(lines as never);
  } else {
    map.addSource(SOURCE_ID, { type: "geojson", data: lines as never });
    map.addLayer({
      id: HALO_ID,
      type: "line",
      source: SOURCE_ID,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": [
          "interpolate",
          ["linear"],
          ["get", "passenger_count"],
          ...OD_COLOR_STOPS,
        ],
        "line-opacity": 0.22,
        "line-width": [
          "interpolate",
          ["linear"],
          ["get", "passenger_count"],
          20, 5,
          100, 9,
          220, 14,
        ],
        "line-blur": 0.8,
      },
    });
    map.addLayer({
      id: LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": [
          "interpolate",
          ["linear"],
          ["get", "passenger_count"],
          ...OD_COLOR_STOPS,
        ],
        "line-width": [
          "interpolate",
          ["linear"],
          ["get", "passenger_count"],
          20, 1.5,
          50, 2.2,
          100, 3.2,
          150, 4.2,
          220, 6,
        ],
        "line-opacity": 0.92,
      },
    });
  }

  const nodeSource = map.getSource(NODES_SOURCE) as maplibregl.GeoJSONSource | undefined;
  if (nodeSource) {
    nodeSource.setData(nodes as never);
  } else {
    map.addSource(NODES_SOURCE, { type: "geojson", data: nodes as never });
    map.addLayer({
      id: NODES_ID,
      type: "circle",
      source: NODES_SOURCE,
      paint: {
        "circle-radius": 6,
        "circle-color": "#ffffff",
        "circle-stroke-width": 2.5,
        "circle-stroke-color": "#0f172a",
        "circle-opacity": 0.95,
      },
    });
  }
}

export function applyOdHour(map: maplibregl.Map, hour: number | null) {
  if (!cachedDaily) return;
  paintFlows(map, scaleByHour(cachedDaily, hour));
}

export async function loadOdFlows(
  map: maplibregl.Map,
  filters: OdFilters | number = 50
) {
  const f: OdFilters =
    typeof filters === "number"
      ? { hour: null, weekday: null, mode: "all", minPassengers: filters }
      : filters;

  const params: Record<string, string | number> = {
    min_passengers: f.minPassengers,
    limit: 80,
  };
  if (f.weekday != null) params.weekday = f.weekday;
  if (f.mode && f.mode !== "all") params.mode = f.mode;

  const response = await api.get("/api/od/flows", { params });
  const raw = response.data as OdCollection;
  cachedDaily = raw;
  cachedHourly = raw.profiles?.hourly ?? null;
  paintFlows(map, scaleByHour(raw, f.hour));
}

export async function loadMobilityZones(map: maplibregl.Map) {
  const response = await api.get("/api/od/zones");
  const data = response.data;

  const sourceId = "mobility-zones";
  const fillId = "mobility-zones-fill";
  const lineId = "mobility-zones-outline";

  const source = map.getSource(sourceId);
  if (source) {
    (source as maplibregl.GeoJSONSource).setData(data);
    return;
  }

  map.addSource(sourceId, { type: "geojson", data });
  map.addLayer({
    id: fillId,
    type: "fill",
    source: sourceId,
    layout: { visibility: "none" },
    paint: { "fill-color": "#0ea5e9", "fill-opacity": 0.1 },
  });
  map.addLayer({
    id: lineId,
    type: "line",
    source: sourceId,
    layout: { visibility: "none" },
    paint: {
      "line-color": "#64748b",
      "line-width": 1,
      "line-dasharray": [2, 1],
      "line-opacity": 0.55,
    },
  });
}

export function fitMapToBBox(
  map: maplibregl.Map,
  bbox: { west: number; south: number; east: number; north: number },
  duration = 900
) {
  if (
    !Number.isFinite(bbox.west) ||
    !Number.isFinite(bbox.south) ||
    !Number.isFinite(bbox.east) ||
    !Number.isFinite(bbox.north) ||
    bbox.east <= bbox.west ||
    bbox.north <= bbox.south
  ) {
    return;
  }
  map.fitBounds(
    [
      [bbox.west, bbox.south],
      [bbox.east, bbox.north],
    ],
    { padding: 48, maxZoom: 13, duration }
  );
}

export function fitMapToOdZones(map: maplibregl.Map) {
  fitMapToBBox(map, {
    west: 47.45,
    south: -18.95,
    east: 47.565,
    north: -18.82,
  });
}
