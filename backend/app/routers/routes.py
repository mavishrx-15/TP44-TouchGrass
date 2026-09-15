"""Walking routes backed by Google Routes and scored against local tree zones."""

from math import asin, ceil, cos, radians, sin, sqrt
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import settings
from app.db import SessionDep
from app.route_scoring import Preferences, allergy_score, park_score, weighted_score

router = APIRouter()
EARTH_RADIUS_M = 6_371_000
TREE_CORRIDOR_M = 100


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    preferences: Preferences = Field(default_factory=Preferences)
    travelMode: Literal["WALK", "TRANSIT"] = "WALK"


class RouteResult(BaseModel):
    id: Literal["recommended"] = "recommended"
    label: str
    bestMatch: bool
    message: str
    explanation: list[str]
    matchScore: float
    scores: dict[str, float]
    travelMode: Literal["WALK", "TRANSIT"]
    withinTimeBudget: bool
    durationMinutes: int
    distanceKm: float
    treeCount: int
    encodedPolyline: str


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
        "locationBias": {
            "circle": {
                "center": {"latitude": -37.8136, "longitude": 144.9631},
                "radius": 50_000,
            }
        },
    }
    data = _google_request(
        "POST",
        "https://places.googleapis.com/v1/places:autocomplete",
        field_mask="suggestions.placePrediction.placeId,suggestions.placePrediction.text.text",
        json=payload,
    )
    return [
        PlaceSuggestion(
            id=item["placePrediction"]["placeId"], label=item["placePrediction"]["text"]["text"]
        )
        for item in data.get("suggestions", [])
        if "placePrediction" in item
    ]


@router.get("/places/{place_id}", response_model=PlaceDetails)
def place_details(place_id: str) -> PlaceDetails:
    """Resolve a selected Google place to routeable coordinates."""
    data = _google_request(
        "GET",
        f"https://places.googleapis.com/v1/places/{place_id}",
        field_mask="id,displayName,location",
    )
    location = data["location"]
    return PlaceDetails(
        id=data["id"],
        label=data["displayName"]["text"],
        coordinates=Coordinates(lat=location["latitude"], lng=location["longitude"]),
    )


@router.post("/routes", response_model=list[RouteResult])
def walking_routes(request: RouteRequest, session: SessionDep) -> list[RouteResult]:
    """Select one preference-weighted route from available Google alternatives."""
    if request.origin == request.destination:
        raise HTTPException(status_code=422, detail="Origin and destination must be different.")
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=503, detail="Google Routes API key is not configured.")

    payload = {
        "origin": {"location": {"latLng": _lat_lng(request.origin)}},
        "destination": {"location": {"latLng": _lat_lng(request.destination)}},
        "travelMode": request.travelMode,
        "computeAlternativeRoutes": True,
        "languageCode": "en-AU",
        "units": "METRIC",
    }
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
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
        raise HTTPException(status_code=404, detail="No route was found for this transport mode.")

    scored = []
    for item in candidates:
        path = _decode_polyline(item["polyline"]["encodedPolyline"])
        rows = _corridor_trees(path, session)
        scored.append(
            (
                item,
                _tree_score(path, session),
                park_score(rows),
                allergy_score(rows, request.preferences),
                len(rows),
            )
        )
    max_trees = max((item[1] for item in scored), default=0) or 1
    ranked = []
    for item, trees, parks, allergy, samples in scored:
        scores = {"canopy": trees / max_trees, "shade": parks, "noise": parks, "allergy": allergy}
        match = weighted_score(scores, request.preferences)
        within = (
            request.travelMode == "TRANSIT"
            or _duration_seconds(item["duration"]) <= request.preferences.walkingMinutes * 60
        )
        ranked.append(
            (within, match, -_duration_seconds(item["duration"]), item, trees, scores, samples)
        )
    selected = max(ranked, key=lambda item: item[:3])
    return [_result(selected, request)]


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


def _result(selected: tuple, request: RouteRequest) -> RouteResult:
    within, match, _, route, tree_count, scores, samples = selected
    weighted = any(getattr(request.preferences, name) for name in scores)
    best = within and (not weighted or match >= 0.7)
    message = (
        "Best available match for your preferences."
        if best
        else "Closest available match; some preferences could not be met."
    )
    if not within:
        message = (
            "No available route fits your walking time. "
            "This is the closest preference match outside your time budget."
        )
    explanation = []
    if request.preferences.canopy:
        explanation.append(
            f"Passes zones containing approximately {tree_count} trees; "
            "canopy uses tree count as a proxy."
        )
    if samples and (request.preferences.shade or request.preferences.noise):
        explanation.append(
            f"{scores['shade']:.0%} of sampled corridor trees are in parks; "
            "used as a shade and quieter-surroundings proxy, not live measurements."
        )
    if samples and request.preferences.allergy:
        explanation.append(
            f"{scores['allergy']:.0%} of sampled trees are outside your selected "
            "avoidance genera/families. This does not measure pollen."
        )
    if not samples:
        explanation.append(
            "No individual tree data was found in this corridor; "
            "shade, noise and allergy matches are unknown."
        )
    if request.travelMode == "WALK":
        explanation.append(
            f"Walking time {'fits' if within else 'exceeds'} your "
            f"{request.preferences.walkingMinutes}-minute budget."
        )
    else:
        explanation.append(
            "Public transport selected; duration covers the whole journey. "
            "The walking-only time budget is not applied."
        )
    if not weighted:
        explanation.append(
            "No environmental priorities selected; the shortest duration breaks the tie."
        )
    return RouteResult(
        label="Your personalised route",
        durationMinutes=max(1, ceil(_duration_seconds(route["duration"]) / 60)),
        distanceKm=round(route["distanceMeters"] / 1000, 2),
        treeCount=tree_count,
        encodedPolyline=route["polyline"]["encodedPolyline"],
        bestMatch=best,
        message=message,
        explanation=explanation,
        matchScore=round(match, 4),
        scores=scores,
        travelMode=request.travelMode,
        withinTimeBudget=within,
    )


def _corridor_trees(path: list[tuple[float, float]], session: SessionDep):
    if not path:
        return []
    rows = session.execute(
        text(
            """
        SELECT latitude, longitude, located_in, display_category, family FROM trees
        WHERE latitude BETWEEN :south AND :north AND longitude BETWEEN :west AND :east
    """
        ),
        {
            "south": min(p[0] for p in path) - 0.002,
            "north": max(p[0] for p in path) + 0.002,
            "west": min(p[1] for p in path) - 0.002,
            "east": max(p[1] for p in path) + 0.002,
        },
    ).all()
    return [r for r in rows if _path_distance_m(r.latitude, r.longitude, path) <= TREE_CORRIDOR_M]


def _path_distance_m(lat: float, lng: float, path: list[tuple[float, float]]) -> float:
    # Project nearby segments into metres so long polyline segments do not omit trees.
    scale_x = EARTH_RADIUS_M * cos(radians(lat))
    points = [(radians(y - lng) * scale_x, radians(x - lat) * EARTH_RADIUS_M) for x, y in path]
    closest = min(sqrt(x * x + y * y) for x, y in points)
    for (ax, ay), (bx, by) in zip(points, points[1:], strict=False):
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = max(0, min(1, -(ax * dx + ay * dy) / length)) if length else 0
        closest = min(closest, sqrt((ax + t * dx) ** 2 + (ay + t * dy) ** 2))
    return closest


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
