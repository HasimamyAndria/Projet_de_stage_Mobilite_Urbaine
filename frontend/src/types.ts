export type ViewId =
  | "accueil"
  | "carte"
  | "dashboard"
  | "deplacements"
  | "zones"
  | "emploi"
  | "simulation"
  | "reco"
  | "rapports";

export type OdFilters = {
  hour: number | null;
  weekday: number | null;
  mode: string;
  minPassengers: number;
};

export const DEFAULT_OD_FILTERS: OdFilters = {
  hour: null,
  weekday: null,
  mode: "all",
  minPassengers: 20,
};

export const NAV_ITEMS: Array<{
  id: ViewId;
  label: string;
  subtitle: string;
}> = [
  { id: "accueil", label: "Accueil", subtitle: "Analyse de la mobilité" },
  { id: "carte", label: "Carte & Flux OD", subtitle: "Zones et desire lines" },
  { id: "dashboard", label: "Tableau de bord", subtitle: "Indicateurs" },
  { id: "deplacements", label: "Déplacements", subtitle: "Journal simulé" },
  { id: "zones", label: "Zones critiques", subtitle: "Points clés" },
  { id: "emploi", label: "Emploi-habitat", subtitle: "Équilibre" },
  { id: "simulation", label: "Simulation", subtitle: "Hypothèse d'aménagement" },
  { id: "reco", label: "Recommandations IA", subtitle: "Actions proposées" },
  { id: "rapports", label: "Rapports", subtitle: "Exports" },
];
