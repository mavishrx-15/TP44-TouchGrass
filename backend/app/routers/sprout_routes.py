"""Planning HTTP adapter; business logic lives in services/planning.py."""

from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.planning import AreasRequest, AreasResponse, PlannedRoute, RoutePlanningRequest
from app.services import planning

router = APIRouter(prefix="/sprout", tags=["Iteration 3 planning"])


@router.post("/route", response_model=PlannedRoute)
def grow_route(request: RoutePlanningRequest, session: SessionDep) -> PlannedRoute:
    return planning.plan_route(request, session)


@router.post("/areas", response_model=AreasResponse)
def other_areas(request: AreasRequest, session: SessionDep) -> AreasResponse:
    return planning.recommend_areas(request, session)
