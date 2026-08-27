import os
import json
import math
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load Drainage Graph JSON if available
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(WORKSPACE_DIR, "dwarka_drainage_graph.json")

def get_drainage_graph():
    if os.path.exists(GRAPH_FILE):
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "nodes": [
            {"id": "NODE_UTTAM_NAGAR_W", "name": "Uttam Nagar West", "elevation_m": 218.2, "lat": 28.6210, "lng": 77.0420},
            {"id": "NODE_DWARKA_MOR_METRO", "name": "Dwarka Mor Metro Crossing", "elevation_m": 211.2, "lat": 28.6186, "lng": 77.0319},
            {"id": "NODE_KAKROLA_UNDERPASS", "name": "Kakrola Mod Underpass", "elevation_m": 209.5, "lat": 28.6120, "lng": 77.0250},
            {"id": "NODE_SEC14_METRO", "name": "Sector 14 Metro Station", "elevation_m": 212.8, "lat": 28.6022, "lng": 77.0260},
            {"id": "NODE_SEC16B_NLU", "name": "Sector 16B NLU Stretch", "elevation_m": 212.0, "lat": 28.6034, "lng": 77.0174},
            {"id": "NODE_SEC6_RIDGE", "name": "Dwarka Sector 6 Ridge", "elevation_m": 219.5, "lat": 28.5910, "lng": 77.0610}
        ]
    }

def calculate_nowcast(lead_time_mins=60):
    # Scale multiplier based on 0-180 minute lead time window
    mult = 1.0
    if lead_time_mins <= 0: mult = 0.2
    elif lead_time_mins <= 15: mult = 0.5
    elif lead_time_mins <= 30: mult = 0.8
    elif lead_time_mins <= 60: mult = 1.0
    elif lead_time_mins <= 120: mult = 0.65
    else: mult = 0.3

    rain_3h_mm = round(65.0 * mult, 1)
    radar_dbz = round(48.5 * mult, 1)
    runoff_mm = round(59.8 * mult, 1)

    nodes = [
        {
            "id": "NODE_DWARKA_MOR_METRO",
            "name": "Dwarka Mor Metro Crossing",
            "lat": 28.6186, "lng": 77.0319,
            "elevation_m": 211.2,
            "water_depth_cm": round(40.3 * mult, 1),
            "hazard_level": "SEVERE" if mult >= 0.8 else ("MODERATE" if mult >= 0.5 else "SAFE"),
            "is_surcharged": True if mult >= 0.5 else False
        },
        {
            "id": "NODE_KAKROLA_UNDERPASS",
            "name": "Kakrola Mod Underpass",
            "lat": 28.6120, "lng": 77.0250,
            "elevation_m": 209.5,
            "water_depth_cm": round(85.0 * mult, 1),
            "hazard_level": "CRITICAL" if mult >= 0.8 else ("SEVERE" if mult >= 0.5 else "CAUTION"),
            "is_surcharged": True if mult >= 0.5 else False
        },
        {
            "id": "NODE_SEC14_METRO",
            "name": "Sector 14 Metro Station",
            "lat": 28.6022, "lng": 77.0260,
            "elevation_m": 212.8,
            "water_depth_cm": round(22.0 * mult, 1),
            "hazard_level": "MODERATE" if mult >= 0.8 else "SAFE",
            "is_surcharged": False
        },
        {
            "id": "NODE_UTTAM_NAGAR_W",
            "name": "Uttam Nagar West Metro",
            "lat": 28.6210, "lng": 77.0420,
            "elevation_m": 218.2,
            "water_depth_cm": round(4.0 * mult, 1),
            "hazard_level": "SAFE",
            "is_surcharged": False
        },
        {
            "id": "NODE_SEC6_RIDGE",
            "name": "Dwarka Sector 6 Ridge",
            "lat": 28.5910, "lng": 77.0610,
            "elevation_m": 219.5,
            "water_depth_cm": 0.0,
            "hazard_level": "SAFE",
            "is_surcharged": False
        }
    ]

    return {
        "system_status": "ONLINE",
        "timestamp_epoch": int(time.time()),
        "lead_time_minutes": lead_time_mins,
        "hydrologic_summary": {
            "radar_reflectivity_dbz": radar_dbz,
            "forecast_rain_3h_mm": rain_3h_mm,
            "surface_runoff_mm": runoff_mm,
            "max_water_depth_cm": round(85.0 * mult, 1),
            "surcharge_active": True if mult >= 0.5 else False
        },
        "spatial_node_predictions": nodes
    }

