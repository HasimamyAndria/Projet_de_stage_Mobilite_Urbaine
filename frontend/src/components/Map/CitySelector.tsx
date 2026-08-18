import { useEffect, useState } from "react";
import api from "../../services/api";
import { usePopover } from "./usePopover";

export type CityBBox = {
  name: string;
  display_name?: string;
  country?: string | null;
  lon: number;
  lat: number;
  west: number;
  south: number;
  east: number;
  north: number;
};

export type ActiveCity = CityBBox & {
  osm_ready: boolean;
  message?: string | null;
  seed_stats?: {
    zones?: number;
    flows?: number;
    trips?: number;
  } | null;
  is_default?: boolean;
};

type Props = {
  onActivated: (city: ActiveCity, meta?: { seeding?: boolean }) => void;
};

export default function CitySelector({ onActivated }: Props) {
  const { open, setOpen, ref } = usePopover();
  const [presets, setPresets] = useState<CityBBox[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CityBBox[]>([]);
  const [current, setCurrent] = useState<ActiveCity | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function boot() {
      try {
        const [presetRes, currentRes] = await Promise.all([
          api.get("/api/cities/presets"),
          api.get("/api/cities/current"),
        ]);
        setPresets(presetRes.data.presets || []);
        setCurrent(currentRes.data);
        if (currentRes.data) onActivated(currentRes.data);
      } catch (err) {
        console.error(err);
        setError("Impossible de charger le contexte ville.");
      }
    }
    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function search() {
    if (query.trim().length < 2) return;
    setError(null);
    try {
      const res = await api.get("/api/cities/search", {
        params: { q: query.trim(), limit: 6 },
      });
      setResults(res.data.results || []);
      if (!(res.data.results || []).length) {
        setError("Aucune ville trouvée.");
      }
    } catch (err) {
      console.error(err);
      setError("Recherche Nominatim indisponible.");
    }
  }

  async function activate(city: CityBBox) {
    setBusy(true);
    setError(null);
    setResults([]);
    setOpen(false);
    const preview: ActiveCity = {
      ...city,
      display_name: city.display_name || city.name,
      osm_ready: false,
      message: `Cadrage sur ${city.name}…`,
    };
    setCurrent(preview);
    onActivated(preview, { seeding: true });
    try {
      const res = await api.post(
        "/api/cities/activate",
        {
          name: city.name,
          display_name: city.display_name || city.name,
          country: city.country,
          lon: city.lon,
          lat: city.lat,
          west: city.west,
          south: city.south,
          east: city.east,
          north: city.north,
          top_n: 36,
        },
        { timeout: 180000 }
      );
      setCurrent(res.data);
      setQuery("");
      onActivated(res.data);
    } catch (err: unknown) {
      console.error(err);
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Échec d’activation de la ville.";
      setError(String(detail));
      setOpen(true);
    } finally {
      setBusy(false);
    }
  }

  const label = busy
    ? "Activation…"
    : current?.name || "Ville";

  return (
    <div className="map-ctrl" ref={ref}>
      <button
        type="button"
        className={open ? "map-ctrl-toggle is-open" : "map-ctrl-toggle"}
        onClick={() => setOpen((value) => !value)}
        disabled={busy}
        aria-expanded={open}
      >
        {label}
      </button>
      {open && (
        <div className="map-ctrl-popover city-popover">
          <p className="map-ctrl-group">Villes prêtes</p>
          <div className="city-presets">
            {presets.map((preset) => (
              <button
                key={preset.name}
                type="button"
                className={
                  current?.name === preset.name ? "city-chip active" : "city-chip"
                }
                disabled={busy}
                onClick={() => activate(preset)}
              >
                {preset.name}
              </button>
            ))}
          </div>

          <p className="map-ctrl-group">Autre ville</p>
          <div className="city-search-row">
            <input
              type="search"
              value={query}
              placeholder="Paris, Madrid…"
              disabled={busy}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") search();
              }}
            />
            <button
              type="button"
              className="city-search-btn"
              onClick={search}
              disabled={busy}
            >
              OK
            </button>
          </div>

          {results.length > 0 && (
            <div className="search-results-popover city-results">
              {results.map((city, index) => (
                <button
                  type="button"
                  key={`${city.name}-${index}`}
                  disabled={busy}
                  onClick={() => activate(city)}
                >
                  <strong>{city.name}</strong>
                  <small>{city.display_name || city.country}</small>
                </button>
              ))}
            </div>
          )}

          {current && (
            <div
              className={current.osm_ready ? "city-status ok" : "city-status warn"}
              role="status"
            >
              <strong>{current.display_name || current.name}</strong>
              <span>
                {current.osm_ready
                  ? `OSM prêt · ${current.seed_stats?.zones ?? "?"} zones`
                  : "OSM manquant pour cette bbox"}
              </span>
            </div>
          )}

          {error && (
            <div className="city-status warn" role="alert">
              <small>{error}</small>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
