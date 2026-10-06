"""Care for the Canopy (Epic 7): pinned trees, photos and messages.

API CONTRACT - agreed between frontend and backend before implementation.
Change this file and tell the other side; do not change response shapes silently.

Base path: /api/care (behind the access gate, like every /api route)

    POST /api/care/pins                          pin a tree at the user's live location
    PUT  /api/care/pins/{id}/photo               add or retake the pin's photo
    POST /api/care/pins/{id}/messages            post a message or a damage report
    GET  /api/care/zones/{zoneId}/messages       approved messages for an area (US7.5)
    POST /api/care/messages/{id}/review          approve or reject a message   (admin)
    POST /api/care/pins/{id}/photo/review        approve or reject a photo     (admin)

Publishing rules, from the Epic 7 acceptance criteria:

- Messages and photos from anyone are hidden until an admin approves them.
  Public reads only ever return approved rows.
- Damage reports are never public. They are stored for the council and are
  not shown in any area listing.
- Review endpoints need the X-Care-Admin header to match CARE_ADMIN_TOKEN. If
  that setting is empty, nobody can approve, so nothing goes public by mistake.
- No account is needed. The pin, photo and message are the whole record.

Photos arrive as JPEG, PNG or WebP data URLs that the browser has already
re-encoded, which strips location metadata (EXIF). The server also checks the
type and size, because it cannot trust the client.
"""

import hmac
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import text

from app.config import settings
from app.db import SessionDep

router = APIRouter()

MAX_BODY_CHARS = 500
# About 1.5 MB of image once base64 is decoded. Phone photos are resized on the
# device before upload, so anything larger is a mistake or an abuse attempt.
MAX_PHOTO_CHARS = 2_000_000
ALLOWED_PHOTO_PREFIXES = (
    "data:image/jpeg;base64,",
    "data:image/png;base64,",
    "data:image/webp;base64,",
)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PinCreate(CamelModel):
    zone_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=100_000)
    photo_data_url: str | None = None


class PhotoUpdate(CamelModel):
    photo_data_url: str


class MessageCreate(CamelModel):
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    kind: Literal["message", "damage_report"] = "message"


class ReviewUpdate(CamelModel):
    status: Literal["approved", "rejected"]


class Pin(CamelModel):
    id: str
    zone_id: str | None
    latitude: float
    longitude: float
    accuracy_m: float
    has_photo: bool
    photo_status: str
    created_at: str


class CareMessage(CamelModel):
    id: str
    pin_id: str
    zone_id: str | None
    body: str
    kind: str
    status: str
    created_at: str


class PublicPin(CamelModel):
    latitude: float
    longitude: float


class PublicMessage(CamelModel):
    id: str
    body: str
    created_at: str
    pin: PublicPin
    photo_data_url: str | None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _check_photo(photo_data_url: str | None) -> None:
    if photo_data_url is None:
        return
    if len(photo_data_url) > MAX_PHOTO_CHARS or not photo_data_url.startswith(
        ALLOWED_PHOTO_PREFIXES
    ):
        raise HTTPException(
            status_code=422, detail="Photo must be a JPEG, PNG or WebP image under 1.5 MB."
        )


def _require_admin(admin_token: str | None) -> None:
    expected = settings.care_admin_token
    if not expected or not admin_token or not hmac.compare_digest(admin_token, expected):
        raise HTTPException(status_code=403, detail="Admin approval is required.")


def _pin_row(row) -> Pin:
    return Pin(
        id=row.id,
        zone_id=row.zone_id,
        latitude=row.latitude,
        longitude=row.longitude,
        accuracy_m=row.accuracy_m,
        has_photo=row.photo_data is not None,
        photo_status=row.photo_status,
        created_at=row.created_at,
    )


