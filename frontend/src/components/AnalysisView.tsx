import { useEffect, useState } from "react";
import api from "../services/api";
import type { ScenarioDraw } from "./Map/AnalysisScenarioLayer";

type MethodRow = {
  method: string;
  label: string;
  k: number;
  eps: number | null;
  min_samples: number | null;
  silhouette: number | null;
  clusters: number;
  noise_share: number;
  eligible: boolean;
  retained: boolean;
};

type ClusterCard = {
  id: number;
  label: string;
  size: number;
  mean_km: number;
  mean_min: number;
  homes: Array<{ name: string; headcount: number }>;
  works: Array<{ name: string; headcount: number }>;
};

type PlaceCount = { name: string; headcount: number };

type Profile = {
  id: string;
  title: string;
  people: number;
  mean_km: number | null;
  reading: string;
  homes?: PlaceCount[];
  works?: PlaceCount[];
  organizations?: Array<{
    organization_name: string;
    example: boolean;
    people: number;
    home_zones: number;
    mean_km: number;
    work: { name: string };
    homes: Array<{ name: string; headcount: number; distance_km?: number }>;
  }>;
};

type OrgHome = {
  name: string;
  headcount: number;
  mode: string;
  distance_km: number;
  lon: number;
  lat: number;
  share: number;
};

type Organization = {
  id: string;
  name: string;
  example: boolean;
  sector: string;
  seat_name: string;
  seat_lon: number;
  seat_lat: number;
  employees: number;
  mean_km: number;
  homes: OrgHome[];
  concentration: string;
  corridor: string;
};

type Corridor = {
  label: string;
  people: number;
  mean_km: number;
  origin_zones: number;
  origins?: Array<{ name: string; lon: number; lat: number; headcount: number }>;
  destination?: { name: string; lon: number; lat: number };
};

type ZoneHit = { name: string; people: number; mean_km?: number | null; reading?: string };
type Imbalance = {
  name: string;
  kind: string;
  eh_index: number;
  residents: number;
  jobs: number;
};

type Impact = {
  people_concerned: number;
  distance_saved_km_per_working_day: number;
  time_saved_min_per_person: number;
  time_saved_h_per_working_day: number;
  trips_reduced_per_working_day: number;
  co2_saved_kg_per_working_day: number;
  assumptions: string;
};

type ScenarioGroup = {
  home: string;
  lon: number;
  lat: number;
  headcount: number;
  mode: string;
  before_km: number;
  after_km: number;
  saved_km_per_working_day: number;
};

type PlacePoint = { name: string; lon: number; lat: number };

type Scenario = {
  kind: string;
  title: string;
  synthetic: boolean;
  example: boolean;
  status: string;
  status_label: string;
  why: string;
  data: string;
  impact: Impact;
  limits: string[];
  groups?: ScenarioGroup[];
  site?: PlacePoint | null;
  seat?: PlacePoint | null;
};

type WorkedHome = {
  name: string;
  headcount: number;
  mode: string;
  distance_km: number;
  lon: number;
  lat: number;
};

type WorkedExample = {
  synthetic: boolean;
  title: string;
  organization_name: string;
  note: string;
  seat_name: string;
  seat?: PlacePoint;
  homes: WorkedHome[];
  corridor: string;
  scenario: Scenario | null;
};

type Analysis = {
  synthetic: boolean;
  estimation_label: string;
  disclaimer: string;
  source: string;
  city: string;
  clustering: {
    chosen: { method: string; label: string; k: number; silhouette: number | null; seed: number | null } | null;
    comparison: MethodRow[];
    why: string;
    variables: string[];
    organization_note?: string;
    clusters: ClusterCard[];
    unit?: string;
  };
  profiles: Profile[];
  organizations: Organization[];
  detections: {
    critical_nodes: ZoneHit[];
    corridors: Corridor[];
    generation_zones: ZoneHit[];
    attraction_zones: ZoneHit[];
    mobility_deserts: Array<ZoneHit & { reading?: string }>;
    emploi_habitat_imbalances: Imbalance[];
    thresholds: Record<string, string>;
  };
  recommendations: Scenario[];
  not_proposed: Array<{ kind: string; reason: string }>;
  worked_example: WorkedExample | null;
};

const MODE_LABEL: Record<string, string> = {
  marche: "marche",
  velo: "vélo",
  bus: "bus",
  taxi: "taxi",
  car: "voiture",
};

