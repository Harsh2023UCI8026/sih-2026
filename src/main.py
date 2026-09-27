import os
import datetime
import json
import math
import mimetypes
import sys
import time
import traceback
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load Drainage Graph JSON if available
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(WORKSPACE_DIR, "dwarka_drainage_graph.json")
API_CONTRACT_VERSION = "1.0.1"
# Request handlers import sibling modules after the server starts. Keep the
# script directory importable even when main.py is launched through runpy.
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

def get_drainage_graph():
    if os.path.exists(GRAPH_FILE):
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "data_quality": "UNCONFIGURED_FALLBACK",
        "provenance_note": "Static fallback coordinates only. No drainage edges or surveyed elevation data are configured.",
        "nodes": [
            {"id": "NODE_UTTAM_NAGAR_W", "name": "Uttam Nagar West", "elevation_m": 218.2, "lat": 28.6210, "lng": 77.0420},
            {"id": "NODE_DWARKA_MOR_METRO", "name": "Dwarka Mor Metro Crossing", "elevation_m": 211.2, "lat": 28.6186, "lng": 77.0319},
            {"id": "NODE_KAKROLA_UNDERPASS", "name": "Kakrola Mod Underpass", "elevation_m": 209.5, "lat": 28.6120, "lng": 77.0250},
            {"id": "NODE_SEC14_METRO", "name": "Sector 14 Metro Station", "elevation_m": 212.8, "lat": 28.6022, "lng": 77.0260},
            {"id": "NODE_SEC16B_NLU", "name": "Sector 16B NLU Stretch", "elevation_m": 212.0, "lat": 28.6034, "lng": 77.0174},
            {"id": "NODE_SEC6_RIDGE", "name": "Dwarka Sector 6 Ridge", "elevation_m": 219.5, "lat": 28.5910, "lng": 77.0610}
        ]
    }


def has_loopback_outbound_proxy():
    """Return whether Python is configured to route HTTP through loopback."""
    import urllib.request

    for value in urllib.request.getproxies().values():
        try:
            proxy_url = value if "://" in value else f"http://{value}"
            if urlparse(proxy_url).hostname in {"127.0.0.1", "localhost", "::1"}:
                return True
        except (TypeError, ValueError):
            continue
    return False


def describe_forecast_request_error(exc):
    """Convert provider/network exceptions into a useful, non-secret message."""
    import socket
    from urllib.error import HTTPError, URLError

    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return "PROVIDER_RATE_LIMITED", "Open-Meteo rate limit reached. Wait a few minutes, then retry."
        if exc.code in (401, 403):
            return (
                "PROVIDER_ACCESS_DENIED",
                "Open-Meteo rejected the request. The public forecast endpoint does not need an API key; check the endpoint and server access."
            )
        return "PROVIDER_HTTP_ERROR", f"Open-Meteo returned HTTP {exc.code}. Try again later."

    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "PROVIDER_TIMEOUT", "Open-Meteo did not respond within 6 seconds. Check the server connection and retry."
    connection_refused = isinstance(reason, OSError) and (
        getattr(reason, "winerror", None) == 10061
        or getattr(reason, "errno", None) in (111, 10061)
    )
    if connection_refused:
        if has_loopback_outbound_proxy():
            return (
                "LOCAL_PROXY_REFUSED",
                "Python's configured local outbound proxy is refusing connections. Check the proxy settings for the server process, then retry.",
            )
        return "CONNECTION_REFUSED", "The app server's connection to Open-Meteo was refused. Check outbound HTTPS access, then retry."
    if isinstance(reason, OSError) and getattr(reason, "errno", None) == 113:
        return "NETWORK_UNREACHABLE", "The app server could not reach Open-Meteo. Check outbound HTTPS access, then retry."
    if isinstance(exc, URLError):
        return "NETWORK_ERROR", "The app server could not connect to Open-Meteo. Check internet/firewall access, then retry."
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "FETCHER_UNAVAILABLE", "The forecast connector could not load. Check the deployment package and retry."
    return "PROVIDER_RESPONSE_ERROR", "Open-Meteo returned an unreadable response. Retry in a moment."


