"""Multipart pin upload and community lookup. Device id is not an account."""

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.db import SessionDep
from app.dependencies import DeviceId
from app.schemas.common import Coordinates
from app.schemas.community import PinsResponse, TreePin
from app.services import community

router = APIRouter(prefix="/pins", tags=["Tree pins"])


@router.post("", response_model=TreePin, status_code=201)
def drop_pin(
    session: SessionDep,
    device_id: DeviceId,
    lat: Annotated[float, Form(ge=-90, le=90, allow_inf_nan=False)],
    lng: Annotated[float, Form(ge=-180, le=180, allow_inf_nan=False)],
    accuracy_m: Annotated[float, Form(alias="accuracyM", ge=0, allow_inf_nan=False)],
    photo: Annotated[UploadFile | None, File()] = None,
) -> TreePin:
    return community.create_pin(
        Coordinates(lat=lat, lng=lng), accuracy_m, device_id, photo, session
    )


@router.get("", response_model=PinsResponse)
def area_pins(
    session: SessionDep,
    device_id: DeviceId,
    zone_id: Annotated[str, Query(alias="zoneId", min_length=1, max_length=120)],
) -> PinsResponse:
    return community.list_pins(zone_id, device_id, session)
