import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { OD_COLOR_STOPS, arcLineString, lineEndpoints } from "./geoArc";

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
};

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

/** Desire lines courbes + nœuds — rendu type maquette « Carte interactive ». */
export async function loadOdFlows(
  map: maplibregl.Map,
  minPassengers = 50
) {
  const response = await api.get("/api/od/flows", {
    params: {
      min_passengers: minPassengers,
      limit: 80,
    },
  });

  const raw = response.data as OdCollection;
  const { lines, nodes } = toArcedCollection(raw);
  console.log("Flux OD (arcs) :", lines.features.length);

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

export function fitMapToOdZones(map: maplibregl.Map) {
  map.fitBounds(
    [
      [47.450, -18.950],
      [47.565, -18.820],
    ],
    { padding: 48, maxZoom: 12.5, duration: 800 }
  );
}
