import maplibregl from "maplibre-gl";
import api from "../../services/api";

const SOURCE_ID = "emploi-habitat";
const FILL_ID = "emploi-habitat-fill";
const LINE_ID = "emploi-habitat-line";

export type EmploiHabitatSummary = {
    zone_count: number;
    scored_count: number;
    avg_score: number | null;
    min_score: number | null;
    max_score: number | null;
    min_zone_name: string | null;
    max_zone_name: string | null;
};

export type EmploiHabitatPayload = {
    type: "FeatureCollection";
    features: Array<Record<string, unknown>>;
    summary: EmploiHabitatSummary;
    formula: string;
    synthetic: boolean;
    note: string;
};

/**
 * M6 — Couche colorée par indice emploi-habitat (eh_index ∈ [0, 1]).
 * Rouge = déséquilibre fort, vert = équilibre emplois/habitat.
 */
export async function loadEmploiHabitat(
    map: maplibregl.Map
): Promise<EmploiHabitatPayload> {
    console.log("===== EMPLOI-HABITAT LAYER (M6) =====");

    const response = await api.get("/api/emploi-habitat");
    const data = response.data as EmploiHabitatPayload;

    console.log("M6 features :", data.features?.length ?? 0);
    console.log("M6 summary :", data.summary);
    console.log("M6 formule :", data.formula);

    const geojson = {
        type: "FeatureCollection" as const,
        features: data.features,
    };

    const source = map.getSource(SOURCE_ID);

    if (source) {
        (source as maplibregl.GeoJSONSource).setData(geojson);
    } else {
        map.addSource(SOURCE_ID, {
            type: "geojson",
            data: geojson,
        });

        // Remplissage coloré selon eh_index
        map.addLayer({
            id: FILL_ID,
            type: "fill",
            source: SOURCE_ID,
            paint: {
                "fill-color": [
                    "interpolate",
                    ["linear"],
                    ["coalesce", ["get", "eh_index"], 0],
                    0.0, "#b91c1c", // déséquilibre fort
                    0.35, "#f59e0b",
                    0.6, "#84cc16",
                    0.85, "#15803d", // équilibre
                ],
                "fill-opacity": 0.38,
            },
        });

        map.addLayer({
            id: LINE_ID,
            type: "line",
            source: SOURCE_ID,
            paint: {
                "line-color": "#14532d",
                "line-width": 1.5,
            },
        });
    }

    // Évite le chevauchement avec les fills M2 / grille brute
    // (on garde les corridors OD visibles)
    for (const layerId of [
        "keypoints-zones-fill",
        "keypoints-zones-line",
        "mobility-zones-fill",
        "mobility-zones-outline",
    ]) {
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, "visibility", "none");
        }
    }

    return data;
}
