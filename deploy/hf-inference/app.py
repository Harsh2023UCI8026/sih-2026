"""RandomForest inference service for the SIH dashboard's Dwarka pilot graph."""

import hmac
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, Field


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("sih-hf-inference")
BASE_DIR = Path(__file__).resolve().parent
GRAPH_PATH = BASE_DIR / "dwarka_drainage_graph.json"
RANGES_PATH = BASE_DIR / "training_feature_ranges.json"
MODEL_FILENAME = os.getenv("MODEL_FILENAME", "dwarka_hydraulic_model.pkl")
MODEL_REVISION = os.getenv("MODEL_REVISION", "main")
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
MAX_GRAPH_EDGES = 1000
_model = None
_model_error = None
_edge_geometries = None
_edge_warnings = None
_graph_edges = None
_graph_nodes = None

app = FastAPI(
    title="SIH Urban Flood Depth Inference",
    version="1.0.0",
    description=(
        "RandomForest surrogate inference for the Dwarka pilot graph. "
        "Outputs are unvalidated estimates, not observed water levels."
    ),
)


class PredictionRequest(BaseModel):
    rain_mm: float = Field(ge=0, le=1000)
    rain_3h_accumulated: float = Field(default=0, ge=0, le=5000)
    radar_reflectivity_dbz: float = Field(default=0, ge=0, le=100)
    imperviousness_ratio: float = Field(default=0.85, ge=0, le=1)


def _load_model():
    global _model, _model_error
    if _model is not None:
        return _model

    try:
        model_path = os.getenv("MODEL_PATH")
        if not model_path:
            repo_id = os.getenv("MODEL_REPO_ID", "").strip()
            if not repo_id:
                raise RuntimeError("Set MODEL_REPO_ID or mount the artifact and set MODEL_PATH.")
            model_path = hf_hub_download(
                repo_id=repo_id,
                filename=MODEL_FILENAME,
                repo_type="model",
                revision=MODEL_REVISION,
                token=os.getenv("HF_TOKEN") or None,
            )

        # joblib/pickle can execute code at load time. Only load an artifact
        # from a Hub repository controlled by this project team.
        _model = joblib.load(model_path)
        if hasattr(_model, "n_jobs"):
            _model.n_jobs = 1
        _model_error = None
        logger.info("Loaded inference artifact (%s bytes).", os.path.getsize(model_path))
        return _model
    except Exception as exc:
        _model_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Could not load the inference artifact")
        raise


def _load_graph_assets():
    global _edge_geometries, _edge_warnings, _graph_edges, _graph_nodes
    if _edge_geometries is not None:
        return

    with GRAPH_PATH.open("r", encoding="utf-8") as graph_file:
        graph = json.load(graph_file)
    with RANGES_PATH.open("r", encoding="utf-8") as ranges_file:
        training_ranges = json.load(ranges_file)

    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    if not edges or len(edges) > MAX_GRAPH_EDGES:
        raise RuntimeError("Bundled pilot graph has an invalid number of edges.")

    geometry_rows = {}
    for edge in edges:
        source = nodes.get(edge.get("source"))
        target = nodes.get(edge.get("target"))
        if not source or not target:
            raise RuntimeError(f"Graph edge {edge.get('id')} references a missing node.")

        catchment = edge.get("catchment_sqm", source.get("inflow_catchment_sqm", 0))
        length = edge.get("length_m", 1)
        raw_slope = (
            source.get("elevation_rim_m", 0) - target.get("elevation_rim_m", 0)
        ) / max(float(length), 1e-9)
        slope = max(raw_slope, 1e-5)
        width, height, diameter = (
            edge.get("width_m"), edge.get("height_m"), edge.get("diameter_m")
        )
        if width and height:
            area = width * height
            perimeter = 2 * (width + height)
        elif diameter:
            area = math.pi * diameter**2 / 4
            perimeter = math.pi * diameter
        else:
            area = 0.25
            perimeter = 2.0

        manning_n = edge.get("mannings_n", 0.013)
        hydraulic_radius = area / perimeter if perimeter else 0
        blockage = edge.get("blockage_factor", 0.5)
        q_raw = (
            (1 / manning_n)
            * area
            * (hydraulic_radius ** (2 / 3))
            * math.sqrt(slope)
        )
        effective_capacity = q_raw * blockage * 3600 * 1000 / max(float(catchment), 1)
        geometry_rows[edge["id"]] = {
            "mannings_n": manning_n,
            "slope": slope,
            "cross_sectional_area_sqm": area,
            "catchment_sqm": catchment,
            "effective_capacity_mmhr": effective_capacity,
        }

    warning_by_edge = {}
    for edge_id, features in geometry_rows.items():
        out_of_range = []
        for feature in GEOMETRY_FEATURES:
            bounds = training_ranges.get(feature)
            if bounds and not (bounds["min"] <= features[feature] <= bounds["max"]):
                out_of_range.append(feature)
        warning_by_edge[edge_id] = out_of_range

    _edge_geometries = geometry_rows
    _edge_warnings = warning_by_edge
    _graph_edges = {edge["id"]: edge for edge in edges}
    _graph_nodes = nodes


