"""Walking routes backed by Google Routes and scored against local tree zones."""

from itertools import pairwise
from math import asin, cos, isfinite, radians, sin, sqrt
from threading import Lock
from time import monotonic
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.cbd import bounds, contains, require_inside
from app.config import settings
from app.db import SessionDep
from app.route_metrics import point_segment_distance_m
from app.security import require_access_token

router = APIRouter()
EARTH_RADIUS_M = 6_371_000
TREE_CORRIDOR_M = 100
_reroute_lock = Lock()
_last_route_by_token: dict[str, float] = {}


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates


class RouteResult(BaseModel):
    id: str
    label: str
    durationMinutes: int
    distanceKm: float
    treeCount: int
    encodedPolyline: str
    steps: list[dict] = Field(default_factory=list)


class PlaceSuggestion(BaseModel):
    id: str
    label: str


class PlaceDetails(BaseModel):
    id: str
    label: str
    coordinates: Coordinates


@router.get("/places/autocomplete", response_model=list[PlaceSuggestion])
def autocomplete_places(query: str = Query(min_length=2, max_length=120)) -> list[PlaceSuggestion]:
    """Google Places suggestions biased to inner Melbourne."""
    boundary = bounds()
    payload = {
        "input": query,
        "includedRegionCodes": ["au"],
        "languageCode": "en-AU",
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": boundary["south"], "longitude": boundary["west"]},
                "high": {"latitude": boundary["north"], "longitude": boundary["east"]},
            }
        },
    }
    data = _google_request(
        "POST",
        "https://places.googleapis.com/v1/places:autocomplete",
        field_mask="suggestions.placePrediction.placeId,suggestions.placePrediction.text.text",
        json=payload,
    )
    result = []
    for item in data.get("suggestions", []):
        prediction = item.get("placePrediction")
        if not prediction:
            continue
        place_id = prediction.get("placeId")
        label = prediction.get("text", {}).get("text")
        if not place_id or not label:
            continue
        detail = _google_request(
            "GET",
            f"https://places.googleapis.com/v1/places/{quote(place_id, safe='')}",
            "location",
        )
        location = detail.get("location", {})
        if (
            location.get("latitude") is not None
            and location.get("longitude") is not None
            and _inside(location["latitude"], location["longitude"])
        ):
            result.append(PlaceSuggestion(id=place_id, label=label))
    return result


@router.get("/places/{place_id}", response_model=PlaceDetails)
def place_details(place_id: str) -> PlaceDetails:
    """Resolve a selected Google place to routeable coordinates."""
    data = _google_request(
        "GET",
        f"https://places.googleapis.com/v1/places/{quote(place_id, safe='')}",
        field_mask="id,displayName,location",
    )
    location = data.get("location")
    if not location or "latitude" not in location or "longitude" not in location:
        raise HTTPException(status_code=502, detail={"code": "place_location_unavailable"})
    require_inside(location["latitude"], location["longitude"])
    display_name = data.get("displayName", {}).get("text")
    if not data.get("id") or not display_name:
        raise HTTPException(status_code=502, detail={"code": "place_details_incomplete"})
    return PlaceDetails(
        id=data["id"],
        label=display_name,
        coordinates=Coordinates(lat=location["latitude"], lng=location["longitude"]),
    )


@router.post("/routes", response_model=list[RouteResult])
def walking_routes(
    request: RouteRequest, session: SessionDep, access_token: str = Depends(require_access_token)
) -> list[RouteResult]:
    """Return Google's fastest walk and the alternative passing most zone trees."""
    require_inside(request.origin.lat, request.origin.lng)
    require_inside(request.destination.lat, request.destination.lng)
    if access_token:
        now = monotonic()
        with _reroute_lock:
            if now - _last_route_by_token.get(access_token, 0) < 20:
                raise HTTPException(status_code=429, detail={"code": "reroute_rate_limited"})
            _last_route_by_token[access_token] = now
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail={"code": "google_maps_unconfigured"})

    payload = {
        "origin": {"location": {"latLng": _lat_lng(request.origin)}},
        "destination": {"location": {"latLng": _lat_lng(request.destination)}},
        "travelMode": "WALK",
        "computeAlternativeRoutes": True,
        "languageCode": "en-AU",
        "units": "METRIC",
    }
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": (
            "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,"
            "routes.legs.steps.navigationInstruction.instructions,"
            "routes.legs.steps.startLocation,routes.legs.steps.distanceMeters"
        ),
    }
    try:
        response = httpx.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_request_failed"}
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_unavailable"}
        ) from error

    try:
        data = response.json()
        candidates = data.get("routes", []) if isinstance(data, dict) else None
        if not isinstance(candidates, list):
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_invalid_response"}
        ) from error
    if not candidates:
        raise HTTPException(status_code=404, detail={"code": "route_not_found"})

    try:
        scored = []
        for item in candidates:
            if not isinstance(item, dict):
                raise ValueError
            encoded = item["polyline"]["encodedPolyline"]
            path = _decode_polyline(encoded)
            duration = _duration_seconds(item["duration"])
            distance = float(item["distanceMeters"])
            if not path or not isfinite(distance) or distance < 0 or duration < 0:
                raise ValueError
            scored.append((_tree_score(path, session), item))
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_routes_invalid_response"}
        ) from error
    fastest = min(scored, key=lambda candidate: _duration_seconds(candidate[1]["duration"]))
    alternatives = [candidate for candidate in scored if candidate[1] is not fastest[1]]
    green = max(
        alternatives or [fastest],
        key=lambda candidate: (candidate[0], -_duration_seconds(candidate[1]["duration"])),
    )
    results = [_result("fastest", "Fastest Route", fastest)]
    if green[1] is not fastest[1]:
        results.append(_result("green", "Tree-Dense Route", green))
    return results


