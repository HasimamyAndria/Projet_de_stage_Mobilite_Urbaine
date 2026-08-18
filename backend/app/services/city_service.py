# -*- coding: utf-8 -*-
"""Contexte ville active + couverture OSM (pipeline multi-villes)."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

# Import du seed OSM (scripts/ hors package app)
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from seed_zones_od_osm import seed as seed_osm_bbox  # noqa: E402

USER_AGENT = "MobiliteUrbaine-Stage/1.0 (educational; contact=local-demo)"
MIN_BUILDINGS = 200
MIN_PLACES = 3
MAX_BBOX_SPAN_DEG = 0.22  # ~20–25 km

# Villes de démarrage (démo + exemples internationaux)
CITY_PRESETS: list[dict] = [
    {
        "name": "Antananarivo",
        "display_name": "Antananarivo, Madagascar",
        "country": "Madagascar",
        "lon": 47.5079,
        "lat": -18.8792,
        "west": 47.450,
        "south": -18.950,
        "east": 47.565,
        "north": -18.820,
    },
    {
        "name": "Paris",
        "display_name": "Paris, France",
        "country": "France",
        "lon": 2.3522,
        "lat": 48.8566,
        "west": 2.25,
        "south": 48.80,
        "east": 2.45,
        "north": 48.91,
    },
    {
        "name": "Madrid",
        "display_name": "Madrid, Spain",
        "country": "Spain",
        "lon": -3.7038,
        "lat": 40.4168,
        "west": -3.78,
        "south": 40.35,
        "east": -3.62,
        "north": 40.48,
    },
]


def ensure_city_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS app_active_city (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name VARCHAR(120) NOT NULL,
                display_name VARCHAR(250),
                country VARCHAR(120),
                lon DOUBLE PRECISION NOT NULL,
                lat DOUBLE PRECISION NOT NULL,
                west DOUBLE PRECISION NOT NULL,
                south DOUBLE PRECISION NOT NULL,
                east DOUBLE PRECISION NOT NULL,
                north DOUBLE PRECISION NOT NULL,
                osm_ready BOOLEAN NOT NULL DEFAULT FALSE,
                seed_stats JSONB,
                message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.commit()


def clamp_bbox(
    west: float,
    south: float,
    east: float,
    north: float,
    lon: float,
    lat: float,
    max_span: float = MAX_BBOX_SPAN_DEG,
) -> tuple[float, float, float, float]:
    """Réduit une bbox trop large autour du centre (perf seed / carte)."""
    west, south, east, north = float(west), float(south), float(east), float(north)
    if east - west > max_span:
        half = max_span / 2
        west, east = lon - half, lon + half
    if north - south > max_span:
        half = max_span / 2
        south, north = lat - half, lat + half
    return west, south, east, north


def check_osm_coverage(
    db: Session,
    west: float,
    south: float,
    east: float,
    north: float,
) -> dict:
    """Compte bâtiments / lieux OSM dans la bbox."""
    has_table = db.execute(
        text(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'planet_osm_polygon'
            """
        )
    ).scalar()
    if not has_table:
        return {
            "osm_ready": False,
            "buildings": 0,
            "places": 0,
            "message": "Tables planet_osm_* absentes — importer un PBF (osm2pgsql).",
        }

    buildings = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM planet_osm_polygon
            WHERE building IS NOT NULL
              AND way && ST_Transform(
                  ST_MakeEnvelope(:w, :s, :e, :n, 4326),
                  3857
              )
            """
        ),
        {"w": west, "s": south, "e": east, "n": north},
    ).scalar()

    places = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM planet_osm_point
            WHERE place IN ('suburb', 'quarter', 'neighbourhood', 'town', 'city')
              AND name IS NOT NULL
              AND ST_Transform(way, 4326) &&
                  ST_MakeEnvelope(:w, :s, :e, :n, 4326)
            """
        ),
        {"w": west, "s": south, "e": east, "n": north},
    ).scalar()

    buildings = int(buildings or 0)
    places = int(places or 0)
    ready = buildings >= MIN_BUILDINGS and places >= MIN_PLACES
    if ready:
        msg = (
            f"Couverture OSM OK ({buildings} bâtiments, {places} lieux) — "
            "seed analytics possible."
        )
    else:
        msg = (
            f"OSM insuffisant dans cette bbox ({buildings} bâtiments, {places} lieux). "
            "Importer un extract de la ville (Geofabrik + osm2pgsql), "
            "puis réactiver la ville."
        )
    return {
        "osm_ready": ready,
        "buildings": buildings,
        "places": places,
        "message": msg,
    }


def nominatim_search_cities(q: str, limit: int = 6) -> list[dict]:
    """Recherche mondiale de villes via Nominatim (OSM)."""
    query = (q or "").strip()
    if len(query) < 2:
        return []

    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": max(1, min(limit, 10)),
            "featuretype": "city",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "fr,en",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    out: list[dict] = []
    for item in raw:
        try:
            lon = float(item["lon"])
            lat = float(item["lat"])
            # Nominatim boundingbox: [south, north, west, east]
            bb = item.get("boundingbox") or []
            south, north, west, east = map(float, bb[:4])
            west, south, east, north = clamp_bbox(
                west, south, east, north, lon, lat
            )
        except (KeyError, TypeError, ValueError):
            continue

        addr = item.get("address") or {}
        country = addr.get("country") or ""
        name = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("municipality")
            or (item.get("name") if isinstance(item.get("name"), str) else None)
            or item.get("display_name", "").split(",")[0]
        )
        out.append(
            {
                "name": name,
                "display_name": item.get("display_name") or name,
                "country": country,
                "lon": lon,
                "lat": lat,
                "west": west,
                "south": south,
                "east": east,
                "north": north,
                "osm_type": item.get("type"),
                "importance": item.get("importance"),
            }
        )
    return out


