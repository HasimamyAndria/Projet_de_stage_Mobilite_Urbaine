import type { LensPayload, PickMode } from "../../lensTypes";
import {
  arrondissementLabel,
  motifLabel,
  readingMode,
  readingQuestion,
  zoneHeadline,
  zoomBandLabel,
  zoomBandOf,
  type Motif,
} from "../../lensReading";

type Props = {
  city: string;
  lens: LensPayload | null;
  pickMode: PickMode;
  motif: Motif;
  originIds: string[];
  destIds: string[];
  zoom: number;
  onPickMode: (mode: PickMode) => void;
  onToggle: (id: string, mode: "origin" | "destination") => void;
  onClear: () => void;
};

function sameIds(left: string[], right: string[]) {
  if (left.length !== right.length) return false;
  const known = new Set(right);
  return left.every((id) => known.has(id));
}

export function readingNote(
  lens: LensPayload | null,
  pickMode: PickMode,
  originIds: string[],
  destIds: string[],
  motif: Motif
): string {
  const question = readingQuestion(pickMode, originIds, destIds, motif);
  if (!lens) return question;
  const ready =
    sameIds(lens.selection.origins, originIds) &&
    sameIds(lens.selection.destinations, destIds);
  if (!ready) return question;
  const departures = lens.indices.regular_workers;
  const jobs = lens.indices.jobs;
  if (originIds.length > 0 && destIds.length === 0 && departures === 0 && jobs > 0) {
    return "Personne ne part d’ici dans la simulation. Ces quartiers accueillent des emplois : passez en mode Destination.";
  }
  if (destIds.length > 0 && originIds.length === 0 && departures === 0 && lens.indices.residents > 0) {
    return "Personne n’arrive ici dans la simulation. Ces quartiers envoient des habitants : passez en mode Origine.";
  }
  return question;
}

export default function OdContextBar({
  city,
  lens,
  pickMode,
  motif,
  originIds,
  destIds,
  zoom,
  onPickMode,
  onToggle,
  onClear,
}: Props) {
  const tone =
    originIds.length > 0 && destIds.length > 0
      ? "corridor"
      : destIds.length > 0 && originIds.length === 0
        ? "destination"
        : "origin";
  const place = lens ? zoneHeadline(lens, pickMode, originIds, destIds) : city;
  const district = lens ? arrondissementLabel(lens, originIds, destIds) : "Arrondissement";
  const note = readingNote(lens, pickMode, originIds, destIds, motif);
  const clickHint =
    pickMode === "destination"
      ? "Chaque clic ajoute ou retire une destination. Les origines déjà choisies restent."
      : pickMode === "corridor"
        ? "Cliquez d’abord les origines, puis les destinations. Plusieurs de chaque côté."
        : "Chaque clic ajoute ou retire une origine. Les destinations déjà choisies restent.";
  const nameOf = (id: string) => lens?.quartiers.find((item) => item.id === id)?.name ?? id;

  const named = place !== (lens?.city.name ?? city);

  return (
    <section className={`od-context ${tone}`} aria-label="Contexte de la carte">
      <p className="od-context-city">
        {lens?.city.name ?? city}
        <span> · {district}</span>
      </p>
      {named && <h2 className="od-context-place">{place}</h2>}
      <p className="od-context-meta">
        Mode : {readingMode(pickMode, originIds.length, destIds.length)}
        {" · Motif : "}
        {motifLabel(motif)}
        {" · "}
        {zoomBandLabel(zoomBandOf(zoom))}
        {" · Données : SIMULÉES"}
      </p>
      <p className="od-context-question">{note}</p>
      <div className="od-context-modes" role="group" aria-label="Ce que le prochain clic ajoute">
        <button
          type="button"
          className={pickMode === "origin" ? "is-on origin" : undefined}
          onClick={() => onPickMode("origin")}
        >
          Origines
        </button>
        <button
          type="button"
          className={pickMode === "destination" ? "is-on destination" : undefined}
          onClick={() => onPickMode("destination")}
        >
          Destinations
        </button>
      </div>
      <p className="od-context-hint">{clickHint}</p>
      {(originIds.length > 0 || destIds.length > 0) && (
        <div className="od-context-picks">
          {originIds.map((id) => (
            <button key={`o-${id}`} type="button" className="origin" onClick={() => onToggle(id, "origin")}>
              Origine · {nameOf(id)} ×
            </button>
          ))}
          {destIds.map((id) => (
            <button key={`d-${id}`} type="button" className="destination" onClick={() => onToggle(id, "destination")}>
              Destination · {nameOf(id)} ×
            </button>
          ))}
        </div>
      )}
      {(originIds.length > 0 || destIds.length > 0) && (
        <button type="button" className="od-context-clear" onClick={onClear}>
          Revenir à toute la ville
        </button>
      )}
    </section>
  );
}
