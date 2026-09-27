# src/hydraulic_model.py
"""Hydraulic model for Dwarka drainage network.
Implements:
1. Rational Method runoff (C * i) for hourly urban runoff estimation.
   NOTE: We use the Rational Method instead of SCS Curve Number because
   SCS CN is designed for event/storm-total rainfall depths, not for
   independent hourly increments.  Applying SCS to each hour independently
   over-attenuates runoff via the initial-abstraction term (Ia = 0.2*S),
   producing zero runoff for moderate hourly intensities that are known to
   cause urban flooding.  The Rational Method (Q = C*i*A) is the standard
   approach for continuous hourly urban runoff estimation where C ≈
   imperviousness_ratio.
2. Manning's equation capacity per edge using pipe geometry from
   dwarka_drainage_graph.json, reduced by a blockage_factor (default 0.5).
   Reference: CPHEEO Manual on Sewerage and Sewage Treatment Systems
   (Ministry of Housing and Urban Affairs, Govt. of India, 2013) recommends
   design capacity reductions of 30-50% for ageing/silted urban drains.
   A 50% blockage factor is a conservative mid-range assumption pending
   actual blockage-survey data.
3. Depth conversion using a contributing_fraction (default 0.15) and a
   ponding area (default 140 m²).  Not all of the upstream catchment's
   excess runoff concentrates at the ponding point within the same hour —
   the rest drains via alternate paths/nodes or takes longer than one hour.
   The formula is:
     depth_cm = (excess_mm/1000 * catchment_sqm * contributing_fraction)
                / ponding_area_sqm * 100
   This keeps the calculation physically meaningful (volume ÷ area = depth)
   while avoiding the unrealistic assumption that the entire catchment's
   excess instantaneously concentrates at a single 140 m² spot.
4. Formula-only estimate bands: LOW_ESTIMATE ≤ 2 cm | CAUTION 2–5 cm | HIGH 5–10 cm |
   SEVERE > 10 cm.
"""

import json, math, os
from typing import Dict, Tuple, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRAPH_PATH = os.path.join(BASE_DIR, "src", "dwarka_drainage_graph.json")
with open(GRAPH_PATH, "r", encoding="utf-8") as f:
    _GRAPH = json.load(f)

_NODES = {n["id"]: n for n in _GRAPH["nodes"]}
_EDGES = {e["id"]: e for e in _GRAPH["edges"]}

# --- Documented defaults (all flagged as "assumed" in outputs) ---
# Ponding area: ~5000 sqm represents a realistic ~100 m stretch of roads,
# intersections, and low-lying areas around a drainage node where floodwater
# would spread during surcharge — not just a single 7 m × 20 m road segment.
_DEFAULT_PONDING_AREA_SQM = 5000.0
_DEFAULT_BLOCKAGE_FACTOR = 0.5
# Contributing fraction: 15% of the upstream catchment's hourly excess runoff
# effectively reaches this specific ponding point within the hour.  The
# remainder drains via alternate paths/nodes or takes longer than one hour.
_DEFAULT_CONTRIBUTING_FRACTION = 0.15


# ---------------------------------------------------------------------------
# 1. Rational Method runoff
# ---------------------------------------------------------------------------
def _rational_runoff_mm(rain_mm: float, imperv: float) -> float:
    """Rational Method: runoff_mm = C * rain_mm, where C = imperviousness_ratio.
    C is bounded to [0, 1]."""
    c = max(0.0, min(1.0, imperv))
    return c * rain_mm


