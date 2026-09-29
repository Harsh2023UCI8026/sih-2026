"""Read-only readiness audit for SIH problem statement 26085.

This module does not run a forecast or load the pickle model. It reports which
operational inputs are present and whether the current assets meet the stated
radar, terrain, drainage, coupled-hydraulics, and validation requirements.
"""

from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sih_data_bundle import validate_sih_data_bundle


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def _nominal_grid_spacing_km(points: list[dict[str, Any]]) -> float | None:
    """Estimate spacing for a regular lat/lon sample grid, if possible."""
    try:
        latitudes = sorted({float(p["latitude"]) for p in points})
        longitudes = sorted({float(p["longitude"]) for p in points})
    except (KeyError, TypeError, ValueError):
        return None

    spacing_km: list[float] = []
    if len(latitudes) > 1:
        spacing_km.extend(
            (b - a) * 111.32 for a, b in zip(latitudes, latitudes[1:])
        )
    if len(longitudes) > 1:
        mean_latitude = sum(latitudes) / len(latitudes) if latitudes else 0.0
        longitude_scale = 111.32 * math.cos(math.radians(mean_latitude))
        spacing_km.extend(
            (b - a) * longitude_scale
            for a, b in zip(longitudes, longitudes[1:])
        )
    return round(_median(spacing_km), 3) if spacing_km else None


def _rainfall_readiness() -> dict[str, Any]:
    fetcher = PROJECT_ROOT / "src" / "fetch_live_radar.py"
    source_text = ""
    try:
        source_text = fetcher.read_text(encoding="utf-8").lower()
    except OSError:
        pass

    current_source = "Open-Meteo point forecast" if "open-meteo" in source_text else "Unavailable"
    return {
        "status": "PARTIAL" if current_source != "Unavailable" else "MISSING",
        "meets_problem_statement": False,
        "current_source": current_source,
        "current_source_is_radar": False,
        "spatial_rainfall_grid": False,
        "gauge_bias_correction": False,
        "missing": [
            "Authorized, machine-readable Doppler-radar rainfall/QPE feed",
            "Rainfall values over the full pilot catchment, not one coordinate",
            "Gauge-based bias correction and source/issue-time metadata",
            "Validated 0-3 hour blend of radar extrapolation and NWP forecasts",
        ],
    }


def _terrain_readiness() -> dict[str, Any]:
    path = PROJECT_ROOT / "src" / "data" / "dwarka_elevation_grid.json"
    data = _read_json(path)
    if not data:
        return {
            "status": "MISSING",
            "meets_problem_statement": False,
            "missing": ["Verified georeferenced high-resolution terrain raster"],
        }

    points = data.get("elevation_points", [])
    points = points if isinstance(points, list) else []
    source = data.get("source", "Unspecified")
    quality = data.get("data_quality", "Unspecified")
    metadata_path = PROJECT_ROOT / "src" / "data" / "dwarka_dem_metadata.json"
    metadata = _read_json(metadata_path) or {}
    raster_relative = metadata.get("raster_path")
    raster_path = (PROJECT_ROOT / raster_relative).resolve() if isinstance(raster_relative, str) else None
    metadata_complete = all(metadata.get(key) not in (None, "") for key in (
        "source", "crs", "cell_size_m", "vertical_accuracy_m", "vertical_datum"
    ))
    resolution_ok = False
    try:
        resolution_ok = float(metadata.get("cell_size_m")) <= 5.0
    except (TypeError, ValueError):
        pass
    raster_exists = bool(raster_path and raster_path.is_file())
    verified = raster_exists and metadata_complete and resolution_ok
    reference_raster = PROJECT_ROOT / "data" / "reference" / "terrain" / "copernicus_glo30_dwarka_pilot.tif"
    reference_metadata = _read_json(
        PROJECT_ROOT / "data" / "reference" / "terrain" / "copernicus_glo30_dwarka_pilot.metadata.json"
    ) or {}
    return {
        "status": "READY" if verified else "PARTIAL",
        "meets_problem_statement": verified,
        "asset": str(path.relative_to(PROJECT_ROOT)).replace(os.sep, "/"),
        "asset_type": "point fixture; not a terrain raster",
        "elevation_sample_count": len(points),
        "nominal_sample_spacing_km": _nominal_grid_spacing_km(points),
        "source": source,
        "data_quality": quality,
        "verified_raster_available": raster_exists,
        "supplementary_reference_raster": {
            "available": reference_raster.is_file(),
            "path": str(reference_raster.relative_to(PROJECT_ROOT)).replace(os.sep, "/"),
            "product": reference_metadata.get("source_product"),
            "nominal_grid_spacing": reference_metadata.get("nominal_grid_spacing"),
            "use_status": "reference_only_not_a_street_scale_dtm",
        },
        "raster_metadata_complete": metadata_complete,
        "vertical_datum_documented": bool(metadata.get("vertical_datum")),
        "missing": [] if verified else [
            "Locally verified, hydrologically conditioned bare-earth DTM at street-scale resolution (the 30 m Copernicus DSM is reference-only)",
            "A terrain manifest covering projected CRS, local vertical accuracy, road curbs/crowns, buildings, and depression conditioning",
            "Road crowns, building barriers, curbs, and depression treatment",
        ],
    }


