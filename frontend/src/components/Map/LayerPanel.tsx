export type LayerKey =
  | "roads"
  | "buildings"
  | "busStops"
  | "busLines"
  | "odFlows"
  | "heatmap"
  | "emploiHabitat"
  | "corridors"
  | "route";

export const LAYER_DEFS: Array<{
  key: LayerKey;
  label: string;
  layerIds: string[];
  defaultOn: boolean;
}> = [
  { key: "roads", label: "Routes", layerIds: ["roads"], defaultOn: false },
  { key: "buildings", label: "Bâtiments", layerIds: ["buildings"], defaultOn: false },
  { key: "busStops", label: "Arrêts de bus", layerIds: ["bus-stops"], defaultOn: false },
  { key: "busLines", label: "Lignes de bus", layerIds: ["bus-lines"], defaultOn: false },
  {
    key: "odFlows",
    label: "Flux OD",
    layerIds: ["od-flows-line", "od-flows-line-halo", "od-nodes-circle"],
    defaultOn: true,
  },
  {
    key: "heatmap",
    label: "Heatmap densité",
    layerIds: ["od-heatmap-layer"],
    defaultOn: true,
  },
  {
    key: "emploiHabitat",
    label: "Indice M6",
    layerIds: ["emploi-habitat-fill", "emploi-habitat-line"],
    defaultOn: false,
  },
  {
    key: "corridors",
    label: "Corridors (zones clés)",
    layerIds: ["keypoints-corridors-line"],
    defaultOn: false,
  },
  { key: "route", label: "Route A→B", layerIds: ["route-layer"], defaultOn: false },
];

type Props = {
  visibility: Record<LayerKey, boolean>;
  onToggle: (key: LayerKey) => void;
};

export default function LayerPanel({ visibility, onToggle }: Props) {
  return (
    <div className="layers-card">
      <h3>Couches</h3>
      {LAYER_DEFS.map((layer) => (
        <label key={layer.key}>
          <input
            type="checkbox"
            checked={visibility[layer.key]}
            onChange={() => onToggle(layer.key)}
          />
          {layer.label}
        </label>
      ))}
    </div>
  );
}
