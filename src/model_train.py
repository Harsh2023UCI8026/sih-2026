"""Build a separate, explicitly opt-in formula-surrogate demo artifact.

Production training is blocked because there are no independently measured
street-water-depth labels. The demo path below uses formula-derived labels and
synthetic cases and must never replace the runtime model.

Key design decisions:
1. NO categorical edge_id — uses continuous physical features only, so the
   demo model can accept other edge geometries. This does not establish that
   it predicts flood depths accurately in new areas.
2. NO leakage — excess_mm and runoff_mm are excluded; they are
   deterministic intermediaries of the same formula that produced depth_cm.
3. SYNTHETIC AUGMENTATION — 20 additional synthetic edges with geometry
   sampled across realistic urban-drain ranges are run through the same
   hydraulic formula to widen the training distribution from 5 to 25
   distinct geometry configurations.  These are clearly labelled
   ``is_synthetic=True`` in the training data.
4. Saves demo-specific feature ranges beside the demo artifact. Runtime
   inference does not load these files.
"""

import os
import json
import math
import argparse
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ── Load project graph geometry (not a surveyed drainage inventory) ──────
def load_edge_geometries(workspace_dir):
    graph_file = os.path.join(workspace_dir, "dwarka_drainage_graph.json")
    with open(graph_file, "r", encoding="utf-8") as f:
        g = json.load(f)

    nodes = {n["id"]: n for n in g["nodes"]}
    edge_geometries = {}

    for e in g["edges"]:
        src = nodes[e["source"]]
        tgt = nodes[e["target"]]

        catch = src.get("inflow_catchment_sqm", 0)
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

        edge_geometries[e["id"]] = {
            "mannings_n": n_val,
            "slope": slope,
            "cross_sectional_area_sqm": area,
            "catchment_sqm": catch,
            "effective_capacity_mmhr": cap_mmhr,
        }
    return pd.DataFrame.from_dict(edge_geometries, orient="index")


# ── Generate synthetic edges ─────────────────────────────────────────────
def generate_synthetic_edges(n_edges=20, seed=42):
    """Create synthetic edge geometries spanning realistic urban-drain ranges.

    Ranges are based on CPHEEO Manual (India) and typical Delhi municipal
    drain dimensions:
      - width:     0.3 – 4.0 m
      - height:    0.3 – 3.0 m
      - mannings_n: 0.011 – 0.025
      - slope:     0.0001 – 0.005
      - width:     0.3 – 10.0 m
      - height:    0.3 – 4.0 m
      - mannings_n: 0.012 – 0.025
      - slope:     0.0001 – 0.015
      - catchment: 1,000 – 2,000,000 sqm
      - blockage:  0.3 – 0.7
    """
    rng = np.random.default_rng(seed)

    rows = {}
    for i in range(n_edges):
        w = rng.uniform(0.3, 10.0)
        h = rng.uniform(0.3, 4.0)
        n_val = rng.uniform(0.012, 0.025)
        slope = rng.uniform(0.0001, 0.015)
        catch = rng.uniform(1000.0, 2_000_000)
        bf = rng.uniform(0.3, 0.7)

        area = w * h
        perim = 2 * (w + h)
        R = area / perim
        q_raw = (1.0 / n_val) * area * (R ** (2.0 / 3.0)) * (slope ** 0.5)
        q_eff = q_raw * bf
        cap_mmhr = q_eff * 3600 * 1000 / catch

        rows[f"SYNTH_EDGE_{i:03d}"] = {
            "mannings_n": n_val,
            "slope": slope,
            "cross_sectional_area_sqm": area,
            "catchment_sqm": catch,
            "effective_capacity_mmhr": cap_mmhr,
        }
    return pd.DataFrame.from_dict(rows, orient="index")


# ── Hydraulic depth formula (mirrors hydraulic_model.py) ─────────────────
def compute_depth_for_row(rain_mm, imperv, cap_mmhr, catch_sqm,
                          contributing_fraction=0.15, ponding_area=5000.0):
    """Deterministic depth formula — used ONLY to label synthetic rows."""
    runoff = max(0.0, min(1.0, imperv)) * rain_mm
    excess = max(runoff - cap_mmhr, 0.0)
    if excess <= 0:
        return 0.0
    vol = (excess / 1000.0) * catch_sqm * contributing_fraction
    return (vol / ponding_area) * 100.0  # cm