def _supplementary_reference_layers() -> dict[str, Any]:
    """List downloaded reference rasters without treating them as operational inputs."""
    specifications = [
        (
            "terrain",
            "data/reference/terrain/copernicus_glo30_dwarka_pilot.tif",
            "data/reference/terrain/copernicus_glo30_dwarka_pilot.metadata.json",
        ),
        (
            "land_cover",
            "data/reference/landcover/esa_worldcover2021_dwarka_pilot.tif",
            "data/reference/landcover/esa_worldcover2021_dwarka_pilot.metadata.json",
        ),
    ]
    layers: list[dict[str, Any]] = []
    for layer_name, raster_relative, metadata_relative in specifications:
        raster_path = PROJECT_ROOT / raster_relative
        metadata = _read_json(PROJECT_ROOT / metadata_relative) or {}
        layers.append(
            {
                "name": layer_name,
                "available": raster_path.is_file() and bool(metadata),
                "path": raster_relative,
                "metadata_path": metadata_relative,
                "size_bytes": raster_path.stat().st_size if raster_path.is_file() else None,
                "product": metadata.get("source_product"),
                "source_url": metadata.get("source_asset_url") or metadata.get("source_url"),
                "use_status": "SUPPLEMENTARY_REFERENCE_ONLY_NOT_USED_FOR_TRAINING_OR_FORECASTS",
            }
        )
    available_count = sum(layer["available"] for layer in layers)
    return {
        "status": "AVAILABLE" if available_count == len(layers) else "PARTIAL",
        "available_count": available_count,
        "layer_count": len(layers),
        "operational_for_street_depth": False,
        "layers": layers,
        "notice": (
            "These public raster crops provide context only. They do not replace "
            "radar QPE, surveyed drainage assets, a conditioned street-scale DTM, "
            "or measured flood depths."
        ),
    }


def _drainage_readiness() -> dict[str, Any]:
    path = PROJECT_ROOT / "src" / "dwarka_drainage_graph.json"
    graph = _read_json(path)
    if not graph:
        return {
            "status": "MISSING",
            "meets_problem_statement": False,
            "missing": ["Directed, georeferenced municipal drainage inventory"],
        }

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    nodes = nodes if isinstance(nodes, list) else []
    edges = edges if isinstance(edges, list) else []
    assumed_nodes = sum(
        bool(n.get("estimated") or n.get("estimated_input"))
        for n in nodes if isinstance(n, dict)
    )
    assumed_edges = sum(
        bool(
            e.get("geometry_estimated")
            or e.get("hydraulic_parameters_assumed")
            or e.get("blockage_factor_assumed")
        )
        for e in edges if isinstance(e, dict)
    )
    complete = bool(nodes and edges) and assumed_nodes == 0 and assumed_edges == 0
    return {
        "status": "READY" if complete else "PARTIAL",
        "meets_problem_statement": complete,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "assumed_node_count": assumed_nodes,
        "assumed_edge_count": assumed_edges,
        "data_quality": graph.get("data_quality", "Unspecified"),
        "missing": [] if complete else [
            "Surveyed manhole/inlet coordinates and rim/invert elevations",
            "Verified pipe/canal connectivity, dimensions, roughness, and capacity",
            "Catchment-to-inlet mapping and documented blockage evidence/assumptions",
            "Downstream outfall water levels and operating controls",
        ],
    }


def _ground_truth_readiness() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "scraped_ground_truth_pilot.csv"
    if not path.exists():
        return {
            "status": "MISSING",
            "meets_problem_statement": False,
            "observation_count": 0,
            "missing": ["Independent, event-based observed water-depth records"],
        }

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.DictReader(input_file)
            fields = set(reader.fieldnames or [])
            rows = list(reader)
    except OSError:
        fields, rows = set(), []

    measured_fields = {
        "event_id", "event_time_utc", "latitude", "longitude", "depth_cm",
        "measurement_method", "validation_status", "source_id",
    }
    # Report-derived estimates are useful for curation, but are not measured
    # observations suitable for validation.
    observation_count = sum(
        1 for row in rows
        if row.get("event_id") not in (None, "")
        and row.get("event_time_utc") not in (None, "")
        and row.get("latitude") not in (None, "")
        and row.get("longitude") not in (None, "")
        if row.get("depth_cm") not in (None, "")
        and row.get("measurement_method") not in (None, "")
        and row.get("source_id") not in (None, "")
        and row.get("validation_status") in {"verified", "surveyed", "sensor"}
    )
    validated = observation_count > 0 and measured_fields.issubset(fields)
    missing = []
    if not rows:
        missing.append("Independent observed depth records (current pilot CSV is empty)")
    if not measured_fields.issubset(fields):
        missing.append("Event ID/time, coordinates, measured depth, method, source ID, and validation status fields")
    if not validated:
        missing.append("Held-out complete storm events for unbiased validation")
    return {
        "status": "READY" if validated else "MISSING",
        "meets_problem_statement": validated,
        "observation_count": len(rows),
        "independent_verified_depth_count": observation_count,
        "columns": sorted(fields),
        "missing": missing,
    }


