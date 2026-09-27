# src/regenerate_hydraulic_csv_multi_edge.py
"""Regenerate the full CSV with per-edge hydraulic model outputs (tidy format).

For each of the 15,264 hourly rows × 5 edges = 76,320 output rows.
Output columns:
  time, edge_id, rain_mm, runoff_mm, effective_capacity_mmhr,
  excess_mm, formula_depth_estimate_cm, drain_surcharge_flag, formula_hazard_category,
  blockage_factor, blockage_factor_assumed,
  ponding_area_sqm, ponding_area_assumed,
  contributing_fraction, contributing_fraction_assumed
"""

import csv, os, sys, math
from collections import Counter, defaultdict

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, WORKSPACE)

from src.hydraulic_model import (
    _rational_runoff_mm, _manning_capacity_mmhr,
    _depth_from_excess_mm, _EDGES,
    _DEFAULT_PONDING_AREA_SQM, _DEFAULT_BLOCKAGE_FACTOR,
    _DEFAULT_CONTRIBUTING_FRACTION,
)

INPUT_CSV = os.path.join(WORKSPACE, "archive", "training_data",
                         "processed_dwarka_hourly_rainfall.csv")
OUTPUT_CSV = os.path.join(WORKSPACE, "archive", "training_data",
                          "processed_dwarka_hourly_rainfall_hydraulic.csv")

OUT_FIELDS = [
    "time", "edge_id", "rain_mm", "runoff_mm",
    "effective_capacity_mmhr", "excess_mm",
    "formula_depth_estimate_cm", "drain_surcharge_flag", "formula_hazard_category",
    "blockage_factor", "blockage_factor_assumed",
    "ponding_area_sqm", "ponding_area_assumed",
    "contributing_fraction", "contributing_fraction_assumed",
]


def _hazard(depth_cm):
    if depth_cm <= 2:
        return 0, "LOW_ESTIMATE"
    elif depth_cm <= 5:
        return 1, "CAUTION"
    elif depth_cm <= 10:
        return 1, "HIGH"
    else:
        return 1, "SEVERE"


def main():
    # Pre-compute per-edge capacities (constant across all rows)
    edge_caps = {}
    for eid in _EDGES:
        cap, catch, bf = _manning_capacity_mmhr(eid)
        edge_caps[eid] = (cap, catch, bf)

    # Stats accumulators
    per_edge_hazard = defaultdict(Counter)
    per_edge_surcharge = defaultdict(int)
    per_edge_max_depth = {}
    per_edge_max_row = {}
    total_rows_in = 0

    with open(INPUT_CSV, newline="", encoding="utf-8") as fin, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=OUT_FIELDS)
        writer.writeheader()

        for row in reader:
            total_rows_in += 1
            rain = float(row.get("rain_mm", 0) or 0)
            imp = float(row.get("imperviousness_ratio", 0) or 0)
            runoff = _rational_runoff_mm(rain, imp)

            for eid in _EDGES:
                cap, catch, bf = edge_caps[eid]
                excess = max(runoff - cap, 0.0)
                depth_cm = _depth_from_excess_mm(
                    excess, _DEFAULT_PONDING_AREA_SQM, catch)
                flag, level = _hazard(depth_cm)

                writer.writerow({
                    "time": row["time"],
                    "edge_id": eid,
                    "rain_mm": rain,
                    "runoff_mm": round(runoff, 4),
                    "effective_capacity_mmhr": round(cap, 4),
                    "excess_mm": round(excess, 4),
                    "formula_depth_estimate_cm": round(depth_cm, 4),
                    "drain_surcharge_flag": flag,
                    "formula_hazard_category": level,
                    "blockage_factor": _DEFAULT_BLOCKAGE_FACTOR,
                    "blockage_factor_assumed": True,
                    "ponding_area_sqm": _DEFAULT_PONDING_AREA_SQM,
                    "ponding_area_assumed": True,
                    "contributing_fraction": _DEFAULT_CONTRIBUTING_FRACTION,
                    "contributing_fraction_assumed": True,
                })

                per_edge_hazard[eid][level] += 1
                if flag == 1:
                    per_edge_surcharge[eid] += 1
                prev_max = per_edge_max_depth.get(eid, 0.0)
                if depth_cm > prev_max:
                    per_edge_max_depth[eid] = depth_cm
                    per_edge_max_row[eid] = (row["time"], rain)

    total_out = total_rows_in * len(_EDGES)

    # Report
    print("=" * 70)
    print("MULTI-EDGE HYDRAULIC CSV REGENERATION COMPLETE")
    print("=" * 70)
    print("Input rows : %d" % total_rows_in)
    print("Edges      : %d" % len(_EDGES))
    print("Output rows: %d" % total_out)
    print()

    for eid in _EDGES:
        cap, catch, bf = edge_caps[eid]
        print("-" * 70)
        print("EDGE: %s  (cap=%.2f mm/hr, catch=%d, bf=%.1f)" % (eid, cap, catch, bf))
        hc = per_edge_hazard[eid]
        for lvl in ["LOW_ESTIMATE", "CAUTION", "HIGH", "SEVERE"]:
            c = hc.get(lvl, 0)
            print("  %-8s: %6d  (%.2f%%)" % (lvl, c, 100 * c / total_rows_in))
        sc = per_edge_surcharge[eid]
        print("  surcharge_flag=1: %d (%.2f%%)" % (sc, 100 * sc / total_rows_in))
        md = per_edge_max_depth.get(eid, 0)
        mr = per_edge_max_row.get(eid, ("?", 0))
        print("  max depth_cm: %.2f  at %s (rain=%.1f mm)" % (md, mr[0], mr[1]))

    print()
    print("Output: %s" % OUTPUT_CSV)


if __name__ == "__main__":
    main()
