import { useEffect, useState } from "react";
import api from "../services/api";
import { printHtmlReport } from "../utils/exportReport";

type Who = {
  home: string;
  work: string;
  headcount: number;
  function: string;
  grade_label: string;
  before_km: number;
  after_km: number;
  mode_label: string;
};

type Option = {
  id: string;
  kind: string;
  title: string;
  people: number;
  site_name: string | null;
  km_saved_per_working_day: number;
  reading: string;
  who: Who[];
  assumptions: string;
  limits: string[];
};

type Step = { when: string; text: string; mode: string };

type Cluster = {
  id: string;
  home_name: string;
  home_parent: string | null;
  work_name: string;
  headcount: number;
  mode_label: string;
  function: string;
  grade_label: string;
  considerable: boolean;
  relocatable: boolean;
  km: number;
  minutes: number;
  far: boolean;
  reading: string;
  rhythm: {
    label: string;
    km_one_way: number;
    minutes_one_way: number;
    mode_label: string;
    note: string;
    steps: Step[];
  };
};

type Sample = {
  id: string;
  name: string;
  job: string;
  home: string;
  work: string;
  cluster_id: string | null;
  blurb: string;
};

type Employer = {
  id: string;
  name: string;
  kind_label: string;
  decision_target: boolean;
  activity: string;
  seat_name: string;
  employee_count: number;
  far_count: number;
  considerable_far_count: number;
  headline: string;
  clusters: Cluster[];
  options: Option[];
  samples: Sample[];
};

type Board = {
  city_name: string;
  focus_id: string | null;
  far_km: number;
  note: string;
  employers: Employer[];
};

export type JourneyPhase = "org" | "trips" | "needs" | "satellite" | "compare" | "decision";

export type JourneyOrg = {
  id: string;
  cityId: string;
  name: string;
  farIds: string[];
  defaultNeedIds: string[];
  satelliteIds: string[];
  defaultSatelliteId: string;
};

const SATELLITE_KINDS = new Set(["louer", "construire"]);

const KIND_LABEL: Record<string, string> = {
  louer: "Location",
  construire: "Construction",
  navette: "Navette",
  teletravail: "Télétravail",
  pas_annexe: "Poste sur site",
  rien: "Proche",
};

function fmt(value: number) {
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
}

