"""Vercel/local adapter for Open-Meteo rainfall and Dwarka depth estimates.

The large RandomForest pickle stays outside this function bundle. If
SIH_RF_INFERENCE_URL is configured, depth inference is delegated to the
Hugging Face service; otherwise the documented local formula is used.
"""

import math
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fetch_live_radar import fetch_live_radar_nowcast
from hydraulic_model import estimate_edge_depths, get_drainage_graph


TRAINING_MAX_RAIN_MM = 150.0
PONDING_AREA_SQM = 5000.0
CONTRIBUTING_FRACTION = 0.15
IMPERVIOUSNESS_RATIO = 0.85
LIVE_CACHE_SECONDS = 300
STALE_CACHE_SECONDS = 900
DISK_CACHE_PATH = os.path.join(tempfile.gettempdir(), "dwarka_live_radar.json")

_forecast_cache = None
_forecast_cache_time = 0.0
_graph = get_drainage_graph()
_graph_nodes = {node["id"]: node for node in _graph.get("nodes", [])}
_graph_edges = {edge["id"]: edge for edge in _graph.get("edges", [])}

DEMO_SCENARIOS = {
    0: {"rain_mm": 65.0, "rain_3h_mm": 65.0, "proxy_dbz": 48.5, "label": "Peak Cloudburst (65 mm/hr)"},
    30: {"rain_mm": 55.0, "rain_3h_mm": 92.5, "proxy_dbz": 45.0, "label": "Heavy Rain (55 mm/hr)"},
    60: {"rain_mm": 40.0, "rain_3h_mm": 105.0, "proxy_dbz": 40.0, "label": "Moderate Rain (40 mm/hr)"},
    120: {"rain_mm": 20.0, "rain_3h_mm": 125.0, "proxy_dbz": 30.0, "label": "Trailing Rain (20 mm/hr)"},
    180: {"rain_mm": 8.0, "rain_3h_mm": 133.0, "proxy_dbz": 20.0, "label": "Dissipating (8 mm/hr)"},
}

NODE_EDGE_MAP = {
    "NODE_DWARKA_MOR_METRO": {
        "name": "Dwarka Mor Metro Crossing", "lat": 28.6186, "lng": 77.0319,
        "elevation_m": 211.2, "feed_edges": ["EDGE_PWD_TRUNK_2", "EDGE_MASTER_DRAIN_SEC3"],
    },
    "NODE_KAKROLA_UNDERPASS": {
        "name": "Kakrola Mod Underpass", "lat": 28.6120, "lng": 77.0250,
        "elevation_m": 209.5, "feed_edges": ["EDGE_KAKROLA_FEEDER", "EDGE_NAJAFGARH_DISCHARGE"],
    },
    "NODE_SEC14_METRO": {
        "name": "Sector 14 Metro Station", "lat": 28.6022, "lng": 77.0260,
        "elevation_m": 212.8, "feed_edges": ["EDGE_MASTER_DRAIN_SEC3"],
    },
    "NODE_UTTAM_NAGAR_W": {
        "name": "Uttam Nagar West Metro", "lat": 28.6210, "lng": 77.0420,
        "elevation_m": 218.2, "feed_edges": ["EDGE_PWD_TRUNK_1"],
    },
    "NODE_SEC16B_NLU": {
        "name": "Sector 16B NLU Stretch", "lat": 28.6034, "lng": 77.0174,
        "elevation_m": 212.0, "feed_edges": ["EDGE_KAKROLA_FEEDER"],
    },
    "NODE_SEC6_RIDGE": {
        "name": "Dwarka Sector 6 Ridge", "lat": 28.5910, "lng": 77.0610,
        "elevation_m": 219.5, "feed_edges": [],
    },
}


def _depth_band(depth_cm):
    if depth_cm >= 50:
        return "CRITICAL"
    if depth_cm >= 30:
        return "SEVERE"
    if depth_cm >= 15:
        return "MODERATE"
    if depth_cm >= 5:
        return "CAUTION"
    return "LOW_ESTIMATE"


