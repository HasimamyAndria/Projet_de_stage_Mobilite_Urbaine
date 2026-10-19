import { useEffect, useState } from "react";
import api from "../services/api";
import type { ScenarioPayload } from "./Map/ScenarioLayer";
import {
  downloadJson,
  downloadSlidesHtml,
  printHtmlReport,
} from "../utils/exportReport";

type Catalog = {
  scenarios: Array<{ code: string; action: string; label: string; question: string }>;
  organizations: Array<{
    key: string;
    name: string;
    work_zone_id: number;
    work_zone_name: string;
    employee_count: number;
  }>;
  zones: Array<{ id: number; name: string; population_proxy: number; jobs_proxy: number }>;
  disclaimer: string;
};

type Pinned = {
  id: string;
  label: string;
  payload: ScenarioPayload;
};

const INDICATOR_ORDER = [
  "trips",
  "km",
  "avg_time_min",
  "co2_t",
  "flow_volume",
  "corridor_pressure",
  "emploi_habitat",
];

function fmt(n: number, digits = 1) {
  return n.toLocaleString("fr-FR", { maximumFractionDigits: digits });
}

type SweepRow = { label: string; time: number; co2: number };

type Props = {
  onScenario: (payload: ScenarioPayload | null) => void;
  initialAction?: string | null;
};

