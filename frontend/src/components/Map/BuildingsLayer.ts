import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { addLayerUnderLabels } from "./basemap";

export async function loadBuildings(map: maplibregl.Map, stale?: () => boolean) {
    const bounds = map.getBounds();
    const response = await api.get("/api/buildings", {
        params: {
            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()
        }
    });
    if (stale?.() || !map.getStyle()) return;

    const source = map.getSource("buildings");

    if (source) {

        (source as maplibregl.GeoJSONSource)
            .setData(response.data);

    }

    else {

        map.addSource("buildings", {
            type: "geojson",
            data: response.data
        });

        addLayerUnderLabels(map, {
            id: "buildings",
            type: "fill",
            source: "buildings",
            layout: { visibility: "none" },
            paint: {
                "fill-color": "#64748b",
                "fill-opacity": 0.35,
                "fill-outline-color": "#334155",
            },
        });

    }

}