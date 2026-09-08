import type { LayerKey } from "./LayerPanel";

export type StageView =
  | "dashboard"
  | "carte"
  | "od"
  | "zones"
  | "emploi"
  | "simulation"
  | "reco";

export const STAGE_NAV: Array<{ id: StageView; label: string }> = [
  { id: "dashboard", label: "Tableau de bord" },
  { id: "carte", label: "Carte interactive" },
  { id: "od", label: "Flux OD" },
  { id: "zones", label: "Zones critiques" },
  { id: "emploi", label: "Emploi-habitat" },
  { id: "simulation", label: "Simulation" },
  { id: "reco", label: "Recommandations" },
];

export const VIEW_COPY: Record<StageView, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Tableau de bord",
    subtitle: "8 KPI · objectifs PDM/SCoT · benchmark illustratif",
  },
  carte: {
    title: "Carte interactive",
    subtitle: "Flux OD, heatmap, filtres horaires / modes",
  },
  od: {
    title: "Flux OD",
    subtitle: "Matrice filtrable et lignes de désir zone→zone",
  },
  zones: {
    title: "Zones critiques",
    subtitle: "Convergence, corridors, déserts, mutualisation, K-means",
  },
  emploi: {
    title: "Emploi-habitat",
    subtitle: "Indice de proximité, bureaux satellites, télétravail",
  },
  simulation: {
    title: "Simulation what-if",
    subtitle: "Tester un aménagement et comparer à la référence",
  },
  reco: {
    title: "Recommandations d'urbanisation",
    subtitle: "Actions typées avec score d'impact estimé",
  },
};

export function applyViewPreset(
  prev: Record<LayerKey, boolean>,
  view: StageView
): Record<LayerKey, boolean> {
  return {
    ...prev,
    odFlows: view === "carte" || view === "od" || view === "simulation",
    heatmap: view === "carte",
    heatmapOrigin: view === "od",
    heatmapDest: view === "od",
    keypoints: view === "zones",
    corridors: view === "zones" || view === "reco",
    convergence: view === "zones" || view === "reco",
    deserts: view === "zones" || view === "reco",
    carpool: view === "zones",
    unbalanced: view === "zones",
    emploiHabitat: view === "emploi",
    satellites: view === "emploi",
    recommendations: view === "reco",
  };
}
