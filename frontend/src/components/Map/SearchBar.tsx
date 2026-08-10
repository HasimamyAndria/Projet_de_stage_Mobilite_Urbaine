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

  async function search() {
    if (!query.trim()) return;
    try {
      const response = await api.get("/api/search", { params: { q: query } });
      setResults(response.data);
    } catch (error) {
      console.error(error);
    }
  }

  function selectPlace(place: SearchResult) {
    onSelectLocation(place.lon, place.lat);
    setResults([]);
    setQuery(place.name);
  }

  return (
    <div className="search-card">
      <h3>Recherche</h3>
      <input
        type="text"
        value={query}
        placeholder="Rechercher un lieu…"
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") search();
        }}
      />
      <button type="button" onClick={search}>
        Rechercher
      </button>
      {results.length > 0 && (
        <div className="search-results">
          {results.map((place, index) => (
            <button
              type="button"
              key={`${place.name}-${index}`}
              onClick={() => selectPlace(place)}
            >
              <strong>{place.name}</strong>
              <br />
              <small>{place.place}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
