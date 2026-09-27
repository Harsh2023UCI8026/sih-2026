# Architecture Overview

The project is a prototype web dashboard with a Python HTTP API. `src/main.py` serves `src/index.html`, static map assets, and the `/api/v1` endpoints. `api/index.py` provides a deployment adapter for selected endpoints.

## Forecast path

1. Forecast mode requests precipitation forecast-model output from Open-Meteo for one Dwarka pilot coordinate (`src/fetch_live_radar.py`; the filename is historical and does not indicate a radar feed). Delhi's 15-minute values are interpolated from hourly output; the public API does not use an API key.
2. The API validates the provider response and a 15-minute server cache. A `refresh=1` query bypasses that cache. Missing, stale, or invalid input produces `UNAVAILABLE`; it is never converted into a zero-rain observation. Provider HTTP/network failures return a diagnostic code and message, and the active browser refreshes every 15 minutes. JSON responses carry an API contract header so the browser can detect an older server process that was not restarted after a code update; refused loopback proxies are diagnosed separately.
3. When input is available, the app produces a prototype depth-model estimate from a RandomForest surrogate and assumed/estimated drainage geometry. The current graph has 6 nodes and 5 edges in the Dwarka pilot; other map zones do not have depth-model coverage. The model has not been independently validated against measured street-water depths, so the response is labelled `UNVALIDATED_MODEL_ESTIMATE`.
4. The browser renders the OpenStreetMap base map, forecast status, model estimates, and source/quality labels. It does not display a live radar layer or local water-sensor readings.

## Other paths

- Demo mode uses fixed synthetic scenarios. These are demonstration inputs and never represent current weather.
- Route options use a road-routing response where available and are still unverified estimates. No route is described as safe.
- Alert endpoints return a preview response. They do not send SMS or contact an agency.
- Historical flood reports and cited hotspot records have mixed provenance and are not treated as measured training truth.

## Trust boundary

Open-Meteo precipitation is forecast-model output, not a local observation. Drainage geometry contains estimated or schematic values. No authenticated local radar, rain-gauge, or water-level feed is connected. The prototype is not an operational warning service.