const KIND_LABEL: Record<string, string> = {
  bureau_satellite: "Bureau satellite",
  tiers_lieu: "Tiers-lieu",
  teletravail: "Télétravail",
  transport_collectif: "Transport collectif",
  parking_relais: "Parking relais",
  piste_cyclable: "Piste cyclable",
  horaires: "Horaires",
};

function fr(value: number | null | undefined, digits = 1) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits === 0 ? 0 : undefined,
  });
}

function modeLabel(mode: string) {
  return MODE_LABEL[mode] ?? mode;
}

function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function StatusBadge({ scenario }: { scenario: Scenario }) {
  const recommended = scenario.status === "scenario_recommande";
  return (
    <span className={recommended ? "ia-status is-recommended" : "ia-status is-possible"}>
      {scenario.status_label}
    </span>
  );
}

function ImpactBlock({ impact, tripsHint }: { impact: Impact; tripsHint: string }) {
  return (
    <div className="ia-impact">
      <div>
        <span>Personnes concernées</span>
        <strong>{fr(impact.people_concerned, 0)}</strong>
      </div>
      <div>
        <span>Distance économisée</span>
        <strong>{fr(impact.distance_saved_km_per_working_day)} voyageurs-km</strong>
        <em>par jour ouvré</em>
      </div>
      <div>
        <span>Temps économisé</span>
        <strong>{fr(impact.time_saved_min_per_person, 0)} min / personne</strong>
        <em>{fr(impact.time_saved_h_per_working_day)} h au total / jour ouvré</em>
      </div>
      <div>
        <span>Déplacements réduits</span>
        <strong>{fr(impact.trips_reduced_per_working_day)}</strong>
        <em>{tripsHint}</em>
      </div>
      <div>
        <span>CO₂ estimé en moins</span>
        <strong>{fr(impact.co2_saved_kg_per_working_day)} kg</strong>
        <em>par jour ouvré</em>
      </div>
    </div>
  );
}

function tripsHintFor(kind: string) {
  if (kind === "bureau_satellite" || kind === "tiers_lieu") {
    return "allers-retours vers le siège ; un trajet vers le site peut rester";
  }
  if (kind === "transport_collectif") return "véhicules individuels évités, pas des personnes";
  if (kind === "teletravail") return "allers-retours évités les jours télétravaillés";
  if (kind === "horaires" || kind === "parking_relais" || kind === "piste_cyclable") {
    return "le nombre de personnes qui se déplacent ne change pas";
  }
  return "par jour ouvré";
}

