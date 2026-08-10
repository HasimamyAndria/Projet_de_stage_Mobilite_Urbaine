import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { loadRoads } from "./RoadsLayer";
import { loadBuildings } from "./BuildingsLayer";
import { loadBusStops } from "./BusStopsLayer";
import { loadBusLines } from "./BusLinesLayer";
import { loadRoute } from "./RouteLayer";
import { loadOdFlows, loadMobilityZones, fitMapToOdZones } from "./OdFlowsLayer";
import { loadKeyPoints } from "./KeyPointsLayer";
import { loadEmploiHabitat } from "./EmploiHabitatLayer";
import { loadHeatmap } from "./HeatmapLayer";
import SearchBar from "./SearchBar";
import KpiPanel, { type KpiMetrics } from "./KpiPanel";
import LayerPanel, { LAYER_DEFS, type LayerKey } from "./LayerPanel";
import MapLegend from "./MapLegend";
import TopMetrics from "./TopMetrics";
import "./AppShell.css";

/** Fond clair type maquette « Carte interactive » (rues / relief lisibles). */
const LIGHT_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap © CARTO",
    },
  },
  layers: [
    {
      id: "carto-light",
      type: "raster",
      source: "carto",
    },
  ],
};

const DEMO_CENTER: [number, number] = [47.5079, -18.8792];
const DEMO_BBOX = {
  west: 47.40,
  south: -18.98,
  east: 47.60,
  north: -18.78,
};

function isInDemoZone(lon: number, lat: number): boolean {
  return (
    lon >= DEMO_BBOX.west &&
    lon <= DEMO_BBOX.east &&
    lat >= DEMO_BBOX.south &&
    lat <= DEMO_BBOX.north
  );
}

