import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadBusLines(map: maplibregl.Map) {
    const bounds = map.getBounds();

    const response = await api.get("/api/bus-lines", {
        params: {
            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth(),
        },
    });

    const source = map.getSource("bus-lines");

    if (source) {
        (source as maplibregl.GeoJSONSource).setData(response.data);
        return;
    }

    map.addSource("bus-lines", {
        type: "geojson",
        data: response.data,
    });

    map.addLayer({
        id: "bus-lines",
        type: "line",
        source: "bus-lines",
        paint: {
            "line-color": "#0066ff",
            "line-width": 4,
            "line-opacity": 0.9,
        },
    });
}
