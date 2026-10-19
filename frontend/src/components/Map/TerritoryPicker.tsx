import type { PickMode } from "../../lensTypes";
import {
  motifLabel,
  readingMode,
  zoomBandLabel,
  type CorridorSide,
  type Motif,
  type ZoomBand,
} from "../../lensReading";

type Props = {
  cityName: string;
  arrondissement: string;
  zoneLabel: string;
  pickMode: PickMode;
  corridorSide: CorridorSide;
  motif: Motif;
  zoomBand: ZoomBand;
  originCount: number;
  destCount: number;
  onPickMode: (mode: PickMode) => void;
  onCorridorSide: (side: CorridorSide) => void;
  onMotif: (motif: Motif) => void;
  onClear: () => void;
};

export default function TerritoryPicker({
  cityName,
  arrondissement,
  zoneLabel,
  pickMode,
  corridorSide,
  motif,
  zoomBand,
  originCount,
  destCount,
  onPickMode,
  onCorridorSide,
  onMotif,
  onClear,
}: Props) {
  return (
    <div className="territory-picker">
      <p className="territory-city">{cityName}</p>
      <p className="territory-place">{arrondissement}</p>
      <p className={`territory-zone ${pickMode}`}>{zoneLabel}</p>
      <ul className="territory-pills">
        <li>Mode : {readingMode(pickMode, originCount, destCount)}</li>
        <li>Motif : {motifLabel(motif)}</li>
        <li>Données : SIMULÉES</li>
      </ul>
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
      {pickMode === "corridor" && (
        <div className="territory-modes" role="group" aria-label="Côté du clic">
          <button
            type="button"
            className={corridorSide === "origin" ? "is-on origin" : undefined}
            onClick={() => onCorridorSide("origin")}
          >
            Cliquer une origine
          </button>
          <button
            type="button"
            className={corridorSide === "destination" ? "is-on destination" : undefined}
            onClick={() => onCorridorSide("destination")}
          >
            Cliquer une destination
          </button>
        </div>
      )}
      <div className="territory-modes" role="group" aria-label="Motif">
        <button
          type="button"
          className={motif === "travail" ? "is-on corridor" : undefined}
          onClick={() => onMotif("travail")}
        >
          Travail
        </button>
        <button
          type="button"
          className={motif === "tous" ? "is-on corridor" : undefined}
          onClick={() => onMotif("tous")}
        >
          Tous les motifs
        </button>
      </div>
      <p className="territory-hint">
        {pickMode === "origin" && "Le clic choisit une origine. Le vert porte la lettre O."}
        {pickMode === "destination" && "Le clic choisit une destination. L’orange porte la lettre D."}
        {pickMode === "corridor" &&
          (corridorSide === "origin"
            ? "Prochain clic : origine (vert, O)."
            : "Prochain clic : destination (orange, D).")}
        {originCount + destCount > 0
          ? ` ${originCount} origine${originCount > 1 ? "s" : ""}, ${destCount} destination${destCount > 1 ? "s" : ""}.`
          : " Plusieurs quartiers possibles."}
      </p>
      <p className="territory-hint">{zoomBandLabel(zoomBand)}</p>
      {originCount + destCount > 0 && (
        <button type="button" className="territory-clear" onClick={onClear}>
          Effacer la sélection
        </button>
      )}
    </div>
  );
}
