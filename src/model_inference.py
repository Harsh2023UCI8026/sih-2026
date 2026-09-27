"""Model Inference with Extrapolation Warnings.

Loads the trained geometry-based RandomForest model and runs flood-depth
predictions on ANY drainage graph (pilot Dwarka, test_zone Palam, or
full_delhi).  For each edge, it checks whether the physical geometry
features fall WITHIN the training data's observed min/max range.  Edges
whose geometry is outside that range are flagged with
``extrapolation_warning: true`` so that downstream consumers (dashboard,
PDF report) can honestly caveat those predictions.
"""

import json, math, os
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List, Any


# ── Feature columns (must match model_train.py) ─────────────────────────
GEOMETRY_FEATURES = [
    "mannings_n",
    "slope",
    "cross_sectional_area_sqm",
    "catchment_sqm",
    "effective_capacity_mmhr",
]

ALL_FEATURES = [
    "rain_mm",
    "rain_3h_accumulated",
    "radar_reflectivity_dbz",
    "imperviousness_ratio",
    "effective_capacity_mmhr",
    "mannings_n",
    "slope",
    "cross_sectional_area_sqm",
    "catchment_sqm",
]

# ── Training-range bounds (from 5 pilot edges) ──────────────────────────
# These are saved alongside the model during training; hardcoded here as a
# fallback so inference works standalone.
_PILOT_TRAINING_RANGE: Dict[str, Dict[str, float]] = {}


def _load_training_range(models_dir: str) -> Dict[str, Dict[str, float]]:
    """Load the training-range JSON saved by model_train.py."""
    global _PILOT_TRAINING_RANGE
    range_path = os.path.join(models_dir, "training_feature_ranges.json")
    if os.path.exists(range_path):
        with open(range_path, "r", encoding="utf-8") as f:
            _PILOT_TRAINING_RANGE = json.load(f)
    return _PILOT_TRAINING_RANGE


