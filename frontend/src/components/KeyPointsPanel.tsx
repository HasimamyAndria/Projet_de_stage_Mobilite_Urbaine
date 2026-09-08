import { useEffect, useState } from "react";
import api from "../services/api";

type Counts = Record<string, number>;

type Payload = {
  counts: Counts;
  rules: Record<string, string | number>;
  note: string;
};

export default function KeyPointsPanel() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/keypoints", { params: { corridor_top_n: 5 } })
      .then((res) => setData(res.data))
      .catch(() => setError("Impossible de charger les points clés."));
  }, []);

  if (error || !data) {
    return (
      <aside className="kpi-panel">
        <h2>Points clés</h2>
        <p className={error ? "kpi-error" : "kpi-muted"}>
          {error ?? "Chargement…"}
        </p>
      </aside>
    );
  }

  const cards = [
    ["convergence", "Nœuds de convergence", "Pôles d'échanges potentiels"],
    ["corridors", "Corridors saturés", "Renfort TC / cyclable"],
    ["deserts", "Déserts de mobilité", "Demande forte, desserte faible"],
    ["carpool", "Mutualisation", "Flux parallèles covoiturage"],
    ["dormitory", "Zones dortoirs", "Habitat >> emplois"],
    ["employment", "Pôles emploi", "Emplois >> habitat"],
  ] as const;

  return (
    <aside className="kpi-panel">
      <h2>Détection des points clés</h2>
      <p className="kpi-subtitle">Heuristiques documentées · M2</p>
      <div className="kpi-grid">
        {cards.map(([key, label, hint]) => (
          <div key={key} className="kpi-card">
            <span className="kpi-label">{label}</span>
            <span className="kpi-value">{data.counts[key] ?? 0}</span>
            <span className="kpi-muted">{hint}</span>
          </div>
        ))}
      </div>
      <section className="kpi-section">
        <h3>Règles</h3>
        <ul className="kpi-legend">
          {Object.entries(data.rules)
            .filter(([, v]) => typeof v === "string")
            .map(([k, v]) => (
              <li key={k}>
                <strong>{k}</strong> — {String(v)}
              </li>
            ))}
        </ul>
      </section>
      <section className="kpi-note">
        <strong>Limites</strong>
        <p>{data.note}</p>
      </section>
    </aside>
  );
}
