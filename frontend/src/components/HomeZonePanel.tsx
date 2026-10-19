import { useState } from "react";
import type { ReactNode } from "react";
import type { LensPayload } from "../lensTypes";
import { tallyModes } from "../lensReading";
import "./HomeZonePanel.css";

type Props = {
  lens: LensPayload | null;
  loading: boolean;
  error: string | null;
  originIds: string[];
  onSelectZone: (id: string) => void;
  onClear: () => void;
  matrix?: ReactNode;
};

const MODE_COLOR: Record<string, string> = {
  bus: "#3b82f6",
  marche: "#22c55e",
  walk: "#22c55e",
  voiture: "#f97316",
  car: "#f97316",
  moto: "#ef4444",
  taxi: "#eab308",
  velo: "#14b8a6",
  bike: "#14b8a6",
};

function fmt(value: number, digits = 0) {
  return value.toLocaleString("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export default function HomeZonePanel({
  lens,
  loading,
  error,
  originIds,
  onSelectZone,
  onClear,
  matrix,
}: Props) {
  const [tab, setTab] = useState<"zone" | "flux">("zone");

  if (error) {
    return (
      <section className="zone-sheet">
        <h2>Zone</h2>
        <p className="zone-sheet-error">{error}</p>
      </section>
    );
  }
  if (!lens) {
    return (
      <section className="zone-sheet">
        <h2>Zone</h2>
        <p className="zone-sheet-muted">
          {loading ? "Chargement des quartiers…" : "Aucune ville active."}
        </p>
      </section>
    );
  }

  const places = lens.quartiers.filter((item) => originIds.includes(item.id));
  const selected = places.length > 0;
  const flows = selected
    ? lens.flows.filter(
        (flow) =>
          originIds.includes(flow.origin_id) || originIds.includes(flow.destination_id)
      )
    : lens.flows;
  const trips = flows.reduce((sum, flow) => sum + flow.headcount, 0);
  const km = flows.reduce((sum, flow) => sum + flow.km * flow.headcount, 0);
  const mean = trips > 0 ? km / trips : null;
  const work = flows
    .filter((flow) => flow.purpose === "travail")
    .reduce((sum, flow) => sum + flow.headcount, 0);
  const residents = selected
    ? places.reduce((sum, place) => sum + place.residents, 0)
    : lens.indices.residents;
  const jobs = selected
    ? places.reduce((sum, place) => sum + place.jobs, 0)
    : lens.indices.jobs;
  const name =
    places.length === 1
      ? places[0].name
      : places.length > 1
        ? `${places.length} quartiers`
        : lens.indices.scope_name || lens.city.name;
  const parent =
    places.length === 1
      ? places[0].parent_name
      : places.length > 1
        ? "Plusieurs arrondissements"
        : lens.city.name;
  const modes = tallyModes(flows);
  const modeTotal = modes.reduce((sum, row) => sum + row.people, 0) || 1;
  const ranked = [...flows].sort((a, b) => b.headcount - a.headcount).slice(0, 8);

  return (
    <section className="zone-sheet">
      <div className="zone-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "zone"}
          className={tab === "zone" ? "active" : undefined}
          onClick={() => setTab("zone")}
        >
          Zone
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "flux"}
          className={tab === "flux" ? "active" : undefined}
          onClick={() => setTab("flux")}
        >
          Flux
        </button>
      </div>

      {tab === "flux" ? (
        <div className="zone-flux">
          <h2>Flux liés à la sélection</h2>
          <p className="zone-sheet-muted">
            {selected
              ? "Volumes simulés qui partent ou arrivent dans les quartiers choisis."
              : "Plus gros flux du cadre. Cliquez un quartier pour resserrer la liste."}
          </p>
          <ul className="zone-flow-list">
            {ranked.map((flow) => (
              <li key={`${flow.origin_id}-${flow.destination_id}-${flow.purpose}`}>
                <span>
                  {flow.origin_name} → {flow.destination_name}
                  <small>
                    {flow.purpose_label} · {fmt(flow.km, 1)} km
                  </small>
                </span>
                <strong>{fmt(flow.headcount)}</strong>
              </li>
            ))}
          </ul>
          {matrix}
        </div>
      ) : (
        <>
          <p className="zone-kicker">Zone sélectionnée</p>
          <label className="zone-pick">
            Quartier
            <select
              value={places.length === 1 ? places[0].id : ""}
              onChange={(event) => {
                if (event.target.value) onSelectZone(event.target.value);
              }}
            >
              <option value="">Toute la ville</option>
              {lens.quartiers.map((place) => (
                <option key={place.id} value={place.id}>
                  {place.name}
                </option>
              ))}
            </select>
          </label>
          <h2>{name}</h2>
          <p className="zone-parent">
            Arrondissement · {parent}
          </p>
          {selected && (
            <button type="button" className="zone-clear" onClick={onClear}>
              Revenir à toute la ville
            </button>
          )}

          <h3>Indicateurs de la zone</h3>
          <dl className="zone-stats">
            <div>
              <dt>Population résidente</dt>
              <dd>{fmt(residents)}</dd>
            </div>
            <div>
              <dt>Emplois</dt>
              <dd>{fmt(jobs)}</dd>
            </div>
            <div>
              <dt>Nombre de trajets</dt>
              <dd>{fmt(trips)}</dd>
            </div>
            <div>
              <dt>Distance totale</dt>
              <dd>{fmt(km, 1)} km</dd>
            </div>
            <div>
              <dt>Distance moyenne</dt>
              <dd>{mean == null ? "—" : `${fmt(mean, 2)} km`}</dd>
            </div>
            <div>
              <dt>Part domicile-travail</dt>
              <dd>{trips ? `${Math.round((work / trips) * 100)} %` : "—"}</dd>
            </div>
          </dl>

          <h3>Répartition modale</h3>
          <div className="mode-bar" aria-hidden="true">
            {modes.map((row) => (
              <span
                key={row.id}
                style={{
                  width: `${(row.people / modeTotal) * 100}%`,
                  background: MODE_COLOR[row.id] ?? "#94a3b8",
                }}
              />
            ))}
          </div>
          <ul className="mode-legend">
            {modes.map((row) => (
              <li key={row.id}>
                <i style={{ background: MODE_COLOR[row.id] ?? "#94a3b8" }} />
                {row.name}
                <strong>{Math.round((row.people / modeTotal) * 100)} %</strong>
              </li>
            ))}
          </ul>
          <p className="zone-sheet-muted">
            Cliquez un quartier sur la carte pour lire ses indicateurs. Les effectifs
            sont des estimations simulées.
          </p>
        </>
      )}
    </section>
  );
}
