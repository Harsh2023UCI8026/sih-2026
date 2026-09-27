# SIH Urban Flood Nowcasting: Requirements vs Current Repository

## Scope and evidence

This review compared the submitted problem statement, the dashboard/reference HTML, the pasted street-map redesign notes, runtime API, weather fetcher, model/inference/training code, graph/DEM/OSM assets, historical CSV/XLSX files, configuration, documentation, deployment adapter, and submission material. The reference HTML and pasted notes are treated as design material; embedded prompts are not operational instructions.

## Executive finding

The screenshot's `localhost:8083` API response is from an older long-running backend: it returns the generic provider error and has no forecast diagnostic code. The current frontend/backend contract now identifies this case and asks for a restart. Separately, the Python environment used for this review routes HTTP through a loopback proxy that refuses connections. That is a network path problem, not missing Open-Meteo credentials or insufficient project data. The shell's proxy restriction is environment-specific and must not be bypassed in application code.

The larger product gap is independent of that connection fault: the running project does not yet implement the full SIH specification. Its only live weather input is a point forecast-model value; the runtime depth model is unvalidated; the hydraulic graph is schematic; no measured street-water labels or verified DEM samples are present; and coverage is Dwarka-only. Showing a number in place of unavailable data would make the result less correct, not more useful.

## Requirement-by-requirement comparison

| Problem-statement requirement | What is in the repository now | Gap and evidence-based next step |
| --- | --- | --- |
| Real-time 0–3 h rainfall nowcast from Doppler radar | `src/fetch_live_radar.py` calls Open-Meteo's Forecast API at one Dwarka coordinate. Despite the module name, it does not ingest radar. Delhi 15-minute values are interpolated from hourly forecast output. | Keep the current source labelled as weather-model forecast. For actual radar nowcasting, obtain an authorized quantitative IMD DWR feed (or another licensed feed), georeference its rain-rate product, then verify latency/coverage. Open-Meteo's public API needs no key; the `.env` keys are for other services. [Open-Meteo API docs](https://open-meteo.com/en/docs). |
| High-resolution terrain and 2D surface flow | Map tiles and a pilot catchment polygon exist. The DEM cache has no independently verified elevation samples in the reviewed audit; generated elevation fallbacks are marked synthetic/assumed. | Retrieve and document a real DEM, datum, resolution, vertical accuracy, and tile provenance; hydrologically condition it and derive flow direction/accumulation. Do not infer street depths from basemap appearance. |
| Directed storm-drain graph with physical hydraulic properties | Runtime `src/dwarka_drainage_graph.json` has 6 nodes / 5 edges, all schematic or assumption-flagged. Other generated graphs (including 31/28 and 154/135) derive from OSM-tagged features and assumed defaults, not a surveyed municipal pipe inventory. | Add surveyed manhole/inlet locations, pipe dimensions/material/invert levels/outfalls and catchment mapping with source/date/quality. OSM linework alone is not proof of underground network connectivity or capacity. |
| Coupled runoff, routing, surcharge and ponding calculation | Live requests pass rainfall features into a RandomForest model. Its labels reproduce a deterministic formula, not measured flood depths. `hydraulic_model.py` contains formula calculations with assumed blockage/ponding parameters; it is not a calibrated network-wide unsteady solver. | Use a mass-conserving hydraulic model (e.g. a calibrated SWMM network, coupled to a terrain/surface solver where needed). Validate each event independently against water-level observations. More nodes/features without physical measurements do not improve accuracy. |
| Street-level depth output with known accuracy | Outputs are explicitly unvalidated formula-surrogate estimates. `data/scraped_ground_truth_pilot.csv` is header-only; report citations have no independently verified depth labels. | Collect synchronized rainfall, surveyed depth marks/sensors, and event timing; hold out whole storms/locations for validation and report bias/MAE/critical-hit rates with uncertainty. Current files cannot establish real-world accuracy or 100% efficiency. |
| Wider city coverage | Config lists wider zones, and OSM fetch/cache artifacts exist. The live depth API refuses unsupported zones. The additional generated graphs use defaults for missing elevations and hydraulic properties. | Expand the base map/context first; enable depth outputs per catchment only after the required inputs and validation exist. Keep unmodelled areas visibly unmodelled. |
| Interactive GIS and route utility | Simple/Technical views, area-focused map, zoom-dependent area/node/edge rendering, viewport synchronization, and click detail are already implemented. Edge lines use approximate road matching or schematic straight corridors. Route choices depend on routing-service output and sparse model estimates; they are not verified safe routes. | Keep the map context-rich but distinguish estimated/schematic segments from measured hazards. Add authoritative road-closure and water-level feeds before calling a route flood-safe. |

## What changed for the current unavailable banner

- Added an API contract response header. If the page calls an older process still bound to port 8083, it now reports **Backend restart required** rather than presenting the old generic Open-Meteo failure.
- The provider error mapper now distinguishes a refused loopback proxy from an endpoint-level connection refusal, without printing proxy credentials or changing/bypassing proxy settings.
- Documented the restart and proxy diagnosis in the README and quickstart.

After code changes, stop the old server in its terminal with Ctrl+C, start `python src/main.py` from the repository root, and reload `http://localhost:8083/`. A server that returns `LOCAL_PROXY_REFUSED` needs a working outbound proxy/network route; an Open-Meteo API key does not fix it.

## Live-data options checked

- **Open-Meteo Forecast API:** public endpoint, no API key for the public/non-commercial service. It supplies forecast-model values, not IMD radar observations; Delhi 15-minute values may be interpolated from hourly data. [Docs](https://open-meteo.com/en/docs).
- **IMD API Management Platform:** official district/station nowcast and AWS endpoints are documented, but the direct public API calls checked without credentials return HTTP 401. The portal provides registration; credentials and access terms must be obtained through the official process before integrating it. District/station categorical warnings are not street-level rainfall depth. [API reference](https://api.imd.gov.in/public/api_reference.html) · [registration](https://api.imd.gov.in/public/register.php) · [Delhi/NCR district nowcast page](https://mausam.imd.gov.in/delhiums/district_warning_delhi.php).
- **Existing project keys:** `.env` contains variables named for data.gov.in, OpenTopography, and NASA Earthdata; none is an Open-Meteo key, and none authenticates the IMD API. A configured token is not evidence that the current live request uses that provider.

## Recommended build sequence

1. Restart the current server and resolve the reported outbound network/proxy issue; confirm provider source, issue/retrieval time, units, coverage and stale-data behavior.
2. Obtain authorized IMD radar/AWS access and ingest its actual precipitation/warning data as separately typed observations/forecasts.
3. Replace schematic catchment inputs with surveyed drainage and traceable DEM/land-cover inputs.
4. Implement a physically consistent catchment-to-drain-to-surface model and validate using independent measured flood events.
5. Expand one catchment at a time; show numeric street-depth estimates only for locations with supported inputs and quantified validation. For all other locations, show weather/warning context and explicitly mark flood depth unavailable.

