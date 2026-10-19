import { useEffect, useState } from "react";
import {
  FLOW_CATALOG_LIMIT,
  FLOW_PAGE_SIZE,
  TRIP_PAGE_SIZE,
  fetchCohortFlows,
  fetchCohortMeta,
  fetchCohortOverview,
  fetchCohortTrips,
  readCohortError,
} from "../cohort/api";
import type {
  CohortFlow,
  CohortFlows,
  CohortMeta,
  CohortOverview,
  CohortQuery,
  CohortTrips,
  DateShare,
  ModeShare,
  PurposeShare,
} from "../cohort/types";
import "./CohortView.css";

type Filters = {
  date_from: string;
  date_to: string;
  mode: string;
  purpose: string;
  origin_id: string;
  destination_id: string;
};

type PlaceOption = { id: string; name: string };

const EMPTY_FILTERS: Filters = {
  date_from: "",
  date_to: "",
  mode: "",
  purpose: "",
  origin_id: "",
  destination_id: "",
};

const PERIOD_LABELS: Record<string, string> = {
  stored_trip_dates: "dates de trajets stockées",
  request: "période demandée",
  empty_window: "fenêtre sans trajet",
  unavailable: "période indisponible",
};

function fmtCount(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
}

function fmtDecimal(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function fmtMeasure(value: number | null | undefined, unit: string): string {
  if (value == null) return "—";
  const base = `${fmtDecimal(value)} ${unit}`;
  if (unit === "min" && value >= 60) {
    const hours = (value / 60).toLocaleString("fr-FR", { maximumFractionDigits: 1 });
    return `${base} (${hours} h)`;
  }
  return base;
}

function fmtIsoDate(value: string | null | undefined): string {
  if (!value) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return value;
  return `${match[3]}/${match[2]}/${match[1]}`;
}

function shortIsoDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return value;
  return `${match[3]}/${match[2]}`;
}

function fmtTime(value: string): string {
  const match = /^(\d{2}):(\d{2})/.exec(value);
  if (!match) return value;
  return `${match[1]}:${match[2]}`;
}

function shareLabel(count: number, total: number): string {
  const base = fmtCount(count);
  if (total <= 0) return base;
  const percent = ((count / total) * 100).toLocaleString("fr-FR", {
    maximumFractionDigits: 1,
  });
  return `${base} · ${percent} %`;
}

function attributeQuery(filters: Filters): CohortQuery {
  return {
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    mode: filters.mode || undefined,
    purpose: filters.purpose || undefined,
  };
}

function placeQuery(filters: Filters): CohortQuery {
  return {
    ...attributeQuery(filters),
    origin_id: filters.origin_id || undefined,
    destination_id: filters.destination_id || undefined,
  };
}

function placeOptions(flows: CohortFlow[], side: "origin" | "destination"): PlaceOption[] {
  const byId = new Map<string, string>();
  for (const flow of flows) {
    const id = side === "origin" ? flow.origin_place_id : flow.destination_place_id;
    const name = side === "origin" ? flow.origin_name : flow.destination_name;
    if (!byId.has(id)) byId.set(id, name);
  }
  const nameCount = new Map<string, number>();
  for (const name of byId.values()) nameCount.set(name, (nameCount.get(name) ?? 0) + 1);
  return [...byId.entries()]
    .map(([id, name]) => ({
      id,
      name: (nameCount.get(name) ?? 0) > 1 ? `${name} (${id})` : name,
    }))
    .sort((a, b) => a.name.localeCompare(b.name, "fr"));
}

function filtersActive(filters: Filters): boolean {
  return Object.values(filters).some((value) => value !== "");
}