def _valid_forecast(payload):
    values = payload.get("nowcast_15min_interval_mm") if isinstance(payload, dict) else None
    timestamps = payload.get("timestamps_iso") if isinstance(payload, dict) else None
    if not isinstance(values, list) or len(values) < 24:
        return False
    if not isinstance(timestamps, list) or len(timestamps) < 24:
        return False
    try:
        return all(math.isfinite(float(value)) and float(value) >= 0 for value in values[:24])
    except (TypeError, ValueError):
        return False


def _read_recent_disk_cache():
    """Load the fetcher's short-lived /tmp cache after a warm-instance restart."""
    try:
        age = time.time() - os.path.getmtime(DISK_CACHE_PATH)
        if age < 0 or age > STALE_CACHE_SECONDS:
            return None, None
        with open(DISK_CACHE_PATH, "r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == 3
            and payload.get("provider") == "Open-Meteo Forecast API"
            and payload.get("data_kind") == "forecast_model"
            and _valid_forecast(payload)
        ):
            return payload, age
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return None, None


def _get_live_forecast(force_refresh=False):
    global _forecast_cache, _forecast_cache_time
    age = time.time() - _forecast_cache_time
    if _forecast_cache and age < LIVE_CACHE_SECONDS and not force_refresh:
        return _forecast_cache, True

    disk_cache, disk_cache_age = _read_recent_disk_cache()
    if disk_cache and disk_cache_age < LIVE_CACHE_SECONDS and not force_refresh:
        _forecast_cache = disk_cache
        _forecast_cache_time = time.time() - disk_cache_age
        return disk_cache, True

    try:
        forecast = fetch_live_radar_nowcast(timeout_sec=6.0)
        if not _valid_forecast(forecast):
            raise ValueError("Open-Meteo forecast response did not contain 24 valid intervals.")
        _forecast_cache = forecast
        _forecast_cache_time = time.time()
        return forecast, False
    except Exception:
        age = time.time() - _forecast_cache_time
        if _forecast_cache and age <= STALE_CACHE_SECONDS:
            return _forecast_cache, True
        if disk_cache and disk_cache_age <= STALE_CACHE_SECONDS:
            _forecast_cache = disk_cache
            _forecast_cache_time = time.time() - disk_cache_age
            return disk_cache, True
        raise


