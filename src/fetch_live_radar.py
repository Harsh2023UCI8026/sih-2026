"""Fetch precipitation forecast input used by the Dwarka prototype.

Despite the historical module name, this module does not read an IMD radar
or a local rain gauge. Open-Meteo's Forecast API supplies model-generated
precipitation values. In India, the requested 15-minute series may be
interpolated from hourly model output; it is not a 15-minute observation.
"""

import datetime
import json
import math
import os
import tempfile
import urllib.parse
import urllib.request


OUTPUT_FILE = os.path.join(tempfile.gettempdir(), "dwarka_live_radar.json")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PILOT_COORDINATES = {"latitude": 28.6186, "longitude": 77.0319}


def fetch_live_radar_nowcast(timeout_sec=6.0):
    """Return a validated Open-Meteo precipitation forecast or raise.

    The return name is retained for compatibility with ``main.py``. The
    returned data is forecast-model output, not an observed radar product.
    Missing/null precipitation is an error; it must never be converted into
    a dry-weather observation.
    """
    params = {
        **PILOT_COORDINATES,
        "minutely_15": "precipitation,rain",
        # 24 quarter-hour steps cover the 3-hour lead plus a 3-hour window.
        "forecast_minutely_15": 24,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "UrbanFloodNowcasting/1.0"},
    )
    # Desktop environments sometimes export an HTTP(S)_PROXY pointing at a
    # local helper which is no longer running.  In that case urllib raises
    # WinError 10061 before it ever reaches Open-Meteo, even though direct
    # HTTPS works. Bypass only loopback proxies; continue honoring configured
    # corporate/non-local proxies.
    loopback_proxy = False
    for proxy_value in urllib.request.getproxies().values():
        try:
            proxy_url = proxy_value if "://" in proxy_value else f"http://{proxy_value}"
            if urllib.parse.urlparse(proxy_url).hostname in {"127.0.0.1", "localhost", "::1"}:
                loopback_proxy = True
                break
        except (TypeError, ValueError):
            continue

    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if loopback_proxy
        else urllib.request.build_opener()
    )
    with opener.open(request, timeout=timeout_sec) as response:
        payload = json.loads(response.read().decode("utf-8"))

    minutely = payload.get("minutely_15") or {}
    precipitation = minutely.get("precipitation")
    timestamps = minutely.get("time")
    if not isinstance(precipitation, list) or not precipitation:
        raise ValueError("Open-Meteo did not return minutely_15 precipitation")
    if not isinstance(timestamps, list) or len(timestamps) < len(precipitation):
        raise ValueError("Open-Meteo precipitation timestamps are missing")

    values = []
    for value in precipitation[:24]:
        if value is None:
            raise ValueError("Open-Meteo returned a null precipitation value")
        amount = float(value)
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Open-Meteo returned an invalid precipitation value")
        values.append(amount)

    result = {
        "schema_version": 3,
        "provider": "Open-Meteo Forecast API",
        "data_kind": "forecast_model",
        "model": payload.get("model", "best_match"),
        "temporal_resolution_note": (
            "Open-Meteo 15-minute precipitation values are interpolated from hourly "
            "forecast output at this location; they are not 15-minute observations."
        ),
        "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "coordinates": PILOT_COORDINATES,
        "nowcast_15min_interval_mm": values,
        "timestamps_iso": timestamps[: len(values)],
    }

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as cache_file:
            json.dump(result, cache_file, indent=2)
    except OSError:
        # The process-local response still works if the optional cache cannot
        # be written (for example, on a read-only host).
        pass

    return result


if __name__ == "__main__":
    print(json.dumps(fetch_live_radar_nowcast(), indent=2))
