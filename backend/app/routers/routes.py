"""Walking routes backed by Google Routes and scored against local tree zones."""

from math import asin, cos, radians, sin, sqrt
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.db import SessionDep

router = APIRouter()
EARTH_RADIUS_M = 6_371_000
TREE_CORRIDOR_M = 100

TravelMode = Literal["WALK", "TRANSIT"]


class Coordinates(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    travelMode: TravelMode = "WALK"


class RouteResult(BaseModel):
    """One route. There is never a second one to compare it against (US3.2).

    treeCount is null in TRANSIT mode: the corridor score describes what you
    walk past, and it would be a false claim about a tram ride. AC forbids the
    explanation making a tree, noise or allergy claim in that mode, so the
    number it would be built from is absent rather than zero.
    """

    travelMode: TravelMode
    durationMinutes: int
    distanceKm: float
    treeCount: int | None
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


@router.post("/routes", response_model=RouteResult)
def plan_route(request: RouteRequest, session: SessionDep) -> RouteResult:
    """Score Google's alternatives and return the single best one (US3.2).

    This used to return two routes labelled "Fastest" and "Tree-Dense" and let
    the user pick. The comparison was the feature, and it is the thing that got
    cut: offering a greener option next to a faster one asks the user to do the
    weighing the app exists to do for them. One route, already chosen.

    Google still gets computeAlternativeRoutes: we need several candidates to
    choose between. What changed is that the choosing happens here instead of
    on screen.
    """
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
        raise HTTPException(status_code=404, detail="No route was found.")

    if request.travelMode == "TRANSIT":
        # Nothing to score: the corridor count describes a walk. Shortest wins.
        fastest = min(candidates, key=lambda item: _duration_seconds(item["duration"]))
        return _result(request.travelMode, (None, fastest))

    scored = [
        (_tree_score(_decode_polyline(item["polyline"]["encodedPolyline"]), session), item)
        for item in candidates
    ]
    return _result(request.travelMode, _best(scored))


def _best(scored: list[tuple[int, dict]]) -> tuple[int, dict]:
    """The highest-scoring candidate, shortest first among equals.

    Duration is the tie-break rather than a competing goal: two alternatives
    often pass the same trees, and there is no reason to hand back the longer
    one. When Google returns a single alternative it wins by default — AC6
    asks that this reads as a choice, not an implied comparison, which is why
    nothing in the response says how many candidates there were.
    """
    return max(
        scored,
        key=lambda candidate: (candidate[0], -_duration_seconds(candidate[1]["duration"])),
    )


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


def _result(travel_mode: TravelMode, scored: tuple[int | None, dict]) -> RouteResult:
    tree_count, route = scored
    return RouteResult(
        travelMode=travel_mode,
        durationMinutes=round(_duration_seconds(route["duration"]) / 60),
        distanceKm=round(route["distanceMeters"] / 1000, 1),
        treeCount=tree_count,
        encodedPolyline=route["polyline"]["encodedPolyline"],
    )


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