def calculate_nowcast(lead_time_mins=60, mode="live", zone="pilot", force_refresh=False):
    """Return a clearly sourced demo or an unvalidated pilot model estimate.

    Live mode uses Open-Meteo forecast-model precipitation as its only live
    weather input. It does not provide measured radar reflectivity or street
    water levels. Modelled depth values are explicitly marked unvalidated.
    """
    import tempfile
    from inference_api import (
        get_node_summary, get_edge_predictions,
        get_system_status, get_lead_time_options, TRAINING_MAX_RAIN_MM,
    )

    now_epoch = int(time.time())
    lead_time_mins = max(0, min(180, int(lead_time_mins)))
    demo_options = get_lead_time_options()

    def unavailable(reason, status="UNAVAILABLE", source="Open-Meteo Forecast API", diagnostic_code=None):
        return {
            "system_status": status,
            "timestamp_epoch": now_epoch,
            "data_source_mode": mode,
            "data_kind": "forecast_model",
            "is_live_data": False,
            "data_quality": "UNAVAILABLE",
            "data_source_name": source,
            "data_scenario_label": source,
            "alert_message": reason,
            "forecast_diagnostic_code": diagnostic_code,
            "lead_time_minutes": lead_time_mins,
            # Synthetic lead-time scenarios are never exposed as live data.
            "lead_time_options": [],
            "metrics": {
                "rain_3h_mm": None,
                "radar_dbz": None,
                "surface_runoff_estimate_mm": None,
                "dwarka_mor_depth_cm": None,
                "max_depth_cm": None,
            },
            "hydrologic_summary": {
                "radar_reflectivity_dbz": None,
                "forecast_rain_3h_mm": None,
                "surface_runoff_mm": None,
                "max_water_depth_cm": None,
                "surcharge_active": None,
            },
            "spatial_node_predictions": [],
            "nodes": [],
            "edge_predictions": [],
        }

    if mode == "simulated":
        edge_preds = get_edge_predictions(lead_time_mins)
        status = get_system_status(lead_time_mins, edge_predictions=edge_preds)
        nodes = get_node_summary(lead_time_mins, edge_predictions=edge_preds)
        rain_rate_mm_hr = status.get("rain_rate_mm_hr")
        rain_3h_mm = status.get("rain_3h_accumulated_mm")
        max_depth = status.get("max_depth_cm")
        return {
            "system_status": "DEMO_SIMULATION",
            "timestamp_epoch": now_epoch,
            "data_source_mode": "simulated",
            "data_kind": "synthetic_demo",
            "is_live_data": False,
            "data_quality": "SYNTHETIC_DEMO",
            "data_source_name": f"Synthetic demo scenario: {status.get('scenario_label', 'Storm Simulation')}",
            "data_scenario_label": status.get("scenario_label", "Storm Simulation"),
            "alert_message": (
                f"DEMO ONLY: synthetic rainfall rate ({rain_rate_mm_hr} mm/hr), "
                f"3-hour scenario total ({rain_3h_mm} mm). Depth output is shown as a band."
            ),
            "lead_time_minutes": lead_time_mins,
            "lead_time_options": demo_options,
            "rain_intensity_exceeds_training": status.get("rain_intensity_exceeds_training", False),
            "training_max_rain_mm": TRAINING_MAX_RAIN_MM,
            "metrics": {
                "rain_3h_mm": rain_3h_mm,
                "rain_rate_mm_hr": rain_rate_mm_hr,
                "radar_dbz": None,
                "derived_reflectivity_proxy_dbz": status.get("radar_dbz"),
                "surface_runoff_estimate_mm": round((rain_3h_mm or 0) * 0.85, 1),
                "dwarka_mor_depth_cm": next((n.get("water_depth_cm") for n in nodes if n.get("id") == "NODE_DWARKA_MOR_METRO"), None),
                "max_depth_cm": max_depth,
            },
            "hydrologic_summary": {
                "radar_reflectivity_dbz": None,
                "forecast_rain_3h_mm": rain_3h_mm,
                "surface_runoff_mm": round((rain_3h_mm or 0) * 0.85, 1),
                "max_water_depth_cm": max_depth,
                "surcharge_active": bool(max_depth is not None and max_depth > 15),
            },
            "spatial_node_predictions": nodes,
            "nodes": nodes,
            "edge_predictions": edge_preds,
        }

    # The current hydraulic graph and trained surrogate cover only the Dwarka pilot.
    if zone != "pilot":
        return unavailable(
            "No validated drainage model is configured for this selected area. "
            "Choose the Dwarka pilot area to view its unvalidated model estimates.",
            status="UNSUPPORTED_AREA",
            source="No model configured for selected area",
        )

    cache_path = os.path.join(tempfile.gettempdir(), "dwarka_live_radar.json")
    forecast = None
    cache_used = False
    cached_fallback = None
    try:
        if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 900:
            with open(cache_path, "r", encoding="utf-8") as cache_file:
                cached = json.load(cache_file)
            if (
                cached.get("schema_version") == 3
                and cached.get("provider") == "Open-Meteo Forecast API"
                and cached.get("data_kind") == "forecast_model"
                and isinstance(cached.get("nowcast_15min_interval_mm"), list)
                and len(cached["nowcast_15min_interval_mm"]) >= 24
                and all(v is not None and math.isfinite(float(v)) and float(v) >= 0 for v in cached["nowcast_15min_interval_mm"][:24])
                and isinstance(cached.get("timestamps_iso"), list)
                and len(cached["timestamps_iso"]) >= 24
            ):
                cached_fallback = cached
                if not force_refresh:
                    forecast = cached
                    cache_used = True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        cached_fallback = None

    if forecast is None:
        try:
            from fetch_live_radar import fetch_live_radar_nowcast
            forecast = fetch_live_radar_nowcast(timeout_sec=6.0)
        except Exception as exc:
            # Open-Meteo can briefly return 5xx responses. Retry once, then
            # use only a fully validated provider cache no older than 15 min.
            if getattr(exc, "code", None) in (500, 502, 503, 504):
                time.sleep(0.5)
                try:
                    forecast = fetch_live_radar_nowcast(timeout_sec=6.0)
                except Exception as retry_exc:
                    exc = retry_exc
            if forecast is None and cached_fallback is not None:
                forecast = cached_fallback
                cache_used = True
                print("[WARN] Open-Meteo refresh failed; using validated forecast cache (<15 min old).")
            elif forecast is None:
                diagnostic_code, diagnostic_message = describe_forecast_request_error(exc)
                print(f"[ERROR] Open-Meteo forecast unavailable ({diagnostic_code}): {exc}")
                return unavailable(
                    f"{diagnostic_message} No rainfall or street-depth estimate is shown; "
                    "this does not mean conditions are dry or safe.",
                    diagnostic_code=diagnostic_code,
                )

    series = forecast.get("nowcast_15min_interval_mm")
    if not isinstance(series, list) or len(series) < 24 or any(v is None for v in series[:24]):
        return unavailable("The forecast feed returned incomplete precipitation data; no depth estimate is shown.")
    try:
        series = [float(v) for v in series[:24]]
    except (TypeError, ValueError):
        return unavailable("The forecast feed returned invalid precipitation data; no depth estimate is shown.")
    if any(not math.isfinite(v) or v < 0 for v in series):
        return unavailable("The forecast feed returned invalid precipitation data; no depth estimate is shown.")

    index = min(12, max(0, lead_time_mins // 15))
    hourly_window = series[index:index + 4]
    # Each entry is a 15-minute precipitation amount in mm. Summing four
    # entries gives the next-hour amount; don't multiply this by four again.
    hourly_rain_mm = sum(hourly_window) if hourly_window else 0.0
    rain_3h_mm = round(sum(series[index:index + 12]), 1)
    proxy_dbz = 0.0
    if hourly_rain_mm > 0:
        proxy_dbz = round(min(55.0, max(15.0, 10 * math.log10(max(1, 200 * (hourly_rain_mm ** 1.6))))), 1)

    live_scenario = {
        "rain_mm": round(hourly_rain_mm, 2),
        "rain_3h_accumulated": rain_3h_mm,
        # The model expects this feature, but the value is a formula-derived
        # proxy and is never presented as a radar observation.
        "radar_reflectivity_dbz": proxy_dbz,
        "imperviousness_ratio": 0.85,
    }
    edge_preds = get_edge_predictions(lead_time_mins, live_rain_scenario=live_scenario)
    status = get_system_status(
        lead_time_mins,
        live_rain_scenario=live_scenario,
        edge_predictions=edge_preds,
    )
    nodes = get_node_summary(
        lead_time_mins,
        live_rain_scenario=live_scenario,
        edge_predictions=edge_preds,
    )
    if not edge_preds:
        return unavailable(
            "Forecast input is available, but the pilot depth model could not produce an estimate. "
            "No street-depth result is shown.",
            status="MODEL_UNAVAILABLE",
            source="Open-Meteo precipitation forecast; depth model unavailable",
        )

    max_depth = status.get("max_depth_cm")
    dwarka_depth = next((n.get("water_depth_cm") for n in nodes if n.get("id") == "NODE_DWARKA_MOR_METRO"), None)
    rain_rate_mm_hr = round(hourly_rain_mm, 2)
    rain_exceeds_training = hourly_rain_mm > TRAINING_MAX_RAIN_MM
    if rain_3h_mm == 0:
        alert_msg = (
            "Open-Meteo forecast: 0.0 mm precipitation over the next 3 hours."
        )
    else:
        alert_msg = (
            f"Open-Meteo forecast: {rain_3h_mm:.1f} mm over the next 3 hours "
            f"({rain_rate_mm_hr:.1f} mm in the next hour; window starts at +{lead_time_mins} min)."
        )
    if rain_exceeds_training:
        alert_msg += f" Rainfall input exceeds the model training range ({TRAINING_MAX_RAIN_MM} mm/hr)."

    retrieved_at = forecast.get("retrieved_at_utc")
    valid_times = forecast.get("timestamps_iso", [])
    return {
        "system_status": "MODEL_ESTIMATE",
        "timestamp_epoch": now_epoch,
        "data_source_mode": "live",
        "data_kind": "forecast_model",
        "is_live_data": True,
        "data_quality": "UNVALIDATED_MODEL_ESTIMATE",
        "data_source_name": "Open-Meteo forecast model + Dwarka pilot depth model",
        "data_scenario_label": "Forecast input; pilot-model depth bands",
        "alert_message": alert_msg,
        "lead_time_minutes": lead_time_mins,
        # Live forecasts do not include fixed synthetic demo scenarios.
        "lead_time_options": [],
        "forecast_retrieved_at_utc": retrieved_at,
        "forecast_cache_used": cache_used,
        "forecast_valid_times": valid_times,
        "forecast_model": forecast.get("model", "best_match"),
        "forecast_temporal_resolution_note": forecast.get("temporal_resolution_note"),
        "rain_intensity_exceeds_training": rain_exceeds_training,
        "training_max_rain_mm": TRAINING_MAX_RAIN_MM,
        "metrics": {
            "rain_3h_mm": rain_3h_mm,
            "rain_rate_mm_hr": rain_rate_mm_hr,
            "radar_dbz": None,
            "derived_reflectivity_proxy_dbz": proxy_dbz,
            "surface_runoff_estimate_mm": round(rain_3h_mm * 0.85, 1),
            "dwarka_mor_depth_cm": dwarka_depth,
            "max_depth_cm": max_depth,
        },
        "hydrologic_summary": {
            "radar_reflectivity_dbz": None,
            "forecast_rain_3h_mm": rain_3h_mm,
            "surface_runoff_mm": round(rain_3h_mm * 0.85, 1),
            "max_water_depth_cm": max_depth,
            "surcharge_active": bool(max_depth is not None and max_depth > 15),
        },
        "spatial_node_predictions": nodes,
        "nodes": nodes,
        "edge_predictions": edge_preds,
    }

def is_in_dwarka_catchment(lat, lng):
    """
    Geofence helper: Checks if coordinates fall within Dwarka Mor Pilot Catchment.
    Bounding Box: (28.5900 N - 28.6300 N, 77.0150 E - 77.0500 E)
    """
    try:
        lat = float(lat)
        lng = float(lng)
        return (28.5900 <= lat <= 28.6300) and (77.0150 <= lng <= 77.0500)
    except Exception:
        return False

class SIHNowcastingAPIHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status_code=200):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-SIH-API-Version', API_CONTRACT_VERSION)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Expose-Headers', 'X-SIH-API-Version')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type='text/html'):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            if content_type.startswith('image/') or content_type.startswith('font/'):
                self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "File Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Dashboard Web UI & Static Assets
        if path == '/' or path == '/index.html':
            self._send_file(os.path.join(WORKSPACE_DIR, 'index.html'), 'text/html')
        elif path in ['/logo.jpeg', '/assets/logo.jpg', '/dashboard-assets/logo.jpg']:
            self._send_file(os.path.join(WORKSPACE_DIR, '..', 'assets', 'logo.jpg'), 'image/jpeg')
        elif path == '/logo.webp':
            self._send_file(os.path.join(WORKSPACE_DIR, 'logo.webp'), 'image/webp')
        elif path == '/human.jpeg':
            self._send_file(os.path.join(WORKSPACE_DIR, 'human.webp'), 'image/webp')
        elif path == '/human.webp':
            self._send_file(os.path.join(WORKSPACE_DIR, 'human.webp'), 'image/webp')
        elif path == '/dashboard-assets/human.webp':
            self._send_file(os.path.join(WORKSPACE_DIR, 'human.webp'), 'image/webp')
        elif path.lower().endswith('.gif'):
            # Serve any .gif file from the workspace directory
            gif_name = os.path.basename(path)
            gif_path = os.path.join(WORKSPACE_DIR, gif_name)
            if os.path.exists(gif_path):
                self._send_file(gif_path, 'image/gif')
            else:
                # Fallback to hello.gif if the requested file is missing
                default_gif = os.path.join(WORKSPACE_DIR, 'hello.gif')
                self._send_file(default_gif, 'image/gif')
        elif path == '/robots.txt':
            self._send_file(os.path.join(WORKSPACE_DIR, 'robots.txt'), 'text/plain')
        elif path == '/sitemap.xml':
            self._send_file(os.path.join(WORKSPACE_DIR, 'sitemap.xml'), 'application/xml')
        elif path == '/site.webmanifest':
            self._send_file(os.path.join(WORKSPACE_DIR, '..', 'site.webmanifest'), 'application/manifest+json')
        elif path == '/dwarka_catchment_bounds.geojson':
            self._send_file(os.path.join(WORKSPACE_DIR, 'data', 'dwarka_catchment_bounds.geojson'), 'application/geo+json')
        elif path.startswith('/data/'):
            relative_path = path[len('/data/'):].replace('/', os.sep)
            data_roots = (
                os.path.abspath(os.path.join(WORKSPACE_DIR, 'src', 'data')),
                os.path.abspath(os.path.join(WORKSPACE_DIR, 'data')),
            )
            asset_path = None
            for data_root in data_roots:
                candidate = os.path.abspath(os.path.join(data_root, relative_path))
                if os.path.commonpath((data_root, candidate)) == data_root and os.path.isfile(candidate):
                    asset_path = candidate
                    break
            if asset_path:
                content_type = mimetypes.guess_type(asset_path)[0] or 'application/octet-stream'
                self._send_file(asset_path, content_type)
            else:
                self.send_error(404, "Data Asset Not Found")
        elif path.startswith('/vendor/leaflet/'):
            vendor_root = os.path.abspath(os.path.join(WORKSPACE_DIR, 'vendor', 'leaflet'))
            asset_path = os.path.abspath(os.path.join(vendor_root, path[len('/vendor/leaflet/'):].replace('/', os.sep)))
            if os.path.commonpath((vendor_root, asset_path)) == vendor_root and os.path.isfile(asset_path):
                content_type = mimetypes.guess_type(asset_path)[0] or 'application/octet-stream'
                self._send_file(asset_path, content_type)
            else:
                self.send_error(404, "Asset Not Found")
        elif path.startswith('/dashboard-assets/leaflet/'):
            vendor_root = os.path.abspath(os.path.join(WORKSPACE_DIR, 'vendor', 'leaflet'))
            relative_asset = path[len('/dashboard-assets/leaflet/'):].replace('/', os.sep)
            asset_path = os.path.abspath(os.path.join(vendor_root, relative_asset))
            if os.path.commonpath((vendor_root, asset_path)) == vendor_root and os.path.isfile(asset_path):
                content_type = mimetypes.guess_type(asset_path)[0] or 'application/octet-stream'
                self._send_file(asset_path, content_type)
            else:
                self.send_error(404, "Asset Not Found")
        elif os.path.exists(os.path.join(WORKSPACE_DIR, os.path.basename(path))) and os.path.isfile(os.path.join(WORKSPACE_DIR, os.path.basename(path))):
            fname = os.path.basename(path)
            fpath = os.path.join(WORKSPACE_DIR, fname)
            ext = os.path.splitext(fname)[1].lower()
            mtype = 'image/gif' if ext == '.gif' else ('image/jpeg' if ext in ['.jpg', '.jpeg'] else ('image/webp' if ext == '.webp' else 'text/plain'))
            self._send_file(fpath, mtype)

        elif path == '/api/v1/zones':
            from utils_config import load_config
            cfg = load_config()
            self._send_json(cfg.get('presets', {}))

        elif path == '/api/v1/nowcast':
            lead_time = int(query.get('lead_time_mins', [60])[0])
            mode = query.get('mode', ['live'])[0]
            zone = query.get('zone', ['pilot'])[0]
            force_refresh = query.get('refresh', ['0'])[0] == '1'
            try:
                self._send_json(calculate_nowcast(lead_time, mode, zone, force_refresh=force_refresh))
            except Exception as exc:
                print(f"[ERROR] Nowcast calculation failed: {exc}")
                traceback.print_exc()
                self._send_json({"error": "Nowcast calculation failed", "detail": str(exc)}, 500)

        # 3. REST API: GET /api/v1/drainage-network
        elif path == '/api/v1/drainage-network':
            self._send_json(get_drainage_graph())

        # 4. REST API: GET /api/v1/potholes-depressions
        elif path == '/api/v1/potholes-depressions':
            pothole_file = os.path.join(WORKSPACE_DIR, 'data', 'pothole_depression_registry.json')
            if os.path.exists(pothole_file):
                with open(pothole_file, 'r', encoding='utf-8') as pf:
                    self._send_json(json.load(pf))
            else:
                self._send_json({"error": "Pothole registry not built yet"}, 404)

        # 4. OpenAPI / Swagger API Docs Endpoint
        elif path in ['/docs', '/docs/', '/api/docs', '/api/docs/', '/api/v1/docs', '/api/v1/docs/']:
            swagger_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
  <title>Urban Flood Dashboard Prototype API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
  <style>
    /* 📱 Mobile-First Responsive Overrides for Swagger UI (360px - 480px) */
    html, body {
      margin: 0;
      padding: 0;
      background: #fafafa;
    }
    @media (max-width: 600px) {
      .swagger-ui .wrapper {
        padding: 0 8px !important;
        width: 100% !important;
        box-sizing: border-box !important;
      }
      .swagger-ui .opblock-summary {
        flex-wrap: wrap !important;
        padding: 8px !important;
      }
      .swagger-ui .opblock-summary-path {
        font-size: 11px !important;
        word-break: break-all !important;
        max-width: 100% !important;
      }
      .swagger-ui .opblock-summary-description {
        display: none !important;
      }
      .swagger-ui .opblock-summary-method {
        min-width: 48px !important;
        font-size: 10px !important;
        padding: 4px 6px !important;
      }
      .swagger-ui table {
        display: block !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        width: 100% !important;
      }
      .swagger-ui .btn {
        width: 100% !important;
        margin: 4px 0 !important;
        box-sizing: border-box !important;
      }
      .swagger-ui .info {
        margin: 12px 0 !important;
      }
      .swagger-ui .info .title {
        font-size: 18px !important;
      }
      .swagger-ui .topbar {
        display: none !important;
      }
      .swagger-ui .opblock-body pre.microlight {
        font-size: 10px !important;
        word-break: break-all !important;
        white-space: pre-wrap !important;
      }
      .swagger-ui .responses-table {
        width: 100% !important;
      }
      .swagger-ui select {
        width: 100% !important;
      }
      .swagger-ui input[type=text] {
        width: 100% !important;
        box-sizing: border-box !important;
      }
    }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/api/v1/openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [
        SwaggerUIBundle.presets.apis
      ]
    });
  </script>
