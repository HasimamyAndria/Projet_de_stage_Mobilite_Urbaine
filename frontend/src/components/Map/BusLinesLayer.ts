import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadBusLines(map: maplibregl.Map) {

    const bounds = map.getBounds();

    console.log("Chargement des lignes de bus...");

    const response = await api.get("/api/bus-lines", {

        params: {

            minLon: bounds.getWest(),
            minLat: bounds.getSouth(),
            maxLon: bounds.getEast(),
            maxLat: bounds.getNorth()

        }

    });

    console.log(
        "Nombre de lignes :",
        response.data.features.length
    );

    const source = map.getSource("bus-lines");

    if (source) {

        console.log("Mise à jour des lignes de bus");

        (source as maplibregl.GeoJSONSource)
            .setData(response.data);

    }

    else {

        console.log("Création de la couche Bus Lines");

        map.addSource("bus-lines", {
            type: "geojson",
            data: response.data

        });

        map.addLayer({

            id: "bus-lines",
            type: "line",
            source: "bus-lines",
            paint: {

                "line-color": "#0066ff",
                "line-width": 4,
                "line-opacity": 0.9

            }

        });

    }

}