# ── Edge geometry extraction (mirrors model_train.py) ────────────────────
def _extract_edge_geometries(graph_path: str) -> pd.DataFrame:
    """Extract physical geometry features from a drainage graph JSON."""
    with open(graph_path, "r", encoding="utf-8") as f:
        g = json.load(f)

    nodes = {n["id"]: n for n in g["nodes"]}
    rows = {}
    for e in g["edges"]:
        src = nodes[e["source"]]
        tgt = nodes[e["target"]]

        catch = e.get("catchment_sqm", src.get("inflow_catchment_sqm", 0))
        length = e.get("length_m", 1)
        raw_slope = (src.get("elevation_rim_m", 0) - tgt.get("elevation_rim_m", 0)) / length
        slope = max(raw_slope, 1e-5)

        w = e.get("width_m")
        h = e.get("height_m")
        d = e.get("diameter_m")
        if w and h:
            area = w * h
            perim = 2 * (w + h)
        elif d:
            area = math.pi * (d ** 2) / 4
            perim = math.pi * d
        else:
            area = 0.25
            perim = 2.0

        n_val = e.get("mannings_n", 0.013)
        R = area / perim if perim else 0.0
        bf = e.get("blockage_factor", 0.5)

        q_raw = (1.0 / n_val) * area * (R ** (2.0 / 3.0)) * (slope ** 0.5)
        q_eff = q_raw * bf
        cap_mmhr = q_eff * 3600 * 1000 / max(catch, 1.0)

        rows[e["id"]] = {
            "mannings_n": n_val,
            "slope": slope,
            "cross_sectional_area_sqm": area,
            "catchment_sqm": catch,
            "effective_capacity_mmhr": cap_mmhr,
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def _check_extrapolation(
    edge_geom_df: pd.DataFrame,
    training_range: Dict[str, Dict[str, float]],
) -> pd.DataFrame:
    """Flag edges whose geometry falls outside the pilot training range.

    Returns a DataFrame with columns: edge_id, feature, value,
    train_min, train_max, extrapolation_warning.
    """
    warnings_list: List[Dict[str, Any]] = []
    for edge_id, row in edge_geom_df.iterrows():
        edge_warnings = []
        for feat in GEOMETRY_FEATURES:
            if feat not in training_range:
                continue
            val = row[feat]
            lo = training_range[feat]["min"]
            hi = training_range[feat]["max"]
            if val < lo or val > hi:
                edge_warnings.append({
                    "edge_id": edge_id,
                    "feature": feat,
                    "value": round(val, 6),
                    "train_min": round(lo, 6),
                    "train_max": round(hi, 6),
                    "extrapolation_warning": True,
                })
        if not edge_warnings:
            warnings_list.append({
                "edge_id": edge_id,
                "feature": "ALL",
                "value": None,
                "train_min": None,
                "train_max": None,
                "extrapolation_warning": False,
            })
        else:
            warnings_list.extend(edge_warnings)
    return pd.DataFrame(warnings_list)


def run_inference(
    graph_path: str,
    rain_scenarios: List[Dict[str, float]],
    models_dir: str,
) -> pd.DataFrame:
    """Run flood-depth inference on every edge in graph_path for each
    rain scenario.

    Parameters
    ----------
    graph_path : str
        Path to a drainage_graph.json (pilot, test_zone, or full_delhi).
    rain_scenarios : list of dict
        Each dict must contain: rain_mm, rain_3h_accumulated,
        radar_reflectivity_dbz, imperviousness_ratio.
    models_dir : str
        Directory containing dwarka_hydraulic_model.pkl and
        training_feature_ranges.json.

    Returns
    -------
    pd.DataFrame
        Columns: edge_id, rain_mm, predicted_depth_cm,
        hazard_level, extrapolation_warning.
    """
    # Load model
    model_path = os.path.join(models_dir, "dwarka_hydraulic_model.pkl")
    model = joblib.load(model_path)
    # Predictions are made one row at a time. Keep this request path serial:
    # the HTTP server runs handlers on Windows worker threads, where a
    # joblib multiprocessing pool can fail while creating named pipes.
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1

    # Load training range for extrapolation checks
    training_range = _load_training_range(models_dir)

    # Extract edge geometries
    edge_geom_df = _extract_edge_geometries(graph_path)

    # Check extrapolation
    extrap_df = _check_extrapolation(edge_geom_df, training_range)
    extrap_flags = (
        extrap_df.groupby("edge_id")["extrapolation_warning"]
        .any()
        .to_dict()
    )

    # Print extrapolation summary
    print("\n" + "=" * 60)
    print("EXTRAPOLATION CHECK: Test Zone vs. Pilot Training Range")
    print("=" * 60)
    if training_range:
        print("\nTraining Feature Ranges (from pilot edges):")
        for feat, bounds in training_range.items():
            print(f"   {feat:30s}: [{bounds['min']:.6f}, {bounds['max']:.6f}]")

        print(f"\nTest Zone Edge Geometry Ranges:")
        for feat in GEOMETRY_FEATURES:
            if feat in edge_geom_df.columns:
                print(f"   {feat:30s}: [{edge_geom_df[feat].min():.6f}, {edge_geom_df[feat].max():.6f}]")

        flagged = [eid for eid, flag in extrap_flags.items() if flag]
        safe = [eid for eid, flag in extrap_flags.items() if not flag]
        print(f"\n   Edges WITHIN training range : {len(safe)}")
        print(f"   Edges OUTSIDE training range: {len(flagged)}")
        if flagged:
            print("\n   [WARN] EXTRAPOLATION WARNING for edges:")
            warn_details = extrap_df[extrap_df["extrapolation_warning"] == True]
            for _, w in warn_details.iterrows():
                print(f"     {w['edge_id']}  ->  {w['feature']}={w['value']}"
                      f"  (train range: [{w['train_min']}, {w['train_max']}])")
    else:
        print("   [WARN] training_feature_ranges.json not found — skipping range check.")
    print("=" * 60)

    # Build prediction rows
    results = []
    for scenario in rain_scenarios:
        for edge_id, geom_row in edge_geom_df.iterrows():
            row_dict = {
                "rain_mm": scenario["rain_mm"],
                "rain_3h_accumulated": scenario.get("rain_3h_accumulated", 0),
                "radar_reflectivity_dbz": scenario.get("radar_reflectivity_dbz", 0),
                "imperviousness_ratio": scenario.get("imperviousness_ratio", 0.85),
                **geom_row.to_dict(),
            }
            X_row = pd.DataFrame([row_dict])[ALL_FEATURES]
            pred = model.predict(X_row)[0]
            pred = max(pred, 0.0)  # clip negatives

            # Hazard level
            if pred <= 2:
                hazard = "LOW_ESTIMATE"
            elif pred <= 5:
                hazard = "CAUTION"
            elif pred <= 10:
                hazard = "HIGH"
            else:
                hazard = "SEVERE"

            results.append({
                "edge_id": edge_id,
                "rain_mm": scenario["rain_mm"],
                "predicted_depth_cm": round(pred, 4),
                "hazard_level": hazard,
                "extrapolation_warning": extrap_flags.get(edge_id, False),
            })

    return pd.DataFrame(results)


# ── CLI entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run flood inference on a drainage graph")
    parser.add_argument("--preset", type=str, default="dwarka", help="Zone preset (e.g., dwarka, test_zone)")
    args = parser.parse_args()

    src_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(src_dir, "..")
    models_dir = os.path.join(base_dir, "models")

    # Use preset to pick the graph
    graph_path = os.path.join(src_dir, f"{args.preset}_drainage_graph.json")
    if not os.path.exists(graph_path):
        print(f"Error: Could not find graph {graph_path}")
        print(f"Did you run graph_construction.py --preset {args.preset} ?")
        exit(1)

    # Test with a range of rainfall intensities
    scenarios = [
        {"rain_mm": 0.0, "rain_3h_accumulated": 0.0, "radar_reflectivity_dbz": 0.0, "imperviousness_ratio": 0.85},
        {"rain_mm": 2.0, "rain_3h_accumulated": 4.0, "radar_reflectivity_dbz": 30.0, "imperviousness_ratio": 0.85},
        {"rain_mm": 10.0, "rain_3h_accumulated": 20.0, "radar_reflectivity_dbz": 45.0, "imperviousness_ratio": 0.85},
        {"rain_mm": 30.0, "rain_3h_accumulated": 60.0, "radar_reflectivity_dbz": 55.0, "imperviousness_ratio": 0.85},
        {"rain_mm": 65.0, "rain_3h_accumulated": 120.0, "radar_reflectivity_dbz": 60.0, "imperviousness_ratio": 0.85},
    ]

    print("FLOOD NOWCASTING MODEL INFERENCE")
    print("Graph:", graph_path)
    results_df = run_inference(graph_path, scenarios, models_dir)

    print("\n" + "=" * 60)
    print("INFERENCE RESULTS")
    print("=" * 60)
    for _, r in results_df.iterrows():
        warn_str = " [EXTRAPOLATION WARN]" if r["extrapolation_warning"] else ""
        print(f"   {r['edge_id']:35s} | rain={r['rain_mm']:5.1f}mm | "
              f"depth={r['predicted_depth_cm']:7.4f}cm | "
              f"{r['hazard_level']:8s}{warn_str}")
