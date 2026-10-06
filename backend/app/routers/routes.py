"""Walking routes backed by Google Routes and scored against local tree zones."""

from math import asin, cos, radians, sin, sqrt
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.cbd import coverage_bounds, require_inside
from app.config import settings
from app.db import SessionDep
from app.schemas.common import Coordinates
from app.schemas.map_data import AreaMetrics
from app.services.zone_data import HIGH_POLLEN_FAMILIES, HIGH_POLLEN_GENERA

router = APIRouter()
EARTH_RADIUS_M = 6_371_000
TREE_CORRIDOR_M = 100

TravelMode = Literal["WALK", "TRANSIT"]

# Iteration-2 handoff, "Prototype rules requiring team confirmation".
WALKING_TIME_TOLERANCE_MINUTES = 2


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
    """What stands within 100m of a route: tree counts, and a canopy rank."""

    trees: int
    park: int
    high_pollen: int
    canopy: int  # mean percentile of the zones the route passes through

    def metrics(self) -> AreaMetrics:
        return AreaMetrics(
            canopy=self.canopy,
            parkShare=self._share(self.park),
            lowAllergyShare=self._share(self.trees - self.high_pollen),
            highPollenTrees=self.high_pollen,
        )

    def _share(self, part: int) -> int:
        return round(100 * part / self.trees) if self.trees else 0


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

    if preferences.allergy is not None and metrics.lowAllergyShare is not None:
        # Both settings read the same share. "avoid" and "lower" would need two
        # different thresholds to behave differently, and nothing has fixed
        # those — one rule is better than two invented ones.
        found.append(
            PreferenceMatch(
                key="allergy",
                label="Allergy preference",
                detail=f"{metrics.highPollenTrees} high-pollen trees along the path",
                matched=metrics.lowAllergyShare >= 50,
                value=metrics.lowAllergyShare,
            )
        )

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
    """Restrict predictions to the CBD and check each actual place location."""
    bounds = coverage_bounds()
    payload = {
        "input": query,
        "includedRegionCodes": ["au"],
        "languageCode": "en-AU",
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": bounds["south"], "longitude": bounds["west"]},
                "high": {"latitude": bounds["north"], "longitude": bounds["east"]},
            }
        },
    }
    data = _google_request(
        "POST",
        "https://places.googleapis.com/v1/places:autocomplete",
        field_mask="suggestions.placePrediction.placeId,suggestions.placePrediction.text.text",
        json=payload,
    )
    suggestions = []
    for item in data.get("suggestions", []):
        prediction = item.get("placePrediction")
        if not prediction:
            continue
        # Restriction rectangles can still contain points outside the rotated
        # grid. Resolve each prediction before exposing it to any search UI.
        try:
            place = place_details(prediction["placeId"])
        except HTTPException as error:
            if error.status_code in (404, 422):
                continue
            raise
        suggestions.append(PlaceSuggestion(id=place.id, label=prediction["text"]["text"]))
    return suggestions


