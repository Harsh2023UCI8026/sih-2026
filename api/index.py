import json
import time
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler

import os
import sys
# Add src directory to path to allow importing the real inference API
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.append(src_path)

from main import API_CONTRACT_VERSION, calculate_nowcast as get_nowcast, get_drainage_graph

class handler(BaseHTTPRequestHandler):
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

        if path in ['/api/docs', '/api/v1/docs', '/api/swagger', '/docs']:
            swagger_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
  <title>SIH 2026 Urban Flood Nowcasting API Docs</title>
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
      url: '/api/openapi.json',
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
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(swagger_html.encode('utf-8'))
            return

        elif path in ['/api/openapi.json', '/api/v1/openapi.json']:
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Urban Flood Dashboard Prototype API",
                    "version": API_CONTRACT_VERSION,
                    "description": "Prototype API. Open-Meteo supplies forecast-model precipitation; street-depth outputs are unvalidated estimates. Alert responses are preview-only."
                },
                "paths": {
                    "/api/nowcast": {
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
                    "/api/drainage-network": {
                        "get": {
                            "summary": "Get 1D Directed Drainage Graph Network G=(V,E)",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/navigate": {
                        "post": {
                            "summary": "Flood-status route comparison (unvalidated pilot estimates; may be unavailable)",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/alert-broadcast": {
                        "post": {
                            "summary": "Prepare a local alert preview; no message is sent",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    }
                }
            }
            self._send_json(openapi_spec)
            return

        elif 'nowcast' in path:
            lead_time = int(query.get('lead_time_mins', [60])[0])
            mode = query.get('mode', ['live'])[0]
            zone = query.get('zone', ['pilot'])[0]
            force_refresh = query.get('refresh', ['0'])[0] == '1'
            self._send_json(get_nowcast(lead_time, mode, zone, force_refresh=force_refresh))
            return

        elif 'potholes-depressions' in path:
            registry_path = os.path.join(src_path, 'data', 'pothole_depression_registry.json')
            try:
                with open(registry_path, 'r', encoding='utf-8') as registry_file:
                    self._send_json(json.load(registry_file))
            except (OSError, json.JSONDecodeError):
                self._send_json({
                    "status": "UNVERIFIED_DATA_NOT_LOADED",
                    "total_hotspots": 0,
                    "hotspots": [],
                    "notice": "Historical registry unavailable; no measurements are inferred.",
                })
            return

        elif 'drainage-network' in path:
            self._send_json(get_drainage_graph())
            return

        else:
            self._send_json({"status": "SIH 2026 Flood Nowcasting Serverless API Active", "docs": "/api/docs"}, 404)
            return

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            body = json.loads(post_data)
        except Exception:
            body = {}

        if 'route/flood-safe' in path or 'navigate' in path:
            self._send_json({
                "routing_status": "UNAVAILABLE",
                "flood_safety_status": "UNVERIFIED",
                "routes": [],
                "notice": "The serverless adapter has no connected road-route provider. It does not fabricate straight-line roads or label a route safe.",
            }, 503)
        elif 'alert-broadcast' in path:
            depth = body.get("water_depth_cm")
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
                "notice": "Preview only. No message was sent and no agency was contacted.",
                "agency_dispatches": {},
            })
        else:
            self._send_json({"error": "POST Endpoint not found"}, 404)

