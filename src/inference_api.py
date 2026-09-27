"""Bridge between ML inference pipeline and the HTTP API server.

Pre-computes synthetic demonstration scenarios for the dashboard slider.
Forecast mode runs inference using forecast-model precipitation, but every
street-depth value is an unvalidated formula-surrogate estimate.

All predictions flow from model_inference.run_inference() which uses the
trained RandomForest + physics-based geometry features.
"""

import json, os, math, time
from typing import Dict, List, Any, Optional
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SRC_DIR, "..")
MODELS_DIR = os.path.join(BASE_DIR, "models")
PILOT_GRAPH = os.path.join(SRC_DIR, "dwarka_drainage_graph.json")

# ── SIMULATED DEMO Lead-time rain scenarios ──────────────────────────────
# WARNING: These are SYNTHETIC scenarios for the "Simulated Storm" demo
# toggle ONLY. They are NOT live data and must NEVER be used when mode=live.
# Live mode passes real Open-Meteo precipitation directly to run_inference().
#
# The values below are fixed demonstration inputs. They are not attributed
# to IMD and do not represent an observed or forecast storm.
#
# The source workbook series peaks at 24.4 mm/hr, but model training also
# added formula-labelled synthetic rows from 0–150 mm/hr. That wider input
# range is synthetic augmentation, not observed-data validation.
DEMO_LEAD_TIME_SCENARIOS = {
    0:   {"rain_mm": 65.0, "rain_3h_accumulated": 65.0,
          "radar_reflectivity_dbz": 48.5, "imperviousness_ratio": 0.85,
          "label": "Peak Cloudburst (65 mm/hr)"},
    30:  {"rain_mm": 55.0, "rain_3h_accumulated": 92.5,
          "radar_reflectivity_dbz": 45.0, "imperviousness_ratio": 0.85,
          "label": "Heavy Rain (55 mm/hr)"},
    60:  {"rain_mm": 40.0, "rain_3h_accumulated": 105.0,
          "radar_reflectivity_dbz": 40.0, "imperviousness_ratio": 0.85,
          "label": "Moderate Rain (40 mm/hr)"},
    120: {"rain_mm": 20.0, "rain_3h_accumulated": 125.0,
          "radar_reflectivity_dbz": 30.0, "imperviousness_ratio": 0.85,
          "label": "Trailing Rain (20 mm/hr)"},
    180: {"rain_mm": 8.0, "rain_3h_accumulated": 133.0,
          "radar_reflectivity_dbz": 20.0, "imperviousness_ratio": 0.85,
          "label": "Dissipating (8 mm/hr)"},
}

# Maximum training input, including formula-labelled synthetic augmentation.
TRAINING_MAX_RAIN_MM = 150.0

# Backward-compatible alias used by main.py's simulated-mode code
LEAD_TIME_SCENARIOS = DEMO_LEAD_TIME_SCENARIOS

# ── Edge-to-node mapping for the 6 dashboard summary locations ─────────
# Maps named display nodes to the edges whose MAX depth represents that node.
NODE_EDGE_MAP = {
    "NODE_DWARKA_MOR_METRO": {
        "name": "Dwarka Mor Metro Crossing",
        "lat": 28.6186, "lng": 77.0319, "elevation_m": 211.2,
        "feed_edges": ["EDGE_PWD_TRUNK_2", "EDGE_MASTER_DRAIN_SEC3"],
    },
    "NODE_KAKROLA_UNDERPASS": {
        "name": "Kakrola Mod Underpass",
        "lat": 28.6120, "lng": 77.0250, "elevation_m": 209.5,
        "feed_edges": ["EDGE_KAKROLA_FEEDER", "EDGE_NAJAFGARH_DISCHARGE"],
    },
    "NODE_SEC14_METRO": {
        "name": "Sector 14 Metro Station",
        "lat": 28.6022, "lng": 77.0260, "elevation_m": 212.8,
        "feed_edges": ["EDGE_MASTER_DRAIN_SEC3"],
    },
    "NODE_UTTAM_NAGAR_W": {
        "name": "Uttam Nagar West Metro",
        "lat": 28.6210, "lng": 77.0420, "elevation_m": 218.2,
        "feed_edges": ["EDGE_PWD_TRUNK_1"],
    },
    "NODE_SEC16B_NLU": {
        "name": "Sector 16B NLU Stretch",
        "lat": 28.6034, "lng": 77.0174, "elevation_m": 212.0,
        "feed_edges": ["EDGE_KAKROLA_FEEDER"],
    },
    "NODE_SEC6_RIDGE": {
        "name": "Dwarka Sector 6 Ridge",
        "lat": 28.5910, "lng": 77.0610, "elevation_m": 219.5,
        "feed_edges": [],  # High ground, no contributing drain edges
    },
}


