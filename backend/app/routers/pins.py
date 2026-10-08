import secrets
import warnings
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.cbd import contains_in_geometry, geometry, require_inside
from app.config import settings
from app.db import SessionDep
from app.routers.map_data import _bounds

router = APIRouter()
MAX_PHOTO = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 40_000_000
DEVICE_LIMIT = 10


@router.post("/pins")
async def create_pin(
    session: SessionDep,
    lat: float = Form(ge=-90, le=90),
    lng: float = Form(ge=-180, le=180),
    accuracy_m: float = Form(gt=0, alias="accuracyM"),
    device_id: str = Form(min_length=8, max_length=100, alias="deviceId"),
    photo: UploadFile | None = File(default=None),  # noqa: B008
    device_token: str | None = Header(default=None, alias="X-Device-Token"),
) -> dict:
    require_inside(lat, lng)
    issued_device_token = _authorize_or_register_device(session, device_id, device_token)
    _rate_limit(session, device_id)
    zone = _zone_at(session, lat, lng)
    if not zone:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "outside_cbd",
                "message": "No CBD tree zone contains this location.",
            },
        )
    lat_delta, lng_delta = 25 / 111_000, 25 / (111_000 * max(cos(radians(lat)), 0.1))
    nearest = session.execute(
        text(
            """SELECT com_id, latitude, longitude FROM trees
        WHERE latitude BETWEEN :south AND :north AND longitude BETWEEN :west AND :east"""
        ),
        {
            "south": lat - lat_delta,
            "north": lat + lat_delta,
            "west": lng - lng_delta,
            "east": lng + lng_delta,
        },
    ).all()
    tree_id = min(
        ((r.com_id, _distance(lat, lng, r.latitude, r.longitude)) for r in nearest),
        key=lambda x: x[1],
        default=(None, 999999),
    )
    nearest_tree = tree_id[0] if tree_id[1] <= 25 else None
    pin_id, now, path = str(uuid4()), datetime.now(UTC), None
    if photo:
        content = await photo.read(MAX_PHOTO + 1)
        if len(content) > MAX_PHOTO:
            raise HTTPException(status_code=413, detail={"code": "photo_too_large"})
        safe_jpeg = _clean_photo(content, photo.content_type)
        path = _upload_photo(pin_id, safe_jpeg)
    session.execute(
        text(
            """INSERT INTO tree_pins
        (id, lat, lng, accuracy_m, cluster_id, photo_path, nearest_tree_id,
         device_id, status, created_at)
        VALUES (:id, :lat, :lng, :accuracy, :zone, :photo, :tree, :device, 'pending', :now)"""
        ),
        {
            "id": pin_id,
            "lat": lat,
            "lng": lng,
            "accuracy": accuracy_m,
            "zone": zone,
            "photo": path,
            "tree": nearest_tree,
            "device": device_id,
            "now": now,
        },
    )
    session.commit()
    return {
        "id": pin_id,
        "lat": lat,
        "lng": lng,
        "accuracyM": accuracy_m,
        "clusterId": zone,
        "photoUrl": _signed_photo(path) if path else None,
        "status": "pending",
        "createdAt": now.isoformat(),
        "deviceToken": issued_device_token,
    }


@router.post("/pins/{pin_id}/messages")
def create_message(
    pin_id: str,
    session: SessionDep,
    kind: str = Form(),
    body: str = Form(min_length=1, max_length=1000),
    device_id: str = Form(min_length=8, max_length=100, alias="deviceId"),
    device_token: str | None = Header(default=None, alias="X-Device-Token"),
) -> dict:
    if kind not in ("message", "report"):
        raise HTTPException(status_code=422, detail={"code": "invalid_message_kind"})
    _require_device_credential(session, device_id, device_token)
    pin = session.execute(
        text("SELECT device_id FROM tree_pins WHERE id=:id"), {"id": pin_id}
    ).first()
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found.")
    if pin.device_id != device_id:
        raise HTTPException(status_code=403, detail={"code": "pin_owner_required"})
    _rate_limit(session, device_id)
    message_id, now = str(uuid4()), datetime.now(UTC)
    session.execute(
        text(
            """INSERT INTO tree_messages (id,pin_id,kind,body,device_id,status,created_at)
        VALUES (:id,:pin,:kind,:body,:device,'pending',:now)"""
        ),
        {
            "id": message_id,
            "pin": pin_id,
            "kind": kind,
            "body": body.strip(),
            "device": device_id,
            "now": now,
        },
    )
    session.commit()
    return {
        "id": message_id,
        "pinId": pin_id,
        "kind": kind,
        "body": body.strip(),
        "status": "pending",
        "createdAt": now.isoformat(),
    }


