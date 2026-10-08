"""Route planning for Sprout: choose a destination, then a route to it.

The backend picks the destination, not the browser (design doc, section 2).
That is what fixes the old bugs: a 20+ min choice getting a 7 min walk, pollen
never changing which route was picked, and a State Library start being sent to
a one-zone precinct.

    1. Reject a start outside the CBD (422 outside_cbd).
    2. Estimate every CBD zone's walk — straight line x 1.3 / 80 m per minute —
       and prefer the ones inside the walking-time band.
    3. Filter by canopy, then rank by park share and, for Avoid high pollen,
       by the smallest share of high-pollen trees.
    4. Ask Google for routes to the top three and measure each one's corridor.
    5. Pick a route whose real time is in the band; then the smallest share of
       high-pollen trees, if asked; then most canopy; then shortest.
    6. If none fits the band, return the closest and say so.

Steps 2 and 3 alone are /api/sprout/areas, so "See other options" and "Find
more trees near you" rank exactly the way the route does.
"""

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cbd import require_inside
from app.integrations import google_routes
from app.repositories import planning as repository
from app.routers.routes import Corridor, _corridor, _decode_polyline, _distance_m
from app.schemas.cbd import CbdZone
from app.schemas.common import Coordinates
from app.schemas.planning import (
    AreaOption,
    AreasRequest,
    AreasResponse,
    Destination,
    PlannedRoute,
    PlanningRequest,
    PreferenceMatch,
    Preferences,
    RouteStep,
)
from app.services import sprout
from app.services.sprout import LOWEST_AVAILABLE, LOWEST_POLLEN, NO_POLLEN

# Confirmed design bands, inclusive. 20 means 20+, not a maximum of 20.
TIME_BANDS = {5: (3, 7), 10: (8, 12), 15: (13, 17), 20: (18, 30), None: (5, 15)}
DETOUR_FACTOR = 1.3
WALK_METRES_PER_MINUTE = 80
REROUTE_INTERVAL_SECONDS = 20
GOOGLE_CANDIDATES = 3

# Inside the CBD only two zones are High, so "dense" has to admit Medium or it
# would leave almost nothing to choose from (design doc, section 2).
DENSE_ENOUGH = {"Medium", "High"}

# Shade is mapped to 20 / 50 / 85 so the existing park-share check keeps
# working (design doc, section 2). Noise reuses the same two ends: a quiet walk
# leans park-side, a lively one street-side.
SHADE_TARGET = {"sunny": 20, "mixed": 50, "cool": 85}
NOISE_TARGET = {"quiet": 85, "lively": 20}

# Park share and pollen share are compared in 10-point steps when ranking
# areas, so that two areas about as shady, or about as pollen-heavy, as each
# other are told apart by the next rule instead of by one percentage point.
SHARE_STEP = 10

CHIPS = {
    "canopy": {"open": "Open sky", "mixed": "Some canopy", "dense": "Deep canopy"},
    "shade": {"sunny": "Sunny and open", "mixed": "Some shade", "cool": "Cool and shaded"},
    "noise": {"quiet": "Quieter", "lively": "Lively"},
    "allergy": {"avoid": "Avoid high pollen"},
    "walkingTime": {5: "5 min", 10: "10 min", 15: "15 min", 20: "20+ min"},
}


@dataclass
class Candidate:
    zone: CbdZone
    estimated_minutes: float
    distance_meters: float


@dataclass
class Option:
    candidate: Candidate
    route: dict
    corridor: Corridor

    @property
    def minutes(self) -> float:
        return float(self.route["duration"].removesuffix("s")) / 60


def plan_route(request: PlanningRequest, session: Session) -> PlannedRoute:
    origin, preferences = request.origin, request.preferences
    require_inside(origin.lat, origin.lng)

    ranked = _ranked(origin, preferences, repository.candidate_zones(session))
    if not ranked:
        raise HTTPException(status_code=404, detail="No tree-dense area was found in the CBD.")

    options = [
        Option(
            candidate,
            route,
            _corridor(_decode_polyline(route["polyline"]["encodedPolyline"]), session),
        )
        for candidate in ranked[:GOOGLE_CANDIDATES]
        for route in google_routes.walking_alternatives(origin, candidate.zone.center)
    ]
    if not options:
        raise HTTPException(status_code=404, detail="No walking route was found.")

    low, high = TIME_BANDS[preferences.walkingTime]
    chosen = min(
        options,
        key=lambda option: (
            _band_gap(round(option.minutes), low, high),
            _pollen_step(option.corridor) if preferences.allergy == "avoid" else 0,
            -option.corridor.canopy,
            option.route.get("distanceMeters", 0),
        ),
    )

    planned = PlannedRoute(
        origin=origin,
        destination=_destination(chosen.candidate.zone),
        durationMinutes=round(chosen.minutes, 1),
        distanceMeters=chosen.route.get("distanceMeters", 0),
        encodedPolyline=chosen.route["polyline"]["encodedPolyline"],
        denseZoneShare=chosen.corridor.dense_share,
        summaryChips=_chips(preferences),
        matches=_matches(preferences, chosen, options, low, high),
        steps=_steps(chosen.route),
        message=_time_message(preferences, chosen, low, high),
    )
    planned.explanation = sprout.explain_route(planned, preferences)
    return planned


