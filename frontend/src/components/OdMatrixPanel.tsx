import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import type { OdFilters } from "../types";
import { downloadJson } from "../utils/exportReport";

type Cell = {
  origin_zone_id: number;
  destination_zone_id: number;
  origin_name: string;
  destination_name: string;
  passenger_count: number;
};

type MatrixPayload = {
  zones: Array<{ id: number; name: string }>;
  cells: Cell[];
  note?: string;
};

type Props = {
  filters: OdFilters;
};

export default function OdMatrixPanel({ filters }: Props) {
  const [data, setData] = useState<MatrixPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string | number> = {
          min_passengers: filters.minPassengers,
        };
        if (filters.hour != null) params.hour = filters.hour;
        if (filters.weekday != null) params.weekday = filters.weekday;
        if (filters.mode !== "all") params.mode = filters.mode;
        const res = await api.get("/api/od/matrix", { params });
        if (!cancelled) setData(res.data);
      } catch {
        if (!cancelled) setError("Impossible de charger la matrice OD.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const lookup = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of data?.cells ?? []) {
      map.set(`${c.origin_zone_id}-${c.destination_zone_id}`, c.passenger_count);
    }
    return map;
  }, [data]);

  const max = useMemo(
    () => Math.max(1, ...Array.from(lookup.values())),
    [lookup]
  );

  if (loading) {
    return (
      <aside className="kpi-panel">
        <h2>Matrice OD</h2>
        <p className="kpi-muted">Chargement…</p>
      </aside>
    );
  }
  if (error || !data) {
    return (
      <aside className="kpi-panel">
        <h2>Matrice OD</h2>
        <p className="kpi-error">{error}</p>
      </aside>
    );
  }

  const zones = data.zones.slice(0, 16);

  return (
    <aside className="kpi-panel">
      <h2>Matrice origine-destination</h2>
      <p className="kpi-subtitle">Filtrable · heure / mode / jour · M1</p>
      <div className="od-matrix-wrap">
        <table className="od-matrix">
          <thead>
            <tr>
              <th>O \ D</th>
              {zones.map((z) => (
                <th key={z.id} title={z.name}>
                  {z.name.replace("Zone ", "")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {zones.map((o) => (
              <tr key={o.id}>
                <th>{o.name.replace("Zone ", "")}</th>
                {zones.map((d) => {
                  if (o.id === d.id) {
                    return <td key={d.id} className="od-diag">—</td>;
                  }
                  const v = lookup.get(`${o.id}-${d.id}`) ?? 0;
                  const t = v / max;
                  return (
                    <td
                      key={d.id}
                      style={{
                        background: `rgba(251, 146, 60, ${0.08 + t * 0.7})`,
                      }}
                      title={`${o.name} → ${d.name} : ${v}`}
                    >
                      {v || ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="kpi-muted">{data.note}</p>
      <button
        type="button"
        className="map-btn"
        onClick={() => downloadJson("matrice-od.json", data)}
      >
        Exporter JSON
      </button>
    </aside>
  );
}