def clear_analytics(db: Session) -> None:
    db.execute(text("TRUNCATE TABLE mobility_flows RESTART IDENTITY"))
    db.execute(text("DELETE FROM mobility_zones"))
    db.commit()


def get_active_city(db: Session) -> dict | None:
    ensure_city_table(db)
    row = db.execute(
        text(
            """
            SELECT
                name, display_name, country, lon, lat,
                west, south, east, north, osm_ready, seed_stats, message
            FROM app_active_city WHERE id = 1
            """
        )
    ).fetchone()
    if not row:
        # Défaut Antananarivo (preset)
        preset = CITY_PRESETS[0]
        cov = check_osm_coverage(
            db,
            preset["west"],
            preset["south"],
            preset["east"],
            preset["north"],
        )
        return {
            **preset,
            "osm_ready": cov["osm_ready"],
            "coverage": cov,
            "seed_stats": None,
            "message": cov["message"],
            "is_default": True,
        }

    stats = row.seed_stats
    if isinstance(stats, str):
        try:
            stats = json.loads(stats)
        except json.JSONDecodeError:
            stats = None

    return {
        "name": row.name,
        "display_name": row.display_name,
        "country": row.country,
        "lon": float(row.lon),
        "lat": float(row.lat),
        "west": float(row.west),
        "south": float(row.south),
        "east": float(row.east),
        "north": float(row.north),
        "osm_ready": bool(row.osm_ready),
        "seed_stats": stats,
        "message": row.message,
        "is_default": False,
    }


def _upsert_active_city(db: Session, payload: dict) -> None:
    ensure_city_table(db)
    db.execute(
        text(
            """
            INSERT INTO app_active_city (
                id, name, display_name, country, lon, lat,
                west, south, east, north, osm_ready, seed_stats, message, updated_at
            ) VALUES (
                1, :name, :display_name, :country, :lon, :lat,
                :west, :south, :east, :north, :osm_ready,
                CAST(:seed_stats AS jsonb), :message, CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                display_name = EXCLUDED.display_name,
                country = EXCLUDED.country,
                lon = EXCLUDED.lon,
                lat = EXCLUDED.lat,
                west = EXCLUDED.west,
                south = EXCLUDED.south,
                east = EXCLUDED.east,
                north = EXCLUDED.north,
                osm_ready = EXCLUDED.osm_ready,
                seed_stats = EXCLUDED.seed_stats,
                message = EXCLUDED.message,
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "name": payload["name"],
            "display_name": payload.get("display_name"),
            "country": payload.get("country"),
            "lon": payload["lon"],
            "lat": payload["lat"],
            "west": payload["west"],
            "south": payload["south"],
            "east": payload["east"],
            "north": payload["north"],
            "osm_ready": payload["osm_ready"],
            "seed_stats": json.dumps(payload.get("seed_stats")),
            "message": payload.get("message"),
        },
    )
    db.commit()


def activate_city(
    db: Session,
    *,
    name: str,
    display_name: str | None,
    country: str | None,
    lon: float,
    lat: float,
    west: float,
    south: float,
    east: float,
    north: float,
    top_n: int = 36,
    force_seed: bool = True,
) -> dict:
    """
    Active une ville : vérifie OSM, seed OD si possible, sinon vide les analytics.
    """
    west, south, east, north = clamp_bbox(west, south, east, north, lon, lat)
    coverage = check_osm_coverage(db, west, south, east, north)

    seed_stats = None
    osm_ready = coverage["osm_ready"]
    message = coverage["message"]

    if osm_ready and force_seed:
        # Seed hors session SQLAlchemy (connexion dédiée dans le script)
        try:
            seed_stats = seed_osm_bbox(
                top_n=max(3, int(top_n)),
                xmin=west,
                ymin=south,
                xmax=east,
                ymax=north,
            )
            message = (
                f"Ville active : {name}. "
                f"Seed OSM OK ({seed_stats.get('zones')} zones, "
                f"{seed_stats.get('flows')} flux)."
            )
        except Exception as exc:
            osm_ready = False
            clear_analytics(db)
            message = f"Échec seed OSM pour {name} : {exc}"
    else:
        # Évite d'afficher l'OD d'une autre ville sur la carte
        clear_analytics(db)
        if not osm_ready:
            message = coverage["message"]

    payload = {
        "name": name,
        "display_name": display_name or name,
        "country": country,
        "lon": lon,
        "lat": lat,
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "osm_ready": osm_ready,
        "seed_stats": seed_stats,
        "message": message,
        "coverage": coverage,
    }
    _upsert_active_city(db, payload)
    return payload
