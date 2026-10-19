import type { LensPayload, PickMode } from "../lensTypes";
import {
  arrondissementLabel,
  bucketFlows,
  formatIndex,
  formatKm,
  formatMin,
  minutesFromKm,
  motifLabel,
  readingMode,
  tallyFlows,
  tallyModes,
  zoneFlags,
  zoneHeadline,
  type CorridorSide,
  type Motif,
} from "../lensReading";
import { readingNote } from "./Map/OdContextBar";
import { IndicatorList } from "./CatalogViews";
import "./LensPanel.css";

function ChartBars({
  rows,
  total,
  onPick,
  color = "#0284c7",
}: {
  rows: Array<{ id: string; name: string; people: number; pickId?: string }>;
  total: number;
  onPick: (id: string) => void;
  color?: string;
}) {
  if (!rows.length) return <p className="lens-muted">Aucun flux dans ce cadre.</p>;
  const max = Math.max(...rows.map((row) => row.people), 1);
  return (
    <ul className="lens-bars">
      {rows.map((row) => (
        <li key={row.id}>
          <div className="lens-bar-label">
            <button type="button" className="text" onClick={() => onPick(row.pickId ?? row.id)}>
              {row.name}
            </button>
            <em>
              {row.people.toLocaleString("fr-FR")} · {Math.round((row.people / total) * 100)} %
            </em>
          </div>
          <div className="lens-track">
            <span style={{ width: `${pct(row.people, max)}%`, background: color }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

type Props = {
  lens: LensPayload | null;
  loading: boolean;
  error: string | null;
  pickMode: PickMode;
  corridorSide: CorridorSide;
  motif: Motif;
  originIds: string[];
  destIds: string[];
  onPickMode: (mode: PickMode) => void;
  onCorridorSide: (side: CorridorSide) => void;
  onMotif: (motif: Motif) => void;
  onToggle: (id: string, mode: "origin" | "destination") => void;
  onClear: () => void;
};

function pct(value: number, max: number) {
  if (max <= 0 || value <= 0) return 0;
  return Math.max(8, Math.round((value / max) * 100));
}

function weightedKm(flows: LensPayload["flows"]): number | null {
  const total = flows.reduce((sum, flow) => sum + flow.headcount, 0);
  if (!total) return null;
  return flows.reduce((sum, flow) => sum + flow.km * flow.headcount, 0) / total;
}

export default function LensPanel({
  lens,
  loading,
  error,
  pickMode,
  corridorSide,
  motif,
  originIds,
  destIds,
  onPickMode,
  onCorridorSide,
  onMotif,
  onToggle,
  onClear,
}: Props) {
  if (error) {
    return (
      <section className="lens-panel">
        <h2>Lecture territoriale</h2>
        <p className="lens-error">{error}</p>
      </section>
    );
  }
  if (!lens) {
    return (
      <section className="lens-panel">
        <h2>Lecture territoriale</h2>
        <p className="lens-muted">{loading ? "Chargement des indices…" : "Aucune ville active."}</p>
      </section>
    );
  }

  const bothSides = originIds.length > 0 && destIds.length > 0;
  const frameFlows = lens.flows.filter(
    (flow) =>
      (originIds.length === 0 || originIds.includes(flow.origin_id)) &&
      (destIds.length === 0 || destIds.includes(flow.destination_id))
  );
  const maxFlow = frameFlows.reduce((max, flow) => Math.max(max, flow.headcount), 0);
  const selected = new Set([...originIds, ...destIds]);
  const groups = new Map<string, typeof lens.quartiers>();
  for (const quartier of lens.quartiers) {
    const list = groups.get(quartier.parent_name) ?? [];
    list.push(quartier);
    groups.set(quartier.parent_name, list);
  }
  const orgFlows = frameFlows.filter((flow) => flow.organization_name);
  const totalPeople = frameFlows.reduce((sum, flow) => sum + flow.headcount, 0) || 1;
  const headline = zoneHeadline(lens, pickMode, originIds, destIds);
  const destinations = tallyFlows(frameFlows, "destination_id", "destination_name").slice(0, 6);
  const origins = tallyFlows(frameFlows, "origin_id", "origin_name").slice(0, 6);
  const modes = tallyModes(frameFlows);
  const distanceBars = bucketFlows(frameFlows, [
    { id: "d1", name: "Moins de 3 km", test: (flow) => flow.km < 3 },
    { id: "d2", name: "3 à 8 km", test: (flow) => flow.km >= 3 && flow.km < 8 },
    { id: "d3", name: "8 à 15 km", test: (flow) => flow.km >= 8 && flow.km < 15 },
    { id: "d4", name: "Plus de 15 km", test: (flow) => flow.km >= 15 },
  ]);
  const timeBars = bucketFlows(frameFlows, [
    { id: "t1", name: "Moins de 15 min", test: (flow) => minutesFromKm(flow.km) < 15 },
    { id: "t2", name: "15 à 30 min", test: (flow) => minutesFromKm(flow.km) >= 15 && minutesFromKm(flow.km) < 30 },
    { id: "t3", name: "30 à 45 min", test: (flow) => minutesFromKm(flow.km) >= 30 && minutesFromKm(flow.km) < 45 },
    { id: "t4", name: "Plus de 45 min", test: (flow) => minutesFromKm(flow.km) >= 45 },
  ]);
  const ehPlaces = (selected.size
    ? lens.quartiers.filter((quartier) => selected.has(quartier.id))
    : [...lens.quartiers].sort((a, b) => (a.eh_index ?? 1) - (b.eh_index ?? 1)).slice(0, 6)
  ).map((quartier) => ({
    id: quartier.id,
    name: quartier.name,
    people: Math.round((quartier.eh_index ?? 0) * 100),
    label: formatIndex(quartier.eh_index),
  }));
  const indicatorZone = (originIds.length ? originIds : destIds).join(",");
  const listedPeople = frameFlows.reduce((sum, flow) => sum + flow.headcount, 0);
  const generated = motif === "travail" ? lens.indices.regular_workers : listedPeople;
  const corridorVolume = motif === "travail" ? lens.indices.regular_workers : listedPeople;
  const meanKm = motif === "travail" ? lens.indices.mean_km : weightedKm(frameFlows);
  const meanMin = meanKm === null ? null : minutesFromKm(meanKm);
  const mainDestination = destinations[0]?.name ?? "—";
  const mainOrigin = origins[0]?.name ?? "—";
  const questionTone = bothSides ? "corridor" : destIds.length && !originIds.length ? "destination" : "origin";

  return (
    <section className="lens-panel">
      <p className="lens-kicker">{lens.city.name}</p>
      <p className="lens-arrondissement">{arrondissementLabel(lens, originIds, destIds)}</p>
      <h2 className={`lens-zone ${questionTone}`}>{headline}</h2>
      <p className={`lens-question ${questionTone}`}>
        {readingNote(lens, pickMode, originIds, destIds, motif)}
      </p>
      <ul className="territory-pills">
        <li>Mode : {readingMode(pickMode, originIds.length, destIds.length)}</li>
        <li>Motif : {motifLabel(motif)}</li>
        <li>Données : SIMULÉES</li>
      </ul>
      <p className="lens-muted">{lens.scope_sentence}</p>

      <div className="territory-modes" role="group" aria-label="Mode de sélection">
        <button
          type="button"
          className={pickMode === "origin" ? "is-on origin" : undefined}
          onClick={() => onPickMode("origin")}
        >
          Origine
        </button>
        <button
          type="button"
          className={pickMode === "destination" ? "is-on destination" : undefined}
          onClick={() => onPickMode("destination")}
        >
          Destination
        </button>
        <button
          type="button"
          className={pickMode === "corridor" ? "is-on corridor" : undefined}
          onClick={() => onPickMode("corridor")}
        >
          O → D
        </button>
      </div>
      <div className="territory-modes" role="group" aria-label="Motif">
        <button type="button" className={motif === "travail" ? "is-on corridor" : undefined} onClick={() => onMotif("travail")}>
          Travail
        </button>
        <button type="button" className={motif === "tous" ? "is-on corridor" : undefined} onClick={() => onMotif("tous")}>
          Tous les motifs
        </button>
      </div>
      {pickMode === "corridor" && (
        <div className="territory-modes" role="group" aria-label="Côté du clic sur la carte">
          <button
            type="button"
            className={corridorSide === "origin" ? "is-on origin" : undefined}
            onClick={() => onCorridorSide("origin")}
          >
            Carte : origine
          </button>
          <button
            type="button"
            className={corridorSide === "destination" ? "is-on destination" : undefined}
            onClick={() => onCorridorSide("destination")}
          >
            Carte : destination
          </button>
        </div>
      )}

      {(originIds.length > 0 || destIds.length > 0) && (
        <div className="lens-chips">
          {originIds.map((id) => {
            const place = lens.quartiers.find((item) => item.id === id);
            return (
              <button key={`o-${id}`} type="button" className="chip origin" onClick={() => onToggle(id, "origin")}>
                Origine · {place?.name ?? id}
              </button>
            );
          })}
          {destIds.map((id) => {
            const place = lens.quartiers.find((item) => item.id === id);
            return (
              <button key={`d-${id}`} type="button" className="chip destination" onClick={() => onToggle(id, "destination")}>
                Destination · {place?.name ?? id}
              </button>
            );
          })}
          <button type="button" className="chip clear" onClick={onClear}>
            Effacer
          </button>
        </div>
      )}

      {bothSides && (
        <div className="lens-volume">
          <span>Volume du flux</span>
          <strong>{corridorVolume.toLocaleString("fr-FR")}</strong>
          <em>personnes · {motifLabel(motif).toLowerCase()}</em>
        </div>
      )}

      <div className="lens-metrics">
        <div>
          <span>Déplacements générés</span>
          <strong>{generated.toLocaleString("fr-FR")}</strong>
        </div>
        <div>
          <span>{questionTone === "destination" ? "Origine principale" : "Destination principale"}</span>
          <strong>{questionTone === "destination" ? mainOrigin : mainDestination}</strong>
        </div>
        <div>
          <span>Distance moyenne</span>
          <strong>{formatKm(meanKm)}</strong>
        </div>
        <div>
          <span>Temps moyen</span>
          <strong>{formatMin(meanMin)}</strong>
        </div>
        <div>
          <span>Indice emploi-habitat</span>
          <strong>{formatIndex(lens.indices.eh_index)}</strong>
        </div>
        <div>
          <span>Habitants / emplois</span>
          <strong>
            {lens.indices.residents.toLocaleString("fr-FR")} / {lens.indices.jobs.toLocaleString("fr-FR")}
          </strong>
        </div>
      </div>
      <h3>Flux principaux</h3>
      {frameFlows.length === 0 ? (
        <p className="lens-muted">Aucun flux pour cette sélection.</p>
      ) : (
        <ul className="lens-flows">
          {frameFlows.slice(0, 5).map((flow) => (
            <li key={`top-${flow.origin_id}-${flow.destination_id}-${flow.purpose}-${flow.organization_id ?? "h"}`}>
              <button type="button" onClick={() => onToggle(flow.origin_id, "origin")}>
                {flow.origin_name}
              </button>
              <span>→</span>
              <button type="button" onClick={() => onToggle(flow.destination_id, "destination")}>
                {flow.destination_name}
              </button>
              <em>{flow.headcount.toLocaleString("fr-FR")}</em>
            </li>
          ))}
        </ul>
      )}
      <p className="lens-note">{lens.indices.eh_sentence}</p>
      <p className="lens-muted">
        Temps estimé à 18 km/h, faute d’heure d’arrivée observée. Navettes travail :{" "}
        {lens.indices.regular_workers.toLocaleString("fr-FR")}. Hors travail :{" "}
        {lens.indices.regular_other.toLocaleString("fr-FR")}.{" "}
        {Math.round(lens.indices.outbound_share * 100)} % quittent le cadre pour travailler.
      </p>

      <h3>Graphiques du cadre</h3>
      <p className="lens-muted">Ils suivent le quartier cliqué, le mode et le motif.</p>
      <section className="lens-chart">
      <h3>Destinations principales</h3>
      <ChartBars rows={destinations} total={totalPeople} color="#c2410c" onPick={(id) => onToggle(id, "destination")} />
      </section>
      <section className="lens-chart">
      <h3>Origines principales</h3>
      <ChartBars rows={origins} total={totalPeople} color="#0f766e" onPick={(id) => onToggle(id, "origin")} />
      </section>
      <section className="lens-chart">
      <h3>Flux</h3>
      <ChartBars
        rows={frameFlows.slice(0, 6).map((flow) => ({
          id: `${flow.origin_id}|${flow.destination_id}|${flow.purpose}|${flow.organization_id ?? "h"}`,
          name: `${flow.origin_name} → ${flow.destination_name}`,
          people: flow.headcount,
          pickId: flow.destination_id,
        }))}
        total={totalPeople}
        color="#1d4ed8"
        onPick={(id) => onToggle(id, "destination")}
      />
      </section>
      <section className="lens-chart">
      <h3>Distance</h3>
      <ChartBars rows={distanceBars} total={totalPeople} color="#475569" onPick={() => undefined} />
      </section>
      <section className="lens-chart">
      <h3>Temps</h3>
      <ChartBars rows={timeBars} total={totalPeople} color="#7c3aed" onPick={() => undefined} />
      </section>
      <section className="lens-chart">
      <h3>Emploi-habitat</h3>
      <ul className="lens-bars">
        {ehPlaces.map((row) => (
          <li key={row.id}>
            <div className="lens-bar-label">
              <button type="button" className="text" onClick={() => onToggle(row.id, pickMode === "destination" ? "destination" : "origin")}>
                {row.name}
              </button>
              <em>{row.label}</em>
            </div>
            <div className="lens-track">
              <span style={{ width: `${Math.max(8, Math.min(100, row.people))}%`, background: row.people < 45 ? "#b91c1c" : row.people < 75 ? "#d97706" : "#0f766e" }} />
            </div>
          </li>
        ))}
      </ul>
      </section>
      <section className="lens-chart">
      <h3>Modes de transport</h3>
      <ChartBars rows={modes} total={totalPeople} color="#0369a1" onPick={() => undefined} />
      </section>

      <h3>Indices du cadre</h3>
      <IndicatorList
        city={lens.city.name}
        zone={indicatorZone}
        mode={pickMode === "destination" ? "destination" : "origine"}
      />

      <h3>Déplacements</h3>
      {frameFlows.length === 0 ? (
        <p className="lens-muted">Aucun déplacement régulier pour cette sélection.</p>
      ) : (
        <ul className="lens-bars">
          {frameFlows.slice(0, 8).map((flow) => (
            <li key={`${flow.origin_id}-${flow.destination_id}-${flow.purpose}-${flow.organization_id ?? "h"}`}>
              <div className="lens-bar-label">
                <button type="button" className="text origin" onClick={() => onToggle(flow.origin_id, "origin")}>
                  {flow.origin_name}
                </button>
                <span>→</span>
                <button type="button" className="text destination" onClick={() => onToggle(flow.destination_id, "destination")}>
                  {flow.destination_name}
                </button>
                <em>{flow.headcount}</em>
              </div>
              <div className="lens-track">
                <span
                  style={{
                    width: `${pct(flow.headcount, maxFlow)}%`,
                    background: flow.purpose === "travail" ? "#0369a1" : "#6d28d9",
                  }}
                />
              </div>
              <p>
                {flow.purpose_label} · {flow.cadence} · {flow.km} km ·{" "}
                {Math.round((flow.km / 18) * 60)} min · {flow.mode}
                {flow.organization_name ? ` · ${flow.organization_name}` : ""} ·{" "}
                {Math.round((flow.headcount / totalPeople) * 100)} % du cadre. Estimation simulée.
              </p>
            </li>
          ))}
        </ul>
      )}

      <h3>Pourquoi ce trajet, et ce qu’il y a sur place</h3>
      <ul className="lens-why">
        {frameFlows.slice(0, 5).map((flow) => (
          <li key={`why-${flow.origin_id}-${flow.destination_id}-${flow.purpose}-${flow.organization_id ?? "h"}`}>
            <strong>
              {flow.origin_name} → {flow.destination_name}
            </strong>
            <p>{flow.why}</p>
            <p className="lens-muted">Sur place : {flow.inside}</p>
          </li>
        ))}
      </ul>

      {lens.purposes.length > 0 && (
        <>
          <h3>Motifs réguliers</h3>
          <ul className="lens-purposes">
            {lens.purposes.map((item) => (
              <li key={item.label}>
                <span>{item.label}</span>
                <strong>{item.people.toLocaleString("fr-FR")}</strong>
              </li>
            ))}
          </ul>
        </>
      )}

      {orgFlows.length > 0 && (
        <>
          <h3>Organisations</h3>
          <ul className="lens-why">
            {orgFlows.slice(0, 6).map((flow) => (
              <li key={`org-${flow.organization_id}-${flow.origin_id}`}>
                <strong>
                  {flow.organization_name} · {flow.headcount} employés
                </strong>
                <p>
                  Habitent {flow.origin_name} ({flow.origin_parent_name}) et travaillent à{" "}
                  {flow.destination_name}.
                </p>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Zones d’accueil pour raccourcir les navettes</h3>
      {lens.relocations.length === 0 ? (
        <p className="lens-muted">
          Pas de zone d’emploi assez proche pour déplacer un groupe sans allonger d’autres trajets.
        </p>
      ) : (
        <ul className="lens-why">
          {lens.relocations.map((item) => (
            <li key={`${item.organization_name}-${item.home_name}-${item.empty_zone_id}`}>
              <strong>
                {item.organization_name} · {item.headcount} employés vers {item.empty_zone_name}
              </strong>
              <p>{item.text}</p>
              <button type="button" className="text destination" onClick={() => onToggle(item.empty_zone_id, "destination")}>
                Voir {item.empty_zone_name}
              </button>
            </li>
          ))}
        </ul>
      )}

      <h3>Indices par quartier</h3>
      <p className="lens-muted">
        Cochez autant d’origines et de destinations que vous voulez. O et D peuvent être cochées ensemble.
        Vert : origine. Orange : destination. Un second clic retire le quartier.
      </p>
      {[...groups.entries()].map(([parent, quartiers]) => (
        <div key={parent} className="lens-group">
          <h4>{parent}</h4>
          <ul>
            {quartiers.map((quartier) => {
              const origin = originIds.includes(quartier.id);
              const dest = destIds.includes(quartier.id);
              const flags = zoneFlags(quartier);
              return (
                <li key={quartier.id} className={selected.has(quartier.id) ? "is-selected" : undefined}>
                  <label className="lens-check origin">
                    <input
                      type="checkbox"
                      checked={origin}
                      aria-label={`Origine ${quartier.name}`}
                      onChange={() => onToggle(quartier.id, "origin")}
                    />
                    O
                  </label>
                  <label className="lens-check destination">
                    <input
                      type="checkbox"
                      checked={dest}
                      aria-label={`Destination ${quartier.name}`}
                      onChange={() => onToggle(quartier.id, "destination")}
                    />
                    D
                  </label>
                  <span>
                    {quartier.name}
                    <small>
                      {" "}
                      · {quartier.role_label}
                      {origin ? " · origine" : ""}
                      {dest ? " · destination" : ""}
                      {flags.critical ? " · zone critique" : ""}
                      {flags.desert ? " · désert de mobilité" : ""}
                    </small>
                  </span>
                  <em>
                    {quartier.residents} hab. · {quartier.jobs} emp. · EH {formatIndex(quartier.eh_index)}
                  </em>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      <p className="lens-foot">{lens.note}</p>
    </section>
  );
}
