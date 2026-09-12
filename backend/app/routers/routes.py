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

# A corridor as dense as twice the median puts a typical walk near 50 and tops
# out on the leafiest. Derived from the data: the median zone holds 20 trees in
# a 0.001-degree cell, and a kilometre of 100m corridor covers about 20 such
# cells, so roughly 400 trees per kilometre is ordinary.
#
# NEEDS TEAM SIGN-OFF, like the allergy taxonomy: it sets where "High canopy"
# starts, and no acceptance criterion fixes it.
CANOPY_FULL_MARK_PER_KM = 800

# Iteration-2 handoff, "Prototype rules requiring team confirmation".
WALKING_TIME_TOLERANCE_MINUTES = 2


class Coordinates(BaseModel):
    lat: float
    lng: float


class Preferences(BaseModel):
    """What the user asked for on the home page. Every field is optional.

    Unset preferences contribute nothing to the score rather than counting as
    zero — leaving canopy alone must not read as "wants no trees".
    """

    canopy: int | None = None  # 0-100 slider
    shade: int | None = None  # 0-100 slider
    noise: Literal["quiet", "lively"] | None = None
    allergy: Literal["avoid", "lower"] | None = None
    walkingTime: Literal[5, 10, 15, 20] | None = None


class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    travelMode: TravelMode = "WALK"
    preferences: Preferences | None = None
    # Optional so the Iteration 1 frontend keeps working while the new one
    # lands; the personalised flow always sends it.
    precinctId: str | None = None


class Corridor(BaseModel):
    """Raw counts for the trees within 100m of a route."""

    trees: int
    park: int

    def metrics(self, distance_km: float) -> "AreaMetrics":
        """Turn the counts into the normalised scores the frontend reads.

        Density is per kilometre, not absolute: a long walk passes more trees
        than a short one without being any leafier, and comparing candidates on
        the raw total would just prefer the longer route.
        """
        per_km = self.trees / distance_km if distance_km else 0
        return AreaMetrics(
            canopy=min(100, round(100 * per_km / CANOPY_FULL_MARK_PER_KM)),
            parkShare=round(100 * self.park / self.trees) if self.trees else 0,
        )


class AreaMetrics(BaseModel):
    """Normalised scores, not measurements.

    canopy is a score, not canopy coverage or a percentile — the dataset counts
    trees, it does not measure crown area. parkShare is the share of trees in
    the corridor that stand in a park rather than on a street: the only shade
    and noise signal the data actually carries. The allergy pair is null until
    the taxonomy is agreed, and null must read as unknown, never as matched.
    """

    canopy: int
    parkShare: int
    lowAllergyShare: int | None = None
    highPollenTrees: int | None = None


class PreferenceMatch(BaseModel):
    key: Literal["canopy", "shade", "noise", "allergy", "time"]
    label: str
    detail: str
    matched: bool
    value: int


class MatchSummary(BaseModel):
    score: int
    matches: list[PreferenceMatch]
    sentence: str


class RouteResult(BaseModel):
    """One route. There is never a second one to compare it against (US3.2).

    metrics and match are null in TRANSIT mode: AC forbids a tree, noise or
    allergy claim about a tram ride, and null is what carries that — treeCount
    stays a plain count of trees near the path, which is true either way but is
    not used to choose or explain a transit route.

    candidateCount is how many alternatives Google returned. The panel says
    "chosen as the best match among the N routes Google found", so the number
    has to come from here; when it is 1 the frontend words it as a choice
    rather than a comparison (AC6).
    """

    id: Literal["personalised"] = "personalised"
    label: str
    travelMode: TravelMode
    durationMinutes: int
    distanceKm: float
    treeCount: int
    encodedPolyline: str
    candidateCount: int
    metrics: AreaMetrics | None = None
    match: MatchSummary | None = None
    message: str | None = None


def _match(
    preferences: Preferences | None, metrics: AreaMetrics, minutes: int
) -> MatchSummary | None:
    """Score the route against what the user asked for.

    Only selected preferences appear. An unset one is not a silent zero and not
    a free pass — it is absent, and the overall score is the mean of what was
    actually asked for, so choosing one preference does not dilute it.

    matched is strict: it means the route reaches the level requested, not that
    it came close. "Partial shade" cannot be reported as a match for "cooler and
    shaded" — the AC rules out flattering a near miss, in either direction.
    """
    if preferences is None:
        return None

    found: list[PreferenceMatch] = []

    if preferences.canopy is not None:
        found.append(
            PreferenceMatch(
                key="canopy",
                label="Tree canopy",
                detail="Tree density along the path",
                matched=metrics.canopy >= preferences.canopy,
                value=metrics.canopy,
            )
        )

    if preferences.shade is not None:
        # Park trees stand in open ground and shade more of the path than a
        # street planting does. It is a proxy for shade, not a measurement of
        # it, and the copy has to keep saying so.
        found.append(
            PreferenceMatch(
                key="shade",
                label="Shade & thermal comfort",
                detail="Park vs. street trees nearby",
                matched=metrics.parkShare >= preferences.shade,
                value=metrics.parkShare,
            )
        )

    if preferences.noise is not None:
        wants_quiet = preferences.noise == "quiet"
        value = metrics.parkShare if wants_quiet else 100 - metrics.parkShare
        found.append(
            PreferenceMatch(
                key="noise",
                label="Noise level",
                detail="Park vs. street trees nearby",
                matched=value >= 50,
                value=value,
            )
        )

    # Allergy stays out entirely until the taxonomy is agreed. Absent reads as
    # unknown; a zero here would render as "does not match", which is a claim
    # about pollen that nothing in the data supports.

    if preferences.walkingTime is not None:
        budget = preferences.walkingTime + WALKING_TIME_TOLERANCE_MINUTES
        found.append(
            PreferenceMatch(
                key="time",
                label="Walking time",
                detail=f"Your {preferences.walkingTime} min budget",
                matched=minutes <= budget,
                value=minutes,
            )
        )

    if not found:
        return None

    scored = [item for item in found if item.key != "time"]
    score = round(sum(item.value for item in scored) / len(scored)) if scored else 0
    return MatchSummary(score=score, matches=found, sentence=_sentence(found))


