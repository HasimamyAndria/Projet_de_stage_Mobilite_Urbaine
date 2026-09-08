import { useEffect, useState } from "react";
import api from "../services/api";
import { downloadJson, printHtmlReport } from "../utils/exportReport";

type Reco = {
  id: number;
  type: string;
  label_fr: string;
  title: string;
  zone_name: string;
  trigger: string;
  impact_indicator: string;
  impact_value: number;
  impact_unit: string;
  impact_score: number;
};

type Payload = {
  items: Reco[];
  note: string;
  catalog: Array<{ type: string; label_fr: string; trigger: string; impact_indicator: string }>;
};

export default function RecoPanel() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/recommendations")
      .then((res) => setData(res.data))
      .catch(() => setError("Impossible de charger les recommandations."));
  }, []);

  if (error || !data) {
    return (
      <aside className="kpi-panel">
        <h2>Recommandations</h2>
        <p className={error ? "kpi-error" : "kpi-muted"}>
          {error ?? "Chargement…"}
        </p>
      </aside>
    );
  }

  return (
    <aside className="kpi-panel">
      <h2>Recommandations d&apos;urbanisation</h2>
      <p className="kpi-subtitle">Typées + score d&apos;impact · M3</p>
      <ol className="kpi-top-list">
        {data.items.slice(0, 12).map((r) => (
          <li key={r.id}>
            <div className="kpi-top-main">
              <strong>{r.title}</strong>
              <span className="kpi-badge">{r.impact_score}</span>
            </div>
            <div className="kpi-top-meta">
              <span>{r.label_fr}</span>
              <span>
                {r.impact_value} {r.impact_unit}
              </span>
            </div>
            <p className="kpi-muted">{r.trigger}</p>
          </li>
        ))}
      </ol>
      <div className="export-row">
        <button
          type="button"
          className="map-btn"
          onClick={() => downloadJson("recommandations.json", data)}
        >
          JSON
        </button>
        <button
          type="button"
          className="map-btn"
          onClick={() =>
            printHtmlReport(
              "Recommandations urbanisation",
              `<table><tr><th>Type</th><th>Site</th><th>Score</th><th>Impact</th></tr>${data.items
                .map(
                  (r) =>
                    `<tr><td>${r.label_fr}</td><td>${r.title}</td><td>${r.impact_score}</td><td>${r.impact_value} ${r.impact_unit}</td></tr>`
                )
                .join("")}</table>`
            )
          }
        >
          PDF
        </button>
      </div>
      <section className="kpi-note">
        <strong>Limites</strong>
        <p>{data.note}</p>
      </section>
    </aside>
  );
}
