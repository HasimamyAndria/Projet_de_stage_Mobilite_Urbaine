"""Itinéraire A→B (pgRouting) sur un sous-graphe bbox.

Le graphe OSM est fragmenté : le sommet le plus proche d'un clic peut
appartenir à une impasse isolée. On ancre A sur un sommet du sous-graphe,
puis on choisit pour B le sommet **atteignable** le plus proche.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("mobilite.routing")

# Coûts = mètres (ST_Length). 30 km couvre Tana / un centre-ville.
_MAX_DRIVE_M = 30000
_PADS_DEG = (0.08, 0.14, 0.22)


def _edges_sql(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    return (
        "SELECT id, source, target, cost, reverse_cost "
        "FROM roads_network "
        "WHERE way && ST_Transform("
        f"ST_MakeEnvelope({float(min_lon)}, {float(min_lat)}, "
        f"{float(max_lon)}, {float(max_lat)}, 4326), 3857)"
    )


def _empty(detail: str) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [],
        "adjusted": False,
        "detail": detail,
    }


def _nearest_vertices(
    db: Session,
    lon: float,
    lat: float,
    edges_sql: str,
    limit: int = 8,
) -> list:
    sql = text(
        """
        WITH edge_nodes AS (
            SELECT source AS vid FROM ("""
        + edges_sql
        + """) e
            UNION
            SELECT target AS vid FROM ("""
        + edges_sql
        + """) e
        )
        SELECT
            v.id,
            ST_X(ST_Transform(v.the_geom, 4326)) AS lon,
            ST_Y(ST_Transform(v.the_geom, 4326)) AS lat,
            ST_Distance(
                v.the_geom,
                ST_Transform(ST_SetSRID(ST_Point(:lon, :lat), 4326), 3857)
            ) AS dist_m
        FROM roads_network_vertices_pgr v
        JOIN edge_nodes n ON n.vid = v.id
        ORDER BY v.the_geom <-> ST_Transform(
            ST_SetSRID(ST_Point(:lon, :lat), 4326), 3857
        )
        LIMIT :lim
        """
    )
    return db.execute(sql, {"lon": lon, "lat": lat, "lim": limit}).fetchall()


def _closest_reachable(
    db: Session,
    edges_sql: str,
    start_id: int,
    end_lon: float,
    end_lat: float,
):
    sql = text(
        """
        SELECT
            dd.node AS id,
            ST_X(ST_Transform(v.the_geom, 4326)) AS lon,
            ST_Y(ST_Transform(v.the_geom, 4326)) AS lat,
            ST_Distance(
                v.the_geom,
                ST_Transform(ST_SetSRID(ST_Point(:lon, :lat), 4326), 3857)
            ) AS dist_m
        FROM pgr_drivingDistance(
            :edges_sql,
            :start_id,
            :max_cost,
            false
        ) AS dd
        JOIN roads_network_vertices_pgr v ON v.id = dd.node
        WHERE dd.node <> :start_id
        ORDER BY v.the_geom <-> ST_Transform(
            ST_SetSRID(ST_Point(:lon, :lat), 4326), 3857
        )
        LIMIT 1
        """
    )
    return db.execute(
        sql,
        {
            "edges_sql": edges_sql,
            "start_id": start_id,
            "max_cost": _MAX_DRIVE_M,
            "lon": end_lon,
            "lat": end_lat,
        },
    ).fetchone()


def _dijkstra_features(db: Session, edges_sql: str, start_id: int, end_id: int) -> list:
    rows = db.execute(
        text(
            """
            SELECT
                rn.id,
                ST_AsGeoJSON(ST_Transform(rn.way, 4326))::json AS geometry
            FROM pgr_dijkstra(
                :edges_sql,
                :start_id,
                :end_id,
                false
            ) AS route
            JOIN roads_network rn ON route.edge = rn.id
            WHERE route.edge <> -1
            """
        ),
        {"edges_sql": edges_sql, "start_id": start_id, "end_id": end_id},
    ).fetchall()
    return [
        {
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {"id": row.id},
        }
        for row in rows
    ]


def calculate_route(
    db: Session,
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
) -> dict:
    logger.info(
        "route A=(%s,%s) B=(%s,%s)", start_lon, start_lat, end_lon, end_lat
    )

    last_detail = "Aucune route à proximité de ces points."

    for pad in _PADS_DEG:
        min_lon = min(start_lon, end_lon) - pad
        max_lon = max(start_lon, end_lon) + pad
        min_lat = min(start_lat, end_lat) - pad
        max_lat = max(start_lat, end_lat) + pad
        edges_sql = _edges_sql(min_lon, min_lat, max_lon, max_lat)

        starts = _nearest_vertices(db, start_lon, start_lat, edges_sql)
        if not starts:
            last_detail = "Pas de sommet routier dans la zone (réseau OSM absent ?)."
            continue

        best = None
        for start in starts:
            if start.dist_m > 1500:
                continue
            reached = _closest_reachable(db, edges_sql, start.id, end_lon, end_lat)
            if reached is None:
                continue
            if best is None or float(reached.dist_m) < float(best[1].dist_m):
                best = (start, reached)
            if float(reached.dist_m) <= 400:
                break

        if best is None:
            last_detail = "Le départ est sur un fragment de réseau trop petit."
            logger.info("aucun sommet atteignable pad=%s", pad)
            continue

        start, reached = best
        features = _dijkstra_features(db, edges_sql, start.id, reached.id)
        if not features:
            last_detail = "Dijkstra vide malgré un sommet atteignable."
            continue

        adjusted = float(reached.dist_m) > 250
        detail = (
            "Arrivée calée sur le réseau routier connecté (le clic n’était pas "
            "sur la même composante)."
            if adjusted
            else "Itinéraire réseau (pgRouting)."
        )
        logger.info(
            "route OK segments=%s start=%s end=%s pad=%s adjusted=%s",
            len(features),
            start.id,
            reached.id,
            pad,
            adjusted,
        )
        return {
            "type": "FeatureCollection",
            "features": features,
            "adjusted": adjusted,
            "detail": detail,
            "snapped_start": {"lon": float(start.lon), "lat": float(start.lat)},
            "snapped_end": {"lon": float(reached.lon), "lat": float(reached.lat)},
        }

    logger.info("route FAIL %s", last_detail)
    return _empty(last_detail)