export default function SimulationPanel({ onScenario, initialAction = null }: Props) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [action, setAction] = useState("add_satellite_office");
  const [orgKey, setOrgKey] = useState("");
  const [employeeShare, setEmployeeShare] = useState(0.2);
  const [teleworkRate, setTeleworkRate] = useState(0.2);
  const [pattern, setPattern] = useState("hybrid_1_2");
  const [zoneId, setZoneId] = useState<number | "">("");
  const [targetZoneId, setTargetZoneId] = useState<number | "">("");
  const [intensity, setIntensity] = useState(0.25);
  const [stagger, setStagger] = useState(0.2);
  const [result, setResult] = useState<ScenarioPayload | null>(null);
  const [pinned, setPinned] = useState<Pinned[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sweep, setSweep] = useState<SweepRow[] | null>(null);
  const [sweepBusy, setSweepBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/simulate/catalog")
      .then((res) => {
        if (cancelled) return;
        const data = res.data as Catalog;
        setCatalog(data);
        if (data.organizations[0]) setOrgKey(data.organizations[0].key);
        if (data.zones[0]) setZoneId(data.zones[0].id);
        const jobs = [...data.zones].sort((a, b) => b.jobs_proxy - a.jobs_proxy);
        const homes = [...data.zones].sort((a, b) => b.population_proxy - a.population_proxy);
        if (jobs[0]) setZoneId(jobs[0].id);
        if (homes[0] && homes[0].id !== jobs[0]?.id) setTargetZoneId(homes[0].id);
        else if (jobs[1]) setTargetZoneId(jobs[1].id);
      })
      .catch(() => {
        if (!cancelled) setError("Catalogue de simulation indisponible.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (initialAction) setAction(initialAction);
  }, [initialAction]);

  useEffect(() => {
    if (!catalog) return;
    const preferred =
      initialAction && catalog.scenarios.some((item) => item.action === initialAction)
        ? initialAction
        : null;
    if (preferred && preferred !== action) setAction(preferred);
    void run(preferred ?? undefined);
    // Le premier calcul part dès que le catalogue (et l'exemple demandé) est connu.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog, initialAction]);

  useEffect(() => () => onScenario(null), [onScenario]);

  async function run(actionOverride?: string) {
    const used = actionOverride ?? action;
    setBusy(true);
    setError(null);
    setSweep(null);
    try {
      const res = await api.get("/api/simulate", {
        params: {
          action: used,
          zone_id: zoneId === "" ? undefined : zoneId,
          target_zone_id: targetZoneId === "" ? undefined : targetZoneId,
          intensity,
          telework_rate: teleworkRate,
          telework_pattern: pattern,
          employee_share: employeeShare,
          organization_key: orgKey || undefined,
          stagger_share: stagger,
        },
      });
      const payload = res.data as ScenarioPayload;
      setResult(payload);
      onScenario(payload);
    } catch {
      setError("Simulation indisponible (backend ou données OD).");
      onScenario(null);
    } finally {
      setBusy(false);
    }
  }

  async function runSweep() {
    const steps =
      action === "add_satellite_office"
        ? [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        : action === "telework"
          ? [0.1, 0.2, 0.4, 0.6, 0.8]
          : [0.2, 0.4, 0.6, 0.8, 1];
    setSweepBusy(true);
    setError(null);
    try {
      const rows: SweepRow[] = [];
      for (const rate of steps) {
        const res = await api.get("/api/simulate", {
          params: {
            action,
            zone_id: zoneId === "" ? undefined : zoneId,
            target_zone_id: targetZoneId === "" ? undefined : targetZoneId,
            intensity: action === "add_satellite_office" || action === "telework" ? intensity : rate,
            telework_rate: action === "telework" ? rate : teleworkRate,
            telework_pattern: pattern,
            employee_share: action === "add_satellite_office" ? rate : employeeShare,
            organization_key: orgKey || undefined,
            stagger_share: action === "shift_schedules" ? rate : stagger,
          },
        });
        const payload = res.data as ScenarioPayload;
        rows.push({
          label: `${Math.round(rate * 100)} %`,
          time: payload.indicators.avg_time_min?.delta ?? 0,
          co2: payload.indicators.co2_t?.delta ?? 0,
        });
      }
      setSweep(rows);
    } catch {
      setError("Le test des taux n'a pas abouti.");
    } finally {
      setSweepBusy(false);
    }
  }

  function pin() {
    if (!result) return;
    const id = [
      result.action,
      orgKey,
      employeeShare,
      teleworkRate,
      pattern,
      zoneId,
      targetZoneId,
      intensity,
      stagger,
    ].join("|");
    const label = result.action_label;
    setPinned((prev) => {
      const next = prev.filter((item) => item.id !== id);
      next.push({ id, label, payload: result });
      return next.slice(-4);
    });
  }

  const card = catalog?.scenarios.find((item) => item.action === action);
  const org = catalog?.organizations.find((item) => item.key === orgKey);
  const indicators = INDICATOR_ORDER.map((key) => result?.indicators[key]).filter(
    (item): item is ScenarioPayload["indicators"][string] => Boolean(item)
  );

  return (
    <aside className="kpi-panel sim-panel">
      <div className="sim-badge">SIMULATION</div>
      <h2>Que se passerait-il ?</h2>
      <p className="kpi-subtitle">
        Si l&apos;organisation de la ville changeait. Comparer avant et après, sans en faire une prévision.
      </p>

      <div className="sim-grid">
        {(catalog?.scenarios ?? []).map((item) => (
          <button
            key={item.action}
            type="button"
            className={action === item.action ? "sim-choice active" : "sim-choice"}
            onClick={() => setAction(item.action)}
          >
            <b>{item.code}</b>
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      {card && <p className="sim-prompt">{card.question}</p>}

      {action === "add_satellite_office" && (
        <>
          <label className="field">
            Entreprise
            <select value={orgKey} onChange={(e) => setOrgKey(e.target.value)}>
              {(catalog?.organizations ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <div className="sim-picks">
            {[0.1, 0.2, 0.3, 0.4].map((rate) => (
              <button
                key={rate}
                type="button"
                className={employeeShare === rate ? "map-btn sim-pick active" : "map-btn sim-pick"}
                onClick={() => setEmployeeShare(rate)}
              >
                {Math.round(rate * 100)} %
              </button>
            ))}
          </div>
          {org && (
            <p className="kpi-muted">
              Si {Math.round(employeeShare * 100)} % des employés de {org.name} (
              {fmt(Math.round(org.employee_count * employeeShare), 0)} personnes sur{" "}
              {fmt(org.employee_count, 0)}) travaillent dans un bureau satellite plus proche de leur
              domicile, au pôle {org.work_zone_name}.
            </p>
          )}
        </>
      )}

      {action === "telework" && (
        <>
          <div className="sim-picks">
            {[0.1, 0.2, 0.3, 0.4].map((rate) => (
              <button
                key={rate}
                type="button"
                className={teleworkRate === rate ? "map-btn sim-pick active" : "map-btn sim-pick"}
                onClick={() => setTeleworkRate(rate)}
              >
                {Math.round(rate * 100)} %
              </button>
            ))}
          </div>
          <label className="field">
            Rythme
            <select value={pattern} onChange={(e) => setPattern(e.target.value)}>
              <option value="hybrid_1_2">Hybride, 1 à 2 jours</option>
              <option value="hybrid_3_4">Hybride, 3 à 4 jours</option>
              <option value="full_remote">Jours entièrement à distance</option>
            </select>
          </label>
        </>
      )}

      {(action === "add_tc_stop" || action === "add_park_ride" || action === "add_bike_lane") && (
        <>
          <label className="field">
            Zone concernée
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value ? Number(e.target.value) : "")}
            >
              {(catalog?.zones ?? []).map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Ampleur {Math.round(intensity * 100)} %
            <input
              type="range"
              min={0.1}
              max={1}
              step={0.05}
              value={intensity}
              onChange={(e) => setIntensity(Number(e.target.value))}
            />
          </label>
        </>
      )}

      {(action === "zoning_housing" || action === "zoning_jobs") && (
        <>
          <p className="kpi-muted">
            Cas collectivité : estimez d&apos;abord les logements, puis les emplois, et gardez les deux
            hypothèses pour les comparer.
          </p>
          <label className="field">
            Ampleur {Math.round(intensity * 100)} %
            <input
              type="range"
              min={0.1}
              max={1}
              step={0.05}
              value={intensity}
              onChange={(e) => setIntensity(Number(e.target.value))}
            />
          </label>
        </>
      )}

      {action === "shift_schedules" && (
        <div className="sim-picks">
          {[0.1, 0.2, 0.3, 0.4].map((rate) => (
            <button
              key={rate}
              type="button"
              className={stagger === rate ? "map-btn sim-pick active" : "map-btn sim-pick"}
              onClick={() => setStagger(rate)}
            >
              {Math.round(rate * 100)} % décalés
            </button>
          ))}
        </div>
      )}

      {action === "relocate_jobs" && (
        <>
          <label className="field">
            Site actuel
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value ? Number(e.target.value) : "")}
            >
              {(catalog?.zones ?? []).map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Nouveau quartier
            <select
              value={targetZoneId}
              onChange={(e) => setTargetZoneId(e.target.value ? Number(e.target.value) : "")}
            >
              {(catalog?.zones ?? [])
                .filter((zone) => zone.id !== zoneId)
                .map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="field">
            Part déplacée {Math.round(intensity * 100)} %
            <input
              type="range"
              min={0.1}
              max={0.8}
              step={0.05}
              value={intensity}
              onChange={(e) => setIntensity(Number(e.target.value))}
            />
          </label>
        </>
      )}

      <button type="button" className="search-card-btn" onClick={() => void run()} disabled={busy || !catalog}>
        {busy ? "Calcul…" : "Estimer l'impact"}
      </button>
      {error && <p className="kpi-error">{error}</p>}

      {result && (
        <>
          <p className="sim-question">{result.question}</p>
          <section className="kpi-section">
            <h3>Avant / après</h3>
            <table className="compare-table">
              <thead>
                <tr>
                  <th>Indicateur</th>
                  <th>Avant</th>
                  <th>Après</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {indicators.map((row) => {
                  const good = row.higher_is_better ? row.delta > 0 : row.delta < 0;
                  const bad = row.higher_is_better ? row.delta < 0 : row.delta > 0;
                  const digits =
                    row.key === "emploi_habitat"
                      ? 3
                      : row.key === "co2_t"
                        ? 2
                        : row.key === "avg_time_min" || row.key === "corridor_pressure"
                          ? 1
                          : 0;
                  return (
                    <tr key={row.key}>
                      <td>
                        {row.label}
                        <span className="sim-unit">{row.unit}</span>
                      </td>
                      <td>{fmt(row.before, digits)}</td>
                      <td>{fmt(row.after, digits)}</td>
                      <td className={good ? "delta-good" : bad ? "delta-bad" : ""}>
                        {row.delta > 0 ? "+" : ""}
                        {fmt(row.delta, digits)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>

          <section className="sim-effects">
            <p>
              <span className="sim-dot sim-dot-good" />
              {result.zone_effects.improved} zone{result.zone_effects.improved > 1 ? "s" : ""} améliorée
              {result.zone_effects.improved > 1 ? "s" : ""}
              {result.zone_effects.improved_names.length > 0 &&
                ` — ${result.zone_effects.improved_names.join(", ")}`}
            </p>
            <p>
              <span className="sim-dot sim-dot-bad" />
              {result.zone_effects.worsened} zone{result.zone_effects.worsened > 1 ? "s" : ""} potentiellement
              aggravée{result.zone_effects.worsened > 1 ? "s" : ""}
              {result.zone_effects.worsened === 0
                ? " — aucune dans cette hypothèse"
                : ` — ${result.zone_effects.worsened_names.join(", ")}`}
            </p>
          </section>

          {result.company && (
            <p className="kpi-muted">
              {fmt(result.company.relocated, 0)} salariés estimés au satellite
              {result.company.satellite_name ? ` (${result.company.satellite_name})` : ""}, sur{" "}
              {fmt(result.company.concerned, 0)} concernés. Site actuel : {result.company.work_zone_name}.
            </p>
          )}

          <button type="button" className="map-btn" onClick={pin}>
            Garder pour comparer
          </button>
          <button type="button" className="map-btn" onClick={() => void runSweep()} disabled={sweepBusy}>
            {sweepBusy ? "Test des taux…" : "Tester plusieurs taux"}
          </button>
          {sweep && (
            <section className="kpi-section">
              <h3>Robustesse</h3>
              <p className="kpi-muted">
                Le même scénario à plusieurs taux. Variation systématique, pas un tirage Monte Carlo.
              </p>
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Taux</th>
                    <th>Δ temps</th>
                    <th>Δ CO₂</th>
                  </tr>
                </thead>
                <tbody>
                  {sweep.map((row) => (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td>{fmt(row.time, 1)}</td>
                      <td>{fmt(row.co2, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="kpi-note">
            <strong>Hypothèses utilisées</strong>
            {result.assumptions.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </section>

          <div className="export-row">
            <button
              type="button"
              className="map-btn"
              onClick={() => downloadJson("simulation-whatif.json", result)}
            >
              Données
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                printHtmlReport(
                  `Simulation — ${result.action_label}`,
                  `<p><strong>SIMULATION</strong> — pas une prédiction.</p>
                   <p>${result.question}</p>
                   <table><tr><th>Indicateur</th><th>Avant</th><th>Après</th><th>Delta</th></tr>
                   ${indicators
                     .map(
                       (row) =>
                         `<tr><td>${row.label}</td><td>${row.before}</td><td>${row.after}</td><td>${row.delta}</td></tr>`
                     )
                     .join("")}
                   </table>
                   <h2>Hypothèses</h2>
                   ${result.assumptions.map((line) => `<p>${line}</p>`).join("")}`
                )
              }
            >
              PDF
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                downloadSlidesHtml("simulation-comite.html", "Comparaison de scénarios", [
                  `<h1>${result.action_label}</h1><p>${result.question}</p><p>${result.disclaimer}</p>`,
                  `<h1>Avant / après</h1><ul>${indicators
                    .map((row) => `<li>${row.label} : ${row.before} → ${row.after} (${row.delta})</li>`)
                    .join("")}</ul>`,
                  `<h1>Limites</h1><ul>${result.assumptions.map((line) => `<li>${line}</li>`).join("")}</ul>`,
                ])
              }
            >
              Présentation
            </button>
          </div>
        </>
      )}

      {pinned.length > 0 && (
        <section className="kpi-section">
          <h3>Scénarios gardés</h3>
          <div className="sim-picks">
            {pinned.map((item) => (
              <button
                key={item.id}
                type="button"
                className="map-btn sim-pick"
                onClick={() => {
                  setResult(item.payload);
                  onScenario(item.payload);
                }}
              >
                {item.label}
              </button>
            ))}
            <button type="button" className="map-btn" onClick={() => setPinned([])}>
              Vider
            </button>
          </div>
          {pinned.length >= 2 && (
            <table className="compare-table">
              <thead>
                <tr>
                  <th>Indicateur</th>
                  {pinned.map((item) => (
                    <th key={item.id}>{item.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {INDICATOR_ORDER.map((key) => (
                  <tr key={key}>
                    <td>{pinned[0].payload.indicators[key]?.label}</td>
                    {pinned.map((item) => {
                      const row = item.payload.indicators[key];
                      if (!row) return <td key={item.id}>—</td>;
                      const good = row.higher_is_better ? row.delta > 0 : row.delta < 0;
                      const bad = row.higher_is_better ? row.delta < 0 : row.delta > 0;
                      return (
                        <td key={item.id} className={good ? "delta-good" : bad ? "delta-bad" : ""}>
                          {row.delta > 0 ? "+" : ""}
                          {fmt(row.delta, row.key === "emploi_habitat" ? 3 : row.key === "co2_t" ? 2 : 1)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="kpi-muted">Chaque colonne est un écart à la situation actuelle. Cliquer un scénario le réaffiche sur la carte.</p>
        </section>
      )}
    </aside>
  );
}
