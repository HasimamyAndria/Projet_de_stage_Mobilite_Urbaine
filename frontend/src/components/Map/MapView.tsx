import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { loadRoads } from "./RoadsLayer";
import { loadBuildings } from "./BuildingsLayer";
import { loadBusStops } from "./BusStopsLayer";
import { loadBusLines } from "./BusLinesLayer";
import { loadOdFlows, loadMobilityZones, fitMapToBBox } from "./OdFlowsLayer";
import { loadKeyPoints } from "./KeyPointsLayer";
import { loadEmploiHabitat } from "./EmploiHabitatLayer";
import { loadHeatmap } from "./HeatmapLayer";
import { DEMO_ROUTE, loadRoute } from "./RouteLayer";
import { bindZoneInspect } from "./inspectZone";
import {
  STAGE_NAV,
  VIEW_COPY,
  applyViewPreset,
  type StageView,
} from "./stageViews";
import SearchBar from "./SearchBar";
import CitySelector, { type ActiveCity } from "./CitySelector";
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

const DEFAULT_CITY: ActiveCity = {
  name: "Antananarivo",
  display_name: "Antananarivo, Madagascar",
  country: "Madagascar",
  lon: 47.5079,
  lat: -18.8792,
  west: 47.45,
  south: -18.95,
  east: 47.565,
  north: -18.82,
  osm_ready: true,
};

