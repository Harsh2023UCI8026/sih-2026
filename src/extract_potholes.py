"""Convert complete rows from a project-curated incident CSV into an unverified registry.

The source CSV mixes report types and coordinate precision. The output therefore
preserves values entered in the local source CSV and explicitly avoids treating them as measured,
verified ground truth or deriving missing elevations/hydraulic parameters.
"""

import csv
import json
import os

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
VASHU_CSV = os.path.join(WORKSPACE_DIR, "data", "vashu.csv")
OUTPUT_JSON = os.path.join(WORKSPACE_DIR, "data", "pothole_depression_registry.json")


def extract_pothole_depression_data():
    if not os.path.exists(VASHU_CSV):
        print(f"[ERROR] {VASHU_CSV} not found")
        return None

    records = []
    malformed_rows = 0
    with open(VASHU_CSV, "r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"latitude", "longitude", "water_depth_cm", "waterlogging_observed"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Source CSV is missing required columns")

        for row in reader:
            if None in row or any(value is None for value in row.values()) or any(row.get(key) in (None, "") for key in required):
                malformed_rows += 1
                continue
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                listed_depth = float(row["water_depth_cm"])
                observed_flag = int(row["waterlogging_observed"])
            except (TypeError, ValueError):
                malformed_rows += 1
                continue
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                malformed_rows += 1
                continue
            if observed_flag != 1 or listed_depth <= 0:
                continue

            records.append({
                "event_id": row.get("event_id"),
                "event_date": row.get("event_date"),
                "location_name": row.get("location_name"),
                "sector": row.get("sector"),
                "latitude": lat,
                "longitude": lon,
                "coordinate_type_as_listed": row.get("coordinate_type"),
                "coordinate_precision_as_listed": row.get("coordinate_precision"),
                "source_confidence_as_listed": row.get("source_confidence"),
                "registry_depth_estimate_cm": listed_depth,
                "severity_as_listed": row.get("severity"),
                "source_type": row.get("source_type"),
                "source_url": row.get("source_url"),
                "notes": row.get("notes"),
                "validation_status": "NOT_INDEPENDENTLY_VALIDATED",
            })

    registry = {
        "dataset_title": "Project registry of historical flood reports (unverified)",
        "source_file": "vashu.csv",
        "record_count": len(records),
        "malformed_rows_skipped": malformed_rows,
        "depth_semantics": "Estimate entered in the local registry; source support and measurement status have not been independently verified.",
        "hotspots": records,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as output:
        json.dump(registry, output, indent=2, ensure_ascii=False)

    print(f"[OK] Wrote {len(records)} unverified cited records; skipped {malformed_rows} malformed rows.")
    return registry


if __name__ == "__main__":
    extract_pothole_depression_data()