# ── Cache ────────────────────────────────────────────────────────────────
_cache: Dict[str, Any] = {}
_cache_time: float = 0.0
CACHE_TTL_SECONDS = 300  # 5 minutes


def _snap_lead_time(lead_time_mins: int) -> int:
    """Snap to nearest pre-computed DEMO lead-time step."""
    steps = sorted(DEMO_LEAD_TIME_SCENARIOS.keys())
    best = steps[0]
    for s in steps:
        if abs(s - lead_time_mins) < abs(best - lead_time_mins):
            best = s
    return best


def _load_graph_edge_metadata() -> Dict[str, Dict]:
    """Load edge metadata (geometry_estimated, geometry_source, coords) from graph JSON."""
    if not os.path.exists(PILOT_GRAPH):
        return {}
    with open(PILOT_GRAPH, "r", encoding="utf-8") as f:
        g = json.load(f)
    nodes = {n["id"]: n for n in g["nodes"]}
    meta = {}
    for e in g["edges"]:
        src = nodes.get(e["source"], {})
        tgt = nodes.get(e["target"], {})
        meta[e["id"]] = {
            "source_node": e["source"],
            "target_node": e["target"],
            "source_lat": src.get("lat", 0),
            "source_lon": src.get("lon", 0),
            "target_lat": tgt.get("lat", 0),
            "target_lon": tgt.get("lon", 0),
            "width_m": e.get("width_m"),
            "height_m": e.get("height_m"),
            "length_m": e.get("length_m"),
            "geometry_estimated": e.get("geometry_estimated", False),
            "geometry_source": e.get("geometry_source", "osm_tags"),
        }
    return meta


def precompute_all_lead_times(graph_path: str = None) -> Dict[int, pd.DataFrame]:
    """Run inference for every DEMO lead-time step and cache the results.
    
    This is used ONLY for the simulated-storm demo toggle.
    Live mode bypasses this cache entirely and runs inference on-the-fly
    with real Open-Meteo precipitation data.
    
    Returns dict: lead_time_mins -> DataFrame of predictions.
    """
    global _cache, _cache_time

    if graph_path is None:
        graph_path = PILOT_GRAPH

    if not os.path.exists(graph_path):
        print(f"[inference_api] Graph not found: {graph_path}")
        return {}

    model_path = os.path.join(MODELS_DIR, "dwarka_hydraulic_model.pkl")
    if not os.path.exists(model_path):
        print(f"[inference_api] Model not found: {model_path}")
        return {}

    # Import here to avoid circular imports at module load time
    from model_inference import run_inference

    results = {}
    for lt, scenario in DEMO_LEAD_TIME_SCENARIOS.items():
        rain_input = {k: v for k, v in scenario.items() if k != "label"}
        df = run_inference(graph_path, [rain_input], MODELS_DIR)
        results[lt] = df

    _cache = results
    _cache_time = time.time()
    print(f"[inference_api] Pre-computed {len(results)} DEMO scenarios, "
          f"{len(results.get(0, []))} edge predictions each.")
    return results


def _ensure_cache():
    """Lazily compute cache if empty or stale."""
    global _cache, _cache_time
    if not _cache or (time.time() - _cache_time) > CACHE_TTL_SECONDS:
        precompute_all_lead_times()


