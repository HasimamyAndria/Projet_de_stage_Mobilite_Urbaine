"""Agrégations de la cohorte simulée sim-cohort.

Les effectifs viennent de PostgreSQL. La période par défaut est le
calendrier inclusif entre la première et la dernière date stockée.
Ce n'est pas la répétition mensuelle du journal diary-week.

Les journées sans déplacement valent :
personnes SIMULATED du jeu × dates du calendrier
− journées-personnes qui ont au moins une étape.
Les filtres de mode, de motif et de lieu ne redéfinissent pas une journée
vide : une journée sans bus peut quand même contenir un trajet.

Distances : orthodromie × 1,35 déjà stockée dans trips.distance_km.
Ce n'est pas un itinéraire pgRouting. Les durées stockées sont simulées.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.engine import Engine

from app.database import engine as default_engine
from app.repositories import cohort_store as store

DATASET_ID = store.DATASET_ID
SOURCE = store.SOURCE
DISTANCE_METHOD = "orthodromie_km_x_1_35"
DISTANCE_UNIT = "km"
DURATION_UNIT = "min"
MAX_TRIP_PAGE = 100
DEFAULT_TRIP_PAGE = 50
MAX_FLOW_PAGE = 500
DEFAULT_FLOW_PAGE = 100
CAVEAT = (
    "Jeu simulé (source SIMULATED), pas une enquête observée et pas une "
    "prévision de circulation. Les distances sont le proxy déjà stocké "
    "(orthodromie × 1,35), pas un itinéraire pgRouting. Les durées sont "
    "simulées, pas des temps de parcours observés."
)
HORIZON_NOTE = (
    "La durée de génération n'est pas une colonne de datasets. "
    "La période par défaut est le calendrier inclusif entre la première "
    "et la dernière date de trajet réellement stockée."
)
EMPTY_DAY_RULE = (
    "Personnes SIMULATED du jeu × dates inclusives de la période "
    "− nombre de couples (personne, date) ayant au moins un trajet. "
    "Le mode, le motif et les lieux filtrés ne servent pas à ce décompte."
)


class CohortNotFound(LookupError):
    """Le jeu sim-cohort n'est pas dans datasets."""


class CohortNotSimulated(ValueError):
    """La ligne existe mais sa source n'est pas SIMULATED."""


class CohortValidationError(ValueError):
    """Paramètre refusé."""


@dataclass(frozen=True)
class ResolvedPeriod:
    date_from: date | None
    date_to: date | None
    calendar_days: int | None
    period_source: str


def _engine(db: Engine | None) -> Engine:
    return default_engine if db is None else db


def _num(value: Decimal | int | float) -> float:
    quantized = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _average(total: Decimal, count: int) -> float | None:
    if count <= 0:
        return None
    return _num(Decimal(total) / Decimal(count))


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def assert_simulated(row: dict | None) -> dict:
    if row is None:
        raise CohortNotFound(
            "Jeu sim-cohort absent. Exécuter scripts/seed_simulated_cohort.py."
        )
    if row.get("source") != SOURCE:
        raise CohortNotSimulated(
            "Le jeu sim-cohort n'est pas marqué SIMULATED. Aucun résultat n'est renvoyé."
        )
    return row


def resolve_period(
    requested_from: date | None,
    requested_to: date | None,
    stored_first: date | None,
    stored_last: date | None,
) -> ResolvedPeriod:
    if requested_from is not None and requested_to is not None:
        if requested_from > requested_to:
            raise CohortValidationError("date_from est postérieure à date_to.")
        days = (requested_to - requested_from).days + 1
        return ResolvedPeriod(requested_from, requested_to, days, "request")
    if requested_from is None and requested_to is None:
        if stored_first is None or stored_last is None:
            return ResolvedPeriod(None, None, None, "unavailable")
        days = (stored_last - stored_first).days + 1
        return ResolvedPeriod(stored_first, stored_last, days, "stored_trip_dates")
    if stored_first is None or stored_last is None:
        raise CohortValidationError(
            "Une seule borne est fournie et le jeu ne contient aucun trajet pour compléter la période."
        )
    start = requested_from if requested_from is not None else stored_first
    end = requested_to if requested_to is not None else stored_last
    if start > end:
        return ResolvedPeriod(start, end, 0, "empty_window")
    days = (end - start).days + 1
    return ResolvedPeriod(start, end, days, "request")