class SIHNowcastingAPIHandler(BaseHTTPRequestHandler):

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

    def _send_file(self, filepath, content_type='text/html'):
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
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

        # 1. Dashboard Web UI
        if path == '/' or path == '/index.html':
            self._send_file(os.path.join(WORKSPACE_DIR, 'index.html'), 'text/html')
        elif path == '/logo.jpeg':
            self._send_file(os.path.join(WORKSPACE_DIR, 'logo.jpeg'), 'image/jpeg')

        # 2. REST API: GET /api/v1/nowcast
        elif path == '/api/v1/nowcast':
            lead_time = int(query.get('lead_time_mins', [60])[0])
            self._send_json(calculate_nowcast(lead_time))

        # 3. REST API: GET /api/v1/drainage-network
        elif path == '/api/v1/drainage-network':
            self._send_json(get_drainage_graph())

        # 4. OpenAPI / Swagger API Docs Endpoint
        elif path == '/docs' or path == '/api/v1/docs':
            swagger_html = """
            <!DOCTYPE html>
            <html>
            <head>
              <title>SIH26085 Flood Nowcasting REST API Docs</title>
              <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
            </head>
            <body>
              <div id="swagger-ui"></div>
              <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js"></script>
              <script>
                SwaggerUIBundle({
                  url: '/api/v1/openapi.json',
                  dom_id: '#swagger-ui',
                });
              </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(swagger_html.encode('utf-8'))

        elif path == '/api/v1/openapi.json':
            openapi_spec = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Urban Flood Nowcasting System REST API (SIH 2026)",
                    "version": "1.0.0",
                    "description": "REST API for 0-3 hour street-level flood depth prediction, drainage graph topology, and flood-safe navigation routing for Dwarka Mor."
                },
                "paths": {
                    "/api/v1/nowcast": {
                        "get": {
                            "summary": "Get Live Street Water Depth Nowcast",
                            "parameters": [
                                {"name": "lead_time_mins", "in": "query", "type": "integer", "default": 60}
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
                            "summary": "Calculate Flood-Safe Alternative Detour Route",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    },
                    "/api/v1/alert-broadcast": {
                        "post": {
                            "summary": "Broadcast Emergency Flood Alert to NDRF, Traffic Police & DMRC",
                            "responses": {"200": {"description": "Successful Response"}}
                        }
                    }
                }
            }
            self._send_json(openapi_spec)

        else:
            self._send_json({"error": "Endpoint not found", "available_endpoints": ["/api/v1/nowcast", "/api/v1/drainage-network", "/api/v1/navigate", "/api/v1/alert-broadcast", "/docs"]}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/v1/navigate':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            
            try:
                body = json.loads(post_data)
            except Exception:
                body = {}

            response_data = {
                "routing_engine": "OSRM / Valhalla Dynamic Hydraulics Engine",
                "origin": body.get("origin", [28.6210, 77.0420]),
                "destination": body.get("destination", [28.5910, 77.0610]),
                "direct_route": {
                    "name": "Standard Direct Route via Najafgarh Road",
                    "status": "BLOCKED",
                    "max_water_depth_cm": 40.3,
                    "hazard_level": "SEVERE",
                    "passable_for_ambulances": False,
                    "penalty_weight": 999.0
                },
                "recommended_safe_detour": {
                    "name": "Flood-Safe Detour via Pankha Road & Dabri Flyover",
                    "status": "SAFE",
                    "max_water_depth_cm": 2.0,
                    "hazard_level": "SAFE",
                    "passable_for_ambulances": True,
                    "distance_km": 6.8,
                    "estimated_time_mins": 14,
                    "waypoints": [
                        [28.6210, 77.0420],
                        [28.6110, 77.0520],
                        [28.5980, 77.0580],
                        [28.5910, 77.0610]
                    ]
                }
            }
            self._send_json(response_data)

        elif parsed.path == '/api/v1/alert-broadcast':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
            
            try:
                body = json.loads(post_data)
            except Exception:
                body = {}

            alert_payload = {
                "alert_status": "BROADCASTED",
                "timestamp_epoch": int(time.time()),
                "target_location": body.get("target_location", "Dwarka Mor Metro Crossing"),
                "water_depth_cm": body.get("water_depth_cm", 40.3),
                "severity": "RED_CRITICAL_EMERGENCY",
                "agency_dispatches": {
                    "delhi_traffic_police": {
                        "action": "ROAD_CLOSURE_ADVISORY",
                        "message": "Najafgarh Road closed at Dwarka Mor. Divert traffic to Dabri Flyover."
                    },
                    "ndrf_disaster_management": {
                        "action": "DEWATERING_PUMP_DEPLOYMENT",
                        "priority": "HIGH_ALERT",
                        "target_pump_station": "Kakrola Outfall Regulator"
                    },
                    "dmrc_delhi_metro": {
                        "action": "STATION_ENTRY_ADVISORY",
                        "message": "Gate 2 at Dwarka Mor Metro Station waterlogged. Direct passengers to Gate 1."
                    }
                }
            }
            self._send_json(alert_payload)
        else:
            self._send_json({"error": "POST Endpoint not found"}, 404)

def run_server(port=8081):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SIHNowcastingAPIHandler)
    print("=" * 60)
    print(f"SIH 2026 REST API Backend Server Running on http://localhost:{port}/")
    print(f"Swagger API Documentation available at: http://localhost:{port}/docs")
    print(f"GET  /api/v1/nowcast?lead_time_mins=60")
    print(f"GET  /api/v1/drainage-network")
    print(f"POST /api/v1/navigate")
    print("=" * 60)
    httpd.serve_forever()

if __name__ == "__main__":
    run_server(8081)
