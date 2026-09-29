"""Road-route alternatives with an explicitly separate flood-context estimate.

Road geometry comes from an OpenStreetMap routing service. Any optional depth
context is a sparse, unvalidated dashboard estimate near schematic pilot nodes;
it is not a measurement along a street and never certifies a route as safe.
"""

from __future__ import annotations

import json
import heapq
import math
import os
import threading
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import ProxyHandler, Request, build_opener, getproxies


_CACHE_TTL_SECONDS = 60
_MIN_REQUEST_GAP_SECONDS = 1.05
_ROUTE_CACHE: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()
_LAST_PUBLIC_REQUEST = 0.0
_LOCAL_ROADS_PATH = Path(__file__).resolve().parent.parent / "data" / "reference" / "roads" / "dwarka_roads.geojson"
_LOCAL_GRAPHS: dict[str, tuple[dict[tuple[float, float], list[tuple]], dict[tuple[float, float], tuple[float, float]]]] = {}
_LOCAL_GRAPH_LOCK = threading.Lock()

_PROFILE = {
    "car": ("routed-car", "driving"),
    "ambulance": ("routed-car", "driving"),
    "suv": ("routed-car", "driving"),
    "rickshaw": ("routed-car", "driving"),
    "auto": ("routed-car", "driving"),
    "bike": ("routed-bike", "cycling"),
    "scooter": ("routed-bike", "cycling"),
    "pedestrian": ("routed-foot", "walking"),
    "foot": ("routed-foot", "walking"),
}


