import { useEffect, useState } from "react";
import api from "../services/api";
import "./LensPanel.css";

type Indicator = {
  id: string;
  name: string;
  value: number | null;
  unit: string;
  definition: string;
  formula: string;
  source: string;
  method: string;
  interpretation: string;
  limit: string;
};

type IndicatorPayload = {
  context: {
    city: string;
    scope: string;
    level: string;
    mode: string;
    period: string;
    purpose: string;
  };
  indicators: Indicator[];
  note: string;
};

export function IndicatorList({
  city,
  zone,
  mode,
}: {
  city: string;
  zone: string;
  mode: string;
}) {
  const [data, setData] = useState<IndicatorPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api
      .get("/api/mobility/indicators", {
        params: { city, zone, mode },
        signal: controller.signal,
      })
      .then((response) => {
        setData(response.data as IndicatorPayload);
        setError(null);
      })
      .catch((err: { code?: string }) => {
        if (err.code === "ERR_CANCELED") return;
        setError("Indices indisponibles.");
      });
    return () => controller.abort();
  }, [city, zone, mode]);

  if (error) return <p className="lens-error">{error}</p>;
  if (!data) return <p className="lens-muted">Calcul des indices…</p>;

  return (
    <div>
      <p className="lens-muted">
        Ville : {data.context.city}. Cadre : {data.context.scope}. Niveau : {data.context.level}.
        Mode : {data.context.mode}. Période : {data.context.period}. Motif : {data.context.purpose}.
      </p>
      <ul className="lens-why">
        {data.indicators.map((item) => (
          <li key={item.id}>
            <strong>
              {item.name}{" "}
              <em>
                {item.value ?? "—"} {item.unit}
              </em>
            </strong>
            <p>{item.interpretation}</p>
            <details>
              <summary>Définition, formule, limite</summary>
              <p>{item.definition}</p>
              <p>Formule : {item.formula}</p>
              <p>Source : {item.source}</p>
              <p>Méthode : {item.method}</p>
              <p>Limite : {item.limit}</p>
            </details>
          </li>
        ))}
      </ul>
      <p className="lens-foot">{data.note}</p>
    </div>
  );
}

type ClusterCard = {
  id: number;
  label: string;
  size: number;
  mean_km: number;
  mean_min: number;
  sector: string;
  homes: Array<{ id: string; name: string; headcount: number }>;
  works: Array<{ id: string; name: string; headcount: number }>;
};

export function ClustersPanel({
  city,
  onSelectZone,
}: {
  city: string;
  onSelectZone: (id: string) => void;
}) {
  const [data, setData] = useState<{
    justification: string;
    k: number;
    silhouette: number | null;
    clusters: ClusterCard[];
    limit: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/mobility/clusters", { params: { city } })
      .then((response) => setData(response.data))
      .catch(() => setError("Profils indisponibles."));
  }, [city]);

  return (
    <section className="lens-panel">
      <p className="lens-kicker">{city}</p>
      <h2>Profils de mobilité</h2>
      {error && <p className="lens-error">{error}</p>}
      {!data && !error && <p className="lens-muted">Classement des navettes…</p>}
      {data && (
        <>
          <p className="lens-lead">{data.justification}</p>
          <p className="lens-muted">
            k = {data.k}. Silhouette = {data.silhouette ?? "—"}. Estimation simulée.
          </p>
          <ul className="lens-why">
            {data.clusters.map((cluster) => (
              <li key={cluster.id}>
                <strong>
                  {cluster.label} · {cluster.size} personnes
                </strong>
                <p>
                  {cluster.mean_km} km · {cluster.mean_min} min · {cluster.sector}
                </p>
                <p>
                  {cluster.homes.map((home) => (
                    <button
                      key={home.id}
                      type="button"
                      className="text origin"
                      onClick={() => onSelectZone(home.id)}
                    >
                      {home.name} ({home.headcount})
                    </button>
                  ))}
                </p>
              </li>
            ))}
          </ul>
          <p className="lens-foot">{data.limit}</p>
        </>
      )}
    </section>
  );
}

type Company = {
  id: string;
  name: string;
  kind_label: string;
  seat_name: string;
  employees: number;
};

type Mobility = {
  company: Company & { activity: string; arrondissement: string };
  mean_km: number | null;
  corridor: string;
  homes: Array<{
    id: string;
    name: string;
    arrondissement: string;
    headcount: number;
    distance_km: number;
    share: number;
    mode: string;
  }>;
  note: string;
};

type ScenarioResult = {
  estimation_label: string;
  scenario: { label: string; justification: string };
  baseline: {
    trips_per_working_day: number;
    km_per_working_day: number;
    hours_per_working_day: number;
    mean_km: number;
  };
  scenario_result: {
    trips_per_working_day: number;
    km_per_working_day: number;
    hours_per_working_day: number;
    mean_km: number;
  };
  impact: {
    employees_concerned: number;
    trips_avoided_per_working_day: number;
    km_reduction_pct: number;
    time_reduction_pct: number;
    vehicle_trips_avoided: number | null;
    zones_relieved: Array<{ name: string; employees: number }>;
    zones_loaded: Array<{ name: string; employees: number }>;
  };
  limits: string[];
};

const SCENARIO_BUTTONS = [
  ["annex", "Site secondaire"],
  ["decentralize", "Site décentralisé"],
  ["telework", "Télétravail"],
  ["collective", "Transport groupé"],
  ["hours", "Horaires"],
] as const;