function initialVisibility(): Record<LayerKey, boolean> {
  return Object.fromEntries(
    LAYER_DEFS.map((d) => [d.key, d.defaultOn])
  ) as Record<LayerKey, boolean>;
}

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);
  const accuracySourceId = "user-accuracy";
  const visibilityRef = useRef(initialVisibility());
  const [visibility, setVisibility] = useState(initialVisibility);
  const [locateStatus, setLocateStatus] = useState<string | null>(null);
  const [locateBusy, setLocateBusy] = useState(false);
  const [outsideDemo, setOutsideDemo] = useState(false);
  const [metrics, setMetrics] = useState<KpiMetrics>({
    zones: null,
    flowCount: null,
    corridors: null,
    ehAvg: null,
    loading: true,
  });

  const applyVisibility = useCallback(
    (map: maplibregl.Map, next: Record<LayerKey, boolean>) => {
      for (const def of LAYER_DEFS) {
        const value = next[def.key] ? "visible" : "none";
        for (const layerId of def.layerIds) {
          if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, "visibility", value);
          }
        }
      }
    },
    []
  );

  const clearUserLocation = useCallback(() => {
    userMarkerRef.current?.remove();
    userMarkerRef.current = null;
    const map = mapRef.current;
    if (!map) return;
    if (map.getLayer("user-accuracy-fill")) map.removeLayer("user-accuracy-fill");
    if (map.getSource(accuracySourceId)) map.removeSource(accuracySourceId);
  }, []);

  const showUserOnMap = useCallback(
    (lon: number, lat: number, accuracy: number, fly: boolean) => {
      const map = mapRef.current;
      if (!map) return;

      clearUserLocation();

      userMarkerRef.current = new maplibregl.Marker({ color: "#2563eb" })
        .setLngLat([lon, lat])
        .setPopup(
          new maplibregl.Popup({ offset: 16 }).setHTML(
            `<strong>Votre position</strong><br/>${lat.toFixed(5)}, ${lon.toFixed(5)}<br/>±${Math.round(accuracy)} m`
          )
        )
        .addTo(map);

      // Cercle de précision approximatif (degrés)
      const radiusDeg = Math.max(accuracy, 30) / 111320;
      const points: [number, number][] = [];
      for (let i = 0; i <= 64; i++) {
        const a = (i / 64) * Math.PI * 2;
        points.push([
          lon + radiusDeg * Math.cos(a) / Math.cos((lat * Math.PI) / 180),
          lat + radiusDeg * Math.sin(a),
        ]);
      }
      points.push(points[0]);

      map.addSource(accuracySourceId, {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: { type: "Polygon", coordinates: [points] },
        },
      });
      map.addLayer({
        id: "user-accuracy-fill",
        type: "fill",
        source: accuracySourceId,
        paint: {
          "fill-color": "#2563eb",
          "fill-opacity": 0.15,
        },
      });

      if (fly) {
        map.flyTo({
          center: [lon, lat],
          zoom: accuracy > 2000 ? 12 : 15,
          essential: true,
        });
      }
    },
    [clearUserLocation]
  );

  const recenterDemo = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    fitMapToOdZones(map);
    setOutsideDemo(false);
    setLocateStatus("Recadré sur la zone démo Antananarivo.");
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: LIGHT_STYLE,
      center: DEMO_CENTER,
      zoom: 12,
    });

    mapRef.current = map;
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "bottom-right"
    );

    let moveTimer: ReturnType<typeof setTimeout> | undefined;

    async function loadBboxLayers() {
      if (map.getZoom() < 11) return;
      try {
        await loadRoads(map);
        await loadBuildings(map);
        await loadBusStops(map);
        await loadBusLines(map);
        applyVisibility(map, visibilityRef.current);
      } catch (error) {
        console.error("Erreur couches bbox :", error);
      }
    }

    async function loadAnalyticsLayers() {
      try {
        await loadMobilityZones(map);
        await loadHeatmap(map);
        await loadOdFlows(map, 50);
        await loadKeyPoints(map);
        await loadEmploiHabitat(map);
        fitMapToOdZones(map);
        await loadRoute(
          map,
          47.52928,
          -18.903276,
          47.5160582,
          -18.8680788
        );
        applyVisibility(map, visibilityRef.current);
      } catch (error) {
        console.error("Erreur couches OD/analytics :", error);
      }
    }

    map.on("load", () => {
      loadBboxLayers();
      loadAnalyticsLayers();
    });

    map.on("moveend", () => {
      if (moveTimer) clearTimeout(moveTimer);
      moveTimer = setTimeout(() => {
        loadBboxLayers();
      }, 450);
    });

    return () => {
      if (moveTimer) clearTimeout(moveTimer);
      userMarkerRef.current = null;
      map.remove();
    };
  }, [applyVisibility]);

  useEffect(() => {
    visibilityRef.current = visibility;
    const map = mapRef.current;
    if (!map) return;
    applyVisibility(map, visibility);
  }, [visibility, applyVisibility]);

  const onToggle = (key: LayerKey) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const locateUser = () => {
    if (!navigator.geolocation) {
      setLocateStatus("La géolocalisation n’est pas supportée par ce navigateur.");
      return;
    }
    if (
      !window.isSecureContext &&
      location.hostname !== "localhost" &&
      location.hostname !== "127.0.0.1"
    ) {
      setLocateStatus(
        "Géolocalisation bloquée : ouvrez l’app en https ou via localhost."
      );
      return;
    }

    setLocateBusy(true);
    setLocateStatus("Demande GPS en cours (haute précision)…");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocateBusy(false);
        const { latitude, longitude, accuracy } = position.coords;
        const inDemo = isInDemoZone(longitude, latitude);

        if (inDemo) {
          setOutsideDemo(false);
          showUserOnMap(longitude, latitude, accuracy, true);
          setLocateStatus(
            `Vous êtes dans la zone démo : ${latitude.toFixed(5)}, ${longitude.toFixed(5)} (±${Math.round(accuracy)} m)`
          );
          return;
        }

        // Hors Antananarivo : on n'arrache plus la carte de la démo
        setOutsideDemo(true);
        showUserOnMap(longitude, latitude, accuracy, false);
        setLocateStatus(
          `GPS : ${latitude.toFixed(5)}, ${longitude.toFixed(5)} (±${Math.round(accuracy)} m). ` +
            `Hors zone démo Antananarivo — les flux OD / OSM démo ne sont pas ici. ` +
            (accuracy > 2000
              ? "Précision faible (souvent localisation IP Windows) : activez le GPS appareil."
              : "Utilisez « Voir ma position » pour y aller, ou restez sur la démo.")
        );
      },
      (error) => {
        setLocateBusy(false);
        if (error.code === error.PERMISSION_DENIED) {
          setLocateStatus(
            "Permission refusée — icône cadenas du navigateur → Autoriser la localisation."
          );
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          setLocateStatus(
            "Position indisponible — Paramètres Windows → Confidentialité → Localisation = Activé."
          );
        } else if (error.code === error.TIMEOUT) {
          setLocateStatus(
            "Délai dépassé — réessayez (Wi‑Fi + GPS). Sur PC la position est souvent imprécise."
          );
        } else {
          setLocateStatus("Impossible d’obtenir votre position.");
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0,
      }
    );
  };

  const flyToMyGps = () => {
    const marker = userMarkerRef.current;
    if (!marker) {
      locateUser();
      return;
    }
    const { lng, lat } = marker.getLngLat();
    mapRef.current?.flyTo({ center: [lng, lat], zoom: 14, essential: true });
    setLocateStatus(
      `Carte centrée sur votre GPS (${lat.toFixed(5)}, ${lng.toFixed(5)}). Attention : peu/pas de données démo hors Antananarivo.`
    );
  };

  const flyToLocation = (lon: number, lat: number) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom: 15 });
  };

  const navItems = useMemo(
    () => [
      { id: "dashboard", label: "Tableau de bord", active: false, disabled: true },
      { id: "carte", label: "Carte interactive", active: true, disabled: false },
      { id: "od", label: "Flux OD", active: false, disabled: true },
      { id: "zones", label: "Zones critiques", active: false, disabled: true },
      { id: "indicateurs", label: "Analyse & Indicateurs", active: false, disabled: true },
      { id: "simulation", label: "Simulation", active: false, disabled: true },
      { id: "reco", label: "Recommandations", active: false, disabled: true },
    ],
    []
  );

  return (
    <div className="app-shell">
      <aside className="app-nav">
        <div className="app-brand">
          <strong>MobilitySmart</strong>
          <span>Plateforme d&apos;analyse de la mobilité urbaine</span>
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.active ? "active" : undefined}
            disabled={item.disabled}
            title={item.disabled ? "Hors MVP stage" : undefined}
          >
            <span>{item.label}</span>
          </button>
        ))}
        <div className="app-nav-foot">
          Sources démo : OSM · OD synthétique
          <br />
          FastAPI · PostGIS · MapLibre
        </div>
      </aside>

      <div className="app-main">
        <header className="app-top">
          <h1>Carte interactive</h1>
          <p>
            Flux OD, heatmap densité, couches OSM — vue décideur Antananarivo
          </p>
          <TopMetrics
            zones={metrics.zones}
            flowCount={metrics.flowCount}
            corridors={metrics.corridors}
            ehAvg={metrics.ehAvg}
            loading={metrics.loading}
          />
        </header>

        <div className="app-workspace">
          <div className="map-stage">
            <div ref={mapContainer} className="map-canvas" />

            <div className="map-overlay-stack-left">
              <LayerPanel visibility={visibility} onToggle={onToggle} />
              <SearchBar onSelectLocation={flyToLocation} />
            </div>

            <MapLegend />

            <div className="map-overlay-actions">
              <button
                type="button"
                className="map-btn"
                onClick={locateUser}
                disabled={locateBusy}
              >
                {locateBusy ? "GPS…" : "Ma position"}
              </button>
              {outsideDemo && (
                <>
                  <button type="button" className="map-btn" onClick={flyToMyGps}>
                    Voir ma position GPS
                  </button>
                  <button type="button" className="map-btn" onClick={recenterDemo}>
                    Revenir à la démo
                  </button>
                </>
              )}
              {locateStatus && (
                <div className="locate-status" role="status">
                  {locateStatus}
                </div>
              )}
            </div>
          </div>

          <div className="side-panel">
            <KpiPanel onMetrics={setMetrics} />
          </div>
        </div>

        <footer className="app-footer">
          <span>Démo contrôlée · volumes synthétiques · k-anonymité ≥ 5</span>
          <span>Antananarivo · bbox + LIMIT</span>
        </footer>
      </div>
    </div>
  );
}
