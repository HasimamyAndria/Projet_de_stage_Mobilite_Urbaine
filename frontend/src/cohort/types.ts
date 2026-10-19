/** Réponses JSON de `/api/mobility/cohort/*`. Les dates arrivent en texte ISO. */

export type CohortFiltersEcho = {
  date_from: string | null;
  date_to: string | null;
  mode: string | null;
  purpose: string | null;
  origin_id: string | null;
  destination_id: string | null;
  person_id: string | null;
};

export type CohortPeriod = {
  date_from: string | null;
  date_to: string | null;
  calendar_days: number | null;
  period_source: string;
};

export type ModeShare = {
  mode_code: string;
  label: string;
  trip_count: number;
  distance_km: number;
  duration_min: number;
};

export type PurposeShare = {
  purpose_code: string;
  label: string;
  trip_count: number;
  distance_km: number;
  duration_min: number;
};

export type DateShare = {
  trip_date: string;
  trip_count: number;
  distance_km: number;
  duration_min: number;
};

export type CohortMeta = {
  dataset_id: string;
  source: string;
  simulated: boolean;
  data_status: string;
  seed: number | null;
  anchor_monday: string | null;
  first_trip_date: string | null;
  last_trip_date: string | null;
  person_count: number;
  trip_count: number;
  label: string;
  horizon_days: null;
  horizon_note: string;
  distance_method: string;
  caveat: string;
};

export type CohortOverview = {
  dataset_id: string;
  source: string;
  simulated: boolean;
  data_status: string;
  distance_unit: string;
  duration_unit: string;
  distance_method: string;
  calendar_rule: string;
  caveat: string;
  filters: CohortFiltersEcho;
  period: CohortPeriod;
  person_count: number;
  trip_count: number;
  distance_km: number;
  duration_min: number;
  average_distance_km: number | null;
  average_duration_min: number | null;
  by_mode: ModeShare[];
  by_purpose: PurposeShare[];
  by_date: DateShare[];
  active_person_days: number | null;
  empty_person_days: number | null;
  empty_person_days_rule: string;
};

export type CohortFlow = {
  origin_place_id: string;
  origin_name: string;
  origin_lon: number;
  origin_lat: number;
  destination_place_id: string;
  destination_name: string;
  destination_lon: number;
  destination_lat: number;
  trip_count: number;
  distance_km: number;
  duration_min: number;
};

export type CohortFlows = {
  dataset_id: string;
  source: string;
  simulated: boolean;
  data_status: string;
  distance_unit: string;
  duration_unit: string;
  distance_method: string;
  caveat: string;
  filters: CohortFiltersEcho;
  pair_count: number;
  limit: number;
  offset: number;
  returned: number;
  flows: CohortFlow[];
};

export type CohortTrip = {
  trip_id: string;
  person_id: string;
  trip_date: string;
  depart_time: string;
  arrive_time: string;
  origin_place_id: string;
  origin_name: string;
  destination_place_id: string;
  destination_name: string;
  purpose_code: string;
  purpose_label: string;
  mode_code: string;
  mode_label: string;
  distance_km: number;
  duration_min: number;
  source: string;
};

export type CohortTrips = {
  dataset_id: string;
  source: string;
  simulated: boolean;
  data_status: string;
  distance_unit: string;
  duration_unit: string;
  distance_method: string;
  caveat: string;
  exposure: string;
  filters: CohortFiltersEcho;
  limit: number;
  offset: number;
  total: number;
  returned: number;
  trips: CohortTrip[];
};

export type CohortQuery = {
  date_from?: string;
  date_to?: string;
  mode?: string;
  purpose?: string;
  origin_id?: string;
  destination_id?: string;
};
