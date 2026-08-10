import maplibregl from "maplibre-gl";
import api from "../../services/api";

export async function loadRoute(
    map: maplibregl.Map,
    startLon: number,
    startLat: number,
    endLon: number,
    endLat: number
) {

    try {

        console.log("Calcul de l'itinéraire...");

        const response = await api.get("/api/route", {

            params: {

                startLon,
                startLat,
                endLon,
                endLat

            }

        });


        const data = response.data;


        // Supprime l'ancien itinéraire si présent

        if (map.getLayer("route-layer")) {

            map.removeLayer("route-layer");

        }

        if (map.getSource("route-source")) {

            map.removeSource("route-source");

        }


        // Ajout de la source GeoJSON

        map.addSource("route-source", {

            type: "geojson",

            data

        });


        // Ajout de la couche de l'itinéraire

        map.addLayer({

            id: "route-layer",

            type: "line",

            source: "route-source",

            paint: {

                "line-color": "#00AAFF",
                "line-width": 6

            }

        });


        console.log("Itinéraire affiché.");

    }

    catch (error) {

        console.error(
            "Erreur calcul itinéraire :",
            error
        );

    }

}