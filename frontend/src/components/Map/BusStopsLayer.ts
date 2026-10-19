import maplibregl from "maplibre-gl";
import api from "../../services/api";
import { addLayerUnderLabels } from "./basemap";

export async function loadBusStops(map: maplibregl.Map, stale?: () => boolean) {
    const bounds = map.getBounds();
    const response = await api.get("/api/bus-stops", {
        params: {
            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()
        }
    });
    if (stale?.() || !map.getStyle()) return;

    const source = map.getSource("bus-stops");

    if (source) {

        (source as maplibregl.GeoJSONSource)
            .setData(response.data);

    }

    else {

        map.addSource("bus-stops", {

            type: "geojson",

            data: response.data

        });

        addLayerUnderLabels(map, {
            id: "bus-stops",
            type: "circle",
            source: "bus-stops",
            layout: { visibility: "none" },
            paint: {
                "circle-radius": 4,
                "circle-color": "#0369a1",
                "circle-stroke-width": 1.5,
                "circle-stroke-color": "#ffffff",
            },
        });

    }

}