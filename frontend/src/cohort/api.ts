import axios from "axios";
import api from "../services/api";
import type {
  CohortFlows,
  CohortMeta,
  CohortOverview,
  CohortQuery,
  CohortTrips,
} from "./types";

const META_URL = "/api/mobility/cohort/meta";
const OVERVIEW_URL = "/api/mobility/cohort/overview";
const FLOWS_URL = "/api/mobility/cohort/flows";
const TRIPS_URL = "/api/mobility/cohort/trips";

/** Taille de page du tableau. Le maximum backend des flux est 500. */
export const FLOW_PAGE_SIZE = 20;
export const FLOW_CATALOG_LIMIT = 500;
/** Défaut backend des étapes. Le maximum est 100. */
export const TRIP_PAGE_SIZE = 50;

class CohortPayloadError extends Error {}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNum(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isShare(value: unknown, codeKey: "mode_code" | "purpose_code"): boolean {
  if (!isRecord(value)) return false;
  return (
    typeof value[codeKey] === "string" &&
    typeof value.label === "string" &&
    isNum(value.trip_count) &&
    isNum(value.distance_km) &&
    isNum(value.duration_min)
  );
}

export function isCohortMeta(value: unknown): value is CohortMeta {
  if (!isRecord(value)) return false;
  return (
    typeof value.dataset_id === "string" &&
    typeof value.source === "string" &&
    typeof value.simulated === "boolean" &&
    typeof value.data_status === "string" &&
    (value.seed === null || isNum(value.seed)) &&
    (value.anchor_monday === null || typeof value.anchor_monday === "string") &&
    (value.first_trip_date === null || typeof value.first_trip_date === "string") &&
    (value.last_trip_date === null || typeof value.last_trip_date === "string") &&
    isNum(value.person_count) &&
    isNum(value.trip_count) &&
    typeof value.label === "string" &&
    value.horizon_days === null &&
    typeof value.horizon_note === "string" &&
    typeof value.distance_method === "string" &&
    typeof value.caveat === "string"
  );
}

export function isCohortOverview(value: unknown): value is CohortOverview {
  if (!isRecord(value) || !isRecord(value.period)) return false;
  return (
    typeof value.dataset_id === "string" &&
    typeof value.distance_unit === "string" &&
    typeof value.duration_unit === "string" &&
    typeof value.distance_method === "string" &&
    typeof value.caveat === "string" &&
    typeof value.empty_person_days_rule === "string" &&
    isNum(value.person_count) &&
    isNum(value.trip_count) &&
    isNum(value.distance_km) &&
    isNum(value.duration_min) &&
    (value.average_distance_km === null || isNum(value.average_distance_km)) &&
    (value.average_duration_min === null || isNum(value.average_duration_min)) &&
    (value.active_person_days === null || isNum(value.active_person_days)) &&
    (value.empty_person_days === null || isNum(value.empty_person_days)) &&
    (value.period.date_from === null || typeof value.period.date_from === "string") &&
    (value.period.date_to === null || typeof value.period.date_to === "string") &&
    (value.period.calendar_days === null || isNum(value.period.calendar_days)) &&
    typeof value.period.period_source === "string" &&
    Array.isArray(value.by_mode) &&
    value.by_mode.every((row) => isShare(row, "mode_code")) &&
    Array.isArray(value.by_purpose) &&
    value.by_purpose.every((row) => isShare(row, "purpose_code")) &&
    Array.isArray(value.by_date) &&
    value.by_date.every(
      (row) =>
        isRecord(row) &&
        typeof row.trip_date === "string" &&
        isNum(row.trip_count) &&
        isNum(row.distance_km) &&
        isNum(row.duration_min),
    )
  );
}

function isFlow(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return (
    typeof value.origin_place_id === "string" &&
    typeof value.origin_name === "string" &&
    typeof value.destination_place_id === "string" &&
    typeof value.destination_name === "string" &&
    isNum(value.trip_count) &&
    isNum(value.distance_km) &&
    isNum(value.duration_min)
  );
}

export function isCohortFlows(value: unknown): value is CohortFlows {
  if (!isRecord(value)) return false;
  return (
    typeof value.distance_unit === "string" &&
    typeof value.duration_unit === "string" &&
    typeof value.distance_method === "string" &&
    typeof value.caveat === "string" &&
    isNum(value.pair_count) &&
    isNum(value.limit) &&
    isNum(value.offset) &&
    isNum(value.returned) &&
    Array.isArray(value.flows) &&
    value.flows.every(isFlow)
  );
}

function isTrip(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return (
    typeof value.trip_id === "string" &&
    typeof value.person_id === "string" &&
    typeof value.trip_date === "string" &&
    typeof value.depart_time === "string" &&
    typeof value.arrive_time === "string" &&
    typeof value.origin_name === "string" &&
    typeof value.destination_name === "string" &&
    typeof value.purpose_label === "string" &&
    typeof value.mode_label === "string" &&
    isNum(value.distance_km) &&
    isNum(value.duration_min) &&
    typeof value.source === "string"
  );
}

export function isCohortTrips(value: unknown): value is CohortTrips {
  if (!isRecord(value)) return false;
  return (
    typeof value.distance_unit === "string" &&
    typeof value.duration_unit === "string" &&
    typeof value.caveat === "string" &&
    typeof value.exposure === "string" &&
    isNum(value.total) &&
    isNum(value.limit) &&
    isNum(value.offset) &&
    isNum(value.returned) &&
    Array.isArray(value.trips) &&
    value.trips.every(isTrip)
  );
}

function params(query: CohortQuery, page?: { limit: number; offset: number }) {
  const out: Record<string, string | number> = {};
  if (query.date_from) out.date_from = query.date_from;
  if (query.date_to) out.date_to = query.date_to;
  if (query.mode) out.mode = query.mode;
  if (query.purpose) out.purpose = query.purpose;
  if (query.origin_id) out.origin_id = query.origin_id;
  if (query.destination_id) out.destination_id = query.destination_id;
  if (page) {
    out.limit = page.limit;
    out.offset = page.offset;
  }
  return out;
}

function detailText(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!Array.isArray(detail)) return null;
  const text = detail
    .map((item) => {
      if (typeof item === "string") return item;
      if (isRecord(item) && typeof item.msg === "string") return item.msg;
      return "";
    })
    .filter(Boolean)
    .join(" ");
  return text || null;
}

