import os
import json

def build_dwarka_drainage_graph(workspace_dir):
    """
    Constructs the 1D Directed Graph Topology G = (V, E) of Dwarka Mor Stormwater Drain Network
    as required by the SIH 2026 Problem Statement (MoES / NCMRWF).
    """
    print("Building 1D Directed Graph Topology for Dwarka Mor Drainage System...")
    
    # Graph Nodes (Manholes, Catchment Inlets, Outfalls)
    nodes = [
        {
            "id": "NODE_UTTAM_NAGAR_W",
            "name": "Uttam Nagar West Inlet",
            "type": "catchment_inlet",
            "latitude": 28.6210,
            "longitude": 77.0420,
            "elevation_rim_m": 218.2,
            "elevation_invert_m": 216.5,
            "max_depth_m": 1.7,
            "inflow_catchment_sqm": 85000
        },
        {
            "id": "NODE_NAWADA_CROSSING",
            "name": "Nawada Junction Manhole",
            "type": "junction_manhole",
            "latitude": 28.6198,
            "longitude": 77.0375,
            "elevation_rim_m": 215.5,
            "elevation_invert_m": 213.8,
            "max_depth_m": 1.7,
            "inflow_catchment_sqm": 110000
        },
        {
            "id": "NODE_DWARKA_MOR_METRO",
            "name": "Dwarka Mor Metro Junction (Critical Hotspot)",
            "type": "surcharge_vulnerable_junction",
            "latitude": 28.6186,
            "longitude": 77.0319,
            "elevation_rim_m": 211.2,
            "elevation_invert_m": 209.2,
            "max_depth_m": 2.0,
            "inflow_catchment_sqm": 240000
        },
        {
            "id": "NODE_SEC3_14_CROSSING",
            "name": "Dwarka Sector 3/14 Storm Drain Junction",
            "type": "junction_manhole",
            "latitude": 28.6150,
            "longitude": 77.0300,
            "elevation_rim_m": 211.8,
            "elevation_invert_m": 209.8,
            "max_depth_m": 2.0,
            "inflow_catchment_sqm": 175000
        },
        {
            "id": "NODE_KAKROLA_UNDERPASS",
            "name": "Kakrola Mod Underpass Low-Point",
            "type": "underpass_depression_node",
            "latitude": 28.6120,
            "longitude": 77.0250,
            "elevation_rim_m": 209.5,
            "elevation_invert_m": 207.0,
            "max_depth_m": 2.5,
            "inflow_catchment_sqm": 190000
        },
        {
            "id": "NODE_NAJAFGARH_OUTFALL",
            "name": "Kakrola Regulator (Najafgarh Drain Outfall)",
            "type": "river_outfall",
            "latitude": 28.6100,
            "longitude": 77.0220,
            "elevation_rim_m": 210.5,
            "elevation_invert_m": 206.5,
            "max_depth_m": 4.0,
            "inflow_catchment_sqm": 500000
        }
    ]
    
    # Directed Edges (Pipes, Box Drains, Canals)
    edges = [
        {
            "id": "EDGE_PWD_TRUNK_1",
            "source": "NODE_UTTAM_NAGAR_W",
            "target": "NODE_NAWADA_CROSSING",
            "type": "concrete_box_drain",
            "length_m": 520,
            "width_m": 1.8,
            "height_m": 1.5,
            "mannings_n": 0.013,
            "max_capacity_cumec": 12.5,
            "equivalent_capacity_mmhr": 55.0
        },
        {
            "id": "EDGE_PWD_TRUNK_2",
            "source": "NODE_NAWADA_CROSSING",
            "target": "NODE_DWARKA_MOR_METRO",
            "type": "concrete_box_drain",
            "length_m": 610,
            "width_m": 2.2,
            "height_m": 1.8,
            "mannings_n": 0.013,
            "max_capacity_cumec": 18.0,
            "equivalent_capacity_mmhr": 45.0
        },
        {
            "id": "EDGE_MASTER_DRAIN_SEC3",
            "source": "NODE_DWARKA_MOR_METRO",
            "target": "NODE_SEC3_14_CROSSING",
            "type": "circular_pipe",
            "length_m": 450,
            "diameter_m": 1.5,
            "mannings_n": 0.013,
            "max_capacity_cumec": 15.0,
            "equivalent_capacity_mmhr": 42.0
        },
        {
            "id": "EDGE_KAKROLA_FEEDER",
            "source": "NODE_SEC3_14_CROSSING",
            "target": "NODE_KAKROLA_UNDERPASS",
            "type": "circular_pipe",
            "length_m": 580,
            "diameter_m": 1.8,
            "mannings_n": 0.013,
            "max_capacity_cumec": 22.0,
            "equivalent_capacity_mmhr": 40.0
        },
        {
            "id": "EDGE_NAJAFGARH_DISCHARGE",
            "source": "NODE_KAKROLA_UNDERPASS",
            "target": "NODE_NAJAFGARH_OUTFALL",
            "type": "open_masonry_canal",
            "length_m": 350,
            "width_m": 4.5,
            "height_m": 3.0,
            "mannings_n": 0.018,
            "max_capacity_cumec": 45.0,
            "equivalent_capacity_mmhr": 60.0
        }
    ]
    
    graph_data = {
        "network_name": "Dwarka Mor & Najafgarh Feeder Stormwater Directed Graph",
        "spatial_crs": "EPSG:4326",
        "nodes": nodes,
        "edges": edges,
        "hydraulic_metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "critical_surcharge_node": "NODE_DWARKA_MOR_METRO",
            "outlet_node": "NODE_NAJAFGARH_OUTFALL",
            "najafgarh_drain_fsl_m": 211.5
        }
    }
    
    out_json_path = os.path.join(workspace_dir, "dwarka_drainage_graph.json")
    with open(out_json_path, 'w', encoding='utf-8') as jf:
        json.dump(graph_data, jf, indent=2)
        
    print(f"[OK] Directed Drainage Graph JSON created: {out_json_path}")
    print(f"     Graph contains {len(nodes)} Nodes and {len(edges)} Directed Edges.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    build_dwarka_drainage_graph(current_dir)
