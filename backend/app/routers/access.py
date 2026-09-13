from hmac import compare_digest

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.security import create_access_token

router = APIRouter()


class AccessVerifyRequest(BaseModel):
    password: str


class AccessVerifyResponse(BaseModel):
    token: str
    expires_in: int


@router.post("/verify", response_model=AccessVerifyResponse)
def verify_access(request: AccessVerifyRequest) -> AccessVerifyResponse:
    if not settings.access_password:
        raise HTTPException(status_code=503, detail="Access password is not configured")
    if not compare_digest(request.password, settings.access_password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return AccessVerifyResponse(
        token=create_access_token(),
        expires_in=settings.access_token_ttl_seconds,
    )
