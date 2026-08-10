from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter(
    prefix="/api",
    tags=["Map"]
)

# =====================================================
# ROUTES
# =====================================================

@router.get("/roads")
def get_roads(
    minLon: float,
    minLat: float,
    maxLon: float,
    maxLat: float,
    db: Session = Depends(get_db)
):

    print("========== ROUTES ==========")
    print(f"BBOX : {minLon}, {minLat}, {maxLon}, {maxLat}")

    sql = text("""
        SELECT
            osm_id,
            name,
            highway,
            ST_AsGeoJSON(
                ST_Transform(way,4326)
            )::json AS geometry

        FROM planet_osm_line

        WHERE highway IS NOT NULL

        AND way && ST_Transform(
            ST_MakeEnvelope(
                :minLon,
                :minLat,
                :maxLon,
                :maxLat,
                4326
            ),
            3857
        )

        LIMIT 5000;
    """)

    rows = db.execute(sql, {
        "minLon": minLon,
        "minLat": minLat,
        "maxLon": maxLon,
        "maxLat": maxLat
    }).fetchall()

    print("Nombre de routes :", len(rows))

    features = []

    for row in rows:

        features.append({

            "type": "Feature",

            "geometry": row.geometry,

            "properties": {

                "osm_id": row.osm_id,

                "name": row.name,

                "highway": row.highway

            }

        })

    return {

        "type": "FeatureCollection",

        "features": features

    }


# =====================================================
# BATIMENTS
# =====================================================

@router.get("/buildings")
def get_buildings(
    minLon: float,
    minLat: float,
    maxLon: float,
    maxLat: float,
    db: Session =Depends(get_db)
):

    print("========== BUILDINGS ==========")
    print(f"BBOX : {minLon}, {minLat}, {maxLon}, {maxLat}")

    sql = text("""
        SELECT

            osm_id,

            building,

            ST_AsGeoJSON(
                ST_Transform(way,4326)
            )::json AS geometry

        FROM planet_osm_polygon

        WHERE building IS NOT NULL

        AND way && ST_Transform(
            ST_MakeEnvelope(
                :minLon,
                :minLat,
                :maxLon,
                :maxLat,
                4326
            ),
            3857
        )

        LIMIT 3000;
    """)

    rows = db.execute(sql, {

        "minLon": minLon,

        "minLat": minLat,

        "maxLon": maxLon,

        "maxLat": maxLat

    }).fetchall()

    print("Nombre de bâtiments :", len(rows))

    if len(rows) > 0:

        print("Premier bâtiment :")

        print(rows[0].geometry)

    features = []

    for row in rows:

        features.append({

            "type": "Feature",

            "geometry": row.geometry,

            "properties": {

                "osm_id": row.osm_id,

                "building": row.building

            }

        })

    return {

        "type": "FeatureCollection",

        "features": features

    }

# ==========================================================
# Endpoint : Arrêts de bus
# ==========================================================

@router.get("/bus-stops")
def get_bus_stops(
    minLon: float,
    minLat: float,
    maxLon: float,
    maxLat: float,
    db: Session = Depends(get_db)
):

    print(f"Bus Stops BBOX : {minLon}, {minLat}, {maxLon}, {maxLat}")

    sql = text("""
        SELECT
            osm_id,
            name,
            highway,
            public_transport,
            ST_AsGeoJSON(
                ST_Transform(way,4326)
            )::json AS geometry
        FROM planet_osm_point
        WHERE
            highway='bus_stop'
            AND ST_Intersects(
                way,
                ST_Transform(
                    ST_MakeEnvelope(
                        :minLon,
                        :minLat,
                        :maxLon,
                        :maxLat,
                        4326
                    ),
                    3857
                )
            );
    """)

    rows = db.execute(sql, {
        "minLon": minLon,
        "minLat": minLat,
        "maxLon": maxLon,
        "maxLat": maxLat
    }).fetchall()

    print(f"Nombre d'arrêts : {len(rows)}")

    features = []

    for row in rows:

        features.append({

            "type": "Feature",

            "geometry": row.geometry,

            "properties": {

                "osm_id": row.osm_id,

                "name": row.name,

                "highway": row.highway,

                "public_transport": row.public_transport

            }

        })

    return {

        "type": "FeatureCollection",

        "features": features

    }

# ============================================================
# Endpoint : Lignes de bus
# ============================================================

