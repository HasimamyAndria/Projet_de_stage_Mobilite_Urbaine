import { useEffect, useState } from "react";
import api from "../services/api";
import { downloadCsv, downloadJson, downloadSlidesHtml, printHtmlReport } from "../utils/exportReport";

type Kpi = { id: string; label: string; value: number | null; unit: string };
type Obj = { name: string; horizon: string; target: number; current: number; unit: string };
type Dash = { kpis: Kpi[]; objectives: Obj[]; note: string };

function fmt(value: number | null, unit: string) {
  if (value == null) return "—";
  const text = value.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
  return unit ? `${text} ${unit}` : text;
}

export default function ReportsView() {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get("/api/kpi/dashboard")
      .then((res) => setData(res.data))
      .catch(() => setError("Les rapports ne peuvent pas être préparés : l'API ne répond pas."));
  }, []);

  return (
    <div className="reports-page">
      <header className="view-intro">
        <h1>Rapports</h1>
        <p>
          Trois exports à partir des indicateurs déjà calculés. Chaque fichier rappelle
          que les volumes sont simulés.
        </p>
      </header>
      {error && <p className="home-kpi-status">{error}</p>}
      {!data && !error && <p className="home-kpi-status">Préparation des synthèses…</p>}
      {data && (
        <div className="report-grid">
          <article className="report-card">
            <h2>Données</h2>
            <p>Le tableau de bord complet, au format JSON, pour un tableur ou un script.</p>
            <div className="export-row">
              <button
                type="button"
                className="home-apply"
                onClick={() =>
                  downloadCsv("mobilite-indicateurs.csv", [
                    ["indicateur", "valeur", "unite"],
                    ...data.kpis.map((item) => [
                      item.label,
                      item.value == null ? "" : String(item.value),
                      item.unit,
                    ]),
                  ])
                }
              >
                Télécharger CSV
              </button>
              <button type="button" className="home-apply" onClick={() => downloadJson("mobilite-dashboard.json", data)}>
                Télécharger JSON
              </button>
            </div>
          </article>
          <article className="report-card">
            <h2>Note pour le conseil</h2>
            <p>Une page imprimable avec les indicateurs et les objectifs PDM / SCoT.</p>
            <button
              type="button"
              className="home-apply"
              onClick={() =>
                printHtmlReport(
                  "Note mobilité urbaine",
                  `<ul>${data.kpis
                    .map((item) => `<li><b>${item.label}</b> — ${fmt(item.value, item.unit)}</li>`)
                    .join("")}</ul>
                   <h2>Objectifs</h2>
                   <ul>${data.objectives
                     .map(
                       (item) =>
                         `<li>${item.name} (${item.horizon}) : actuel ${item.current}, cible ${item.target} ${item.unit}</li>`
                     )
                     .join("")}</ul>
                   <p>${data.note}</p>`
                )
              }
            >
              Ouvrir l'impression
            </button>
          </article>
          <article className="report-card">
            <h2>Support de présentation</h2>
            <p>Quatre diapositives HTML à ouvrir dans un navigateur.</p>
            <button
              type="button"
              className="home-apply"
              onClick={() =>
                downloadSlidesHtml("mobilite-conseil.html", "Conseil municipal", [
                  `<h1>MobilitySmart</h1><p>Synthèse de démonstration. Volumes simulés.</p>`,
                  `<h1>Indicateurs</h1><ul>${data.kpis
                    .map((item) => `<li>${item.label} : ${fmt(item.value, item.unit)}</li>`)
                    .join("")}</ul>`,
                  `<h1>Objectifs</h1><ul>${data.objectives
                    .map((item) => `<li>${item.name} — ${item.horizon}</li>`)
                    .join("")}</ul>`,
                  `<h1>Limites</h1><p>${data.note}</p>`,
                ])
              }
            >
              Télécharger HTML
            </button>
          </article>
        </div>
      )}
    </div>
  );
}
