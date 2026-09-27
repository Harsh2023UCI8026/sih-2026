"""Construct a drainage graph from fetched OSM GeoJSON for a given preset."""

import os
import json
import math
from utils_config import get_zone_config, cache_path

def build_graph(preset: str, geojson_path: str, workspace_dir: str):
    if not os.path.exists(geojson_path):
        print(f"Error: GeoJSON not found at {geojson_path}")
        print(f"Run `python src/fetch_delhi_osm.py --preset {preset}` first.")
        return
        
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    features = data.get("features", [])
    
    nodes = []
    edges = []
    
    node_coords_map = {} # (lon, lat) -> node_id
    
    def get_or_create_node(coord):
        lon, lat = coord[0], coord[1]
        key = (round(lon, 6), round(lat, 6))
        if key not in node_coords_map:
            node_id = f"NODE_{len(nodes):04d}"
            node_coords_map[key] = node_id
            nodes.append({
                "id": node_id,
                "lat": lat,
                "lon": lon,
                "elevation_rim_m": 215.0, # Default, in a real pipeline we'd sample DEM
                "inflow_catchment_sqm": 50000.0,
                "is_outfall": False
            })
        return node_coords_map[key]
        
    for feat in features:
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})
        
        if geom.get("type") == "LineString":
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            closed_loop = coords[0] == coords[-1]
                
            src_node = get_or_create_node(coords[0])
            tgt_node = get_or_create_node(coords[-1])
            
            lat_mid = (coords[0][1] + coords[-1][1]) / 2.0
            dx = (coords[-1][0] - coords[0][0]) * 111000 * math.cos(math.radians(lat_mid))
            dy = (coords[-1][1] - coords[0][1]) * 111000
            dist_m = math.sqrt(dx**2 + dy**2)
            
            # Simple variable catchment estimation based on edge length
            # Assuming a 150m tributary strip width draining into the line
            catchment_sqm = max(1000.0, dist_m * 150.0)
            
            w_str = props.get("width")
            h_str = props.get("height")
            d_str = props.get("diameter")
            
            is_estimated = False
            if w_str and h_str:
                w = float(w_str)
                h = float(h_str)
            elif w_str:
                w = float(w_str)
                h = w * 0.8 # Assume rectangular or slightly flat
            elif d_str:
                w = float(d_str)
                h = float(d_str)
            else:
                is_estimated = True
                # Rational-method heuristic: cross-sectional area scales with sqrt(catchment)
                # k ~ 0.01. So for 10,000 sqm -> sqrt=100 -> area ~ 1.0 sqm
                est_area = 0.01 * math.sqrt(catchment_sqm)
                w = max(0.3, math.sqrt(est_area))
                h = max(0.3, w * 0.8)
                
            edge_id = f"EDGE_{preset.upper()}_{len(edges):04d}"
            
        # Determine edge type, handling natural water specially
        if props.get("waterway"):
            edge_type = props["waterway"]
        elif props.get("natural") == "water":
            if props.get("water") in ("river", "canal"):
                edge_type = props["water"]
            else:
                # For other natural water (e.g., storage), we already handled closed loops above.
                # If not a closed loop, treat as generic drain
                edge_type = "drain"
        else:
            edge_type = "drain"

        edges.append({
            "id": edge_id,
            "source": src_node,
            "target": tgt_node,
            "type": edge_type,
            "length_m": max(dist_m, 1.0),
            "width_m": round(w, 2),
            "height_m": round(h, 2),
            "catchment_sqm": round(catchment_sqm, 2),
            "mannings_n": 0.015,
            "blockage_factor": 0.5,
            "geometry_estimated": is_estimated,
            "geometry_source": "rational_method_fallback" if is_estimated else "osm_tags"
        })
            
    if nodes:
        nodes[-1]["is_outfall"] = True
        nodes[-1]["elevation_rim_m"] = 210.0
        
    graph_data = {
        "network_name": f"{preset} Drainage Graph",
        "spatial_crs": "EPSG:4326",
        "nodes": nodes,
        "edges": edges,
    }
    
    out_json_path = os.path.join(workspace_dir, f"{preset}_drainage_graph.json")
    with open(out_json_path, 'w', encoding='utf-8') as jf:
        json.dump(graph_data, jf, indent=2)
        
    print(f"[SUCCESS] Constructed graph for {preset}: {out_json_path}")
    print(f"          {len(nodes)} Nodes, {len(edges)} Edges.")

if __name__ == "__main__":
    bbox, preset, endpoints = get_zone_config("Construct drainage graph from OSM GeoJSON")
    out_filename = "palam_catchment.geojson" if preset == "test_zone" else f"{preset}_osm_drains.geojson"
    geojson_path = str(cache_path("osm", out_filename))
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    build_graph(preset, geojson_path, current_dir)
