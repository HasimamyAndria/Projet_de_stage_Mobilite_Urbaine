import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { loadRoads } from "./RoadsLayer";
import { loadBuildings } from "./BuildingsLayer";
import { loadBusStops } from "./BusStopsLayer";
import { loadBusLines } from "./BusLinesLayer";
import { loadOdFlows, loadMobilityZones, fitMapToBBox, applyOdHour } from "./OdFlowsLayer";
import { loadKeyPoints } from "./KeyPointsLayer";
import { loadEmploiHabitat } from "./EmploiHabitatLayer";
import { loadRecommendations } from "./RecommendationsLayer";
import { loadSatellites } from "./SatellitesLayer";
import { DEMO_ROUTE, loadRoute } from "./RouteLayer";
import { bindZoneInspect } from "./inspectZone";
import {
  PERSONAS,
  STAGE_NAV,
  VIEW_COPY,
  applyViewPreset,
  type PersonaId,
  type StageView,
} from "./stageViews";
import NavIcon from "./NavIcon";
import SearchBar from "./SearchBar";
import CitySelector, { type ActiveCity } from "./CitySelector";
import LayerPanel, { LAYER_DEFS, type LayerKey } from "./LayerPanel";
import MapLegend from "./MapLegend";
import FlowFilters from "../FlowFilters";
import HourAnimator from "../HourAnimator";
import OdMatrixPanel from "../OdMatrixPanel";
import KeyPointsPanel from "../KeyPointsPanel";
import RecoPanel from "../RecoPanel";
import SimulationPanel from "../SimulationPanel";
import HomeKpis, { type HomePeriod } from "../HomeKpis";
import HomeZonePanel from "../HomeZonePanel";
import LensPanel from "../LensPanel";
import ReportsView from "../ReportsView";
import SpecProcessPanel from "../SpecProcessPanel";
import OdContextBar from "./OdContextBar";
import {
  setOdVisible,
  setScenarioVisible,
  showScenario as showWhatIf,
  type ScenarioPayload,
} from "./ScenarioLayer";
import EmploiHabitatPanel from "../EmploiHabitatPanel";
import DashboardView from "../DashboardView";
import DiaryView from "../DiaryView";
import {
  clearTerritory,
  paintTerritory,
  setTerritoryClicksBlocked,
  setTerritoryPick,
} from "./TerritoryLensLayer";
import { DEFAULT_OD_FILTERS, type OdFilters } from "../../types";
import type { LensPayload, PickMode } from "../../lensTypes";
import {
  arrondissementLabel,
  motifLabel,
  readingMode,
  type CorridorSide,
  type Motif,
} from "../../lensReading";
import axios from "axios";
import api from "../../services/api";
import { loadQuietBasemap, mapRenderOptions } from "./basemap";
import "./AppShell.css";

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

function toggleIds(current: string[], ids: string[]): string[] {
  const next = new Set(current);
  const allOn = ids.every((id) => next.has(id));
  if (allOn) {
    for (const id of ids) next.delete(id);
  } else {
    for (const id of ids) next.add(id);
  }
  return [...next];
}

function lensErrorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response
    ?.data?.detail;
  if (detail) return String(detail);
  return "Impossible de charger la lecture par quartier. Vérifie le backend.";
}

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);
  const accuracySourceId = "user-accuracy";
  const [visibility, setVisibility] = useState(() =>
    applyViewPreset(initialVisibility(), "demarche")
  );
  const visibilityRef = useRef(visibility);
  const cityRef = useRef<ActiveCity>(DEFAULT_CITY);
  const filtersRef = useRef<OdFilters>(DEFAULT_OD_FILTERS);
  const [filters, setFilters] = useState<OdFilters>(DEFAULT_OD_FILTERS);
  const [playing, setPlaying] = useState(false);
  const startMarkerRef = useRef<maplibregl.Marker | null>(null);
  const endMarkerRef = useRef<maplibregl.Marker | null>(null);
  const routePickRef = useRef<"off" | "start" | "end">("off");
  const [locateStatus, setLocateStatus] = useState<string | null>(null);
  const [locateBusy, setLocateBusy] = useState(false);
  const [outsideCity, setOutsideCity] = useState(false);
  const [activeCity, setActiveCity] = useState<ActiveCity>(DEFAULT_CITY);
  const [dataEpoch, setDataEpoch] = useState(0);
  const [stageView, setStageView] = useState<StageView>("demarche");
  const [persona, setPersona] = useState<PersonaId>("jury");
  const [simAction, setSimAction] = useState<string | null>(null);
  const [navOpen, setNavOpen] = useState(true);
  const [homePeriod, setHomePeriod] = useState<HomePeriod>("jour");
  const [draftPeriod, setDraftPeriod] = useState<HomePeriod>("jour");
  const [draftMotif, setDraftMotif] = useState<Motif>("tous");
  const [draftMode, setDraftMode] = useState(DEFAULT_OD_FILTERS.mode);
  const [routeBusy, setRouteBusy] = useState(false);
  const [routePickMode, setRoutePickMode] = useState<"off" | "start" | "end">(
    "off"
  );
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [whatIf, setWhatIf] = useState<ScenarioPayload | null>(null);
  const [situation, setSituation] = useState<"current" | "simulated">("simulated");

  const onWhatIf = useCallback((payload: ScenarioPayload | null) => {
    setWhatIf(payload);
    if (payload) setSituation("simulated");
  }, []);
  const [pickMode, setPickMode] = useState<PickMode>("origin");
  const [corridorSide, setCorridorSide] = useState<CorridorSide>("origin");
  const [motif, setMotif] = useState<Motif>("tous");
  const [originIds, setOriginIds] = useState<string[]>([]);
  const [destIds, setDestIds] = useState<string[]>([]);
  const [lens, setLens] = useState<LensPayload | null>(null);
  const [lensLoading, setLensLoading] = useState(true);
  const [lensError, setLensError] = useState<string | null>(null);
  const [mapZoom, setMapZoom] = useState(12);
  const pickModeRef = useRef<PickMode>("origin");
  const corridorSideRef = useRef<CorridorSide>("origin");
  const originIdsRef = useRef<string[]>([]);
  const destIdsRef = useRef<string[]>([]);
  const lensRef = useRef<LensPayload | null>(null);
  const flewKey = useRef("");
  const reloadOverlaysRef = useRef<() => void>(() => {});
  pickModeRef.current = pickMode;
  corridorSideRef.current = corridorSide;
  originIdsRef.current = originIds;
  destIdsRef.current = destIds;
  lensRef.current = lens;

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
      await loadOdFlows(map, filtersRef.current);
      await loadKeyPoints(map);
      await loadEmploiHabitat(map);
      await loadRecommendations(map);
      await loadSatellites(map);
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
      const same =
        cityRef.current.name === city.name &&
        cityRef.current.west === city.west &&
        cityRef.current.osm_ready === city.osm_ready;
      cityRef.current = city;
      setActiveCity(city);
      setOutsideCity(false);
      setLocateStatus(null);
      if (same) return;
      const moved = flyToCity(city);
      if (!moved) {
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
    const container = mapContainer.current;
    if (!container) return;

    let cancelled = false;
    let map: maplibregl.Map | null = null;
    let resizeObserver: ResizeObserver | undefined;
    let moveTimer: ReturnType<typeof setTimeout> | undefined;

    void loadQuietBasemap()
      .then((style) => {
        if (cancelled) return;
        map = new maplibregl.Map({
          container,
          style,
          center: [DEFAULT_CITY.lon, DEFAULT_CITY.lat],
          zoom: 12,
          ...mapRenderOptions(),
        });

        const activeMap = map;
        mapRef.current = activeMap;
        resizeObserver = new ResizeObserver(() => {
          activeMap.resize();
        });
        resizeObserver.observe(container);
        activeMap.addControl(
          new maplibregl.NavigationControl({ showCompass: false }),
          "bottom-right"
        );
        activeMap.addControl(
          new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
          "bottom-left"
        );

        let overlayToken = 0;

        async function loadBboxLayers() {
          if (activeMap.getZoom() < 11) return;
          const shown = visibilityRef.current;
          const wanted = {
            buildings: shown.buildings,
            roads: shown.roads,
            busLines: shown.busLines,
            busStops: shown.busStops,
          };
          if (!wanted.buildings && !wanted.roads && !wanted.busLines && !wanted.busStops) {
            return;
          }
          const token = ++overlayToken;
          const stale = () => token !== overlayToken || cancelled;
          try {
            await Promise.all([
              wanted.buildings ? loadBuildings(activeMap, stale) : Promise.resolve(),
              wanted.roads ? loadRoads(activeMap, stale) : Promise.resolve(),
              wanted.busLines ? loadBusLines(activeMap, stale) : Promise.resolve(),
              wanted.busStops ? loadBusStops(activeMap, stale) : Promise.resolve(),
            ]);
            if (stale() || !activeMap.getStyle()) return;
            applyVisibility(activeMap, visibilityRef.current);
          } catch (error) {
            if (stale()) return;
            console.error("Erreur couches bbox :", error);
          }
        }

        reloadOverlaysRef.current = () => {
          void loadBboxLayers();
        };

        async function loadAnalyticsLayers() {
          try {
            await loadMobilityZones(activeMap);
            await loadOdFlows(activeMap, filtersRef.current);
            await loadKeyPoints(activeMap);
            await loadEmploiHabitat(activeMap);
            await loadRecommendations(activeMap);
            await loadSatellites(activeMap);
            if (cancelled || !activeMap.getStyle()) return;
            fitMapToBBox(activeMap, cityRef.current);
            applyVisibility(activeMap, visibilityRef.current);
            setAnalyticsError(null);
          } catch (error) {
            if (cancelled) return;
            console.error("Erreur couches OD/analytics :", error);
            setAnalyticsError(
              "Impossible de charger les couches analytiques. Vérifie l’API et le seed OD."
            );
          }
        }

        activeMap.on("load", () => {
          activeMap.resize();
          void loadAnalyticsLayers();
          bindZoneInspect(activeMap, () => routePickRef.current !== "off");
        });

        activeMap.on("click", (event) => {
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

        activeMap.on("moveend", () => {
          if (moveTimer) clearTimeout(moveTimer);
          moveTimer = setTimeout(() => {
            void loadBboxLayers();
          }, 450);
        });
      })
      .catch((error) => {
        console.error(error);
        if (!cancelled) setAnalyticsError("Le fond de carte n'a pas pu être chargé.");
      });

    return () => {
      cancelled = true;
      if (moveTimer) clearTimeout(moveTimer);
      resizeObserver?.disconnect();
      userMarkerRef.current = null;
      startMarkerRef.current?.remove();
      endMarkerRef.current?.remove();
      reloadOverlaysRef.current = () => {};
      map?.remove();
      mapRef.current = null;
    };
  }, [applyVisibility, placeRouteMarker, runRoute]);

  useEffect(() => {
    visibilityRef.current = visibility;
    const map = mapRef.current;
    if (!map) return;
    applyVisibility(map, visibility);
    if (visibility.roads || visibility.buildings || visibility.busStops || visibility.busLines) {
      reloadOverlaysRef.current();
    }
  }, [visibility, applyVisibility]);

  useEffect(() => {
    filtersRef.current = filters;
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    let cancelled = false;
    async function refresh() {
      try {
        await loadOdFlows(map!, filters);
        if (!cancelled) applyVisibility(map!, visibilityRef.current);
      } catch (error) {
        console.error("Erreur refresh OD :", error);
      }
    }
    void refresh();
    return () => {
      cancelled = true;
    };
  }, [filters.mode, filters.weekday, filters.minPassengers, applyVisibility]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    applyOdHour(map, filters.hour);
  }, [filters.hour]);

  useEffect(() => {
    setTerritoryPick((id, level, rawIds) => {
      if (routePickRef.current !== "off") return;
      const ids = (level === "commune" ? rawIds.split(",") : [id])
        .map((item) => item.trim())
        .filter(Boolean);
      if (!ids.length) return;
      const mode = pickModeRef.current;
      const side: "origin" | "destination" =
        mode === "destination"
          ? "destination"
          : mode === "corridor"
            ? corridorSideRef.current
            : "origin";
      const current = side === "origin" ? originIdsRef.current : destIdsRef.current;
      const removing = ids.every((item) => current.includes(item));
      const apply = (prev: string[]) => toggleIds(prev, ids);
      if (side === "origin") setOriginIds(apply);
      else setDestIds(apply);
      if (mode === "corridor" && side === "origin" && !removing) {
        setCorridorSide("destination");
      }
      const known = lensRef.current;
      const label =
        ids.length > 3
          ? `${ids.length} quartiers`
          : ids
              .map((item) => known?.quartiers.find((place) => place.id === item)?.name ?? item)
              .join(", ");
      const role = side === "origin" ? "origine" : "destination";
      const kept = side === "origin" ? destIdsRef.current.length : originIdsRef.current.length;
      const hint = removing
        ? ""
        : kept > 0
          ? " L’autre côté de la sélection reste en place."
          : side === "origin"
            ? " Cliquez d’autres quartiers pour ajouter des origines."
            : " Cliquez d’autres quartiers pour ajouter des destinations.";
      setLocateStatus(
        ids.length > 1
          ? `${label} ${removing ? "ne sont plus des" : "sont ajoutés comme"} ${role}s.${hint}`
          : `${label} ${removing ? "n’est plus une" : "est ajouté comme"} ${role}.${hint}`
      );
    });
  }, []);

  useEffect(() => {
    setTerritoryClicksBlocked(routePickMode !== "off");
  }, [routePickMode]);

  const seenCity = useRef(activeCity.name);
  useEffect(() => {
    if (seenCity.current === activeCity.name) return;
    seenCity.current = activeCity.name;
    setOriginIds([]);
    setDestIds([]);
    setLens(null);
    flewKey.current = "";
  }, [activeCity.name]);

  useEffect(() => {
    const controller = new AbortController();
    setLensLoading(true);
    setLensError(null);
      api
      .get("/api/mobility/lens", {
        params: {
          city: activeCity.name,
          purpose: motif === "tous" ? "" : motif,
          origins: originIds.join(","),
          destinations: destIds.join(","),
        },
        signal: controller.signal,
      })
      .then((response) => {
        setLens(response.data as LensPayload);
        setLensError(null);
      })
      .catch((err: unknown) => {
        if (axios.isCancel(err) || (err as { code?: string }).code === "ERR_CANCELED") {
          return;
        }
        console.error(err);
        setLensError(lensErrorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLensLoading(false);
      });
    return () => controller.abort();
  }, [activeCity.name, motif, originIds, destIds]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const run = () => {
      if (!map.isStyleLoaded()) return;
      if (lens) paintTerritory(map, lens, originIds, destIds);
      else clearTerritory(map);
      applyVisibility(map, visibilityRef.current);
    };
    if (map.isStyleLoaded()) run();
    else map.once("load", run);
    const onZoom = () => {
      setMapZoom(map.getZoom());
      run();
    };
    setMapZoom(map.getZoom());
    map.on("zoomend", onZoom);
    return () => {
      map.off("load", run);
      map.off("zoomend", onZoom);
    };
  }, [lens, originIds, destIds, applyVisibility]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !lens) return;
    const key = `${lens.city.id}|${originIds.join(",")}|${destIds.join(",")}`;
    if (!map.isStyleLoaded()) return;
    const ids = [...originIds, ...destIds];
    if (flewKey.current === key) return;
    flewKey.current = key;
    if (ids.length !== 1) return;
    const point = lens.quartiers.find((quartier) => quartier.id === ids[0]);
    if (!point) return;
    map.flyTo({
      center: [point.lon, point.lat],
      zoom: Math.max(map.getZoom(), 13),
      essential: true,
    });
  }, [lens, originIds, destIds]);

  const onToggle = (key: LayerKey) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      if (stageView !== "simulation" || !whatIf) {
        setScenarioVisible(map, false);
        applyVisibility(map, visibilityRef.current);
        return;
      }
      showWhatIf(map, whatIf);
      const showCurrent = situation === "current";
      setScenarioVisible(map, !showCurrent);
      if (showCurrent) applyVisibility(map, visibilityRef.current);
      else setOdVisible(map, false);
    };

    if (map.isStyleLoaded()) draw();
    else map.once("load", draw);
    return () => {
      map.off("load", draw);
    };
  }, [stageView, whatIf, situation, visibility, applyVisibility]);

  const onStageNav = (view: StageView) => {
    setStageView(view);
    setVisibility((prev) => applyViewPreset(prev, view));
    if (view !== "dashboard" && view !== "deplacements" && view !== "rapports") {
      requestAnimationFrame(() => mapRef.current?.resize());
    }
  };

  const allowedViews =
    PERSONAS.find((item) => item.id === persona)?.views ?? STAGE_NAV.map((item) => item.id);
  const visibleNav = STAGE_NAV.filter((item) => allowedViews.includes(item.id));

  const openExample = (view: StageView, action?: string) => {
    setSimAction(action ?? null);
    onStageNav(view);
  };

  const toggleNav = () => setNavOpen((open) => !open);

  useEffect(() => {
    const id = window.setTimeout(() => mapRef.current?.resize(), 220);
    return () => window.clearTimeout(id);
  }, [navOpen, stageView]);

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

  const clearPlaces = () => {
    setOriginIds([]);
    setDestIds([]);
  };

  const showHome = stageView === "accueil";
  const showMapFocus = stageView === "carte";
  const cityLabel = activeCity.display_name || activeCity.name;
  const viewCopy = VIEW_COPY[stageView];
  const showDashboard = stageView === "dashboard";
  const showDiary = stageView === "deplacements";
  const showReports = stageView === "rapports";
  const fullPage = showDashboard || showDiary || showReports;
  const people =
    lens == null ? null : lens.indices.regular_workers + lens.indices.regular_other;

  const applyHomeFilters = () => {
    setHomePeriod(draftPeriod);
    setMotif(draftMotif);
    setFilters((prev) => ({ ...prev, mode: draftMode }));
  };

  const timeControls = visibility.odFlows ? (
    <div className="side-filters">
      <FlowFilters filters={filters} onChange={setFilters} compact />
      <HourAnimator
        hour={filters.hour}
        playing={playing}
        onHour={(hour) => setFilters((prev) => ({ ...prev, hour }))}
        onPlaying={setPlaying}
      />
    </div>
  ) : null;

  const zonePanel = (
    <HomeZonePanel
      lens={lens}
      loading={lensLoading}
      error={lensError}
      originIds={originIds}
      onSelectZone={(id) => {
        setPickMode("origin");
        setOriginIds([id]);
        setDestIds([]);
      }}
      onClear={clearPlaces}
      matrix={showMapFocus ? <OdMatrixPanel filters={filters} /> : undefined}
    />
  );

  const togglePlace = (id: string, mode: "origin" | "destination") => {
    if (mode === "origin") setOriginIds((prev) => toggleIds(prev, [id]));
    else setDestIds((prev) => toggleIds(prev, [id]));
  };

  const choosePickMode = (mode: PickMode) => {
    setPickMode(mode);
    if (mode === "corridor") setCorridorSide("origin");
  };

  const readingPanel = (
    <LensPanel
      lens={lens}
      loading={lensLoading}
      error={lensError}
      pickMode={pickMode}
      corridorSide={corridorSide}
      motif={motif}
      originIds={originIds}
      destIds={destIds}
      onPickMode={choosePickMode}
      onCorridorSide={setCorridorSide}
      onMotif={setMotif}
      onToggle={togglePlace}
      onClear={clearPlaces}
    />
  );

  let side = showMapFocus ? readingPanel : zonePanel;
  if (stageView === "zones") side = <KeyPointsPanel />;
  else if (stageView === "reco") side = <RecoPanel />;
  else if (stageView === "simulation")
    side = <SimulationPanel onScenario={onWhatIf} initialAction={simAction} />;
  else if (stageView === "emploi")
    side = (
      <EmploiHabitatPanel
        onReloadSatellites={() => {
          const map = mapRef.current;
          if (map) void loadSatellites(map);
        }}
        onAnnexesGeoJSON={(fc) => {
          const map = mapRef.current;
          if (map && fc) {
            void loadSatellites(map, null, fc);
            setVisibility((prev) => ({ ...prev, satellites: true }));
          }
        }}
      />
    );
  else if (stageView === "demarche")
    side = (
      <SpecProcessPanel
        onResult={(payload) => {
          const map = mapRef.current;
          if (!map || !payload?.geojson) return;
          const draw = () => {
            void loadSatellites(map, null, payload.geojson);
            setVisibility((prev) => ({ ...prev, satellites: true }));
            if (payload.focus) {
              map.flyTo({
                center: [payload.focus.lon, payload.focus.lat],
                zoom: Math.max(map.getZoom(), 12),
                essential: true,
              });
            }
          };
          if (map.isStyleLoaded()) draw();
          else map.once("load", draw);
        }}
      />
    );

  return (
    <div className={navOpen ? "app-shell" : "app-shell nav-collapsed"}>
      <aside className="app-nav">
        <div className="app-nav-head">
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={navOpen}
            aria-label={navOpen ? "Replier le menu" : "Afficher le menu"}
            title={navOpen ? "Replier le menu" : "Afficher le menu"}
            onClick={toggleNav}
          >
            <span aria-hidden="true">{navOpen ? "‹" : "›"}</span>
          </button>
          <span className="brand-mark" aria-hidden="true">
            <NavIcon name="map" />
          </span>
          <div className="app-brand">
            <strong>MobilitySmart</strong>
            <span>Mobilité urbaine intelligente</span>
          </div>
        </div>
        {visibleNav.map((item) => (
          <button
            key={item.id}
            type="button"
            className={stageView === item.id ? "nav-item active" : "nav-item"}
            aria-current={stageView === item.id ? "page" : undefined}
            onClick={() => onStageNav(item.id)}
          >
            <NavIcon name={item.icon} />
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
        <label className="nav-persona">
          <span className="nav-label">Profil</span>
          <select
            value={persona}
            aria-label="Profil de démonstration"
            onChange={(event) => {
              const next = event.target.value as PersonaId;
              const views = PERSONAS.find((item) => item.id === next)?.views ?? allowedViews;
              setPersona(next);
              if (!views.includes(stageView)) onStageNav(views[0]);
            }}
          >
            {PERSONAS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <div className="app-nav-foot">
          Une mobilité plus fluide pour une ville plus durable
          <strong>MobilitySmart v1.0.0</strong>
        </div>
      </aside>

      <div className="app-main">
        <div className="demo-banner" role="status">
          <span className="demo-dot" aria-hidden="true" />
          <strong>DONNÉES DE DÉMONSTRATION — SIMULÉES</strong>
          <span>Ce sont des données générées pour la démonstration. Elles ne représentent pas la réalité.</span>
        </div>
        <header className="app-toolbar">
          {showHome ? <span className="toolbar-badge">{activeCity.name}</span> : <CitySelector onActivated={onCityActivated} />}
          <span className="toolbar-badge">Démonstration</span>
        </header>
        {!activeCity.osm_ready && (
          <p className="app-banner warn" role="status">
            OSM manquant pour cette ville : importer un extract Geofabrik (osm2pgsql) puis réactiver la ville.
          </p>
        )}
        {analyticsError && (
          <p className="app-banner error" role="alert">
            {analyticsError}
          </p>
        )}
        {showHome && (
          <section className="home-block">
            <div className="home-title">
              <h1>{viewCopy.title}</h1>
              <p>{viewCopy.subtitle}</p>
            </div>
            <div className="home-filters">
              <label>
                Période
                <select
                  value={draftPeriod}
                  onChange={(event) => setDraftPeriod(event.target.value as HomePeriod)}
                >
                  <option value="jour">Journée type</option>
                  <option value="semaine">Semaine type (5 jours)</option>
                  <option value="trimestre">Trimestre illustratif</option>
                </select>
              </label>
              <label>
                Motif
                <select
                  value={draftMotif}
                  onChange={(event) => setDraftMotif(event.target.value as Motif)}
                >
                  <option value="tous">Tous les motifs</option>
                  <option value="travail">Domicile-travail</option>
                </select>
              </label>
              <label>
                Mode de transport
                <select value={draftMode} onChange={(event) => setDraftMode(event.target.value)}>
                  <option value="all">Tous les modes</option>
                  <option value="car">Voiture</option>
                  <option value="bus">Bus / TC</option>
                  <option value="bike">Vélo</option>
                  <option value="walk">Marche</option>
                </select>
              </label>
              <label>
                Ville
                <CitySelector onActivated={onCityActivated} />
              </label>
              <button type="button" className="home-apply" onClick={applyHomeFilters}>
                Appliquer les filtres
              </button>
            </div>
            <HomeKpis period={homePeriod} people={people} refreshKey={dataEpoch} />
          </section>
        )}
        {!showHome && !fullPage && (
          <header className="view-intro">
            <h1>{viewCopy.title}</h1>
            {showMapFocus ? (
              <p>
                {(lens?.city.name ?? activeCity.name)}
                {" · "}
                {lens ? arrondissementLabel(lens, originIds, destIds) : "Tous les arrondissements"}
                {" · "}
                Mode : {readingMode(pickMode, originIds.length, destIds.length)}
                {" · Motif : "}
                {motifLabel(motif)}
                {" · Données : SIMULÉES"}
              </p>
            ) : (
              <p>
                {viewCopy.subtitle}
                {cityLabel ? ` · ${cityLabel}` : ""}
              </p>
            )}
          </header>
        )}

        <div className="app-fill">
        {showDashboard && <DashboardView />}
        {showDiary && <DiaryView />}
        {showReports && <ReportsView />}
        <div className={fullPage ? "app-map-host is-hidden" : "app-map-host"}>
        <div className="app-workspace">
          <div className={showHome ? "map-stage is-home" : showMapFocus ? "map-stage is-od" : "map-stage"}>
            <div ref={mapContainer} className="map-canvas" />
            {showHome && (
              <h2 className="map-card-title">Flux origine-destination</h2>
            )}
            {showMapFocus && (
              <div className="map-readout">
                <OdContextBar
                  city={activeCity.name}
                  lens={lens}
                  pickMode={pickMode}
                  motif={motif}
                  originIds={originIds}
                  destIds={destIds}
                  zoom={mapZoom}
                  onPickMode={choosePickMode}
                  onToggle={togglePlace}
                  onClear={clearPlaces}
                />
                <MapLegend visibility={visibility} />
              </div>
            )}

            {!showHome && (
            <div className="map-chrome-top">
              <SearchBar onSelectLocation={flyToLocation} />
              <LayerPanel visibility={visibility} onToggle={onToggle} />
            </div>
            )}

            <div className="map-chrome-bottom">
              {stageView === "simulation" ? (
                <div className="map-legend-card">
                  <span className="legend-title">
                    {situation === "current" ? "Situation actuelle" : "Situation simulée"}
                  </span>
                  <div className="legend-swatch-row">
                    <span className="legend-dot" style={{ background: "#16a34a" }} />
                    Zone améliorée
                  </div>
                  <div className="legend-swatch-row">
                    <span className="legend-dot" style={{ background: "#dc2626" }} />
                    Zone potentiellement aggravée
                  </div>
                  <div className="legend-swatch-row">
                    <span className="legend-dot" style={{ background: "#4ade80" }} />
                    Flux allégé
                  </div>
                  <div className="legend-swatch-row">
                    <span className="legend-dot" style={{ background: "#f87171" }} />
                    Flux renforcé
                  </div>
                  <p className="legend-note">SIMULATION — pas une prédiction</p>
                  <div className="sim-picks">
                    <button
                      type="button"
                      className={situation === "current" ? "map-btn sim-pick active" : "map-btn sim-pick"}
                      onClick={() => setSituation("current")}
                    >
                      Actuelle
                    </button>
                    <button
                      type="button"
                      className={situation === "simulated" ? "map-btn sim-pick active" : "map-btn sim-pick"}
                      onClick={() => setSituation("simulated")}
                    >
                      Simulée
                    </button>
                  </div>
                </div>
              ) : showHome ? (
                <div className="map-legend-card home-legend">
                  <span className="legend-title">Légende</span>
                  <div className="legend-grid">
                    <div className="legend-swatch-row">
                      <span className="legend-dot" style={{ background: "#7c3aed" }} />
                      Quartier
                    </div>
                    <div className="legend-swatch-row">
                      <span className="legend-line" style={{ background: "#2563eb" }} />
                      Flux OD
                    </div>
                  </div>
                  <p className="legend-note">
                    Les lignes relient les zones. L'épaisseur suit le volume. Ce ne sont pas des itinéraires.
                  </p>
                </div>
              ) : showMapFocus ? null : (
                <MapLegend visibility={visibility} />
              )}
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
              {!showHome && (
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
              )}
            </div>
          </div>

          <div className="side-panel">
            {timeControls}
            {side}
          </div>
        </div>
        </div>
        </div>

        {showHome && (
          <section className="home-cases" aria-label="Démarches d'exemple">
            <h2>Trois démarches d&apos;exemple</h2>
            <button type="button" className="home-shortcut" onClick={() => openExample("deplacements")}>
              <span className="shortcut-copy">
                <strong>Entreprise centralisée</strong>
                <span>
                  Choisir l&apos;organisation, lire les trajets longs, tester une annexe, comparer, puis décider.
                </span>
              </span>
            </button>
            <button type="button" className="home-shortcut" onClick={() => openExample("simulation", "zoning_housing")}>
              <span className="shortcut-copy">
                <strong>Collectivité</strong>
                <span>
                  Comparer plus de logements et plus d&apos;emplois, puis garder les deux hypothèses côte à côte.
                </span>
              </span>
            </button>
            <button type="button" className="home-shortcut" onClick={() => openExample("emploi")}>
              <span className="shortcut-copy">
                <strong>Plusieurs employeurs</strong>
                <span>
                  Classer 3 à 5 sites (annexe, tiers-lieu, mixité) avec le score temps, km, CO₂, desserte et faisabilité.
                </span>
              </span>
            </button>
          </section>
        )}
        {showHome && (
          <div className="home-shortcuts">
            <button type="button" className="home-shortcut" onClick={() => onStageNav("carte")}>
              <span className="shortcut-ico teal" />
              <span className="shortcut-copy">
                <strong>Carte et flux OD</strong>
                <span>Visualisez les zones et les flux de déplacements entre quartiers.</span>
              </span>
              <span className="shortcut-arrow" aria-hidden="true">→</span>
            </button>
            <button type="button" className="home-shortcut" onClick={() => onStageNav("dashboard")}>
              <span className="shortcut-ico blue" />
              <span className="shortcut-copy">
                <strong>Tableau de bord</strong>
                <span>Analysez les indicateurs et les tendances de la mobilité.</span>
              </span>
              <span className="shortcut-arrow" aria-hidden="true">→</span>
            </button>
            <button type="button" className="home-shortcut" onClick={() => onStageNav("simulation")}>
              <span className="shortcut-ico amber" />
              <span className="shortcut-copy">
                <strong>Simulation</strong>
                <span>Testez des scénarios pour améliorer la mobilité et réduire les émissions.</span>
              </span>
              <span className="shortcut-arrow" aria-hidden="true">→</span>
            </button>
            <button type="button" className="home-shortcut" onClick={() => onStageNav("reco")}>
              <span className="shortcut-ico violet" />
              <span className="shortcut-copy">
                <strong>Recommandations IA</strong>
                <span>Obtenez des conseils à partir des déséquilibres observés.</span>
              </span>
              <span className="shortcut-arrow" aria-hidden="true">→</span>
            </button>
          </div>
        )}
        <footer className="app-footer">
          <span>© OpenStreetMap · effectifs simulés</span>
          <span>{cityLabel}</span>
        </footer>
      </div>
    </div>
  );
}
