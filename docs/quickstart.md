# Quickstart

## Run locally

From the project root, install the packages listed in `requirements.txt` if they are not already installed:

```powershell
pip install -r requirements.txt
```

Then start the server:

```powershell
python src/main.py
```

Open [http://127.0.0.1:8083/](http://127.0.0.1:8083/). The server listens on port 8083.

## Dashboard

- Choose **Simple View** for the public-facing dashboard or **Technical View** for model inputs, method, and provenance notes.
- Open **Interactive Map** to view the OpenStreetMap base map. Flood-depth colors only appear when the pilot model has a usable precipitation input.
- Forecast mode uses Open-Meteo forecast-model precipitation. It is not a rain-gauge or radar observation.
- If the banner says **Backend restart required**, stop the old server process with Ctrl+C, rerun `python src/main.py` from the repository root, and reload the page. If it reports **local proxy refused**, fix the Python server's configured outbound proxy/network path; adding an Open-Meteo API key will not help.
- Demo mode uses fixed synthetic scenarios and is labelled as a simulation.
- Street-depth results are unvalidated model estimates, not measured water levels. If the forecast feed is unavailable or the location is outside the pilot, the dashboard shows unavailable instead of treating missing data as zero or safe.
- Route options require a usable input and road-routing service response. A route estimate is not a flood-safety guarantee.
- Alert actions create a local preview only; no agency or SMS message is sent.

## Data and limitations

See [the data provenance audit](../DATA_PROVENANCE_AUDIT.md) for sources and known gaps. Forecast API availability depends on network access. This prototype has no connected local radar, rain gauge, or water-level sensors and should not be used for operational travel decisions.
