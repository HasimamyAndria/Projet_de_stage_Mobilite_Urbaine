import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { addLayerUnderLabels } from "./basemap";

export async function loadBusLines(map: maplibregl.Map, stale?: () => boolean) {
    const bounds = map.getBounds();

    const response = await api.get("/api/bus-lines", {
        params: {
            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth(),
        },
    });

    if (stale?.() || !map.getStyle()) return;

    const source = map.getSource("bus-lines");

    if (source) {
        (source as maplibregl.GeoJSONSource).setData(response.data);
        return;
    }

    map.addSource("bus-lines", {
        type: "geojson",
        data: response.data,
    });

    addLayerUnderLabels(map, {
        id: "bus-lines",
        type: "line",
        source: "bus-lines",
        layout: { visibility: "none" },
        paint: {
            "line-color": "#0369a1",
            "line-width": 2.5,
            "line-opacity": 0.85,
        },
    });
}