def _google_request(method: str, url: str, field_mask: str, json: dict | None = None) -> dict:
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail={"code": "google_maps_unconfigured"})
    try:
        response = httpx.request(
            method,
            url,
            json=json,
            headers={
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": field_mask,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError
        return data
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_places_request_failed"}
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_places_unavailable"}
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=502, detail={"code": "google_places_invalid_response"}
        ) from error


def _lat_lng(value: Coordinates) -> dict[str, float]:
    return {"latitude": value.lat, "longitude": value.lng}


def _result(route_id: str, label: str, scored: tuple[int, dict]) -> RouteResult:
    tree_count, route = scored
    return RouteResult(
        id=route_id,
        label=label,
        durationMinutes=round(_duration_seconds(route["duration"]) / 60),
        distanceKm=round(route["distanceMeters"] / 1000, 1),
        treeCount=tree_count,
        encodedPolyline=route["polyline"]["encodedPolyline"],
        steps=[
            {
                "instruction": step.get("navigationInstruction", {}).get("instructions", ""),
                "startLocation": step.get("startLocation", {}).get("latLng", {}),
                "distanceMeters": step.get("distanceMeters", 0),
            }
            for leg in route.get("legs", [])
            for step in leg.get("steps", [])
        ],
    )


def _inside(lat: float, lng: float) -> bool:
    return contains(lat, lng)


def _duration_seconds(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("s"):
        raise ValueError("Invalid duration")
    duration = float(value.removesuffix("s"))
    if not isfinite(duration) or duration < 0:
        raise ValueError("Invalid duration")
    return round(duration)


def _tree_score(path: list[tuple[float, float]], session: SessionDep) -> int:
    """Count tree totals in zones whose centres are within 100m of the route."""
    if not path:
        return 0
    latitudes = [point[0] for point in path]
    longitudes = [point[1] for point in path]
    padding = 0.002
    rows = session.execute(
        text(
            """
            SELECT cluster_id, center_lat, center_lon, tree_count
            FROM zones
            WHERE center_lat BETWEEN :south AND :north
              AND center_lon BETWEEN :west AND :east
            """
        ),
        {
            "south": min(latitudes) - padding,
            "north": max(latitudes) + padding,
            "west": min(longitudes) - padding,
            "east": max(longitudes) + padding,
        },
    ).all()
    return sum(
        row.tree_count
        for row in rows
        if any(
            point_segment_distance_m(row.center_lat, row.center_lon, start, end) <= TREE_CORRIDOR_M
            for start, end in pairwise(path)
        )
        or (
            len(path) == 1
            and _distance_m(row.center_lat, row.center_lon, *path[0]) <= TREE_CORRIDOR_M
        )
    )


def _distance_m(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    delta_lat = radians(lat_b - lat_a)
    delta_lng = radians(lng_b - lng_a)
    value = (
        sin(delta_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(delta_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(value))


def _decode_polyline(value: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    index = latitude = longitude = 0
    while index < len(value):
        latitude_delta, index = _decode_value(value, index)
        longitude_delta, index = _decode_value(value, index)
        latitude += latitude_delta
        longitude += longitude_delta
        points.append((latitude / 100_000, longitude / 100_000))
    return points


def _decode_value(value: str, index: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        if index >= len(value) or shift > 60:
            raise ValueError("Invalid encoded polyline")
        byte = ord(value[index]) - 63
        index += 1
        result |= (byte & 0x1F) << shift
        shift += 5
        if byte < 0x20:
            break
    return (~(result >> 1) if result & 1 else result >> 1), index
