import json
import random

with open("src/test_zone_drainage_graph.json", "r") as f:
    graph = json.load(f)

edges = graph["edges"]
nodes = {n["id"]: n for n in graph["nodes"]}

# 1. 10 random edges
print("--- 10 RANDOM PALAM EDGES ---")
sample_edges = random.sample(edges, min(10, len(edges)))
for e in sample_edges:
    w = e.get("width_m")
    h = e.get("height_m")
    print(f"Edge {e['id']}: width={w}, height={h}, length={e.get('length_m'):.2f}")

# 2. Check defaults
default_count = 0
for e in edges:
    if e.get("width_m") == 1.5 and e.get("height_m") == 1.5:
        default_count += 1

print(f"\nTotal Edges: {len(edges)}")
print(f"Edges with default 1.5x1.5m geometry: {default_count}")
