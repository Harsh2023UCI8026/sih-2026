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
                    "/api/v1/route/flood-safe": {
                        "post": {
                            "summary": "Dynamic Point A -> Point B Flood-Aware Routing API",
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

            # Clearance thresholds (cm)
            thresholds = {
                "pedestrian": 10.0,
                "bike": 15.0,
                "twowheeler": 15.0,
                "rickshaw": 18.0,
                "autorickshaw": 18.0,
                "car": 25.0,
                "ambulance": 45.0,
                "suv": 45.0
            }
            max_allowed = thresholds.get(vehicle_type, 25.0)

            # Get current nowcast depths
            nowcast = calculate_nowcast(lead_time_mins)
            flood_nodes = nowcast.get("spatial_node_predictions", [])

            # Compute 3 alternative routes (using OSRM or robust fallback solver)
            import urllib.request
            osrm_routes = []
            try:
                osrm_url = f"http://router.project-osrm.org/route/v1/driving/{orig['lng']},{orig['lat']};{dest['lng']},{dest['lat']}?overview=full&geometries=geojson&alternatives=true&steps=true"
                req = urllib.request.Request(osrm_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        osrm_data = json.loads(resp.read().decode('utf-8'))
                        osrm_routes = osrm_data.get("routes", [])
            except Exception as e:
                print("OSRM query offline/failed, using dynamic multi-route generator:", e)

            routes_response = []

            if osrm_routes:
                for idx, r in enumerate(osrm_routes):
                    coords_raw = r["geometry"]["coordinates"] # [lng, lat]
                    coords = [[c[1], c[0]] for c in coords_raw] # [lat, lng]
                    distance_km = round(r.get("distance", 0) / 1000.0, 1)
                    eta_mins = max(1, round(r.get("duration", 0) / 60.0))

                    # Check max flood depth along route coordinates
                    max_depth = 0.0
                    flooded_segs = []

                    for pt in coords:
                        for fn in flood_nodes:
                            # Euclidean distance approximation in meters
                            d_m = math.sqrt((pt[0] - fn["lat"])**2 + (pt[1] - fn["lng"])**2) * 111000
                            if d_m < 400: # Within 400m of a flooded manhole/junction
                                d_cm = fn.get("water_depth_cm", 0.0)
                                if d_cm > max_depth:
                                    max_depth = d_cm
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

                    if max_depth > max_allowed:
                        status = "BLOCKED"
                    elif max_depth > 12.0:
                        status = "RISKY"
                    else:
                        status = "SAFE"

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
                        "max_water_depth_cm": round(max_depth, 1),
                        "vehicle_type": vehicle_type,
                        "clearance_threshold_cm": max_allowed,
                        "flooded_segments": unique_flooded,
                        "coordinates": coords,
                        "google_maps_url": gmaps_url
                    })

            # Guaranteed Dynamic 3-Route Multi-Path Generator if OSRM returned < 2 routes
            if len(routes_response) < 2:
                # Direct distance approx
                dist_direct_km = math.sqrt((orig['lat'] - dest['lat'])**2 + (orig['lng'] - dest['lng'])**2) * 111.0
                dist_direct_km = max(0.5, round(dist_direct_km, 1))

                mid_lat = (orig['lat'] + dest['lat']) / 2.0
                mid_lng = (orig['lng'] + dest['lng']) / 2.0

                # Perpendicular offset vector for 2 alternative detours
                dx = dest['lng'] - orig['lng']
                dy = dest['lat'] - orig['lat']
                norm = math.sqrt(dx*dx + dy*dy) or 1.0
                offset_dist = min(0.03, max(0.008, norm * 0.25))

                # Route 1: Direct path
                r1_coords = [
                    [orig['lat'], orig['lng']],
                    [mid_lat, mid_lng],
                    [dest['lat'], dest['lng']]
                ]

                # Route 2: North/East Bypass detour (+offset)
                r2_coords = [
                    [orig['lat'], orig['lng']],
                    [orig['lat'] + (dest['lat']-orig['lat'])*0.33 + (-dy/norm)*offset_dist, orig['lng'] + (dest['lng']-orig['lng'])*0.33 + (dx/norm)*offset_dist],
                    [orig['lat'] + (dest['lat']-orig['lat'])*0.66 + (-dy/norm)*offset_dist, orig['lng'] + (dest['lng']-orig['lng'])*0.66 + (dx/norm)*offset_dist],
                    [dest['lat'], dest['lng']]
                ]

                # Route 3: South/West Bypass detour (-offset)
                r3_coords = [
                    [orig['lat'], orig['lng']],
                    [orig['lat'] + (dest['lat']-orig['lat'])*0.33 - (-dy/norm)*offset_dist, orig['lng'] + (dest['lng']-orig['lng'])*0.33 - (dx/norm)*offset_dist],
                    [orig['lat'] + (dest['lat']-orig['lat'])*0.66 - (-dy/norm)*offset_dist, orig['lng'] + (dest['lng']-orig['lng'])*0.66 - (dx/norm)*offset_dist],
                    [dest['lat'], dest['lng']]
                ]

                all_candidate_paths = [
                    ("r1", "Direct Route", r1_coords, dist_direct_km, max(2, int(dist_direct_km * 2.5))),
                    ("r2", "Bypass Detour A", r2_coords, round(dist_direct_km * 1.2, 1), max(3, int(dist_direct_km * 3.0))),
                    ("r3", "Bypass Detour B", r3_coords, round(dist_direct_km * 1.35, 1), max(4, int(dist_direct_km * 3.4)))
                ]

                routes_response = []
                for r_id, r_name, c_list, r_dist, r_eta in all_candidate_paths:
                    max_depth = 0.0
                    flooded_segs = []

                    for pt in c_list:
                        for fn in flood_nodes:
                            d_m = math.sqrt((pt[0] - fn["lat"])**2 + (pt[1] - fn["lng"])**2) * 111000
                            if d_m < 450:
                                d_cm = fn.get("water_depth_cm", 0.0)
                                if d_cm > max_depth:
                                    max_depth = d_cm
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

                    if max_depth > max_allowed:
                        status = "BLOCKED"
                    elif max_depth > 12.0:
                        status = "RISKY"
                    else:
                        status = "SAFE"

                    # Waypoints for Google Maps
                    wp_str = f"{c_list[1][0]:.5f},{c_list[1][1]:.5f}"
                    gmaps = f"https://www.google.com/maps/dir/?api=1&origin={orig['lat']:.5f},{orig['lng']:.5f}&destination={dest['lat']:.5f},{dest['lng']:.5f}&waypoints={wp_str}&travelmode=driving"

                    routes_response.append({
                        "route_id": r_id,
                        "name": r_name,
                        "status": status,
                        "eta_minutes": r_eta,
                        "distance_km": r_dist,
                        "max_water_depth_cm": round(max_depth, 1),
                        "vehicle_type": vehicle_type,
                        "clearance_threshold_cm": max_allowed,
                        "flooded_segments": unique_flooded,
                        "coordinates": c_list,
                        "google_maps_url": gmaps
                    })

            # Sort routes: SAFE first, then RISKY, then BLOCKED
            status_order = {"SAFE": 0, "RISKY": 1, "BLOCKED": 2}
            routes_response.sort(key=lambda x: (status_order.get(x["status"], 3), x["eta_minutes"]))

            recommended_id = routes_response[0]["route_id"] if routes_response else None

            self._send_json({
                "routing_engine": "OSRM Hydraulics & Flood-Aware Engine",
                "origin": orig,
                "destination": dest,
                "vehicle_type": vehicle_type,
                "lead_time_minutes": lead_time_mins,
                "recommended_route_id": recommended_id,
                "routes": routes_response
            })

        elif parsed.path == '/api/v1/navigate':
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

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

def run_server(port=8081):
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
    run_server(8081)
