import { usePopover } from "./usePopover";

export type LayerKey =
  | "territory"
  | "roads"
  | "buildings"
  | "busStops"
  | "busLines"
  | "odFlows"
  | "heatmap"
  | "heatmapOrigin"
  | "heatmapDest"
  | "keypoints"
  | "emploiHabitat"
  | "corridors"
  | "convergence"
  | "deserts"
  | "carpool"
  | "unbalanced"
  | "satellites"
  | "recommendations"
  | "route";

export const LAYER_DEFS: Array<{
  key: LayerKey;
  label: string;
  group: "analyse" | "osm";
  layerIds: string[];
  defaultOn: boolean;
  inPanel?: boolean;
}> = [
  {
    key: "territory",
    label: "Quartiers et arrondissements",
    group: "analyse",
    layerIds: [
      "lens-communes-fill",
      "lens-communes-line",
      "lens-commune-labels",
      "lens-flows-halo",
      "lens-flows-line",
      "lens-flows-arrow",
      "lens-quartiers",
      "lens-quartiers-focus",
      "lens-quartier-halo",
      "lens-quartier-role",
      "lens-quartier-selected-labels",
      "lens-quartier-labels",
    ],
    defaultOn: true,
    inPanel: true,
  },
  {
    key: "odFlows",
    label: "Flux OD",
    group: "analyse",
    layerIds: ["od-flows-line", "od-flows-line-halo", "od-nodes-circle"],
    defaultOn: false,
  },
  {
    key: "heatmap",
    label: "Heatmap activité",
    group: "analyse",
    layerIds: ["od-heatmap-layer"],
    defaultOn: false,
  },
  {
    key: "heatmapOrigin",
    label: "Densité départs",
    group: "analyse",
    layerIds: ["od-heatmap-origin"],
    defaultOn: false,
  },
  {
    key: "heatmapDest",
    label: "Densité arrivées",
    group: "analyse",
    layerIds: ["od-heatmap-dest"],
    defaultOn: false,
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
    label: "Corridors saturés",
    group: "analyse",
    layerIds: ["keypoints-corridors-line"],
    defaultOn: false,
  },
  {
    key: "convergence",
    label: "Nœuds de convergence",
    group: "analyse",
    layerIds: ["keypoints-convergence"],
    defaultOn: false,
  },
  {
    key: "deserts",
    label: "Déserts de mobilité",
    group: "analyse",
    layerIds: ["keypoints-deserts-fill", "keypoints-deserts-line"],
    defaultOn: false,
  },
  {
    key: "carpool",
    label: "Mutualisation",
    group: "analyse",
    layerIds: ["keypoints-carpool-line"],
    defaultOn: false,
  },
  {
    key: "unbalanced",
    label: "Couples RH déséquilibrés",
    group: "analyse",
    layerIds: ["keypoints-unbalanced-line"],
    defaultOn: false,
  },
  {
    key: "satellites",
    label: "Bureaux satellites",
    group: "analyse",
    layerIds: ["satellites-fill", "satellites-point"],
    defaultOn: false,
  },
  {
    key: "recommendations",
    label: "Recommandations",
    group: "analyse",
    layerIds: ["reco-line", "reco-fill", "reco-point"],
    defaultOn: false,
  },
  {
    key: "route",
    label: "Route A→B",
    group: "analyse",
    layerIds: ["route-layer"],
    defaultOn: false,
  },
  {
    key: "roads",
    label: "Routes",
    group: "osm",
    layerIds: ["roads"],
    defaultOn: false,
    inPanel: true,
  },
  {
    key: "buildings",
    label: "Bâtiments",
    group: "osm",
    layerIds: ["buildings"],
    defaultOn: false,
    inPanel: true,
  },
  {
    key: "busStops",
    label: "Arrêts de bus",
    group: "osm",
    layerIds: ["bus-stops"],
    defaultOn: false,
    inPanel: true,
  },
  {
    key: "busLines",
    label: "Lignes de bus",
    group: "osm",
    layerIds: ["bus-lines"],
    defaultOn: false,
    inPanel: true,
  },
];

type Props = {
  visibility: Record<LayerKey, boolean>;
  onToggle: (key: LayerKey) => void;
};

export default function LayerPanel({ visibility, onToggle }: Props) {
  const { open, setOpen, ref } = usePopover();
  const panelLayers = LAYER_DEFS.filter((layer) => layer.inPanel);
  const activeCount = panelLayers.filter((layer) => visibility[layer.key]).length;

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
          <p className="map-ctrl-group">Repères</p>
          {panelLayers
            .filter((layer) => layer.group === "analyse")
            .map((layer) => (
              <label key={layer.key}>
                <input
                  type="checkbox"
                  checked={visibility[layer.key]}
                  onChange={() => onToggle(layer.key)}
                />
                {layer.label}
              </label>
            ))}
          <p className="map-ctrl-group">Réseau</p>
          {panelLayers
            .filter((layer) => layer.group === "osm")
            .map((layer) => (
              <label key={layer.key}>
                <input
                  type="checkbox"
                  checked={visibility[layer.key]}
                  onChange={() => onToggle(layer.key)}
                />
                {layer.label}
              </label>
            ))}
          <p className="layers-note">
            Routes, bâtiments, arrêts et lignes de bus s'ajoutent seulement si vous les cochez. Le fond affiche déjà la ville.
          </p>
        </div>
      )}
    </div>
  );
}
