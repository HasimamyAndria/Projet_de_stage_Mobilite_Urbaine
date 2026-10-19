export type LngLat = [number, number];

export type LineStringGeom = {
  type: "LineString";
  coordinates: LngLat[];
};

export type GeometryLike =
  | LineStringGeom
  | { type: "MultiLineString"; coordinates: LngLat[][] }
  | { type: string; coordinates?: unknown };

/** Arc quadratique entre deux points (style desire line maquette). */
export function arcLineString(
  start: LngLat,
  end: LngLat,
  steps = 40
): LineStringGeom {
  const mx = (start[0] + end[0]) / 2;
  const my = (start[1] + end[1]) / 2;
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const len = Math.hypot(dx, dy) || 1;
  const offset = Math.min(0.045, len * 0.22);
  const cx = mx - (dy / len) * offset;
  const cy = my + (dx / len) * offset;

  const coordinates: LngLat[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const u = 1 - t;
    coordinates.push([
      u * u * start[0] + 2 * u * t * cx + t * t * end[0],
      u * u * start[1] + 2 * u * t * cy + t * t * end[1],
    ]);
  }
  return { type: "LineString", coordinates };
}

export function arrowHead(line: LineStringGeom): LineStringGeom {
  const coords = line.coordinates;
  const end = coords[coords.length - 1];
  const prev = coords[Math.max(0, coords.length - 5)];
  const dx = end[0] - prev[0];
  const dy = end[1] - prev[1];
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const size = Math.min(0.016, Math.max(0.0042, len * 0.45));
  const left: LngLat = [
    end[0] - ux * size - uy * size * 0.45,
    end[1] - uy * size + ux * size * 0.45,
  ];
  const right: LngLat = [
    end[0] - ux * size + uy * size * 0.45,
    end[1] - uy * size - ux * size * 0.45,
  ];
  return { type: "LineString", coordinates: [left, end, right] };
}

export function lineEndpoints(
  geometry: GeometryLike | null | undefined
): { start: LngLat; end: LngLat } | null {
  if (!geometry) return null;
  if (geometry.type === "LineString") {
    const coords = geometry.coordinates as LngLat[];
    if (!coords || coords.length < 2) return null;
    return { start: coords[0], end: coords[coords.length - 1] };
  }
  if (geometry.type === "MultiLineString") {
    const coords = (geometry.coordinates as LngLat[][])?.[0];
    if (!coords || coords.length < 2) return null;
    return { start: coords[0], end: coords[coords.length - 1] };
  }
  return null;
}

/** Échelle couleur type maquette MobilitySmart (adaptée volumes démo). */
export const OD_COLOR_STOPS = [
  20, "#166534",
  50, "#22c55e",
  100, "#eab308",
  150, "#f97316",
  220, "#dc2626",
] as const;
