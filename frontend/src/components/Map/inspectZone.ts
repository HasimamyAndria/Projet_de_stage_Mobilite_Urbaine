import maplibregl from "maplibre-gl";

const INSPECT_LAYERS = [
  "keypoints-zones-fill",
  "emploi-habitat-fill",
  "mobility-zones-fill",
];

function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const map: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return map[char] ?? char;
  });
}

export function zonePopupHtml(props: Record<string, unknown>): string {
  const name = escapeHtml(props.name ?? "Zone");
  const label = escapeHtml(props.label_fr ?? props.label ?? "—");
  const cluster =
    props.cluster_label != null
      ? escapeHtml(props.cluster_label)
      : props.cluster_id != null
        ? escapeHtml(`Groupe ${Number(props.cluster_id) + 1}`)
        : "—";
  const pop = escapeHtml(props.population_proxy ?? "—");
  const jobs = escapeHtml(props.jobs_proxy ?? "—");
  const eh =
    props.eh_index != null && props.eh_index !== ""
      ? Number(props.eh_index).toFixed(2)
      : "—";

  return `<div class="zone-popup">
    <strong>${name}</strong>
    <p>Label M2 : ${label}</p>
    <p>Cluster : ${cluster}</p>
    <p>Population proxy : ${pop} · Emplois proxy : ${jobs}</p>
    <p>Indice M6 : ${eh}</p>
  </div>`;
}

type InspectableMap = maplibregl.Map & { __zoneInspect?: boolean };

export function bindZoneInspect(
  map: maplibregl.Map,
  shouldIgnore: () => boolean
) {
  const tagged = map as InspectableMap;
  if (tagged.__zoneInspect) return;
  tagged.__zoneInspect = true;

  map.on("click", (event) => {
    if (shouldIgnore()) return;
    const layers = INSPECT_LAYERS.filter((id) => Boolean(map.getLayer(id)));
    if (!layers.length) return;
    const feature = map.queryRenderedFeatures(event.point, { layers })[0];
    if (!feature) return;
    new maplibregl.Popup({ offset: 12, closeButton: true })
      .setLngLat(event.lngLat)
      .setHTML(zonePopupHtml((feature.properties || {}) as Record<string, unknown>))
      .addTo(map);
  });
}