def _sentence(matches: list[PreferenceMatch]) -> str:
    """One line naming what was met, and what was not.

    AC4 asks the explanation to reference at least one selected preference, and
    forbids describing a level as something it is not — so this is assembled
    from the same matched flags the panel renders, never written separately.
    """
    met = [item.label.lower() for item in matches if item.matched]
    missed = [item.label.lower() for item in matches if not item.matched]

    if met and missed:
        return f"Matches your {_join(met)}, but not your {_join(missed)}."
    if met:
        return f"Matches your {_join(met)}."
    return f"The closest available route, though it misses your {_join(missed)}."


def _join(labels: list[str]) -> str:
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


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

    scored = [
        (_corridor(_decode_polyline(item["polyline"]["encodedPolyline"]), session), item)
        for item in candidates
    ]

    if request.travelMode == "TRANSIT":
        # Selection is by time alone. The tree count still comes back — it is a
        # true count of trees near the path — but nothing is scored or claimed.
        chosen = min(scored, key=lambda candidate: _duration_seconds(candidate[1]["duration"]))
        return _result(request.travelMode, chosen, len(candidates))

    # Time is a constraint, not a scored dimension: a route that blows the
    # budget is out of the running however leafy it is. If none qualify the
    # user still gets the best of what exists, with a message saying so, rather
    # than an empty screen (AC7).
    budget = request.preferences.walkingTime if request.preferences else None
    within = scored
    message = None
    if budget is not None:
        limit = budget + WALKING_TIME_TOLERANCE_MINUTES
        within = [item for item in scored if _duration_minutes(item[1]) <= limit]
        if not within:
            within = scored
            message = (
                f"No route came in under {budget} min. This is the best match "
                "of what's available."
            )

    chosen = _best(within)
    corridor, route = chosen
    metrics = corridor.metrics(_distance_km(route))
    return _result(
        request.travelMode,
        chosen,
        len(candidates),
        metrics=metrics,
        match=_match(request.preferences, metrics, _duration_minutes(route)),
        message=message,
    )


def _best(scored: list[tuple[Corridor, dict]]) -> tuple[Corridor, dict]:
    """The leafiest candidate per kilometre, shortest first among equals.

    Per kilometre rather than in total: a longer way round passes more trees
    without being any leafier, and ranking on the raw count would reward the
    detour for being long.

    Duration is the tie-break rather than a competing goal — two alternatives
    often pass the same trees, and there is no reason to return the longer one.
    """
    return max(
        scored,
        key=lambda candidate: (
            candidate[0].trees / max(_distance_km(candidate[1]), 0.01),
            -_duration_seconds(candidate[1]["duration"]),
        ),
    )


def _distance_km(route: dict) -> float:
    return round(route["distanceMeters"] / 1000, 1)


def _duration_minutes(route: dict) -> int:
    return round(_duration_seconds(route["duration"]) / 60)


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


def _result(
    travel_mode: TravelMode,
    scored: tuple[Corridor, dict],
    candidate_count: int,
    metrics: AreaMetrics | None = None,
    match: MatchSummary | None = None,
    message: str | None = None,
) -> RouteResult:
    corridor, route = scored
    return RouteResult(
        label=(
            "Personalised walking route" if travel_mode == "WALK" else "Personalised transit route"
        ),
        travelMode=travel_mode,
        durationMinutes=_duration_minutes(route),
        distanceKm=_distance_km(route),
        treeCount=corridor.trees,
        encodedPolyline=route["polyline"]["encodedPolyline"],
        candidateCount=candidate_count,
        metrics=metrics,
        match=match,
        message=message,
    )


def _duration_seconds(value: str) -> int:
    return round(float(value.removesuffix("s")))


def _corridor(path: list[tuple[float, float]], session: SessionDep) -> Corridor:
    """Every tree within 100m of the route, counted three ways.

    One query feeds all three scorers. It reads trees rather than zone centres:
    a zone contributes its whole count the moment its centre falls in range,
    which is close enough for "is this walk leafy" but cannot answer park-vs-
    street, because located_in lives on the tree.
    """
    if not path:
        return Corridor(trees=0, park=0)

    latitudes = [point[0] for point in path]
    longitudes = [point[1] for point in path]
    padding = 0.002  # ~200m, so the bbox covers the corridor at either end
    rows = session.execute(
        text(
            """
            SELECT latitude, longitude, located_in
            FROM trees
            WHERE latitude BETWEEN :south AND :north
              AND longitude BETWEEN :west AND :east
            """
        ),
        {
            "south": min(latitudes) - padding,
            "north": max(latitudes) + padding,
            "west": min(longitudes) - padding,
            "east": max(longitudes) + padding,
        },
    ).all()

    near = [
        row
        for row in rows
        if min(_distance_m(row.latitude, row.longitude, lat, lng) for lat, lng in path)
        <= TREE_CORRIDOR_M
    ]
    return Corridor(
        trees=len(near),
        park=sum(1 for row in near if row.located_in == "Park"),
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
