"""Structural preflight for externally supplied SIH 26085 data.

The validator checks manifests, CSV fields, file paths, and network references.
It deliberately does not decode raster/netCDF data or certify its accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE = PROJECT_ROOT / "data" / "operational_bundle"
OBSERVATION_FIELDS = {
    "event_id", "event_time_utc", "latitude", "longitude", "depth_cm",
    "measurement_method", "validation_status", "source_id",
}
VALIDATION_STATUSES = {"verified", "surveyed", "sensor"}


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"Cannot read valid JSON: {type(exc).__name__}"
    if not isinstance(value, dict):
        return None, "Top-level JSON value must be an object"
    return value, None


def _required_fields(value: dict[str, Any], fields: set[str]) -> list[str]:
    return sorted(
        field for field in fields
        if value.get(field) is None or value.get(field) == ""
    )


def _resolve_bundle_file(bundle: Path, relative_path: Any) -> tuple[Path | None, str | None]:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return None, "file path must be a non-empty relative path"
    candidate_text = relative_path.strip()
    candidate = Path(candidate_text)
    if candidate.is_absolute():
        return None, "absolute file paths are not allowed"
    resolved_bundle = bundle.resolve()
    resolved_candidate = (resolved_bundle / candidate).resolve()
    try:
        resolved_candidate.relative_to(resolved_bundle)
    except ValueError:
        return None, "file path escapes the bundle directory"
    if not resolved_candidate.is_file():
        return None, f"file not found: {candidate_text}"
    try:
        if resolved_candidate.stat().st_size == 0:
            return None, f"file is empty: {candidate_text}"
    except OSError:
        return None, f"file cannot be inspected: {candidate_text}"
    return resolved_candidate, None


def _manifest(bundle: Path, relative_manifest: str) -> tuple[dict[str, Any] | None, list[str]]:
    path, path_error = _resolve_bundle_file(bundle, relative_manifest)
    if path_error:
        return None, [path_error]
    assert path is not None
    value, json_error = _load_json(path)
    return value, [json_error] if json_error else []


def _rainfall_check(bundle: Path) -> dict[str, Any]:
    manifest, errors = _manifest(bundle, "rainfall/manifest.json")
    warnings: list[str] = []
    if manifest is None:
        return {"status": "INCOMPLETE", "errors": errors, "warnings": warnings}

    required = {
        "provider", "product", "product_type", "issue_time_utc", "time_step_minutes",
        "units", "crs", "bbox_wgs84", "valid_times_utc", "data_files",
        "spatial_representation", "grid_cell_size_m",
    }
    missing = _required_fields(manifest, required)
    if missing:
        errors.append("Missing manifest fields: " + ", ".join(missing))
    if manifest.get("product_type") not in {"radar_qpe", "radar_nowcast", "radar_nwp_blend"}:
        errors.append("product_type must identify a radar_qpe, radar_nowcast, or radar_nwp_blend grid")
    if manifest.get("spatial_representation") != "grid":
        errors.append("spatial_representation must be 'grid'; a point series is not catchment rainfall coverage")

    issue_time = _parse_utc(manifest.get("issue_time_utc"))
    if manifest.get("issue_time_utc") and issue_time is None:
        errors.append("issue_time_utc must be an ISO-8601 timestamp with timezone")
    valid_times = manifest.get("valid_times_utc")
    parsed_valid_times = [_parse_utc(value) for value in valid_times] if isinstance(valid_times, list) else []
    if valid_times is not None and (not parsed_valid_times or any(value is None for value in parsed_valid_times)):
        errors.append("valid_times_utc must be a non-empty list of ISO-8601 timestamps with timezone")
    if issue_time and parsed_valid_times and all(value is not None for value in parsed_valid_times):
        horizon_minutes = (max(parsed_valid_times) - issue_time).total_seconds() / 60
        if horizon_minutes < 180:
            warnings.append("Rainfall valid times do not cover the full 3-hour target horizon")
        if horizon_minutes < 0:
            errors.append("Rainfall valid times precede the issue time")

    try:
        time_step = float(manifest.get("time_step_minutes"))
        if not math.isfinite(time_step) or time_step <= 0:
            raise ValueError
    except (TypeError, ValueError):
        if manifest.get("time_step_minutes") is not None:
            errors.append("time_step_minutes must be a positive number")

    try:
        grid_cell_size = float(manifest.get("grid_cell_size_m"))
        if not math.isfinite(grid_cell_size) or grid_cell_size <= 0:
            raise ValueError
    except (TypeError, ValueError):
        if manifest.get("grid_cell_size_m") is not None:
            errors.append("grid_cell_size_m must be a positive number")

    bbox = manifest.get("bbox_wgs84")
    if bbox is not None:
        try:
            west, south, east, north = [float(part) for part in bbox]
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError
        except (TypeError, ValueError):
            errors.append("bbox_wgs84 must be [west, south, east, north] in valid degrees")

    files = manifest.get("data_files")
    checked_files = 0
    if files is not None:
        if not isinstance(files, list) or not files:
            errors.append("data_files must be a non-empty list of bundle-relative file paths")
        else:
            for relative_path in files:
                _, file_error = _resolve_bundle_file(bundle, relative_path)
                if file_error:
                    errors.append(f"Rainfall {file_error}")
                else:
                    checked_files += 1

    if manifest.get("gauge_bias_correction") is not True:
        warnings.append("Gauge-bias correction is not declared as applied")
    if not isinstance(manifest.get("gauge_bias_method"), str) or not manifest.get("gauge_bias_method", "").strip():
        warnings.append("Gauge-bias correction method/provenance is not documented")
    return {
        "status": "STRUCTURE_VALID" if not errors else "INCOMPLETE",
        "errors": errors,
        "warnings": warnings,
        "checked_data_file_count": checked_files,
        "product_type": manifest.get("product_type"),
        "spatial_representation": manifest.get("spatial_representation"),
        "provider": manifest.get("provider"),
    }


def _terrain_check(bundle: Path) -> dict[str, Any]:
    manifest, errors = _manifest(bundle, "terrain/manifest.json")
    warnings: list[str] = []
    if manifest is None:
        return {"status": "INCOMPLETE", "errors": errors, "warnings": warnings}

    required = {
        "raster_file", "source", "crs", "horizontal_unit", "cell_size_m",
        "vertical_accuracy_m", "vertical_datum", "processing_notes",
    }
    missing = _required_fields(manifest, required)
    if missing:
        errors.append("Missing manifest fields: " + ", ".join(missing))
    _, file_error = _resolve_bundle_file(bundle, manifest.get("raster_file"))
    if file_error:
        errors.append("Terrain " + file_error)
    if manifest.get("horizontal_unit") not in (None, "m", "metre", "meter", "metres", "meters"):
        errors.append("horizontal_unit must be metres for hydraulic length calculations")
    for name in ("cell_size_m", "vertical_accuracy_m"):
        try:
            number = float(manifest.get(name))
            if not math.isfinite(number) or number <= 0:
                raise ValueError
            if name == "cell_size_m" and number > 5:
                warnings.append("DEM cell size is coarser than the project's 5 m street-scale screening target")
        except (TypeError, ValueError):
            if manifest.get(name) is not None:
                errors.append(f"{name} must be a positive number")
    if manifest.get("crs") and "4326" in str(manifest.get("crs")):
        warnings.append("DEM CRS appears geographic; confirm the raster is projected before hydraulic calculations")
    return {
        "status": "STRUCTURE_VALID" if not errors else "INCOMPLETE",
        "errors": errors,
        "warnings": warnings,
        "raster_metadata_decoded": False,
        "source": manifest.get("source"),
    }


def _drainage_check(bundle: Path) -> dict[str, Any]:
    path, path_error = _resolve_bundle_file(bundle, "drainage/network.json")
    if path_error:
        return {"status": "INCOMPLETE", "errors": [path_error], "warnings": [], "node_count": 0, "link_count": 0}
    assert path is not None
    graph, json_error = _load_json(path)
    if graph is None:
        return {"status": "INCOMPLETE", "errors": [json_error or "Invalid drainage graph"], "warnings": [], "node_count": 0, "link_count": 0}

    errors: list[str] = []
    warnings: list[str] = []
    for field in ("source", "crs", "horizontal_unit", "nodes", "links"):
        if graph.get(field) in (None, ""):
            errors.append(f"Drainage network missing field: {field}")
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    links = graph.get("links") if isinstance(graph.get("links"), list) else []
    if not nodes:
        errors.append("Drainage network must contain nodes")
    if not links:
        errors.append("Drainage network must contain links")

    node_ids: set[str] = set()
    unsurveyed_nodes = 0
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"Node {index} must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"Node {index} needs a non-empty string id")
            continue
        if node_id in node_ids:
            errors.append(f"Duplicate drainage node id: {node_id}")
        node_ids.add(node_id)
        if node.get("latitude") is None or node.get("longitude") is None:
            errors.append(f"Node {node_id} is missing latitude/longitude")
        else:
            try:
                latitude, longitude = float(node["latitude"]), float(node["longitude"])
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"Node {node_id} has invalid latitude/longitude")
        if node.get("rim_elevation_m") is None or node.get("invert_elevation_m") is None:
            errors.append(f"Node {node_id} is missing rim_elevation_m/invert_elevation_m")
        else:
            try:
                rim = float(node["rim_elevation_m"])
                invert = float(node["invert_elevation_m"])
                if not (math.isfinite(rim) and math.isfinite(invert)):
                    raise ValueError
                if rim < invert:
                    warnings.append(f"Node {node_id} rim elevation is below invert elevation; review vertical datum/fields")
            except (TypeError, ValueError):
                errors.append(f"Node {node_id} has invalid rim_elevation_m/invert_elevation_m")
        if node.get("survey_status") not in {"surveyed", "verified", "as_built"}:
            unsurveyed_nodes += 1
    if unsurveyed_nodes:
        warnings.append(f"{unsurveyed_nodes} node(s) lack surveyed/verified/as_built status")

    link_ids: set[str] = set()
    unsurveyed_links = 0
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(f"Link {index} must be an object")
            continue
        link_id = link.get("id")
        if not isinstance(link_id, str) or not link_id.strip():
            errors.append(f"Link {index} needs a non-empty string id")
        elif link_id in link_ids:
            errors.append(f"Duplicate drainage link id: {link_id}")
        else:
            link_ids.add(link_id)
        from_node, to_node = link.get("from_node"), link.get("to_node")
        if (
            not isinstance(from_node, str)
            or not isinstance(to_node, str)
            or from_node not in node_ids
            or to_node not in node_ids
        ):
            errors.append(f"Link {link_id or index} references an unknown from_node/to_node")
        length = link.get("length_m")
        roughness = link.get("roughness_manning_n")
        diameter = link.get("diameter_m")
        width, height = link.get("width_m"), link.get("height_m")
        if length is None or roughness is None or not (diameter is not None or (width is not None and height is not None)):
            errors.append(f"Link {link_id or index} is missing length, cross-section, or Manning roughness")
        else:
            try:
                dimensions = [float(length), float(roughness)]
                dimensions.extend([float(diameter)] if diameter is not None else [float(width), float(height)])
                if any(not math.isfinite(value) or value <= 0 for value in dimensions):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"Link {link_id or index} has non-positive or invalid length/section/roughness")
        if link.get("survey_status") not in {"surveyed", "verified", "as_built"}:
            unsurveyed_links += 1
    if unsurveyed_links:
        warnings.append(f"{unsurveyed_links} link(s) lack surveyed/verified/as_built status")
    if graph.get("horizontal_unit") not in (None, "m", "metre", "meter", "metres", "meters"):
        errors.append("Drainage horizontal_unit must be metres")
    return {
        "status": "STRUCTURE_VALID" if not errors else "INCOMPLETE",
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes),
        "link_count": len(links),
        "surveyed_nodes": len(nodes) - unsurveyed_nodes,
        "surveyed_links": len(links) - unsurveyed_links,
    }


def _observations_check(bundle: Path) -> dict[str, Any]:
    path, path_error = _resolve_bundle_file(bundle, "observations/depth_observations.csv")
    if path_error:
        return {"status": "INCOMPLETE", "errors": [path_error], "warnings": [], "row_count": 0}
    assert path is not None
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            columns = set(reader.fieldnames or [])
            missing_columns = sorted(OBSERVATION_FIELDS - columns)
            if missing_columns:
                errors.append("Observation CSV missing columns: " + ", ".join(missing_columns))
            event_counts: dict[str, int] = {}
            source_ids: set[str] = set()
            valid_rows = 0
            invalid_rows = 0
            dry_rows = 0
            for row_number, row in enumerate(reader, start=2):
                row_errors: list[str] = []
                event_id = (row.get("event_id") or "").strip()
                if not event_id:
                    row_errors.append("event_id")
                timestamp = _parse_utc(row.get("event_time_utc"))
                if timestamp is None:
                    row_errors.append("event_time_utc")
                try:
                    latitude = float(row.get("latitude", ""))
                    longitude = float(row.get("longitude", ""))
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        raise ValueError
                except (TypeError, ValueError):
                    row_errors.append("latitude/longitude")
                try:
                    depth = float(row.get("depth_cm", ""))
                    if not math.isfinite(depth) or depth < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    row_errors.append("depth_cm")
                    depth = None
                if not (row.get("measurement_method") or "").strip():
                    row_errors.append("measurement_method")
                source_id = (row.get("source_id") or "").strip()
                if not source_id:
                    row_errors.append("source_id")
                else:
                    source_ids.add(source_id)
                if (row.get("validation_status") or "").strip().lower() not in VALIDATION_STATUSES:
                    row_errors.append("validation_status")
                if row_errors:
                    invalid_rows += 1
                    if invalid_rows <= 10:
                        errors.append(f"Observation row {row_number} has invalid/missing: " + ", ".join(row_errors))
                    continue
                valid_rows += 1
                event_counts[event_id] = event_counts.get(event_id, 0) + 1
                if depth == 0 or (row.get("observed_condition") or "").strip().lower() == "dry":
                    dry_rows += 1
    except (OSError, csv.Error) as exc:
        return {"status": "INCOMPLETE", "errors": [f"Cannot read observation CSV: {type(exc).__name__}"], "warnings": [], "row_count": 0}

    if "observed_condition" not in columns:
        warnings.append("Add observed_condition (wet/dry) so false-alarm performance can be checked explicitly")
    if valid_rows == 0:
        errors.append("Observation CSV contains no valid measured-depth rows")
    if dry_rows == 0:
        warnings.append("No dry/zero-depth observations are present")
    if len(event_counts) < 2:
        warnings.append("At least two independent storm events are needed for event-wise holdout validation")
    return {
        "status": "STRUCTURE_VALID" if not errors and valid_rows > 0 else "INCOMPLETE",
        "errors": errors,
        "warnings": warnings,
        "row_count": valid_rows + invalid_rows,
        "valid_row_count": valid_rows,
        "invalid_row_count": invalid_rows,
        "storm_event_count": len(event_counts),
        "source_count": len(source_ids),
        "dry_or_zero_depth_count": dry_rows,
        "event_counts": event_counts,
    }


def validate_sih_data_bundle(bundle_dir: str | Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    """Check the local operational data bundle without decoding large assets."""
    bundle = Path(bundle_dir)
    if not bundle.is_absolute():
        bundle = (PROJECT_ROOT / bundle).resolve()
    else:
        bundle = bundle.resolve()
    components = {
        "rainfall": _rainfall_check(bundle),
        "terrain": _terrain_check(bundle),
        "drainage": _drainage_check(bundle),
        "observations": _observations_check(bundle),
    }
    complete = all(component["status"] == "STRUCTURE_VALID" for component in components.values())
    try:
        display_bundle = bundle.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_bundle = bundle.name
    return {
        "problem_statement_id": "26085",
        "bundle_directory": display_bundle,
        "status": "STRUCTURE_VALID_REQUIRES_DOMAIN_REVIEW" if complete else "INCOMPLETE",
        "all_component_schemas_valid": complete,
        "components": components,
        "limitations": [
            "This is a structural preflight, not a data-quality certification or model-accuracy test.",
            "Raster, NetCDF, GRIB, and other binary contents are not decoded; only their paths and non-zero sizes are checked.",
            "Hydraulic plausibility, source authorization, coordinate coverage, and observation independence require expert review.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight the SIH 26085 rainfall/DEM/drainage/observation data bundle")
    parser.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE), help="Bundle folder (default: data/operational_bundle)")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    args = parser.parse_args()
    report = validate_sih_data_bundle(args.bundle_dir)
    print(json.dumps(report, indent=None if args.compact else 2, ensure_ascii=False))
    return 0 if report["all_component_schemas_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