@router.get("/pins")
def get_pins(
    session: SessionDep,
    zoneId: str = Query(min_length=1),
    x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
) -> list[dict]:
    if x_device_id and not x_device_token:
        raise HTTPException(status_code=403, detail={"code": "device_credential_required"})
    if x_device_token and not x_device_id:
        raise HTTPException(status_code=422, detail={"code": "device_id_required"})
    if x_device_id and x_device_token:
        _require_device_credential(session, x_device_id, x_device_token)
    if not session.execute(
        text("SELECT 1 FROM zones WHERE cluster_id=:id"), {"id": zoneId}
    ).first():
        raise HTTPException(status_code=404, detail="Unknown zone.")
    rows = session.execute(
        text(
            """SELECT id, lat, lng, accuracy_m, cluster_id, photo_path,
        device_id, status, created_at
        FROM tree_pins WHERE cluster_id=:zone AND status <> 'hidden'
          AND (status='approved' OR device_id=:device)
        ORDER BY created_at DESC"""
        ),
        {"zone": zoneId, "device": x_device_id or ""},
    ).all()
    result = []
    for pin in rows:
        messages = session.execute(
            text(
                """SELECT id, kind, body, device_id, status, created_at
            FROM tree_messages
            WHERE pin_id=:pin AND status <> 'hidden'
              AND (status='approved' OR device_id=:device) ORDER BY created_at"""
            ),
            {"pin": pin.id, "device": x_device_id or ""},
        ).all()
        result.append(
            {
                "id": pin.id,
                "lat": pin.lat,
                "lng": pin.lng,
                "accuracyM": pin.accuracy_m,
                "clusterId": pin.cluster_id,
                "photoUrl": _signed_photo(pin.photo_path) if pin.photo_path else None,
                "status": pin.status,
                "createdAt": _isoformat(pin.created_at),
                "messages": [
                    {
                        "id": m.id,
                        "kind": m.kind,
                        "body": m.body,
                        "status": m.status,
                        "createdAt": _isoformat(m.created_at),
                    }
                    for m in messages
                ],
            }
        )
    return result


def _authorize_or_register_device(
    session: SessionDep, device_id: str, token: str | None
) -> str | None:
    credential = session.execute(
        text("SELECT credential_hash FROM device_credentials WHERE device_id=:device"),
        {"device": device_id},
    ).first()
    if credential:
        _require_matching_credential(credential.credential_hash, token)
        return None

    existing_content = session.execute(
        text(
            """
            SELECT 1 FROM tree_pins WHERE device_id=:device
            UNION ALL
            SELECT 1 FROM tree_messages WHERE device_id=:device
            LIMIT 1
            """
        ),
        {"device": device_id},
    ).first()
    if existing_content:
        raise HTTPException(status_code=403, detail={"code": "device_credential_required"})
    if token:
        raise HTTPException(status_code=403, detail={"code": "invalid_device_credential"})

    issued_token = secrets.token_urlsafe(32)
    try:
        session.execute(
            text(
                """
                INSERT INTO device_credentials (device_id, credential_hash, created_at)
                VALUES (:device, :hash, :created)
                """
            ),
            {
                "device": device_id,
                "hash": sha256(issued_token.encode("utf-8")).hexdigest(),
                "created": datetime.now(UTC),
            },
        )
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail={"code": "device_registration_race"}) from error
    return issued_token


def _require_device_credential(session: SessionDep, device_id: str, token: str | None) -> None:
    credential = session.execute(
        text("SELECT credential_hash FROM device_credentials WHERE device_id=:device"),
        {"device": device_id},
    ).first()
    if not credential:
        raise HTTPException(status_code=403, detail={"code": "device_credential_required"})
    _require_matching_credential(credential.credential_hash, token)


