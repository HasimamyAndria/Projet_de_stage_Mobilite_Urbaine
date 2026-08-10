# -*- coding: utf-8 -*-
"""Trouve 2 points A/B connectes pour la demo route (sous-graphe Tana)."""
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

edges_sql = """
SELECT id, source, target, cost, reverse_cost
FROM roads_network
WHERE way && ST_Transform(
    ST_MakeEnvelope(47.48, -18.93, 47.55, -18.86, 4326),
    3857
)
"""

# start = sommet le plus proche du centre ville
start = db.execute(
    text(
        """
        SELECT id,
               ST_X(ST_Transform(the_geom,4326)) AS lon,
               ST_Y(ST_Transform(the_geom,4326)) AS lat
        FROM roads_network_vertices_pgr
        ORDER BY the_geom <-> ST_Transform(
            ST_SetSRID(ST_Point(47.52, -18.91), 4326), 3857
        )
        LIMIT 1
        """
    )
).fetchone()
print("start", start.id, start.lon, start.lat)

# drivingDistance dans le sous-graphe (rapide)
dd = db.execute(
    text(
        """
        SELECT node, agg_cost
        FROM pgr_drivingDistance(
            :edges,
            :start_id,
            2000,
            false
        )
        WHERE agg_cost BETWEEN 900 AND 1800
        ORDER BY agg_cost DESC
        LIMIT 1
        """
    ),
    {"edges": edges_sql, "start_id": start.id},
).fetchone()

if not dd:
    print("NO_END")
    db.close()
    raise SystemExit(1)

end = db.execute(
    text(
        """
        SELECT id,
               ST_X(ST_Transform(the_geom,4326)) AS lon,
               ST_Y(ST_Transform(the_geom,4326)) AS lat
        FROM roads_network_vertices_pgr
        WHERE id = :id
        """
    ),
    {"id": dd.node},
).fetchone()
print("end", end.id, end.lon, end.lat, "cost", round(dd.agg_cost, 1))

n = db.execute(
    text(
        """
        SELECT COUNT(*) FILTER (WHERE edge <> -1) AS edges
        FROM pgr_dijkstra(:edges, :s, :e, false)
        """
    ),
    {"edges": edges_sql, "s": start.id, "e": end.id},
).scalar()
print("dijkstra_edges", n)
print("DEMO_COORDS")
print(f"  startLon={start.lon}")
print(f"  startLat={start.lat}")
print(f"  endLon={end.lon}")
print(f"  endLat={end.lat}")
db.close()
