# SIH 26085 data readiness and acceptance criteria

The prototype exposes a read-only readiness report at:

- Local server: `GET /api/v1/data-readiness`
- Vercel API: `GET /api/data-readiness`

The report describes the assets available to the running process. It does not
run a flood forecast, unpickle the Random Forest artifact, contact data
providers, or change the existing forecast response. `PROTOTYPE_ONLY` means
one or more required components are missing or unvalidated; it must not be
presented as an operational street-depth service.

## Local data bundle preflight

Put externally obtained, authorized inputs under `data/operational_bundle/`:

```text
data/operational_bundle/
  rainfall/manifest.json
  rainfall/<provider rainfall files>
  terrain/manifest.json
  terrain/<DEM or DTM raster>
  drainage/network.json
  observations/depth_observations.csv
```

Run the structural preflight from the repository root:

```powershell
python -B src/sih_data_bundle.py
```

It checks required metadata, file existence and non-zero size, timestamp and
coordinate syntax, observation fields, and drainage link references. It does
not decode raster/netCDF/GRIB contents, confirm provider permissions, prove
that records are independent, validate hydraulic values, or measure model
accuracy. A `STRUCTURE_VALID_REQUIRES_DOMAIN_REVIEW` result means the bundle
passed only those mechanical checks. The API readiness report includes the
same preflight under `operational_bundle_preflight`.

Manifest contract:

- `rainfall/manifest.json`: `provider`, `product`, `product_type`,
  timezone-aware `issue_time_utc`, `time_step_minutes`, `units`, `crs`,
  `bbox_wgs84` as `[west, south, east, north]`, `valid_times_utc` as a list
  of timezone-aware ISO-8601 timestamps, `spatial_representation` equal to
  `grid`, positive `grid_cell_size_m`, and `data_files` as paths relative to
  the bundle. `product_type` must identify `radar_qpe`, `radar_nowcast`, or
  `radar_nwp_blend`; a point series or historical reanalysis does not qualify
  as the radar-grid input. Declare `gauge_bias_correction` and
  `gauge_bias_method` when applicable. Retain the provider's original files
  and metadata; normalize units and grid orientation in a documented
  processing step before routing.
- `terrain/manifest.json`: `raster_file` (bundle-relative), `source`, `crs`,
  `horizontal_unit` in metres, `cell_size_m`, `vertical_accuracy_m`,
  `vertical_datum`, and `processing_notes`. Five metres is the project's
  initial street-scale screening target, not a guarantee of adequate terrain
  accuracy. Check the raster's actual CRS, nodata, vertical datum, and grid
  alignment with a geospatial reader before use.
- `drainage/network.json`: `source`, `crs`, `horizontal_unit`, `nodes`, and
  `links`. Each node needs a unique `id`; include `latitude`, `longitude`,
  `rim_elevation_m`, `invert_elevation_m`, and `survey_status`. Each link needs
  a unique `id`, `from_node`, `to_node`, `length_m`, `roughness_manning_n`,
  `survey_status`, and either `diameter_m` or both `width_m` and `height_m`.
  Retain unknown/assumed properties as explicitly labelled metadata instead of
  filling them with guessed survey values.
- `observations/depth_observations.csv`: required columns are
  `event_id,event_time_utc,latitude,longitude,depth_cm,measurement_method,validation_status,source_id`.
  Use timezone-aware timestamps, centimetres, measured zero depths for dry
  locations, and `verified`, `surveyed`, or `sensor` for `validation_status`
  only when supported by provenance. Add `observed_condition` (`wet`/`dry`)
  to make false-alarm evaluation explicit. Keep complete storms together for
  train/validation/test splits.

The preflight reports warnings for short rainfall horizons, missing bias
correction provenance, coarse terrain cells, unsurveyed/underspecified drain
properties, and absent dry or multiple-event observations. Those warnings
still need to be resolved or accepted explicitly before calibrating a model.

## Audit of previously shared candidate files

The desktop files `najafgarh` and `dwarka` are CSV-formatted hourly point
weather histories (despite having no filename extension). Each has 96,792
rows from 2015-09-04 through 2026-09-18 and coordinates recorded in its
metadata. Their `rain (mm)` and `precipitation (mm)` columns are identical in
both files. They do not identify an observing gauge, radar product, provider
model/version, or gridded coverage. The two points are approximately 5.4 km
and 6.5 km from the nearest nodes in the current schematic pilot graph. Treat
them only as candidate historical point forcing until the source/model and
license are confirmed; they are not radar rainfall observations and do not
meet the operational rainfall contract above.

