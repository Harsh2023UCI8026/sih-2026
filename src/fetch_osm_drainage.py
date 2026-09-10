import json
import urllib.request
import urllib.parse
import os

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(WORKSPACE_DIR, "dwarka_osm_drains.geojson")

def fetch_dwarka_osm_drains():
    """
    Fetches real-world OpenStreetMap vector stormwater drains, canals, and manholes
    for the Dwarka Mor pilot catchment bounding box (28.59N to 28.63N, 77.01E to 77.05E).
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass QL Query for Dwarka Catchment Bounding Box
    # (south, west, north, east) = (28.5900, 77.0150, 28.6300, 77.0500)
    bbox = "28.5900,77.0150,28.6300,77.0500"
    
    query = f"""
    [out:json][timeout:30];
    (
      way["waterway"="canal"]({bbox});
      way["waterway"="drain"]({bbox});
      way["waterway"="ditch"]({bbox});
      node["manhole"="drain"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    
    print("[INFO] Querying OpenStreetMap Overpass API for Dwarka Mor stormwater drains...")
    
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req = urllib.request.Request(overpass_url, data=data, headers={'User-Agent': 'UrbanFloodNowcasting/1.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        elements = result.get('elements', [])
        nodes_dict = {}
        features = []
        
        # Build node lookup table
        for elem in elements:
            if elem['type'] == 'node':
                nodes_dict[elem['id']] = (elem['lon'], elem['lat'])
                if 'tags' in elem and elem['tags'].get('manhole') == 'drain':
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": f"node_{elem['id']}",
                            "name": elem['tags'].get('name', 'Storm Drain Inlet'),
                            "type": "drain_inlet"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [elem['lon'], elem['lat']]
                        }
                    })

        # Build way (line) features
        for elem in elements:
            if elem['type'] == 'way' and 'nodes' in elem:
                coords = [nodes_dict[nid] for nid in elem['nodes'] if nid in nodes_dict]
                if len(coords) >= 2:
                    tags = elem.get('tags', {})
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": f"way_{elem['id']}",
                            "name": tags.get('name', tags.get('waterway', 'Storm Drain Channel')),
                            "waterway_type": tags.get('waterway', 'drain')
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coords
                        }
                    })

        geojson = {
            "type": "FeatureCollection",
            "name": "Dwarka_OSM_Stormwater_Drains",
            "features": features
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
            
        print(f"[SUCCESS] Extracted {len(features)} stormwater features to {OUTPUT_FILE}")
        return geojson
        
    except Exception as e:
        print(f"[ERROR] Overpass API Query failed: {e}")
        return None

if __name__ == "__main__":
    fetch_dwarka_osm_drains()
