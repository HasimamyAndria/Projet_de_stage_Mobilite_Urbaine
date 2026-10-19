import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import maplibregl from "maplibre-gl";
import { loadQuietBasemap, mapRenderOptions } from "./Map/basemap";
import api from "../services/api";
import EmployerBoard, { type JourneyOrg, type JourneyPhase } from "./EmployerBoard";
import "./DiaryView.css";

type Period = "day" | "week" | "month" | "year";

const JOURNEY: Array<{ id: JourneyPhase; label: string; next: string }> = [
  { id: "org", label: "Choisir une organisation", next: "Examiner les trajets" },
  { id: "trips", label: "Examiner les trajets", next: "Identifier les besoins" },
  { id: "needs", label: "Identifier les besoins", next: "Tester un bureau satellite" },
  { id: "satellite", label: "Tester un bureau satellite", next: "Comparer les résultats" },
  { id: "compare", label: "Comparer les résultats", next: "Préparer la décision" },
  { id: "decision", label: "Préparer une décision", next: "" },
];

type City = {
  id: string;
  name: string;
  aka: string;
  population: number;
  bbox: [number, number, number, number];
};

type Place = {
  id: string;
  name: string;
  level: "city" | "commune" | "quartier";
  role_label: string;
  parent_name: string | null;
  city_id: string;
  lon: number;
  lat: number;
};

type Person = {
  id: string;
  name: string;
  age: number | null;
  job: string;
  city_id: string;
  home: string;
  work: string;
  blurb: string;
};

type Employee = {
  id: string;
  name: string;
  job: string;
  home: string;
  work: string;
  cluster_id: string;
  named: boolean;
};

type Option = { id: string; label: string; color?: string };

type Catalog = {
  population_rule: string;
  note: string;
  periods: Option[];
  weekdays: Array<{ id: number; label: string }>;
  purposes: Option[];
  modes: Option[];
  cities: City[];
  places: Place[];
  persons: Person[];
  zoom: { city_below: number; quartier_from: number };
};

type Trip = {
  id: string;
  weekday_label: string;
  origin_name: string;
  destination_name: string;
  purpose_label: string;
  purpose_color: string;
  detail: string;
  mode_label: string;
  depart_label: string;
  minutes: number;
  km: number;
  source: string;
  origin: [number, number];
  destination: [number, number];
  people?: number;
};

type Bar = { id: string; label: string; color: string; count: number; share: number };

type Suggestion = {
  id: string;
  purpose: string;
  purpose_label: string;
  home_name: string;
  current_name: string;
  current_km: number;
  suggested_name: string;
  suggested_km: number;
  people: number;
  saved_km: number;
  reading: string;
};

type Diary = {
  note: string;
  listing_note: string;
  scope?: "all" | "person";
  organization_id?: string;
  organization_name?: string;
  employee_count?: number;
  employees?: Employee[];
  person: Person;
  stats: {
    trip_count: number;
    km: number;
    duration: { value: number; unit: string };
    non_work_share: number;
  };
  volume: { question: string; points: Array<{ label: string; value: number }> };
  purposes: { question: string; items: Bar[] };
  modes: { question: string; items: Bar[] };
  trips: Trip[];
  geojson: Collection;
  suggestions?: Suggestion[];
};

type Collection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: string; coordinates: number[] | number[][] };
    properties: Record<string, string | number | null>;
  }>;
};

const EMPTY: Collection = { type: "FeatureCollection", features: [] };