function isInCityBBox(lon: number, lat: number, city: ActiveCity): boolean {
  return (
    lon >= city.west &&
    lon <= city.east &&
    lat >= city.south &&
    lat <= city.north
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
  const cityRef = useRef<ActiveCity>(DEFAULT_CITY);
  const startMarkerRef = useRef<maplibregl.Marker | null>(null);
  const endMarkerRef = useRef<maplibregl.Marker | null>(null);
  const routePickRef = useRef<"off" | "start" | "end">("off");
  const [visibility, setVisibility] = useState(initialVisibility);
  const [locateStatus, setLocateStatus] = useState<string | null>(null);
  const [locateBusy, setLocateBusy] = useState(false);
  const [outsideCity, setOutsideCity] = useState(false);
  const [activeCity, setActiveCity] = useState<ActiveCity>(DEFAULT_CITY);
  const [dataEpoch, setDataEpoch] = useState(0);
  const [stageView, setStageView] = useState<StageView>("carte");
  const [routeBusy, setRouteBusy] = useState(false);
  const [routePickMode, setRoutePickMode] = useState<"off" | "start" | "end">(
    "off"
  );
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<KpiMetrics>({
    zones: null,
    flowCount: null,
    corridors: null,
    ehAvg: null,
    loading: true,
  });

  useEffect(() => {
    if (!locateStatus) return;
    const timer = window.setTimeout(() => setLocateStatus(null), 8000);
    return () => window.clearTimeout(timer);
  }, [locateStatus]);

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

  const clearRouteMarkers = useCallback(() => {
    startMarkerRef.current?.remove();
    endMarkerRef.current?.remove();
    startMarkerRef.current = null;
    endMarkerRef.current = null;
  }, []);

  const placeRouteMarker = useCallback(
    (which: "start" | "end", lon: number, lat: number) => {
      const map = mapRef.current;
      if (!map) return;
      const existing = which === "start" ? startMarkerRef : endMarkerRef;
      existing.current?.remove();
      existing.current = new maplibregl.Marker({
        color: which === "start" ? "#16a34a" : "#dc2626",
      })
        .setLngLat([lon, lat])
        .setPopup(
          new maplibregl.Popup({ offset: 12 }).setHTML(
            `<strong>${which === "start" ? "Départ A" : "Arrivée B"}</strong>`
          )
        )
        .addTo(map);
    },
    []
  );

  const runRoute = useCallback(
    async (startLon: number, startLat: number, endLon: number, endLat: number) => {
      const map = mapRef.current;
      if (!map) return;
      setRouteBusy(true);
      setLocateStatus("Calcul de l’itinéraire A→B (réseau, pas une desire line)…");
      try {
        placeRouteMarker("start", startLon, startLat);
        placeRouteMarker("end", endLon, endLat);
        const result = await loadRoute(
          map,
          startLon,
          startLat,
          endLon,
          endLat,
          true
        );
        setVisibility((prev) => ({ ...prev, route: true }));
        if (result.snappedStart) {
          placeRouteMarker(
            "start",
            result.snappedStart.lon,
            result.snappedStart.lat
          );
        }
        if (result.snappedEnd) {
          placeRouteMarker("end", result.snappedEnd.lon, result.snappedEnd.lat);
        }
        if (result.count === 0) {
          setLocateStatus(
            result.detail ||
              "Pas d’itinéraire : cliquez plus près d’une rue du réseau OSM."
          );
        } else if (result.adjusted) {
          setLocateStatus(
            `Itinéraire : ${result.count} segments. ${result.detail}`
          );
        } else {
          setLocateStatus(
            `Itinéraire A→B : ${result.count} segments (pgRouting). Distinct des flux OD.`
          );
        }
      } catch (error) {
        console.error(error);
        setLocateStatus("Impossible de calculer l’itinéraire (API).");
      } finally {
        setRouteBusy(false);
        routePickRef.current = "off";
        setRoutePickMode("off");
        const canvas = mapRef.current?.getCanvas();
        if (canvas) canvas.style.cursor = "";
      }
    },
    [placeRouteMarker]
  );

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

      const radiusDeg = Math.max(accuracy, 30) / 111320;
      const points: [number, number][] = [];
      for (let i = 0; i <= 64; i++) {
        const a = (i / 64) * Math.PI * 2;
        points.push([
          lon + (radiusDeg * Math.cos(a)) / Math.cos((lat * Math.PI) / 180),
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

  const flyToCity = useCallback((city: ActiveCity, duration = 1100) => {
    const map = mapRef.current;
    if (!map || !map.loaded()) return false;
    fitMapToBBox(map, city, duration);
    return true;
  }, []);

  const reloadAnalytics = useCallback(async () => {
    const map = mapRef.current;
    if (!map) return;
    try {
      await loadMobilityZones(map);
      await loadHeatmap(map);
      await loadOdFlows(map, 50);
      await loadKeyPoints(map);
      await loadEmploiHabitat(map);
      applyVisibility(map, visibilityRef.current);
      setAnalyticsError(null);
    } catch (error) {
      console.error("Erreur rechargement analytics :", error);
      setAnalyticsError(
        "Impossible de charger les couches analytiques. Vérifie l’API et le seed OD."
      );
    }
  }, [applyVisibility]);

  const onCityActivated = useCallback(
    (city: ActiveCity, meta?: { seeding?: boolean }) => {
      cityRef.current = city;
      setActiveCity(city);
      setOutsideCity(false);
      setLocateStatus(null);
      const moved = flyToCity(city);
      if (!moved) {
        // Carte pas encore prête : cadrage au load.
        return;
      }
      if (!meta?.seeding) {
        setDataEpoch((n) => n + 1);
        void reloadAnalytics();
      }
    },
    [flyToCity, reloadAnalytics]
  );

  const recenterCity = useCallback(() => {
    const city = cityRef.current;
    if (!flyToCity(city, 800)) return;
    setOutsideCity(false);
    setLocateStatus(`Recadré sur ${city.display_name || city.name}.`);
  }, [flyToCity]);

  useEffect(() => {
    if (!mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: LIGHT_STYLE,
      center: [DEFAULT_CITY.lon, DEFAULT_CITY.lat],
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
        fitMapToBBox(map, cityRef.current);
        applyVisibility(map, visibilityRef.current);
        setAnalyticsError(null);
      } catch (error) {
        console.error("Erreur couches OD/analytics :", error);
        setAnalyticsError(
          "Impossible de charger les couches analytiques. Vérifie l’API et le seed OD."
        );
      }
    }

    map.on("load", () => {
      loadBboxLayers();
      loadAnalyticsLayers();
      bindZoneInspect(map, () => routePickRef.current !== "off");
    });

    map.on("click", (event) => {
      const step = routePickRef.current;
      if (step === "off") return;
      const { lng, lat } = event.lngLat;
      if (step === "start") {
        placeRouteMarker("start", lng, lat);
        routePickRef.current = "end";
        setRoutePickMode("end");
        setLocateStatus("Cliquez l’arrivée B sur la carte.");
        return;
      }
      void runRoute(
        startMarkerRef.current?.getLngLat().lng ?? lng,
        startMarkerRef.current?.getLngLat().lat ?? lat,
        lng,
        lat
      );
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
      startMarkerRef.current?.remove();
      endMarkerRef.current?.remove();
      map.remove();
    };
  }, [applyVisibility, placeRouteMarker, runRoute]);

  useEffect(() => {
    visibilityRef.current = visibility;
    const map = mapRef.current;
    if (!map) return;
    applyVisibility(map, visibility);
  }, [visibility, applyVisibility]);

  const onToggle = (key: LayerKey) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const onStageNav = (view: StageView) => {
    setStageView(view);
    setVisibility((prev) => applyViewPreset(prev, view));
  };

  const startDemoRoute = () => {
    routePickRef.current = "off";
    void runRoute(
      DEMO_ROUTE.startLon,
      DEMO_ROUTE.startLat,
      DEMO_ROUTE.endLon,
      DEMO_ROUTE.endLat
    );
  };

  const startPickRoute = () => {
    const map = mapRef.current;
    clearRouteMarkers();
    routePickRef.current = "start";
    setRoutePickMode("start");
    if (map) map.getCanvas().style.cursor = "crosshair";
    setLocateStatus("Cliquez le départ A, puis l’arrivée B.");
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
        const city = cityRef.current;
        const inCity = isInCityBBox(longitude, latitude, city);

        if (inCity) {
          setOutsideCity(false);
          showUserOnMap(longitude, latitude, accuracy, true);
          setLocateStatus(
            `Vous êtes dans ${city.name} : ${latitude.toFixed(5)}, ${longitude.toFixed(5)} (±${Math.round(accuracy)} m)`
          );
          return;
        }

        setOutsideCity(true);
        showUserOnMap(longitude, latitude, accuracy, false);
        setLocateStatus(
          `GPS : ${latitude.toFixed(5)}, ${longitude.toFixed(5)} (±${Math.round(accuracy)} m). ` +
            `Hors de la ville active (${city.name}). ` +
            (accuracy > 2000
              ? "Précision faible : activez le GPS appareil."
              : "Utilisez « Voir ma position » ou revenez à la ville.")
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
      `Carte centrée sur votre GPS (${lat.toFixed(5)}, ${lng.toFixed(5)}).`
    );
  };

  const flyToLocation = (lon: number, lat: number) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom: 15 });
  };

  const cityLabel = activeCity.display_name || activeCity.name;
  const viewCopy = VIEW_COPY[stageView];

  return (
    <div className="app-shell">
      <aside className="app-nav">
        <div className="app-brand">
          <strong>MobilitySmart</strong>
          <span>Plateforme multi-villes · OSM + OD estimée</span>
        </div>
        {STAGE_NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            className={stageView === item.id ? "active" : undefined}
            onClick={() => onStageNav(item.id)}
          >
            <span>{item.label}</span>
          </button>
        ))}
        <div className="app-nav-foot">
          Sources : OSM · OD gravitaire
          <br />
          FastAPI · PostGIS · MapLibre
        </div>
      </aside>

      <div className="app-main">
        <header className="app-top">
          <h1>{viewCopy.title}</h1>
          <p>
            {viewCopy.subtitle} · {cityLabel}
            {!activeCity.osm_ready ? " (OSM à importer)" : ""}
          </p>
          {!activeCity.osm_ready && (
            <p className="app-banner warn" role="status">
              OSM manquant pour cette ville : importer un extract Geofabrik
              (osm2pgsql) puis réactiver la ville.
            </p>
          )}
          {analyticsError && (
            <p className="app-banner error" role="alert">
              {analyticsError}
            </p>
          )}
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

            <div className="map-chrome-top">
              <SearchBar onSelectLocation={flyToLocation} />
              <CitySelector onActivated={onCityActivated} />
              <LayerPanel visibility={visibility} onToggle={onToggle} />
            </div>

            <div className="map-chrome-bottom">
              <MapLegend visibility={visibility} />
              {locateStatus && (
                <div className="locate-status" role="status">
                  <p>{locateStatus}</p>
                  <button
                    type="button"
                    className="locate-dismiss"
                    onClick={() => setLocateStatus(null)}
                    aria-label="Fermer le message"
                  >
                    ×
                  </button>
                </div>
              )}
              <div className="map-overlay-actions">
                <button
                  type="button"
                  className="map-btn"
                  onClick={startDemoRoute}
                  disabled={routeBusy}
                >
                  {routeBusy ? "Itinéraire…" : "Itinéraire démo"}
                </button>
                <button
                  type="button"
                  className={routePickMode !== "off" ? "map-btn is-picking" : "map-btn"}
                  onClick={startPickRoute}
                  disabled={routeBusy}
                >
                  Choisir A et B
                </button>
                <button
                  type="button"
                  className="map-btn"
                  onClick={locateUser}
                  disabled={locateBusy}
                >
                  {locateBusy ? "GPS…" : "Ma position"}
                </button>
                {outsideCity && (
                  <>
                    <button type="button" className="map-btn" onClick={flyToMyGps}>
                      Voir ma position GPS
                    </button>
                    <button type="button" className="map-btn" onClick={recenterCity}>
                      Revenir à la ville
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="side-panel">
            <KpiPanel onMetrics={setMetrics} refreshKey={dataEpoch} />
          </div>
        </div>

        <footer className="app-footer">
          <span>
            © OpenStreetMap © CARTO ·{" "}
            {activeCity.osm_ready ? "OSM prêt" : "OSM manquant"} · OD gravitaire
          </span>
          <span>{cityLabel}</span>
        </footer>
      </div>
    </div>
  );
}