/** `null` si la requête a été annulée : l'appelant ne doit pas afficher d'erreur. */
export function readCohortError(error: unknown, fallback: string): string | null {
  if (axios.isCancel(error)) return null;
  if (error instanceof CohortPayloadError) return error.message;
  if (axios.isAxiosError(error)) {
    if (!error.response) return "Connexion au backend impossible.";
    const detail = detailText(error.response.data?.detail);
    if (detail) return detail;
    if (error.response.status === 404) return "Jeu sim-cohort introuvable.";
    return fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export async function fetchCohortMeta(signal: AbortSignal): Promise<CohortMeta> {
  const { data } = await api.get<unknown>(META_URL, { signal });
  if (!isCohortMeta(data)) {
    throw new CohortPayloadError("Réponse /meta non conforme.");
  }
  return data;
}

export async function fetchCohortOverview(
  query: CohortQuery,
  signal: AbortSignal,
): Promise<CohortOverview> {
  const { data } = await api.get<unknown>(OVERVIEW_URL, {
    params: params(query),
    signal,
  });
  if (!isCohortOverview(data)) {
    throw new CohortPayloadError("Réponse /overview non conforme.");
  }
  return data;
}

export async function fetchCohortFlows(
  query: CohortQuery,
  page: { limit: number; offset: number },
  signal: AbortSignal,
): Promise<CohortFlows> {
  const { data } = await api.get<unknown>(FLOWS_URL, {
    params: params(query, page),
    signal,
  });
  if (!isCohortFlows(data)) {
    throw new CohortPayloadError("Réponse /flows non conforme.");
  }
  return data;
}

export async function fetchCohortTrips(
  query: CohortQuery,
  page: { limit: number; offset: number },
  signal: AbortSignal,
): Promise<CohortTrips> {
  const { data } = await api.get<unknown>(TRIPS_URL, {
    params: params(query, page),
    signal,
  });
  if (!isCohortTrips(data)) {
    throw new CohortPayloadError("Réponse /trips non conforme.");
  }
  return data;
}
