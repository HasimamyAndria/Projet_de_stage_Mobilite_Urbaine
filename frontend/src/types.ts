export type ViewId =
  | "dashboard"
  | "carte"
  | "od"
  | "zones"
  | "emploi"
  | "simulation"
  | "reco";

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
  { id: "dashboard", label: "Tableau de bord", subtitle: "KPI exécutifs · M5" },
  { id: "carte", label: "Carte interactive", subtitle: "Flux, heatmap · M1" },
  { id: "od", label: "Flux OD", subtitle: "Matrice filtrable · M1" },
  { id: "zones", label: "Zones critiques", subtitle: "Points clés · M2" },
  { id: "emploi", label: "Emploi-habitat", subtitle: "Proximité · M6" },
  { id: "simulation", label: "Simulation", subtitle: "What-if · M4" },
  { id: "reco", label: "Recommandations", subtitle: "Urbanisation · M3" },
];
