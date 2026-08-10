import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadRoads(map: maplibregl.Map) {

    const bounds = map.getBounds();

    const response = await api.get("/api/roads", {

        params: {

            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()

        }

    });
    // Affichage des routes
    console.log("Routes :", response.data.features.length);

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

        map.addLayer({

            id: "roads",

            type: "line",

            source: "roads",

            paint: {

                "line-color": "#ff0000",

                "line-width": 2

            }

        });

    }

}