function fmt(value: number) {
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function hourFromTime(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return hour + minute / 60;
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function errorText(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

const WEEK_FULL = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
const MONTH_FULL = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

function barCaption(period: Period, index: number, label: string) {
  if (period === "week") return WEEK_FULL[index] ?? label;
  if (period === "month") {
    const day = WEEK_FULL[index % 7];
    return day ? `Jour ${label} · ${day}` : `Jour ${label}`;
  }
  if (period === "year") return MONTH_FULL[index] ?? label;
  return label;
}

function barBadge(period: Period, index: number, label: string) {
  if (period === "month") {
    const day = WEEK_FULL[index % 7];
    return day ? `${label} · ${day.slice(0, 3)}` : label;
  }
  return barCaption(period, index, label);
}

function VolumeChart({ volume, period }: { volume: Diary["volume"]; period: Period }) {
  const [picked, setPicked] = useState<number | null>(null);
  const signature = volume.points.map((point) => `${point.label}:${point.value}`).join("|");
  useEffect(() => {
    setPicked(null);
  }, [signature]);

  const max = Math.max(...volume.points.map((point) => point.value), 1);
  const dense = volume.points.length > 14;
  const chosen = picked != null ? volume.points[picked] : null;
  const chosenName = chosen && picked != null ? barCaption(period, picked, chosen.label) : null;

  return (
    <article className={picked == null ? "diary-chart diary-chart-volume" : "diary-chart diary-chart-volume has-pick"}>
      <h2>{volume.question}</h2>
      <p className="diary-muted">Un bâton = un moment. Cliquez un jour pour le marquer.</p>
      <p className="diary-picked" role="status">
        {chosen && chosenName ? (
          <>
            <i aria-hidden="true" />
            <strong>{chosenName}</strong>
            <span>{fmt(chosen.value)} trajets</span>
          </>
        ) : (
          <span>Aucun jour marqué.</span>
        )}
      </p>
      <div className="diary-vbars" role="list">
        {volume.points.map((point, index) => {
          const selected = picked === index;
          const name = barCaption(period, index, point.label);
          const showLabel = selected || !dense || index % 5 === 0;
          return (
            <button
              key={`${point.label}-${index}`}
              type="button"
              role="listitem"
              className={selected ? "diary-vcol is-selected" : "diary-vcol"}
              aria-pressed={selected}
              title={`${name} : ${fmt(point.value)} trajets`}
              onClick={() => setPicked(selected ? null : index)}
            >
              {selected && <span className="diary-vbadge">{barBadge(period, index, point.label)}</span>}
              {(selected || !dense) && <span className="diary-vval">{fmt(point.value)}</span>}
              <span className="diary-vtrack">
                <span style={{ height: `${Math.max(point.value > 0 ? 6 : 0, (point.value / max) * 100)}%` }} />
              </span>
              <span className="diary-vlab">{showLabel ? point.label : ""}</span>
            </button>
          );
        })}
      </div>
    </article>
  );
}

function ShareChart({
  title,
  hint,
  items,
  accent,
}: {
  title: string;
  hint: string;
  items: Bar[];
  accent: string;
}) {
  return (
    <article className={`diary-chart ${accent}`}>
      <h2>{title}</h2>
      <p className="diary-muted">{hint}</p>
      {items.length === 0 ? (
        <p className="diary-muted">Aucun trajet sur cette période.</p>
      ) : (
        <ul className="diary-hbars">
          {items.map((item) => (
            <li key={item.id}>
              <span>{item.label}</span>
              <span className="diary-htrack">
                <span style={{ width: `${item.share}%`, background: item.color }} />
              </span>
              <span className="diary-hval">
                {fmt(item.count)} · {fmt(item.share)} %
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function rosterGroups(employees: Employee[]) {
  const groups: Array<{ key: string; title: string; people: Employee[] }> = [];
  for (const employee of employees) {
    const key = employee.cluster_id;
    const last = groups[groups.length - 1];
    if (!last || last.key !== key) {
      groups.push({ key, title: `${employee.home} — ${employee.job}`, people: [employee] });
    } else {
      last.people.push(employee);
    }
  }
  return groups;
}

export default function DiaryView() {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const fitted = useRef("");
  const [mapHost, setMapHost] = useState<HTMLDivElement | null>(null);

  const [meta, setMeta] = useState<Catalog | null>(null);
  const [diary, setDiary] = useState<Diary | null>(null);
  const [cityId, setCityId] = useState("tana");
  const [orgId, setOrgId] = useState("");
  const [personId, setPersonId] = useState("");
  const [period, setPeriod] = useState<Period>("week");
  const [weekday, setWeekday] = useState(0);
  const [zoom, setZoom] = useState(11);
  const [mapReady, setMapReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [formNote, setFormNote] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [revision, setRevision] = useState(0);

  const [originId, setOriginId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [purpose, setPurpose] = useState("supermarche");
  const [detail, setDetail] = useState("");
  const [mode, setMode] = useState("bus");
  const [depart, setDepart] = useState("17:30");
  const [formDay, setFormDay] = useState(4);
  const [phase, setPhase] = useState<JourneyPhase>("org");
  const [reached, setReached] = useState(0);
  const [journey, setJourney] = useState<JourneyOrg | null>(null);
  const [needIds, setNeedIds] = useState<string[]>([]);
  const [satelliteId, setSatelliteId] = useState("");

  const onOrgReady = useCallback((info: JourneyOrg) => {
    setJourney((prev) => (prev?.id === info.id && prev.cityId === info.cityId ? prev : info));
  }, []);

  useEffect(() => {
    if (!journey) return;
    setNeedIds(journey.defaultNeedIds);
    setSatelliteId(journey.defaultSatelliteId);
    setPhase("org");
    setReached(0);
  }, [journey]);

  useEffect(() => {
    api
      .get<Catalog>("/api/mobility/meta")
      .then((res) => setMeta(res.data))
      .catch(() => setLoadError("Catalogue indisponible. Démarrez l'API (port 8000)."));
  }, []);

  useEffect(() => {
    if (!meta) return;
    const quartiers = meta.places.filter(
      (place) => place.city_id === cityId && place.level === "quartier"
    );
    setOriginId(quartiers[0]?.id ?? "");
    setDestinationId(quartiers[1]?.id ?? quartiers[0]?.id ?? "");
  }, [meta, cityId]);

  useEffect(() => {
    setPersonId("");
  }, [orgId]);

  useEffect(() => {
    if (!orgId) {
      setDiary(null);
      return;
    }
    let cancelled = false;
    api
      .get<Diary>(`/api/mobility/employers/${orgId}/movements`, {
        params: { period, weekday, person_id: personId || undefined },
      })
      .then((res) => {
        if (cancelled) return;
        setDiary(res.data);
        setLoadError(null);
      })
      .catch((error) => {
        if (cancelled) return;
        setDiary(null);
        setLoadError(errorText(error, "Lecture des déplacements impossible."));
      });
    return () => {
      cancelled = true;
    };
  }, [orgId, personId, period, weekday, revision]);

  useEffect(() => {
    if (!mapHost) return;
    let cancelled = false;
    let map: maplibregl.Map | null = null;
    let observer: ResizeObserver | undefined;

    void loadQuietBasemap()
      .then((style) => {
        if (cancelled) return;
        map = new maplibregl.Map({
          container: mapHost,
          style,
          center: [47.52, -18.91],
          zoom: 11,
          ...mapRenderOptions(),
        });
        mapRef.current = map;
        const activeMap = map;
        activeMap.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

        activeMap.on("load", () => {
          if (cancelled) return;
          activeMap.addSource("diary-places", { type: "geojson", data: EMPTY });
          activeMap.addSource("diary-trips", { type: "geojson", data: EMPTY });
          activeMap.addLayer({
            id: "diary-places",
            type: "circle",
            source: "diary-places",
            filter: [
              "any",
              ["all", ["<", ["zoom"], 11], ["==", ["get", "level"], "city"]],
              ["all", [">=", ["zoom"], 11], ["==", ["get", "level"], "commune"]],
              ["all", [">=", ["zoom"], 13.5], ["==", ["get", "level"], "quartier"]],
            ],
            paint: {
              "circle-radius": ["match", ["get", "level"], "city", 9, "commune", 7, 5],
              "circle-color": ["match", ["get", "level"], "city", "#0f766e", "commune", "#0369a1", "#c2410c"],
              "circle-stroke-width": 1.5,
              "circle-stroke-color": "#ffffff",
            },
          });
          activeMap.addLayer({
            id: "diary-labels",
            type: "symbol",
            source: "diary-places",
            filter: [
              "any",
              ["all", ["<", ["zoom"], 11], ["==", ["get", "level"], "city"]],
              ["all", [">=", ["zoom"], 11], ["<", ["zoom"], 13.5], ["==", ["get", "level"], "commune"]],
              ["all", [">=", ["zoom"], 13.5], ["==", ["get", "level"], "quartier"]],
            ],
            layout: {
              "text-field": ["get", "name"],
              "text-font": ["Noto Sans Regular"],
              "text-size": 12,
              "text-offset": [0, 1.15],
              "text-anchor": "top",
            },
            paint: {
              "text-color": "#0f172a",
              "text-halo-color": "#ffffff",
              "text-halo-width": 1.2,
            },
          });
          activeMap.addLayer({
            id: "diary-trips",
            type: "line",
            source: "diary-trips",
            paint: {
              "line-color": ["get", "color"],
              "line-width": [
                "interpolate",
                ["linear"],
                ["coalesce", ["get", "weight"], 1],
                1,
                3,
                32,
                10,
              ],
              "line-opacity": 0.9,
            },
          });
          activeMap.on("zoom", () => setZoom(activeMap.getZoom()));
          activeMap.on("click", "diary-trips", (event) => {
            const feature = event.features?.[0];
            const props = feature?.properties;
            if (!props) return;
            new maplibregl.Popup({ offset: 8 })
              .setLngLat(event.lngLat)
              .setHTML(
                `<strong>${escapeHtml(String(props.label ?? ""))}</strong><br/>${escapeHtml(String(props.people ?? ""))}<br/>${escapeHtml(String(props.when ?? ""))}<br/>${escapeHtml(String(props.purpose ?? ""))} · ${escapeHtml(String(props.mode ?? ""))}<br/>${escapeHtml(String(props.detail ?? ""))}`
              )
              .addTo(activeMap);
          });
          activeMap.on("mouseenter", "diary-trips", () => {
            activeMap.getCanvas().style.cursor = "pointer";
          });
          activeMap.on("mouseleave", "diary-trips", () => {
            activeMap.getCanvas().style.cursor = "";
          });
          observer = new ResizeObserver(() => activeMap.resize());
          observer.observe(mapHost);
          activeMap.resize();
          setZoom(activeMap.getZoom());
          setMapReady(true);
        });
      })
      .catch((error) => {
        console.error(error);
      });

    return () => {
      cancelled = true;
      observer?.disconnect();
      map?.remove();
      mapRef.current = null;
      fitted.current = "";
      setMapReady(false);
    };
  }, [mapHost]);

  const placeData = useMemo<Collection>(() => {
    if (!meta) return EMPTY;
    return {
      type: "FeatureCollection",
      features: meta.places
        .filter((place) => place.city_id === cityId)
        .map((place) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [place.lon, place.lat] },
          properties: { name: place.name, level: place.level },
        })),
    };
  }, [meta, cityId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    (map.getSource("diary-places") as maplibregl.GeoJSONSource | undefined)?.setData(
      placeData as never
    );
    (map.getSource("diary-trips") as maplibregl.GeoJSONSource | undefined)?.setData(
      (diary?.geojson ?? EMPTY) as never
    );
  }, [mapReady, placeData, diary]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !meta) return;
    const key = `${cityId}:${orgId}:${personId}`;
    if (fitted.current === key) return;
    const city = meta.cities.find((item) => item.id === cityId);
    const fitCity = () => {
      if (!city) return;
      const [west, south, east, north] = city.bbox;
      map.fitBounds(
        [
          [west, south],
          [east, north],
        ],
        { padding: 36, duration: 700 }
      );
    };
    if (!diary || (personId && diary.person.id !== personId) || (!personId && diary.scope !== "all")) {
      return;
    }
    if (diary.trips.length === 0) fitCity();
    else {
      const bounds = new maplibregl.LngLatBounds();
      for (const trip of diary.trips) {
        bounds.extend(trip.origin);
        bounds.extend(trip.destination);
      }
      map.fitBounds(bounds, { padding: 48, maxZoom: 13, duration: 700 });
    }
    fitted.current = key;
  }, [mapReady, meta, diary, cityId, orgId, personId]);

  const city = meta?.cities.find((item) => item.id === cityId);
  const sameOrg = diary?.organization_id === orgId;
  const employees = sameOrg ? (diary?.employees ?? []) : [];
  const selected = employees.find((item) => item.id === personId);
  const view =
    sameOrg && diary && ((personId === "" && diary.scope === "all") || diary.person.id === personId)
      ? diary
      : null;
  const person = view?.person ?? null;
  const quartiers = meta?.places.filter((place) => place.city_id === cityId && place.level === "quartier") ?? [];
  const groups = new Map<string, Place[]>();
  for (const place of quartiers) {
    const key = place.parent_name ?? "Quartiers";
    groups.set(key, [...(groups.get(key) ?? []), place]);
  }
  const levelLabel =
    !meta ? "" : zoom < meta.zoom.city_below ? "Ville" : zoom < meta.zoom.quartier_from ? "Sous-villes" : "Quartiers";

  async function submitTrip(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setFormNote(null);
    if (!personId) {
      setFormError("Choisissez une personne.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/api/mobility/trips", {
        person_id: personId,
        weekday: formDay,
        origin_id: originId,
        destination_id: destinationId,
        purpose,
        detail,
        mode,
        depart_hour: hourFromTime(depart),
      });
      setDetail("");
      setFormNote("Trajet ajouté à la semaine type. Il entre dans les totaux du mois et de l'année.");
      setWeekday(formDay);
      setPeriod("day");
      setRevision((value) => value + 1);
    } catch (error) {
      setFormError(errorText(error, "Enregistrement impossible."));
    } finally {
      setSaving(false);
    }
  }

  async function removeTrip(tripId: string) {
    setFormError(null);
    try {
      await api.delete(`/api/mobility/trips/${tripId}`);
      setRevision((value) => value + 1);
    } catch (error) {
      setFormError(errorText(error, "Suppression impossible."));
    }
  }

  if (loadError && !meta) {
    return (
      <div className="diary-page">
        <p className="diary-error">{loadError}</p>
      </div>
    );
  }
  if (!meta || !city) {
    return (
      <div className="diary-page">
        <p className="diary-muted">Chargement des déplacements…</p>
      </div>
    );
  }

  const needsDetail = purpose !== "travail";
  const stepIndex = JOURNEY.findIndex((step) => step.id === phase);
  const continueBlocked =
    (phase === "org" && !orgId) ||
    (phase === "trips" && Boolean(orgId) && !diary && !loadError) ||
    (phase === "needs" && Boolean(journey && journey.farIds.length > 0 && needIds.length === 0)) ||
    (phase === "satellite" && Boolean(journey && journey.satelliteIds.length > 0 && !satelliteId));

  function goTo(index: number) {
    if (index < 0 || index >= JOURNEY.length) return;
    if (index > reached + 1) return;
    if (index > stepIndex && continueBlocked) return;
    setPhase(JOURNEY[index].id);
    setReached((value) => Math.max(value, index));
  }

  return (
    <div className="diary-page">
      <header className="diary-head">
        <div>
          <h1>Décider pour une organisation</h1>
          <p>
            {city.name} ({city.aka}). Choisir l&apos;organisation, examiner les trajets, identifier
            les besoins, tester un bureau satellite, comparer, puis préparer la décision.
          </p>
        </div>
        <label className="field">
          Ville
          <select value={cityId} onChange={(event) => setCityId(event.target.value)}>
            {meta.cities.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </header>
      <ol className="journey" aria-label="Démarche">
        {JOURNEY.map((step, index) => (
          <li key={step.id}>
            <button
              type="button"
              className={
                phase === step.id ? "is-current" : index < stepIndex || index <= reached ? "is-done" : undefined
              }
              aria-current={phase === step.id ? "step" : undefined}
              disabled={index > reached}
              onClick={() => goTo(index)}
            >
              <span>{index + 1}</span>
              {step.label}
            </button>
          </li>
        ))}
      </ol>
      <p className="diary-banner">{meta.note}</p>
      {loadError && <p className="diary-error">{loadError}</p>}

      <EmployerBoard
        cityId={cityId}
        phase={phase}
        needIds={needIds}
        satelliteId={satelliteId}
        onSelectOrg={setOrgId}
        onOpenPerson={(id) => {
          setPersonId(id);
          setPeriod("week");
          setPhase("trips");
          setReached((value) => Math.max(value, 1));
        }}
        onToggleNeed={(id) =>
          setNeedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
        }
        onSatellite={setSatelliteId}
        onOrgReady={onOrgReady}
      />

      {phase === "trips" && (
      <>
      <h2 className="employer-options-title">Volumes et carte</h2>

      <div className="diary-filters">
        <div className="diary-periods" role="tablist" aria-label="Période">
          {meta.periods.map((item) => (
            <button
              key={item.id}
              type="button"
              className={period === item.id ? "active" : undefined}
              onClick={() => setPeriod(item.id as Period)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {period === "day" && (
          <label className="field">
            Jour type
            <select value={weekday} onChange={(event) => setWeekday(Number(event.target.value))}>
              {meta.weekdays.map((day) => (
                <option key={day.id} value={day.id}>
                  {day.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="employer-focus">
        <aside className="employer-roster" aria-label="Employés de l'organisation">
          <button
            type="button"
            className={personId === "" ? "active" : undefined}
            onClick={() => setPersonId("")}
          >
            <strong>Ensemble</strong>
            <span>{employees.length} employés</span>
          </button>
          {rosterGroups(employees).map((group) => (
            <div key={group.key} className="employer-roster-group">
              <p>
                {group.title} <span>({group.people.length})</span>
              </p>
              {group.people.map((employee) => (
                <button
                  key={employee.id}
                  type="button"
                  className={personId === employee.id ? "active" : undefined}
                  onClick={() => setPersonId(employee.id)}
                >
                  <strong>{employee.name}</strong>
                  <span>{employee.named ? "semaine détaillée" : employee.job}</span>
                </button>
              ))}
            </div>
          ))}
        </aside>
        <div>
      {person && (
        <section className="diary-profile">
          <strong>
            {person.age ? `${person.name}, ${person.age} ans — ${person.job}` : person.name}
          </strong>
          <p className="diary-muted">
            {view?.scope === "all"
              ? person.blurb
              : `Domicile : ${person.home} · Travail : ${person.work}. ${person.blurb}`}
          </p>
        </section>
      )}

      {view && (
        <section className="diary-kpis">
          <article className="diary-kpi">
            <span>Déplacements</span>
            <strong>{fmt(view.stats.trip_count)}</strong>
          </article>
          <article className="diary-kpi">
            <span>Distance</span>
            <strong>{fmt(view.stats.km)} km</strong>
          </article>
          <article className="diary-kpi">
            <span>Temps de trajet</span>
            <strong>
              {fmt(view.stats.duration.value)} {view.stats.duration.unit}
            </strong>
          </article>
          <article className="diary-kpi">
            <span>Hors travail</span>
            <strong>{fmt(view.stats.non_work_share)} %</strong>
          </article>
        </section>
      )}

      {view?.suggestions && (
        <section className="diary-suggestions">
          <h2>Près du domicile</h2>
          <p className="diary-muted">
            Courses et culte reviennent chaque semaine au même endroit. Quand un lieu plus proche existe, il est proposé ici.
          </p>
          {view.suggestions.length === 0 ? (
            <p className="diary-muted">Le supermarché et le lieu de culte habituels sont déjà les plus proches du domicile.</p>
          ) : (
            <ul>
              {view.suggestions.map((item) => (
                <li key={item.id} className={item.purpose === "culte" ? "is-culte" : "is-shop"}>
                  <strong>
                    {item.purpose_label} · {item.home_name}
                  </strong>
                  <p>{item.reading}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="diary-layout">
        <article className="diary-map-card">
          <div ref={setMapHost} className="diary-map" />
          <div className="diary-zoom">
            <strong>Niveau : {levelLabel}</strong>
            Dézoomez pour la ville. Zoomez pour les sous-villes, puis les quartiers.
          </div>
        </article>
        <div className="diary-charts">
          {view && (
            <>
              <VolumeChart volume={view.volume} period={period} />
              <ShareChart
                title={view.purposes.question}
                hint={
                  view.scope === "all"
                    ? "Une barre = un motif. La longueur est la part de tous les employés."
                    : "Une barre = un motif. La longueur est la part des trajets."
                }
                items={view.purposes.items}
                accent="diary-chart-why"
              />
              <ShareChart
                title={view.modes.question}
                hint={
                  view.scope === "all"
                    ? "Une barre = un mode, pour l'ensemble des employés."
                    : "Une barre = un mode. Ce n'est pas le même graph que les motifs."
                }
                items={view.modes.items}
                accent="diary-chart-how"
              />
              <p className="diary-muted">{view.note}</p>
            </>
          )}
        </div>
      </div>
        </div>
      </div>

      <div className="diary-bottom">
        <section className="diary-table-card">
          <h2>
            {view?.scope === "all"
              ? "Trajets de l'ensemble"
              : `Trajets de ${person ? person.name.split(" ")[0] : "la personne"}`}
          </h2>
          <p className="diary-muted">{view?.listing_note}</p>
          <div className="diary-table-wrap">
            <table className="diary-table">
              <thead>
                <tr>
                  <th>Quand</th>
                  <th>De → vers</th>
                  <th>Motif</th>
                  <th>Mode</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(view?.trips ?? []).map((trip) => (
                  <tr key={trip.id}>
                    <td>
                      {trip.weekday_label.includes("–") ? trip.weekday_label : trip.weekday_label.slice(0, 3)}{" "}
                      {trip.depart_label}
                      <span className="diary-detail">
                        {trip.minutes} min · {fmt(trip.km)} km
                        {trip.people && trip.people > 1 ? ` · ${fmt(trip.people)} employés` : ""}
                      </span>
                    </td>
                    <td>
                      {trip.origin_name} → {trip.destination_name}
                    </td>
                    <td>
                      <span className="diary-dot" style={{ background: trip.purpose_color }} />
                      {trip.purpose_label}
                      {trip.source === "saisie" && <span className="diary-tag">saisie</span>}
                      <span className="diary-detail">{trip.detail}</span>
                    </td>
                    <td>{trip.mode_label}</td>
                    <td>
                      {trip.source === "saisie" && (
                        <button type="button" className="diary-link" onClick={() => removeTrip(trip.id)}>
                          Retirer
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {selected?.named && (
        <form className="diary-form" onSubmit={submitTrip}>
          <h2>Saisir un déplacement</h2>
          <p className="diary-muted">
            Point A vers point B. Hors travail, la personne doit dire ce qu&apos;elle va faire
            (supermarché, visite, santé, loisir…).
          </p>
          <div className="diary-form-grid">
            <label className="field">
              Jour de la semaine type
              <select value={formDay} onChange={(event) => setFormDay(Number(event.target.value))}>
                {meta.weekdays.map((day) => (
                  <option key={day.id} value={day.id}>
                    {day.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Heure de départ
              <input type="time" value={depart} onChange={(event) => setDepart(event.target.value)} required />
            </label>
            <label className="field">
              Départ
              <select value={originId} onChange={(event) => setOriginId(event.target.value)} required>
                {[...groups.entries()].map(([name, places]) => (
                  <optgroup key={name} label={name}>
                    {places.map((place) => (
                      <option key={place.id} value={place.id}>
                        {place.name} — {place.role_label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className="field">
              Arrivée
              <select
                value={destinationId}
                onChange={(event) => setDestinationId(event.target.value)}
                required
              >
                {[...groups.entries()].map(([name, places]) => (
                  <optgroup key={name} label={name}>
                    {places.map((place) => (
                      <option key={place.id} value={place.id}>
                        {place.name} — {place.role_label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className="field">
              Motif
              <select value={purpose} onChange={(event) => setPurpose(event.target.value)}>
                {meta.purposes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Mode
              <select value={mode} onChange={(event) => setMode(event.target.value)}>
                {meta.modes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field wide">
              {needsDetail ? "Ce que la personne mentionne" : "Précision (facultative)"}
              <textarea
                rows={3}
                value={detail}
                required={needsDetail}
                minLength={needsDetail ? 8 : undefined}
                placeholder="Ex. : courses au supermarché Jumbo, rendez-vous médical, visite famille"
                onChange={(event) => setDetail(event.target.value)}
              />
            </label>
          </div>
          {formError && <p className="diary-error">{formError}</p>}
          {formNote && <p className="diary-muted">{formNote}</p>}
          <button type="submit" disabled={saving || !personId}>
            {saving ? "Enregistrement…" : "Ajouter à la semaine type"}
          </button>
        </form>
        )}
      </div>
      </>
      )}

      <div className="journey-nav">
        <button type="button" disabled={stepIndex === 0} onClick={() => goTo(stepIndex - 1)}>
          Retour
        </button>
        {stepIndex < JOURNEY.length - 1 && (
          <button type="button" className="journey-next" disabled={continueBlocked} onClick={() => goTo(stepIndex + 1)}>
            {JOURNEY[stepIndex].next}
          </button>
        )}
        {phase === "needs" && journey && journey.farIds.length > 0 && needIds.length === 0 && (
          <p>Cochez au moins un groupe éloigné.</p>
        )}
        {phase === "satellite" && journey && journey.satelliteIds.length > 0 && !satelliteId && (
          <p>Choisissez le bureau satellite à tester.</p>
        )}
      </div>
    </div>
  );
}
