import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException

from app.config import settings


def ensure_access_configured() -> None:
    if not settings.access_password or len(settings.access_token_secret.encode()) < 32:
        raise HTTPException(status_code=503, detail="Access gate is not configured")


def _encode_token(payload: dict[str, int]) -> str:
    ensure_access_configured()
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=")
    signature = hmac.new(
        settings.access_token_secret.encode(),
        encoded_payload,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded_payload.decode()}.{encoded_signature.decode()}"


def _decode_token(token: str) -> dict[str, int] | None:
    try:
        ensure_access_configured()
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            settings.access_token_secret.encode(),
            encoded_payload.encode(),
            hashlib.sha256,
        ).digest()
        actual_signature = base64.urlsafe_b64decode(encoded_signature + "===")
        if not hmac.compare_digest(actual_signature, expected_signature):
            return None

        payload = base64.urlsafe_b64decode(encoded_payload + "===")
        decoded = json.loads(payload)
        if not isinstance(decoded, dict) or int(decoded["exp"]) <= int(time.time()):
            return None
        return {"exp": int(decoded["exp"])}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def create_access_token() -> str:
    expires_at = int(time.time()) + settings.access_token_ttl_seconds
    return _encode_token({"exp": expires_at})


def require_access_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")
    if not _decode_token(authorization.removeprefix("Bearer ").strip()):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