@router.get("/bus-lines")
def get_bus_lines(
    minLon: float,
    minLat: float,
    maxLon: float,
    maxLat: float,
    db: Session = Depends(get_db)
):

    print("========== LIGNES DE BUS ==========")
    print(f"BBOX : {minLon}, {minLat}, {maxLon}, {maxLat}")

    sql = text("""
        SELECT
            osm_id,
            name,
            ref,
            operator,
            route,
            ST_AsGeoJSON(
                ST_Transform(way,4326)
            )::json AS geometry

        FROM planet_osm_line

        WHERE
            route = 'bus'

            AND ST_Intersects(

                way,

                ST_Transform(

                    ST_MakeEnvelope(

                        :minLon,
                        :minLat,
                        :maxLon,
                        :maxLat,
                        4326

                    ),

                    3857

                )

            )

        LIMIT 1000;
    """)

    rows = db.execute(sql, {

        "minLon": minLon,
        "minLat": minLat,
        "maxLon": maxLon,
        "maxLat": maxLat

    }).fetchall()

    print("Nombre de lignes :", len(rows))

    features = []

    for row in rows:

        features.append({

            "type": "Feature",

            "geometry": row.geometry,

            "properties": {

                "osm_id": row.osm_id,

                "name": row.name,

                "ref": row.ref,

                "operator": row.operator,

                "route": row.route

            }

        })

    return {

        "type": "FeatureCollection",

        "features": features

    }

#Searchbar endpoint
@router.get("/search")
def search_place(
    q: str,
    db: Session = Depends(get_db)
):

    sql = text("""
        SELECT
            name,

            ST_X(
                ST_Transform(
                    way,
                    4326
                )
            ) AS lon,

            ST_Y(
                ST_Transform(
                    way,
                    4326
                )
            ) AS lat,

            place

        FROM planet_osm_point

        WHERE
            name IS NOT NULL
            AND name ILIKE :query

        ORDER BY

            CASE

                WHEN place='city' THEN 1
                WHEN place='town' THEN 2
                WHEN place='village' THEN 3
                WHEN place='suburb' THEN 4
                ELSE 5

            END

        LIMIT 20
    """)

    rows = db.execute(
        sql,
        {
            "query": f"%{q}%"
        }
    ).fetchall()

    return [

        {
            "name": row.name,
            "lon": row.lon,
            "lat": row.lat,
            "place": row.place
        }

        for row in rows

    ]

@router.get("/route")
def calculate_route(
    startLon: float,
    startLat: float,
    endLon: float,
    endLat: float,
    db: Session = Depends(get_db)
):

    #=================================================
    # Sommet de départ
    #=================================================

    start_vertex_sql = text("""

        SELECT id
        FROM roads_network_vertices_pgr

        ORDER BY

        the_geom <->

        ST_Transform(

            ST_SetSRID(

                ST_Point(
                    :lon,
                    :lat
                ),

                4326

            ),

            3857

        )

        LIMIT 1;

    """)

    start_vertex = db.execute(

        start_vertex_sql,

        {
            "lon": startLon,
            "lat": startLat
        }

    ).fetchone()


    #=================================================
    # Sommet d'arrivée
    #=================================================

    end_vertex_sql = text("""

        SELECT id
        FROM roads_network_vertices_pgr

        ORDER BY

        the_geom <->

        ST_Transform(

            ST_SetSRID(

                ST_Point(
                    :lon,
                    :lat
                ),

                4326

            ),

            3857

        )

        LIMIT 1;

    """)

    end_vertex = db.execute(

        end_vertex_sql,

        {
            "lon": endLon,
            "lat": endLat
        }

    ).fetchone()


    start_id = start_vertex.id
    end_id = end_vertex.id


    print("Sommet départ :", start_id)
    print("Sommet arrivée :", end_id)


    #=================================================
    # Calcul du trajet
    #=================================================

    route_sql = text("""
        SELECT
            rn.id,
            ST_AsGeoJSON(
                ST_Transform(
                    rn.way,
                    4326
                )
            )::json AS geometry
            FROM pgr_dijkstra(
            'SELECT
                id,
                source,
                target,
                cost,
                reverse_cost
            FROM roads_network
            ',
            :start_id,
            :end_id,
            false
        ) AS route
        JOIN roads_network rn
        ON route.edge = rn.id
        WHERE route.edge <> -1;
    """)

    rows = db.execute(
        route_sql,
        {
            "start_id": start_id,
            "end_id": end_id
        }

    ).fetchall()

    print("Nombre de segments :", len(rows))
    #=================================================
    # GeoJSON
    #=================================================
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": row.geometry,
            "properties": {
                "id": row.id
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features

    }