# ---------------------------------------------------------------------------
# 2. Manning's equation capacity (with blockage factor)
# ---------------------------------------------------------------------------
def _manning_capacity_mmhr(edge_id: str) -> Tuple[float, float, float]:
    """Compute effective Manning capacity in mm/hr for a given edge.

    Returns (effective_capacity_mmhr, catchment_sqm, blockage_factor).
    effective_capacity = raw_Manning_Q × blockage_factor

    Blockage factor reference: CPHEEO Manual on Sewerage and Sewage
    Treatment Systems (MoHUA, 2013) — capacity reduction of 30-50% for
    silted/aged urban drains in Indian cities.
    """
    e = _EDGES[edge_id]
    src = _NODES[e["source"]]
    catch = src.get("inflow_catchment_sqm", 1.0) or 1.0

    # Pipe cross-section geometry
    if e.get("width_m") and e.get("height_m"):
        w, h = e["width_m"], e["height_m"]
        area = w * h
        perim = 2 * (w + h)
    elif e.get("diameter_m"):
        d = e["diameter_m"]
        area = math.pi * d ** 2 / 4.0
        perim = math.pi * d
    else:
        area = 0.5 * 0.5
        perim = 2 * (0.5 + 0.5)

    R = area / perim if perim else 0.0
    length = e.get("length_m", 1.0)
    elev_src = src.get("elevation_rim_m", 0)
    elev_tgt = _NODES[e["target"]].get("elevation_rim_m", 0)
    slope = max((elev_src - elev_tgt) / length, 1e-5)
    n = e.get("mannings_n", 0.013)

    q_raw = (1.0 / n) * area * (R ** (2.0 / 3.0)) * (slope ** 0.5)  # m³/s
    bf = e.get("blockage_factor", _DEFAULT_BLOCKAGE_FACTOR)
    q_eff = q_raw * bf
    cap_mmhr = q_eff * 3600 * 1000 / catch
    return cap_mmhr, catch, bf


# ---------------------------------------------------------------------------
# 3. Depth conversion (with contributing fraction)
# ---------------------------------------------------------------------------
def _depth_from_excess_mm(
    excess_mm: float,
    pond_area: float,
    catch_sqm: float,
    contributing_fraction: float = _DEFAULT_CONTRIBUTING_FRACTION,
) -> float:
    """Convert excess runoff (mm over catchment) to water depth (cm) at the
    ponding point.

    depth_cm = (excess_mm/1000 × catch_sqm × contributing_fraction) / pond_area × 100

    contributing_fraction (default 0.15) represents the share of the upstream
    catchment's hourly excess that effectively concentrates at this specific
    ponding point within the hour.  The remainder drains via alternate
    paths/nodes or arrives over a longer time window.
    """
    if excess_mm <= 0:
        return 0.0
    volume_m3 = (excess_mm / 1000.0) * catch_sqm * contributing_fraction
    depth_m = volume_m3 / pond_area
    return depth_m * 100.0  # → cm


# ---------------------------------------------------------------------------
# 4. Main entry point
# ---------------------------------------------------------------------------
def compute_water_depth(row: Dict[str, str]) -> Tuple[float, int, str]:
    """Compute water depth, surcharge flag, and hazard level for one row."""
    rain = float(row.get("rain_mm", 0) or 0)
    imp = float(row.get("imperviousness_ratio", 0) or 0)

    runoff = _rational_runoff_mm(rain, imp)

    rep_edge = next(iter(_EDGES))
    cap, catch_sqm, _ = _manning_capacity_mmhr(rep_edge)

    excess = max(runoff - cap, 0.0)
    depth_cm = _depth_from_excess_mm(excess, _DEFAULT_PONDING_AREA_SQM, catch_sqm)

    # Hazard thresholds and binary surcharge flag
    if depth_cm <= 2:
        level = "LOW_ESTIMATE"
        flag = 0
    elif depth_cm <= 5:
        level = "CAUTION"
        flag = 1
    elif depth_cm <= 10:
        level = "HIGH"
        flag = 1
    else:
        level = "SEVERE"
        flag = 1

    return depth_cm, flag, level


# ---------------------------------------------------------------------------
# 5. Diagnostics helper
# ---------------------------------------------------------------------------
def get_representative_edge_info() -> Dict[str, Any]:
    """Return info about the edge used for capacity calculations."""
    rep_edge = next(iter(_EDGES))
    e = _EDGES[rep_edge]
    geom = ("rectangular" if e.get("width_m") and e.get("height_m")
            else "circular" if e.get("diameter_m") else "unknown")
    return {
        "edge_id": rep_edge,
        "geometry_type": geom,
        "width_m": e.get("width_m"),
        "height_m": e.get("height_m"),
        "diameter_m": e.get("diameter_m"),
        "mannings_n": e.get("mannings_n"),
        "blockage_factor": e.get("blockage_factor", _DEFAULT_BLOCKAGE_FACTOR),
        "blockage_factor_assumed": e.get("blockage_factor_assumed", True),
        "contributing_fraction": _DEFAULT_CONTRIBUTING_FRACTION,
        "contributing_fraction_assumed": True,
        "ponding_area_sqm": _DEFAULT_PONDING_AREA_SQM,
        "ponding_area_assumed": True,
    }
