import json
import urllib.request
import os
import argparse
from utils_config import get_zone_config, cache_path, retry

def generate_grid(bbox):
    """Generate a 5x5 grid of lat/lon points within the given bbox.
    Returns a list of dicts with 'latitude' and 'longitude' keys.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    steps = 5
    lat_step = (max_lat - min_lat) / (steps - 1)
    lon_step = (max_lon - min_lon) / (steps - 1)
    locations = []
    for i in range(steps):
        for j in range(steps):
            lat = round(min_lat + i * lat_step, 4)
            lon = round(min_lon + j * lon_step, 4)
            locations.append({"latitude": lat, "longitude": lon})
    return locations

def fetch_elevation_grid(preset: str):
    """Fetch elevation data for the given preset and write to a preset‑specific JSON file.
    The output file is stored under ``cache/dem/<preset>_elevation_grid.json``.
    """
    # Load bbox directly from config using load_config
    from utils_config import load_config
    cfg = load_config(preset)
    bbox = cfg['bbox']
    print(f"[INFO] Fetching DEM for preset '{preset}' with bbox {bbox}")
    locations = generate_grid(bbox)
    payload = json.dumps({"locations": locations}).encode('utf-8')
    url = "https://api.open-elevation.com/api/v1/lookup"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "UrbanFloodNowcasting/1.0"}
    )
    output_path = cache_path("dem", f"{preset}_elevation_grid.json")
    # Define a helper for the request with validation
    def _make_request():
        with urllib.request.urlopen(req, timeout=120) as response:
            ct = response.headers.get('Content-Type', '')
            if 'application/json' not in ct:
                raise Exception(f"Unexpected content type {ct}")
            return json.loads(response.read().decode('utf-8'))
    # Retry on network errors or validation failures
    try:
        res_data = retry(_make_request, max_attempts=3, backoff=2)
        results = res_data.get('results', [])
        dataset = {
            "source": "Open-Elevation API lookup",
            "data_quality": "REMOTE_PROVIDER_RESPONSE_NOT_INDEPENDENTLY_VALIDATED",
            "notice": "The API response and vertical accuracy have not been independently checked for this pilot.",
            "bounding_box": f"{bbox[1]},{bbox[0]} to {bbox[3]},{bbox[2]}",
            "total_sample_points": len(results),
            "elevation_points": results
        }
    except Exception as e:
        print(f"[WARN] Open-Elevation API offline or rate‑limited ({e}). Generating fallback dataset...")
        min_lon, min_lat, max_lon, max_lat = bbox
        fallback = []
        for loc in locations:
            elev = 200 + (loc["latitude"] - min_lat) * 10 + (loc["longitude"] - min_lon) * 5
            fallback.append({"latitude": loc["latitude"], "longitude": loc["longitude"], "elevation_msl_m": round(elev, 1)})
        dataset = {
            "source": "Synthetic fallback elevation formula",
            "data_kind": "synthetic_fallback",
            "data_quality": "SYNTHETIC_NOT_MEASURED",
            "notice": "These generated values are not DEM measurements and must not be used as elevation observations.",
            "bounding_box": f"{bbox[1]},{bbox[0]} to {bbox[3]},{bbox[2]}",
            "total_sample_points": len(fallback),
            "elevation_points": fallback
        }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    print(f"[SUCCESS] Saved {len(dataset['elevation_points'])} elevation points to {output_path}")
    return dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch DEM for a preset")
    parser.add_argument('--preset', type=str, required=True, help='Preset name from config.yaml')
    args = parser.parse_args()
    fetch_elevation_grid(args.preset)
