# Urban Flood Nowcasting Prototype

This repository contains a Dwarka flood-dashboard prototype for the SIH 2026 problem area. It is not an operational flood-warning service and is not affiliated with or validated by a government agency.

## What the app currently uses

| Output | Current source | What it means |
| --- | --- | --- |
| Precipitation input in Forecast mode | Open-Meteo Forecast API at the Dwarka pilot coordinate | Forecast-model output, not a local rain-gauge or radar observation. Open-Meteo documents that 15-minute values can be interpolated from hourly data outside North America and Central Europe: [API documentation](https://open-meteo.com/en/docs). |
| Street-depth estimate | Local RandomForest surrogate and pilot drainage graph | An unvalidated model estimate. The surrogate was trained against a deterministic hydraulic formula using synthetic rainfall/geometry cases and assumed drain parameters. No local water-level sensor is connected. |
| Base map | OpenStreetMap tiles; route geometry may use the public OSRM endpoint | Geographic context and route geometry only; neither source supplies flood depth observations. |
| Demo mode | Precomputed synthetic storm scenarios | Interface demonstration only; not a forecast or observation. |
| Alert control | Local JSON preview endpoint | No SMS or government-agency message is sent. |

The dashboard has **Simple View** and **Technical View**, with a responsive **Interactive Map** panel. It now requests a fresh forecast when asked and refreshes the forecast every 15 minutes while the page is active. The status line shows the retrieval time and whether the server reused its short-lived cache. A provider error includes a connection/HTTP diagnostic. The API returns a version header so the dashboard can identify an older Python server that is still running after source files change; stop it with Ctrl+C and start `python src/main.py` again. A refused loopback proxy is identified separately from an Open-Meteo API-key error. Open-Meteo's public forecast API does not use the keys in `.env`; its 15-minute Delhi precipitation values are interpolated from hourly forecast output. The serialized model file has no embedded provenance metadata; `models/model_provenance.json` records the known limits of the current training pipeline.

The configured OpenTopography key is referenced by the offline DEM-fetch script only. The data.gov.in and NASA Earthdata variables are not used by the current runtime forecast or inference path.

The dashboard now returns an unavailable state instead of treating a timeout, unsupported area, missing model output, or absent route sample as 0 cm. A low or zero model estimate is not a statement that a road is dry or safe. The route comparison is restricted to the Dwarka pilot, depends on external road routing, and uses sparse model-node estimates near roads rather than measurements along road segments.

## Data and model limits

- There is no independently validated set of local observed water depths in the runtime path, so the project cannot state real-world accuracy or “most accurate” performance.
- Depth coverage consists of **6 nodes and 5 schematic drainage edges** in the Dwarka pilot. The graph's elevations, drain dimensions, capacities, catchments, and blockage values are assumptions; OSM/OSRM line geometry is only geographic context and does not verify underground drains or surface-water depths. Other configured map zones do not have a depth model.
- The runtime surrogate has nine model columns, but several carry no independent information: reflectivity is derived from forecast rain, imperviousness is fixed at 0.85, and hydraulic capacity uses assumed graph values. Its target is a deterministic formula output, not observed street water. Adding columns, nodes, or synthetic cases cannot establish predictive accuracy.
- The historical CSV and hotspot registry contain project-entered incident records with mixed coordinate precision. Depth entries and linked sources have not been independently verified; these records are not used as measured training truth.
- `data/scraped_ground_truth_pilot.csv` currently has a header and no observations. The flood-report CSV contains citations but no measured depth labels. Historical workbook files do not preserve enough provider/version metadata to establish their provenance.
- Rainfall-to-reflectivity conversion is a formula-derived model feature. The UI does not present it as measured radar reflectivity.

For a trustworthy operational model, connect authenticated local rain/radar feeds, water-level sensors or surveyed post-event depths, a surveyed drainage inventory, and an independent validation process. Until then, use the app for prototype exploration only and check official advisories for travel decisions.

`src/model_train.py` now refuses to overwrite the runtime model with its formula/synthetic training data. The optional `--allow-formula-surrogate-demo` flag writes a separate demo artifact only.

## Run locally

From the repository root:

```powershell
python src/main.py
```

The server listens on **http://localhost:8083/**. Useful endpoints:

- `GET /api/v1/nowcast?mode=live&lead_time_mins=60&zone=pilot`
- `GET /api/v1/nowcast?mode=live&lead_time_mins=60&zone=pilot&refresh=1` — force a provider request instead of reusing the recent server cache
- API JSON responses include `X-SIH-API-Version`; if the dashboard reports an old server process, stop the previous `python src/main.py` process before restarting it.
- `GET /api/v1/drainage-network`
- `POST /api/v1/route/flood-safe` — returns no flood-safety result when required inputs are unavailable
- `POST /api/v1/alert-broadcast` — prepares a preview only; it does not send messages
- `/api/docs` — API documentation

## Project entry points

- `src/index.html` — dashboard and Leaflet map UI
- `src/main.py` — local HTTP/API server
- `src/fetch_live_radar.py` — legacy-named module that fetches Open-Meteo precipitation forecast data; it does not fetch radar imagery
- `src/model_train.py`, `src/hydraulic_model.py`, `src/model_inference.py` — formula-surrogate training and inference
- `models/model_provenance.json` — known model training/validation limits
- `src/inference_api.py` — live inference and synthetic demo scenarios
- `src/data/` — graph, map geometry, historical/report-derived source files, and static assets
- `DATA_PROVENANCE_AUDIT.md` — file/data authenticity findings and remediation notes