`dwarka_flood_dataset_extended_v2.csv` has 48 location rows on 25 dates. It
contains 45 positive labels and 3 negative controls, 30 numeric depth entries
(27 non-zero), and 11 rows marked as having local rainfall measurements. The
three zero-depth negative rows are explicitly described in their notes as
negative-control samples, not surveyed dry outcomes. Coordinate precision is
mixed: 16 rows are marked low precision, while 19 are marked exact or high;
only 16 rows fall within 3 km of one of the current six schematic graph nodes.
The table combines Dwarka, adjacent areas, and Delhi-wide cases, and its
event-date field does not give measurement time-of-day. Source URLs and
confidence labels still need row-by-row verification before reported depths
are treated as labels. Spot checks found official records that confirm
waterlogging occurrence without supporting the table's numeric depth: the
[Delhi 2008 slide deck](https://environment.delhi.gov.in/sites/default/files/inline-files/aemc18_sept_2008.pdf)
labels waterlogging at Dwarka Sector 20 but does not state 40 cm; the
[Delhi Flood Control Order 2023](https://ifc.delhi.gov.in/sites/default/files/ifc/universal/fco-2023.pdf)
lists the Road 219 / K.M. Chowk to Ashirwad Chowk Dwarka Sector 12 incident on
22 July 2018, but does not state 45 cm. The official [Flood Control Order
2025](https://ifc.delhi.gov.in/sites/default/files/ifc/circulars-orders/fco_2025.pdf)
lists waterlogging in Dwarka Sectors 19, 20, 21, and 23 on 28 June 2024, but
does not provide the table's 68 cm or 110 cm depths. Those documents support
incident occurrence only; the numeric depths remain unverified from the
linked evidence checked here.

This incident table can support a curated event timeline and exploratory case
studies. It is not balanced or independently surveyed enough to validate a
street-depth model, and the rows must not be split randomly as if they were 48
independent storms. The two hourly histories may support a separate historical
rainfall baseline after provenance and event-time alignment are verified.
Neither dataset has been copied into the runtime bundle or used to retrain the
Random Forest.

## Newly acquired public reference layers

The project now includes two small, clipped public raster references under
`data/reference/`. They were extracted from source Cloud-Optimized GeoTIFFs by
HTTP byte-range reads; the full source tiles were not copied into the repository.
Each asset has a sidecar JSON with source, bounds, license/attribution, extraction
details, limitations, and SHA-256. `scripts/extract_worldcover_pilot.py` reproduces
the land-cover crop and requires optional `rasterio` and `numpy` packages.

- `terrain/copernicus_glo30_dwarka_pilot.tif` is a Copernicus GLO-30 Public 2021
  DSM crop at about 30 m. It includes buildings and vegetation, is not
  hydrologically conditioned, and does not meet the street-scale DTM requirement.
- `landcover/esa_worldcover2021_dwarka_pilot.tif` is ESA WorldCover 2021 v200 at
  about 10 m. About 77.3% of valid pixels in this buffered rectangular crop are
  labelled built-up. That fraction is not a measured impervious fraction and
  must not be used directly as a runoff coefficient. WorldCover reports 76.7%
  global overall accuracy; local/class accuracy differs.

These layers are listed separately in the readiness response as
`supplementary_reference_layers`; they are not fed to the model and do not change
the `PROTOTYPE_ONLY` status or support a prediction-accuracy claim.

## Najafgarh drainage-plan context

The project also includes `src/data/najafgarh_dmp_2018_context.json`, a cited
summary of Section 3.3 of the [2018 IIT Delhi / IFCD Drainage Master Plan](https://ifc.delhi.gov.in/sites/default/files/inline-files/main_report_dmp_version51.pdf). The
Technical View presents the report's basin-wide Table 3.3-2 land-use values as
a chart and summarizes its regional flow, pump, depression, and storage
concepts. The report's scenarios are used to explain model-design lessons,
including the need to validate drain slopes and evaluate downstream effects.

This is reference material only. The chapter reports that department-supplied
survey inputs had not been fully vetted and uses assumed storage depths in
some scenarios. The charts/maps do not provide a current Dwarka subcatchment
vector, street-level depth observations, or local impervious percentages. The
summary is not consumed by forecast inference or model training and does not
change operational readiness.

Sources: [Copernicus DEM open data registry](https://registry.opendata.aws/copernicus-dem/),
[Copernicus DEM product handbook](https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf),
[ESA WorldCover data access](https://esa-worldcover.org/en/data-access), and
[WorldCover 2021 product manual](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PUM_V2.0.pdf).

## Required inputs before claiming street-depth predictions

| Component | Minimum evidence expected | Current project status |
| --- | --- | --- |
| Rainfall forcing | Machine-readable radar QPE/nowcast covering the pilot, valid and issue times, units, spatial reference, freshness checks, and gauge-bias-correction provenance. The 0–3 h feed should retain uncertainty and identify any NWP blend. | One-coordinate Open-Meteo forecast-model input; not a radar grid. NASA IMERG is a possible retrospective/coarse satellite rainfall reference, not a Doppler-radar nowcast, and is not currently part of the runtime. |
| Terrain | Georeferenced terrain raster with documented source, horizontal resolution, vertical accuracy/datum, and treatment of roads, buildings, and depressions. | 25 unverified elevation points plus a public 30 m DSM reference crop; no locally verified, conditioned street-scale DTM. |
| Drainage network | Surveyed nodes/links, coordinates, invert and rim levels, dimensions, roughness, connectivity, catchments, inlet capture, capacity, and outfall boundary conditions. Unknown or estimated properties must stay labelled. | Six nodes and five schematic links, with assumed properties; existing OSM extract contains waterway features and two inlet records, not a verified municipal pipe network. |
| Coupled hydraulics | 1D drainage routing coupled bidirectionally and with mass accounting to 2D surface flow, including surcharge and backflow. | No 2D surface solver or verified coupling module detected. |
| Validation observations | Independent, time/location-linked depth observations with measurement method and source, including dry/negative locations. Hold out complete storm events from calibration/training. | The pilot ground-truth CSV is header-only; independent observed-depth validation is false in model provenance. |
| Runtime model | The deployed inference path, artifact, model version, and reported provenance must match. A formula-only fallback must be labelled as such. | Local `/api/v1/nowcast` uses the local RandomForest when the artifact is present (set `SIH_LOCAL_INFERENCE_BACKEND=formula` to force the formula). Vercel uses the lightweight formula unless a healthy remote HF/Render inference endpoint is configured. The RF targets are formula-derived/synthetic and have no observed-depth validation. |

## Recommended validation protocol

1. Split by complete storm event, not random rows or timestamps from the same storm.
2. Compare rainfall persistence, the calibrated hydraulic solver, and the ML surrogate on identical held-out events.
3. Report depth MAE/RMSE and bias in centimetres, flood-threshold precision/recall and critical-road misses, and skill by forecast lead time.
4. For probabilistic forecasts, report calibration/reliability and interval coverage alongside point errors.
5. Include data freshness, missing-input behavior, inference latency, and the percentage of the pilot area with valid coverage.
6. Do not infer dry/safe from missing data, do not describe formula-derived labels as observed depths, and do not label a route safe without validated coverage and reviewed routing rules.

## Model training and deployment

Use a calibrated 1D/2D solver to generate a physically consistent scenario archive,
then train a fast graph/spatiotemporal surrogate against the solver and calibrate
it against independent observations. Random Forest may be retained as a baseline
or residual model, but the existing formula-surrogate has no observed-depth
validation and cannot support a real-world accuracy claim.

The current large pickle is not loaded by the readiness endpoint. Keep model
artifacts outside ordinary Git history; if an artifact is later validated,
publish a versioned artifact with a checksum and configure the production API to
load that exact version. The opt-in `--compact-demo` trainer writes a separate,
compressed formula-label demo for size experiments; it does not create
field-validated predictions and must not replace the production path by itself.

## Public drainage schedule context

The project also stores the Najafgarh-block drain schedule and regulator-level values transcribed from the 2025 Flood Control Order in `data/reference/drainage/`. These planning schedules identify named drains and design summaries, but have no GIS geometry or street-level asset attributes and do not replace the schematic six-node/five-link graph. The inferred unit headings in the drain table should be confirmed with I&FC before engineering use. See `docs/STORM_DRAIN_DATA_ACQUISITION.md` for the agency request sequence and data checklist.
