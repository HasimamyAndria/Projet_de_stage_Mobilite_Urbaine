import { useState } from "react";
import api from "../../services/api";

type SearchResult = {
    name: string;
    lon: number;
    lat: number;
    place: string;
};

type Props = {
    onSelectLocation: (
        lon: number,
        lat: number
    ) => void;
};

export default function SearchBar({
    onSelectLocation
}: Props) {

    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);

    //--------------------------------------------------
    // Recherche
    //--------------------------------------------------

    async function search() {

        if (!query.trim()) return;

        try {

            const response = await api.get(
                "/api/search",
                {
                    params: {
                        q: query
                    }
                }
            );

            console.log(
                "Résultats :",
                response.data
            );

            setResults(response.data);

        }

        catch (error) {

            console.error(error);

        }

    }

    //--------------------------------------------------
    // Sélection d'un résultat
    //--------------------------------------------------

    function selectPlace(
        place: SearchResult
    ) {

        console.log(
            "Lieu sélectionné :",
            place
        );

        onSelectLocation(
            place.lon,
            place.lat
        );

        setResults([]);
        setQuery(place.name);

    }

    return (

        <div
            style={{
                position: "absolute",
                top: "10px",
                left: "120px",
                zIndex: 9999,
                width: "320px"
            }}
        >

            <div
                style={{
                    background: "white",
                    padding: "10px",
                    borderRadius: "8px",
                    boxShadow:
                        "0 2px 8px rgba(0,0,0,0.2)"
                }}
            >

                <input
                    type="text"
                    value={query}
                    placeholder="Rechercher un lieu..."
                    onChange={(e) =>
                        setQuery(
                            e.target.value
                        )
                    }
                    style={{
                        width: "100%",
                        padding: "8px",
                        marginBottom: "8px"
                    }}
                />

                <button
                    onClick={search}
                    style={{
                        width: "100%",
                        padding: "8px",
                        cursor: "pointer"
                    }}
                >
                    Rechercher
                </button>

            </div>

            {results.length > 0 && (

                <div
                    style={{
                        background: "white",
                        marginTop: "5px",
                        borderRadius: "8px",
                        maxHeight: "250px",
                        overflowY: "auto",
                        boxShadow:
                            "0 2px 8px rgba(0,0,0,0.2)"
                    }}
                >

                    {results.map(
                        (place, index) => (

                            <div
                                key={index}
                                onClick={() =>
                                    selectPlace(place)
                                }
                                style={{
                                    padding: "10px",
                                    cursor: "pointer",
                                    borderBottom:
                                        "1px solid #eee"
                                }}
                            >

                                <strong>
                                    {place.name}
                                </strong>

                                <br />

                                <small>
                                    {place.place}
                                </small>

                            </div>

                        )
                    )}

                </div>

            )}

        </div>

    );

}