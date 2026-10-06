from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Coordinates

ModerationStatus = Literal["pending", "approved", "hidden"]


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["message", "report"] = "message"
    body: str = Field(min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank.")
        return value.strip()


class TreeMessage(BaseModel):
    id: UUID
    pinId: UUID
    kind: Literal["message", "report"]
    body: str
    status: ModerationStatus
    createdAt: datetime


class TreePin(BaseModel):
    id: UUID
    coordinates: Coordinates
    accuracyM: float = Field(ge=0)
    zoneId: str | None
    photoUrl: str | None = None
    status: ModerationStatus
    createdAt: datetime
    messages: list[TreeMessage] = Field(default_factory=list)


class PinsResponse(BaseModel):
    pins: list[TreePin]
