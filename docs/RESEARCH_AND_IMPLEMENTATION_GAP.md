# SIH 26085 research and implementation status

**Reviewed:** 29 September 2026  
**Scope:** the project files in this repository, the current dashboard/API paths, the supplied local reference datasets, and published urban-flood nowcasting research. The attached screenshots are treated as evidence of the UI state, not as instructions or flood observations.

## Problem statement target

SIH 26085 asks for a 0–3 hour urban-flood nowcast that couples spatial rainfall with high-resolution terrain and a directed, georeferenced storm-drain network; predicts surface inundation at streets/intersections; presents results in a GIS dashboard; and supplies route alternatives using flood exposure. That target needs four different evidence classes to agree: rainfall forcing, terrain/roads, surveyed drainage and controls, and event-linked measured water depths for calibration and evaluation.

## What this build currently does

| Requirement | Current implementation | What the evidence supports |
| --- | --- | --- |
| Forecast input | Open-Meteo hourly point forecast at one Dwarka coordinate, interpolated into 15-minute values | Point forecast-model precipitation; no IMD Doppler radar/QPE grid, gauge correction, or catchment-wide rainfall field |
| Terrain and imperviousness | Copernicus GLO-30 DSM and ESA WorldCover crop are available as reference assets; the model uses an assumed 0.85 imperviousness ratio | Context layers only; not a surveyed, hydrologically conditioned street-scale DTM or a local calibrated runoff coefficient |
| Drainage graph | Six nodes and five edges with schematic/assumed elevations, dimensions, slopes, capacities, and blockage factors | Demonstration graph only; the public I&FC/FCO extracts identify named drains and planning values but do not provide the node/pipe GIS needed to replace it |
| Surface flow | Direct runoff/Manning-capacity formula creates depth bands | Formula estimate only; no 2D shallow-water solver and no bidirectional 1D drain/2D surface exchange |
| Random Forest | Local 1.53 GB-class pickle; training code uses formula-derived targets and synthetic augmentation | A surrogate of assumptions, not a model validated against observed Dwarka street-water depths |
| Deployed inference | `api/lightweight_nowcast.py` applies the formula directly; `vercel.json` excludes the large pickle | Faster, smaller deployment with different predictions from the prior local RF path unless both paths are made consistent |
| Street-level validation | `data/scraped_ground_truth_pilot.csv` has no observed depth rows. Delhi Traffic Police/FCO extracts are incident occurrences without exact coordinates/depths | No measured depth accuracy or calibrated safe/unsafe road clearance claim |
| Route suggestions | The prior serverless adapter returned HTTP 503; the dashboard then replaced the response with a generic “No route is labeled safe” toast | That message was a disconnected route-provider code path, not a conclusion derived from rainfall. The current working tree now requests OpenStreetMap road alternatives separately from flood context |

The read-only `/api/v1/data-readiness` audit reports `PROTOTYPE_ONLY`; none of the six required operational components meets the full target. Reference data are useful, but have not been promoted into measurements or model labels.

## Supplied/local dataset review

- `data/reference/roads/dwarka_roads.geojson` is OpenStreetMap road geometry suitable for map context and route display under ODbL attribution. It does not contain flood depth or verified closure state.
- `data/reference/terrain/copernicus_glo30_dwarka_pilot.tif` is a roughly 30 m surface model, not a curb-aware bare-earth street DTM. `data/reference/landcover/esa_worldcover2021_dwarka_pilot.tif` is a 10 m land-cover reference layer. They must not be presented as a calibrated street-flow surface.
- `data/reference/drainage/` contains Delhi Drainage Map/Flood Control Order 2025 named-drain, regulator, and jurisdiction extracts. They help name likely data owners and check published planning values; missing coordinates, connectivity, pipe sizes, invert/rim levels, and survey status mean they cannot validate the current six-node/five-edge graph.
- `data/reference/waterlogging/` preserves dated Delhi Traffic Police and FCO incident candidates. These are occurrence evidence only: blank coordinates and depths remain blank; duplicated extracts are not independent samples. They can seed a geocoding/field-verification queue but not supervised depth labels or “dry” labels.
- The historical Dwarka/Najafgarh weather workbooks are point/hourly series with incomplete provider/model provenance, not DWR radar pixels. Do not call the proxy column measured reflectivity.
- `src/data/pothole_depression_registry.json` contains curated historical estimates with source/coordinate uncertainty, not a surveyed depression inventory.
- `src/data/najafgarh_dmp_2018_context.json` powers the Technical View basin-scale land-use/reference card. Its basin-wide figures and design-rainfall simulations are not used as Dwarka node elevations, model features, or measured labels.

