"""CBD HTTP adapter. Owner: Tian."""

from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.cbd import CbdZones, ZoneFacts
from app.services import cbd_data

router = APIRouter(tags=["CBD data"])


@router.get("/cbd/zones", response_model=CbdZones)
def cbd_zones(session: SessionDep) -> CbdZones:
    return cbd_data.cbd_zones(session)


@router.get("/zones/{zone_id}/facts", response_model=ZoneFacts)
def zone_facts(zone_id: str, session: SessionDep) -> ZoneFacts:
    return cbd_data.zone_facts(zone_id, session)
