"""Walking routes backed by Google Routes and scored against local tree zones."""

from math import asin, cos, radians, sin, sqrt
from threading import Lock
from time import monotonic

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import settings
from app.cbd import polygon, require_inside
from app.db import SessionDep
from app.security import optional_access_token

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
    payload = {
        "input": query,
        "includedRegionCodes": ["au"],
        "languageCode": "en-AU",
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": min(p[1] for p in polygon()), "longitude": min(p[0] for p in polygon())},
                "high": {"latitude": max(p[1] for p in polygon()), "longitude": max(p[0] for p in polygon())},
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
        place_id = prediction["placeId"]
        detail = _google_request("GET", f"https://places.googleapis.com/v1/places/{place_id}", "location")
        location = detail.get("location", {})
        if location and _inside(location["latitude"], location["longitude"]):
            result.append(PlaceSuggestion(id=place_id, label=prediction["text"]["text"]))
    return result


@router.get("/places/{place_id}", response_model=PlaceDetails)
def place_details(place_id: str) -> PlaceDetails:
    """Resolve a selected Google place to routeable coordinates."""
    data = _google_request(
        "GET",
        f"https://places.googleapis.com/v1/places/{place_id}",
        field_mask="id,displayName,location",
    )
    location = data["location"]
    require_inside(location["latitude"], location["longitude"])
    return PlaceDetails(
        id=data["id"],
        label=data["displayName"]["text"],
        coordinates=Coordinates(lat=location["latitude"], lng=location["longitude"]),
    )


@router.post("/routes", response_model=list[RouteResult])
def walking_routes(request: RouteRequest, session: SessionDep,
                   access_token: str | None = Depends(optional_access_token)) -> list[RouteResult]:
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
        raise HTTPException(status_code=503, detail="Google Routes API key is not configured.")

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
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.steps.navigationInstruction.instructions,routes.legs.steps.startLocation,routes.legs.steps.distanceMeters",
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
        detail = (
            error.response.json()
            .get("error", {})
            .get("message", "Google Routes rejected the request.")
        )
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail="Google Routes could not be reached."
        ) from error

    candidates = response.json().get("routes", [])
    if not candidates:
        raise HTTPException(status_code=404, detail="No walking route was found.")

    scored = [
        (_tree_score(_decode_polyline(item["polyline"]["encodedPolyline"]), session), item)
        for item in candidates
    ]
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
        raise HTTPException(status_code=503, detail="Google Maps API key is not configured.")
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
        return response.json()
    except httpx.HTTPStatusError as error:
        detail = (
            error.response.json()
            .get("error", {})
            .get("message", "Google Maps rejected the request.")
        )
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Google Maps could not be reached.") from error


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
    try:
        from app.cbd import contains

        return contains(lat, lng)
    except HTTPException:
        return False


def _duration_seconds(value: str) -> int:
    return round(float(value.removesuffix("s")))


def _tree_score(path: list[tuple[float, float]], session: SessionDep) -> int:
    """Count trees in zone centres within 100m of decoded route vertices."""
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
        if min(_distance_m(row.center_lat, row.center_lon, lat, lng) for lat, lng in path)
        <= TREE_CORRIDOR_M
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
        byte = ord(value[index]) - 63
        index += 1
        result |= (byte & 0x1F) << shift
        shift += 5
        if byte < 0x20:
            break
    return (~(result >> 1) if result & 1 else result >> 1), index
