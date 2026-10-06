"""SQL access owned by the community developer; commit complete transactions."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.community import PinsResponse, TreeMessage, TreePin


def insert_pin(
    session: Session,
    pin: TreePin,
    device_id: UUID,
    photo_path: str | None,
    nearest_tree_id: int | None,
) -> None:
    raise NotImplementedError("tree_pins insert pending")


def insert_message(session: Session, message: TreeMessage, device_id: UUID) -> None:
    raise NotImplementedError("tree_messages insert pending")


def visible_pins(session: Session, zone_id: str, device_id: UUID) -> PinsResponse:
    # TODO: authorization must apply independently to pins, messages and attached photos.
    raise NotImplementedError("community visibility query pending")
