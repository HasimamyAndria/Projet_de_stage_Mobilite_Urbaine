import type { LayerKey } from "./LayerPanel";

export type StageView = "carte" | "od" | "zones" | "indicateurs";

export const STAGE_NAV: Array<{ id: StageView; label: string }> = [
  { id: "carte", label: "Carte interactive" },
  { id: "od", label: "Flux OD" },
  { id: "zones", label: "Zones clés" },
  { id: "indicateurs", label: "Indicateurs" },
];

export const VIEW_COPY: Record<StageView, { title: string; subtitle: string }> = {
  carte: {
    title: "Carte interactive",
    subtitle: "Flux OD, heatmap, couches OSM — vue décideur",
  },
  od: {
    title: "Flux OD",
    subtitle: "Desire lines agrégées zone→zone (pas des itinéraires rue)",
  },
  zones: {
    title: "Zones clés",
    subtitle: "Dortoirs, pôles d’emploi, clustering spatial, corridors",
  },
  indicateurs: {
    title: "Indicateurs",
    subtitle: "Indice emploi-habitat (M6) et synthèse KPI (M5)",
  },
};

export function applyViewPreset(
  prev: Record<LayerKey, boolean>,
  view: StageView
): Record<LayerKey, boolean> {
  return {
    ...prev,
    odFlows: view === "carte" || view === "od",
    heatmap: view === "carte" || view === "od",
    keypoints: view === "zones",
    corridors: view === "zones",
    emploiHabitat: view === "indicateurs",
  };
}