def _authorize(authorization: str | None = Header(default=None)):
    expected = os.getenv("API_BEARER_TOKEN", "")
    if not expected:
        return
    supplied = authorization or ""
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.on_event("startup")
def warm_model():
    """Download/cache the artifact at startup so health checks report readiness."""
    try:
        _load_graph_assets()
        _load_model()
    except Exception:
        # Keep healthz reachable and return a useful 503 from /predict. This
        # allows fixing Space settings without a restart loop.
        pass


@app.get("/healthz")
def healthz():
    try:
        _load_graph_assets()
    except Exception as exc:
        return {"status": "not_ready", "model_loaded": _model is not None, "error": str(exc)}
    return {
        "status": "ready" if _model is not None else "not_ready",
        "model_loaded": _model is not None,
        "model_error_type": _model_error.split(":", 1)[0] if _model_error else None,
        "edge_count": len(_edge_geometries),
        "model_kind": "RandomForest surrogate; formula-derived/synthetic training targets",
    }


@app.post("/predict", dependencies=[Depends(_authorize)])
def predict(inputs: PredictionRequest):
    try:
        model = _load_model()
        _load_graph_assets()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model service not ready: {type(exc).__name__}") from exc

    prediction_input: dict[str, Any] = inputs.model_dump()
    output = []
    for edge_id, geometry in _edge_geometries.items():
        row = {**prediction_input, **geometry}
        features = pd.DataFrame([row], columns=ALL_FEATURES)
        depth = max(float(model.predict(features)[0]), 0.0)
        if not math.isfinite(depth):
            raise HTTPException(status_code=502, detail="Model returned a non-finite prediction.")
        hazard = "LOW_ESTIMATE" if depth <= 2 else "CAUTION" if depth <= 5 else "HIGH" if depth <= 10 else "SEVERE"
        edge = _graph_edges[edge_id]
        source = _graph_nodes[edge["source"]]
        target = _graph_nodes[edge["target"]]
        output.append({
            "edge_id": edge_id,
            "rain_mm": inputs.rain_mm,
            "predicted_depth_cm": round(depth, 4),
            "hazard_level": hazard,
            "extrapolation_warning": bool(_edge_warnings.get(edge_id)),
            "extrapolation_features": _edge_warnings.get(edge_id, []),
            "rain_intensity_exceeds_training": inputs.rain_mm > 150,
            "geometry_estimated": bool(edge.get("geometry_estimated", True)),
            "geometry_source": edge.get("geometry_source", "SCHEMATIC_ASSUMPTION"),
            "source_node": edge.get("source"),
            "target_node": edge.get("target"),
            "source_lat": source.get("latitude", source.get("lat", 0)),
            "source_lon": source.get("longitude", source.get("lon", 0)),
            "target_lat": target.get("latitude", target.get("lat", 0)),
            "target_lon": target.get("longitude", target.get("lon", 0)),
            "width_m": edge.get("width_m"),
            "height_m": edge.get("height_m"),
            "length_m": edge.get("length_m"),
            "effective_capacity_mmhr": round(geometry["effective_capacity_mmhr"], 4),
            "catchment_sqm": round(geometry["catchment_sqm"], 2),
            "forecast_available": True,
            "formula_estimate": False,
            "prediction_backend": "random_forest_huggingface",
        })

    return {
        "status": "ok",
        "model_kind": "RandomForest surrogate",
        "label_semantics": "Formula-derived/synthetic targets; no independent observed-depth validation",
        "predictions": output,
    }
