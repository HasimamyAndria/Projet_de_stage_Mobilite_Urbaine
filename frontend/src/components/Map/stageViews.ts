import type { LayerKey } from "./LayerPanel";

export type StageView =
  | "demarche"
  | "accueil"
  | "carte"
  | "dashboard"
  | "deplacements"
  | "zones"
  | "emploi"
  | "simulation"
  | "reco"
  | "rapports";

export type NavIconName =
  | "home"
  | "map"
  | "chart"
  | "route"
  | "alert"
  | "balance"
  | "sliders"
  | "spark"
  | "file"
  | "steps";

export type PersonaId = "jury" | "urbaniste" | "elu" | "entreprise" | "citoyen";

export const STAGE_NAV: Array<{ id: StageView; label: string; icon: NavIconName }> = [
  { id: "demarche", label: "Optimisation", icon: "steps" },
  { id: "accueil", label: "Accueil", icon: "home" },
  { id: "carte", label: "Carte & Flux OD", icon: "map" },
  { id: "dashboard", label: "Tableau de bord", icon: "chart" },
  { id: "deplacements", label: "Déplacements", icon: "route" },
  { id: "zones", label: "Zones critiques", icon: "alert" },
  { id: "emploi", label: "Emploi-habitat", icon: "balance" },
  { id: "simulation", label: "Simulation", icon: "sliders" },
  { id: "reco", label: "Recommandations IA", icon: "spark" },
  { id: "rapports", label: "Rapports", icon: "file" },
];

export const PERSONAS: Array<{
  id: PersonaId;
  label: string;
  views: StageView[];
}> = [
  {
    id: "jury",
    label: "Démo complète",
    views: STAGE_NAV.map((item) => item.id),
  },
  {
    id: "urbaniste",
    label: "Urbaniste",
    views: ["demarche", "accueil", "carte", "zones", "reco", "simulation", "emploi"],
  },
  {
    id: "elu",
    label: "Élu",
    views: ["demarche", "accueil", "dashboard", "simulation", "rapports"],
  },
  {
    id: "entreprise",
    label: "Entreprise / DRH",
    views: ["demarche", "accueil", "deplacements", "emploi", "simulation"],
  },
  {
    id: "citoyen",
    label: "Citoyen",
    views: ["demarche", "accueil", "carte", "emploi"],
  },
];

export const VIEW_COPY: Record<StageView, { title: string; subtitle: string }> = {
  demarche: {
    title: "Optimisation des sites",
    subtitle: "Demande, candidats, choix, score, puis comparaison à la référence",
  },
  accueil: {
    title: "Analyse de la mobilité urbaine",
    subtitle:
      "Explorez les déplacements, identifiez les zones prioritaires et prenez des décisions éclairées pour une mobilité plus durable et plus efficace.",
  },
  carte: {
    title: "Carte et flux origine-destination",
    subtitle: "Quartiers, lignes de désir et matrice des volumes entre zones",
  },
  dashboard: {
    title: "Tableau de bord",
    subtitle: "Indicateurs, objectifs et évolution illustrative",
  },
  deplacements: {
    title: "Déplacements",
    subtitle:
      "Choisir une organisation, examiner les trajets, identifier les besoins, tester un bureau satellite, comparer, puis décider",
  },
  zones: {
    title: "Zones critiques",
    subtitle: "Convergence, corridors, déserts et pôles",
  },
  emploi: {
    title: "Emploi-habitat",
    subtitle: "Équilibre entre habitants et emplois, bureaux annexes, télétravail",
  },
  simulation: {
    title: "Simulation",
    subtitle: "Comparer une hypothèse d'aménagement à la situation actuelle",
  },
  reco: {
    title: "Recommandations IA",
    subtitle: "Actions proposées à partir des déséquilibres observés",
  },
  rapports: {
    title: "Rapports",
    subtitle: "Exporter une synthèse pour le conseil ou l'équipe projet",
  },
};

export function applyViewPreset(
  prev: Record<LayerKey, boolean>,
  view: StageView
): Record<LayerKey, boolean> {
  const analysis = view === "accueil" || view === "carte";
  return {
    ...prev,
    territory: analysis,
    odFlows: view === "simulation",
    heatmap: false,
    heatmapOrigin: false,
    heatmapDest: false,
    keypoints: view === "zones",
    corridors: view === "zones" || view === "reco",
    convergence: view === "zones" || view === "reco",
    deserts: view === "zones" || view === "reco",
    carpool: view === "zones",
    unbalanced: view === "zones",
    emploiHabitat: view === "emploi",
    satellites: view === "emploi" || view === "demarche",
    recommendations: view === "reco",
  };
}
