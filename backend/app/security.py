import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_access_token(authorization: str | None = Header(default=None)) -> str:
    if not settings.access_token:
        raise HTTPException(status_code=503, detail={"code": "access_token_unconfigured"})
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not secrets.compare_digest(supplied, settings.access_token):
        raise HTTPException(status_code=401, detail={"code": "unauthorized"})
    return supplied


def optional_access_token(authorization: str | None = Header(default=None)) -> str | None:
    if not settings.access_token:
        return None
    return require_access_token(authorization)