@router.get("/places/{place_id}", response_model=PlaceDetails)
def place_details(place_id: str) -> PlaceDetails:
    """Resolve a selected Google place to routeable coordinates."""
    data = _google_request(
        "GET",
        f"https://places.googleapis.com/v1/places/{place_id}",
        field_mask="id,displayName,location",
    )
    location = data.get("location")
    if not location:
        raise HTTPException(status_code=404, detail="Place has no location.")
    coordinates = Coordinates(lat=location["latitude"], lng=location["longitude"])
    require_inside(coordinates.lat, coordinates.lng)
    return PlaceDetails(
        id=data["id"],
        label=data["displayName"]["text"],
        coordinates=coordinates,
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
    require_inside(request.origin.lat, request.origin.lng)
    require_inside(request.destination.lat, request.destination.lng)

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
    metrics = corridor.metrics()
    return _result(
        request.travelMode,
        chosen,
        len(candidates),
        metrics=metrics,
        match=_match(request.preferences, metrics, _duration_minutes(route)),
        message=message,
    )


def _best(scored: list[tuple[Corridor, dict]]) -> tuple[Corridor, dict]:
    """The candidate through the leafiest areas, shortest first among equals.

    Ranking on the canopy percentile rather than a raw count keeps length out of
    it — a longer way round passes more trees without going anywhere leafier,
    and a total would reward the detour for being long.

    Duration is the tie-break rather than a competing goal: two alternatives
    often cross the same zones, and there is no reason to return the longer one.
    """
    return max(
        scored,
        key=lambda candidate: (
            candidate[0].canopy,
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


CORRIDOR_SAMPLE_POINTS = 120


def _resample_path(
    path: list[tuple[float, float]], max_points: int = CORRIDOR_SAMPLE_POINTS
) -> list[tuple[float, float]]:
    """Evenly-spaced subset of path points for the corridor membership check.

    A 100m corridor doesn't need every polyline vertex checked - Google packs
    one every few metres, so for a several-km route _near() was comparing
    thousands of trees against a similar number of points (15s+ for a 5km
    route). A few dozen evenly spaced points keep sub-100m spacing for
    walking-scale routes without the O(trees x points) blowup; the bounding
    box query above still uses the full path so it isn't narrowed by this.
    """
    if len(path) <= max_points:
        return path
    step = (len(path) - 1) / (max_points - 1)
    return [path[round(i * step)] for i in range(max_points)]


def _corridor(path: list[tuple[float, float]], session: SessionDep) -> Corridor:
    """Everything within 100m of the route: the trees, and the zones.

    The trees answer park-versus-street and high-pollen, which live on the tree
    row. The zones answer canopy, because canopy is defined as a zone's rank
    inside its own precinct and a route has no precinct of its own to be ranked
    in — it is scored by the areas it passes through.
    """
    if not path:
        return Corridor(trees=0, park=0, high_pollen=0, canopy=0)

    corridor_path = _resample_path(path)
    boxes = _corridor_boxes(corridor_path)

    tree_where, tree_params = _corridor_where(boxes, "latitude", "longitude", "t")
    trees = _near(
        session.execute(
            text(
                f"""
                SELECT latitude, longitude, located_in, display_category, family
                FROM trees
                WHERE {tree_where}
                """
            ),
            tree_params,
        ).all(),
        corridor_path,
        lambda row: (row.latitude, row.longitude),
    )

    # Ranked across every zone before the corridor boxes narrow it down: a
    # zone's percentile is a property of its precinct, not of this route's
    # neighbours.
    zone_where, zone_params = _corridor_where(boxes, "center_lat", "center_lon", "z")
    zones = _near(
        session.execute(
            text(
                f"""
                SELECT center_lat, center_lon, canopy_rank FROM (
                    SELECT center_lat, center_lon,
                           PERCENT_RANK() OVER (
                               PARTITION BY precinct ORDER BY tree_count
                           ) AS canopy_rank
                    FROM zones
                ) ranked
                WHERE {zone_where}
                """
            ),
            zone_params,
        ).all(),
        corridor_path,
        lambda row: (row.center_lat, row.center_lon),
    )

    return Corridor(
        trees=len(trees),
        park=sum(1 for row in trees if row.located_in == "Park"),
        high_pollen=sum(
            1
            for row in trees
            if row.display_category in HIGH_POLLEN_GENERA or row.family in HIGH_POLLEN_FAMILIES
        ),
        canopy=round(100 * sum(row.canopy_rank for row in zones) / len(zones)) if zones else 0,
    )


def _corridor_boxes(path: list[tuple[float, float]]) -> list[dict[str, float]]:
    """A small box around each sampled path point, instead of one box for
    the whole route.

    A single min/max bounding box over a long or diagonal route pulls in
    every tree between its ends - for a 5km route that was ~29,000 trees
    fetched (and then checked one by one against every path point in
    Python) versus the low hundreds actually within 100m of the path. Many
    small boxes, OR'd together in SQL, let the database do that narrowing
    instead.
    """
    padding = 0.001  # ~110m: a bit more than TREE_CORRIDOR_M, trimmed exactly by _near()
    return [
        {
            "south": lat - padding,
            "north": lat + padding,
            "west": lng - padding,
            "east": lng + padding,
        }
        for lat, lng in path
    ]


def _corridor_where(
    boxes: list[dict[str, float]], lat_col: str, lng_col: str, prefix: str
) -> tuple[str, dict[str, float]]:
    """An `OR`-of-ranges SQL clause covering every box, with bound params.

    lat_col/lng_col are trusted column names from callers in this module,
    not request input, so interpolating them is safe.
    """
    clauses = []
    params: dict[str, float] = {}
    for i, box in enumerate(boxes):
        clauses.append(
            f"({lat_col} BETWEEN :{prefix}_s{i} AND :{prefix}_n{i} "
            f"AND {lng_col} BETWEEN :{prefix}_w{i} AND :{prefix}_e{i})"
        )
        params[f"{prefix}_s{i}"] = box["south"]
        params[f"{prefix}_n{i}"] = box["north"]
        params[f"{prefix}_w{i}"] = box["west"]
        params[f"{prefix}_e{i}"] = box["east"]
    return " OR ".join(clauses), params


def _near(rows: list, path: list[tuple[float, float]], point) -> list:
    """Rows whose point falls within the corridor, not just the bounding box."""
    return [
        row
        for row in rows
        if min(_distance_m(*point(row), lat, lng) for lat, lng in path) <= TREE_CORRIDOR_M
    ]


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
