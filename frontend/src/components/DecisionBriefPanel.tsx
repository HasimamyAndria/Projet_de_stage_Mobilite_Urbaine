import { useEffect, useState } from "react";
import api from "../services/api";
import {
  downloadJson,
  downloadSlidesHtml,
  printHtmlReport,
} from "../utils/exportReport";
import type { AnnexesGeoJSON } from "./Map/SatellitesLayer";

type Scenario = {
  id: string;
  label: string;
  trips: number;
  km: number;
  co2_t: number;
  avg_time_min: number;
  arrivals_at_hq: number | null;
  delta: {
    trips: number | null;
    km: number | null;
    co2_t: number | null;
    avg_time_min: number | null;
    arrivals_at_hq: number | null;
  };
};

type Brief = {
  ok: boolean;
  message: string | null;
  anchor: { id: number; name: string; jobs_proxy: number } | null;
  critical_corridors: Array<{
    origin_name: string;
    volume: number;
    distance_km: number | null;
    costly: boolean;
  }>;
  annexes: Array<{
    rank: number;
    name: string;
    type_label: string;
    km_saved_proxy: number;
    impact_score?: number;
    criteria?: Array<{ id: string; label: string; weight: number; score: number; value: number; unit: string }>;
    constraints: Record<string, string | number>;
  }>;
  geojson: AnnexesGeoJSON;
  scenarios: Scenario[];
  recommendation: {
    scenario_id: string;
    rationale: string;
    hypotheses: string[];
  } | null;
  note_decideur: string;
  limitations: string[];
  parameters_used?: {
    telework_rate: number;
    annex_intensity: number;
    telework_pattern: string;
  };
};

type ZoneOpt = { id: number; name: string };

function fmt(n: number | null | undefined, digits = 1) {
  if (n == null) return "seuil k";
  return n.toLocaleString("fr-FR", { maximumFractionDigits: digits });
}

function deltaClass(n: number | null | undefined) {
  if (n == null || n === 0) return "";
  return n < 0 ? "delta-good" : "delta-bad";
}

type MetricKey = "trips" | "km" | "co2_t" | "avg_time_min" | "arrivals_at_hq";

const INDICATORS: Array<{ key: MetricKey; label: string; digits: number }> = [
  { key: "trips", label: "Trajets / j", digits: 0 },
  { key: "km", label: "km parcourus", digits: 0 },
  { key: "avg_time_min", label: "Temps moyen (min)", digits: 1 },
  { key: "co2_t", label: "CO₂ (t)", digits: 2 },
  { key: "arrivals_at_hq", label: "Arrivées au siège", digits: 0 },
];

