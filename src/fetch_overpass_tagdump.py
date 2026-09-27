#!/usr/bin/env python
import sys, json, requests, re

def fetch_and_dump(bbox):
    # bbox: min_lon,min_lat,max_lon,max_lat
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"[out:json][timeout:300];(node({bbox});way({bbox}););out meta geom;"
    resp = requests.post(overpass_url, data={"data": query}, headers={"User-Agent": "SIH-2026-TagDump"}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    elements = data.get('elements', [])
    print(f"TOTAL_ELEMENTS {len(elements)}")
    pattern = re.compile(r"drain|water|storm|sewer|canal|culvert", re.IGNORECASE)
    matching = []
    for el in elements:
        tags = el.get('tags', {})
        if not tags:
            continue
        for k, v in tags.items():
            if pattern.search(k) or pattern.search(v):
                matching.append(tags)
                break
    print(f"MATCHING_ELEMENTS {len(matching)}")
    for tags in matching[:10]:
        print(json.dumps(tags, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: script.py BBOX(min_lon,min_lat,max_lon,max_lat)")
        sys.exit(1)
    fetch_and_dump(sys.argv[1])