function HBars({
  rows,
  total,
  colorClass,
}: {
  rows: Array<{ key: string; label: string; trip_count: number }>;
  total: number;
  colorClass?: string;
}) {
  if (rows.length === 0) {
    return <p className="cohort-empty">Aucun trajet pour cette répartition.</p>;
  }
  const max = Math.max(...rows.map((row) => row.trip_count), 0);
  return (
    <ul className="cohort-hbars">
      {rows.map((row) => (
        <li key={row.key} title={`${row.label} : ${fmtCount(row.trip_count)} trajets`}>
          <span className="cohort-hlabel">{row.label}</span>
          <span className="cohort-htrack">
            <span
              className={colorClass}
              style={{ width: max > 0 ? `${(row.trip_count / max) * 100}%` : "0%" }}
            />
          </span>
          <span className="cohort-hval">{shareLabel(row.trip_count, total)}</span>
        </li>
      ))}
    </ul>
  );
}

function DateChart({ points }: { points: DateShare[] }) {
  if (points.length === 0) {
    return <p className="cohort-empty">Aucune date avec trajet pour ces filtres.</p>;
  }
  const max = Math.max(...points.map((point) => point.trip_count), 0);
  const dense = points.length > 16;
  return (
    <div className="cohort-vscroll">
      <div className="cohort-vbars" style={{ minWidth: points.length * 32 }}>
        {points.map((point, index) => (
          <div
            key={point.trip_date}
            className="cohort-vcol"
            title={`${fmtIsoDate(point.trip_date)} : ${fmtCount(point.trip_count)} trajets`}
          >
            {!dense && <span className="cohort-vval">{fmtCount(point.trip_count)}</span>}
            <div className="cohort-vtrack">
              <span style={{ height: max > 0 ? `${(point.trip_count / max) * 100}%` : "0%" }} />
            </div>
            <span className="cohort-vlab">
              {dense && index % 4 !== 0 ? "" : shortIsoDate(point.trip_date)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModeCompare({
  rows,
  distanceUnit,
  durationUnit,
}: {
  rows: ModeShare[];
  distanceUnit: string;
  durationUnit: string;
}) {
  if (rows.length === 0) {
    return <p className="cohort-empty">Aucun mode pour cette comparaison.</p>;
  }
  const maxDistance = Math.max(...rows.map((row) => row.distance_km), 0);
  const maxDuration = Math.max(...rows.map((row) => row.duration_min), 0);
  return (
    <div className="cohort-compare">
      {rows.map((row) => (
        <div key={row.mode_code}>
          <h3>{row.label}</h3>
          <ul className="cohort-hbars">
            <li title={`${row.label} : ${fmtMeasure(row.distance_km, distanceUnit)}`}>
              <span className="cohort-hlabel">Distance</span>
              <span className="cohort-htrack">
                <span
                  className="distance"
                  style={{
                    width: maxDistance > 0 ? `${(row.distance_km / maxDistance) * 100}%` : "0%",
                  }}
                />
              </span>
              <span className="cohort-hval">{fmtMeasure(row.distance_km, distanceUnit)}</span>
            </li>
            <li title={`${row.label} : ${fmtMeasure(row.duration_min, durationUnit)}`}>
              <span className="cohort-hlabel">Durée</span>
              <span className="cohort-htrack">
                <span
                  className="duration"
                  style={{
                    width: maxDuration > 0 ? `${(row.duration_min / maxDuration) * 100}%` : "0%",
                  }}
                />
              </span>
              <span className="cohort-hval">{fmtMeasure(row.duration_min, durationUnit)}</span>
            </li>
          </ul>
        </div>
      ))}
    </div>
  );
}

function Pager({
  offset,
  limit,
  total,
  disabled,
  onOffset,
}: {
  offset: number;
  limit: number;
  total: number;
  disabled: boolean;
  onOffset: (offset: number) => void;
}) {
  if (total <= 0) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="cohort-pager">
      <button
        type="button"
        disabled={disabled || offset <= 0}
        onClick={() => onOffset(Math.max(0, offset - limit))}
      >
        Précédent
      </button>
      <span>
        {fmtCount(from)}–{fmtCount(to)} sur {fmtCount(total)}
      </span>
      <button
        type="button"
        disabled={disabled || offset + limit >= total}
        onClick={() => onOffset(offset + limit)}
      >
        Suivant
      </button>
    </div>
  );
}

function MetaCard({
  meta,
  loading,
  error,
}: {
  meta: CohortMeta | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <section className="cohort-meta" aria-busy={loading}>
      <h2>Métadonnées du jeu</h2>
      {loading && !meta && <p className="cohort-muted">Chargement des métadonnées…</p>}
      {error && (
        <p className="cohort-error" role="alert">
          {error}
        </p>
      )}
      {meta && (
        <>
          <p>{meta.label}</p>
          <dl className="cohort-facts">
            <div>
              <dt>Jeu</dt>
              <dd>{meta.dataset_id}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{meta.source}</dd>
            </div>
            <div>
              <dt>Statut</dt>
              <dd>{meta.data_status}</dd>
            </div>
            <div>
              <dt>Début des trajets</dt>
              <dd>{fmtIsoDate(meta.first_trip_date)}</dd>
            </div>
            <div>
              <dt>Fin des trajets</dt>
              <dd>{fmtIsoDate(meta.last_trip_date)}</dd>
            </div>
            <div>
              <dt>Lundi d’ancrage</dt>
              <dd>{fmtIsoDate(meta.anchor_monday)}</dd>
            </div>
            <div>
              <dt>Personnes</dt>
              <dd>{fmtCount(meta.person_count)}</dd>
            </div>
            <div>
              <dt>Trajets</dt>
              <dd>{fmtCount(meta.trip_count)}</dd>
            </div>
            <div>
              <dt>Graine</dt>
              <dd>{meta.seed == null ? "Non renseignée" : String(meta.seed)}</dd>
            </div>
            <div>
              <dt>Méthode des distances</dt>
              <dd>{meta.distance_method}</dd>
            </div>
          </dl>
          <p>{meta.horizon_note}</p>
          <p>{meta.caveat}</p>
        </>
      )}
    </section>
  );
}

export default function CohortView() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [flowOffset, setFlowOffset] = useState(0);
  const [tripOffset, setTripOffset] = useState(0);
  const [meta, setMeta] = useState<CohortMeta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [catalog, setCatalog] = useState<CohortOverview | null>(null);
  const [overview, setOverview] = useState<CohortOverview | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [placeCatalog, setPlaceCatalog] = useState<CohortFlows | null>(null);
  const [placeError, setPlaceError] = useState<string | null>(null);
  const [flows, setFlows] = useState<CohortFlows | null>(null);
  const [flowsError, setFlowsError] = useState<string | null>(null);
  const [flowsLoading, setFlowsLoading] = useState(true);
  const [trips, setTrips] = useState<CohortTrips | null>(null);
  const [tripsError, setTripsError] = useState<string | null>(null);
  const [tripsLoading, setTripsLoading] = useState(true);

  const patchFilters = (patch: Partial<Filters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setFlowOffset(0);
    setTripOffset(0);
  };

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setMetaLoading(true);
    setMetaError(null);
    fetchCohortMeta(controller.signal)
      .then((data) => {
        if (!active) return;
        setMeta(data);
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = readCohortError(error, "Métadonnées indisponibles.");
        if (!message) return;
        setMeta(null);
        setMetaError(message);
      })
      .finally(() => {
        if (active) setMetaLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const dates = attributeQuery({ ...filters, mode: "", purpose: "" });
    const scoped = attributeQuery(filters);
    const same = !filters.mode && !filters.purpose;
    setOverviewLoading(true);
    setOverviewError(null);
    setOverview(null);
    const catalogRequest = fetchCohortOverview(dates, controller.signal);
    const displayRequest = same
      ? catalogRequest
      : fetchCohortOverview(scoped, controller.signal);
    Promise.all([catalogRequest, displayRequest])
      .then(([nextCatalog, nextOverview]) => {
        if (!active) return;
        setCatalog(nextCatalog);
        setOverview(nextOverview);
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = readCohortError(error, "Indicateurs indisponibles.");
        if (!message) return;
        setOverview(null);
        setOverviewError(message);
      })
      .finally(() => {
        if (active) setOverviewLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters.date_from, filters.date_to, filters.mode, filters.purpose]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setPlaceError(null);
    fetchCohortFlows(
      attributeQuery(filters),
      { limit: FLOW_CATALOG_LIMIT, offset: 0 },
      controller.signal,
    )
      .then((data) => {
        if (!active) return;
        setPlaceCatalog(data);
        if (data.pair_count === data.returned) {
          const origins = new Set(data.flows.map((flow) => flow.origin_place_id));
          const destinations = new Set(data.flows.map((flow) => flow.destination_place_id));
          setFilters((prev) => {
            const originGone = prev.origin_id !== "" && !origins.has(prev.origin_id);
            const destinationGone =
              prev.destination_id !== "" && !destinations.has(prev.destination_id);
            if (!originGone && !destinationGone) return prev;
            return {
              ...prev,
              origin_id: originGone ? "" : prev.origin_id,
              destination_id: destinationGone ? "" : prev.destination_id,
            };
          });
        }
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = readCohortError(error, "Liste des lieux indisponible.");
        if (!message) return;
        setPlaceCatalog(null);
        setPlaceError(message);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters.date_from, filters.date_to, filters.mode, filters.purpose]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setFlowsLoading(true);
    setFlowsError(null);
    setFlows(null);
    fetchCohortFlows(
      placeQuery(filters),
      { limit: FLOW_PAGE_SIZE, offset: flowOffset },
      controller.signal,
    )
      .then((data) => {
        if (!active) return;
        setFlows(data);
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = readCohortError(error, "Flux indisponibles.");
        if (!message) return;
        setFlows(null);
        setFlowsError(message);
      })
      .finally(() => {
        if (active) setFlowsLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters, flowOffset]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setTripsLoading(true);
    setTripsError(null);
    setTrips(null);
    fetchCohortTrips(
      placeQuery(filters),
      { limit: TRIP_PAGE_SIZE, offset: tripOffset },
      controller.signal,
    )
      .then((data) => {
        if (!active) return;
        setTrips(data);
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = readCohortError(error, "Trajets indisponibles.");
        if (!message) return;
        setTrips(null);
        setTripsError(message);
      })
      .finally(() => {
        if (active) setTripsLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters, tripOffset]);

  const modes = catalog?.by_mode ?? [];
  const purposes = catalog?.by_purpose ?? [];
  const origins = placeCatalog ? placeOptions(placeCatalog.flows, "origin") : [];
  const destinations = placeCatalog ? placeOptions(placeCatalog.flows, "destination") : [];
  const placesTruncated =
    placeCatalog != null && placeCatalog.pair_count > placeCatalog.returned;
  const periodLabel = overview
    ? PERIOD_LABELS[overview.period.period_source] ?? overview.period.period_source
    : null;
  const noTrips = overview != null && overview.trip_count === 0;
  const datasetEmpty = meta != null && meta.trip_count === 0 && meta.person_count === 0;

  return (
    <div className="cohort-page">
      <p className="cohort-banner" role="status">
        Données simulées — ne représentent pas une enquête réelle
      </p>

      <section className="cohort-sources">
        <h2>Source de cette vue</h2>
        <ul>
          <li>
            <strong>sim-cohort</strong> — personnes et trajets individuels simulés. Tous les
            indicateurs, graphiques, flux et trajets de cette page viennent de{" "}
            <code>/api/mobility/cohort</code>.
          </li>
          <li>
            <strong>diary-week</strong> — journal de mobilité de la vue Déplacements. Non inclus.
          </li>
          <li>
            <strong>mobility_flows</strong> — flux origine-destination de la carte. Non inclus.
          </li>
          <li>
            <strong>sim_trips</strong> et les autres tables <strong>sim_*</strong> — simulation de
            groupe de la vue Simulation. Non incluses.
          </li>
        </ul>
      </section>

      <MetaCard meta={meta} loading={metaLoading} error={metaError} />

      {datasetEmpty && (
        <p className="cohort-empty" role="status">
          Le jeu sim-cohort ne contient aucune personne ni aucun trajet.
        </p>
      )}

      <form
        className="cohort-filters"
        aria-label="Filtres de la cohorte simulée"
        onSubmit={(event) => event.preventDefault()}
      >
        <label className="field">
          Début
          <input
            type="date"
            value={filters.date_from}
            onChange={(event) => patchFilters({ date_from: event.target.value })}
          />
        </label>
        <label className="field">
          Fin
          <input
            type="date"
            value={filters.date_to}
            onChange={(event) => patchFilters({ date_to: event.target.value })}
          />
        </label>
        <label className="field">
          Mode
          <select
            value={filters.mode}
            onChange={(event) => patchFilters({ mode: event.target.value })}
          >
            <option value="">Tous les modes</option>
            {modes.map((mode) => (
              <option key={mode.mode_code} value={mode.mode_code}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Motif
          <select
            value={filters.purpose}
            onChange={(event) => patchFilters({ purpose: event.target.value })}
          >
            <option value="">Tous les motifs</option>
            {purposes.map((purpose) => (
              <option key={purpose.purpose_code} value={purpose.purpose_code}>
                {purpose.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Origine
          <select
            value={filters.origin_id}
            onChange={(event) => patchFilters({ origin_id: event.target.value })}
          >
            <option value="">Toutes les origines</option>
            {origins.map((place) => (
              <option key={place.id} value={place.id}>
                {place.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Destination
          <select
            value={filters.destination_id}
            onChange={(event) => patchFilters({ destination_id: event.target.value })}
          >
            <option value="">Toutes les destinations</option>
            {destinations.map((place) => (
              <option key={place.id} value={place.id}>
                {place.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="cohort-reset"
          onClick={() => {
            setFilters(EMPTY_FILTERS);
            setFlowOffset(0);
            setTripOffset(0);
          }}
        >
          Réinitialiser
        </button>
      </form>
      <p className="cohort-muted">
        {overviewLoading && "Actualisation des indicateurs…"}
        {!overviewLoading && overview && (
          <>
            Période lue : {fmtIsoDate(overview.period.date_from)} –{" "}
            {fmtIsoDate(overview.period.date_to)}
            {overview.period.calendar_days != null
              ? ` · ${fmtCount(overview.period.calendar_days)} jours`
              : ""}
            {periodLabel ? ` · ${periodLabel}` : ""}. Les dates vides restent dans le calendrier
            des journées sans déplacement, mais n’apparaissent pas dans le graphique journalier.
          </>
        )}
        {placeError && ` Liste des lieux : ${placeError}`}
        {placesTruncated &&
          " La liste des lieux ne couvre que la première page de couples renvoyée par l’API."}
      </p>
      <p className="cohort-muted">
        L’origine et la destination filtrent les flux et le tableau des trajets. Les indicateurs
        et les graphiques suivent la période, le mode et le motif.
      </p>

      <section aria-busy={overviewLoading} aria-label="Indicateurs de la cohorte">
        {overviewError && (
          <p className="cohort-error" role="alert">
            {overviewError}
          </p>
        )}
        {overviewLoading && !overview && !overviewError && (
          <p className="cohort-muted">Chargement des indicateurs…</p>
        )}
        {noTrips && (
          <p className="cohort-empty" role="status">
            {filtersActive(filters)
              ? "Aucun trajet pour ces filtres."
              : "Aucun trajet sur la période renvoyée par l’API."}
          </p>
        )}
        {overview && (
          <>
            <div className="cohort-kpis">
              <article className="cohort-kpi">
                <span>Personnes</span>
                <strong>{fmtCount(overview.person_count)}</strong>
                <em>Effectif du jeu. Le mode et le motif ne le modifient pas.</em>
              </article>
              <article className="cohort-kpi">
                <span>Trajets</span>
                <strong>{fmtCount(overview.trip_count)}</strong>
              </article>
              <article className="cohort-kpi">
                <span>Distance totale</span>
                <strong>{fmtMeasure(overview.distance_km, overview.distance_unit)}</strong>
              </article>
              <article className="cohort-kpi">
                <span>Durée totale</span>
                <strong>{fmtMeasure(overview.duration_min, overview.duration_unit)}</strong>
              </article>
              <article className="cohort-kpi">
                <span>Distance moyenne par trajet</span>
                <strong>
                  {fmtMeasure(overview.average_distance_km, overview.distance_unit)}
                </strong>
              </article>
              <article className="cohort-kpi">
                <span>Durée moyenne par trajet</span>
                <strong>
                  {fmtMeasure(overview.average_duration_min, overview.duration_unit)}
                </strong>
              </article>
              <article className="cohort-kpi">
                <span>Journées-personnes sans déplacement</span>
                <strong>{fmtCount(overview.empty_person_days)}</strong>
                <em>{overview.empty_person_days_rule}</em>
              </article>
              <article className="cohort-kpi">
                <span>Journées-personnes avec au moins un trajet</span>
                <strong>{fmtCount(overview.active_person_days)}</strong>
              </article>
            </div>
            <p className="cohort-muted">{overview.caveat}</p>

            <div className="cohort-charts">
              <article className="cohort-chart cohort-chart-mode">
                <h2>Trajets par mode</h2>
                <p>Unité : nombre de trajets. La part est calculée sur les trajets filtrés.</p>
                <HBars
                  rows={overview.by_mode.map((row: ModeShare) => ({
                    key: row.mode_code,
                    label: row.label,
                    trip_count: row.trip_count,
                  }))}
                  total={overview.trip_count}
                />
              </article>
              <article className="cohort-chart cohort-chart-purpose">
                <h2>Trajets par motif</h2>
                <p>Unité : nombre de trajets. La part est calculée sur les trajets filtrés.</p>
                <HBars
                  rows={overview.by_purpose.map((row: PurposeShare) => ({
                    key: row.purpose_code,
                    label: row.label,
                    trip_count: row.trip_count,
                  }))}
                  total={overview.trip_count}
                  colorClass="purpose"
                />
              </article>
              <article className="cohort-chart cohort-chart-date cohort-wide">
                <h2>Trajets par date</h2>
                <p>
                  Unité : nombre de trajets. Seules les dates renvoyées par l’API, donc celles
                  qui ont au moins un trajet, sont affichées.
                </p>
                <DateChart points={overview.by_date} />
              </article>
              <article className="cohort-chart cohort-chart-compare cohort-wide">
                <h2>Distance et durée par mode</h2>
                <p>
                  Deux échelles distinctes : distance en {overview.distance_unit}, durée en{" "}
                  {overview.duration_unit}. Méthode : {overview.distance_method}.
                </p>
                <div className="cohort-legend">
                  <span>
                    <i style={{ background: "#a78bfa" }} /> Distance ({overview.distance_unit})
                  </span>
                  <span>
                    <i style={{ background: "#fb923c" }} /> Durée ({overview.duration_unit})
                  </span>
                </div>
                <ModeCompare
                  rows={overview.by_mode}
                  distanceUnit={overview.distance_unit}
                  durationUnit={overview.duration_unit}
                />
              </article>
            </div>
          </>
        )}
      </section>

      <section className="cohort-table-card" aria-busy={flowsLoading}>
        <h2>Flux origine-destination</h2>
        <p>
          Couples de lieux de sim-cohort, triés par l’API. Ce ne sont pas des itinéraires
          routiers : les distances sont simulées ({flows?.distance_method ?? overview?.distance_method ?? "méthode indiquée par l’API"})
          et ne viennent pas de pgRouting. Ils ne sont pas dessinés sur la carte, qui affiche
          les flux <code>mobility_flows</code> de la ville courante. Cette cohorte couvre
          plusieurs villes.
        </p>
        {flows?.caveat && <p>{flows.caveat}</p>}
        {flowsLoading && <p className="cohort-muted">Chargement des flux…</p>}
        {flowsError && (
          <p className="cohort-error" role="alert">
            {flowsError}
          </p>
        )}
        {flows && flows.flows.length === 0 && (
          <p className="cohort-empty" role="status">
            Aucun couple origine-destination pour ces filtres.
          </p>
        )}
        {flows && flows.flows.length > 0 && (
          <div className="cohort-table-wrap">
            <table className="cohort-table">
              <thead>
                <tr>
                  <th scope="col">Origine</th>
                  <th scope="col">Destination</th>
                  <th scope="col" className="num">
                    Trajets
                  </th>
                  <th scope="col" className="num">
                    Distance ({flows.distance_unit})
                  </th>
                  <th scope="col" className="num">
                    Durée ({flows.duration_unit})
                  </th>
                </tr>
              </thead>
              <tbody>
                {flows.flows.map((flow) => (
                  <tr key={`${flow.origin_place_id}-${flow.destination_place_id}`}>
                    <td title={flow.origin_place_id}>{flow.origin_name}</td>
                    <td title={flow.destination_place_id}>{flow.destination_name}</td>
                    <td className="num">{fmtCount(flow.trip_count)}</td>
                    <td className="num">{fmtDecimal(flow.distance_km)}</td>
                    <td className="num">{fmtMeasure(flow.duration_min, flows.duration_unit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {flows && (
          <Pager
            offset={flows.offset}
            limit={flows.limit}
            total={flows.pair_count}
            disabled={flowsLoading}
            onOffset={setFlowOffset}
          />
        )}
      </section>

      <section className="cohort-table-card" aria-busy={tripsLoading}>
        <h2>Trajets simulés</h2>
        <p>
          Page demandée à l’API, au plus {TRIP_PAGE_SIZE} lignes.{" "}
          {trips?.exposure ?? "Pseudonyme, lieux et étape. Pas de nom affichable."}
        </p>
        {tripsLoading && <p className="cohort-muted">Chargement des trajets…</p>}
        {tripsError && (
          <p className="cohort-error" role="alert">
            {tripsError}
          </p>
        )}
        {trips && trips.trips.length === 0 && (
          <p className="cohort-empty" role="status">
            Aucun trajet pour ces filtres.
          </p>
        )}
        {trips && trips.trips.length > 0 && (
          <div className="cohort-table-wrap">
            <table className="cohort-table">
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Départ</th>
                  <th scope="col">Arrivée</th>
                  <th scope="col">Origine</th>
                  <th scope="col">Destination</th>
                  <th scope="col">Motif</th>
                  <th scope="col">Mode</th>
                  <th scope="col" className="num">
                    Distance ({trips.distance_unit})
                  </th>
                  <th scope="col" className="num">
                    Durée ({trips.duration_unit})
                  </th>
                  <th scope="col">Pseudonyme</th>
                </tr>
              </thead>
              <tbody>
                {trips.trips.map((trip) => (
                  <tr key={trip.trip_id}>
                    <td>{fmtIsoDate(trip.trip_date)}</td>
                    <td>{fmtTime(trip.depart_time)}</td>
                    <td>{fmtTime(trip.arrive_time)}</td>
                    <td>{trip.origin_name}</td>
                    <td>{trip.destination_name}</td>
                    <td>{trip.purpose_label}</td>
                    <td>{trip.mode_label}</td>
                    <td className="num">{fmtDecimal(trip.distance_km)}</td>
                    <td className="num">{fmtMeasure(trip.duration_min, trips.duration_unit)}</td>
                    <td>{trip.person_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {trips && (
          <Pager
            offset={trips.offset}
            limit={trips.limit}
            total={trips.total}
            disabled={tripsLoading}
            onOffset={setTripOffset}
          />
        )}
      </section>
    </div>
  );
}
