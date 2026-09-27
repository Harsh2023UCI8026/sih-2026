"""Fetch OSM drainage features for a given preset."""
import json
from pathlib import Path
from typing import Dict, List, Tuple
from utils_config import cache_path, get_zone_config, retry

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TILE_SIZE_DEG = 0.02

def tile_bbox(bbox: List[float]) -> List[Tuple[float, float, float, float]]:
    min_lon, min_lat, max_lon, max_lat = bbox
    tiles = []
    lon = min_lon
    while lon < max_lon:
        next_lon = min(lon + TILE_SIZE_DEG, max_lon)
        lat = min_lat
        while lat < max_lat:
            next_lat = min(lat + TILE_SIZE_DEG, max_lat)
            tiles.append((lon, lat, next_lon, next_lat))
            lat = next_lat
        lon = next_lon
    return tiles

def build_query(tile: Tuple[float, float, float, float]) -> str:
    (lon1, lat1, lon2, lat2) = tile
    bbox_str = f"{lat1},{lon1},{lat2},{lon2}"
    tags = ["man_made=storm_drain", "manhole=drain", "waterway=drain", "waterway=canal", "natural=water"]
    query_parts = ["[out:json][timeout:300];", "("]
    for tag in tags:
        query_parts.append(f"node[{tag}]({bbox_str});")
        query_parts.append(f"way[{tag}]({bbox_str});")
    query_parts.append(");")
    query_parts.append("out meta geom;")
    return "".join(query_parts)

def request_post(query: str):
    import requests
    headers = {"User-Agent": "SIH-2026-UrbanFloodNowcasting/1.0"}
    # Increased timeout for large tiles
    return requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=610)

def fetch_tile(tile: Tuple[float, float, float, float], cache_file: Path) -> Dict:
    if cache_file.is_file():
        with cache_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    # Build query for this tile
    query = build_query(tile)

    # Define a helper that performs the request and validates the response
    def _request_and_validate():
        resp = request_post(query)
        if resp.status_code >= 500:
            raise Exception(f"Overpass server error {resp.status_code}")
        ct = resp.headers.get('Content-Type', '')
        if 'application/json' not in ct:
            raise Exception(f"Unexpected content type {ct}")
        return resp

    # Use retry on the combined request/validation step
    try:
        response = retry(_request_and_validate, max_attempts=3, backoff=2)
    except Exception as e:
        print(f"[WARN] Tile fetch failed after retries: {e}. Skipping this tile.")
        # Return empty structure so downstream parsing yields no features
        data = {"elements": []}
        # No caching for failed tile
        return data

    # Parse JSON (should succeed after validation)
    data = response.json()


    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return data

def node_feature(el: Dict) -> Dict:
    return {"type": "Feature", "properties": el.get("tags", {}),
            "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]}}

def way_feature(el: Dict, node_lookup: Dict[int, Tuple[float, float]]) -> Dict:
    if "geometry" in el:
        coords = [[pt["lon"], pt["lat"]] for pt in el["geometry"]]
    else:
        coords = [node_lookup[nid] for nid in el["nodes"] if nid in node_lookup]
    return {"type": "Feature", "properties": el.get("tags", {}),
            "geometry": {"type": "LineString", "coordinates": coords}}

def parse_overpass(data: Dict) -> List[Dict]:
    elements = data.get("elements", [])
    node_lookup = {el["id"]: (el["lon"], el["lat"]) for el in elements if el["type"] == "node"}
    features = []
    for el in elements:
        if el["type"] == "node":
            features.append(node_feature(el))
        elif el["type"] == "way":
            if not el.get("geometry") and not all(nid in node_lookup for nid in el.get("nodes", [])):
                continue
            features.append(way_feature(el, node_lookup))
    return features

def merge_features(all_features: List[Dict]) -> Dict:
    return {"type": "FeatureCollection", "features": all_features}

def main() -> None:
    bbox, preset, endpoints = get_zone_config("Fetch OSM drainage features")
    out_filename = "palam_catchment.geojson" if preset == "test_zone" else f"{preset}_osm_drains.geojson"
    out_path = cache_path("osm", out_filename)
    tiles = tile_bbox(bbox)
    all_features: List[Dict] = []
    for idx, tile in enumerate(tiles):
        tile_cache = cache_path("osm", f"{preset}_tile_{idx}.json")
        data = fetch_tile(tile, tile_cache)
        feats = parse_overpass(data)
        all_features.extend(feats)
        # Log per-tile result
        tile_status = "cached" if tile_cache.is_file() else "fetched"
        print(f"[INFO] Tile {idx}: {len(feats)} features ({tile_status})")
    merged = merge_features(all_features)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_features)} features to {out_path}")

if __name__ == "__main__":
    main()