def _point(value: Any) -> dict[str, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        lat, lng = value[0], value[1]
    elif isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lng = value.get("lng", value.get("lon", value.get("longitude")))
    else:
        return None
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return {"lat": lat, "lng": lng}


def _maps_url(origin: dict[str, float], destination: dict[str, float], mode: str) -> str:
    travel_mode = {"foot": "walking", "bike": "bicycling", "car": "driving"}.get(mode, "driving")
    query = urlencode({
        "api": "1",
        "origin": f"{origin['lat']:.6f},{origin['lng']:.6f}",
        "destination": f"{destination['lat']:.6f},{destination['lng']:.6f}",
        "travelmode": travel_mode,
    })
    return f"https://www.google.com/maps/dir/?{query}"


def _step_summary(legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for leg in legs:
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver") or {}
            name = str(step.get("name") or "Unnamed road").strip()
            kind = str(maneuver.get("type") or "continue").replace("_", " ")
            modifier = str(maneuver.get("modifier") or "").replace("_", " ")
            distance_m = step.get("distance")
            try:
                distance_m = max(0, int(float(distance_m)))
            except (TypeError, ValueError):
                distance_m = None
            summaries.append({
                "instruction": f"{kind}{(' ' + modifier) if modifier else ''} · {name}",
                "road_name": name,
                "distance_m": distance_m,
            })
    # Keep the route card useful on narrow screens and avoid thousands of tiny steps.
    if len(summaries) <= 5:
        return summaries
    picks = [0, len(summaries) // 4, len(summaries) // 2, (3 * len(summaries)) // 4, len(summaries) - 1]
    return [summaries[index] for index in dict.fromkeys(picks)]


def _request_osrm(url: str, referer: str | None) -> dict[str, Any]:
    global _LAST_PUBLIC_REQUEST
    with _CACHE_LOCK:
        delay = _MIN_REQUEST_GAP_SECONDS - (time.monotonic() - _LAST_PUBLIC_REQUEST)
        if delay > 0:
            time.sleep(delay)
        _LAST_PUBLIC_REQUEST = time.monotonic()

    headers = {
        "User-Agent": "SIH-2026-Urban-Flood-Nowcast/1.0 (student route comparison; OSM attribution enabled)",
        "Accept": "application/json",
    }
    if referer and referer.startswith("https://"):
        headers["Referer"] = referer
    request = Request(url, headers=headers)
    # Honor configured non-local proxies, but bypass a dead loopback proxy.
    # This is the same failure mode that can otherwise hide route geometry
    # while the OSRM endpoint itself is reachable over direct HTTPS.
    loopback_proxy = False
    for proxy_value in getproxies().values():
        try:
            proxy_url = proxy_value if "://" in proxy_value else f"http://{proxy_value}"
            if urlparse(proxy_url).hostname in {"127.0.0.1", "localhost", "::1"}:
                loopback_proxy = True
                break
        except (TypeError, ValueError):
            continue
    opener = build_opener(ProxyHandler({})) if loopback_proxy else build_opener()
    with opener.open(request, timeout=4.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        raise ValueError("Routing provider did not return an Ok route response.")
    return payload


def _road_speed_kph(profile: str, highway: str) -> float:
    if profile == "foot":
        return 4.5 if highway not in {"steps", "path", "corridor"} else 3.0
    if profile == "bike":
        return 18.0 if highway == "cycleway" else 13.0 if highway in {"path", "footway"} else 15.0
    return {
        "motorway": 55.0, "trunk": 45.0, "primary": 35.0, "secondary": 30.0,
        "tertiary": 24.0, "unclassified": 20.0, "residential": 18.0,
        "living_street": 10.0, "service": 10.0,
    }.get(highway, 16.0)


def _load_local_road_graph(profile: str):
    """Load a small OSM road extract for route-line fallback when OSRM is down."""
    with _LOCAL_GRAPH_LOCK:
        cached = _LOCAL_GRAPHS.get(profile)
        if cached is not None:
            return cached
        if not _LOCAL_ROADS_PATH.is_file():
            return None, None

        allowed = {
            "car": {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
                    "residential", "living_street", "service", "road", "*_link"},
            "bike": {"primary", "secondary", "tertiary", "unclassified", "residential",
                     "living_street", "service", "cycleway", "path", "footway"},
            "foot": {"primary", "secondary", "tertiary", "unclassified", "residential",
                     "living_street", "service", "cycleway", "path", "footway", "steps"},
        }[profile]
        graph: dict[tuple[float, float], list[tuple]] = {}
        node_coords: dict[tuple[float, float], tuple[float, float]] = {}

        try:
            with _LOCAL_ROADS_PATH.open("r", encoding="utf-8") as roads_file:
                features = json.load(roads_file).get("features", [])
        except (OSError, ValueError, TypeError):
            return None, None

        for feature in features:
            geometry = feature.get("geometry") or {}
            properties = feature.get("properties") or {}
            if geometry.get("type") != "LineString":
                continue
            highway = str(properties.get("highway") or "").lower()
            if highway not in allowed and not (profile == "car" and highway.endswith("_link")):
                continue

            access = str(properties.get("access") or "").lower()
            mode_access = str(properties.get({"car": "motor_vehicle", "bike": "bicycle", "foot": "foot"}[profile]) or "").lower()
            car_access = str(properties.get("motorcar") or "").lower() if profile == "car" else ""
            if access in {"no", "private"} or mode_access in {"no", "private"} or car_access in {"no", "private"}:
                continue

            coordinates = geometry.get("coordinates") or []
            if len(coordinates) < 2:
                continue
            oneway = str(properties.get("oneway") or "").lower()
            reverse_only = oneway == "-1"
            bicycle_override = profile == "bike" and str(properties.get("oneway:bicycle") or "").lower() == "no"
            directed = profile != "foot" and not bicycle_override and (
                oneway in {"yes", "1", "true"} or reverse_only or properties.get("junction") == "roundabout"
            )

            def key_and_coords(pair):
                try:
                    lng, lat = float(pair[0]), float(pair[1])
                    if not (math.isfinite(lat) and math.isfinite(lng)):
                        return None, None
                    key = (round(lng, 6), round(lat, 6))
                    return key, (lng, lat)
                except (TypeError, ValueError, IndexError):
                    return None, None

            for first, second in zip(coordinates, coordinates[1:]):
                key_a, coord_a = key_and_coords(first)
                key_b, coord_b = key_and_coords(second)
                if key_a is None or key_b is None or key_a == key_b:
                    continue
                lat_mid = math.radians((coord_a[1] + coord_b[1]) / 2)
                distance_m = math.hypot(
                    (coord_b[0] - coord_a[0]) * 111320.0 * math.cos(lat_mid),
                    (coord_b[1] - coord_a[1]) * 111320.0,
                )
                if distance_m <= 0 or distance_m > 2000:
                    continue
                speed = _road_speed_kph(profile, highway)
                cost_s = distance_m / (speed * 1000.0 / 3600.0)
                node_coords[key_a] = coord_a
                node_coords[key_b] = coord_b
                if reverse_only:
                    graph.setdefault(key_b, []).append((key_a, distance_m, cost_s))
                else:
                    graph.setdefault(key_a, []).append((key_b, distance_m, cost_s))
                    if not directed:
                        graph.setdefault(key_b, []).append((key_a, distance_m, cost_s))

        _LOCAL_GRAPHS[profile] = (graph, node_coords)
        return graph, node_coords


def _nearest_road_node(point: dict[str, float], node_coords: dict[tuple[float, float], tuple[float, float]]):
    lat0, lng0 = point["lat"], point["lng"]
    cos_lat = math.cos(math.radians(lat0))
    best_node = None
    best_distance = float("inf")
    for node, (lng, lat) in node_coords.items():
        distance = math.hypot((lng - lng0) * 111320.0 * cos_lat, (lat - lat0) * 111320.0)
        if distance < best_distance:
            best_node, best_distance = node, distance
    return best_node, best_distance


def _local_osm_route(origin: dict[str, float], destination: dict[str, float], vehicle_type: str, flood_context: Any):
    profile = "foot" if vehicle_type in {"pedestrian", "foot"} else "bike" if vehicle_type in {"bike", "scooter"} else "car"
    graph, node_coords = _load_local_road_graph(profile)
    if not graph or not node_coords:
        return None

    start, start_snap_m = _nearest_road_node(origin, node_coords)
    finish, finish_snap_m = _nearest_road_node(destination, node_coords)
    if start is None or finish is None or start_snap_m > 750 or finish_snap_m > 750:
        return None

    costs = {start: 0.0}
    previous: dict[tuple[float, float], tuple[tuple[float, float], float]] = {}
    queue = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != costs.get(node):
            continue
        if node == finish:
            break
        for neighbour, distance_m, seconds in graph.get(node, []):
            candidate = cost + seconds
            if candidate < costs.get(neighbour, float("inf")):
                costs[neighbour] = candidate
                previous[neighbour] = (node, distance_m)
                heapq.heappush(queue, (candidate, neighbour))
    if finish not in costs:
        return None

    path = [finish]
    graph_distance_m = 0.0
    cursor = finish
    while cursor != start:
        parent, segment_m = previous[cursor]
        graph_distance_m += segment_m
        cursor = parent
        path.append(cursor)
    path.reverse()

    coordinates = [[origin["lat"], origin["lng"]]]
    for node in path:
        lng, lat = node_coords[node]
        candidate = [lat, lng]
        if math.hypot((candidate[1] - coordinates[-1][1]) * 111320.0, (candidate[0] - coordinates[-1][0]) * 111320.0) > 2:
            coordinates.append(candidate)
    if math.hypot((destination["lng"] - coordinates[-1][1]) * 111320.0, (destination["lat"] - coordinates[-1][0]) * 111320.0) > 2:
        coordinates.append([destination["lat"], destination["lng"]])

    speed = _road_speed_kph(profile, "residential")
    snap_distance = start_snap_m + finish_snap_m
    total_distance = graph_distance_m + snap_distance
    eta_seconds = costs[finish] + snap_distance / (speed * 1000.0 / 3600.0)
    raw_coords = [[lng, lat] for lat, lng in coordinates]
    return {
        "route_id": "local-osm-route",
        "name": "Local OSM road path",
        "status": "LOCAL_OSM_ROAD_GEOMETRY",
        "eta_minutes": max(1, round(eta_seconds / 60.0)),
        "distance_km": round(total_distance / 1000.0, 2),
        "vehicle_type": vehicle_type,
        "coordinates": coordinates,
        "steps": [],
        "google_maps_url": _maps_url(origin, destination, vehicle_type),
        "origin_snap_distance_m": round(start_snap_m),
        "destination_snap_distance_m": round(finish_snap_m),
        **_route_depth_context(raw_coords, flood_context),
    }


def _fetch_routes(origin: dict[str, float], destination: dict[str, float], vehicle_type: str, referer: str | None):
    global _ROUTE_CACHE
    profile_prefix, profile_name = _PROFILE.get(vehicle_type, _PROFILE["car"])
    cache_key = (
        round(origin["lat"], 5), round(origin["lng"], 5),
        round(destination["lat"], 5), round(destination["lng"], 5), profile_prefix,
    )
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _ROUTE_CACHE.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return json.loads(json.dumps(cached[1])), "FOSSGIS_OSRM_OPENSTREETMAP", True
        _ROUTE_CACHE = {key: value for key, value in _ROUTE_CACHE.items() if now - value[0] < _CACHE_TTL_SECONDS}

    coordinates = f"{origin['lng']:.6f},{origin['lat']:.6f};{destination['lng']:.6f},{destination['lat']:.6f}"
    query = urlencode({
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "3",
        "steps": "true",
        "continue_straight": "false",
    })

    base_url = os.environ.get("OSRM_ROUTING_BASE_URL", "https://routing.openstreetmap.de").rstrip("/")
    providers = [(f"{base_url}/{profile_prefix}/route/v1/driving/{coordinates}?{query}", "FOSSGIS_OSRM_OPENSTREETMAP")]
    # If a custom single-profile OSRM endpoint is configured, do not send a
    # second request to public infrastructure. The public fallback is for the
    # default FOSSGIS demo only and remains subject to best-effort availability.
    if "OSRM_ROUTING_BASE_URL" not in os.environ:
        providers.append((f"https://router.project-osrm.org/route/v1/{profile_name}/{coordinates}?{query}", "OSRM_PROJECT_DEMO_OPENSTREETMAP"))

    for url, provider_name in providers:
        try:
            result = _request_osrm(url, referer)
            with _CACHE_LOCK:
                _ROUTE_CACHE[cache_key] = (time.monotonic(), result)
            return result, provider_name, False
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            continue

    return {"routes": []}, "OSM_ROUTE_PROVIDER_NO_GEOMETRY", False


def _distance_to_route_m(node: dict[str, Any], coordinates: list[list[float]]) -> float | None:
    try:
        node_lat = float(node.get("lat", node.get("latitude")))
        node_lng = float(node.get("lng", node.get("lon", node.get("longitude"))))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(node_lat) and math.isfinite(node_lng)):
        return None
    cos_lat = math.cos(math.radians(node_lat))
    minimum = None
    # OSM route vertices are densely sampled; this is a screening distance,
    # not a road/flow intersection calculation.
    stride = max(1, len(coordinates) // 3000)
    for lng, lat in coordinates[::stride]:
        dx = (float(lng) - node_lng) * 111320.0 * cos_lat
        dy = (float(lat) - node_lat) * 111320.0
        distance = math.hypot(dx, dy)
        if minimum is None or distance < minimum:
            minimum = distance
            if minimum <= 15:
                return minimum
    return minimum


def _route_depth_context(coordinates: list[list[float]], flood_context: Any) -> dict[str, Any]:
    context = flood_context if isinstance(flood_context, dict) else {}
    quality = str(context.get("data_quality") or "UNAVAILABLE")
    permitted = {
        "UNVALIDATED_FORMULA_ESTIMATE",
        "UNVALIDATED_MODEL_ESTIMATE",
        "SYNTHETIC_FORMULA_DEMO",
        "SYNTHETIC_DEMO_RF_ESTIMATE",
        "SYNTHETIC_DEMO_FORMULA_ESTIMATE",
    }
    nodes = context.get("nodes") if quality in permitted else []
    nodes = nodes[:50] if isinstance(nodes, list) else []
    matches = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        raw_depth = node.get("water_depth_cm", node.get("depth_cm"))
        try:
            depth = float(raw_depth)
            if not math.isfinite(depth) or depth < 0 or depth > 500:
                continue
        except (TypeError, ValueError):
            continue
        distance = _distance_to_route_m(node, coordinates)
        if distance is not None and distance <= 125:
            matches.append({
                "node_name": str(node.get("name") or node.get("id") or "Pilot model point")[:100],
                "depth_cm": round(depth, 1),
                "distance_to_route_m": round(distance),
            })
    if not matches:
        return {
            "max_water_depth_cm": None,
            "flood_context_status": "NO_NEARBY_VALIDATED_STREET_OBSERVATION",
            "nearby_depth_estimates": [],
            "note": "No validated street-depth observation is available for this route.",
        }
    matches.sort(key=lambda item: item["depth_cm"], reverse=True)
    return {
        "max_water_depth_cm": matches[0]["depth_cm"],
        "flood_context_status": quality,
        "nearby_depth_estimates": matches[:4],
        "note": "These are unvalidated point estimates near schematic pilot nodes, not water-depth readings on this road.",
    }


def build_route_response(
    body: Any,
    *,
    referer: str | None = None,
    flood_context: Any = None,
    lead_time_mins: int | None = None,
) -> dict[str, Any]:
    """Return road alternatives even when pilot flood data is absent."""
    body = body if isinstance(body, dict) else {}
    origin = _point(body.get("origin"))
    destination = _point(body.get("destination"))
    if origin is None or destination is None:
        return {
            "routing_status": "INVALID_ROUTE_ENDPOINTS",
            "flood_safety_status": "UNVERIFIED",
            "routes": [],
            "notice": "Enter a starting point and destination that can be placed on the map.",
        }

    vehicle_type = str(body.get("vehicle_type") or "car").strip().lower()[:24]
    lead = lead_time_mins
    if lead is None:
        try:
            lead = max(0, min(180, int(body.get("lead_time_mins", 60))))
        except (TypeError, ValueError):
            lead = 60

    provider_data, provider_name, cache_used = _fetch_routes(origin, destination, vehicle_type, referer)
    raw_routes = provider_data.get("routes", []) if isinstance(provider_data, dict) else []
    maps_fallback = _maps_url(origin, destination, vehicle_type)
    routes = []

    for index, route in enumerate(raw_routes[:3]):
        geometry = route.get("geometry") or {}
        raw_coordinates = geometry.get("coordinates", [])
        if not isinstance(raw_coordinates, list) or len(raw_coordinates) < 2:
            continue
        coords = []
        for pair in raw_coordinates:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                try:
                    lng, lat = float(pair[0]), float(pair[1])
                    if math.isfinite(lat) and math.isfinite(lng):
                        coords.append([lat, lng])
                except (TypeError, ValueError):
                    continue
        if len(coords) < 2:
            continue

        distance_m = float(route.get("distance") or 0)
        duration_s = float(route.get("duration") or 0)
        depth_context = _route_depth_context(raw_coordinates, flood_context)
        legs = route.get("legs", []) if isinstance(route.get("legs"), list) else []
        steps = _step_summary(legs)
        waypoints = []
        if len(coords) > 12:
            for point_index in (len(coords) // 3, (2 * len(coords)) // 3):
                lat, lng = coords[point_index]
                waypoints.append(f"{lat:.5f},{lng:.5f}")
        route_maps_url = _maps_url(origin, destination, vehicle_type)
        if waypoints:
            query = urlencode({
                "api": "1",
                "origin": f"{origin['lat']:.6f},{origin['lng']:.6f}",
                "destination": f"{destination['lat']:.6f},{destination['lng']:.6f}",
                "travelmode": {"pedestrian": "walking", "bike": "bicycling"}.get(vehicle_type, "driving"),
                "waypoints": "|".join(waypoints),
            })
            route_maps_url = f"https://www.google.com/maps/dir/?{query}"

        routes.append({
            "route_id": f"r{index + 1}",
            "name": "Fastest road option" if index == 0 else f"Alternative route {index + 1}",
            "status": "ROAD_ROUTE_FROM_OPENSTREETMAP",
            "eta_minutes": max(1, round(duration_s / 60)) if duration_s > 0 else None,
            "distance_km": round(distance_m / 1000, 2) if distance_m > 0 else None,
            "vehicle_type": vehicle_type,
            "coordinates": coords,
            "steps": steps,
            "google_maps_url": route_maps_url,
            **depth_context,
        })

    if not routes:
        local_route = _local_osm_route(origin, destination, vehicle_type, flood_context)
        if local_route:
            routes = [local_route]
            provider_name = "LOCAL_OSM_ROAD_EXTRACT"

    all_routes_have_context = bool(routes) and all(route.get("max_water_depth_cm") is not None for route in routes)
    if len(routes) > 1 and all_routes_have_context:
        routes.sort(key=lambda route: (route["max_water_depth_cm"], route["eta_minutes"] or 10**6))
        for index, route in enumerate(routes):
            route["route_id"] = f"r{index + 1}"
            route["name"] = "Lowest nearby model estimate" if index == 0 else f"Alternative route {index + 1}"
        recommended_id = routes[0]["route_id"]
        recommendation_basis = "LOWEST_NEARBY_UNVALIDATED_NODE_ESTIMATE_THEN_ETA"
        notice = "Road options are ranked using nearby pilot-model context and route time. The estimate does not measure water on the road."
    elif routes and provider_name == "LOCAL_OSM_ROAD_EXTRACT":
        recommended_id = routes[0]["route_id"]
        recommendation_basis = "LOCAL_OSM_ROAD_GRAPH_PATH"
        notice = "Showing a path traced through the bundled OpenStreetMap roads. ETA is approximate; live traffic, closures, and turn restrictions are not included."
    elif routes:
        routes.sort(key=lambda route: route.get("eta_minutes") or 10**6)
        for index, route in enumerate(routes):
            route["name"] = "Fastest road option" if index == 0 else f"Alternative route {index + 1}"
        recommended_id = routes[0]["route_id"]
        recommendation_basis = "FASTEST_OPENSTREETMAP_ROAD_OPTION"
        notice = "Road options use OpenStreetMap geometry; live traffic and road closures are not included."
    else:
        routes = [{
            "route_id": "live-directions",
            "name": "Open live road directions",
            "status": "LIVE_DIRECTIONS_LINK",
            "eta_minutes": None,
            "distance_km": None,
            "vehicle_type": vehicle_type,
            "coordinates": [],
            "steps": [],
            "google_maps_url": maps_fallback,
            "max_water_depth_cm": None,
            "flood_context_status": "UNVERIFIED",
            "nearby_depth_estimates": [],
            "note": "This link opens current road directions. Floodwater and road closures are not checked by the routing link.",
        }]
        recommended_id = "live-directions"
        recommendation_basis = "EXTERNAL_LIVE_DIRECTIONS_LINK"
        notice = "Road geometry is temporarily unavailable. The map marks the trip endpoints; open live directions for the road route."

    return {
        "routing_engine": provider_name,
        "routing_status": "LOCAL_OSM_ROUTE_FALLBACK" if provider_name == "LOCAL_OSM_ROAD_EXTRACT" else "ROUTES_AVAILABLE" if provider_data.get("routes") else "LIVE_DIRECTIONS_LINK_READY",
        "route_cache_used": cache_used,
        "flood_safety_status": "UNVERIFIED",
        "flood_context_source": str((flood_context or {}).get("data_quality") or "UNAVAILABLE") if isinstance(flood_context, dict) else "UNAVAILABLE",
        "recommendation_basis": recommendation_basis,
        "recommendation_is_safety_clearance": False,
        "lead_time_minutes": lead,
        "origin": origin,
        "destination": destination,
        "vehicle_type": vehicle_type,
        "recommended_route_id": recommended_id,
        "notice": notice,
        "route_data_attribution": (
            "© OpenStreetMap contributors · route geometry from the bundled local road extract."
            if provider_name == "LOCAL_OSM_ROAD_EXTRACT" else
            "© OpenStreetMap contributors · Directions via OSRM/FOSSGIS. Route request coordinates are sent to the routing provider; route times do not include live traffic, flood closures, or agency restrictions."
        ),
        "route_attribution_url": "https://www.openstreetmap.org/copyright",
        "route_fix_map_url": "https://www.openstreetmap.org/fixthemap",
        "routes": routes,
    }