</body>
</html>"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(swagger_html.encode('utf-8'))

        elif path == '/api/v1/openapi.json':
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Urban Flood Dashboard Prototype API",
                    "version": API_CONTRACT_VERSION,
                    "description": "Prototype REST API. Open-Meteo supplies forecast-model precipitation; street-depth outputs are unvalidated estimates. Route comparisons can be unavailable and are not safety clearances."
                },
                "paths": {
                    "/api/v1/nowcast": {
                        "get": {
                            "summary": "Get forecast input and unvalidated Dwarka pilot depth estimate",
                            "parameters": [
                                {"name": "lead_time_mins", "in": "query", "schema": {"type": "integer", "default": 60}},
                                {"name": "zone", "in": "query", "schema": {"type": "string", "default": "pilot"}},
                                {"name": "refresh", "in": "query", "schema": {"type": "boolean", "default": False}, "description": "Set true to bypass the recent server cache"}
                            ],
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/v1/drainage-network": {
                        "get": {
                            "summary": "Get 1D Directed Drainage Graph Network G=(V,E)",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/v1/navigate": {
                        "post": {
                            "summary": "Compare OSRM routes with unvalidated pilot model estimates; no safety clearance",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/v1/route/flood-safe": {
                        "post": {
                            "summary": "Compare OSRM route geometry with nearby unvalidated model estimates; no safety clearance",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/v1/alert-broadcast": {
                        "post": {
                            "summary": "Prepare a local alert preview; no message is sent",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    }
                }
            }
            self._send_json(openapi_spec)

        else:
            self._send_json({"error": "Endpoint not found", "available_endpoints": ["/api/v1/nowcast", "/api/v1/drainage-network", "/api/v1/navigate", "/api/v1/route/flood-safe", "/api/v1/alert-broadcast", "/docs"]}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/v1/route/flood-safe':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            
            try:
                body = json.loads(post_data)
            except Exception:
                body = {}

            orig = body.get("origin", {"lat": 28.6210, "lng": 77.0420})
            dest = body.get("destination", {"lat": 28.5910, "lng": 77.0610})
            if isinstance(orig, list): orig = {"lat": orig[0], "lng": orig[1]}
            if isinstance(dest, list): dest = {"lat": dest[0], "lng": dest[1]}

            vehicle_type = body.get("vehicle_type", "car").lower()
            lead_time_mins = int(body.get("lead_time_mins", 60))

            # Comparison uses unvalidated pilot estimates only. The selected
            # vehicle is context and no vehicle clearance threshold is applied.
            nowcast = calculate_nowcast(lead_time_mins, mode="live", zone="pilot")
            pilot_coverage = is_in_dwarka_catchment(orig.get("lat"), orig.get("lng")) and is_in_dwarka_catchment(dest.get("lat"), dest.get("lng"))
            if not pilot_coverage or nowcast.get("data_quality") != "UNVALIDATED_MODEL_ESTIMATE":
                reason = (
                    "Flood-status comparison is available only for routes fully inside the Dwarka pilot and when forecast data is available."
                    if not pilot_coverage else
                    "Forecast or pilot depth model is unavailable. No route is labeled safe."
                )
                self._send_json({
                    "routing_engine": "Flood-aware route comparison unavailable",
                    "routing_status": "FLOOD_STATUS_UNAVAILABLE",
                    "flood_safety_status": "UNVERIFIED",
                    "origin": orig, "destination": dest,
                    "vehicle_type": vehicle_type, "lead_time_minutes": lead_time_mins,
                    "notice": reason, "routes": [],
                })
                return
            flood_nodes = nowcast.get("spatial_node_predictions", [])

            # Compute 3 alternative routes (using OSRM or robust fallback solver)
            import urllib.request
            osrm_routes = []
            try:
                osrm_url = f"http://router.project-osrm.org/route/v1/driving/{orig['lng']},{orig['lat']};{dest['lng']},{dest['lat']}?overview=full&geometries=geojson&alternatives=true&steps=true"
                req = urllib.request.Request(osrm_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        osrm_data = json.loads(resp.read().decode('utf-8'))
                        osrm_routes = osrm_data.get("routes", [])
            except Exception as e:
                print("OSRM query offline/failed, using dynamic multi-route generator:", e)

            routes_response = []
            if not osrm_routes:
                self._send_json({
                    "routing_engine": "OSRM unavailable",
                    "routing_status": "ROAD_ROUTE_UNAVAILABLE",
                    "flood_safety_status": "UNVERIFIED",
                    "origin": orig, "destination": dest,
                    "vehicle_type": vehicle_type, "lead_time_minutes": lead_time_mins,
                    "notice": "No road-route provider response was available. Straight-line routes are not shown as drivable roads.",
                    "routes": [],
                })
                return

            if osrm_routes:
                for idx, r in enumerate(osrm_routes):
                    coords_raw = r["geometry"]["coordinates"] # [lng, lat]
                    coords = [[c[1], c[0]] for c in coords_raw] # [lat, lng]
                    distance_km = round(r.get("distance", 0) / 1000.0, 1)
                    eta_mins = max(1, round(r.get("duration", 0) / 60.0))

                    # Check max flood depth along route coordinates
                    max_depth = None
                    flooded_segs = []

                    for pt in coords:
                        for fn in flood_nodes:
                            # Euclidean distance approximation in meters
                            d_m = math.sqrt((pt[0] - fn["lat"])**2 + (pt[1] - fn["lng"])**2) * 111000
                            if d_m < 400: # Sparse node estimate within 400m; not a road measurement
                                d_cm = fn.get("water_depth_cm")
                                if d_cm is None:
                                    continue
                                max_depth = max(float(d_cm), max_depth if max_depth is not None else float(d_cm))
                                if d_cm > 15.0:
                                    flooded_segs.append({
                                        "road_name": fn["name"],
                                        "depth_cm": d_cm,
                                        "coords": [fn["lat"], fn["lng"]]
                                    })

                    unique_flooded = []
                    seen = set()
                    for fs in flooded_segs:
                        if fs["road_name"] not in seen:
                            seen.add(fs["road_name"])
                            unique_flooded.append(fs)

                    status = "MODEL_ESTIMATE"

                    wps = []
                    if len(coords) > 6:
                        step_idx = len(coords) // 3
                        for k in range(1, 3):
                            wpt = coords[k * step_idx]
                            wps.append(f"{wpt[0]:.5f},{wpt[1]:.5f}")

                    wp_param = "|".join(wps)
                    gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={orig['lat']:.5f},{orig['lng']:.5f}&destination={dest['lat']:.5f},{dest['lng']:.5f}"
                    if wp_param:
                        gmaps_url += f"&waypoints={wp_param}"
                    gmaps_url += "&travelmode=driving"

                    routes_response.append({
                        "route_id": f"r{idx+1}",
                        "name": f"Route Option {idx+1}" + (" (Direct)" if idx==0 else " (Alternative)"),
                        "status": status,
                        "eta_minutes": eta_mins,
                        "distance_km": distance_km,
                        "max_water_depth_cm": round(max_depth, 1) if max_depth is not None else None,
                        "vehicle_type": vehicle_type,
                        "flooded_segments": unique_flooded,
                        "coordinates": coords,
                        "google_maps_url": gmaps_url
                    })

            # OSRM supplies road geometry. Flood depths are sparse, unvalidated
            # estimates near pilot graph nodes; they are not road measurements.
            routes_response.sort(key=lambda x: (x["max_water_depth_cm"] if x["max_water_depth_cm"] is not None else float("inf"), x["eta_minutes"]))

            orig_in_catchment = is_in_dwarka_catchment(orig['lat'], orig['lng'])
            dest_in_catchment = is_in_dwarka_catchment(dest['lat'], dest['lng'])
            is_outside_pilot = not (orig_in_catchment and dest_in_catchment)

            geofence_message = None

            recommended_id = routes_response[0]["route_id"] if routes_response else "r1"

            self._send_json({
                "routing_engine": "OSRM road geometry + unvalidated pilot model estimates",
                "routing_status": "ROUTES_WITH_UNVALIDATED_DEPTH_ESTIMATES",
                "flood_safety_status": "UNVERIFIED_MODEL_ESTIMATE",
                "model_caveat": "Depths are sparse model estimates around pilot graph nodes, not observed water depths along the road.",
                "origin": orig,
                "destination": dest,
                "vehicle_type": vehicle_type,
                "lead_time_minutes": lead_time_mins,
                "origin_in_catchment": orig_in_catchment,
                "destination_in_catchment": dest_in_catchment,
                "is_outside_pilot": is_outside_pilot,
                "geofence_message": geofence_message,
                "recommended_route_id": recommended_id,
                "routes": routes_response
            })

        elif parsed.path == '/api/v1/navigate':
            self._send_json({
                "routing_status": "USE_FLOOD_SAFE_ROUTE_ENDPOINT",
                "notice": "This legacy endpoint is not configured to validate flood conditions. Use /api/v1/route/flood-safe; it returns no route when pilot forecast/model inputs are unavailable.",
                "routes": [],
            }, 410)

        elif parsed.path == '/api/v1/alert-broadcast':
            # This endpoint only prepares a local preview. The project has no
            # connected agency dispatch, SMS gateway, or verified sensor feed.
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            try:
                body = json.loads(post_data)
            except (TypeError, json.JSONDecodeError):
                body = {}

            depth = body.get('water_depth_cm')
            try:
                depth = float(depth) if depth is not None else None
            except (TypeError, ValueError):
                depth = None

            self._send_json({
                "alert_status": "PREVIEW_ONLY_NOT_SENT",
                "timestamp_epoch": int(time.time()),
                "target_location": body.get("target_location"),
                "water_depth_cm": depth,
                "data_quality": "UNVALIDATED_MODEL_ESTIMATE" if depth is not None else "UNAVAILABLE",
                "notice": "Preview only. No message was sent and no emergency agency was contacted.",
                "agency_dispatches": {},
            })
        else:
            self._send_json({"error": "POST Endpoint not found"}, 404)

class ReusableHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

def run_server(port=8083):
    server_address = ('', port)
    httpd = ReusableHTTPServer(server_address, SIHNowcastingAPIHandler)
    print("=" * 60)
    print(f"SIH 2026 REST API Backend Server Running on http://localhost:{port}/")
    print(f"Swagger API Documentation available at: http://localhost:{port}/docs")
    print(f"GET  /api/v1/nowcast?lead_time_mins=60")
    print(f"GET  /api/v1/drainage-network")
    print(f"POST /api/v1/route/flood-safe")
    print("=" * 60)
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(8083)
