# src/run_hydraulic_24h.py
"""Run the hydraulic model for a 24-hour period and print diagnostics + table.

Usage:  python src/run_hydraulic_24h.py [DATE]
        DATE defaults to 2021-08-08.
"""

import csv, os, sys

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src import hydraulic_model as hm

CSV_PATH = os.path.join(
    WORKSPACE_ROOT, "archive", "training_data",
    "processed_dwarka_hourly_rainfall.csv",
)


def load_rows_for_date(csv_path: str, date_prefix: str):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["time"].startswith(date_prefix):
                rows.append(row)
    return rows


def run(target_date: str):
    rows = load_rows_for_date(CSV_PATH, target_date)
    if not rows:
        print(f"No data found for {target_date}")
        return

    # Diagnostics
    edge_info = hm.get_representative_edge_info()
    cap_mmhr, catch_sqm, bf = hm._manning_capacity_mmhr(edge_info["edge_id"])
    print(f"\n=== Hydraulic Model Test: {target_date} ===")
    print("--- Representative Edge Diagnostics ---")
    print(f"Edge ID            : {edge_info['edge_id']}")
    print(f"Geometry type      : {edge_info['geometry_type']}")
    print(f"Width (m)          : {edge_info.get('width_m')}")
    print(f"Height (m)         : {edge_info.get('height_m')}")
    print(f"Diameter (m)       : {edge_info.get('diameter_m')}")
    print(f"Manning's n        : {edge_info.get('mannings_n')}")
    print(f"Blockage factor    : {bf}  (assumed={edge_info.get('blockage_factor_assumed')})")
    print(f"Effective capacity : {cap_mmhr:.2f} mm/hr")
    print(f"Catchment area     : {catch_sqm:.0f} sqm")
    print(f"Contributing frac  : {edge_info.get('contributing_fraction')}  (assumed={edge_info.get('contributing_fraction_assumed')})")
    print(f"Ponding area       : {edge_info.get('ponding_area_sqm')} sqm  (assumed={edge_info.get('ponding_area_assumed')})\n")

    print("time             | rain_mm | depth_cm | surcharge_flag | flood_hazard_level")
    print("---------------- | ------- | -------- | -------------- | ------------------")
    for row in rows:
        depth_cm, flag, level = hm.compute_water_depth(row)
        print(f"{row['time']} | {float(row['rain_mm']):7.1f} | {depth_cm:8.2f} | {flag:14d} | {level}")


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2021-08-08"
    run(date)
