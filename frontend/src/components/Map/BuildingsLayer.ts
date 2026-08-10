import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadBuildings(map: maplibregl.Map) {

    const bounds = map.getBounds();

    const response = await api.get("/api/buildings", {

        params: {

            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()

        }

    });

    console.log("Bâtiments :", response.data.features.length);

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

        map.addLayer({

            id: "buildings",
            type: "fill",
            source: "buildings",
            paint: {
                "fill-color": "#342e86",
                "fill-opacity": 0.6,
                "fill-outline-color": "#1b1919"
            }

        });

    }

}