"""Owner: community developer. No automatic council/email/share actions."""

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.cbd import require_inside
from app.errors import feature_pending
from app.schemas.common import Coordinates
from app.schemas.community import MessageRequest, PinsResponse, TreeMessage, TreePin

MAX_PHOTO_BYTES = 5 * 1024 * 1024
NEAREST_TREE_METRES = 25
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png"}


def create_pin(
    position: Coordinates,
    accuracy_m: float,
    device_id: UUID,
    photo: UploadFile | None,
    session: Session,
) -> TreePin:
    require_inside(position.lat, position.lng)
    # TODO: bound file reads, decode/re-encode and strip metadata before private storage;
    # resolve zone from bounds + nearest tree within 25m; save pending; rate limit.
    feature_pending("community.create_pin")


def post_message(
    pin_id: UUID, request: MessageRequest, device_id: UUID, session: Session
) -> TreeMessage:
    # TODO: validate pin, author access and rate limit; save pending; never email.
    feature_pending("community.post_message")


def list_pins(zone_id: str, device_id: UUID, session: Session) -> PinsResponse:
    # TODO: approved + caller-owned pending only, with message AND photo checks.
    # Never return device ids, nearest_tree_id, raw storage paths or public bucket URLs.
    feature_pending("community.list_pins")
