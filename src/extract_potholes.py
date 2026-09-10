import csv
import json
import os

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
VASHU_CSV = os.path.join(WORKSPACE_DIR, "vashu.csv")
OUTPUT_JSON = os.path.join(WORKSPACE_DIR, "pothole_depression_registry.json")

def extract_pothole_depression_data():
    """
    Extracts authentic micro-topography road depression & pothole waterlogging hotspots
    from vashu.csv (verified Delhi Govt / PWD / Traffic Police ground-truth dataset).
    """
    print("[INFO] Extracting authentic Pothole & Road Depression data from vashu.csv...")
    
    if not os.path.exists(VASHU_CSV):
        print(f"[ERROR] {VASHU_CSV} not found!")
        return None

    depressions = []
    with open(VASHU_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('latitude') or not row.get('longitude'):
                continue
            
            try:
                lat = float(row['latitude'])
                lng = float(row['longitude'])
                elev = float(row.get('elevation_m') or 215.0)
                observed_depth = float(row.get('water_depth_cm') or 0.0)
                is_waterlogged = int(row.get('waterlogging_observed') or 0)
                
                if is_waterlogged == 1 and observed_depth > 0:
                    depressions.append({
                        "event_id": row.get('event_id'),
                        "location_name": row.get('location_name'),
                        "sector": row.get('sector'),
                        "latitude": lat,
                        "longitude": lng,
                        "elevation_m": elev,
                        "observed_water_depth_cm": observed_depth,
                        "severity": row.get('severity', 'High'),
                        "drain_overflow": int(row.get('drain_overflow') or 0),
                        "traffic_impact": int(row.get('traffic_impact') or 0),
                        "infrastructure_impact": int(row.get('infrastructure_impact') or 0),
                        "pothole_depression_factor_s": round(max(0.1, (218.0 - elev) * 0.12), 2),
                        "mannings_n_clogged": 0.022 if int(row.get('drain_overflow') or 0) == 1 else 0.015,
                        "source_type": row.get('source_type'),
                        "source_url": row.get('source_url'),
                        "notes": row.get('notes')
                    })
            except ValueError:
                continue

    registry = {
        "dataset_title": "Dwarka Verified Micro-Depression & Pothole Ground-Truth Registry",
        "source_file": "vashu.csv",
        "total_verified_hotspots": len(depressions),
        "hotspots": depressions
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as jf:
        json.dump(registry, jf, indent=2)

    print(f"[SUCCESS] Extracted {len(depressions)} verified road depression/pothole hotspots to {OUTPUT_JSON}")
    return registry

if __name__ == "__main__":
    extract_pothole_depression_data()
