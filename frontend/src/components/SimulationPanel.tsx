import { useEffect, useState } from "react";
import api from "../services/api";
import {
  downloadJson,
  downloadSlidesHtml,
  printHtmlReport,
} from "../utils/exportReport";

type Comparison = {
  trips: { ref: number; scenario: number; delta: number };
  km: { ref: number; scenario: number; delta: number };
  avg_time_min: { ref: number; scenario: number; delta: number };
  co2_t: { ref: number; scenario: number; delta: number };
  modal_share: {
    ref: Record<string, number>;
    scenario: Record<string, number>;
  };
};

type Result = {
  action: string;
  action_label: string;
  zone_name: string | null;
  comparison: Comparison;
  assumptions: string[];
  note: string;
  actions_catalog: Record<string, string>;
};

const ACTIONS = [
  ["add_tc_stop", "Arrêt TC"],
  ["add_bike_lane", "Piste cyclable"],
  ["add_park_ride", "Parking relais"],
  ["add_satellite_office", "Bureau satellite"],
  ["zoning_housing", "Friche → logements"],
  ["zoning_jobs", "Mixité emplois"],
  ["telework", "Télétravail"],
] as const;

function fmt(n: number, digits = 1) {
  return n.toLocaleString("fr-FR", { maximumFractionDigits: digits });
}

export default function SimulationPanel() {
  const [action, setAction] = useState("add_tc_stop");
  const [intensity, setIntensity] = useState(0.25);
  const [teleworkRate, setTeleworkRate] = useState(0.2);
  const [pattern, setPattern] = useState("hybrid_1_2");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.get("/api/simulate", {
        params: {
          action,
          intensity,
          telework_rate: teleworkRate,
          telework_pattern: pattern,
        },
      });
      setResult(res.data);
    } catch {
      setError("Simulation indisponible (backend).");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const c = result?.comparison;

  return (
    <aside className="kpi-panel">
      <h2>Simulation what-if</h2>
      <p className="kpi-subtitle">Scénario vs référence · M4</p>

      <label className="field">
        Infrastructure / zonage
        <select value={action} onChange={(e) => setAction(e.target.value)}>
          {ACTIONS.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Intensité {Math.round(intensity * 100)}%
        <input
          type="range"
          min={0.05}
          max={1}
          step={0.05}
          value={intensity}
          onChange={(e) => setIntensity(Number(e.target.value))}
        />
      </label>
      {action === "telework" && (
        <>
          <label className="field">
            Taux télétravail {Math.round(teleworkRate * 100)}%
            <input
              type="range"
              min={0}
              max={0.8}
              step={0.05}
              value={teleworkRate}
              onChange={(e) => setTeleworkRate(Number(e.target.value))}
            />
          </label>
          <label className="field">
            Rythme
            <select value={pattern} onChange={(e) => setPattern(e.target.value)}>
              <option value="full_remote">Full remote</option>
              <option value="hybrid_1_2">Hybride 1-2 j</option>
              <option value="hybrid_3_4">Hybride 3-4 j</option>
            </select>
          </label>
        </>
      )}
      <button type="button" className="search-card-btn" onClick={run} disabled={busy}>
        {busy ? "Calcul…" : "Mesurer l'impact"}
      </button>
      {error && <p className="kpi-error">{error}</p>}

      {c && (
        <>
          <section className="kpi-section">
            <h3>Comparaison côte à côte</h3>
            <table className="compare-table">
              <thead>
                <tr>
                  <th>Indicateur</th>
                  <th>Réf.</th>
                  <th>Scénario</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Trajets / j", c.trips],
                    ["km parcourus", c.km],
                    ["Temps moyen (min)", c.avg_time_min],
                    ["CO₂ (t/j)", c.co2_t],
                  ] as const
                ).map(([label, row]) => (
                  <tr key={label}>
                    <td>{label}</td>
                    <td>{fmt(row.ref)}</td>
                    <td>{fmt(row.scenario)}</td>
                    <td className={row.delta < 0 ? "delta-good" : row.delta > 0 ? "delta-bad" : ""}>
                      {row.delta > 0 ? "+" : ""}
                      {fmt(row.delta)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="kpi-muted">
              Part VP {Math.round((c.modal_share.ref.car || 0) * 100)}% →{" "}
              {Math.round((c.modal_share.scenario.car || 0) * 100)}% · TC{" "}
              {Math.round((c.modal_share.ref.bus || 0) * 100)}% →{" "}
              {Math.round((c.modal_share.scenario.bus || 0) * 100)}%
            </p>
          </section>
          <section className="kpi-note">
            <strong>Hypothèses</strong>
            {(result?.assumptions ?? []).map((a) => (
              <p key={a}>{a}</p>
            ))}
            <p>{result?.note}</p>
          </section>
          <div className="export-row">
            <button
              type="button"
              className="map-btn"
              onClick={() => downloadJson("scenario-whatif.json", result)}
            >
              Données
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                printHtmlReport(
                  `Scénario ${result?.action_label}`,
                  `<p>${result?.assumptions.join(" ")}</p>
                   <table><tr><th>KPI</th><th>Réf</th><th>Scénario</th><th>Delta</th></tr>
                   <tr><td>Trajets</td><td>${c.trips.ref}</td><td>${c.trips.scenario}</td><td>${c.trips.delta}</td></tr>
                   <tr><td>km</td><td>${c.km.ref}</td><td>${c.km.scenario}</td><td>${c.km.delta}</td></tr>
                   <tr><td>CO2 t</td><td>${c.co2_t.ref}</td><td>${c.co2_t.scenario}</td><td>${c.co2_t.delta}</td></tr>
                   </table>`
                )
              }
            >
              PDF
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                downloadSlidesHtml("scenario-comite.html", "Comité mobilité", [
                  `<h1>${result?.action_label}</h1><p>Comparaison à la situation de référence.</p>`,
                  `<h1>Impact</h1><p>km ${c.km.delta} · CO₂ ${c.co2_t.delta} t · temps ${c.avg_time_min.delta} min</p>`,
                  `<h1>Limites</h1><p>${result?.note}</p>`,
                ])
              }
            >
              Présentation
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