def get_edge_predictions(lead_time_mins: int = 60, live_rain_scenario: Dict = None) -> List[Dict]:
    """Get per-edge predictions for a given lead time.
    
    Parameters
    ----------
    lead_time_mins : int
        Lead time in minutes (used to snap to a demo scenario if live_rain_scenario is None).
    live_rain_scenario : dict or None
        If provided, runs inference on-the-fly with these real precipitation values
        instead of using the cached DEMO scenarios. Must contain keys:
        rain_mm, rain_3h_accumulated, radar_reflectivity_dbz, imperviousness_ratio.
    
    Returns list of dicts with: edge_id, rain_mm, predicted_depth_cm,
    hazard_level, extrapolation_warning, geometry_estimated, geometry_source,
    source_lat, source_lon, target_lat, target_lon, rain_intensity_exceeds_training.
    """
    if live_rain_scenario is not None:
        # LIVE MODE: run inference on-the-fly with real precipitation data
        from model_inference import run_inference
        if not os.path.exists(PILOT_GRAPH) or not os.path.exists(os.path.join(MODELS_DIR, "dwarka_hydraulic_model.pkl")):
            return []
        rain_input = {k: v for k, v in live_rain_scenario.items() if k != "label"}
        df = run_inference(PILOT_GRAPH, [rain_input], MODELS_DIR)
        rain_exceeds_training = live_rain_scenario.get("rain_mm", 0) > TRAINING_MAX_RAIN_MM
    else:
        # DEMO MODE: use cached pre-computed scenarios
        _ensure_cache()
        lt = _snap_lead_time(lead_time_mins)
        df = _cache.get(lt)
        scenario = DEMO_LEAD_TIME_SCENARIOS.get(lt, {})
        rain_exceeds_training = scenario.get("rain_mm", 0) > TRAINING_MAX_RAIN_MM

    if df is None or df.empty:
        return []

    edge_meta = _load_graph_edge_metadata()
    
    records = []
    for _, row in df.iterrows():
        eid = row["edge_id"]
        meta = edge_meta.get(eid, {})
        records.append({
            "edge_id": eid,
            "rain_mm": row["rain_mm"],
            "predicted_depth_cm": row["predicted_depth_cm"],
            "hazard_level": row["hazard_level"],
            "extrapolation_warning": bool(row["extrapolation_warning"]),
            "rain_intensity_exceeds_training": rain_exceeds_training,
            "geometry_estimated": meta.get("geometry_estimated", False),
            "geometry_source": meta.get("geometry_source", "unknown"),
            "source_lat": meta.get("source_lat", 0),
            "source_lon": meta.get("source_lon", 0),
            "target_lat": meta.get("target_lat", 0),
            "target_lon": meta.get("target_lon", 0),
            "width_m": meta.get("width_m"),
            "height_m": meta.get("height_m"),
            "length_m": meta.get("length_m"),
        })
    return records


def get_node_summary(lead_time_mins: int = 60, live_rain_scenario: Dict = None) -> List[Dict]:
    """Aggregate per-edge predictions to the 6 named dashboard nodes.
    
    Each node's depth = max depth across its feed_edges.
    
    Parameters
    ----------
    lead_time_mins : int
        Lead time in minutes.
    live_rain_scenario : dict or None
        If provided, threaded directly to get_edge_predictions() so live
        mode runs inference with real Open-Meteo data instead of cached
        DEMO scenarios.
    """
    # Explicitly thread live_rain_scenario to get_edge_predictions
    edge_preds = get_edge_predictions(lead_time_mins, live_rain_scenario)
    edge_lookup = {ep["edge_id"]: ep for ep in edge_preds}

    nodes = []
    for node_id, info in NODE_EDGE_MAP.items():
        max_depth = None
        feed_details = []
        any_extrapolation = False
        any_estimated = False
        any_rain_exceeds = False

        for eid in info["feed_edges"]:
            ep = edge_lookup.get(eid)
            if ep:
                if max_depth is None or ep["predicted_depth_cm"] > max_depth:
                    max_depth = ep["predicted_depth_cm"]
                any_extrapolation = any_extrapolation or ep["extrapolation_warning"]
                any_estimated = any_estimated or ep["geometry_estimated"]
                any_rain_exceeds = any_rain_exceeds or ep.get("rain_intensity_exceeds_training", False)
                feed_details.append({
                    "edge_id": eid,
                    "depth_cm": ep["predicted_depth_cm"],
                    "hazard_level": ep["hazard_level"],
                    "extrapolation_warning": ep["extrapolation_warning"],
                    "geometry_estimated": ep["geometry_estimated"],
                    "rain_intensity_exceeds_training": ep.get("rain_intensity_exceeds_training", False),
                })

        # These are estimate bands, not road-safety statuses. No contributing
        # graph edge means no model coverage, not a zero-depth reading.
        if max_depth is None:
            hazard = "NO_MODEL_COVERAGE"
        elif max_depth > 50:
            hazard = "CRITICAL"
        elif max_depth > 30:
            hazard = "SEVERE"
        elif max_depth > 15:
            hazard = "MODERATE"
        elif max_depth > 5:
            hazard = "CAUTION"
        else:
            hazard = "LOW_ESTIMATE"

        nodes.append({
            "id": node_id,
            "name": info["name"],
            "lat": info["lat"],
            "lng": info["lng"],
            "elevation_m": info["elevation_m"],
            "water_depth_cm": round(max_depth, 1) if max_depth is not None else None,
            "hazard_level": hazard,
            "is_surcharged": max_depth > 15 if max_depth is not None else None,
            "extrapolation_warning": any_extrapolation,
            "rain_intensity_exceeds_training": any_rain_exceeds,
            "geometry_estimated": any_estimated,
            "feed_edges": feed_details,
        })
    return nodes