def _request_random_forest(rain_mm, rain_3h_mm, proxy_dbz):
    """Call the optional Hugging Face model service; return None on failure."""
    endpoint = os.environ.get("SIH_RF_INFERENCE_URL", "").strip()
    if not endpoint:
        return None, "not_configured"

    timeout = 7.0
    try:
        timeout = max(1.0, min(20.0, float(os.environ.get("SIH_RF_INFERENCE_TIMEOUT_SECONDS", "7"))))
    except (TypeError, ValueError):
        pass

    body = json.dumps({
        "rain_mm": max(0.0, float(rain_mm)),
        "rain_3h_accumulated": max(0.0, float(rain_3h_mm)),
        "radar_reflectivity_dbz": max(0.0, float(proxy_dbz)),
        "imperviousness_ratio": IMPERVIOUSNESS_RATIO,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = os.environ.get("SIH_RF_INFERENCE_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(1_000_001).decode("utf-8"))
        predictions = payload.get("predictions") if isinstance(payload, dict) else None
        if not isinstance(payload, dict) or payload.get("status") != "ok" or not isinstance(predictions, list):
            raise ValueError("unexpected response shape")

        parsed = {}
        for prediction in predictions:
            if not isinstance(prediction, dict):
                raise ValueError("invalid prediction row")
            edge_id = prediction.get("edge_id")
            depth = float(prediction.get("predicted_depth_cm"))
            if edge_id not in _graph_edges or not math.isfinite(depth) or depth < 0:
                raise ValueError("invalid edge prediction")
            parsed[edge_id] = prediction
        if set(parsed) != set(_graph_edges):
            raise ValueError("model response did not cover the configured pilot graph")
        return parsed, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[WARN] Hugging Face RandomForest inference unavailable ({type(exc).__name__}).")
        return None, "service_unavailable"


def _build_edges(rain_mm, random_forest_predictions=None):
    estimates = estimate_edge_depths(rain_mm, IMPERVIOUSNESS_RATIO)
    output = []
    for estimate in estimates:
        edge = _graph_edges.get(estimate["edge_id"], {})
        source = _graph_nodes.get(edge.get("source"), {})
        target = _graph_nodes.get(edge.get("target"), {})
        model_prediction = (random_forest_predictions or {}).get(estimate["edge_id"])
        if model_prediction:
            estimate.update({
                "predicted_depth_cm": model_prediction["predicted_depth_cm"],
                "hazard_level": model_prediction.get("hazard_level", _depth_band(model_prediction["predicted_depth_cm"])),
                "extrapolation_warning": bool(model_prediction.get("extrapolation_warning", False)),
                "extrapolation_features": model_prediction.get("extrapolation_features", []),
                "formula_estimate": False,
                "prediction_backend": "random_forest_huggingface",
            })
        estimate.update({
            "forecast_available": True,
            "rain_intensity_exceeds_training": rain_mm > TRAINING_MAX_RAIN_MM,
            "geometry_estimated": bool(edge.get("geometry_estimated", True)),
            "geometry_source": edge.get("geometry_source", "SCHEMATIC_ASSUMPTION"),
            "source_node": edge.get("source"),
            "target_node": edge.get("target"),
            "source_lat": source.get("latitude", source.get("lat", 0)),
            "source_lon": source.get("longitude", source.get("lon", 0)),
            "target_lat": target.get("latitude", target.get("lat", 0)),
            "target_lon": target.get("longitude", target.get("lon", 0)),
            "width_m": edge.get("width_m"),
            "height_m": edge.get("height_m"),
            "length_m": edge.get("length_m"),
        })
        output.append(estimate)
    return output


def _build_nodes(edge_predictions):
    edge_lookup = {edge["edge_id"]: edge for edge in edge_predictions}
    nodes = []
    for node_id, info in NODE_EDGE_MAP.items():
        feed_details = []
        for edge_id in info["feed_edges"]:
            prediction = edge_lookup.get(edge_id)
            if prediction:
                feed_details.append({
                    "edge_id": edge_id,
                    "depth_cm": prediction["predicted_depth_cm"],
                    "hazard_level": prediction["hazard_level"],
                    "extrapolation_warning": bool(prediction.get("extrapolation_warning", False)),
                    "geometry_estimated": prediction["geometry_estimated"],
                    "rain_intensity_exceeds_training": prediction["rain_intensity_exceeds_training"],
                })

        max_depth = max((item["depth_cm"] for item in feed_details), default=None)
        nodes.append({
            "id": node_id,
            "name": info["name"],
            "lat": info["lat"],
            "lng": info["lng"],
            "elevation_m": info["elevation_m"],
            "water_depth_cm": round(max_depth, 1) if max_depth is not None else None,
            "hazard_level": _depth_band(max_depth) if max_depth is not None else "NO_MODEL_COVERAGE",
            "is_surcharged": max_depth > 15 if max_depth is not None else None,
            "extrapolation_warning": any(item["extrapolation_warning"] for item in feed_details),
            "rain_intensity_exceeds_training": any(item["rain_intensity_exceeds_training"] for item in feed_details),
            "geometry_estimated": any(item["geometry_estimated"] for item in feed_details),
            "feed_edges": feed_details,
        })
    return nodes


def _unavailable_response(lead_time_mins, mode, message, status="UNAVAILABLE"):
    return {
        "system_status": status,
        "timestamp_epoch": int(time.time()),
        "data_source_mode": mode,
        "data_kind": "forecast_model" if mode == "live" else "synthetic_demo",
        "is_live_data": False,
        "data_quality": "UNAVAILABLE",
        "data_source_name": "Open-Meteo Forecast API" if mode == "live" else "Synthetic demo",
        "data_scenario_label": "Forecast unavailable" if mode == "live" else "Synthetic demo unavailable",
        "alert_message": message,
        "lead_time_minutes": lead_time_mins,
        "lead_time_options": [],
        "metrics": {
            "rain_3h_mm": None, "rain_rate_mm_hr": None, "radar_dbz": None,
            "derived_reflectivity_proxy_dbz": None, "surface_runoff_estimate_mm": None,
            "dwarka_mor_depth_cm": None, "max_depth_cm": None,
        },
        "hydrologic_summary": {
            "radar_reflectivity_dbz": None, "forecast_rain_3h_mm": None,
            "surface_runoff_mm": None, "max_water_depth_cm": None,
            "surcharge_active": None,
        },
        "spatial_node_predictions": [],
        "nodes": [],
        "edge_predictions": [],
    }


def calculate_lightweight_nowcast(lead_time_mins=60, mode="live", zone="pilot", force_refresh=False):
    """Create a forecast response without bundling/loading the local ML pickle."""
    lead_time_mins = max(0, min(180, int(lead_time_mins)))
    if zone != "pilot":
        return _unavailable_response(
            lead_time_mins, mode,
            "Depth estimates are configured only for the Dwarka pilot area.",
            status="UNSUPPORTED_AREA",
        )

    if mode == "simulated":
        scenario_lead = min(DEMO_SCENARIOS, key=lambda step: abs(step - lead_time_mins))
        scenario = DEMO_SCENARIOS[scenario_lead]
        rain_rate_mm_hr = scenario["rain_mm"]
        rain_3h_mm = scenario["rain_3h_mm"]
        proxy_dbz = scenario["proxy_dbz"]
        retrieved_at = None
        valid_times = []
        forecast_model = None
        cache_used = False
        data_quality = "SYNTHETIC_FORMULA_DEMO"
        data_kind = "synthetic_demo"
        data_source_name = "Synthetic demo rainfall + formula-only depth estimate"
        scenario_label = scenario["label"]
        system_status = "DEMO_SIMULATION"
        lead_time_options = [
            {"lead_time_mins": step, "label": item["label"],
             "rain_rate_mm_hr": item["rain_mm"], "rain_3h_accumulated_mm": item["rain_3h_mm"]}
            for step, item in DEMO_SCENARIOS.items()
        ]
    else:
        try:
            forecast, cache_used = _get_live_forecast(force_refresh=force_refresh)
        except Exception:
            return _unavailable_response(
                lead_time_mins, mode,
                "The Open-Meteo forecast could not be reached and no recent forecast is cached. Retry shortly.",
                status="FORECAST_UNAVAILABLE",
            )

        series = [float(value) for value in forecast["nowcast_15min_interval_mm"][:24]]
        index = min(12, max(0, lead_time_mins // 15))
        rain_rate_mm_hr = round(sum(series[index:index + 4]), 2)
        rain_3h_mm = round(sum(series[index:index + 12]), 1)
        proxy_dbz = 0.0
        if rain_rate_mm_hr > 0:
            proxy_dbz = round(min(55.0, max(15.0, 10 * math.log10(max(1, 200 * (rain_rate_mm_hr ** 1.6))))), 1)
        retrieved_at = forecast.get("retrieved_at_utc")
        valid_times = forecast.get("timestamps_iso", [])
        forecast_model = forecast.get("model", "best_match")
        data_quality = "UNVALIDATED_FORMULA_ESTIMATE"
        data_kind = "forecast_model"
        data_source_name = "Open-Meteo forecast + direct assumed-drain formula"
        scenario_label = "Forecast input; formula-only pilot estimate"
        system_status = "FORMULA_ESTIMATE"
        lead_time_options = []

    # Run the configured RandomForest for live forecast input and for the
    # explicitly selected synthetic demo scenario. Demo rainfall stays marked
    # as synthetic; the model backend must not change its provenance.
    rf_predictions, rf_fallback_reason = _request_random_forest(
        rain_rate_mm_hr, rain_3h_mm, proxy_dbz
    )
    edge_predictions = _build_edges(rain_rate_mm_hr, rf_predictions)
    random_forest_active = rf_predictions is not None
    if mode == "live":
        data_quality = "UNVALIDATED_MODEL_ESTIMATE" if random_forest_active else "UNVALIDATED_FORMULA_ESTIMATE"
        system_status = "MODEL_ESTIMATE" if random_forest_active else "FORMULA_ESTIMATE"
        data_source_name = (
            "Open-Meteo forecast + Hugging Face RandomForest surrogate"
            if random_forest_active else "Open-Meteo forecast + direct assumed-drain formula"
        )
    else:
        data_quality = (
            "SYNTHETIC_DEMO_RF_ESTIMATE"
            if random_forest_active else "SYNTHETIC_DEMO_FORMULA_ESTIMATE"
        )
        data_source_name = (
            "Synthetic demo rainfall + Hugging Face RandomForest surrogate"
            if random_forest_active else "Synthetic demo rainfall + direct assumed-drain formula"
        )
    nodes = _build_nodes(edge_predictions)
    max_depth = max((edge["predicted_depth_cm"] for edge in edge_predictions), default=None)
    dwarka_mor_depth = next(
        (node["water_depth_cm"] for node in nodes if node["id"] == "NODE_DWARKA_MOR_METRO"),
        None,
    )
    source_message = (
        f"Demo scenario · synthetic rainfall input {rain_rate_mm_hr:.1f} mm/h · "
        f"{'RandomForest' if random_forest_active else 'hydraulic-formula'} depth-band estimates for mapped pilot links."
        if mode == "simulated" else
        f"Open-Meteo forecast: {rain_3h_mm:.1f} mm over the next 3 hours. "
        (
            "Depth bands use a RandomForest surrogate trained on formula-derived/synthetic targets; they are not water-level measurements."
            if random_forest_active else
            "Depth bands use an unvalidated hydraulic formula and assumed drain properties; they are not water-level measurements."
        )
    )

    response = {
        "system_status": system_status,
        "timestamp_epoch": int(time.time()),
        "data_source_mode": mode,
        "data_kind": data_kind,
        "is_live_data": mode == "live",
        "data_quality": data_quality,
        "data_source_name": data_source_name,
        "data_scenario_label": scenario_label,
        "alert_message": source_message,
        "lead_time_minutes": lead_time_mins,
        "lead_time_options": lead_time_options,
        "rain_intensity_exceeds_training": rain_rate_mm_hr > TRAINING_MAX_RAIN_MM,
        "training_max_rain_mm": TRAINING_MAX_RAIN_MM,
        "metrics": {
            "rain_3h_mm": rain_3h_mm,
            "rain_rate_mm_hr": rain_rate_mm_hr,
            "radar_dbz": None,
            "derived_reflectivity_proxy_dbz": proxy_dbz,
            "surface_runoff_estimate_mm": round(rain_3h_mm * IMPERVIOUSNESS_RATIO, 1),
            "dwarka_mor_depth_cm": dwarka_mor_depth,
            "max_depth_cm": round(max_depth, 1) if max_depth is not None else None,
        },
        "hydrologic_summary": {
            "radar_reflectivity_dbz": None,
            "forecast_rain_3h_mm": rain_3h_mm,
            "surface_runoff_mm": round(rain_3h_mm * IMPERVIOUSNESS_RATIO, 1),
            "max_water_depth_cm": round(max_depth, 1) if max_depth is not None else None,
            "surcharge_active": max_depth > 15 if max_depth is not None else None,
        },
        "spatial_node_predictions": nodes,
        "nodes": nodes,
        "edge_predictions": edge_predictions,
        "depth_model_backend": "random_forest_huggingface" if random_forest_active else "hydraulic_formula",
        "formula_assumptions": {
            "imperviousness_ratio": IMPERVIOUSNESS_RATIO,
            "blockage_factor": "Per-edge graph value; assumed where not surveyed",
            "contributing_fraction": CONTRIBUTING_FRACTION,
            "ponding_area_sqm": PONDING_AREA_SQM,
        },
        "model_caveat": (
            "The RandomForest artifact is served by the configured inference service. Its training labels are formula-derived/synthetic and it has no independent observed-depth validation; outputs are estimates, not measurements or safety clearances."
            if random_forest_active else
            "The direct hydraulic formula is active. Configure SIH_RF_INFERENCE_URL to use the RandomForest service. Drain geometry/capacity are assumptions; outputs are unvalidated estimates, not measurements or safety clearances."
        ),
    }
    if mode == "live" and not random_forest_active:
        response["depth_model_fallback_reason"] = rf_fallback_reason
    if mode == "live":
        response.update({
            "forecast_retrieved_at_utc": retrieved_at,
            "forecast_cache_used": cache_used,
            "forecast_valid_times": valid_times,
            "forecast_model": forecast_model,
            "forecast_temporal_resolution_note": (
                "Open-Meteo's Delhi 15-minute precipitation values are interpolated from hourly forecast output; "
                "they are not 15-minute observations."
            ),
        })
    return response