def _require_matching_credential(expected_hash: str, token: str | None) -> None:
    actual_hash = sha256(token.encode("utf-8")).hexdigest() if token else ""
    if not token or not compare_digest(actual_hash, expected_hash):
        raise HTTPException(status_code=403, detail={"code": "invalid_device_credential"})


def _zone_at(session: SessionDep, lat: float, lng: float) -> str | None:
    boundary = geometry()
    rows = session.execute(text("SELECT cluster_id FROM zones")).scalars().all()
    for cluster_id in rows:
        bounds = _bounds(cluster_id)
        if (
            bounds.south <= lat <= bounds.north
            and bounds.west <= lng <= bounds.east
            and contains_in_geometry(boundary, lat, lng)
        ):
            return cluster_id
    return None


def _rate_limit(session: SessionDep, device: str) -> None:
    since = datetime.now(UTC) - timedelta(hours=1)
    count = session.execute(
        text(
            """SELECT (
                SELECT COUNT(*) FROM tree_pins
                WHERE device_id=:device AND created_at>=:since
            ) + (
                SELECT COUNT(*) FROM tree_messages
                WHERE device_id=:device AND created_at>=:since
            )"""
        ),
        {"device": device, "since": since},
    ).scalar_one()
    if count >= DEVICE_LIMIT:
        raise HTTPException(status_code=429, detail={"code": "device_rate_limited"})


def _clean_photo(content: bytes, content_type: str | None) -> bytes:
    expected_formats = {"image/jpeg": "JPEG", "image/png": "PNG"}
    if content_type not in expected_formats:
        raise HTTPException(status_code=415, detail={"code": "invalid_photo_type"})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(content))
        if image.format != expected_formats[content_type]:
            raise ValueError
        if image.width * image.height > MAX_PHOTO_PIXELS:
            raise HTTPException(status_code=413, detail={"code": "photo_dimensions_too_large"})
        image = ImageOps.exif_transpose(image)
        image.load()
        image.thumbnail((1600, 1600))
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_photo"}) from exc


def _require_storage_configured() -> None:
    if (
        not settings.supabase_url
        or not settings.supabase_service_role_key
        or not settings.supabase_storage_bucket
    ):
        raise HTTPException(status_code=503, detail={"code": "photo_storage_unconfigured"})


def _isoformat(value: datetime | str) -> str:
    return value.isoformat() if isinstance(value, datetime) else value


def _upload_photo(pin_id: str, content: bytes) -> str:
    _require_storage_configured()
    _require_private_bucket()
    path = f"{pin_id}.jpg"
    try:
        endpoint = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{settings.supabase_storage_bucket}/{path}"
        )
        response = httpx.post(
            endpoint,
            content=content,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
                "Content-Type": "image/jpeg",
                "x-upsert": "false",
            },
            timeout=15,
        )
        response.raise_for_status()
        return path
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail={"code": "photo_upload_failed"}) from exc


def _require_private_bucket() -> None:
    _require_storage_configured()
    try:
        endpoint = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/"
            f"{settings.supabase_storage_bucket}"
        )
        response = httpx.get(
            endpoint,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        if response.json().get("public") is not False:
            raise HTTPException(status_code=503, detail={"code": "photo_bucket_must_be_private"})
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail={"code": "photo_storage_unavailable"}) from exc


def _signed_photo(path: str) -> str:
    _require_storage_configured()
    _require_private_bucket()
    try:
        endpoint = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/"
            f"{settings.supabase_storage_bucket}/{path}"
        )
        response = httpx.post(
            endpoint,
            json={"expiresIn": 3600},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        url = response.json()["signedURL"]
        return (
            url
            if url.startswith("http")
            else f"{settings.supabase_url.rstrip('/')}/storage/v1{url}"
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail={"code": "photo_url_unavailable"}) from exc


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    a, b = radians(lat2 - lat1), radians(lng2 - lng1)
    value = sin(a / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(b / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))
