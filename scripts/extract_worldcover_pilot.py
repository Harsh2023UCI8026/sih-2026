"""Extract the ESA WorldCover 2021 land-cover crop for the Dwarka pilot.

Requires rasterio and numpy. The source is a public Cloud-Optimized GeoTIFF;
GDAL's /vsicurl/ reader fetches only the requested byte ranges.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds


ROOT = Path(__file__).resolve().parents[1]
TERRAIN = ROOT / "data/reference/terrain/copernicus_glo30_dwarka_pilot.tif"
OUTPUT_DIR = ROOT / "data/reference/landcover"
OUTPUT = OUTPUT_DIR / "esa_worldcover2021_dwarka_pilot.tif"
METADATA = OUTPUT_DIR / "esa_worldcover2021_dwarka_pilot.metadata.json"
SOURCE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_N27E075_Map.tif"
)


def main() -> None:
    if not TERRAIN.is_file():
        raise SystemExit(f"Pilot bounds raster not found: {TERRAIN}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(TERRAIN) as terrain:
        bounds = terrain.bounds

    with rasterio.Env(
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    ):
        with rasterio.open(f"/vsicurl/{SOURCE_URL}") as source:
            window = from_bounds(
                bounds.left,
                bounds.bottom,
                bounds.right,
                bounds.top,
                source.transform,
            ).round_offsets().round_lengths()
            land_cover = source.read(1, window=window)
            transform = source.window_transform(window)
            profile = source.profile.copy()
            profile.update(
                driver="GTiff",
                height=land_cover.shape[0],
                width=land_cover.shape[1],
                transform=transform,
                compress="DEFLATE",
                predictor=2,
                tiled=True,
                blockxsize=256,
                blockysize=256,
            )

    with rasterio.open(OUTPUT, "w", **profile) as destination:
        destination.write(land_cover, 1)

    classes, counts = np.unique(land_cover, return_counts=True)
    class_counts = {str(int(code)): int(count) for code, count in zip(classes, counts)}
    valid_pixels = int(np.count_nonzero(land_cover))
    built_up_pixels = int(np.count_nonzero(land_cover == 50))
    transform = profile["transform"]
    metadata = {
        "title": "ESA WorldCover 10 m 2021 v200 Dwarka pilot land-cover crop",
        "publisher": "ESA WorldCover consortium",
        "source_product": "ESA WorldCover 10 m 2021 v200 Map",
        "source_url": SOURCE_URL,
        "source_registry": "https://registry.opendata.aws/esa-worldcover/",
        "product_user_manual": (
            "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
            "v200/2021/docs/WorldCover_PUM_V2.0.pdf"
        ),
        "extraction": (
            "Cloud-Optimized GeoTIFF window read using HTTP byte ranges; clipped "
            "to the Copernicus GLO-30 pilot extent; no resampling."
        ),
        "crs": "EPSG:4326",
        "resolution_degrees": [float(profile["transform"].a), float(-profile["transform"].e)],
        "clip_bounds_wgs84": [
            float(transform.c),
            float(transform.f + land_cover.shape[0] * transform.e),
            float(transform.c + land_cover.shape[1] * transform.a),
            float(transform.f),
        ],
        "shape_rows_cols": [int(land_cover.shape[0]), int(land_cover.shape[1])],
        "nodata_value": 0,
        "pixel_counts_by_class": class_counts,
        "valid_pixel_count": valid_pixels,
        "class_50_built_up_fraction_of_valid_cutout_pixels": (
            built_up_pixels / valid_pixels if valid_pixels else None
        ),
        "class_legend": {
            "10": "Tree cover",
            "20": "Shrubland",
            "30": "Grassland",
            "40": "Cropland",
            "50": "Built-up",
            "60": "Bare / sparse vegetation",
            "70": "Snow and ice",
            "80": "Permanent water bodies",
            "90": "Herbaceous wetland",
            "95": "Mangroves",
            "100": "Moss and lichen",
        },
        "known_accuracy": (
            "The product reports 76.7% overall accuracy globally for 2021 v200; "
            "class- and region-specific accuracy varies."
        ),
        "caution": (
            "Class 50 is a land-cover category, not a measured impervious-surface "
            "fraction. Do not convert it directly to a runoff coefficient. This is "
            "a 2021 classification, not a current 2026 survey."
        ),
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "required_map_attribution": (
            "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel "
            "data (2021) processed by ESA WorldCover consortium"
        ),
        "citation": (
            "Zanaga, D. et al. (2022). ESA WorldCover 10 m 2021 v200. "
            "https://doi.org/10.5281/zenodo.7254221"
        ),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "use_status": "SUPPLEMENTARY_REFERENCE_ONLY_NOT_USED_FOR_TRAINING_OR_FORECASTS",
    }
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "metadata": str(METADATA),
                "size_bytes": OUTPUT.stat().st_size,
                "valid_pixel_count": valid_pixels,
                "class_counts": class_counts,
                "built_up_fraction_of_cutout": metadata[
                    "class_50_built_up_fraction_of_valid_cutout_pixels"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