def get_system_status(lead_time_mins: int = 60, live_rain_scenario: Dict = None) -> Dict:
    """System-wide summary for the top banner."""
    edge_preds = get_edge_predictions(lead_time_mins, live_rain_scenario)
    if not edge_preds:
        return {
            "max_depth_cm": None,
            "edges_low_estimate": 0, "edges_caution": 0,
            "edges_moderate": 0, "edges_severe": 0, "edges_critical": 0,
            "total_edges": 0,
            "scenario_label": "No data",
        }

    depths = [ep["predicted_depth_cm"] for ep in edge_preds]

    if live_rain_scenario:
        rain_mm = live_rain_scenario.get("rain_mm", 0)
        rain_3h_accumulated_mm = live_rain_scenario.get("rain_3h_accumulated", 0)
        radar_dbz = live_rain_scenario.get("radar_reflectivity_dbz", 0)
        label = f"Forecast input ({rain_mm} mm/hr)"
    else:
        lt = _snap_lead_time(lead_time_mins)
        scenario = DEMO_LEAD_TIME_SCENARIOS.get(lt, {})
        rain_mm = scenario.get("rain_mm", 0)
        rain_3h_accumulated_mm = scenario.get("rain_3h_accumulated", 0)
        radar_dbz = scenario.get("radar_reflectivity_dbz", 0)
        label = scenario.get("label", "Unknown")

    return {
        "max_depth_cm": round(max(depths), 1),
        "mean_depth_cm": round(sum(depths) / len(depths), 2),
        "rain_mm": rain_mm,
        "radar_dbz": radar_dbz,
        "edges_low_estimate": sum(1 for d in depths if d <= 2),
        "edges_caution": sum(1 for d in depths if 2 < d <= 5),
        "edges_moderate": sum(1 for d in depths if 5 < d <= 15),
        "edges_severe": sum(1 for d in depths if 15 < d <= 50),
        "edges_critical": sum(1 for d in depths if d > 50),
        "total_edges": len(depths),
        "scenario_label": label,
        "rain_rate_mm_hr": rain_mm,
        "rain_3h_accumulated_mm": rain_3h_accumulated_mm,
        "lead_time_mins": lead_time_mins,
        "rain_intensity_exceeds_training": rain_mm > TRAINING_MAX_RAIN_MM,
    }


def get_lead_time_options() -> List[Dict]:
    """Return available DEMO lead-time steps with their scenario labels."""
    return [
        {"lead_time_mins": lt, "label": s["label"], "rain_rate_mm_hr": s["rain_mm"],
         "rain_3h_accumulated_mm": s["rain_3h_accumulated"]}
        for lt, s in sorted(DEMO_LEAD_TIME_SCENARIOS.items())
    ]
