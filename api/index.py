import json
import time
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler

def get_nowcast(lead_time_mins=60):
    mult = 1.0
    if lead_time_mins <= 0: mult = 0.2
    elif lead_time_mins <= 15: mult = 0.5
    elif lead_time_mins <= 30: mult = 0.8
    elif lead_time_mins <= 60: mult = 1.0
    elif lead_time_mins <= 120: mult = 0.65
    else: mult = 0.3

    return {
        "system_status": "ONLINE",
        "timestamp_epoch": int(time.time()),
        "lead_time_minutes": lead_time_mins,
        "hydrologic_summary": {
            "radar_reflectivity_dbz": round(48.5 * mult, 1),
            "forecast_rain_3h_mm": round(65.0 * mult, 1),
            "surface_runoff_mm": round(59.8 * mult, 1),
            "max_water_depth_cm": round(85.0 * mult, 1),
            "surcharge_active": True if mult >= 0.5 else False
        },
        "spatial_node_predictions": [
            {
                "id": "NODE_DWARKA_MOR_METRO",
                "name": "Dwarka Mor Metro Crossing",
                "lat": 28.6186, "lng": 77.0319,
                "elevation_m": 211.2,
                "water_depth_cm": round(40.3 * mult, 1),
                "hazard_level": "SEVERE" if mult >= 0.8 else "SAFE",
                "is_surcharged": True if mult >= 0.5 else False
            },
            {
                "id": "NODE_KAKROLA_UNDERPASS",
                "name": "Kakrola Mod Underpass",
                "lat": 28.6120, "lng": 77.0250,
                "elevation_m": 209.5,
                "water_depth_cm": round(85.0 * mult, 1),
                "hazard_level": "CRITICAL" if mult >= 0.8 else "SAFE",
                "is_surcharged": True if mult >= 0.5 else False
            }
        ]
    }

class handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
                    "title": "Urban Flood Nowcasting System REST API (SIH 2026)",
                    "version": "1.0.0",
                    "description": "REST API for 0-3 hour street-level flood depth prediction, drainage graph topology, and flood-safe navigation routing."
                },
                "paths": {
                    "/api/nowcast": {
                        "get": {
                            "summary": "Get Live Street Water Depth Nowcast",
                            "parameters": [
                                {"name": "lead_time_mins", "in": "query", "type": "integer", "default": 60}
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
                            "summary": "Calculate Flood-Safe Alternative Detour Route",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/alert-broadcast": {
                        "post": {
                            "summary": "Broadcast Emergency Flood Alert to NDRF, Traffic Police & DMRC",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    }
                }
            }
            self._send_json(openapi_spec)
            return

        elif 'nowcast' in path:
            lead_time = int(query.get('lead_time_mins', [60])[0])
            self._send_json(get_nowcast(lead_time))
            return

        elif 'drainage-network' in path:
            network = {
                "nodes": [
                    {"id": "NODE_UTTAM_NAGAR_W", "name": "Uttam Nagar West", "elevation_m": 218.2, "lat": 28.6210, "lng": 77.0420},
                    {"id": "NODE_DWARKA_MOR_METRO", "name": "Dwarka Mor Metro Crossing", "elevation_m": 211.2, "lat": 28.6186, "lng": 77.0319},
                    {"id": "NODE_KAKROLA_UNDERPASS", "name": "Kakrola Mod Underpass", "elevation_m": 209.5, "lat": 28.6120, "lng": 77.0250},
                    {"id": "NODE_SEC14_METRO", "name": "Sector 14 Metro Station", "elevation_m": 212.8, "lat": 28.6022, "lng": 77.0260}
                ]
            }
            self._send_json(network)
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

        if 'navigate' in path:
            response_data = {
                "routing_engine": "OSRM / Valhalla Dynamic Hydraulics Engine",
                "origin": body.get("origin", [28.6210, 77.0420]),
                "destination": body.get("destination", [28.5910, 77.0610]),
                "recommended_safe_detour": {
                    "name": "Flood-Safe Detour via Pankha Road & Dabri Flyover",
                    "status": "SAFE",
                    "max_water_depth_cm": 2.0,
                    "hazard_level": "SAFE",
                    "estimated_time_mins": 14
                }
            }
            self._send_json(response_data)
        elif 'alert-broadcast' in path:
            alert_payload = {
                "alert_status": "BROADCASTED",
                "timestamp_epoch": int(time.time()),
                "target_location": body.get("target_location", "Dwarka Mor Metro Crossing"),
                "severity": "RED_CRITICAL_EMERGENCY"
            }
            self._send_json(alert_payload)
        else:
            self._send_json({"error": "POST Endpoint not found"}, 404)