def _require(connection) -> dict:
    return assert_simulated(store.fetch_dataset(connection))


def _check_code(connection, kind: str, code: str | None) -> None:
    if code is None:
        return
    if kind == "mode":
        found = store.mode_exists(connection, code)
        label = "mode"
    else:
        found = store.purpose_exists(connection, code)
        label = "motif"
    if not found:
        raise CohortValidationError(f"{label} inconnu : {code}")


def _check_place(connection, place_id: str | None, role: str) -> None:
    if place_id is None:
        return
    if not store.place_exists(connection, place_id):
        raise CohortValidationError(f"Lieu {role} inconnu : {place_id}")


def _filters_echo(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    mode: str | None = None,
    purpose: str | None = None,
    origin_id: str | None = None,
    destination_id: str | None = None,
    person_id: str | None = None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "mode": mode,
        "purpose": purpose,
        "origin_id": origin_id,
        "destination_id": destination_id,
        "person_id": person_id,
    }


def _check_dates(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise CohortValidationError("date_from est postérieure à date_to.")


def _page(limit: int, offset: int, maximum: int) -> tuple[int, int]:
    if limit < 1 or limit > maximum:
        raise CohortValidationError(f"limit doit être compris entre 1 et {maximum}.")
    if offset < 0:
        raise CohortValidationError("offset doit être supérieur ou égal à 0.")
    return limit, offset


def _share_rows(rows: list[dict], code_key: str, labels: dict[str, str]) -> list[dict]:
    ranked = sorted(rows, key=lambda item: (-item["trip_count"], item[code_key]))
    payload = []
    for item in ranked:
        code = item[code_key]
        payload.append(
            {
                code_key: code,
                "label": labels.get(code, code),
                "trip_count": item["trip_count"],
                "distance_km": _num(item["distance_km"]),
                "duration_min": _num(item["duration_min"]),
            }
        )
    return payload


def get_meta(db: Engine | None = None) -> dict:
    with _engine(db).connect() as connection:
        dataset = _require(connection)
        first, last, trips = store.trip_bounds(connection)
        persons = store.count_persons(connection)
    anchor = dataset["anchor_monday"]
    return {
        "dataset_id": dataset["id"],
        "source": dataset["source"],
        "simulated": True,
        "data_status": "simulated",
        "seed": None if dataset["seed"] is None else int(dataset["seed"]),
        "anchor_monday": anchor,
        "first_trip_date": first,
        "last_trip_date": last,
        "person_count": persons,
        "trip_count": trips,
        "label": dataset["label"],
        "horizon_days": None,
        "horizon_note": HORIZON_NOTE,
        "distance_method": DISTANCE_METHOD,
        "caveat": CAVEAT,
    }


def get_overview(
    date_from: date | None = None,
    date_to: date | None = None,
    mode: str | None = None,
    purpose: str | None = None,
    db: Engine | None = None,
) -> dict:
    mode_code = _blank(mode)
    purpose_code = _blank(purpose)
    with _engine(db).connect() as connection:
        _require(connection)
        _check_code(connection, "mode", mode_code)
        _check_code(connection, "purpose", purpose_code)
        stored_first, stored_last, _stored_count = store.trip_bounds(connection)
        period = resolve_period(date_from, date_to, stored_first, stored_last)
        persons = store.count_persons(connection)
        attribute_filters = {
            "mode_code": mode_code,
            "purpose_code": purpose_code,
        }
        if period.calendar_days == 0:
            aggregated = {
                "total": {"trip_count": 0, "distance_km": Decimal("0"), "duration_min": Decimal("0")},
                "by_mode": [],
                "by_purpose": [],
                "by_date": [],
            }
            active = 0
        elif period.calendar_days is None:
            aggregated = {
                "total": {"trip_count": 0, "distance_km": Decimal("0"), "duration_min": Decimal("0")},
                "by_mode": [],
                "by_purpose": [],
                "by_date": [],
            }
            active = None
        else:
            aggregated = store.aggregate_trips(
                connection,
                {
                    "date_from": period.date_from,
                    "date_to": period.date_to,
                    **attribute_filters,
                },
            )
            active = store.active_person_days(connection, period.date_from, period.date_to)
        mode_labels = store.label_map(connection, "modes")
        purpose_labels = store.label_map(connection, "purposes")
    total = aggregated["total"]
    trip_count = int(total["trip_count"])
    if active is None or period.calendar_days is None:
        empty = None
    else:
        empty = persons * period.calendar_days - active
    dates = sorted(aggregated["by_date"], key=lambda item: item["trip_date"])
    return {
        "dataset_id": DATASET_ID,
        "source": SOURCE,
        "simulated": True,
        "data_status": "simulated",
        "distance_unit": DISTANCE_UNIT,
        "duration_unit": DURATION_UNIT,
        "distance_method": DISTANCE_METHOD,
        "calendar_rule": "stored_dates",
        "caveat": CAVEAT,
        "filters": _filters_echo(date_from=date_from, date_to=date_to, mode=mode_code, purpose=purpose_code),
        "period": {
            "date_from": period.date_from,
            "date_to": period.date_to,
            "calendar_days": period.calendar_days,
            "period_source": period.period_source,
        },
        "person_count": persons,
        "trip_count": trip_count,
        "distance_km": _num(total["distance_km"]),
        "duration_min": _num(total["duration_min"]),
        "average_distance_km": _average(total["distance_km"], trip_count),
        "average_duration_min": _average(total["duration_min"], trip_count),
        "by_mode": _share_rows(aggregated["by_mode"], "mode_code", mode_labels),
        "by_purpose": _share_rows(aggregated["by_purpose"], "purpose_code", purpose_labels),
        "by_date": [
            {
                "trip_date": item["trip_date"],
                "trip_count": item["trip_count"],
                "distance_km": _num(item["distance_km"]),
                "duration_min": _num(item["duration_min"]),
            }
            for item in dates
        ],
        "active_person_days": active,
        "empty_person_days": empty,
        "empty_person_days_rule": EMPTY_DAY_RULE,
    }


def get_flows(
    date_from: date | None = None,
    date_to: date | None = None,
    mode: str | None = None,
    purpose: str | None = None,
    origin_id: str | None = None,
    destination_id: str | None = None,
    limit: int = DEFAULT_FLOW_PAGE,
    offset: int = 0,
    db: Engine | None = None,
) -> dict:
    mode_code = _blank(mode)
    purpose_code = _blank(purpose)
    origin = _blank(origin_id)
    destination = _blank(destination_id)
    _check_dates(date_from, date_to)
    limit, offset = _page(limit, offset, MAX_FLOW_PAGE)
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "mode_code": mode_code,
        "purpose_code": purpose_code,
        "origin_place_id": origin,
        "destination_place_id": destination,
    }
    with _engine(db).connect() as connection:
        _require(connection)
        _check_code(connection, "mode", mode_code)
        _check_code(connection, "purpose", purpose_code)
        _check_place(connection, origin, "d'origine")
        _check_place(connection, destination, "de destination")
        pair_count = store.count_flows(connection, filters)
        rows = store.list_flows(connection, filters, limit, offset)
    flows = [
        {
            "origin_place_id": row["origin_place_id"],
            "origin_name": row["origin_name"],
            "origin_lon": float(row["origin_lon"]),
            "origin_lat": float(row["origin_lat"]),
            "destination_place_id": row["destination_place_id"],
            "destination_name": row["destination_name"],
            "destination_lon": float(row["destination_lon"]),
            "destination_lat": float(row["destination_lat"]),
            "trip_count": int(row["trip_count"]),
            "distance_km": _num(row["distance_km"]),
            "duration_min": _num(row["duration_min"]),
        }
        for row in rows
    ]
    return {
        "dataset_id": DATASET_ID,
        "source": SOURCE,
        "simulated": True,
        "data_status": "simulated",
        "distance_unit": DISTANCE_UNIT,
        "duration_unit": DURATION_UNIT,
        "distance_method": DISTANCE_METHOD,
        "caveat": CAVEAT + " Ces flux ne viennent pas de mobility_flows ni de sim_trips.",
        "filters": _filters_echo(
            date_from=date_from,
            date_to=date_to,
            mode=mode_code,
            purpose=purpose_code,
            origin_id=origin,
            destination_id=destination,
        ),
        "pair_count": pair_count,
        "limit": limit,
        "offset": offset,
        "returned": len(flows),
        "flows": flows,
    }