## What the research says to build

1. **Spatial rainfall forcing:** use calibrated DWR rainfall/QPE and short-lead radar extrapolation where available; carry source, issue time, valid time, CRS, accumulation period, quality flags, and uncertainty. Blend toward numerical weather prediction as the radar lead grows, rather than treating one hourly point forecast as a street-scale rain field.
2. **A real hydraulic surface:** use a surveyed, hydrologically conditioned terrain grid/mesh with road crowns, underpasses, barriers, and depressions. Keep horizontal CRS, vertical datum, resolution, and local vertical accuracy in the asset manifest.
3. **A real drainage model:** map inlets/manholes, directed links, invert/rim elevations, sizes, roughness, outfalls, pumps/gates, and maintenance/blockage evidence. Couple 1D pipe hydraulics to 2D street-surface flow and represent surcharge exchange.
4. **Calibration before the fast surrogate:** run event simulations with the physical model, calibrate against water-level sensors and surveyed/post-event street depths, then train a compact ML surrogate on those physics runs. Hold out whole storms and locations; report depth error, flood/no-flood precision/recall or CSI, timing error, uncertainty, and runtime. Formula-label fit scores are not real-flood skill.
5. **Route ranking with explicit coverage:** intersect real road geometry with time-indexed depth/uncertainty and verified closures. Where observations/model coverage do not reach a road, show “unverified” and keep the route as a normal road-direction option only. Traffic, closures, and flood hazard are separate inputs.

Primary research references:

