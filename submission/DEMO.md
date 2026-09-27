# Prototype Walkthrough

1. Start the local server with `python src/main.py` and open `http://127.0.0.1:8083/`.
2. Show **Simple View** and **Technical View** to compare the public-facing summary with the model/input details.
3. Open **Interactive Map** to show the OpenStreetMap base layer and its prototype bounds.
4. Show Forecast mode and its provider/status labels. If Open-Meteo is unavailable, the correct result is **Unavailable**; do not present that as dry weather.
5. Optionally switch to Demo mode and identify all rain animation and depth output as synthetic/model estimates.
6. Show the route comparison caveat and alert preview. Neither certifies a safe route nor sends an agency message.

All depth values are unvalidated estimates. Check official local advisories for actual conditions.