export function CompaniesPanel({
  city,
  onSelectZone,
}: {
  city: string;
  onSelectZone: (id: string) => void;
}) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [mobility, setMobility] = useState<Mobility | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/companies", { params: { city } })
      .then((response) => {
        const rows = response.data.companies as Company[];
        setCompanies(rows);
        setCompanyId(rows[0]?.id ?? "");
      })
      .catch(() => setError("Organisations indisponibles."));
  }, [city]);

  useEffect(() => {
    if (!companyId) return;
    setResult(null);
    api
      .get(`/api/companies/${companyId}/mobility`)
      .then((response) => setMobility(response.data as Mobility))
      .catch(() => setError("Lecture de l'organisation impossible."));
  }, [companyId]);

  const run = (scenario: string) => {
    setBusy(true);
    api
      .post("/api/simulation", { organization_id: companyId, scenario })
      .then((response) => {
        setResult(response.data as ScenarioResult);
        setError(null);
      })
      .catch(() => setError("Scénario impossible."))
      .finally(() => setBusy(false));
  };

  return (
    <section className="lens-panel">
      <p className="lens-kicker">{city}</p>
      <h2>Organisations</h2>
      <p className="lens-lead">
        Employés simulés par quartier de résidence. Le scénario chiffre un changement, il ne l'applique pas.
      </p>
      {error && <p className="lens-error">{error}</p>}
      <label className="lens-muted">
        Organisation
        <select value={companyId} onChange={(event) => setCompanyId(event.target.value)}>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name} · {company.employees}
            </option>
          ))}
        </select>
      </label>
      {mobility && (
        <>
          <p>
            Siège : {mobility.company.seat_name} ({mobility.company.arrondissement}). Distance moyenne :{" "}
            {mobility.mean_km ?? "—"} km.
          </p>
          {mobility.corridor && <p className="lens-note">{mobility.corridor}</p>}
          <ul className="lens-bars">
            {mobility.homes.map((home) => (
              <li key={home.id}>
                <div className="lens-bar-label">
                  <button type="button" className="text origin" onClick={() => onSelectZone(home.id)}>
                    {home.name}
                  </button>
                  <em>{home.headcount}</em>
                </div>
                <div className="lens-track">
                  <span style={{ width: `${Math.round(home.share * 100)}%` }} />
                </div>
                <p>
                  {Math.round(home.share * 100)} % · {home.distance_km} km · {home.mode}
                </p>
              </li>
            ))}
          </ul>
          <div className="territory-modes">
            {SCENARIO_BUTTONS.map(([id, label]) => (
              <button key={id} type="button" disabled={busy} onClick={() => run(id)}>
                {label}
              </button>
            ))}
          </div>
        </>
      )}
      {result && (
        <div>
          <h3>{result.scenario.label}</h3>
          <p className="lens-kicker">{result.estimation_label}</p>
          <p>{result.scenario.justification}</p>
          <ul className="lens-purposes">
            <li>
              <span>Déplacements / jour ouvré</span>
              <strong>
                {result.baseline.trips_per_working_day} → {result.scenario_result.trips_per_working_day}
              </strong>
            </li>
            <li>
              <span>Distance km / jour</span>
              <strong>
                {result.baseline.km_per_working_day} → {result.scenario_result.km_per_working_day}
              </strong>
            </li>
            <li>
              <span>Temps heures / jour</span>
              <strong>
                {result.baseline.hours_per_working_day} → {result.scenario_result.hours_per_working_day}
              </strong>
            </li>
          </ul>
          <p>
            Employés concernés : {result.impact.employees_concerned}. Réduction de distance :{" "}
            {result.impact.km_reduction_pct} %. Réduction de temps : {result.impact.time_reduction_pct} %.
            Déplacements évités : {result.impact.trips_avoided_per_working_day} / jour ouvré.
            {result.impact.vehicle_trips_avoided != null &&
              ` Véhicules individuels évités : ${result.impact.vehicle_trips_avoided}.`}
          </p>
          <ul className="lens-foot">
            {result.limits.map((limit) => (
              <li key={limit}>{limit}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function QualityPanel({ city }: { city: string }) {
  const [data, setData] = useState<{
    records: { companies: number; persons: number; trips: number; journal_persons: number };
    completeness: number;
    error_count: number;
    missing_fields: number;
    anomalies: Array<{ level: string; code: string; message: string }>;
    note: string;
  } | null>(null);

  useEffect(() => {
    api.get("/api/mobility/quality", { params: { city } }).then((response) => setData(response.data));
  }, [city]);

  if (!data) {
    return (
      <section className="lens-panel">
        <h2>Qualité des données</h2>
        <p className="lens-muted">Contrôle en cours…</p>
      </section>
    );
  }

  return (
    <section className="lens-panel">
      <p className="lens-kicker">{city}</p>
      <h2>Qualité des données</h2>
      <p className="lens-lead">{data.note}</p>
      <div className="lens-metrics">
        <div>
          <span>Organisations</span>
          <strong>{data.records.companies}</strong>
        </div>
        <div>
          <span>Personnes simulées</span>
          <strong>{data.records.persons}</strong>
        </div>
        <div>
          <span>Trajets groupés</span>
          <strong>{data.records.trips}</strong>
        </div>
        <div>
          <span>Complétude</span>
          <strong>{Math.round(data.completeness * 100)} %</strong>
        </div>
      </div>
      <p className="lens-muted">
        Champs manquants : {data.missing_fields}. Anomalies bloquantes : {data.error_count}. Fiches de journal :{" "}
        {data.records.journal_persons}.
      </p>
      <ul className="lens-why">
        {data.anomalies.map((item, index) => (
          <li key={`${item.code}-${index}`}>
            <strong>
              {item.level} · {item.code}
            </strong>
            <p>{item.message}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
