export type LensFlow = {
  origin_id: string;
  destination_id: string;
  purpose: string;
  purpose_label: string;
  detail: string;
  headcount: number;
  km: number;
  cadence: string;
  mode: string;
  regular: boolean;
  organization_id: string | null;
  organization_name: string | null;
  organization_kind: string | null;
  why: string;
  origin_name: string;
  destination_name: string;
  origin_lon: number;
  origin_lat: number;
  destination_lon: number;
  destination_lat: number;
  origin_parent_id: string;
  origin_parent_name: string;
  destination_parent_id: string;
  destination_parent_name: string;
  destination_role: string;
  destination_role_label: string;
  inside: string;
};

export type LensQuartier = {
  id: string;
  name: string;
  parent_id: string;
  parent_name: string;
  role: string;
  role_label: string;
  lon: number;
  lat: number;
  residents: number;
  jobs: number;
  eh_index: number | null;
  outbound_share: number;
  mean_km: number | null;
};

export type LensCommune = {
  id: string;
  name: string;
  lon: number;
  lat: number;
  quartier_ids: string[];
  geometry: { type: "Polygon"; coordinates: number[][][] };
};

export type LensPayload = {
  city: { id: string; name: string; aka: string; population: number };
  question: string;
  scope_sentence: string;
  selection: { origins: string[]; destinations: string[] };
  indices: {
    scope_name: string;
    residents: number;
    jobs: number;
    eh_index: number | null;
    eh_sentence: string;
    outbound_share: number;
    mean_km: number | null;
    regular_workers: number;
    regular_other: number;
    pressure: number;
  };
  flows: LensFlow[];
  purposes: Array<{ label: string; people: number }>;
  arrivals: Array<{
    id: string;
    name: string;
    parent_name: string;
    role_label: string;
    inside: string;
    people: number;
    purposes: string[];
  }>;
  relocations: Array<{
    organization_name: string;
    headcount: number;
    home_name: string;
    home_parent: string;
    work_name: string;
    km: number;
    empty_zone_id: string;
    empty_zone_name: string;
    empty_zone_parent: string;
    empty_zone_role: string;
    annex_km: number;
    gain_km: number;
    text: string;
  }>;
  quartiers: LensQuartier[];
  communes: LensCommune[];
  synthetic: boolean;
  note: string;
};

export type PickMode = "origin" | "destination" | "corridor";
