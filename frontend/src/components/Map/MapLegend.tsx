import type { LayerKey } from "./LayerPanel";

type Props = {
  visibility: Record<LayerKey, boolean>;
};

export default function MapLegend({ visibility }: Props) {
  const showOd = visibility.odFlows;
  const showHeat = visibility.heatmap;
  const showM6 = visibility.emploiHabitat;
  const showCorridors = visibility.corridors;
  const showKeypoints = visibility.keypoints;
  const showRoute = visibility.route;

  if (
    !showOd &&
    !showHeat &&
    !showM6 &&
    !showCorridors &&
    !showKeypoints &&
    !showRoute
  ) {
    return null;
  }

  return (
    <div className="map-legend-card">
      {showOd && (
        <div className="legend-block">
          <span className="legend-title">Flux OD</span>
          <div
            className="legend-gradient"
            style={{
              background:
                "linear-gradient(90deg, #166534, #22c55e, #eab308, #f97316, #dc2626)",
            }}
          />
          <div className="legend-ends">
            <span>&lt; 50</span>
            <span>&gt; 200</span>
          </div>
        </div>
      )}
      {showHeat && (
        <div className="legend-block">
          <span className="legend-title">Densité</span>
          <div
            className="legend-gradient"
            style={{
              background:
                "linear-gradient(90deg, #1e40af, #22c55e, #eab308, #f97316, #dc2626)",
            }}
          />
          <div className="legend-ends">
            <span>Faible</span>
            <span>Forte</span>
          </div>
        </div>
      )}
      {showM6 && (
        <div className="legend-block">
          <span className="legend-title">Indice M6</span>
          <div
            className="legend-gradient"
            style={{
              background: "linear-gradient(90deg, #b91c1c, #f59e0b, #15803d)",
            }}
          />
          <div className="legend-ends">
            <span>Bas</span>
            <span>Équilibré</span>
          </div>
        </div>
      )}
      {showKeypoints && (
        <div className="legend-block">
          <span className="legend-title">Zones clés M2</span>
          <div className="legend-swatch-row">
            <span className="legend-dot" style={{ background: "#7c3aed" }} />
            Dortoir
          </div>
          <div className="legend-swatch-row">
            <span className="legend-dot" style={{ background: "#ea580c" }} />
            Pôle emploi
          </div>
          <div className="legend-swatch-row">
            <span className="legend-dot" style={{ background: "#38bdf8" }} />
            Mixte
          </div>
        </div>
      )}
      {showCorridors && (
        <div className="legend-swatch-row">
          <span className="legend-line" style={{ background: "#f87171" }} />
          Corridors M2
        </div>
      )}
      {showRoute && (
        <div className="legend-swatch-row">
          <span className="legend-line" style={{ background: "#38bdf8" }} />
          Itinéraire A→B
        </div>
      )}
    </div>
  );
}