export default function DecisionBriefPanel({
  onAnnexesGeoJSON,
}: {
  onAnnexesGeoJSON?: (fc: AnnexesGeoJSON | null) => void;
}) {
  const [zones, setZones] = useState<ZoneOpt[]>([]);
  const [anchorZoneId, setAnchorZoneId] = useState<string>("");
  const [organization, setOrganization] = useState("Direction des finances");
  const [sector, setSector] = useState("admin");
  const [headcount, setHeadcount] = useState(800);
  const [sharePresent, setSharePresent] = useState(0.35);
  const [teleMax, setTeleMax] = useState(0.4);
  const [pattern, setPattern] = useState("hybrid_1_2");
  const [maxAnnexes, setMaxAnnexes] = useState(3);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get("/api/od/zones")
      .then((res) => {
        const feats = res.data?.features ?? [];
        setZones(
          feats.map((f: { properties?: { id: number; name: string } }) => ({
            id: f.properties?.id as number,
            name: f.properties?.name as string,
          }))
        );
      })
      .catch(() => setZones([]));
  }, []);

  async function compare() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post("/api/decision-brief", {
        anchor_zone_id: anchorZoneId === "" ? null : Number(anchorZoneId),
        organization,
        sector,
        headcount,
        share_must_be_present: sharePresent,
        telework_rate_max: teleMax,
        telework_pattern: pattern,
        max_annexes: maxAnnexes,
        peak_hours: [7, 8, 9],
      });
      const data = res.data as Brief;
      setBrief(data);
      if (data.ok && data.geojson) {
        onAnnexesGeoJSON?.(data.geojson);
      }
      if (!data.ok) {
        setError(data.message || "Dossier incomplet.");
      }
    } catch {
      setError("Dossier décideur indisponible (backend).");
    } finally {
      setBusy(false);
    }
  }

  const recId = brief?.recommendation?.scenario_id;
  const rec = brief?.scenarios.find((s) => s.id === recId);
  const ref = brief?.scenarios.find((s) => s.id === "reference");

  return (
    <section className="kpi-section brief-block">
      <h3>Dossier décideur</h3>
      <p className="kpi-muted">
        Comparer bureaux annexes et télétravail pour un siège centre-ville.
        Aucun trajet individuel n&apos;est utilisé.
      </p>

      <label className="field">
        Siège (pôle d&apos;emploi)
        <select value={anchorZoneId} onChange={(e) => setAnchorZoneId(e.target.value)}>
          <option value="">Pôle centre le plus attractif (défaut)</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Organisation
        <input
          type="text"
          value={organization}
          onChange={(e) => setOrganization(e.target.value)}
        />
      </label>
      <label className="field">
        Secteur
        <select value={sector} onChange={(e) => setSector(e.target.value)}>
          <option value="admin">Finance / admin</option>
          <option value="tertiaire">Tertiaire</option>
          <option value="tech">Tech</option>
          <option value="soin">Soin</option>
          <option value="industrie">Industrie</option>
        </select>
      </label>
      <label className="field">
        Effectif {headcount}
        <input
          type="range"
          min={50}
          max={5000}
          step={50}
          value={headcount}
          onChange={(e) => setHeadcount(Number(e.target.value))}
        />
      </label>
      <label className="field">
        Part devant être présente {Math.round(sharePresent * 100)}%
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={sharePresent}
          onChange={(e) => setSharePresent(Number(e.target.value))}
        />
      </label>
      <label className="field">
        Taux max télétravail {Math.round(teleMax * 100)}%
        <input
          type="range"
          min={0}
          max={0.8}
          step={0.05}
          value={teleMax}
          onChange={(e) => setTeleMax(Number(e.target.value))}
        />
      </label>
      <label className="field">
        Rythme
        <select value={pattern} onChange={(e) => setPattern(e.target.value)}>
          <option value="full_remote">Full remote</option>
          <option value="hybrid_1_2">Hybride 1–2 j</option>
          <option value="hybrid_3_4">Hybride 3–4 j</option>
        </select>
      </label>
      <label className="field">
        Nombre max d&apos;annexes {maxAnnexes}
        <input
          type="range"
          min={3}
          max={5}
          step={1}
          value={maxAnnexes}
          onChange={(e) => setMaxAnnexes(Number(e.target.value))}
        />
      </label>
      <button
        type="button"
        className="search-card-btn"
        onClick={compare}
        disabled={busy}
      >
        {busy ? "Calcul…" : "Comparer les scénarios"}
      </button>
      {error && <p className="kpi-error">{error}</p>}

      {brief?.ok && ref && (
        <>
          <p className="kpi-muted">
            Siège : {brief.anchor?.name} · {brief.critical_corridors.length}{" "}
            corridors critiques
          </p>
          <div className="od-matrix-wrap">
            <table className="compare-table">
              <thead>
                <tr>
                  <th>Indicateur</th>
                  {brief.scenarios.map((s) => (
                    <th key={s.id} className={s.id === recId ? "row-self" : undefined}>
                      {s.id === "reference"
                        ? "Réf."
                        : s.id === "annexes"
                          ? "Annexes"
                          : s.id === "telework"
                            ? "Télétravail"
                            : "Mix"}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {INDICATORS.map((ind) => (
                  <tr key={ind.key}>
                    <td>{ind.label}</td>
                    {brief.scenarios.map((s) => {
                      const v = s[ind.key];
                      return (
                        <td
                          key={s.id}
                          className={s.id === recId ? "row-self" : undefined}
                        >
                          {fmt(typeof v === "number" ? v : null, ind.digits)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rec && (
            <p className="kpi-muted">
              Mix / levier retenu vs référence : trajets{" "}
              <span className={deltaClass(rec.delta.trips)}>
                {fmt(rec.delta.trips, 0)}
              </span>{" "}
              · km{" "}
              <span className={deltaClass(rec.delta.km)}>{fmt(rec.delta.km, 0)}</span>{" "}
              · CO₂ évité{" "}
              <span className={deltaClass(rec.delta.co2_t)}>
                {fmt(rec.delta.co2_t != null ? -rec.delta.co2_t : null, 2)} t
              </span>{" "}
              · arrivées au siège{" "}
              <span className={deltaClass(rec.delta.arrivals_at_hq)}>
                {fmt(rec.delta.arrivals_at_hq, 0)}
              </span>
            </p>
          )}

          <h3>Bureaux annexes retenus</h3>
          <ol className="kpi-top-list">
            {brief.annexes.map((a) => (
              <li key={a.rank}>
                <div className="kpi-top-main">
                  <strong>{a.name}</strong>
                </div>
                <div className="kpi-top-meta">
                  <span>{a.type_label}</span>
                  <span>Score {a.impact_score ?? "—"}/100</span>
                  <span>{a.km_saved_proxy} km/j évités (proxy)</span>
                </div>
                {a.criteria && a.criteria.length > 0 && (
                  <p className="kpi-muted">
                    {a.criteria
                      .map((item) => `${item.label} ${item.score} (${Math.round(item.weight * 100)} %)`)
                      .join(" · ")}
                  </p>
                )}
                <p className="kpi-muted">
                  Foncier {(a.constraints.foncier as string) ?? "—"} · TC{" "}
                  {(a.constraints.desserte_tc as string) ?? "—"}
                </p>
              </li>
            ))}
          </ol>

          <h3>Corridors critiques</h3>
          <ul className="kpi-legend">
            {brief.critical_corridors.slice(0, 6).map((c) => (
              <li key={c.origin_name}>
                {c.origin_name} → siège · {c.volume} passagers
                {c.costly ? " · ≥ 6 km" : ""}
              </li>
            ))}
          </ul>

          {brief.recommendation && (
            <section className="kpi-note">
              <strong>Levier retenu</strong>
              {brief.recommendation.rationale.split("\n").map((line) => (
                <p key={line}>{line}</p>
              ))}
            </section>
          )}

          <section className="decision-note">
            <strong>Note décideur</strong>
            <pre>{brief.note_decideur}</pre>
          </section>

          <div className="export-row">
            <button
              type="button"
              className="map-btn"
              onClick={() => downloadJson("dossier-decideur.json", brief)}
            >
              JSON
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                printHtmlReport(
                  `Note décideur — ${organization}`,
                  `<pre style="white-space:pre-wrap;font-family:Segoe UI,sans-serif">${brief.note_decideur
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")}</pre>
                   <p class="muted">${brief.limitations[0] ?? ""}</p>`
                )
              }
            >
              Impression
            </button>
            <button
              type="button"
              className="map-btn"
              onClick={() =>
                downloadSlidesHtml("dossier-comite.html", "Dossier décideur", [
                  `<h1>${organization}</h1><p>${brief.anchor?.name ?? ""} — 4 scénarios.</p>`,
                  `<h1>Impact</h1><p>CO₂ ${fmt(rec?.delta.co2_t, 2)} t · arrivées ${fmt(rec?.delta.arrivals_at_hq, 0)} · km ${fmt(rec?.delta.km, 0)}</p>`,
                  `<h1>Limites</h1><p>${(brief.limitations ?? []).join(" ")}</p>`,
                ])
              }
            >
              Présentation
            </button>
          </div>
        </>
      )}
    </section>
  );
}
