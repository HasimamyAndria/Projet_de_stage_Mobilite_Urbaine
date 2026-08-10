import maplibregl from "maplibre-gl";
import api from "../../services/api";

const ZONES_SOURCE = "keypoints-zones";
const ZONES_FILL = "keypoints-zones-fill";
const ZONES_LINE = "keypoints-zones-line";
const CORRIDORS_SOURCE = "keypoints-corridors";
const CORRIDORS_LINE = "keypoints-corridors-line";

/**
 * M2 — Affiche zones classifiées + corridors.
 * Couleurs :
 * - dortoir = violet
 * - pôle emploi = orange
 * - mixte = bleu clair
 * - corridor = rouge épais
 */
export async function loadKeyPoints(map: maplibregl.Map) {
    console.log("===== KEYPOINTS LAYER (M2) =====");

    const response = await api.get("/api/keypoints", {
        params: { corridor_top_n: 5 },
    });

    const data = response.data;
    console.log("Keypoints counts :", data.counts);
    console.log("Règles :", data.rules);

    // --- Zones classifiées ---
    const zonesData = data.zones;
    const zonesSource = map.getSource(ZONES_SOURCE);

    if (zonesSource) {
        (zonesSource as maplibregl.GeoJSONSource).setData(zonesData);
    } else {
        map.addSource(ZONES_SOURCE, {
            type: "geojson",
            data: zonesData,
        });

        map.addLayer({
            id: ZONES_FILL,
            type: "fill",
            source: ZONES_SOURCE,
            paint: {
                "fill-color": [
                    "match",
                    ["get", "label"],
                    "dormitory", "#7c3aed",
                    "employment", "#ea580c",
                    "balanced", "#38bdf8",
                    "#94a3b8",
                ],
                "fill-opacity": 0.28,
            },
        });

        map.addLayer({
            id: ZONES_LINE,
            type: "line",
            source: ZONES_SOURCE,
            paint: {
                "line-color": [
                    "match",
                    ["get", "label"],
                    "dormitory", "#5b21b6",
                    "employment", "#c2410c",
                    "balanced", "#0284c7",
                    "#64748b",
                ],
                "line-width": 2,
            },
        });
    }

    // --- Corridors ---
    const corridorsData = data.corridors;
    const corridorsSource = map.getSource(CORRIDORS_SOURCE);

    if (corridorsSource) {
        (corridorsSource as maplibregl.GeoJSONSource).setData(corridorsData);
    } else {
        map.addSource(CORRIDORS_SOURCE, {
            type: "geojson",
            data: corridorsData,
        });

        map.addLayer({
            id: CORRIDORS_LINE,
            type: "line",
            source: CORRIDORS_SOURCE,
            layout: {
                "line-cap": "round",
                "line-join": "round",
            },
            paint: {
                "line-color": "#dc2626",
                "line-width": 5,
                "line-opacity": 0.9,
            },
        });
    }

    // Masquer l'ancienne grille uniforme si présente (évite double couche)
    if (map.getLayer("mobility-zones-fill")) {
        map.setLayoutProperty("mobility-zones-fill", "visibility", "none");
    }
    if (map.getLayer("mobility-zones-outline")) {
        map.setLayoutProperty("mobility-zones-outline", "visibility", "none");
    }

    console.log(
        `Zones keypoints : ${zonesData.features?.length ?? 0}, ` +
        `corridors : ${corridorsData.features?.length ?? 0}`
    );

    return data;
}
