from datetime import datetime, timedelta, timezone
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import text

from app.cbd import polygons, require_inside
from app.config import settings
from app.db import SessionDep
from app.routers.map_data import _bounds

router = APIRouter()
MAX_PHOTO = 5 * 1024 * 1024
DEVICE_LIMIT = 10


@router.post("/pins")
async def create_pin(session: SessionDep, lat: float = Form(ge=-90, le=90), lng: float = Form(ge=-180, le=180), accuracy_m: float = Form(gt=0, alias="accuracyM"),
                     device_id: str = Form(min_length=8, max_length=100, alias="deviceId"), photo: UploadFile | None = File(default=None)) -> dict:
    require_inside(lat, lng)
    _rate_limit(session, device_id)
    zone = _zone_at(session, lat, lng)
    if not zone:
        raise HTTPException(status_code=422, detail={"code": "outside_cbd", "message": "No CBD tree zone contains this location."})
    lat_delta, lng_delta = 25 / 111_000, 25 / (111_000 * max(cos(radians(lat)), .1))
    nearest = session.execute(text("""SELECT com_id, latitude, longitude FROM trees
        WHERE latitude BETWEEN :south AND :north AND longitude BETWEEN :west AND :east"""),
        {"south": lat - lat_delta, "north": lat + lat_delta, "west": lng - lng_delta, "east": lng + lng_delta}).all()
    tree_id = min(((r.com_id, _distance(lat, lng, r.latitude, r.longitude)) for r in nearest), key=lambda x: x[1], default=(None, 999999))
    nearest_tree = tree_id[0] if tree_id[1] <= 25 else None
    pin_id, now, path = str(uuid4()), datetime.now(timezone.utc), None
    if photo:
        content = await photo.read(MAX_PHOTO + 1)
        if len(content) > MAX_PHOTO:
            raise HTTPException(status_code=413, detail={"code": "photo_too_large"})
        safe_jpeg = _clean_photo(content, photo.content_type)
        path = _upload_photo(pin_id, safe_jpeg)
    session.execute(text("""INSERT INTO tree_pins
        (id, lat, lng, accuracy_m, cluster_id, photo_path, nearest_tree_id, device_id, status, created_at)
        VALUES (:id, :lat, :lng, :accuracy, :zone, :photo, :tree, :device, 'pending', :now)"""),
        {"id": pin_id, "lat": lat, "lng": lng, "accuracy": accuracy_m, "zone": zone, "photo": path,
         "tree": nearest_tree, "device": device_id, "now": now})
    session.commit()
    return {"id": pin_id, "lat": lat, "lng": lng, "accuracyM": accuracy_m, "clusterId": zone,
            "photoUrl": _signed_photo(path) if path else None, "status": "pending", "createdAt": now.isoformat()}


@router.post("/pins/{pin_id}/messages")
def create_message(pin_id: str, session: SessionDep, kind: str = Form(), body: str = Form(min_length=1, max_length=1000),
                   device_id: str = Form(min_length=8, max_length=100, alias="deviceId")) -> dict:
    if kind not in ("message", "report"):
        raise HTTPException(status_code=422, detail={"code": "invalid_message_kind"})
    pin = session.execute(text("SELECT device_id FROM tree_pins WHERE id=:id"), {"id": pin_id}).first()
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found.")
    if pin.device_id != device_id:
        raise HTTPException(status_code=403, detail={"code": "pin_owner_required"})
    _rate_limit(session, device_id)
    message_id, now = str(uuid4()), datetime.now(timezone.utc)
    session.execute(text("""INSERT INTO tree_messages (id,pin_id,kind,body,device_id,status,created_at)
        VALUES (:id,:pin,:kind,:body,:device,'pending',:now)"""),
        {"id": message_id, "pin": pin_id, "kind": kind, "body": body.strip(), "device": device_id, "now": now})
    session.commit()
    return {"id": message_id, "pinId": pin_id, "kind": kind, "body": body.strip(), "status": "pending", "createdAt": now.isoformat()}