- Costabile et al. (2023), [“Toward Street-Level Nowcasting of Flash Floods Impacts Based on HPC Hydrodynamic Modeling … and High-Resolution Weather Radar Data”](https://doi.org/10.1029/2023WR034599), *Water Resources Research*. It studies radar-driven 2D shallow-water hydrodynamic nowcasting and street-level impacts; the authors discuss rainfall resolution and calibration as material to the result.
- Zahura et al. (2020), [“Training Machine Learning Surrogate Models From a High-Fidelity Physics-Based Model … for Real-Time Street-Scale Flood Prediction”](https://doi.org/10.1029/2019WR027038), *Water Resources Research*. Its RF emulates a high-resolution 1D/2D physics model across 16,914 road segments and reports a large runtime reduction. The transferable idea is “surrogate of a calibrated physical model”; the paper does not validate this project's formula-trained forest.
- Wu et al. (2022), [“Urban Pluvial Flood Modeling by Coupling Raster-Based Two-Dimensional Hydrodynamic Model and SWMM”](https://www.mdpi.com/2073-4441/14/11/1760), *Water*. It describes a calibrated/validated SWMM + raster 2D shallow-water coupling, a closer match to the SIH drainage/surface requirement than a runoff-capacity formula.
- Ming et al. (2025), [“City-scale high-resolution flood nowcasting based on high-performance hydrodynamic modelling”](https://doi.org/10.1016/j.ijdrr.2025.105584), *International Journal of Disaster Risk Reduction*. It evaluates a GPU-accelerated 2D shallow-water/radar nowcast framework and a 2024 event; use as a scale/performance reference, not as a ready-made Delhi dataset.

## IIT Bombay / Mumbai reference

There is a real IIT Bombay/MoES Mumbai effort behind the claim, but it should be described with its dates and scope. The government [ISTI project record](https://www.indiascienceandtechnology.gov.in/research/near-real-time-urban-flood-forecasting-system?language=en) lists Dr. Subhankar Karmakar/IIT Bombay, a 2014–2017 project, and the Mithi catchment. Its proposed components included real-time sensors, weather modelling with an urban canopy model, tidal forecasting, and an integrated flash/tidal flood inundation system. C-DAC's [2017–18 annual report](https://cdac.in/index.aspx?id=pdf_annual_report_17-18) says a WRF–Urban Canopy Model short-term hydro-meteorological forecast and preliminary real-time Mumbai flood-prediction experiment ran on PARAM Yuva-II during monsoon and was compared with actual observations. The [C-DAC project summary](https://cdac.in/index.aspx?id=achieve_high_performance_computing) also describes the IIT Bombay/MoES collaboration and heavy-rainfall simulations.

This is evidence of a past research/development and preliminary experiment, not proof that the same project is a currently operated, publicly accessible Mumbai street-routing service. Its useful design lesson is the multi-team coupling of weather, urban surface, tide, sensors, hydrology/hydrodynamics, and observed-event validation. It is not a source of Dwarka rainfall, drain geometry, or depth labels.

## Why the alert appeared, and what changed in this working tree

The deployed `api/index.py` previously returned HTTP 503 for every `/api/v1/route/flood-safe` request because the serverless adapter had no road provider. The browser threw on every non-2xx response and displayed its generic toast. The local server contained an OSRM route branch but returned early when either endpoint fell outside a small pilot polygon or a model/forecast was missing. Thus road routing and flood assessment were incorrectly tied together.

The current code changes:

- route alternatives now come from an OpenStreetMap/OSRM road graph; ETA, distance, and a short maneuver/road summary are shown;
- the public route provider has a request cache and a 1 request/second process-level gate; if it returns no geometry, a local path is traced through the bundled OSM road extract before falling back to Google Maps directions;
- road directions are still returned outside the Dwarka flood-model footprint. Nearby graph depths are attached only as unvalidated point context and are never labelled safe;
- the browser now renders the provider's route/caveat response instead of replacing it with the old generic toast;
- the Simple View no longer calls a zero-rain/0–5 cm formula band “Dry forecast” or displays a green confirmation icon. It says the street depth is unverified;
- local `src/main.py` now uses the same lightweight formula path as Vercel by default for prediction parity and latency. Set `SIH_LOCAL_INFERENCE_BACKEND=random_forest` to opt into the old local RF path for comparison; its outputs still lack observed-depth validation;
- the right-side technical panel now reserves scroll space around fixed assistant controls and shows the current six-part data-readiness snapshot plus the data-request status;
- a tightly cropped icon-only favicon replaces the full logo poster.

The FOSSGIS service is a public best-effort service with a stated maximum of one request per second; it logs route requests and requires attribution and a “fix the map” link. The working tree respects that with a short cache/rate gate and displays attribution, but a competition prototype should move to a team-operated OSRM service or a contracted provider before depending on uptime. Route travel times do not include live traffic or closures.

## 1.53 GB model and deployment path

The local pickle is 1,527,296,833 bytes (about 1.42 GiB). `.gitattributes` already tracks it with Git LFS, and the file is excluded by `vercel.json`. Git LFS solves the repository transport problem; it does not make the model fit or load quickly in a serverless function. GitHub's current [per-file LFS limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage) are 2 GB on Free/Pro. Its included quota is 10 GiB/month each for storage and bandwidth on Free/Pro ([billing details](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)); repeated versions and clones can consume that quickly.

Vercel's standard function packaging is far below this pickle size; [large Functions](https://vercel.com/kb/guide/troubleshooting-function-250mb-limit) can reach 5 GB on Fluid Compute for eligible projects, but package size alone does not solve cold-start, deserialization, or memory pressure. The safer current path is the small formula estimate, which returns promptly and is explicitly caveated. `src/model_train.py --allow-formula-surrogate-demo --compact-demo` now creates a separate compressed, bounded-tree demo RF artifact for size/runtime experiments; do not replace the deployed path with it until it is evaluated against independent measured or calibrated-physics targets. For a production model, train against physical-model runs and real events, export a compact versioned artifact (or host it as a separate model service/object store), warm/cache it, and measure memory and p95 latency on the actual hosting tier.

## Data request status

`docs/DATA_ACQUISITION_REQUEST_DRAFT.md`, `docs/IMD_RAINFALL_DATA_FETCH_GUIDE.md`, and `docs/STORM_DRAIN_DATA_ACQUISITION.md` contain the formal request language and submission steps for radar/gauges, drainage GIS, terrain, and event-linked depth observations. The team sent an initial hourly-rainfall availability inquiry to RMC New Delhi and received a reply: select Safdarjung or Palam, submit the prescribed Data Request Form, and provide a valid college ID. The formal request and station dataset are still pending; the existing drafts and their bracketed details need review before submission.

## Priority next steps

1. Confirm the actual project lead/contact and pilot boundary; submit separate requests to IMD and Delhi I&FC/MCD/PWD/DJB data owners, and record reply/license terms.
2. Turn the event-only CSVs into a geocoded field-check list. Collect observed wet and dry road-depth/time records with measurement method and uncertainty.
3. Obtain a conditioned street DTM and surveyed network, replace assumed graph values, then run/calibrate a 1D/2D model on historical events.
4. Train a storm-held-out RF/compact surrogate only after physics labels and field checks exist; report uncertainty and event-based validation.
5. Validate route segments against that time-dependent depth grid and verified closures. Until then, call the route output “road options with unverified flood exposure.”