def recommend_areas(request: AreasRequest, session: Session) -> AreasResponse:
    origin = request.origin
    require_inside(origin.lat, origin.lng)
    ranked = _ranked(
        origin,
        request.preferences,
        repository.candidate_zones(session),
        excluded=set(request.excludedZoneIds),
    )
    return AreasResponse(
        areas=[
            AreaOption(
                destination=_destination(candidate.zone),
                estimatedMinutes=round(candidate.estimated_minutes, 1),
                distanceMeters=round(candidate.distance_meters),
            )
            for candidate in ranked[: request.limit]
        ]
    )


def _ranked(
    origin: Coordinates,
    preferences: Preferences,
    zones: list[CbdZone],
    excluded: set[str] | frozenset[str] = frozenset(),
) -> list[Candidate]:
    """Steps 2 and 3: every CBD zone, best first.

    Zones inside the time band come first; when none are, the nearest to it
    lead instead, so there is always a closest answer rather than an empty list.

    Canopy is a filter. Only "Open sky" admits Low zones: with no canopy
    preference the destination is still a tree-dense area, because that is what
    the rest of the journey calls it ("You've reached your tree-dense area",
    US6.5). The filter never empties the list — if nothing is dense enough, the
    ranking falls back to every zone.

    Pollen is ranked by share, not by count. Counting rewards a small zone for
    being small — fewer trees, so fewer high-pollen ones — and with Deep canopy
    also chosen it sends the walk to the sparsest patch on offer.
    """
    candidates = [_estimate(origin, zone) for zone in zones if zone.id not in excluded]
    if preferences.canopy != "open":
        candidates = [c for c in candidates if c.zone.density in DENSE_ENOUGH] or candidates

    low, high = TIME_BANDS[preferences.walkingTime]
    target = _park_share_target(preferences)
    return sorted(
        candidates,
        key=lambda c: (
            _band_gap(round(c.estimated_minutes), low, high),
            (
                round(abs(c.zone.metrics.parkShare - target) / SHARE_STEP)
                if target is not None
                else 0
            ),
            (round(_pollen_share(c.zone) / SHARE_STEP) if preferences.allergy == "avoid" else 0),
            -c.zone.treeCount if preferences.canopy == "dense" else 0,
            c.estimated_minutes,
        ),
    )


def _estimate(origin: Coordinates, zone: CbdZone) -> Candidate:
    walking = _distance_m(origin.lat, origin.lng, zone.center.lat, zone.center.lng) * DETOUR_FACTOR
    return Candidate(zone, walking / WALK_METRES_PER_MINUTE, walking)


def _pollen_share(zone: CbdZone) -> int:
    """Percentage of the zone's trees that are high-pollen."""
    low_allergy = zone.metrics.lowAllergyShare
    return 100 - low_allergy if low_allergy is not None else 0


def _band_gap(minutes: int, low: int, high: int) -> int:
    """How far outside the band a walk is, in whole minutes; 0 when it fits.

    Callers pass the minutes rounded the way the card shows them, so a walk
    that reads "7 min" counts as fitting a 3-7 band. Comparing unrounded
    minutes here while the card rounds would pick a 7.4 min route as fitting
    and then tell the user it was too long.
    """
    return max(low - minutes, minutes - high, 0)


def _park_share_target(preferences: Preferences) -> float | None:
    targets = [
        target
        for target in (
            SHADE_TARGET.get(preferences.shade),
            NOISE_TARGET.get(preferences.noise),
        )
        if target is not None
    ]
    return sum(targets) / len(targets) if targets else None


def _destination(zone: CbdZone) -> Destination:
    return Destination(
        zoneId=zone.id,
        label=zone.label,
        center=zone.center,
        bounds=zone.bounds,
        density=zone.density,
        treeCount=zone.treeCount,
    )


def _chips(preferences: Preferences) -> list[str]:
    """One chip per preference the user actually chose, in step order."""
    return [
        CHIPS[key][value]
        for key in ("canopy", "shade", "noise", "allergy", "walkingTime")
        if (value := getattr(preferences, key)) is not None
    ]