def _model_readiness() -> dict[str, Any]:
    provenance_path = PROJECT_ROOT / "models" / "model_provenance.json"
    provenance = _read_json(provenance_path) or {}
    artifact = PROJECT_ROOT / "models" / "dwarka_hydraulic_model.pkl"
    artifact_bytes = artifact.stat().st_size if artifact.is_file() else None
    vercel_path = PROJECT_ROOT / "vercel.json"
    try:
        vercel_config = vercel_path.read_text(encoding="utf-8").lower()
    except OSError:
        vercel_config = ""
    excludes_model = "models/**/*.pkl" in vercel_config
    observed_validation = provenance.get("independent_observed_depth_validation") is True
    deployment_ready = observed_validation and artifact.is_file() and not excludes_model
    return {
        "status": "READY" if deployment_ready else "NOT_VALIDATED_OR_DEPLOYMENT_MISMATCH",
        "meets_problem_statement": deployment_ready,
        "model_kind": provenance.get("model_kind", "Unknown"),
        "label_semantics": provenance.get("label_semantics", "Unknown"),
        "independent_observed_depth_validation": observed_validation,
        "local_pickle_present": artifact.is_file(),
        "local_pickle_size_bytes": artifact_bytes,
        "vercel_excludes_pickle": excludes_model,
        "deployed_inference_path": "formula_only" if excludes_model else "check_deployment_configuration",
        "pickle_was_loaded": False,
        "missing": [] if observed_validation else [
            "Training targets from independently measured flood depths or calibrated physics simulations",
            "Storm-wise holdout evaluation against measured observations",
            "A deployment artifact and model-serving path that match local inference",
        ],
    }


def _surface_solver_readiness() -> dict[str, Any]:
    candidates = [
        PROJECT_ROOT / "src" / "surface_flow_model.py",
        PROJECT_ROOT / "src" / "coupled_1d2d_model.py",
        PROJECT_ROOT / "src" / "two_d_surface_solver.py",
    ]
    available = [p.name for p in candidates if p.is_file()]
    manifest_path = PROJECT_ROOT / "src" / "data" / "coupled_model_provenance.json"
    manifest = _read_json(manifest_path) or {}
    coupling_validated = manifest.get("bidirectional_exchange_validated") is True
    observed_validation = manifest.get("independent_validation") is True
    ready = bool(available) and coupling_validated and observed_validation
    return {
        "status": "READY" if ready else "MISSING",
        "meets_problem_statement": ready,
        "solver_modules_found": available,
        "bidirectional_surface_drain_exchange_verified": coupling_validated,
        "independent_validation": observed_validation,
        "missing": [] if ready else [
            "2D surface-flow solver over a verified DEM",
            "coupled_model_provenance.json documenting validated exchange and independent validation",
        ],
    }


def build_data_readiness_report() -> dict[str, Any]:
    """Return a safe, read-only readiness summary for the current project."""
    components = {
        "rainfall_nowcast": _rainfall_readiness(),
        "terrain": _terrain_readiness(),
        "drainage_network": _drainage_readiness(),
        "coupled_surface_hydraulics": _surface_solver_readiness(),
        "ground_truth_and_validation": _ground_truth_readiness(),
        "ml_and_deployment": _model_readiness(),
    }
    ready_count = sum(
        component.get("meets_problem_statement") is True
        for component in components.values()
    )
    return {
        "problem_statement_id": "26085",
        "report_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "OPERATIONAL_READY" if ready_count == len(components) else "PROTOTYPE_ONLY",
        "ready_component_count": ready_count,
        "required_component_count": len(components),
        "prediction_accuracy_claim_supported": components["ground_truth_and_validation"]["meets_problem_statement"],
        "components": components,
        "supplementary_reference_layers": _supplementary_reference_layers(),
        "operational_bundle_preflight": validate_sih_data_bundle(
            PROJECT_ROOT / "data" / "operational_bundle"
        ),
        "notice": (
            "This read-only audit does not run a flood forecast or load the model pickle. "
            "The operational-bundle preflight checks file and schema structure only; it does not "
            "validate data quality or accuracy. A missing input means the corresponding street-depth "
            "prediction is not validated."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(build_data_readiness_report(), indent=2))