function ScenarioCard({
  scenario,
  onShowScenario,
}: {
  scenario: Scenario;
  onShowScenario: (draw: ScenarioDraw) => void;
}) {
  const canDraw = Boolean(scenario.groups?.length && scenario.seat && scenario.site);
  return (
    <article className={scenario.example ? "dash-card ia-card ia-example" : "dash-card ia-card"}>
      <div className="ia-card-head">
        <StatusBadge scenario={scenario} />
        {scenario.example && <span className="ia-chip">jeu d'exemple simulé</span>}
        <span className="ia-chip">estimation simulée</span>
      </div>
      <h3>{scenario.title}</h3>
      <h4>Pourquoi ?</h4>
      <p>{scenario.why}</p>
      <h4>Sur quelles données ?</h4>
      <p>{scenario.data}</p>
      <h4>Combien de personnes sont concernées ?</h4>
      <p>
        {fr(scenario.impact.people_concerned, 0)} personnes dans ce scénario. Ce sont des
        effectifs simulés.
      </p>
      <h4>Quel impact estimé ?</h4>
      <ImpactBlock impact={scenario.impact} tripsHint={tripsHintFor(scenario.kind)} />
      <p className="kpi-muted">{scenario.impact.assumptions}</p>
      {scenario.groups && scenario.groups.length > 0 && (
        <table className="compare-table ia-table">
          <thead>
            <tr>
              <th>Résidence</th>
              <th>Personnes</th>
              <th>Mode</th>
              <th>Avant</th>
              <th>Après</th>
              <th>Voyageurs-km / jour</th>
            </tr>
          </thead>
          <tbody>
            {scenario.groups.map((group) => (
              <tr key={group.home}>
                <td>{group.home}</td>
                <td>{group.headcount}</td>
                <td>{modeLabel(group.mode)}</td>
                <td>{fr(group.before_km)} km</td>
                <td>{fr(group.after_km)} km</td>
                <td>{fr(group.saved_km_per_working_day)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h4>Quelles limites ?</h4>
      <ul className="ia-limits">
        {scenario.limits.map((limit) => (
          <li key={limit}>{limit}</li>
        ))}
      </ul>
      {canDraw && (
        <button
          type="button"
          className="map-btn"
          onClick={() =>
            onShowScenario({
              title: scenario.title,
              note: `${scenario.status_label}. Trait orange : vers le siège. Pointillé : vers le site proposé. Estimation simulée.`,
              origins: scenario.groups!.map((group) => ({
                name: group.home,
                lon: group.lon,
                lat: group.lat,
                headcount: group.headcount,
              })),
              destination: scenario.seat!,
              site: scenario.site,
            })
          }
        >
          Voir ce scénario sur la carte
        </button>
      )}
    </article>
  );
}

export default function AnalysisView({
  city,
  onShowScenario,
}: {
  city: string;
  onShowScenario: (draw: ScenarioDraw) => void;
}) {
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError(null);
    api
      .get("/api/mobility/analysis", { params: { city }, signal: controller.signal })
      .then((response) => setData(response.data as Analysis))
      .catch((err: { code?: string }) => {
        if (err.code === "ERR_CANCELED") return;
        setError("Analyse indisponible. L'API ne répond pas.");
      });
    return () => controller.abort();
  }, [city]);

  if (error) {
    return (
      <div className="dash-page">
        <p className="kpi-error">{error}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="dash-page">
        <p className="kpi-muted">Analyse des profils simulés…</p>
      </div>
    );
  }

  const chosen = data.clustering.chosen;
  const example = data.worked_example;

  return (
    <div className="dash-page ia-page">
      <header className="dash-head">
        <div>
          <h1>Analyse de la mobilité</h1>
          <p>
            Profils, concentrations et scénarios · {data.city} · {data.estimation_label}
          </p>
        </div>
      </header>

      <p className="ia-banner" role="note">
        {data.disclaimer}
      </p>
      <p className="kpi-muted">{data.source}</p>

      <nav className="ia-jump" aria-label="Sections de l'analyse">
        {[
          ["ia-clusters", "Clustering"],
          ["ia-profils", "Profils"],
          ["ia-orgs", "Organisations"],
          ["ia-detect", "Détection"],
          ["ia-scenarios", "Scénarios"],
          ["ia-exemple", "Exemple"],
        ].map(([id, label]) => (
          <button key={id} type="button" onClick={() => jump(id)}>
            {label}
          </button>
        ))}
      </nav>

      <section id="ia-clusters" className="ia-section">
        <h2>Clustering</h2>
        <p>
          Chaque point est un groupe d'employés simulés qui partagent déjà une origine, une
          destination, une distance, un mode et une fréquence. La taille d'un profil est la somme
          des effectifs.
        </p>
        {data.clustering.variables.length > 0 && (
          <p>Variables : {data.clustering.variables.join(" · ")}.</p>
        )}
        {data.clustering.organization_note && <p>{data.clustering.organization_note}</p>}
        {data.clustering.comparison.length > 0 && (
          <table className="compare-table ia-table">
            <thead>
              <tr>
                <th>Méthode</th>
                <th>Réglage</th>
                <th>Silhouette</th>
                <th>Groupes</th>
                <th>Bruit</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.clustering.comparison.map((row) => (
                <tr key={row.method} className={row.retained ? "row-self" : undefined}>
                  <td>{row.label}</td>
                  <td>
                    {row.method === "dbscan"
                      ? `eps ${row.eps} · minPts ${row.min_samples}`
                      : `k = ${row.k}`}
                  </td>
                  <td>{row.silhouette ?? "—"}</td>
                  <td>{row.clusters}</td>
                  <td>{Math.round(row.noise_share * 100)} %</td>
                  <td>{row.retained ? "retenue" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p>{data.clustering.why}</p>
        {chosen && (
          <p className="kpi-muted">
            Méthode retenue : {chosen.label}
            {chosen.k ? ` · k = ${chosen.k}` : ""}
            {chosen.silhouette != null ? ` · silhouette ${chosen.silhouette}` : ""}
            {chosen.seed != null ? ` · graine ${chosen.seed}` : ""}.
          </p>
        )}
        <div className="ia-cards">
          {data.clustering.clusters.map((cluster) => (
            <article key={cluster.id} className="dash-card">
              <h3>{cluster.label}</h3>
              <p>
                {fr(cluster.size, 0)} personnes · {fr(cluster.mean_km)} km · {cluster.mean_min} min
              </p>
              <p>
                Résidences :{" "}
                {cluster.homes.map((home) => `${home.name} (${home.headcount})`).join(", ")}
              </p>
              <p>
                Travail : {cluster.works.map((work) => `${work.name} (${work.headcount})`).join(", ")}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section id="ia-profils" className="ia-section">
        <h2>Profils</h2>
        <p>
          Ces trois lectures sont métier. Elles décrivent les groupes simulés. Elles ne sont pas la
          sortie brute de l'algorithme.
        </p>
        <div className="ia-cards">
          {data.profiles.map((profile) => (
            <article
              key={profile.id}
              className={profile.id === "convergence" ? "dash-card ia-example" : "dash-card"}
            >
              <h3>{profile.title}</h3>
              <p>
                <strong>{fr(profile.people, 0)} personnes</strong>
                {profile.mean_km != null ? ` · ${fr(profile.mean_km)} km en moyenne` : ""}
              </p>
              <p>{profile.reading}</p>
              {profile.homes && profile.homes.length > 0 && (
                <p>
                  Résidences :{" "}
                  {profile.homes.map((home) => `${home.name} (${home.headcount})`).join(", ")}
                </p>
              )}
              {profile.works && profile.works.length > 0 && (
                <p>
                  Lieux de travail :{" "}
                  {profile.works.map((work) => `${work.name} (${work.headcount})`).join(", ")}
                </p>
              )}
              {profile.organizations && profile.organizations.length > 0 && (
                <ul className="ia-limits">
                  {profile.organizations.map((org) => (
                    <li key={org.organization_name}>
                      <strong>{org.organization_name}</strong>
                      {org.example ? " — jeu d'exemple simulé" : ""} : {org.home_zones} quartiers,{" "}
                      {fr(org.people, 0)} personnes, {fr(org.mean_km)} km, vers {org.work.name}.
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>
      </section>

      <section id="ia-orgs" className="ia-section">
        <h2>Organisations</h2>
        <p>Pour chaque organisation : zones de résidence, zone de travail, flux et concentration.</p>
        <div className="ia-stack">
          {data.organizations.map((org) => (
            <article key={org.id} className={org.example ? "dash-card ia-example" : "dash-card"}>
              <h3>
                {org.name}
                {org.example ? " · jeu d'exemple" : ""}
              </h3>
              <p>
                {org.sector} · {fr(org.employees, 0)} employés simulés · siège à {org.seat_name} ·{" "}
                {fr(org.mean_km)} km en moyenne
              </p>
              <p>{org.concentration}</p>
              {org.corridor && <p>{org.corridor}</p>}
              <ul className="ia-limits">
                {org.homes.map((home) => (
                  <li key={home.name}>
                    {home.name} : {home.headcount} personnes ({Math.round(home.share * 100)} %),{" "}
                    {fr(home.distance_km)} km, {modeLabel(home.mode)}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="map-btn"
                onClick={() =>
                  onShowScenario({
                    title: `${org.name} → ${org.seat_name}`,
                    note: `Organisation simulée. ${org.concentration}`,
                    origins: org.homes,
                    destination: { name: org.seat_name, lon: org.seat_lon, lat: org.seat_lat },
                  })
                }
              >
                Voir les flux sur la carte
              </button>
            </article>
          ))}
        </div>
      </section>

      <section id="ia-detect" className="ia-section">
        <h2>Détection</h2>
        <div className="ia-detect">
          <DetectList
            title="Nœuds critiques"
            rows={data.detections.critical_nodes.map(
              (item) => `${item.name} · ${item.people} arrivées`
            )}
          />
          <article className="dash-card">
            <h3>Corridors</h3>
            {data.detections.corridors.length === 0 && <p>Aucun corridor au seuil retenu.</p>}
            <ul className="ia-limits">
              {data.detections.corridors.map((corridor) => (
                <li key={corridor.label}>
                  {corridor.label} · {corridor.people} personnes · {fr(corridor.mean_km)} km
                  {corridor.origins && corridor.destination && (
                    <button
                      type="button"
                      className="ia-text-btn"
                      onClick={() =>
                        onShowScenario({
                          title: corridor.label,
                          note: `Corridor simulé : ${corridor.label}.`,
                          origins: corridor.origins!,
                          destination: corridor.destination!,
                        })
                      }
                    >
                      Voir
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </article>
          <DetectList
            title="Forte génération"
            rows={data.detections.generation_zones.map(
              (item) => `${item.name} · ${item.people} départs${item.mean_km != null ? ` · ${fr(item.mean_km)} km` : ""}`
            )}
          />
          <DetectList
            title="Forte attractivité"
            rows={data.detections.attraction_zones.map(
              (item) => `${item.name} · ${item.people} arrivées`
            )}
          />
          <DetectList
            title="Déserts de mobilité"
            rows={data.detections.mobility_deserts.map(
              (item) => item.reading || `${item.name} · ${item.people} personnes`
            )}
          />
          <DetectList
            title="Déséquilibres emploi-habitat"
            rows={data.detections.emploi_habitat_imbalances.map(
              (item) =>
                `${item.name} · ${item.kind} · indice ${fr(item.eh_index)} · ${item.residents} résidents / ${item.jobs} emplois`
            )}
          />
        </div>
        <details>
          <summary>Seuils utilisés</summary>
          <ul className="ia-limits">
            {Object.entries(data.detections.thresholds).map(([key, text]) => (
              <li key={key}>{text}</li>
            ))}
          </ul>
        </details>
      </section>

      <section id="ia-scenarios" className="ia-section">
        <h2>Scénarios</h2>
        <p>
          Chaque fiche est un scénario recommandé ou un scénario potentiellement pertinent. Aucune
          n'est une solution optimale certaine. Les chiffres ne s'additionnent pas d'une fiche à
          l'autre.
        </p>
        <div className="ia-stack">
          {data.recommendations.map((scenario) => (
            <ScenarioCard
              key={`${scenario.kind}-${scenario.title}`}
              scenario={scenario}
              onShowScenario={onShowScenario}
            />
          ))}
        </div>
        {data.not_proposed.length > 0 && (
          <>
            <h3>Non proposés sur ce jeu</h3>
            <ul className="ia-limits">
              {data.not_proposed.map((item) => (
                <li key={item.kind}>
                  <strong>{KIND_LABEL[item.kind] ?? item.kind}.</strong> {item.reason}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section id="ia-exemple" className="ia-section">
        <h2>Exemple travaillé</h2>
        {!example && (
          <p>
            Le jeu d'exemple (30 employés à Ivato, 25 à Talatamaty, 20 à Ambohibao) est rattaché à
            Antananarivo. Il n'est pas dans le catalogue de {data.city}.
          </p>
        )}
        {example && (
          <article className="dash-card ia-example">
            <p className="ia-kicker">estimation simulée</p>
            <h3>{example.title}</h3>
            <p>{example.note}</p>
            <p>
              <strong>{example.organization_name}</strong> · siège à {example.seat_name}
            </p>
            <p>Corridor détecté : {example.corridor}</p>
            <ul className="ia-limits">
              {example.homes.map((home) => (
                <li key={home.name}>
                  {home.headcount} à {home.name} · {fr(home.distance_km)} km · {modeLabel(home.mode)}
                </li>
              ))}
            </ul>
            {example.scenario ? (
              <>
                <p>
                  Scénario associé : <StatusBadge scenario={example.scenario} /> {example.scenario.title}
                </p>
                <ImpactBlock
                  impact={example.scenario.impact}
                  tripsHint={tripsHintFor(example.scenario.kind)}
                />
                <p className="kpi-muted">{example.scenario.impact.assumptions}</p>
              </>
            ) : (
              <p>Le corridor est détecté. Aucun site du catalogue ne raccourcit ces navettes d'au moins 4 km.</p>
            )}
            {example.seat && (
              <button
                type="button"
                className="map-btn"
                onClick={() =>
                  onShowScenario({
                    title: example.scenario?.title ?? example.corridor,
                    note: "Jeu d'exemple simulé. Trait orange : vers le siège. Pointillé : vers le site proposé.",
                    origins: (example.scenario?.groups ?? example.homes).map((home) => ({
                      name: "home" in home ? home.home : home.name,
                      lon: home.lon,
                      lat: home.lat,
                      headcount: home.headcount,
                    })),
                    destination: example.seat!,
                    site: example.scenario?.site,
                  })
                }
              >
                Voir le corridor et le site proposé
              </button>
            )}
          </article>
        )}
      </section>
    </div>
  );
}

function DetectList({ title, rows }: { title: string; rows: string[] }) {
  return (
    <article className="dash-card">
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p>Aucun cas au seuil retenu.</p>
      ) : (
        <ul className="ia-limits">
          {rows.map((row) => (
            <li key={row}>{row}</li>
          ))}
        </ul>
      )}
    </article>
  );
}
