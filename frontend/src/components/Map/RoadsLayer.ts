import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { addLayerUnderLabels } from "./basemap";

export async function loadRoads(map: maplibregl.Map, stale?: () => boolean) {
    const bounds = map.getBounds();
    const response = await api.get("/api/roads", {
        params: {
            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()
        }
    });
    if (stale?.() || !map.getStyle()) return;

    const source = map.getSource("roads");

    if (source) {

        (source as maplibregl.GeoJSONSource)
            .setData(response.data);

    }

    else {

        map.addSource("roads", {

            type: "geojson",

            data: response.data
        
        });

        addLayerUnderLabels(map, {
            id: "roads",
            type: "line",
            source: "roads",
            layout: { visibility: "none" },
            paint: {
                "line-color": "#1e3a8a",
                "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.7, 14, 1.8, 16, 3],
                "line-opacity": 0.9,
            },
        });

    }

}