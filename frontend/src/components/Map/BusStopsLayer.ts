import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadBusStops(map: maplibregl.Map) {

    const bounds = map.getBounds();

    const response = await api.get("/api/bus-stops", {

        params: {

            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()

        }

    });

    console.log("Arrêts de bus :", response.data.features.length);

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

        map.addLayer({

            id: "bus-stops",

            type: "circle",

            source: "bus-stops",

            paint: {

                "circle-radius": 5,

                "circle-color": "#0066ff",

                "circle-stroke-width": 1,

                "circle-stroke-color": "#ffffff"

            }

        });

    }

}