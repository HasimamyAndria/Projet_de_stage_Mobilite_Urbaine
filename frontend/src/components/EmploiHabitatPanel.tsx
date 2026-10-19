import { useEffect, useState } from "react";
import api from "../services/api";
import DecisionBriefPanel from "./DecisionBriefPanel";
import type { AnnexesGeoJSON } from "./Map/SatellitesLayer";

type Diagnostic = {
  eh_index_100_avg: number | null;
  axes: Record<
    string,
    { north?: number; south?: number; east?: number; west?: number; center?: number; periphery?: number; label: string }
  >;
  dormitories: Array<{ name: string; population: number; jobs: number }>;
  disconnected_jobs: Array<{ name: string; population: number; jobs: number }>;
  sectors: Array<{ sector: string; share: number }>;
  note: string;
};

type SatellitePayload = {
  anchor: { name: string; jobs_proxy: number };
  barycenter: { lon: number; lat: number };
  candidates: Array<{
    rank: number;
    name: string;
    type_label: string;
    impact_score: number;
    km_saved_proxy: number;
    constraints: Record<string, string | number>;
  }>;
  method: string;
  note: string;
};

export default function EmploiHabitatPanel({
  onReloadSatellites,
  onAnnexesGeoJSON,
}: {
  onReloadSatellites?: () => void;
  onAnnexesGeoJSON?: (fc: AnnexesGeoJSON | null) => void;
}) {
  const [diag, setDiag] = useState<Diagnostic | null>(null);
  const [sats, setSats] = useState<SatellitePayload | null>(null);
  const [rate, setRate] = useState(0.2);
  const [pattern, setPattern] = useState("hybrid_1_2");
  const [combine, setCombine] = useState(false);
  const [tele, setTele] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState("");
  const [contribNote, setContribNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<{
    person_count: number;
    couples: Array<{
      id: string;
      title: string;
      left: { name: string; value: number; unit: string };
      right: { name: string; value: number; unit: string };
      indicator: { name: string; value: number; unit: string };
      stats: Array<{ name: string; value: number; unit: string }>;
      reading: string;
    }>;
  } | null>(null);

  useEffect(() => {
    api
      .get("/api/mobility/overview", { params: { city_id: "tana", period: "week" } })
      .then((res) => setOverview(res.data))
      .catch(() => setOverview(null));
  }, []);

  useEffect(() => {
    Promise.all([
      api.get("/api/emploi-habitat/diagnostic"),
      api.get("/api/emploi-habitat/satellites", { params: { k: 5 } }),
    ])
      .then(([d, s]) => {
        setDiag(d.data);
        setSats(s.data);
        onReloadSatellites?.();
      })
      .catch(() => setError("Module emploi-habitat indisponible."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runTelework() {
    const res = await api.get("/api/emploi-habitat/telework", {
      params: { rate, pattern, combine_satellite: combine },
    });
    setTele(res.data);
  }

  async function sendContribution() {
    if (!message.trim()) return;
    await api.post("/api/contributions", {
      kind: "suggestion",
      message,
    });
    setMessage("");
    setContribNote("Signalement enregistré (démo, mémoire serveur).");
  }

  if (error) {
    return (
      <aside className="kpi-panel">
        <h2>Emploi-habitat</h2>
        <p className="kpi-error">{error}</p>
        <DecisionBriefPanel onAnnexesGeoJSON={onAnnexesGeoJSON} />
      </aside>
    );
  }

  const axes = diag?.axes ?? {};

  return (
    <aside className="kpi-panel">
      <h2>Rapprochement emploi-habitat</h2>
      <p className="kpi-subtitle">Indice 0-100 · bureaux annexes · dossier décideur · M6</p>

      <DecisionBriefPanel onAnnexesGeoJSON={onAnnexesGeoJSON} />

      <section className="kpi-section">
        <h3>Indice de proximité</h3>
        <div className="kpi-card kpi-card-eh">
          <span className="kpi-label">Moyenne métropole</span>
          <span className="kpi-value">{diag?.eh_index_100_avg ?? "—"} / 100</span>
        </div>
        <ul className="kpi-legend">
          {Object.values(axes).map((ax) => (
            <li key={ax.label}>
              {ax.label} :{" "}
              {Object.entries(ax)
                .filter(([k]) => k !== "label")
                .map(([k, v]) => `${k} ${v ?? "—"}`)
                .join(" · ")}
            </li>
          ))}
        </ul>
      </section>

      {overview && overview.couples.length > 0 && (
        <section className="kpi-section">
          <h3>Couples d&apos;indicateurs</h3>
          <p className="kpi-muted">
            Deux paramètres, un indicateur, des stats. Semaine type de{" "}
            {overview.person_count} individus simulés à Antananarivo.
          </p>
          <div className="couple-grid">
            {overview.couples.map((couple) => (
              <article key={couple.id} className="couple-card">
                <h3>{couple.title}</h3>
                <div className="couple-pair">
                  <div>
                    <span>{couple.left.name}</span>
                    <strong>
                      {couple.left.value} {couple.left.unit}
                    </strong>
                  </div>
                  <div>
                    <span>{couple.right.name}</span>
                    <strong>
                      {couple.right.value} {couple.right.unit}
                    </strong>
                  </div>
                </div>
                <p className="couple-indicator">{couple.indicator.name}</p>
                <div className="couple-meter">
                  <div style={{ width: `${Math.min(100, couple.indicator.value)}%` }} />
                </div>
                <strong className="couple-score">
                  {couple.indicator.value} {couple.indicator.unit}
                </strong>
                <ul>
                  {couple.stats.map((stat) => (
                    <li key={stat.name}>
                      {stat.name} : {stat.value} {stat.unit}
                    </li>
                  ))}
                </ul>
                <p className="kpi-muted">{couple.reading}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="kpi-section">
        <h3>Zones dortoirs</h3>
        <p className="kpi-muted">
          {(diag?.dormitories ?? []).map((z) => z.name).join(", ") || "—"}
        </p>
        <h3>Zones d&apos;activités déconnectées</h3>
        <p className="kpi-muted">
          {(diag?.disconnected_jobs ?? []).map((z) => z.name).join(", ") || "—"}
        </p>
      </section>

      <section className="kpi-section">
        <h3>Bureaux satellites (3-5 sites)</h3>
        <p className="kpi-muted">
          Ancre : {sats?.anchor.name} · {sats?.anchor.jobs_proxy} emplois proxy
        </p>
        <ol className="kpi-top-list">
          {(sats?.candidates ?? []).map((c) => (
            <li key={c.rank}>
              <div className="kpi-top-main">
                <strong>
                  {c.rank}. {c.name}
                </strong>
                <span className="kpi-badge">{c.impact_score}</span>
              </div>
              <div className="kpi-top-meta">
                <span>{c.type_label}</span>
                <span>{c.km_saved_proxy} km évités (proxy)</span>
              </div>
            </li>
          ))}
        </ol>
        <p className="kpi-muted">{sats?.method}</p>
      </section>

      <section className="kpi-section">
        <h3>Télétravail (axe secondaire)</h3>
        <label className="field">
          Taux {Math.round(rate * 100)}%
          <input
            type="range"
            min={0}
            max={0.8}
            step={0.05}
            value={rate}
            onChange={(e) => setRate(Number(e.target.value))}
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
        <label>
          <input
            type="checkbox"
            checked={combine}
            onChange={(e) => setCombine(e.target.checked)}
          />{" "}
          Combiner avec bureau satellite
        </label>
        <button type="button" className="map-btn" onClick={runTelework}>
          Estimer l&apos;impact
        </button>
        {tele && (
          <p className="kpi-muted">
            km {(tele.comparison as { km?: { delta?: number } })?.km?.delta ?? "—"} ·
            CO₂{" "}
            {(tele.comparison as { co2_t?: { delta?: number } })?.co2_t?.delta ??
              "—"}{" "}
            t
          </p>
        )}
      </section>

      <section className="kpi-section">
        <h3>Contribution citoyenne</h3>
        <textarea
          className="contrib-input"
          rows={3}
          placeholder="Signaler un besoin ou une suggestion de tiers-lieu…"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button type="button" className="map-btn" onClick={sendContribution}>
          Envoyer
        </button>
        {contribNote && <p className="kpi-muted">{contribNote}</p>}
      </section>

      <section className="kpi-note">
        <strong>Vue grand public</strong>
        <p>
          L&apos;indice de votre quartier est la couleur de la maille sur la carte
          (0 = déséquilibre, 100 = proximité emplois/habitat). {diag?.note}
        </p>
      </section>
    </aside>
  );
}
