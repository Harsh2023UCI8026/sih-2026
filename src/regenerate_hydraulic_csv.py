# src/regenerate_hydraulic_csv.py
"""Regenerate the full CSV with hydraulic model outputs.

Reads processed_dwarka_hourly_rainfall.csv (original, untouched),
runs compute_water_depth on every row, and writes
processed_dwarka_hourly_rainfall_hydraulic.csv with updated columns.
"""

import csv, os, sys, math
from collections import Counter

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, WORKSPACE)

from src.hydraulic_model import (
    compute_water_depth, get_representative_edge_info,
    _manning_capacity_mmhr, _DEFAULT_PONDING_AREA_SQM,
    _DEFAULT_BLOCKAGE_FACTOR, _DEFAULT_CONTRIBUTING_FRACTION,
)

INPUT_CSV = os.path.join(WORKSPACE, "archive", "training_data",
                         "processed_dwarka_hourly_rainfall.csv")
OUTPUT_CSV = os.path.join(WORKSPACE, "archive", "training_data",
                          "processed_dwarka_hourly_rainfall_hydraulic.csv")

# Metadata columns (constant for every row — single representative edge)
edge_info = get_representative_edge_info()
META = {
    "blockage_factor": _DEFAULT_BLOCKAGE_FACTOR,
    "blockage_factor_assumed": True,
    "ponding_area_sqm": _DEFAULT_PONDING_AREA_SQM,
    "ponding_area_assumed": True,
    "contributing_fraction": _DEFAULT_CONTRIBUTING_FRACTION,
    "contributing_fraction_assumed": True,
    "representative_edge_id": edge_info["edge_id"],
}

def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        in_fields = reader.fieldnames

        # Output fieldnames: original + metadata columns
        meta_keys = list(META.keys())
        out_fields = list(in_fields) + [k for k in meta_keys if k not in in_fields]

        rows_out = []
        hazard_counts = Counter()
        surcharge_count = 0
        max_depth = 0.0
        max_depth_row = None
        depths = []
        rain3h_vals = []

        for i, row in enumerate(reader):
            depth_cm, flag, level = compute_water_depth(row)

            # Overwrite the placeholder columns
            row["formula_depth_estimate_cm"] = f"{depth_cm:.4f}"
            row["drain_surcharge_flag"] = str(flag)
            row["formula_hazard_category"] = level

            # Add metadata columns
            for k, v in META.items():
                row[k] = str(v)

            rows_out.append(row)

            # Statistics
            hazard_counts[level] += 1
            if flag == 1:
                surcharge_count += 1
            if depth_cm > max_depth:
                max_depth = depth_cm
                max_depth_row = row.copy()
            depths.append(depth_cm)
            rain3h_vals.append(float(row.get("rain_3h_accumulated", 0) or 0))

    # Write output
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    total = len(rows_out)

    # Pearson correlation between rain_3h_accumulated and depth_cm
    n = len(depths)
    mean_d = sum(depths) / n
    mean_r = sum(rain3h_vals) / n
    num = sum((d - mean_d) * (r - mean_r) for d, r in zip(depths, rain3h_vals))
    den_d = math.sqrt(sum((d - mean_d) ** 2 for d in depths))
    den_r = math.sqrt(sum((r - mean_r) ** 2 for r in rain3h_vals))
    pearson_r = num / (den_d * den_r) if den_d and den_r else 0.0

    # Report
    print(f"Total rows processed: {total}")
    print(f"\nFormula estimate category distribution (not safety labels):")
    for lvl in ["LOW_ESTIMATE", "CAUTION", "HIGH", "SEVERE"]:
        c = hazard_counts.get(lvl, 0)
        print(f"  {lvl:8s}: {c:6d}  ({100*c/total:.2f}%)")
    print(f"\nRows with drain_surcharge_flag=1: {surcharge_count} ({100*surcharge_count/total:.2f}%)")
    print(f"\nPearson r (rain_3h_accumulated vs depth_cm): {pearson_r:.4f}")
    print(f"\nHighest depth_cm: {max_depth:.2f} cm")
    if max_depth_row:
        print(f"  at time: {max_depth_row['time']}")
        print(f"  rain_mm: {max_depth_row['rain_mm']}")
    print(f"\nOutput saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
