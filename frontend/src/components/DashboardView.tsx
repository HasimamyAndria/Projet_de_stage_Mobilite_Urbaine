import { useEffect, useState } from "react";
import api from "../services/api";
import {
  downloadJson,
  downloadSlidesHtml,
  printHtmlReport,
} from "../utils/exportReport";

type Kpi = { id: string; label: string; value: number | null; unit: string; hint: string };
type Point = { period: string; trips: number; km: number; co2_t: number };
type Bench = {
  city: string;
  eh_index: number | null;
  tc_share: number;
  avg_time_min: number;
  self?: boolean;
};
type Obj = {
  name: string;
  horizon: string;
  target: number;
  current: number;
  progress: number;
  unit: string;
};

type Dash = {
  kpis: Kpi[];
  timeseries: { points: Point[]; note: string };
  benchmark: Bench[];
  objectives: Obj[];
  note: string;
};

function fmt(v: number | null, unit: string) {
  if (v == null) return "—";
  const n = v.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
  return unit ? `${n} ${unit}` : n;
}

export default function DashboardView() {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [granularity, setGranularity] = useState<"month" | "quarter" | "year">("month");

  useEffect(() => {
    api
      .get("/api/kpi/dashboard")
      .then((res) => setData(res.data))
      .catch(() => setError("Tableau de bord indisponible (API)."));
  }, []);

  if (error) {
    return (
      <div className="dash-page">
        <p className="kpi-error">{error}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="dash-page">
        <p className="kpi-muted">Chargement des indicateurs…</p>
      </div>
    );
  }

  const maxTrips = Math.max(...data.timeseries.points.map((p) => p.trips), 1);
  const points =
    granularity === "year"
      ? [
          {
            period: "2025",
            trips: Math.round(
              data.timeseries.points.reduce((s, p) => s + p.trips, 0) / 12
            ),
            km: 0,
            co2_t: 0,
          },
        ]
      : granularity === "quarter"
        ? [0, 1, 2, 3].map((q) => {
            const slice = data.timeseries.points.slice(q * 3, q * 3 + 3);
            return {
              period: `T${q + 1} 2025`,
              trips: Math.round(slice.reduce((s, p) => s + p.trips, 0) / slice.length),
              km: 0,
              co2_t: 0,
            };
          })
        : data.timeseries.points;

  return (
    <div className="dash-page">
      <header className="dash-head">
        <div>
          <h1>Tableau de bord exécutif</h1>
          <p>6-8 indicateurs · objectifs PDM / SCoT · benchmark illustratif</p>
        </div>
        <div className="export-row">
          <button
            type="button"
            className="map-btn"
            onClick={() => downloadJson("dashboard-kpi.json", data)}
          >
            Données
          </button>
          <button
            type="button"
            className="map-btn"
            onClick={() =>
              printHtmlReport(
                "Tableau de bord mobilité",
                `<div>${data.kpis.map((k) => `<p><b>${k.label}</b> ${fmt(k.value, k.unit)}</p>`).join("")}</div>
                 <h2>Objectifs</h2>
                 <ul>${data.objectives.map((o) => `<li>${o.name} (${o.horizon}) : ${o.current} / cible ${o.target}</li>`).join("")}</ul>`
              )
            }
          >
            PDF conseil
          </button>
          <button
            type="button"
            className="map-btn"
            onClick={() =>
              downloadSlidesHtml("dashboard-conseil.html", "Conseil municipal", [
                `<h1>MobilitySmart</h1><p>Synthèse exécutive Antananarivo (démo)</p>`,
                `<h1>8 KPI</h1><ul>${data.kpis.map((k) => `<li>${k.label} : ${fmt(k.value, k.unit)}</li>`).join("")}</ul>`,
                `<h1>Objectifs PDM / SCoT</h1><ul>${data.objectives.map((o) => `<li>${o.name} — ${o.horizon}</li>`).join("")}</ul>`,
                `<h1>Limites</h1><p>${data.note}</p>`,
              ])
            }
          >
            PowerPoint (HTML)
          </button>
        </div>
      </header>

      <section className="dash-kpis">
        {data.kpis.map((k) => (
          <article key={k.id} className="dash-kpi">
            <span className="label">{k.label}</span>
            <span className="value">{fmt(k.value, k.unit)}</span>
            <span className="hint">{k.hint}</span>
          </article>
        ))}
      </section>

      <section className="dash-grid">
        <article className="dash-card">
          <div className="dash-card-head">
            <h2>Évolution temporelle</h2>
            <select
              value={granularity}
              onChange={(e) =>
                setGranularity(e.target.value as "month" | "quarter" | "year")
              }
            >
              <option value="month">Mois</option>
              <option value="quarter">Trimestre</option>
              <option value="year">Année</option>
            </select>
          </div>
          <div className="spark-row">
            {points.map((p) => (
              <div key={p.period} className="spark-col" title={String(p.trips)}>
                <div
                  className="spark-bar"
                  style={{ height: `${Math.max(8, (p.trips / maxTrips) * 100)}%` }}
                />
                <span>{p.period.replace("2025-", "")}</span>
              </div>
            ))}
          </div>
          <p className="kpi-muted">{data.timeseries.note}</p>
        </article>

        <article className="dash-card">
          <h2>Benchmark métropoles</h2>
          <table className="compare-table">
            <thead>
              <tr>
                <th>Ville</th>
                <th>Indice EH</th>
                <th>Part TC</th>
                <th>Temps</th>
              </tr>
            </thead>
            <tbody>
              {data.benchmark.map((b) => (
                <tr key={b.city} className={b.self ? "row-self" : undefined}>
                  <td>{b.city}</td>
                  <td>{b.eh_index ?? "—"}</td>
                  <td>{Math.round((b.tc_share || 0) * 100)}%</td>
                  <td>{b.avg_time_min} min</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="kpi-muted">Valeurs hors démo : illustratives.</p>
        </article>

        <article className="dash-card dash-card-wide">
          <h2>Objectifs métropolitains</h2>
          {data.objectives.map((o) => (
            <div key={o.name} className="obj-row">
              <div className="obj-meta">
                <strong>{o.name}</strong>
                <span>
                  {o.horizon} · actuel {o.current} · cible {o.target} {o.unit}
                </span>
              </div>
              <div className="obj-bar">
                <div
                  style={{ width: `${Math.min(100, o.progress * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </article>
      </section>
      <p className="kpi-muted dash-foot">{data.note}</p>
    </div>
  );
}
