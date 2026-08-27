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
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if 'nowcast' in path:
            lead_time = int(query.get('lead_time_mins', [60])[0])
            self.wfile.write(json.dumps(get_nowcast(lead_time), indent=2).encode('utf-8'))
        else:
            self.wfile.write(json.dumps({"status": "SIH 2026 Flood Nowcasting Serverless API Active"}, indent=2).encode('utf-8'))
        return
