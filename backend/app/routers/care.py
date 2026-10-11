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
- Damage reports can appear alongside messages only after admin approval.
  Saving a report does not submit it to the council; the visitor shares it separately.
- Review endpoints need the X-Care-Admin header to match CARE_ADMIN_TOKEN. If
  that setting is empty, nobody can approve, so nothing goes public by mistake.
- No account is needed. The pin, photo and message are the whole record.

Photos arrive as JPEG, PNG or WebP data URLs that the browser has already
re-encoded, which strips location metadata (EXIF). The server also checks the
type and size, because it cannot trust the client.

DEVICE CREDENTIALS (hardening)
-------------------------------
A pin and its messages carry a deviceId the browser makes up and keeps in
localStorage - that alone would let anyone pin or message under someone
else's deviceId just by guessing or copying the string. The first time a
device posts, the server issues it a random credential (returned once, as
deviceToken) and remembers only its hash; every later post from that
deviceId must present the matching X-Device-Token header. A device with no
credential and no token is treated as new. Retaking a pin's photo or
messaging under it also requires the token that created the pin - except a
pin from before this feature shipped, which has no deviceId to check against
and is left open. POSTS_PER_DEVICE_PER_HOUR caps pins + messages per device.
"""

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import SessionDep
from app.services.content_filter import is_unsafe_text

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
DeviceToken = Annotated[str | None, Header(alias="X-Device-Token")]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PinCreate(CamelModel):
    zone_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=100_000)
    photo_data_url: str | None = None
    device_id: str = Field(min_length=8, max_length=100)


class PhotoUpdate(CamelModel):
    photo_data_url: str
    device_id: str = Field(min_length=8, max_length=100)


class MessageCreate(CamelModel):
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    kind: Literal["message", "damage_report"] = "message"
    device_id: str = Field(min_length=8, max_length=100)


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
    # Only set once, in the response to the POST that first registers this
    # device - the client stores it and sends it back as X-Device-Token.
    device_token: str | None = None


class CareMessage(CamelModel):
    id: str
    pin_id: str
    zone_id: str | None
    body: str
    kind: str
    status: str
    created_at: str
    device_token: str | None = None


class PublicPin(CamelModel):
    latitude: float
    longitude: float


class PublicMessage(CamelModel):
    id: str
    kind: Literal["message", "damage_report"]
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


def _authorize_or_register_device(session, device_id: str, token: str | None) -> str | None:
    """Verifies the device's existing credential, or issues it a new one.

    Returns the raw token only when one was just issued - that is the one
    time the caller needs to pass it back to the browser, since only its
    hash is kept from here on.
    """
    row = session.execute(
        text("SELECT credential_hash FROM device_credentials WHERE device_id = :device"),
        {"device": device_id},
    ).first()
    if row is not None:
        supplied_hash = sha256(token.encode()).hexdigest() if token else ""
        if not token or not hmac.compare_digest(supplied_hash, row.credential_hash):
            raise HTTPException(status_code=403, detail="Invalid device credential.")
        return None
    if token:
        # A token was presented for a device with no stored credential - it
        # cannot be a valid one.
        raise HTTPException(status_code=403, detail="Invalid device credential.")
    issued = token_urlsafe(32)
    try:
        session.execute(
            text(
                "INSERT INTO device_credentials (device_id, credential_hash, created_at) "
                "VALUES (:device, :hash, :created)"
            ),
            {"device": device_id, "hash": sha256(issued.encode()).hexdigest(), "created": _now()},
        )
    except IntegrityError as error:
        # Two requests from the same brand-new device raced to register.
        session.rollback()
        raise HTTPException(status_code=409, detail="Try again.") from error
    return issued


def _require_pin_owner(pin_device_id: str | None, device_id: str) -> None:
    # A pin from before device credentials existed has no owner to check.
    if pin_device_id is not None and pin_device_id != device_id:
        raise HTTPException(
            status_code=403, detail="Only the device that made this pin can do that."
        )


def _rate_limit(session, device_id: str) -> None:
    if settings.posts_per_device_per_hour == 0:
        return
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    count = session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM tree_pins
                 WHERE device_id = :device AND created_at >= :since) +
                (SELECT COUNT(*) FROM tree_messages
                 WHERE device_id = :device AND created_at >= :since)
            """
        ),
        {"device": device_id, "since": since},
    ).scalar_one()
    if count >= settings.posts_per_device_per_hour:
        raise HTTPException(
            status_code=429, detail="Too many posts from this device. Try again later."
        )


def _pin_row(row, device_token: str | None = None) -> Pin:
    return Pin(
        id=row.id,
        zone_id=row.zone_id,
        latitude=row.latitude,
        longitude=row.longitude,
        accuracy_m=row.accuracy_m,
        has_photo=row.photo_data is not None,
        photo_status=row.photo_status,
        created_at=row.created_at,
        device_token=device_token,
    )


