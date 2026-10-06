from uuid import UUID

from fastapi import APIRouter

from app.db import SessionDep
from app.dependencies import DeviceId
from app.schemas.community import MessageRequest, TreeMessage
from app.services import community

router = APIRouter(prefix="/pins", tags=["Tree messages"])


@router.post("/{pin_id}/messages", response_model=TreeMessage, status_code=201)
def write_message(
    pin_id: UUID, request: MessageRequest, device_id: DeviceId, session: SessionDep
) -> TreeMessage:
    return community.post_message(pin_id, request, device_id, session)
