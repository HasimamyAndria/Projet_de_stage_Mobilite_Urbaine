import { useEffect, useState } from "react";
import api from "../services/api";

type Place = { name: string; kind: string };

type Benefits = {
  km_avoided?: number | null;
  fuel_l_saved?: number | null;
  co2_t_avoided?: number | null;
  time_h_saved?: number | null;
  traffic_reduction_pct?: number | null;
  pollution_reduction_pct?: number | null;
  hours_saved_per_employee?: number | null;
  dynamism_index?: number | null;
  narrative?: string;
};

type Site = {
  name: string;
  lon: number;
  lat: number;
  distance_home_km: number;
  distance_work_km: number;
};

type Solution = {
  action: string;
  label: string;
  site: Site | null;
  rationale: string;
  remote_share: number;
  benefits: Benefits;
};

type Payload = {
  input: {
    home: { name: string; lon: number; lat: number };
    work: { name: string; lon: number; lat: number };
    work_label: string;
    employees: number;
    distance_km_road: number;
    distance_km_straight: number;
    band: string;
  };
  hypotheses: { note: string };
  algorithm: { primary: Solution; alternatives: Solution[] };
  deepseek: {
    available: boolean;
    skipped: boolean;
    error: string | null;
    model: string | null;
    label?: string;
    primary_action: string | null;
    site_name: string | null;
    rationale: string | null;
    benefits: Benefits | null;
  };
  comparison: {
    same_action: boolean;
    same_site: boolean;
    reading: string;
    deltas_algorithm_minus_deepseek: Record<string, number | null>;
  } | null;
};

const BANDS: Record<string, string> = {
  lt_2: "moins de 2 km",
  ring_2_5: "déjà dans les 2 à 5 km",
  mid_5_20: "entre 5 et 20 km",
  remote_20_30: "entre 20 et 30 km",
  remote_30_plus: "plus de 30 km",
};

const ROWS: Array<{ key: keyof Benefits; label: string; digits: number; unit: string }> = [
  { key: "traffic_reduction_pct", label: "Trafic vers le centre", digits: 0, unit: " %" },
  { key: "pollution_reduction_pct", label: "Pollution (CO₂)", digits: 0, unit: " %" },
  { key: "co2_t_avoided", label: "CO₂ évité", digits: 1, unit: " t" },
  { key: "fuel_l_saved", label: "Carburant", digits: 0, unit: " L" },
  { key: "km_avoided", label: "Kilomètres", digits: 0, unit: " km" },
  { key: "time_h_saved", label: "Temps de trajet", digits: 0, unit: " h" },
  { key: "dynamism_index", label: "Dynamisme", digits: 0, unit: "/100" },
];

function pct(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return `−${fmt(value, 0)} %`;
}

