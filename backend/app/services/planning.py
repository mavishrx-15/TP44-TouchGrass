"""Owner: route developer. Implement destination ranking and Google selection here."""

from sqlalchemy.orm import Session

from app.cbd import require_inside
from app.errors import feature_pending
from app.schemas.planning import AreasRequest, AreasResponse, PlannedRoute, PlanningRequest

# Confirmed design bands, inclusive. 20 means 20+, not a maximum of 20.
TIME_BANDS = {5: (3, 7), 10: (8, 12), 15: (13, 17), 20: (18, 30), None: (5, 15)}
DETOUR_FACTOR = 1.3
WALK_METRES_PER_MINUTE = 80
REROUTE_INTERVAL_SECONDS = 20


def plan_route(request: PlanningRequest, session: Session) -> PlannedRoute:
    require_inside(request.origin.lat, request.origin.lng)
    # TODO: shared area ranking -> top 3 Google requests -> corridor metrics -> selection.
    # Call sprout.explain_route only after producing factual match results.
    feature_pending("planning.route")


def recommend_areas(request: AreasRequest, session: Session) -> AreasResponse:
    require_inside(request.origin.lat, request.origin.lng)
    # TODO: use same ranking as plan_route; filter excludedZoneIds from device visits.
    feature_pending("planning.areas")