# ── Main training function ───────────────────────────────────────────────
def train_dwarka_flood_model(workspace_dir, allow_formula_surrogate_demo=False):
    if not allow_formula_surrogate_demo:
        raise RuntimeError(
            "Refusing to train or overwrite the runtime model: this script learns from "
            "formula-derived depth labels and synthetic cases, not measured street-water depths. "
            "The independent pilot depth file is currently empty. Use "
            "--allow-formula-surrogate-demo only if you explicitly want a separate demo artifact."
        )

    print("=" * 60)
    print("DEMO ONLY: FORMULA-LABELLED + SYNTHETIC SURROGATE (NOT RUNTIME MODEL)")
    print("=" * 60)

    models_dir = os.path.join(workspace_dir, "..", "models")

    hydraulic_csv = os.path.join(workspace_dir, "..", "archive", "training_data",
                                 "processed_dwarka_hourly_rainfall_hydraulic.csv")
    original_csv = os.path.join(workspace_dir, "..", "archive", "training_data",
                                "processed_dwarka_hourly_rainfall.csv")

    # ── 1. Load historical workbook rows and formula-derived labels ───────
    print("1. Loading workbook time-series and formula-derived depth labels...")
    df_hydro = pd.read_csv(hydraulic_csv).rename(columns={
        "formula_depth_estimate_cm": "depth_cm",
    })
    if "effective_capacity_mmhr" in df_hydro.columns:
        df_hydro = df_hydro.drop(columns=["effective_capacity_mmhr"])
    original_data = pd.read_csv(original_csv)
    proxy_column = "rainfall_reflectivity_proxy_dbz" if "rainfall_reflectivity_proxy_dbz" in original_data else "radar_reflectivity_dbz"
    df_orig = original_data[
        ["time", "rain_3h_accumulated", proxy_column, "imperviousness_ratio"]
    ].rename(columns={proxy_column: "radar_reflectivity_dbz"})
    df = pd.merge(df_hydro, df_orig, on="time", how="left")

    print("2. Mapping real edge geometries...")
    edge_geom_df = load_edge_geometries(workspace_dir)
    df = df.merge(edge_geom_df, left_on="edge_id", right_index=True, how="left")
    df["is_synthetic"] = False
    print(f"   Workbook time-series rows (not measured depth observations): {len(df):,}")

    # ── 2. Generate synthetic augmentation ───────────────────────────────
    print("3. Generating synthetic edge augmentation...")
    synth_edges = generate_synthetic_edges(n_edges=20, seed=42)

    # Use the same rain time-series from the original data as a base
    rain_cols = ["time", "rain_mm", "rain_3h_accumulated",
                 "radar_reflectivity_dbz", "imperviousness_ratio"]
    rain_ts = df_orig.copy()
    rain_ts = rain_ts.merge(
        df_hydro[["time", "rain_mm"]].drop_duplicates(),
        on="time", how="left",
    )

    rng_rain = np.random.default_rng(42)
    synth_rows = []
    for edge_id, geom in synth_edges.iterrows():
        for _, rain_row in rain_ts.iterrows():
            # Augment rain_mm with synthetic extreme rain up to 150 mm/hr
            synth_rain_mm = rng_rain.uniform(0.0, 150.0)
            synth_rain_3h = synth_rain_mm * 1.5  # rough proportional scaling
            synth_dbz = min(65.0, 20.0 + (synth_rain_mm * 0.3)) if synth_rain_mm > 0 else 0.0

            depth = compute_depth_for_row(
                rain_mm=synth_rain_mm,
                imperv=rain_row["imperviousness_ratio"],
                cap_mmhr=geom["effective_capacity_mmhr"],
                catch_sqm=geom["catchment_sqm"],
            )
            synth_rows.append({
                "time": rain_row["time"],
                "edge_id": edge_id,
                "rain_mm": synth_rain_mm,
                "rain_3h_accumulated": synth_rain_3h,
                "radar_reflectivity_dbz": synth_dbz,
                "imperviousness_ratio": rain_row["imperviousness_ratio"],
                "depth_cm": depth,
                "effective_capacity_mmhr": geom["effective_capacity_mmhr"],
                "mannings_n": geom["mannings_n"],
                "slope": geom["slope"],
                "cross_sectional_area_sqm": geom["cross_sectional_area_sqm"],
                "catchment_sqm": geom["catchment_sqm"],
                "is_synthetic": True,
            })

    df_synth = pd.DataFrame(synth_rows)
    print(f"   Synthetic rows: {len(df_synth):,} (20 edges × {len(rain_ts):,} hours)")

    # ── 3. Combine real + synthetic ──────────────────────────────────────
    features_to_use = [
        "rain_mm", "rain_3h_accumulated", "radar_reflectivity_dbz",
        "imperviousness_ratio", "effective_capacity_mmhr",
        "mannings_n", "slope", "cross_sectional_area_sqm", "catchment_sqm",
    ]
    common_cols = features_to_use + ["depth_cm", "is_synthetic"]
    df_combined = pd.concat([df[common_cols], df_synth[common_cols]], ignore_index=True)
    print(f"   Combined total: {len(df_combined):,} rows "
          f"(25 distinct geometries × rain time-series)")

    # ── 4. Prep features ─────────────────────────────────────────────────
    print("4. Preprocessing...")
    X = df_combined[features_to_use]
    y = df_combined["depth_cm"]

    non_zero = (y > 0).sum()
    print(f"   Rows with depth > 0: {non_zero:,} ({non_zero / len(y) * 100:.2f}%)")

    # ── 5. Save training feature ranges ──────────────────────────────────
    geom_feats = ["mannings_n", "slope", "cross_sectional_area_sqm",
                  "catchment_sqm", "effective_capacity_mmhr"]
    training_range = {}
    for feat in geom_feats:
        training_range[feat] = {
            "min": float(X[feat].min()),
            "max": float(X[feat].max()),
        }
    print("5. Training geometry feature ranges:")
    for feat, bounds in training_range.items():
        print(f"   {feat:30s}: [{bounds['min']:.6f}, {bounds['max']:.6f}]")

    # ── 6. Train/test split ──────────────────────────────────────────────
    print("6. Splitting workbook time-series rows chronologically (80/20)...")
    # This holdout evaluates reproduction of generated formula labels; it is
    # not an independent validation against street-water observations.
    real_times = df['time'].unique()
    real_times.sort()
    split_idx = int(0.8 * len(real_times))
    train_times = real_times[:split_idx]
    test_times = real_times[split_idx:]

    df_real_train = df[df['time'].isin(train_times)]
    df_real_test = df[df['time'].isin(test_times)]

    print(f"   Workbook date range train: {train_times.min()} to {train_times.max()}")
    print(f"   Workbook date range test : {test_times.min()} to {test_times.max()}")
    print(f"   Workbook rows - train: {len(df_real_train):,}, test: {len(df_real_test):,}")
    print(f"   Synthetic rows total: {len(df_synth):,}")

    # Split synthetic data (standard 80/20)
    X_synth = df_synth[features_to_use]
    y_synth = df_synth["depth_cm"]
    X_synth_train, X_synth_test, y_synth_train, y_synth_test = train_test_split(
        X_synth, y_synth, test_size=0.2, random_state=42
    )

    # Combine training sets
    X_train = pd.concat([df_real_train[features_to_use], X_synth_train], ignore_index=True)
    y_train = pd.concat([df_real_train["depth_cm"], y_synth_train], ignore_index=True)

    X_test_real = df_real_test[features_to_use]
    y_test_real = df_real_test["depth_cm"]
    X_test_synth = X_synth_test
    y_test_synth = y_synth_test

    print(f"   Train total={len(X_train):,}, Test (Synthetic)={len(X_test_synth):,}, Test (Formula-label workbook holdout)={len(X_test_real):,}")

    # ── 7. Fit model with sample weighting (real rows up‑weighted) ─────────────────────────────────────────────────────
    print("7. Training RandomForestRegressor with workbook rows weighted x4...")
    model = RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
    
    # Build weight array: real rows get higher weight
    real_weight = 4
    # The first len(df_real_train) rows in X_train are real, the rest are synthetic
    is_real_mask = np.array([True] * len(df_real_train) + [False] * len(X_synth_train))
    sample_weights = np.where(is_real_mask, real_weight, 1)
    
    model.fit(X_train, y_train, sample_weight=sample_weights)

    # ── 8. Evaluate ──────────────────────────────────────────────────────
    print("8. Evaluating...")
    y_pred_synth = model.predict(X_test_synth)
    mae_synth = mean_absolute_error(y_test_synth, y_pred_synth)
    rmse_synth = np.sqrt(mean_squared_error(y_test_synth, y_pred_synth))
    r2_synth = r2_score(y_test_synth, y_pred_synth)

    y_pred_real = model.predict(X_test_real)
    mae_real = mean_absolute_error(y_test_real, y_pred_real)
    rmse_real = np.sqrt(mean_squared_error(y_test_real, y_pred_real))
    r2_real = r2_score(y_test_real, y_pred_real)

    print("\n" + "=" * 60)
    print("METRICS: SYNTHETIC (FORMULA) TEST SET")
    print("=" * 60)
    print(f"   MAE  : {mae_synth:.4f} cm")
    print(f"   RMSE : {rmse_synth:.4f} cm")
    print(f"   R²   : {r2_synth:.4f}")

    print("\n" + "=" * 60)
    print("METRICS: WORKBOOK HOLDOUT (FORMULA-LABEL REPRODUCTION; NOT FLOOD VALIDATION)")
    print("=" * 60)
    print(f"   MAE  : {mae_real:.4f} cm")
    print(f"   RMSE : {rmse_real:.4f} cm")
    print(f"   R²   : {r2_real:.4f}")

    nz_mask_synth = y_test_synth > 0
    if nz_mask_synth.sum() > 0:
        y_tnz_synth, y_pnz_synth = y_test_synth[nz_mask_synth], y_pred_synth[nz_mask_synth]
        print("\n" + "-" * 60)
        print("NON-ZERO FLOOD SUBSET (SYNTHETIC)")
        print("-" * 60)
        print(f"   Subset : {nz_mask_synth.sum()} samples")
        print(f"   MAE    : {mean_absolute_error(y_tnz_synth, y_pnz_synth):.4f} cm")
        print(f"   RMSE   : {np.sqrt(mean_squared_error(y_tnz_synth, y_pnz_synth)):.4f} cm")
        print(f"   R²     : {r2_score(y_tnz_synth, y_pnz_synth):.4f}")

    nz_mask_real = y_test_real > 0
    if nz_mask_real.sum() > 0:
        y_tnz_real, y_pnz_real = y_test_real[nz_mask_real], y_pred_real[nz_mask_real]
        print("\n" + "-" * 60)
        print("NON-ZERO FORMULA-LABEL SUBSET (WORKBOOK HOLDOUT; NOT FLOOD VALIDATION)")
        print("-" * 60)
        print(f"   Subset : {nz_mask_real.sum()} samples")
        print(f"   MAE    : {mean_absolute_error(y_tnz_real, y_pnz_real):.4f} cm")
        print(f"   RMSE   : {np.sqrt(mean_squared_error(y_tnz_real, y_pnz_real)):.4f} cm")
        print(f"   R²     : {r2_score(y_tnz_real, y_pnz_real):.4f}")
    print("=" * 60)

    # ── 9. Feature importances ───────────────────────────────────────────
    print("\n9. Feature Importances:")
    imp = pd.DataFrame({
        "Feature": X_train.columns,
        "Importance": model.feature_importances_,
    }).sort_values("Importance", ascending=False)
    for _, row in imp.iterrows():
        print(f"   {row['Feature']:30s}: {row['Importance']:.4f}")

    # ── 10. Save model + ranges ──────────────────────────────────────────
    print("\n10. Saving model & training ranges...")
    models_dir = os.path.join(workspace_dir, "..", "models")
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(model, os.path.join(models_dir, "dwarka_hydraulic_formula_surrogate_demo.pkl"))
    with open(os.path.join(models_dir, "training_feature_ranges_demo.json"), "w") as f:
        json.dump(training_range, f, indent=2)
    provenance = {
        "model_kind": "RandomForest surrogate for a deterministic hydraulic formula",
        "label_semantics": "Formula-derived estimate; not measured street-water depth",
        "inputs": "Historical workbook time series of unverified provenance plus synthetic rain/geometry augmentation",
        "independent_observed_depth_validation": False,
        "metrics_semantics": "Fit to formula-generated labels only; not real-world flood accuracy",
    }
    with open(os.path.join(models_dir, "model_provenance_demo.json"), "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print(f"   Saved separate demo artifacts to {models_dir}/")
    print("\n[COMPLETE] Formula surrogate demo built; runtime model was not modified and no flood validation was performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build only an explicitly requested formula-surrogate demo artifact")
    parser.add_argument(
        "--allow-formula-surrogate-demo",
        action="store_true",
        help="Explicitly build a non-runtime demo model from formula-generated labels",
    )
    args = parser.parse_args()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    train_dwarka_flood_model(current_dir, allow_formula_surrogate_demo=args.allow_formula_surrogate_demo)
