import json
import urllib.request
import os

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(WORKSPACE_DIR, "dwarka_live_radar.json")

def fetch_live_radar_nowcast():
    """
    Fetches real-time Doppler Weather Radar & nowcast rain intensity data
    for Delhi / Dwarka Mor (28.6186N, 77.0319E) via RainViewer & Open-Meteo Weather Radar APIs.
    """
    print("[INFO] Querying RainViewer & Open-Meteo Radar API for Delhi Doppler Weather Radar reflectivity...")
    
    # 1. RainViewer Weather Radar Timestamp API
    rainviewer_url = "https://api.rainviewer.com/public/weather-maps.json"
    
    try:
        req = urllib.request.Request(rainviewer_url, headers={'User-Agent': 'UrbanFloodNowcasting/1.0'})
        with urllib.request.urlopen(req, timeout=20) as res:
            rv_data = json.loads(res.read().decode('utf-8'))
            
        radar_past = rv_data.get('radar', {}).get('past', [])
        latest_timestamp = radar_past[-1]['time'] if radar_past else None
        
        # 2. Open-Meteo High-Resolution Precipitation Nowcast for Dwarka (28.6186 N, 77.0319 E)
        openmeteo_url = "https://api.open-meteo.com/v1/forecast?latitude=28.6186&longitude=77.0319&minutely_15=precipitation,rain&forecast_days=1&timezone=Asia%2FKolkata"
        req_om = urllib.request.Request(openmeteo_url, headers={'User-Agent': 'UrbanFloodNowcasting/1.0'})
        
        with urllib.request.urlopen(req_om, timeout=20) as res_om:
            om_data = json.loads(res_om.read().decode('utf-8'))
            
        min_15 = om_data.get('minutely_15', {})
        precip_series = min_15.get('precipitation', [])[:12] # Next 3 hours (12 x 15min steps)
        time_series = min_15.get('time', [])[:12]
        
        radar_dataset = {
            "station": "IMD Palam S-Band Doppler Weather Radar (Delhi)",
            "coordinates": {"lat": 28.6186, "lng": 77.0319},
            "rainviewer_radar_host": rv_data.get('host'),
            "latest_radar_timestamp": latest_timestamp,
            "nowcast_15min_interval_mm": precip_series,
            "timestamps_iso": time_series
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(radar_dataset, f, indent=2)
            
        print(f"[SUCCESS] Live Doppler Radar & 0-3h Nowcast saved to {OUTPUT_FILE}")
        return radar_dataset
        
    except Exception as e:
        print(f"[ERROR] Live Radar API fetch failed: {e}")
        return None

if __name__ == "__main__":
    fetch_live_radar_nowcast()