function fmtKm(value: number) {
  return value.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export default function EmployerBoard({
  cityId,
  phase,
  needIds,
  satelliteId,
  onSelectOrg,
  onOpenPerson,
  onToggleNeed,
  onSatellite,
  onOrgReady,
}: {
  cityId: string;
  phase: JourneyPhase;
  needIds: string[];
  satelliteId: string;
  onSelectOrg: (organizationId: string) => void;
  onOpenPerson: (personId: string) => void;
  onToggleNeed: (clusterId: string) => void;
  onSatellite: (optionId: string) => void;
  onOrgReady: (org: JourneyOrg) => void;
}) {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [orgId, setOrgId] = useState("");
  const [clusterId, setClusterId] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get<Board>("/api/mobility/employers", { params: { city_id: cityId } })
      .then((res) => {
        if (cancelled) return;
        setBoard(res.data);
        setError(null);
        const next = res.data.focus_id ?? res.data.employers[0]?.id ?? "";
        setOrgId(next);
      })
      .catch(() => {
        if (!cancelled) setError("Lecture des employeurs impossible.");
      });
    return () => {
      cancelled = true;
    };
  }, [cityId]);

  const org = board?.employers.find((item) => item.id === orgId) ?? board?.employers[0];

  useEffect(() => {
    if (org?.id) onSelectOrg(org.id);
  }, [org?.id, onSelectOrg]);

  useEffect(() => {
    if (!org) return;
    const far = org.clusters.filter((item) => item.far);
    const preferred = far.filter((item) => item.considerable);
    const satellites = org.options.filter((item) => SATELLITE_KINDS.has(item.kind));
    const primary = satellites.find((item) => item.kind === "louer" && !item.title.startsWith("Autre"));
    onOrgReady({
      id: org.id,
      cityId,
      name: org.name,
      farIds: far.map((item) => item.id),
      defaultNeedIds: (preferred.length > 0 ? preferred : far).map((item) => item.id),
      satelliteIds: satellites.map((item) => item.id),
      defaultSatelliteId: primary?.id ?? satellites[0]?.id ?? "",
    });
  }, [org, cityId, onOrgReady]);

  useEffect(() => {
    if (!org) return;
    const preferred =
      org.clusters.find((item) => item.far && item.considerable) ??
      org.clusters.find((item) => item.far) ??
      org.clusters[0];
    setClusterId(preferred?.id ?? "");
  }, [org]);

  if (error) return <p className="diary-error">{error}</p>;
  if (!board || !org) return <p className="diary-muted">Chargement des employeurs…</p>;

  const cluster = org.clusters.filter((item) => item.far).find((item) => item.id === clusterId) ??
    org.clusters.find((item) => item.id === clusterId) ??
    org.clusters[0];
  const people = cluster
    ? org.samples.filter((sample) => sample.cluster_id === cluster.id)
    : [];
  const farClusters = org.clusters.filter((item) => item.far);
  const selectedNeeds = org.clusters.filter((item) => needIds.includes(item.id));
  const satellites = org.options.filter((item) => SATELLITE_KINDS.has(item.kind));
  const tested = org.options.find((item) => item.id === satelliteId) ?? null;
  const withoutAnnex = org.options.find((item) => item.kind === "pas_annexe" || item.kind === "rien");

  const testedName = tested?.title.replace(/^Autre possibilité : /, "").replace(/^./, (letter) => letter.toUpperCase());
  const argument = tested
    ? `Retenir « ${testedName} » pour ${org.name}. ${fmt(tested.people)} personnes verraient le trajet vers ${org.seat_name} remplacé par un trajet vers ${tested.site_name ?? "l'annexe"}, soit ${fmt(tested.km_saved_per_working_day)} km évités par jour ouvré. ${tested.reading}`
    : `Ne pas ouvrir de bureau satellite pour ${org.name}. ${withoutAnnex?.reading ?? "Le catalogue ne chiffre pas d'annexe pour ces groupes."}`;

  function printDecision() {
    const rows = (tested?.who ?? [])
      .map(
        (row) =>
          `<tr><td>${escapeHtml(`${row.headcount} ${row.function}`)}</td><td>${escapeHtml(row.home)} → ${escapeHtml(row.work)}</td><td>${fmtKm(row.before_km)} km</td><td>${fmtKm(row.after_km)} km</td></tr>`
      )
      .join("");
    const needs = selectedNeeds
      .map(
        (item) =>
          `<li>${fmt(item.headcount)} ${escapeHtml(item.function)} — ${escapeHtml(item.home_name)} → ${escapeHtml(item.work_name)}, ${fmtKm(item.km)} km</li>`
      )
      .join("");
    const others = org.options
      .map(
        (option) =>
          `<li>${option.id === tested?.id ? "<b>Testé. </b>" : ""}${escapeHtml(option.title)} — ${fmt(option.people)} personnes, ${fmt(option.km_saved_per_working_day)} km évités / jour ouvré</li>`
      )
      .join("");
    printHtmlReport(
      `Décision — ${org.name}`,
      `<p>${escapeHtml(org.kind_label)} · siège à ${escapeHtml(org.seat_name)} · ${fmt(org.employee_count)} employés dans les groupes.</p>
       <h2>Besoins retenus</h2>
       <ul>${needs || "<li>Aucun groupe au-delà du seuil d'éloignement.</li>"}</ul>
       <h2>Décision argumentée</h2>
       <p>${escapeHtml(argument)}</p>
       <h2>Comparaison</h2>
       <ul>${others}</ul>
       ${rows ? `<h2>Avant / après pour l'annexe testée</h2><table><thead><tr><th>Groupe</th><th>Trajet</th><th>Avant</th><th>Après</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
       <h2>Hypothèses et limites</h2>
       <p>${escapeHtml(tested?.assumptions ?? withoutAnnex?.assumptions ?? "")}</p>
       <ul>${(tested?.limits ?? withoutAnnex?.limits ?? []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
       <p class="muted">${escapeHtml(board.note)}</p>`
    );
  }

  return (
    <section className="employer">
      {phase === "org" && (
        <header className="employer-intro">
          <h2>1. Choisir une organisation</h2>
          <p>
            {board.city_name}. Grandes organisations et branches d&apos;État : on regroupe les
            gens qui habitent le même quartier, travaillent au même endroit et occupent la même
            fonction. À partir de 20 personnes et de {fmt(board.far_km)} km, la suite chiffre
            un bureau satellite.
          </p>
          <p className="diary-muted">{board.note}</p>
        </header>
      )}

      {phase === "org" && (
      <div className="employer-orgs" role="tablist" aria-label="Organisations">
        {board.employers.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === org.id}
            className={item.id === org.id ? "employer-org active" : "employer-org"}
            onClick={() => setOrgId(item.id)}
          >
            <span className="employer-kind">{item.kind_label}</span>
            <strong>{item.name}</strong>
            <span>
              {fmt(item.far_count)} loin du siège
              {item.considerable_far_count > 0
                ? ` · ${fmt(item.considerable_far_count)} postes considérables`
                : ""}
            </span>
          </button>
        ))}
      </div>
      )}

      {phase !== "org" && (
        <p className="journey-context">
          Organisation : <strong>{org.name}</strong>
          <span>
            {" "}
            · siège à {org.seat_name} · {fmt(org.employee_count)} employés dans les groupes
          </span>
        </p>
      )}

      {(phase === "org" || phase === "trips") && (
      <p className="employer-headline">
        <strong>{org.headline}</strong>
        <span>
          {" "}
          · siège à {org.seat_name} · {fmt(org.employee_count)} employés dans les groupes ·{" "}
          {org.activity}
        </span>
      </p>
      )}

      {phase === "trips" && (
      <>
      <div className="journey-step">
        <h2>2. Examiner les trajets</h2>
        <p>
          Chaque ligne est un groupe : même domicile, même travail, même fonction. Le récit à droite
          est une journée type. Les graphiques en dessous comptent les trajets.
        </p>
      </div>
      <div className="employer-split">
        <div className="diary-table-wrap">
          <table className="diary-table employer-table">
            <thead>
              <tr>
                <th>Effectif</th>
                <th>Domicile → travail</th>
                <th>Fonction</th>
                <th>Trajet</th>
              </tr>
            </thead>
            <tbody>
              {org.clusters.map((item) => (
                <tr
                  key={item.id}
                  className={item.id === cluster?.id ? "is-selected" : undefined}
                  onClick={() => setClusterId(item.id)}
                >
                  <td>
                    <strong>{fmt(item.headcount)}</strong>
                    {item.far && <span className="employer-flag">loin</span>}
                  </td>
                  <td>
                    {item.home_name}
                    {item.home_parent ? ` (${item.home_parent})` : ""} → {item.work_name}
                  </td>
                  <td>
                    {item.function}
                    <span className="diary-detail">{item.grade_label}</span>
                  </td>
                  <td>
                    {fmtKm(item.km)} km · {item.minutes} min · {item.mode_label}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {cluster && (
          <article className="employer-rhythm">
            <h3>
              {fmt(cluster.headcount)} · {cluster.home_name} → {cluster.work_name}
            </h3>
            <p>{cluster.reading}</p>
            <p className="diary-muted">
              {cluster.rhythm.label} · {cluster.rhythm.mode_label} · {fmtKm(cluster.rhythm.km_one_way)} km
              · {cluster.rhythm.minutes_one_way} min par trajet
            </p>
            <ol>
              {cluster.rhythm.steps.map((step) => (
                <li key={`${step.when}-${step.text}`}>
                  <strong>{step.when}</strong> {step.text}
                </li>
              ))}
            </ol>
            <p className="diary-muted">{cluster.rhythm.note}</p>
            {people.length > 0 && (
              <div className="employer-samples">
                {people.map((sample) => (
                  <button key={sample.id} type="button" onClick={() => onOpenPerson(sample.id)}>
                    Semaine de {sample.name}, {sample.job}
                  </button>
                ))}
              </div>
            )}
          </article>
        )}
      </div>
      </>
      )}

      {phase === "needs" && (
        <div className="journey-step">
          <h2>3. Identifier les besoins</h2>
          <p>
            Un besoin est un groupe dont le domicile est à {fmt(board.far_km)} km ou plus du siège.
            Cochez les groupes que la décision doit traiter.
          </p>
          {farClusters.length === 0 ? (
            <p className="diary-muted">
              Aucun groupe de {org.name} n&apos;atteint ce seuil. Il n&apos;y a pas de besoin
              d&apos;éloignement à traiter.
            </p>
          ) : (
            <ul className="journey-needs">
              {farClusters.map((item) => (
                <li key={item.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={needIds.includes(item.id)}
                      onChange={() => onToggleNeed(item.id)}
                    />
                    <span>
                      <strong>
                        {fmt(item.headcount)} {item.function}
                      </strong>
                      {item.home_name}
                      {item.home_parent ? ` (${item.home_parent})` : ""} → {item.work_name}
                      {" · "}
                      {fmtKm(item.km)} km · {item.minutes} min · {item.mode_label}
                      {item.considerable && <em> poste considérable</em>}
                    </span>
                  </label>
                  <p>{item.reading}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {phase === "satellite" && (
        <div className="journey-step">
          <h2>4. Tester un bureau satellite</h2>
          <p>
            La location et la construction posent une annexe près du domicile. Choisissez l&apos;annexe
            à tester. La navette et le télétravail restent visibles à l&apos;étape suivante.
          </p>
          {satellites.length === 0 ? (
            <article className="employer-option">
              <span className="employer-kind">{KIND_LABEL[withoutAnnex?.kind ?? "rien"]}</span>
              <h3>{withoutAnnex?.title ?? "Pas de bureau satellite à tester"}</h3>
              <p>{withoutAnnex?.reading}</p>
              <p className="diary-muted">{withoutAnnex?.limits.join(" ")}</p>
            </article>
          ) : (
            <div className="employer-options">
              {satellites.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={option.id === satelliteId ? "employer-option is-tested" : "employer-option"}
                  aria-pressed={option.id === satelliteId}
                  onClick={() => onSatellite(option.id)}
                >
                  <span className="employer-kind">{KIND_LABEL[option.kind] ?? option.kind}</span>
                  <h3>{option.title}</h3>
                  <p className="employer-metrics">
                    <strong>{fmt(option.people)}</strong> personnes ·{" "}
                    <strong>{fmt(option.km_saved_per_working_day)}</strong> km évités / jour ouvré
                    {option.site_name ? ` · ${option.site_name}` : ""}
                  </p>
                  <p>{option.reading}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {phase === "compare" && (
        <div className="journey-step">
          <h2>5. Comparer les résultats</h2>
          <p>
            La situation actuelle est le trajet jusqu&apos;au siège. L&apos;annexe testée se compare aux
            autres possibilités sur les kilomètres évités par jour ouvré.
          </p>
          <div className="diary-table-wrap">
            <table className="diary-table">
              <thead>
                <tr>
                  <th>Possibilité</th>
                  <th>Personnes</th>
                  <th>km évités / jour ouvré</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Situation actuelle — siège à {org.seat_name}</td>
                  <td>{fmt(selectedNeeds.reduce((sum, item) => sum + item.headcount, 0) || org.far_count)}</td>
                  <td>0</td>
                </tr>
                {org.options.map((option) => (
                  <tr key={option.id} className={option.id === tested?.id ? "is-selected" : undefined}>
                    <td>
                      {option.id === tested?.id && <span className="employer-flag">testé</span>}{" "}
                      {option.title}
                    </td>
                    <td>{fmt(option.people)}</td>
                    <td>{fmt(option.km_saved_per_working_day)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {tested && tested.who.length > 0 && (
            <>
              <h3 className="employer-options-title">Avant et après pour l&apos;annexe testée</h3>
              <div className="diary-table-wrap">
                <table className="diary-table">
                  <thead>
                    <tr>
                      <th>Groupe</th>
                      <th>Aujourd&apos;hui</th>
                      <th>Vers l&apos;annexe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tested.who.map((row) => (
                      <tr key={`${row.home}-${row.function}`}>
                        <td>
                          {fmt(row.headcount)} {row.function}
                          <span className="diary-detail">
                            {row.home} → {row.work}
                          </span>
                        </td>
                        <td>{fmtKm(row.before_km)} km</td>
                        <td>{fmtKm(row.after_km)} km</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {phase === "decision" && (
        <div className="journey-step">
          <h2>6. Préparer une décision argumentée</h2>
          <article className="journey-brief">
            <p>
              <strong>{org.name}</strong> · {org.kind_label} · siège à {org.seat_name}
            </p>
            <h3>Besoins retenus</h3>
            {selectedNeeds.length === 0 ? (
              <p>Aucun groupe éloigné n&apos;est retenu.</p>
            ) : (
              <ul>
                {selectedNeeds.map((item) => (
                  <li key={item.id}>
                    {fmt(item.headcount)} {item.function} — {item.home_name} → {item.work_name},{" "}
                    {fmtKm(item.km)} km, {item.minutes} min
                  </li>
                ))}
              </ul>
            )}
            <h3>Décision</h3>
            <p>{argument}</p>
            <p className="diary-muted">{tested?.assumptions ?? withoutAnnex?.assumptions}</p>
            <ul>
              {(tested?.limits ?? withoutAnnex?.limits ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="diary-muted">{board.note}</p>
            <button type="button" className="journey-print" onClick={printDecision}>
              Imprimer la note
            </button>
          </article>
        </div>
      )}
    </section>
  );
}
