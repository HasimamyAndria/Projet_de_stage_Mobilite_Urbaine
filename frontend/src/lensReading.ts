import type { LensFlow, LensPayload, LensQuartier, PickMode } from "./lensTypes";

export type Motif = "travail" | "tous";
export type CorridorSide = "origin" | "destination";
export type ZoomBand = "flux" | "quartiers" | "details";

/** Vitesse retenue pour estimer un temps à partir des kilomètres simulés. */
export const ASSUMED_KMH = 18;

export const MODE_LABELS: Record<string, string> = {
  bus: "Bus",
  taxi: "Taxi",
  marche: "Marche",
  velo: "Vélo",
  voiture: "Voiture",
  car: "Voiture",
};

export function zoomBandOf(zoom: number): ZoomBand {
  if (zoom < 11.2) return "flux";
  if (zoom < 13.2) return "quartiers";
  return "details";
}

export function zoomBandLabel(band: ZoomBand): string {
  if (band === "flux") return "Dézoom : flux principaux";
  if (band === "quartiers") return "Zoom : quartiers";
  return "Zoom important : détails";
}

export function modeLabel(mode: PickMode): string {
  if (mode === "destination") return "DESTINATION";
  if (mode === "corridor") return "ORIGINE → DESTINATION";
  return "ORIGINE";
}

export function readingMode(mode: PickMode, originCount: number, destCount: number): string {
  if (originCount > 0 && destCount > 0) return "ORIGINE → DESTINATION";
  if (destCount > 0 && originCount === 0) return "DESTINATION";
  if (originCount > 0) return "ORIGINE";
  return modeLabel(mode);
}

export function motifLabel(motif: Motif): string {
  return motif === "travail" ? "TRAVAIL" : "TOUS";
}

export function placeName(lens: LensPayload, id: string): string {
  return lens.quartiers.find((item) => item.id === id)?.name ?? id;
}

export function placeNames(lens: LensPayload, ids: string[]): string[] {
  return ids.map((id) => placeName(lens, id));
}

export function arrondissementLabel(lens: LensPayload, originIds: string[], destIds: string[]): string {
  const ids = [...originIds, ...destIds];
  if (!ids.length) return "Tous les arrondissements";
  const names = [
    ...new Set(
      ids
        .map((id) => lens.quartiers.find((item) => item.id === id)?.parent_name)
        .filter((name): name is string => Boolean(name))
    ),
  ];
  return names.join(", ") || "Tous les arrondissements";
}

export function zoneHeadline(
  lens: LensPayload,
  pickMode: PickMode,
  originIds: string[],
  destIds: string[]
): string {
  const origins = placeNames(lens, originIds);
  const dests = placeNames(lens, destIds);
  if (origins.length && dests.length) {
    return `${origins.join(", ")} → ${dests.join(", ")}`;
  }
  if (destIds.length && (pickMode === "destination" || !origins.length)) {
    return `DESTINATION : ${dests.join(", ")}`;
  }
  if (origins.length) return `ORIGINE : ${origins.join(", ")}`;
  if (dests.length) return `DESTINATION : ${dests.join(", ")}`;
  return lens.city.name;
}

export function readingQuestion(
  pickMode: PickMode,
  originIds: string[],
  destIds: string[],
  motif: Motif
): string {
  if (originIds.length && destIds.length) {
    return "Quel volume relie ces origines à ces destinations ?";
  }
  if (destIds.length > 0 && originIds.length === 0) {
    return motif === "travail"
      ? "D'où viennent les personnes qui travaillent dans cette zone ?"
      : "D'où viennent les personnes qui se rendent dans cette zone ?";
  }
  if (originIds.length > 0) {
    return "Où vont les habitants de cette zone ?";
  }
  if (pickMode === "destination") {
    return "Cliquez une destination pour voir d’où viennent les personnes.";
  }
  if (pickMode === "corridor") {
    return "Cliquez une origine, puis une destination, pour lire le volume du flux.";
  }
  return "Cliquez un quartier de départ pour voir où vont ses habitants.";
}

export type ZoneFlags = {
  weight: number;
  critical: boolean;
  desert: boolean;
};

export function zoneFlags(quartier: Pick<LensQuartier, "residents" | "jobs" | "eh_index" | "mean_km" | "outbound_share">): ZoneFlags {
  const weight = quartier.residents + quartier.jobs;
  const critical = quartier.eh_index !== null && quartier.eh_index < 0.45;
  const desert =
    quartier.jobs <= Math.max(20, quartier.residents * 0.12) &&
    (quartier.mean_km ?? 0) >= 8 &&
    quartier.outbound_share >= 0.55;
  return { weight, critical, desert };
}

export function importantIds(quartiers: LensQuartier[]): Set<string> {
  const ranked = [...quartiers].sort(
    (a, b) => zoneFlags(b).weight - zoneFlags(a).weight
  );
  const keep = Math.max(3, Math.ceil(ranked.length * 0.28));
  return new Set(ranked.slice(0, keep).filter((item) => zoneFlags(item).weight > 0).map((item) => item.id));
}

export type BarRow = { id: string; name: string; people: number };

export function tallyFlows(
  flows: LensFlow[],
  idKey: "origin_id" | "destination_id",
  nameKey: "origin_name" | "destination_name"
): BarRow[] {
  const buckets = new Map<string, BarRow>();
  for (const flow of flows) {
    const id = flow[idKey];
    const current = buckets.get(id) ?? { id, name: flow[nameKey], people: 0 };
    current.people += flow.headcount;
    buckets.set(id, current);
  }
  return [...buckets.values()].sort((a, b) => b.people - a.people);
}

export function tallyModes(flows: LensFlow[]): BarRow[] {
  const buckets = new Map<string, BarRow>();
  for (const flow of flows) {
    const id = flow.mode || "autre";
    const current = buckets.get(id) ?? { id, name: MODE_LABELS[id] ?? id, people: 0 };
    current.people += flow.headcount;
    buckets.set(id, current);
  }
  return [...buckets.values()].sort((a, b) => b.people - a.people);
}

export function bucketFlows(
  flows: LensFlow[],
  bins: Array<{ id: string; name: string; test: (flow: LensFlow) => boolean }>
): BarRow[] {
  return bins.map((bin) => ({
    id: bin.id,
    name: bin.name,
    people: flows.reduce((sum, flow) => sum + (bin.test(flow) ? flow.headcount : 0), 0),
  }));
}

export function minutesFromKm(km: number): number {
  return Math.round((km / ASSUMED_KMH) * 60);
}

export function formatKm(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} km`;
}

export function formatMin(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("fr-FR")} min`;
}

export function formatIndex(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