def get_trips(
    date_from: date | None = None,
    date_to: date | None = None,
    mode: str | None = None,
    purpose: str | None = None,
    origin_id: str | None = None,
    destination_id: str | None = None,
    person_id: str | None = None,
    limit: int = DEFAULT_TRIP_PAGE,
    offset: int = 0,
    db: Engine | None = None,
) -> dict:
    mode_code = _blank(mode)
    purpose_code = _blank(purpose)
    origin = _blank(origin_id)
    destination = _blank(destination_id)
    person = _blank(person_id)
    _check_dates(date_from, date_to)
    limit, offset = _page(limit, offset, MAX_TRIP_PAGE)
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "mode_code": mode_code,
        "purpose_code": purpose_code,
        "origin_place_id": origin,
        "destination_place_id": destination,
        "person_id": person,
    }
    with _engine(db).connect() as connection:
        _require(connection)
        _check_code(connection, "mode", mode_code)
        _check_code(connection, "purpose", purpose_code)
        _check_place(connection, origin, "d'origine")
        _check_place(connection, destination, "de destination")
        if person is not None and not store.person_in_cohort(connection, person):
            raise CohortValidationError(
                "Personne absente de sim-cohort. Le journal diary-week n'est pas lu ici."
            )
        total = store.count_filtered_trips(connection, filters)
        rows = store.list_trips(connection, filters, limit, offset)
    trips = [
        {
            "trip_id": row["trip_id"],
            "person_id": row["person_id"],
            "trip_date": row["trip_date"],
            "depart_time": row["depart_time"],
            "arrive_time": row["arrive_time"],
            "origin_place_id": row["origin_place_id"],
            "origin_name": row["origin_name"],
            "destination_place_id": row["destination_place_id"],
            "destination_name": row["destination_name"],
            "purpose_code": row["purpose_code"],
            "purpose_label": row["purpose_label"],
            "mode_code": row["mode_code"],
            "mode_label": row["mode_label"],
            "distance_km": _num(row["distance_km"]),
            "duration_min": _num(row["duration_min"]),
            "source": row["source"],
        }
        for row in rows
    ]
    return {
        "dataset_id": DATASET_ID,
        "source": SOURCE,
        "simulated": True,
        "data_status": "simulated",
        "distance_unit": DISTANCE_UNIT,
        "duration_unit": DURATION_UNIT,
        "distance_method": DISTANCE_METHOD,
        "caveat": CAVEAT,
        "exposure": "Pseudonyme, lieux et étape. Pas de nom affichable ni de texte libre.",
        "filters": _filters_echo(
            date_from=date_from,
            date_to=date_to,
            mode=mode_code,
            purpose=purpose_code,
            origin_id=origin,
            destination_id=destination,
            person_id=person,
        ),
        "limit": limit,
        "offset": offset,
        "total": total,
        "returned": len(trips),
        "trips": trips,
    }