def _load_pin(session, pin_id: str):
    row = session.execute(
        text(
            """
            SELECT id, zone_id, latitude, longitude, accuracy_m, photo_data, photo_status,
                   device_id, created_at
            FROM tree_pins WHERE id = :id
            """
        ),
        {"id": pin_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Pin not found.")
    return row


@router.post("/pins", response_model=Pin, status_code=201)
def create_pin(payload: PinCreate, session: SessionDep, x_device_token: DeviceToken = None) -> Pin:
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
    issued_token = _authorize_or_register_device(session, payload.device_id, x_device_token)
    _rate_limit(session, payload.device_id)
    pin_id = uuid.uuid4().hex
    session.execute(
        text(
            """
            INSERT INTO tree_pins
                (id, zone_id, latitude, longitude, accuracy_m, photo_data, photo_status,
                 device_id, created_at)
            VALUES (:id, :zone_id, :lat, :lng, :acc, :photo, 'pending', :device, :created)
            """
        ),
        {
            "id": pin_id,
            "zone_id": payload.zone_id,
            "lat": payload.latitude,
            "lng": payload.longitude,
            "acc": payload.accuracy_m,
            "photo": payload.photo_data_url,
            "device": payload.device_id,
            "created": _now(),
        },
    )
    session.commit()
    return _pin_row(_load_pin(session, pin_id), device_token=issued_token)


@router.put("/pins/{pin_id}/photo", response_model=Pin)
def update_photo(
    pin_id: str, payload: PhotoUpdate, session: SessionDep, x_device_token: DeviceToken = None
) -> Pin:
    """Add or retake the photo (US7.2). A new photo goes back to pending review."""
    _check_photo(payload.photo_data_url)
    pin = _load_pin(session, pin_id)
    _require_pin_owner(pin.device_id, payload.device_id)
    issued_token = _authorize_or_register_device(session, payload.device_id, x_device_token)
    session.execute(
        text("UPDATE tree_pins SET photo_data = :photo, photo_status = 'pending' WHERE id = :id"),
        {"photo": payload.photo_data_url, "id": pin_id},
    )
    session.commit()
    return _pin_row(_load_pin(session, pin_id), device_token=issued_token)


@router.post("/pins/{pin_id}/messages", response_model=CareMessage, status_code=201)
def create_message(
    pin_id: str, payload: MessageCreate, session: SessionDep, x_device_token: DeviceToken = None
) -> CareMessage:
    """Post a message to a pinned tree (US7.3), or a damage report (US7.4).

    Text must pass the community filter. Every message and damage report starts
    pending and can only appear publicly after administrator approval.
    """
    pin = _load_pin(session, pin_id)
    _require_pin_owner(pin.device_id, payload.device_id)
    issued_token = _authorize_or_register_device(session, payload.device_id, x_device_token)
    _rate_limit(session, payload.device_id)
    message_id = uuid.uuid4().hex
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    if is_unsafe_text(body):
        raise HTTPException(
            status_code=422,
            detail="Please keep community messages respectful and free of adult content.",
        )
    session.execute(
        text(
            """
            INSERT INTO tree_messages
                (id, pin_id, zone_id, body, kind, device_id, status, created_at)
            VALUES (:id, :pin, :zone, :body, :kind, :device, 'pending', :created)
            """
        ),
        {
            "id": message_id,
            "pin": pin_id,
            "device": payload.device_id,
            "zone": pin.zone_id,
            "body": body,
            "kind": payload.kind,
            "created": _now(),
        },
    )
    session.commit()
    return _message_row(session, message_id, device_token=issued_token)


def _message_row(session, message_id: str, device_token: str | None = None) -> CareMessage:
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
        device_token=device_token,
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
            SELECT m.id, m.kind, m.body, m.created_at, p.latitude, p.longitude,
                   CASE WHEN p.photo_status = 'approved' THEN p.photo_data END AS photo_data
            FROM tree_messages m
            JOIN tree_pins p ON p.id = m.pin_id
            WHERE m.zone_id = :zone AND m.status = 'approved'
              AND m.kind IN ('message', 'damage_report')
            ORDER BY m.created_at DESC
            LIMIT :limit
            """
        ),
        {"zone": zone_id, "limit": limit},
    ).all()
    return [
        PublicMessage(
            id=row.id,
            kind=row.kind,
            body=row.body,
            created_at=row.created_at,
            pin=PublicPin(latitude=row.latitude, longitude=row.longitude),
            photo_data_url=row.photo_data,
        )
        for row in rows
        if not is_unsafe_text(row.body)
    ]


@router.post("/messages/{message_id}/review", response_model=CareMessage)
def review_message(
    message_id: str,
    payload: ReviewUpdate,
    session: SessionDep,
    x_care_admin: Annotated[str | None, Header()] = None,
) -> CareMessage:
    _require_admin(x_care_admin)
    if payload.status == "approved":
        message = session.execute(
            text("SELECT body FROM tree_messages WHERE id = :id"), {"id": message_id}
        ).first()
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found.")
        if is_unsafe_text(message.body):
            raise HTTPException(status_code=422, detail="This message failed the content filter.")
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
