# Data Provenance and Prototype Limitations

This review covered the dashboard, local and serverless APIs, fetch/model/training code, generated CSVs, map and graph assets, historical reports, deployment metadata, README/docs, and the submission presentation. It distinguishes forecasts, observations, registry-entered historical estimates, assumptions, and synthetic demo values. Links inside historical records were not individually checked against every cited source.

## What the running app can use

- **Forecast mode:** Requests 15-minute precipitation forecast-model output from the Open-Meteo Forecast API for one Dwarka pilot coordinate. This is not a local rain-gauge reading or IMD radar image. Open-Meteo documents that 15-minute values outside North America and Central Europe may be interpolated from hourly output: [Forecast API documentation](https://open-meteo.com/en/docs).
- **Forecast connection diagnosis:** The old backend used a 3-second timeout and collapsed HTTP errors, timeouts, and network failures into the same generic banner. It now waits up to 6 seconds, returns a safe diagnostic code/message, supports an explicit refresh request, and the active dashboard retries every 15 minutes. JSON responses include an API-version header; the dashboard asks for a server restart if it receives a response from an older still-running process. A refused loopback proxy is named as a proxy configuration failure. Open-Meteo's public API does not require an API key; the keys in `.env` do not authenticate that request. This execution environment's Python proxy points to a loopback sink and refuses outbound connections, so a successful live provider response could not be confirmed here.
- **Depth output:** When forecast input and the model artifact are available, a RandomForest surrogate produces unvalidated estimates using a deterministic hydraulic formula and assumed graph parameters. There is no independent local measured-depth validation set, so no real-world accuracy score can be stated.
- **Fallback behavior:** Missing, stale, invalid, or unsupported inputs return unavailable/null metrics. Missing coverage is no longer shown as 0 cm, green, dry, or safe. During the latest local run, the Open-Meteo request did not succeed; the UI correctly showed unavailable.
- **Map:** OpenStreetMap tiles provide geographic context. The base map is not a flood layer. Depth styling appears only with usable model estimates; no live radar or water-level sensor layer is connected.
- **Demo mode:** Uses fixed synthetic scenarios. They are not observations or forecasts. The animated rain image is a decorative simulation and is only available in Demo mode.
- **Routes and alerts:** Road geometry may come from the public OSRM service. Nearby depth comparisons are sparse unvalidated model estimates, not measurements on roads. Routes are not safety-certified. Alert endpoints prepare local previews and do not contact agencies or send SMS.

## Local data and model findings

- `src/data/vashu.csv` contains project-curated incident records with citation fields. Two rows are short by one final field; the registry extractor now skips incomplete rows and does not invent missing elevation or hydraulic values.
- `src/data/pothole_depression_registry.json` contains 24 retained historical records. Depths are estimates entered in the local source CSV, not independently checked source claims or observed measurements. Records carry validation and coordinate-quality labels; URLs and confidence fields have not been independently verified.
- `data/scraped_ground_truth_pilot.csv` has a header and no observation rows. The cited flood-report CSVs do not provide an independent measured-depth validation dataset.
- The 15,264-row rainfall CSV and 76,320-row hydraulic CSV contain generated formula features/labels. Their weather-workbook provider and version provenance is not preserved sufficiently to authenticate the historical rainfall series. Reflectivity-like columns and depth/hazard fields are now named as rainfall proxies and formula estimates.
- `models/dwarka_hydraulic_model.pkl` is a RandomForest surrogate. The current training script labels formula-generated hydraulic outputs and adds synthetic rain/geometry combinations. Its training metrics are formula-reproduction metrics, not flood-prediction accuracy. The existing pickle was not retrained in this pass and has no embedded provenance record; see `models/model_provenance.json`.
- The feature matrix has nine columns—rain intensity, 3-hour rain, rainfall-derived reflectivity proxy, imperviousness, effective drain capacity, Manning roughness, slope, cross-section area, and catchment area—but these are not nine independent measured drivers. Imperviousness is fixed at 0.85 and drainage capacity/elevation inputs are schematic. Formula-labelled workbook rows and synthetic augmentation cannot provide observed-depth accuracy.
- `src/model_train.py` now fails closed by default. Its opt-in formula-surrogate demo writes separate demo artifacts and cannot replace the runtime model.
- `src/dwarka_drainage_graph.json` has 6 nodes and 5 edges. The other configured map zones do not have validated depth coverage. OSM caches contain 30 pilot, 2 ITO, and 135 Palam drain-like features, but the DEM caches have zero elevation points. The offline graph builder fills missing elevation with 215 m and estimates missing dimensions/catchments; using its output as operational prediction data would add assumptions, not verified coverage.
- Runtime graph geometry in `src/dwarka_drainage_graph.json` is schematic. Node elevations, drain sizes, capacities, and connectivity are not independently surveyed. The static graph asset now mirrors the runtime graph and carries the same limitations.
- `src/data/dwarka_elevation_grid.json` and cached DEM files have no independently checked retrieval/provenance record. The fetch script now marks fallback elevation values as synthetic and not measurements.
- The catchment polygon is a manually defined prototype boundary, not official service coverage. The old static `dwarka_live_radar.json` was a stale all-zero fixture and is now marked disabled so it cannot be mistaken for current radar data.
- **Additional-source review:** Open-Meteo's public endpoint requires no key, so the supplied unrelated keys cannot fix this request. IMD's published AWS API documentation says the caller's public IP must be whitelisted; station weather data is not road-level flood depth. IMD's archived hourly rainfall data for Delhi/NCR is supplied through a chargeable data process. [IMD API guide](https://mausam.imd.gov.in/imd_latest/contents/api.pdf) · [IMD Delhi data-supply process](https://mausam.imd.gov.in/newdelhi/docs/data-procedure.pdf).

## Changes made

- Added responsive **Simple View** and **Technical View** dashboards and retained the interactive OpenStreetMap panel.
- Added 6-second forecast networking diagnostics, a manual refresh control, provider-retrieval/cache status, and a 15-minute refresh while the dashboard is active.
- Added backend-version detection so a long-running stale server cannot leave the dashboard showing an unexplained generic provider failure.
- Prevented formula/synthetic surrogate training from overwriting the model used by the live endpoint.
- Made forecast and estimate provenance visible in both views; relabelled Demo as synthetic.
- Removed false radar/gauge, safety-clearance, verified-hotspot, agency-dispatch, and fabricated-performance claims from the UI, API descriptions, docs, and submission PDF.
- Prevented null depth values and nodes without model coverage from rendering as green zero-depth readings.
- Removed fixed vehicle water-clearance thresholds and route “safe” claims.
- Changed data-generation and model-training scripts to preserve formula/synthetic provenance and avoid fabricating DEM-based drainage integrations.
- Replaced the stale radar fixture, relabelled generated training columns and low-depth categories, and documented model provenance.

## What is needed for an operational service

Connect authenticated local rainfall/radar feeds, calibrated water-level sensors or surveyed event depths, a surveyed and versioned drainage inventory, independent event-based validation, and reviewed warning and routing procedures. Until then, use official advisories for travel decisions and treat every model value as an unvalidated estimate.
