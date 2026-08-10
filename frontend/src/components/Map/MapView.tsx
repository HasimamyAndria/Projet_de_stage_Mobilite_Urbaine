import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { loadRoads } from "./RoadsLayer";
import { loadBuildings } from "./BuildingsLayer";
import { loadBusStops } from "./BusStopsLayer";
import { loadBusLines } from "./BusLinesLayer";
import { loadRoute } from "./RouteLayer";
import SearchBar from "./SearchBar";


export default function MapView() {

    //--------------------------------------------------
    // Référence HTML du conteneur de la carte
    //--------------------------------------------------
    const mapContainer = useRef<HTMLDivElement>(null);
    //--------------------------------------------------
    // Référence MapLibre
    //--------------------------------------------------
    const mapRef = useRef<maplibregl.Map | null>(null);
    //--------------------------------------------------
    // Initialisation de la carte
    //--------------------------------------------------

    useEffect(() => {

        if (!mapContainer.current) return;
        console.log("Initialisation de la carte...");
        const map = new maplibregl.Map({

            container: mapContainer.current,
            style: "https://demotiles.maplibre.org/style.json",
            center: [47.5079, -18.8792],
            zoom: 13

        });

        //--------------------------------------------------
        // Sauvegarde de la référence
        //--------------------------------------------------

        mapRef.current = map;

        //--------------------------------------------------
        // Boutons zoom + rotation
        //--------------------------------------------------

        map.addControl(
            new maplibregl.NavigationControl()
        );

        //--------------------------------------------------
        // Chargement de toutes les couches
        //--------------------------------------------------

        async function loadAllLayers() {

            try {

                console.log("Chargement des couches...");

                await loadRoads(map);
                await loadBuildings(map);
                await loadBusStops(map);
                await loadBusLines(map);
                await loadRoute(
                  map,
                    47.526175,
                    -18.893910,
                    47.5079,
                    -18.8792
                );
                
                console.log(
                    "Toutes les couches sont chargées."
                );

            }

            catch (error) {

                console.error(
                    "Erreur chargement couches :",
                    error
                );

            }

        }

        //--------------------------------------------------
        // Chargement initial
        //--------------------------------------------------

        map.on("load", () => {

            console.log("Carte chargée");
            loadAllLayers();

        });

        //--------------------------------------------------
        // Rechargement après déplacement
        //--------------------------------------------------

        map.on("moveend", () => {

            console.log("Carte déplacée");
            loadAllLayers();

        });

        //--------------------------------------------------
        // Nettoyage
        //--------------------------------------------------

        return () => {

            console.log("Fermeture de la carte");
            map.remove();

        };

    }, []);

    //--------------------------------------------------
    // Fonction GPS
    //--------------------------------------------------

    const locateUser = () => {

        console.log("Demande GPS...");

        if (!navigator.geolocation) {

            alert(
                "La géolocalisation n'est pas supportée."
            );

            return;

        }

        navigator.geolocation.getCurrentPosition(

            //--------------------------------------------------
            // Succès
            //--------------------------------------------------

            (position) => {

                const latitude =
                    position.coords.latitude;

                const longitude =
                    position.coords.longitude;

                console.log(
                    "===== POSITION GPS ====="
                );

                console.log(
                    "Latitude :",
                    latitude
                );

                console.log(
                    "Longitude :",
                    longitude
                );

                if (!mapRef.current) return;

                //--------------------------------------------------
                // Marqueur utilisateur
                //--------------------------------------------------

                new maplibregl.Marker({

                    color: "#0066ff"

                })

                    .setLngLat([
                        longitude,
                        latitude
                    ])

                    .addTo(mapRef.current);

                //--------------------------------------------------
                // Déplacement de la carte
                //--------------------------------------------------

                mapRef.current.flyTo({

                    center: [
                        longitude,
                        latitude
                    ],

                    zoom: 16,

                    essential: true

                });

            },

            //--------------------------------------------------
            // Erreur GPS
            //--------------------------------------------------

            (error) => {

                console.error(
                    "Erreur GPS :",
                    error
                );

                alert(
                    "Impossible d'obtenir votre position."
                );

            }

        );

    };

    const flyToLocation = (

            lon: number,
            lat: number

        ) => {

            if (!mapRef.current)
                return;

            mapRef.current.flyTo({

                center: [

                    lon,
                    lat

                ],

                zoom: 17

            });
    };   

    //--------------------------------------------------
    // Interface
    //--------------------------------------------------

    return (

        <>

            {/* Bouton GPS */}

            <button

                onClick={locateUser}

                style={{

                    position: "absolute",
                    top: "10px",
                    left: "10px",
                    zIndex: 9999,
                    padding: "10px",
                    border: "none",
                    borderRadius: "8px",
                    backgroundColor: "#2563eb",
                    color: "white",
                    cursor: "pointer"

                }}

            >

                📍 Ma position

            </button>

            {/* Carte */}
            <SearchBar
                 onSelectLocation={
                    flyToLocation
                }
/>    
            <div

                ref={mapContainer}
                style={{
                    width: "100vw",
                    height: "100vh"
                }}

            />

        </>

    );

}