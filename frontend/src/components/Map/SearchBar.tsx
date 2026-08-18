import { useState } from "react";
import api from "../../services/api";

type SearchResult = {
  name: string;
  lon: number;
  lat: number;
  place: string;
};

type Props = {
  onSelectLocation: (lon: number, lat: number) => void;
};

export default function SearchBar({ onSelectLocation }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.get("/api/search", { params: { q: query } });
      const list = Array.isArray(response.data) ? response.data : [];
      setResults(list);
      if (!list.length) {
        setError("Aucun lieu trouvé dans OSM pour cette requête.");
      }
    } catch (err) {
      console.error(err);
      setError("Recherche indisponible (API).");
    } finally {
      setBusy(false);
    }
  }

  function selectPlace(place: SearchResult) {
    onSelectLocation(place.lon, place.lat);
    setResults([]);
    setQuery(place.name);
  }

  return (
    <div className="map-ctrl search-ctrl">
      <input
        type="search"
        value={query}
        placeholder="Rechercher un lieu…"
        aria-label="Rechercher un lieu"
        onChange={(e) => {
          setQuery(e.target.value);
          if (!e.target.value) {
            setResults([]);
            setError(null);
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") search();
        }}
      />
      {results.length > 0 && (
        <div className="map-ctrl-popover search-results-popover">
          {results.map((place, index) => (
            <button
              type="button"
              key={`${place.name}-${index}`}
              onClick={() => selectPlace(place)}
            >
              <strong>{place.name}</strong>
              <small>{place.place}</small>
            </button>
          ))}
        </div>
      )}
      {busy && results.length === 0 && !error && (
        <div className="map-ctrl-hint">Recherche…</div>
      )}
      {error && results.length === 0 && (
        <div className="map-ctrl-hint" role="status">
          {error}
        </div>
      )}
    </div>
  );
}