function fmt(value: number | null | undefined, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export default function DecisionPanel({
  onFocus,
}: {
  onFocus?: (lon: number, lat: number) => void;
}) {
  const [places, setPlaces] = useState<Place[]>([]);
  const [home, setHome] = useState("Talatamaty");
  const [work, setWork] = useState("Anosy");
  const [workLabel, setWorkLabel] = useState("Domaine Finance");
  const [employees, setEmployees] = useState(80);
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(includeDeepseek: boolean) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post(
        "/api/decision/compare",
        {
          home_name: home,
          work_name: work,
          employees: Number(employees) || 1,
          work_label: workLabel,
          include_deepseek: includeDeepseek,
        },
        { timeout: 60000 }
      );
      setData(res.data);
      const site = res.data?.algorithm?.primary?.site;
      const focus = site ?? res.data?.input?.home;
      if (focus && onFocus) onFocus(focus.lon, focus.lat);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Aide à la décision indisponible (backend).");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    api
      .get("/api/decision/places")
      .then((res) => {
        const list = (res.data.places ?? []) as Place[];
        setPlaces(list);
      })
      .catch(() => setError("Liste des lieux indisponible."));
  }, []);

  useEffect(() => {
    if (!places.length) return;
    run(false);
    // Premier affichage : algorithme seul, sans appel DeepSeek.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [places]);

  const algo = data?.algorithm.primary;
  const ds = data?.deepseek;

  return (
    <aside className="kpi-panel">
      <h2>Aide à la décision</h2>
      <p className="kpi-subtitle">Algorithme interne et second avis DeepSeek</p>

      <div className="decision-presets">
        <button
          type="button"
          className="map-btn"
          onClick={() => {
            setHome("Talatamaty");
            setWork("Anosy");
            setWorkLabel("Domaine Finance");
          }}
        >
          Talatamaty → Anosy
        </button>
        <button
          type="button"
          className="map-btn"
          onClick={() => {
            setHome("Ambohimanga");
            setWork("Anosy");
            setWorkLabel("Domaine Finance");
          }}
        >
          Cas 20–30 km
        </button>
      </div>

      <label className="field">
        Domicile des salariés
        <select value={home} onChange={(e) => setHome(e.target.value)}>
          {places.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Lieu de travail
        <select value={work} onChange={(e) => setWork(e.target.value)}>
          {places.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Activité
        <input
          type="text"
          value={workLabel}
          maxLength={120}
          onChange={(e) => setWorkLabel(e.target.value)}
        />
      </label>
      <label className="field">
        Effectif
        <input
          type="number"
          min={1}
          max={5000}
          value={employees}
          onChange={(e) => setEmployees(Number(e.target.value))}
        />
      </label>

      <button
        type="button"
        className="search-card-btn"
        disabled={busy || home === work}
        onClick={() => run(true)}
      >
        {busy ? "Calcul…" : "Comparer algorithme et DeepSeek"}
      </button>
      {home === work && (
        <p className="kpi-muted">Choisissez un domicile différent du lieu de travail.</p>
      )}
      {error && <p className="kpi-error">{error}</p>}

      {data && algo && (
        <>
          <p className="kpi-muted">
            {data.input.employees} salariés · {data.input.work_label} à {data.input.work.name} ·
            domicile {data.input.home.name} · {fmt(data.input.distance_km_road, 1)} km de route (
            {BANDS[data.input.band] ?? data.input.band})
          </p>

          <article className="decision-card">
            <h3>Algorithme</h3>
            <p className="decision-action">{algo.label}</p>
            {algo.site && (
              <p className="kpi-muted">
                Site : {algo.site.name} · {fmt(algo.site.distance_home_km, 1)} km du domicile
              </p>
            )}
            <p>{algo.rationale}</p>
            <BenefitGrid benefits={algo.benefits} />
            {algo.site && onFocus && (
              <button
                type="button"
                className="map-btn"
                onClick={() => onFocus(algo.site!.lon, algo.site!.lat)}
              >
                Voir {algo.site.name} sur la carte
              </button>
            )}
          </article>

          {data.algorithm.alternatives.length > 0 && (
            <section className="kpi-section">
              <h3>Autres leviers</h3>
              <ul className="decision-alts">
                {data.algorithm.alternatives.map((alt) => (
                  <li key={`${alt.action}-${alt.site?.name ?? "site"}`}>
                    <strong>{alt.label}</strong>
                    {alt.site ? ` — ${alt.site.name}` : ""}
                    <span className="kpi-muted">
                      {" "}
                      · trafic {fmt(alt.benefits.traffic_reduction_pct, 0)} % · CO₂{" "}
                      {fmt(alt.benefits.co2_t_avoided, 1)} t · carburant{" "}
                      {fmt(alt.benefits.fuel_l_saved, 0)} L
                    </span>
                    <p className="kpi-muted">{alt.rationale}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <article className="decision-card">
            <h3>DeepSeek{ds?.model ? ` · ${ds.model}` : ""}</h3>
            {ds?.skipped && (
              <p className="kpi-muted">
                Pas encore appelé. Le bouton ci-dessus envoie la même situation, sans le résultat
                de l&apos;algorithme.
              </p>
            )}
            {ds?.error && <p className="kpi-error">{ds.error}</p>}
            {ds?.available && (
              <>
                <p className="decision-action">{ds.label || ds.primary_action}</p>
                {ds.site_name && <p className="kpi-muted">Site : {ds.site_name}</p>}
                <p>{ds.rationale}</p>
                {ds.benefits && <BenefitGrid benefits={ds.benefits} />}
              </>
            )}
          </article>

          {data.comparison && (
            <section className="kpi-section">
              <h3>Comparaison</h3>
              <p className={data.comparison.same_action ? "delta-good" : "delta-bad"}>
                {data.comparison.same_action ? "Même action" : "Action différente"}
                {data.comparison.same_site ? " · même site" : " · site différent"}
              </p>
              <p>{data.comparison.reading}</p>
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Indicateur</th>
                    <th>Algo</th>
                    <th>DeepSeek</th>
                    <th>Écart</th>
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((row) => (
                    <tr key={row.key}>
                      <td>{row.label}</td>
                      <td>
                        {fmt(algo.benefits[row.key] as number | null, row.digits)}
                        {row.unit}
                      </td>
                      <td>
                        {fmt(ds?.benefits?.[row.key] as number | null, row.digits)}
                        {row.unit}
                      </td>
                      <td>
                        {fmt(data.comparison?.deltas_algorithm_minus_deepseek[row.key], row.digits)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="kpi-muted">Écart = algorithme − DeepSeek. Référence auditable : l&apos;algorithme.</p>
            </section>
          )}

          <section className="kpi-note">
            <strong>Hypothèses</strong>
            <p>{data.hypotheses.note}</p>
          </section>
        </>
      )}
    </aside>
  );
}

function BenefitGrid({ benefits }: { benefits: Benefits }) {
  return (
    <div className="decision-kpis">
      <div>
        <span>Trafic en ville</span>
        <strong>{pct(benefits.traffic_reduction_pct)}</strong>
      </div>
      <div>
        <span>Pollution</span>
        <strong>{pct(benefits.pollution_reduction_pct)}</strong>
      </div>
      <div>
        <span>Carburant</span>
        <strong>{fmt(benefits.fuel_l_saved, 0)} L</strong>
      </div>
      <div>
        <span>CO₂</span>
        <strong>{fmt(benefits.co2_t_avoided, 1)} t</strong>
      </div>
      <div>
        <span>Déplacements</span>
        <strong>{fmt(benefits.km_avoided, 0)} km</strong>
      </div>
      <div>
        <span>Dynamisme</span>
        <strong>{fmt(benefits.dynamism_index, 0)}/100</strong>
      </div>
    </div>
  );
}
