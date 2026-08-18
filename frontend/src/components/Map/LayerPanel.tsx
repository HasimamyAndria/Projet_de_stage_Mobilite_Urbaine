import { usePopover } from "./usePopover";

export type LayerKey =
  | "roads"
  | "buildings"
  | "busStops"
  | "busLines"
  | "odFlows"
  | "heatmap"
  | "keypoints"
  | "emploiHabitat"
  | "corridors"
  | "route";

export const LAYER_DEFS: Array<{
  key: LayerKey;
  label: string;
  group: "analyse" | "osm";
  layerIds: string[];
  defaultOn: boolean;
}> = [
  {
    key: "odFlows",
    label: "Flux OD",
    group: "analyse",
    layerIds: ["od-flows-line", "od-flows-line-halo", "od-nodes-circle"],
    defaultOn: true,
  },
  {
    key: "heatmap",
    label: "Heatmap densité",
    group: "analyse",
    layerIds: ["od-heatmap-layer"],
    defaultOn: true,
  },
  {
    key: "keypoints",
    label: "Zones clés (M2)",
    group: "analyse",
    layerIds: ["keypoints-zones-fill", "keypoints-zones-line"],
    defaultOn: false,
  },
  {
    key: "emploiHabitat",
    label: "Indice M6",
    group: "analyse",
    layerIds: ["emploi-habitat-fill", "emploi-habitat-line"],
    defaultOn: false,
  },
  {
    key: "corridors",
    label: "Corridors (zones clés)",
    group: "analyse",
    layerIds: ["keypoints-corridors-line"],
    defaultOn: false,
  },
  {
    key: "route",
    label: "Route A→B",
    group: "analyse",
    layerIds: ["route-layer"],
    defaultOn: false,
  },
  { key: "roads", label: "Routes", group: "osm", layerIds: ["roads"], defaultOn: false },
  {
    key: "buildings",
    label: "Bâtiments",
    group: "osm",
    layerIds: ["buildings"],
    defaultOn: false,
  },
  {
    key: "busStops",
    label: "Arrêts de bus",
    group: "osm",
    layerIds: ["bus-stops"],
    defaultOn: false,
  },
  {
    key: "busLines",
    label: "Lignes de bus",
    group: "osm",
    layerIds: ["bus-lines"],
    defaultOn: false,
  },
];

type Props = {
  visibility: Record<LayerKey, boolean>;
  onToggle: (key: LayerKey) => void;
};

export default function LayerPanel({ visibility, onToggle }: Props) {
  const { open, setOpen, ref } = usePopover();
  const activeCount = LAYER_DEFS.filter((layer) => visibility[layer.key]).length;

  return (
    <div className="map-ctrl" ref={ref}>
      <button
        type="button"
        className={open ? "map-ctrl-toggle is-open" : "map-ctrl-toggle"}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        Couches
        <span className="map-ctrl-badge">{activeCount}</span>
      </button>
      {open && (
        <div className="map-ctrl-popover layers-popover">
          <p className="map-ctrl-group">Analyse</p>
          {LAYER_DEFS.filter((layer) => layer.group === "analyse").map((layer) => (
            <label key={layer.key}>
              <input
                type="checkbox"
                checked={visibility[layer.key]}
                onChange={() => onToggle(layer.key)}
              />
              {layer.label}
            </label>
          ))}
          <p className="map-ctrl-group">Fond OSM</p>
          {LAYER_DEFS.filter((layer) => layer.group === "osm").map((layer) => (
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
      )}
    </div>
  );
}