@router.get("/pins")
def get_pins(session: SessionDep, zoneId: str = Query(min_length=1), x_device_id: str | None = Header(default=None)) -> list[dict]:
    if not session.execute(text("SELECT 1 FROM zones WHERE cluster_id=:id"), {"id": zoneId}).first():
        raise HTTPException(status_code=404, detail="Unknown zone.")
    rows = session.execute(text("""SELECT id, lat, lng, accuracy_m, cluster_id, photo_path, device_id, status, created_at
        FROM tree_pins WHERE cluster_id=:zone AND (status='approved' OR device_id=:device)
        ORDER BY created_at DESC"""), {"zone": zoneId, "device": x_device_id or ""}).all()
    result = []
    for pin in rows:
        messages = session.execute(text("""SELECT id, kind, body, device_id, status, created_at FROM tree_messages
            WHERE pin_id=:pin AND (status='approved' OR device_id=:device) ORDER BY created_at"""),
            {"pin": pin.id, "device": x_device_id or ""}).all()
        result.append({"id": pin.id, "lat": pin.lat, "lng": pin.lng, "accuracyM": pin.accuracy_m,
            "clusterId": pin.cluster_id, "photoUrl": _signed_photo(pin.photo_path) if pin.photo_path else None, "status": pin.status,
            "createdAt": pin.created_at.isoformat(), "messages": [{"id": m.id, "kind": m.kind, "body": m.body,
            "status": m.status, "createdAt": m.created_at.isoformat()} for m in messages]})
    return result


def _zone_at(session: SessionDep, lat: float, lng: float) -> str | None:
    rings = polygons()
    rows = session.execute(text("SELECT cluster_id FROM zones")).scalars().all()
    for cluster_id in rows:
        bounds = _bounds(cluster_id)
        if (bounds.south <= lat <= bounds.north and bounds.west <= lng <= bounds.east
                and any(_in_ring(ring, lat, lng) for ring in rings)):
            return cluster_id
    return None


def _in_ring(ring: list[list[float]], lat: float, lng: float) -> bool:
    inside = False
    for index, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(index + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _rate_limit(session: SessionDep, device: str) -> None:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = session.execute(text("""SELECT (SELECT COUNT(*) FROM tree_pins WHERE device_id=:device AND created_at>=:since)
        + (SELECT COUNT(*) FROM tree_messages WHERE device_id=:device AND created_at>=:since)"""),
        {"device": device, "since": since}).scalar_one()
    if count >= DEVICE_LIMIT:
        raise HTTPException(status_code=429, detail={"code": "device_rate_limited"})


def _clean_photo(content: bytes, content_type: str | None) -> bytes:
    if content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=415, detail={"code": "invalid_photo_type"})
    try:
        image = Image.open(BytesIO(content))
        if image.format not in ("JPEG", "PNG"):
            raise ValueError
        image.load()
        image.thumbnail((1600, 1600))
        if image.mode not in ("RGB", "L"):
            background = Image.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image.convert("RGB"))
            image = background
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_photo"}) from exc


def _upload_photo(pin_id: str, content: bytes) -> str:
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_storage_bucket:
        raise HTTPException(status_code=503, detail={"code": "photo_storage_unconfigured"})
    _require_private_bucket()
    path = f"{pin_id}.jpg"
    try:
        response = httpx.post(f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_storage_bucket}/{path}",
            content=content, headers={"Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key, "Content-Type": "image/jpeg", "x-upsert": "false"}, timeout=15)
        response.raise_for_status()
        return path
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail={"code": "photo_upload_failed"}) from exc


def _require_private_bucket() -> None:
    try:
        response = httpx.get(f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{settings.supabase_storage_bucket}",
            headers={"Authorization": f"Bearer {settings.supabase_service_role_key}",
                     "apikey": settings.supabase_service_role_key}, timeout=10)
        response.raise_for_status()
        if response.json().get("public") is not False:
            raise HTTPException(status_code=503, detail={"code": "photo_bucket_must_be_private"})
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail={"code": "photo_storage_unavailable"}) from exc


def _signed_photo(path: str) -> str:
    try:
        response = httpx.post(f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{settings.supabase_storage_bucket}/{path}",
            json={"expiresIn": 3600}, headers={"Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key}, timeout=10)
        response.raise_for_status()
        url = response.json()["signedURL"]
        return url if url.startswith("http") else f"{settings.supabase_url.rstrip('/')}/storage/v1{url}"
    except (httpx.HTTPError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail={"code": "photo_url_unavailable"}) from exc


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    a, b = radians(lat2 - lat1), radians(lng2 - lng1)
    value = sin(a / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(b / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(value))
