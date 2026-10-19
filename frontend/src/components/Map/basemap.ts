import type { AddLayerObject, Map } from "maplibre-gl";

/** Carte lisible : rues, eau, parcs et noms. Les couches Routes / bus de l'appli restent à part. */
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

export function loadQuietBasemap(): Promise<string> {
  return Promise.resolve(STYLE_URL);
}

export function mapRenderOptions() {
  return {
    fadeDuration: 0,
    maxPitch: 0,
    pitchWithRotate: false,
    dragRotate: false,
    touchPitch: false,
    pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
  } as const;
}

/** Les noms du fond restent lisibles au-dessus des tracés activés par l'utilisateur. */
export function addLayerUnderLabels(map: Map, layer: AddLayerObject) {
  if (map.getLayer(layer.id)) return;
  const before = map.getStyle()?.layers?.find((item) => item.type === "symbol")?.id;
  if (before && map.getLayer(before)) map.addLayer(layer, before);
  else map.addLayer(layer);
}
