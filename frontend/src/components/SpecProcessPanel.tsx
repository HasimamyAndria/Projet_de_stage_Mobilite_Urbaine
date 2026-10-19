import { useEffect, useRef, useState } from "react";
import api from "../services/api";
import type { AnnexesGeoJSON } from "./Map/SatellitesLayer";

type CaseCard = {
  id: string;
  pdf: string;
  title: string;
  actor: string;
  question: string;
};

type Criterion = {
  id: string;
  label: string;
  weight: number;
  score: number;
  value: number;
  unit: string;
};

type Candidate = {
  id: string;
  name: string;
  rank: number;
  impact_score: number;
  parent?: string;
  people: number;
  selected: boolean;
  criteria: Criterion[];
};

type Scenario = {
  id: string;
  label: string;
  detail?: string;
  people: number;
  basins: number;
  employers: number;
  minutes_per_person: number;
  km_saved_per_day: number;
  co2_t_year: number;
  co2_t_horizon: number;
  trips_captured: number;
  peak_reduction_pct: number;
  hours_year: number;
  avg_minutes_now: number;
  avg_minutes_after: number;
};

type Step = { id: number; title: string; lines: string[] };

type Payload = {
  case: CaseCard;
  parameters: { adoption: number; telework: number; horizon_years: number };
  steps: Step[];
  candidates: Candidate[];
  scenarios: Scenario[];
  dominant_id: string;
  focus: { lon: number; lat: number; name?: string };
  geojson: AnnexesGeoJSON;
  note: string;
};

type Props = {
  onResult: (payload: Payload) => void;
};

export default function SpecProcessPanel({ onResult }: Props) {
  const [cases, setCases] = useState<CaseCard[]>([]);
  const [caseId, setCaseId] = useState("entreprise");
  const [adoption, setAdoption] = useState(60);
  const [telework, setTelework] = useState(0);
  const [horizon, setHorizon] = useState(1);
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openStep, setOpenStep] = useState(1);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    api
      .get("/api/spec/cases")
      .then((res) => setCases(res.data.cases ?? []))
      .catch(() => setError("Impossible de charger les cas."));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setError(null);
      api
        .get(`/api/spec/cases/${caseId}`, {
          params: { adoption: adoption / 100, telework: telework / 100, horizon },
        })
        .then((res) => {
          setData(res.data);
          onResultRef.current(res.data);
        })
        .catch(() => setError("Le calcul des sites n'a pas abouti."));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [caseId, adoption, telework, horizon]);

  return (
    <aside className="kpi-panel spec-process">
      <h2>Optimisation des sites</h2>
      <p className="kpi-subtitle">Cinq étapes du PDF · chapitre 6 · Antananarivo simulé</p>

      <div className="spec-cases">
        {(cases.length ? cases : [{ id: caseId, pdf: "", title: "Chargement", actor: "", question: "" }]).map(
          (item) => (
            <button
              key={item.id}
              type="button"
              className={item.id === caseId ? "spec-case is-on" : "spec-case"}
              onClick={() => {
                setCaseId(item.id);
                setOpenStep(1);
              }}
            >
              <span>{item.pdf ? `Cas ${item.pdf}` : item.id}</span>
              <strong>{item.title}</strong>
            </button>
          )
        )}
      </div>

      {data && (
        <p className="kpi-muted">
          {data.case.actor} · {data.case.question}
        </p>
      )}

      <div className="spec-controls">
        <label>
          Adoption {adoption} %
          <input
            type="range"
            min={20}
            max={100}
            step={10}
            value={adoption}
            onChange={(event) => setAdoption(Number(event.target.value))}
          />
        </label>
        <label>
          Télétravail {telework} %
          <input
            type="range"
            min={0}
            max={80}
            step={10}
            value={telework}
            onChange={(event) => setTelework(Number(event.target.value))}
          />
        </label>
        <label>
          Horizon
          <select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>
            {[1, 3, 5, 10].map((year) => (
              <option key={year} value={year}>
                {year} an{year > 1 ? "s" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="kpi-error">{error}</p>}
      {!data && !error && <p className="kpi-muted">Calcul en cours…</p>}

      {data && (
        <>
          <ol className="spec-steps">
            {data.steps.map((step) => (
              <li key={step.id}>
                <button type="button" className="spec-step-btn" onClick={() => setOpenStep(step.id)}>
                  <span>{step.id}</span>
                  {step.title}
                </button>
                {openStep === step.id && (
                  <ul>
                    {step.lines.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>

          <h3>Classement</h3>
          <ol className="kpi-top-list">
            {data.candidates.map((site) => (
              <li key={site.id}>
                <div className="kpi-top-main">
                  <strong>
                    {site.rank}. {site.name}
                  </strong>
                  <span className="kpi-badge">{site.impact_score}</span>
                </div>
                <div className="kpi-top-meta">
                  <span>{site.parent}</span>
                  <span>{site.selected ? "Retenu" : "Candidat"}</span>
                </div>
                {site.rank === 1 && (
                  <ul className="spec-criteria">
                    {site.criteria.map((item) => (
                      <li key={item.id}>
                        {Math.round(item.weight * 100)} % {item.label} · {item.value} {item.unit}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>

          <h3>Comparaison à la référence</h3>
          <ul className="spec-scenarios">
            {data.scenarios.map((item) => (
              <li key={item.id} className={item.id === data.dominant_id ? "is-dominant" : undefined}>
                <strong>{item.label}</strong>
                {item.id === data.dominant_id && <span> · dominant</span>}
                <p>
                  {item.people} salariés · {item.minutes_per_person} min/j · {item.km_saved_per_day} km/j ·{" "}
                  {item.co2_t_year} t CO₂/an
                  {data.parameters.horizon_years > 1 ? ` · ${item.co2_t_horizon} t sur ${data.parameters.horizon_years} ans` : ""}
                </p>
                <p>
                  {item.trips_captured} trajets captés · {item.basins} bassins · {item.peak_reduction_pct} % de
                  pointe en moins · {item.hours_year.toLocaleString("fr-FR")} h/an cumulées
                </p>
                {item.detail && <p>{item.detail}</p>}
              </li>
            ))}
          </ul>
          <p className="kpi-muted">{data.note}</p>
        </>
      )}
    </aside>
  );
}