def _matches(
    preferences: Preferences, chosen: Option, options: list[Option], low: int, high: int
) -> list[PreferenceMatch]:
    """Whether the chosen route meets each preference that was set.

    Strict either way: a near miss is reported as missed, and nothing is
    reported for a preference the user left alone.
    """
    park = chosen.corridor.metrics().parkShare
    matches: list[PreferenceMatch] = []

    if preferences.canopy is not None:
        density = chosen.candidate.zone.density
        matches.append(
            PreferenceMatch(
                key="canopy",
                matched=preferences.canopy == "open" or density in DENSE_ENOUGH,
                detail=f"{density} tree density at the destination",
            )
        )

    if preferences.shade is not None:
        matches.append(
            PreferenceMatch(
                key="shade",
                matched=park >= SHADE_TARGET[preferences.shade],
                detail=f"{park}% of trees along the way are park trees",
            )
        )

    if preferences.noise is not None:
        quiet_side = park >= 50
        matches.append(
            PreferenceMatch(
                key="noise",
                matched=quiet_side if preferences.noise == "quiet" else not quiet_side,
                detail="Mostly park-side" if quiet_side else "Mostly street-side",
            )
        )

    if preferences.allergy == "avoid":
        matches.append(_pollen_match(chosen, options))

    if preferences.walkingTime is not None:
        matches.append(_time_match(preferences.walkingTime, chosen.minutes, low, high))

    return matches


def _pollen_step(corridor: Corridor) -> int:
    """A route's high-pollen share, in the same 10-point steps as areas.

    Share rather than count, as for areas. The design doc says "fewest
    high-pollen trees", and a count does measure exposure — how many pollen
    sources the walk passes — which is a fair reading for an allergy. But a
    route passing fewer trees altogether always wins on count, so with Deep
    canopy also chosen it picks the barest street on offer. Measured on Flinders
    Street Station to the 20+ band: a route past 279 trees, 68% of them
    high-pollen, beat one past 412 at 52%. Share keeps "lots of trees, few of
    them the pollen-heavy kind", which is what both preferences together ask for.
    """
    if not corridor.trees:
        return 0
    return round(100 * corridor.high_pollen / corridor.trees / SHARE_STEP)


def _pollen_match(chosen: Option, options: list[Option]) -> PreferenceMatch:
    """The design doc's wording, which never shows a raw pollen count.

    "Lowest-pollen" is claimed on the same measure the route was picked by, so
    the card cannot say one thing while the choice did another. It is only
    claimed when true across every route compared: a lower-pollen route that did
    not fit the walking time is not hidden behind it.
    """
    if chosen.corridor.high_pollen == 0:
        return PreferenceMatch(key="allergy", matched=True, detail=NO_POLLEN)
    if len(options) == 1:
        return PreferenceMatch(key="allergy", matched=True, detail=LOWEST_AVAILABLE)
    if _pollen_step(chosen.corridor) == min(_pollen_step(o.corridor) for o in options):
        return PreferenceMatch(key="allergy", matched=True, detail=LOWEST_POLLEN)
    return PreferenceMatch(
        key="allergy",
        matched=False,
        detail="A lower-pollen route didn't fit your walking time",
    )


def _time_match(choice: int, minutes: float, low: int, high: int) -> PreferenceMatch:
    shown = round(minutes)
    budget = "20+ min" if choice == 20 else f"{choice} min"
    if low <= shown <= high:
        return PreferenceMatch(
            key="time", matched=True, detail=f"{shown} min · fits your {budget} walk"
        )
    side = "shorter" if shown < low else "longer"
    return PreferenceMatch(
        key="time", matched=False, detail=f"{shown} min · {side} than your {budget} walk"
    )


def _time_message(preferences: Preferences, chosen: Option, low: int, high: int) -> str | None:
    """Step 6: say so when nothing fitted. Only for a time the user chose."""
    if preferences.walkingTime is None or _band_gap(round(chosen.minutes), low, high) == 0:
        return None
    budget = "20+ min" if preferences.walkingTime == 20 else f"{preferences.walkingTime} min"
    return f"No route fitted your {budget} walk, so this is the closest."


def _steps(route: dict) -> list[RouteStep]:
    """Turn-by-turn steps for the walk's direction tips (US6.3).

    streetName is left empty: Google gives the street inside the instruction
    text ("Head east on Flinders St"), and the tip can show that sentence as it
    is rather than guessing the street out of it.
    """
    steps = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            location = step.get("startLocation", {}).get("latLng")
            if not location:
                continue
            steps.append(
                RouteStep(
                    instruction=step.get("navigationInstruction", {}).get("instructions", ""),
                    start=Coordinates(lat=location["latitude"], lng=location["longitude"]),
                    distanceMeters=step.get("distanceMeters", 0),
                )
            )
    return steps