def _load_pin(session, pin_id: str):
    row = session.execute(
        text(
            """
            SELECT id, zone_id, latitude, longitude, accuracy_m, photo_data, photo_status,
                   created_at
            FROM tree_pins WHERE id = :id
            """
        ),
        {"id": pin_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Pin not found.")
    return row


@router.post("/pins", response_model=Pin, status_code=201)
def create_pin(payload: PinCreate, session: SessionDep) -> Pin:
    """Pin the tree the user is standing next to (US7.1).

    The accuracy the phone reported is stored with the pin, so the card can show
    it and the council can judge how far to trust the position.
    """
    _check_photo(payload.photo_data_url)
    if payload.zone_id is not None:
        exists = session.execute(
            text("SELECT 1 FROM zones WHERE cluster_id = :z"), {"z": payload.zone_id}
        ).first()
        if exists is None:
            raise HTTPException(status_code=404, detail="Unknown zone.")
    pin_id = uuid.uuid4().hex
    session.execute(
        text(
            """
            INSERT INTO tree_pins
                (id, zone_id, latitude, longitude, accuracy_m, photo_data, photo_status, created_at)
            VALUES (:id, :zone_id, :lat, :lng, :acc, :photo, 'pending', :created)
            """
        ),
        {
            "id": pin_id,
            "zone_id": payload.zone_id,
            "lat": payload.latitude,
            "lng": payload.longitude,
            "acc": payload.accuracy_m,
            "photo": payload.photo_data_url,
            "created": _now(),
        },
    )
    session.commit()
    return _pin_row(_load_pin(session, pin_id))


@router.put("/pins/{pin_id}/photo", response_model=Pin)
def update_photo(pin_id: str, payload: PhotoUpdate, session: SessionDep) -> Pin:
    """Add or retake the photo (US7.2). A new photo goes back to pending review."""
    _check_photo(payload.photo_data_url)
    _load_pin(session, pin_id)
    session.execute(
        text("UPDATE tree_pins SET photo_data = :photo, photo_status = 'pending' WHERE id = :id"),
        {"photo": payload.photo_data_url, "id": pin_id},
    )
    session.commit()
    return _pin_row(_load_pin(session, pin_id))


@router.post("/pins/{pin_id}/messages", response_model=CareMessage, status_code=201)
def create_message(pin_id: str, payload: MessageCreate, session: SessionDep) -> CareMessage:
    """Post a message to a pinned tree (US7.3), or a damage report (US7.4).

    Every message starts pending. Damage reports stay pending for the council
    and are never published, whatever the review outcome.
    """
    pin = _load_pin(session, pin_id)
    message_id = uuid.uuid4().hex
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    session.execute(
        text(
            """
            INSERT INTO tree_messages (id, pin_id, zone_id, body, kind, status, created_at)
            VALUES (:id, :pin, :zone, :body, :kind, 'pending', :created)
            """
        ),
        {
            "id": message_id,
            "pin": pin_id,
            "zone": pin.zone_id,
            "body": body,
            "kind": payload.kind,
            "created": _now(),
        },
    )
    session.commit()
    return _message_row(session, message_id)


def _message_row(session, message_id: str) -> CareMessage:
    row = session.execute(
        text(
            "SELECT id, pin_id, zone_id, body, kind, status, created_at "
            "FROM tree_messages WHERE id = :id"
        ),
        {"id": message_id},
    ).first()
    return CareMessage(
        id=row.id,
        pin_id=row.pin_id,
        zone_id=row.zone_id,
        body=row.body,
        kind=row.kind,
        status=row.status,
        created_at=row.created_at,
    )


@router.get("/zones/{zone_id}/messages", response_model=list[PublicMessage])
def approved_messages(
    zone_id: str,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PublicMessage]:
    """Approved messages for one area, newest first (US7.5).

    A photo is included only when the photo itself was approved. A message can
    be public while its photo is still hidden.
    """
    rows = session.execute(
        text(
            """
            SELECT m.id, m.body, m.created_at, p.latitude, p.longitude,
                   CASE WHEN p.photo_status = 'approved' THEN p.photo_data END AS photo_data
            FROM tree_messages m
            JOIN tree_pins p ON p.id = m.pin_id
            WHERE m.zone_id = :zone AND m.status = 'approved' AND m.kind = 'message'
            ORDER BY m.created_at DESC
            LIMIT :limit
            """
        ),
        {"zone": zone_id, "limit": limit},
    ).all()
    return [
        PublicMessage(
            id=row.id,
            body=row.body,
            created_at=row.created_at,
            pin=PublicPin(latitude=row.latitude, longitude=row.longitude),
            photo_data_url=row.photo_data,
        )
        for row in rows
    ]


@router.post("/messages/{message_id}/review", response_model=CareMessage)
def review_message(
    message_id: str,
    payload: ReviewUpdate,
    session: SessionDep,
    x_care_admin: Annotated[str | None, Header()] = None,
) -> CareMessage:
    _require_admin(x_care_admin)
    result = session.execute(
        text("UPDATE tree_messages SET status = :status WHERE id = :id"),
        {"status": payload.status, "id": message_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Message not found.")
    session.commit()
    return _message_row(session, message_id)


@router.post("/pins/{pin_id}/photo/review", response_model=Pin)
def review_photo(
    pin_id: str,
    payload: ReviewUpdate,
    session: SessionDep,
    x_care_admin: Annotated[str | None, Header()] = None,
) -> Pin:
    _require_admin(x_care_admin)
    _load_pin(session, pin_id)
    session.execute(
        text("UPDATE tree_pins SET photo_status = :status WHERE id = :id"),
        {"status": payload.status, "id": pin_id},
    )
    session.commit()
    return _pin_row(_load_pin(session, pin_id))
