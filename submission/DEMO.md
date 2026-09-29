# Prototype Walkthrough

1. Start the local server with `python src/main.py` and open `http://127.0.0.1:8083/`.
2. Show **Simple View** and **Technical View** to compare the public-facing summary with the model/input details.
3. Open **Interactive Map** to show the OpenStreetMap base layer and its prototype bounds.
4. Show Forecast mode and its provider/status labels. If Open-Meteo is unavailable, the dashboard switches to a labelled synthetic scenario; do not call the scenario a live forecast.
5. Open Technical View to identify the active depth backend (local RandomForest, remote RandomForest, or formula) and describe all mapped depth bands as unvalidated model estimates.
6. Compare a route and show its map geometry. OSRM directions can fall back to the bundled OSM road extract; ETA is approximate and the result is not a flood-safety clearance. The alert preview does not send an agency message.

All depth values are unvalidated estimates. Check official local advisories for actual conditions.
