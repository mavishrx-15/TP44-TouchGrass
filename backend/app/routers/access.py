from hmac import compare_digest

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.security import create_access_token, ensure_access_configured

router = APIRouter()


class AccessVerifyRequest(BaseModel):
    password: str = Field(max_length=1024)


class AccessVerifyResponse(BaseModel):
    token: str
    expires_in: int


@router.post("/verify", response_model=AccessVerifyResponse)
def verify_access(request: AccessVerifyRequest) -> AccessVerifyResponse:
    ensure_access_configured()
    if not compare_digest(request.password.encode(), settings.access_password.encode()):
        raise HTTPException(status_code=401, detail="Incorrect password")

    return AccessVerifyResponse(
        token=create_access_token(),
        expires_in=settings.access_token_ttl_seconds,
    )
