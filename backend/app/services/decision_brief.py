"""
Dossier décideur — orchestration télétravail + bureaux annexes.

Aucun moteur de simulation supplémentaire : les indicateurs viennent de
`simulate`, `get_telework_impact` et `get_satellite_sites`.
La note est un texte cadré (pas un LLM, pas de volumes inventés).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.privacy import K_ANONYMITY_MIN
from app.services.emploi_habitat import get_satellite_sites, get_telework_impact
from app.services.simulation import TELEWORK_DAY_SHARE, simulate

SECTOR_MULT = {
    "tertiaire": 1.2,
    "tech": 1.4,
    "soin": 0.4,
    "admin": 1.1,
    "industrie": 0.2,
}

PATTERN_LABELS = {
    "full_remote": "full remote (5 j hors site)",
    "hybrid_1_2": "hybride 1–2 jours / semaine",
    "hybrid_3_4": "hybride 3–4 jours / semaine",
}

SCENARIO_LABELS = {
    "reference": "Référence — tout le monde au siège",
    "annexes": "Bureaux annexes seuls",
    "telework": "Télétravail seul",
    "mix": "Mix recommandé (télétravail + annexes)",
}


def _clamp_k(k: int) -> int:
    return max(3, min(5, int(k)))


def _effective_telework_rate(
    rate_max: float, share_present: float, sector: str
) -> float:
    """Taux réellement passé à get_telework_impact / simulate(telework)."""
    eligible = max(0.0, 1.0 - float(share_present))
    rate_max = max(0.0, min(0.8, float(rate_max)))
    mult = SECTOR_MULT.get((sector or "admin").strip().lower(), 1.0)
    sector_adj = rate_max * mult
    if (sector or "").lower() == "tech":
        sector_adj = min(0.8, sector_adj)
    return round(min(0.8, rate_max, eligible, sector_adj), 4)


def _annex_intensity(k: int, share_present: float, costly_share: float) -> float:
    """Intensité [0.05, 1] du simulate(add_satellite_office) existant."""
    raw = (k / 5.0) * (0.35 + 0.65 * share_present * max(costly_share, 0.15))
    return round(max(0.05, min(1.0, raw)), 2)


def _publish_volume(value: float) -> int | None:
    """Ne jamais exposer un volume agrégé sous le seuil k."""
    n = int(round(value))
    if n <= 0:
        return 0
    if n < K_ANONYMITY_MIN:
        return None
    return n


def _delta_num(scenario: float | int | None, ref: float | int | None) -> float | None:
    if scenario is None or ref is None:
        return None
    return round(float(scenario) - float(ref), 2)


def _ind(src: dict) -> dict[str, Any]:
    return {
        "trips": int(src["trips"]),
        "km": float(src["km"]),
        "co2_t": float(src["co2_t"]),
        "avg_time_min": float(src["avg_time_min"]),
        "time_h": float(src.get("time_h") or 0.0),
        "modal_share": dict(src.get("modal_share") or {}),
    }


def _compose_mix(
    tele_scen: dict, sat_scen: dict, baseline: dict, share_present: float
) -> dict[str, Any]:
    """Mix sans double compte : télétravail retire des trajets ; l'annexe
    ne raccourcit que la part encore présente (share_must_be_present)."""
    trips_b = max(int(baseline["trips"]), 1)
    km_b = max(float(baseline["km"]), 1e-9)
    co2_b = max(float(baseline["co2_t"]), 1e-9)
    time_b = max(float(baseline["time_h"]), 1e-9)

    remaining_frac = float(tele_scen["trips"]) / trips_b
    sat_km_reduce = 1.0 - float(sat_scen["km"]) / km_b
    sat_co2_reduce = 1.0 - float(sat_scen["co2_t"]) / co2_b
    sat_time_reduce = 1.0 - float(sat_scen["time_h"]) / time_b
    annex_weight = min(1.0, float(share_present) / max(remaining_frac, 1e-9))

    trips = int(tele_scen["trips"])
    km = round(float(tele_scen["km"]) * (1.0 - sat_km_reduce * annex_weight), 1)
    co2_t = round(float(tele_scen["co2_t"]) * (1.0 - sat_co2_reduce * annex_weight), 2)
    time_h = round(float(tele_scen["time_h"]) * (1.0 - sat_time_reduce * annex_weight), 1)
    avg_time_min = round(time_h * 60.0 / max(trips, 1), 1)
    return {
        "trips": trips,
        "km": km,
        "co2_t": co2_t,
        "avg_time_min": avg_time_min,
        "time_h": time_h,
        "modal_share": dict(tele_scen.get("modal_share") or {}),
        "annex_weight": round(annex_weight, 3),
        "sat_km_reduce": round(sat_km_reduce, 4),
    }


def _arrivals(
    inbound: float,
    *,
    share_present: float,
    costly_share: float,
    tele_remaining_frac: float,
    divert_annexes: bool,
) -> int | None:
    """Proxy d'arrivées au siège (volume OD agrégé vers l'ancre, k ≥ 5)."""
    if inbound <= 0:
        return 0
    remaining = inbound * tele_remaining_frac
    if divert_annexes:
        diverted = inbound * share_present * costly_share
        remaining = max(0.0, remaining - diverted)
    return _publish_volume(remaining)


def _annexes_geojson(candidates: list[dict]) -> dict:
    features: list[dict] = []
    for c in candidates:
        props = {
            key: val
            for key, val in c.items()
            if key != "geometry" and val is not None
        }
        geom = c.get("geometry")
        if geom:
            features.append(
                {"type": "Feature", "geometry": geom, "properties": dict(props)}
            )
        lon, lat = c.get("lon"), c.get("lat")
        if lon is not None and lat is not None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)],
                    },
                    "properties": {**props, "marker": "annexe"},
                }
            )
    return {"type": "FeatureCollection", "features": features}


def _empty_payload(message: str, dossier: dict, extra: dict | None = None) -> dict:
    payload = {
        "ok": False,
        "message": message,
        "dossier": dossier,
        "anchor": None,
        "residential_basins": [],
        "critical_corridors": [],
        "annexes": [],
        "geojson": {"type": "FeatureCollection", "features": []},
        "scenarios": [],
        "recommendation": None,
        "note_decideur": (
            "Impossible de produire une note chiffrée : les flux agrégés vers le "
            "siège sont absents ou sous le seuil de k-anonymité (≥ 5 passagers). "
            "Aucun volume n'a été inventé."
        ),
        "limitations": _limitations(),
        "synthetic": True,
    }
    if extra:
        payload.update(extra)
    return payload


def _limitations() -> list[str]:
    return [
        "Volumes OD synthétiques (modèle gravitaire de démo Antananarivo / OSM), "
        "à recaler sur des données RH et de mobilité réelles avant une décision budgétaire.",
        "Élasticités forfaitaires du module de simulation (reports modaux, raccourcissement km).",
        "Pas d'affectation de trafic sur le graphe routier : le proxy de pression est le "
        "volume entrant évité vers le siège, pas une capacité ni une congestion mesurée.",
        "Indice emploi-habitat intra-zone (pas de 2SFCA, pas d'accessibilité inter-zones).",
        "Aucun trajet individuel, nom, adresse ou GPS n'est lu ni stocké "
        f"(k-anonymité ≥ {K_ANONYMITY_MIN}).",
        "Ce n'est pas une prévision de congestion temps réel ni un calcul d'émissions réglementaire.",
    ]


def _build_note(
    *,
    dossier: dict,
    anchor: dict,
    chosen: dict,
    scenarios: list[dict],
    annexes: list[dict],
    corridors: list[dict],
    hypotheses: list[str],
    parameters: dict,
) -> str:
    ref = next(s for s in scenarios if s["id"] == "reference")
    rec = next(s for s in scenarios if s["id"] == chosen["id"])
    org = dossier.get("organization") or "l'organisation"
    peak = dossier.get("peak_hours") or [7, 8, 9]
    peak_txt = "–".join(str(h) for h in peak[:2]) + " h" if peak else "heures de pointe"
    costly = [c for c in corridors if c.get("costly")]
    bassin_txt = (
        ", ".join(f"{c['origin_name']} ({c['volume']} passagers proxy)" for c in costly[:5])
        if costly
        else "aucun bassin ≥ 6 km au-dessus du seuil k"
    )
    sites = annexes[:3]
    sites_txt = "\n".join(
        f"  {i}. {a['name']} — {a.get('type_label') or a.get('type')} "
        f"(km évités proxy : {a.get('km_saved_proxy')}, "
        f"foncier : {(a.get('constraints') or {}).get('foncier', 'n/d')}, "
        f"TC : {(a.get('constraints') or {}).get('desserte_tc', 'n/d')})"
        for i, a in enumerate(sites, 1)
    ) or "  (aucun site retenu)"

    def _fmt(v, suffix=""):
        if v is None:
            return "sous seuil k"
        if isinstance(v, float):
            return f"{v:,.1f}{suffix}".replace(",", " ")
        return f"{v:,}{suffix}".replace(",", " ")

    co2_evite = None
    if rec["delta"]["co2_t"] is not None:
        co2_evite = -rec["delta"]["co2_t"]
    arr_evite = None
    if rec["delta"]["arrivals_at_hq"] is not None:
        arr_evite = -rec["delta"]["arrivals_at_hq"]

    return (
        f"Note décideur — {org}\n"
        f"Siège / pôle d'emploi : {anchor.get('name')} "
        f"(zone {anchor.get('id')}, {anchor.get('jobs_proxy', 0)} emplois proxy).\n"
        f"Effectif de référence : {dossier.get('headcount')} agents · "
        f"secteur {dossier.get('sector')} · fenêtre d'arrivées {peak_txt}.\n\n"
        f"Constat\n"
        f"Les arrivées domicile → siège saturent des corridors qui alimentent le centre "
        f"et un nœud de convergence. Bassins résidentiels éloignés (≥ 6 km) : {bassin_txt}. "
        f"Corridors critiques (top flux agrégés vers le siège, k ≥ {K_ANONYMITY_MIN}) : "
        f"{len(corridors)} liaisons. Le CO₂ associé est surtout porté par la voiture "
        f"(facteurs déjà utilisés par la plateforme, kg/pkm).\n\n"
        f"Levier retenu\n"
        f"{rec['label']}. {chosen.get('rationale', '').replace(chr(10), ' ')}\n\n"
        f"Chiffres avant / après (ordre de grandeur, journée type démo)\n"
        f"  Trajets : {_fmt(ref['trips'])} → {_fmt(rec['trips'])} "
        f"(Δ {rec['delta']['trips']})\n"
        f"  km parcourus : {_fmt(ref['km'])} → {_fmt(rec['km'])} "
        f"(Δ {rec['delta']['km']})\n"
        f"  Temps moyen : {_fmt(ref['avg_time_min'], ' min')} → "
        f"{_fmt(rec['avg_time_min'], ' min')}\n"
        f"  CO₂ : {_fmt(ref['co2_t'], ' t')} → {_fmt(rec['co2_t'], ' t')} "
        f"(CO₂ évité : {_fmt(co2_evite, ' t')})\n"
        f"  Arrivées au siège (proxy volume entrant) : "
        f"{_fmt(ref['arrivals_at_hq'])} → {_fmt(rec['arrivals_at_hq'])} "
        f"(évitées : {_fmt(arr_evite)})\n\n"
        f"Bureaux annexes proposés (méthode satellites existante, k="
        f"{parameters.get('max_annexes')})\n"
        f"{sites_txt}\n\n"
        f"Hypothèses explicites\n"
        + "".join(f"  • {h}\n" for h in hypotheses)
        + "\n"
        f"Limites — à lire avant tout arbitrage budgétaire\n"
        f"Chiffres de démonstration (OD synthétiques Antananarivo / OSM). "
        f"Ce n'est pas une prévision de congestion temps réel, ni un calcul "
        f"d'émissions réglementaire, ni une étude de trafic. Recaler sur les "
        f"effectifs RH, les métiers réellement télétravaillables et une enquête "
        f"déplacements avant d'engager un budget d'annexes."
    )


def _rationale(
    rec: dict, ref: dict, parameters: dict, n_annexes: int, n_corridors: int
) -> str:
    co2 = rec["delta"]["co2_t"]
    arr = rec["delta"]["arrivals_at_hq"]
    km = rec["delta"]["km"]
    pattern = PATTERN_LABELS.get(parameters["telework_pattern"], parameters["telework_pattern"])
    return (
        f"Parmi les scénarios respectant le taux max de télétravail "
        f"({int(parameters['telework_rate_max']*100)} %), la part devant rester "
        f"présente ({int(parameters['share_must_be_present']*100)} %) et le plafond "
        f"d'annexes ({parameters['max_annexes']}), « {rec['label']} » réduit le plus "
        f"le CO₂ (Δ {co2} t) et les arrivées au siège (Δ {arr}).\n"
        f"Le télétravail ({pattern}, taux appliqué {int(parameters['telework_rate']*100)} %) "
        f"retire des jours sur site pour les métiers éligibles ; il ne s'applique pas "
        f"à l'accueil, la caisse ou les archives physiques.\n"
        f"Les bureaux annexes ({n_annexes} sites) ne suppriment pas le déplacement : "
        f"ils raccourcissent les km des agents qui doivent être présents et habitent "
        f"un bassin coûteux (≥ 6 km).\n"
        f"Le mix ne compte pas deux fois la même personne : un agent en télétravail "
        f"ce jour-là n'est pas affecté à une annexe.\n"
        f"Le proxy de pression porte sur {n_corridors} corridors alimentant le siège "
        f"(volume entrant évité, Δ km {km}) — pas une capacité routière réelle."
    )


def build_decision_brief(db: Session, dossier: dict) -> dict:
    organization = (dossier.get("organization") or "Direction des finances").strip()
    sector = (dossier.get("sector") or "admin").strip().lower()
    if sector not in SECTOR_MULT:
        sector = "admin"
    headcount = max(1, int(dossier.get("headcount") or 800))
    share_present = max(0.0, min(1.0, float(dossier.get("share_must_be_present") or 0.35)))
    rate_max = max(0.0, min(0.8, float(dossier.get("telework_rate_max") or 0.40)))
    pattern = dossier.get("telework_pattern") or "hybrid_1_2"
    if pattern not in TELEWORK_DAY_SHARE:
        pattern = "hybrid_1_2"
    max_annexes = _clamp_k(int(dossier.get("max_annexes") or 3))
    peak_hours = [
        int(h)
        for h in (dossier.get("peak_hours") or [7, 8, 9])
        if isinstance(h, (int, float)) and 0 <= int(h) <= 23
    ] or [7, 8, 9]
    anchor_zone_id = dossier.get("anchor_zone_id")
    if anchor_zone_id is not None:
        try:
            anchor_zone_id = int(anchor_zone_id)
        except (TypeError, ValueError):
            anchor_zone_id = None

    echoed = {
        "anchor_zone_id": anchor_zone_id,
        "organization": organization,
        "sector": sector,
        "headcount": headcount,
        "share_must_be_present": share_present,
        "telework_rate_max": rate_max,
        "telework_pattern": pattern,
        "max_annexes": max_annexes,
        "peak_hours": peak_hours,
    }

    satellites = get_satellite_sites(db, zone_id=anchor_zone_id, k=max_annexes)
    anchor = satellites.get("anchor")
    basins = list(satellites.get("residential_basins") or [])
    candidates = list(satellites.get("candidates") or [])[:max_annexes]

    if not anchor:
        return _empty_payload(
            "Aucune zone d'emploi disponible pour ancrer le siège.",
            echoed,
        )

    inbound = float(sum(int(b.get("volume") or 0) for b in basins))
    costly_vol = float(
        sum(int(b.get("volume") or 0) for b in basins if b.get("costly"))
    )
    if inbound < K_ANONYMITY_MIN:
        return _empty_payload(
            "Aucun flux agrégé vers le siège au-dessus du seuil k-anonymité "
            f"(≥ {K_ANONYMITY_MIN} passagers). Impossible de comparer des scénarios "
            "sans inventer des volumes.",
            echoed,
            extra={"anchor": anchor, "residential_basins": basins},
        )

    costly_share = costly_vol / inbound if inbound else 0.0
    tele_rate = _effective_telework_rate(rate_max, share_present, sector)
    intensity = _annex_intensity(max_annexes, share_present, costly_share)
    day_share = TELEWORK_DAY_SHARE[pattern]
    aid = int(anchor["id"])

    sat_sim = simulate(
        db,
        action="add_satellite_office",
        zone_id=aid,
        intensity=intensity,
    )
    tele_impact = get_telework_impact(
        db,
        rate=tele_rate,
        pattern=pattern,
        combine_satellite=False,
    )

    baseline = _ind(sat_sim["baseline"])
    annex_ind = _ind(sat_sim["scenario"])
    tele_ind = _ind(tele_impact["scenario"])
    mix_ind = _compose_mix(
        tele_impact["scenario"], sat_sim["scenario"], sat_sim["baseline"], share_present
    )

    tele_remaining = tele_ind["trips"] / max(baseline["trips"], 1)

    corridors = [
        {
            "origin_zone_id": b.get("zone_id"),
            "origin_name": b.get("name"),
            "volume": int(b.get("volume") or 0),
            "distance_km": b.get("distance_km"),
            "costly": bool(b.get("costly")),
        }
        for b in basins
        if int(b.get("volume") or 0) >= K_ANONYMITY_MIN
    ]

    annexes = []
    for c in candidates:
        annexes.append(
            {
                "rank": c.get("rank"),
                "zone_id": c.get("zone_id"),
                "name": c.get("name"),
                "type": c.get("type"),
                "type_label": c.get("type_label"),
                "km_saved_proxy": c.get("km_saved_proxy"),
                "impact_score": c.get("impact_score"),
                "criteria": c.get("criteria") or [],
                "constraints": c.get("constraints") or {},
                "lon": c.get("lon"),
                "lat": c.get("lat"),
            }
        )

    def pack(sid: str, ind: dict, arrivals: int | None, extra: dict | None = None) -> dict:
        row = {
            "id": sid,
            "label": SCENARIO_LABELS[sid],
            "trips": ind["trips"],
            "km": ind["km"],
            "co2_t": ind["co2_t"],
            "avg_time_min": ind["avg_time_min"],
            "arrivals_at_hq": arrivals,
            "corridor_pressure_proxy": arrivals,
            "delta": {
                "trips": _delta_num(ind["trips"], baseline["trips"]),
                "km": _delta_num(ind["km"], baseline["km"]),
                "co2_t": _delta_num(ind["co2_t"], baseline["co2_t"]),
                "avg_time_min": _delta_num(ind["avg_time_min"], baseline["avg_time_min"]),
                "arrivals_at_hq": _delta_num(arrivals, _publish_volume(inbound)),
            },
        }
        if extra:
            row.update(extra)
        return row

    ref_arrivals = _publish_volume(inbound)
    scenarios = [
        pack("reference", baseline, ref_arrivals),
        pack(
            "annexes",
            annex_ind,
            _arrivals(
                inbound,
                share_present=share_present,
                costly_share=costly_share,
                tele_remaining_frac=1.0,
                divert_annexes=True,
            ),
        ),
        pack(
            "telework",
            tele_ind,
            _arrivals(
                inbound,
                share_present=share_present,
                costly_share=costly_share,
                tele_remaining_frac=tele_remaining,
                divert_annexes=False,
            ),
        ),
        pack(
            "mix",
            mix_ind,
            _arrivals(
                inbound,
                share_present=share_present,
                costly_share=costly_share,
                tele_remaining_frac=tele_remaining,
                divert_annexes=True,
            ),
            extra={"annex_weight": mix_ind.get("annex_weight")},
        ),
    ]

    policies = [s for s in scenarios if s["id"] != "reference"]

    def rank_key(s: dict) -> tuple:
        arr = s["arrivals_at_hq"] if s["arrivals_at_hq"] is not None else 10**9
        return (float(s["co2_t"]), float(arr), float(s["km"]))

    recommended = min(policies, key=rank_key)

    km_saved_pct_annex = round(
        (1.0 - annex_ind["km"] / max(baseline["km"], 1e-9)) * 100.0, 1
    )
    parameters = {
        "telework_rate": tele_rate,
        "telework_rate_max": rate_max,
        "telework_pattern": pattern,
        "day_share": day_share,
        "share_must_be_present": share_present,
        "eligible_share": round(1.0 - share_present, 3),
        "max_annexes": max_annexes,
        "annex_intensity": intensity,
        "km_saved_pct_annex": km_saved_pct_annex,
        "costly_share": round(costly_share, 3),
        "sector": sector,
        "sector_rates": tele_impact.get("sector_rates") or {},
        "simulate_annex": {
            "action": "add_satellite_office",
            "zone_id": aid,
            "intensity": intensity,
        },
        "telework_api": {
            "rate": tele_rate,
            "pattern": pattern,
        },
    }

    hypotheses = [
        f"Taux de télétravail appliqué : {int(tele_rate*100)} % "
        f"(plafond dossier {int(rate_max*100)} %, part télétravaillable "
        f"{int((1-share_present)*100)} %, secteur {sector}, plafond moteur 80 %).",
        f"Rythme {PATTERN_LABELS[pattern]} : {int(day_share*100)} % des jours hors site "
        f"pour les agents concernés (simulate / get_telework_impact).",
        f"Part d'agents qui doivent rester présents : {int(share_present*100)} % "
        f"— seuls candidats aux bureaux annexes (accueil, caisse, archives physiques, etc.).",
        f"Bureaux annexes : {len(annexes)} sites, intensité simulate "
        f"{intensity} → environ {km_saved_pct_annex} % de km évités (raccourcissement, "
        f"trajets conservés). Méthode : barycentre des bassins ≥ 6 km puis greedy p-médianes.",
        f"Part des volumes vers le siège issus de bassins ≥ 6 km : "
        f"{int(costly_share*100)} % (proxy de réaffectation vers l'annexe la plus proche).",
        "Mix : un agent en télétravail ce jour-là n'est pas compté dans une annexe "
        f"(poids annexe sur les km restants = {mix_ind.get('annex_weight')}).",
        f"Effectif déclaré {headcount} agents : ordre de grandeur organisationnel ; "
        "les volumes OD restent agrégés zone→zone (pas d'effectifs nominatifs).",
        f"Heures de pointe saisies {peak_hours} : fenêtre décisionnelle ; les volumes "
        "démo sont agrégés, ce n'est pas un profil horaire calibré.",
        *(sat_sim.get("assumptions") or []),
        tele_impact.get("note") or "Télétravail : pas de migration résidentielle modélisée.",
    ]

    rationale = _rationale(
        recommended, scenarios[0], parameters, len(annexes), len(corridors)
    )
    recommendation = {
        "scenario_id": recommended["id"],
        "rationale": rationale,
        "hypotheses": hypotheses,
    }
    note = _build_note(
        dossier=echoed,
        anchor=anchor,
        chosen={**recommendation, "id": recommended["id"], "label": recommended["label"]},
        scenarios=scenarios,
        annexes=annexes,
        corridors=corridors,
        hypotheses=hypotheses,
        parameters=parameters,
    )

    return {
        "ok": True,
        "message": None,
        "dossier": echoed,
        "anchor": anchor,
        "residential_basins": basins,
        "critical_corridors": corridors,
        "annexes": annexes,
        "geojson": _annexes_geojson(candidates),
        "scenarios": scenarios,
        "recommendation": recommendation,
        "note_decideur": note,
        "limitations": _limitations(),
        "parameters_used": parameters,
        "method": satellites.get("method"),
        "synthetic": True,
        "privacy": {
            "k_anonymity_min": K_ANONYMITY_MIN,
            "individual_trajectories": False,
        },
    }
