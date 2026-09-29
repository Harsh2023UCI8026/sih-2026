# Urban Flood Nowcasting Prototype

This repository contains a Dwarka flood-dashboard prototype for the SIH 2026 problem area. It is not an operational flood-warning service and is not affiliated with or validated by a government agency.

## What the app currently uses

| Output | Current source | What it means |
| --- | --- | --- |
| Precipitation input in Forecast mode | Open-Meteo Forecast API at the Dwarka pilot coordinate | Forecast-model output, not a local rain-gauge or radar observation. Open-Meteo documents that 15-minute values can be interpolated from hourly data outside North America and Central Europe: [API documentation](https://open-meteo.com/en/docs). |
| Street-depth estimate | Local Python API uses the RandomForest artifact when present; Vercel uses the lightweight formula unless a remote HF/Render inference endpoint is configured | An unvalidated estimate. The forest was trained against formula-derived/synthetic targets and assumed drain parameters. No local water-level sensor is connected. |
| Base map | OpenStreetMap tiles; route geometry may use the public OSRM endpoint | Geographic context and route geometry only; neither source supplies flood depth observations. |
| Demo mode | Precomputed synthetic storm scenarios | Interface demonstration only; not a forecast or observation. |
| Alert control | Local JSON preview endpoint | No SMS or government-agency message is sent. |

The dashboard has **Simple View** and **Technical View**, with a responsive **Interactive Map** panel. It now requests a fresh forecast when asked and refreshes the forecast every 15 minutes while the page is active. The status line shows the retrieval time and whether the server reused its short-lived cache. A provider error includes a connection/HTTP diagnostic. The API returns a version header so the dashboard can identify an older Python server that is still running after source files change; stop it with Ctrl+C and start `python src/main.py` again. A refused loopback proxy is identified separately from an Open-Meteo API-key error. Open-Meteo's public forecast API does not use the keys in `.env`; its 15-minute Delhi precipitation values are interpolated from hourly forecast output. The serialized model file has no embedded provenance metadata; `models/model_provenance.json` records the known limits of the current training pipeline.

The configured OpenTopography key is referenced by the offline DEM-fetch script only. The data.gov.in and NASA Earthdata variables are not used by the current runtime forecast or inference path.

The dashboard does not treat a timeout, unsupported area, missing model output, or absent route sample as 0 cm. When the live forecast cannot be reached and no recent provider cache is available, the UI switches to a clearly labelled illustrative rain scenario so the map and model flow remain explorable. A low or zero model estimate is not a statement that a road is dry or safe. Road directions are requested independently of the Dwarka depth-model footprint; flood context is sparse and unvalidated near-node information, not measurements along road segments. If OSRM returns no geometry, the route service tries the bundled local OSM road extract; if that also cannot connect the endpoints, it shows the trip endpoints and a Google Maps directions link.

## Data and model limits

- There is no independently validated set of local observed water depths in the runtime path, so the project cannot state real-world accuracy or “most accurate” performance.
- Depth coverage consists of **6 nodes and 5 schematic drainage edges** in the Dwarka pilot. The graph's elevations, drain dimensions, capacities, catchments, and blockage values are assumptions; OSM/OSRM line geometry is only geographic context and does not verify underground drains or surface-water depths. Other configured map zones do not have a depth model.
- The runtime surrogate has nine model columns, but several carry no independent information: reflectivity is derived from forecast rain, imperviousness is fixed at 0.85, and hydraulic capacity uses assumed graph values. Its target is a deterministic formula output, not observed street water. Adding columns, nodes, or synthetic cases cannot establish predictive accuracy.
- The historical CSV and hotspot registry contain project-entered incident records with mixed coordinate precision. Depth entries and linked sources have not been independently verified; these records are not used as measured training truth.
- `data/scraped_ground_truth_pilot.csv` currently has a header and no observations. The flood-report CSV contains citations but no measured depth labels. Historical workbook files do not preserve enough provider/version metadata to establish their provenance.
- Rainfall-to-reflectivity conversion is a formula-derived model feature. The UI does not present it as measured radar reflectivity.

### Najafgarh drainage-plan reference

Technical View includes a source-linked summary of the IIT Delhi / IFCD 2018 Drainage Master Plan, Section 3.3. Its land-use chart is basin-wide context from Table 3.3-2. The report describes depression storage, upstream inflows, pump/downstream interactions, and storage or low-impact-development scenarios. Its simulations use design-rainfall scenarios and include assumptions; they are not measured Dwarka outcomes.

The summary is stored in `src/data/najafgarh_dmp_2018_context.json` and served as a reference asset. The current forecast and model do not consume it. Its basin maps are not georeferenced GIS vectors, and the reported urban land-use percentage is not an impervious-surface measurement or a local runoff coefficient.

For a trustworthy operational model, connect authenticated local rain/radar feeds, water-level sensors or surveyed post-event depths, a surveyed drainage inventory, and an independent validation process. Until then, use the app for prototype exploration only and check official advisories for travel decisions.

`src/model_train.py` now refuses to overwrite the runtime model with its formula/synthetic training data. The optional `--allow-formula-surrogate-demo` flag writes a separate demo artifact only.
For a compact local size/runtime experiment, add `--compact-demo`; this still trains on formula-derived/synthetic labels and is not validated for flood prediction. Local `python src/main.py` automatically uses the existing RandomForest artifact when present; set `SIH_LOCAL_INFERENCE_BACKEND=formula` to force the lightweight formula path. Vercel uses the lightweight adapter and can call the optional Hugging Face service.

## Optional remote RandomForest backend

`deploy/hf-inference/` contains the FastAPI service and Dockerfile for either a Hugging Face Docker Space or a Render Web Service. The private HF Model repo is artifact storage; the service needs enough RAM to load the 1.53 GB model. Point Vercel's `SIH_RF_INFERENCE_URL` at the service's `/predict` endpoint only after `/healthz` reports `model_loaded: true`; when the remote service is absent or unhealthy, Vercel keeps using the lightweight formula path. Render setup, environment variables, and the free-tier memory limit are documented in [deploy/hf-inference/README.md](deploy/hf-inference/README.md).

The model artifact is about 1.53 GB. Google Drive plus `gdown` is not needed: a Hugging Face Model repo is the intended artifact source for the Space. Hugging Face's default Space disk is ephemeral, so a restart may download the file again. Current Vercel Python Functions document a standard 500 MB uncompressed bundle limit, and a separate 5 GB Large Functions beta exists for eligible Fluid Compute projects; artifact size alone no longer proves Vercel is impossible, but runtime memory, cold-start time, account eligibility, and deployment settings still need checking. The HF Space keeps the large artifact outside the Vercel dashboard bundle.

## Run locally

From the repository root:

```powershell
python src/main.py
```

The server listens on **http://localhost:8083/**. Useful endpoints:

- `GET /api/v1/nowcast?mode=live&lead_time_mins=60&zone=pilot`
- `GET /api/v1/nowcast?mode=live&lead_time_mins=60&zone=pilot&refresh=1` — force a provider request instead of reusing the recent server cache
- `GET /api/v1/data-readiness` — read-only audit of radar, terrain, drainage, coupled-solver, observed-depth, and deployment readiness for SIH PS 26085
- API JSON responses include `X-SIH-API-Version`; if the dashboard reports an old server process, stop the previous `python src/main.py` process before restarting it.
- `GET /api/v1/drainage-network`
- `POST /api/v1/route/flood-safe` — returns OpenStreetMap road alternatives even when pilot flood-depth data are missing; any nearby model context is unvalidated and never a safety clearance
- `POST /api/v1/alert-broadcast` — prepares a preview only; it does not send messages
- `/api/docs` — API documentation

## Project entry points

- `src/index.html` — dashboard and Leaflet map UI
- `src/main.py` — local HTTP/API server
- `src/fetch_live_radar.py` — legacy-named module that fetches Open-Meteo precipitation forecast data; it does not fetch radar imagery
- `src/model_train.py`, `src/hydraulic_model.py`, `src/model_inference.py` — formula-surrogate training and inference
- `src/data_readiness.py` — read-only PS 26085 readiness report; it never loads the pickle or fabricates observations
- `models/model_provenance.json` — known model training/validation limits
- `src/inference_api.py` — live inference and synthetic demo scenarios
- `src/data/` — graph, map geometry, historical/report-derived source files, and static assets
- `DATA_PROVENANCE_AUDIT.md` — file/data authenticity findings and remediation notes
- `docs/RESEARCH_AND_IMPLEMENTATION_GAP.md` — SIH target, local dataset evidence, IIT Bombay/Mumbai reference, papers, deployment cause, and next steps
- `submission/FINAL_PPT_SLIDE_PLAN.md` — recommended final deck structure and demo narration

The 2025 Flood Control Order also publishes named Najafgarh-block drain summary values and regulator levels. Extracts are stored under data/reference/drainage/; they are planning-table references without network geometry and do not replace the six-node/five-link schematic graph. See [docs/STORM_DRAIN_DATA_ACQUISITION.md](docs/STORM_DRAIN_DATA_ACQUISITION.md) for steps to request existing GIS/CAD records from the responsible agency.

The project includes an IMD / Delhi I&amp;FC data-request packet in `docs/DATA_ACQUISITION_REQUEST_DRAFT.md`. The runtime dashboard does not yet consume agency-supplied rainfall or street-depth observations.
