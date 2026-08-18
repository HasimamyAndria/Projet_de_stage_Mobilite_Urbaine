# -*- coding: utf-8 -*-
"""Provenance des données analytics (zones / OD)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.privacy import K_ANONYMITY_MIN

NOTE_OSM = (
    "Zones et proxies issus d'OpenStreetMap (lieux, bâtiments, POI). "
    "Volumes OD estimés par modèle gravitaire population×emplois / distance "
    "(pas une enquête ménage). Agrégats zone→zone uniquement, "
    f"seuil k-anonymité k>={K_ANONYMITY_MIN}."
)

NOTE_DEMO = (
    "Volumes synthétiques (grille démo + modèle gravitaire). "
    "Données agrégées zone→zone, aucune donnée individuelle. "
    f"Seuil k-anonymité k>={K_ANONYMITY_MIN}."
)


def get_data_provenance(db: Session) -> dict:
    """
    Détecte si le peuplement courant est OSM réel ou grille démo.
    """
    row = db.execute(
        text(
            """
            SELECT zone_type, COUNT(*) AS n
            FROM mobility_zones
            GROUP BY zone_type
            ORDER BY n DESC
            LIMIT 1
            """
        )
    ).fetchone()

    zone_type = row.zone_type if row else None
    is_osm = bool(zone_type and str(zone_type).startswith("osm"))

    return {
        "synthetic": not is_osm,
        "zone_type": zone_type,
        "data_source": "osm" if is_osm else "grid_demo",
        "note": NOTE_OSM if is_osm else NOTE_DEMO,
    }
