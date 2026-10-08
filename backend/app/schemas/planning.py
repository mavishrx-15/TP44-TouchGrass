"""Iteration 3 planning contract. Mood is intentionally rejected."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Coordinates
from app.schemas.map_data import Bounds, Density


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canopy: Literal["open", "mixed", "dense"] | None = None
    shade: Literal["sunny", "mixed", "cool"] | None = None
    noise: Literal["quiet", "lively"] | None = None
    allergy: Literal["avoid"] | None = None
    walkingTime: Literal[5, 10, 15, 20] | None = None


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Coordinates
    preferences: Preferences = Field(default_factory=Preferences)


class AreasRequest(PlanningRequest):
    excludedZoneIds: list[str] = Field(default_factory=list, max_length=500)
    limit: int = Field(default=3, ge=1, le=3)


class Destination(BaseModel):
    zoneId: str
    label: str
    center: Coordinates
    bounds: Bounds
    density: Density
    treeCount: int = Field(ge=0)


class AreaOption(BaseModel):
    destination: Destination
    estimatedMinutes: float = Field(ge=0)
    distanceMeters: float = Field(ge=0)


class AreasResponse(BaseModel):
    areas: list[AreaOption]


class RouteStep(BaseModel):
    instruction: str
    streetName: str | None = None
    start: Coordinates
    distanceMeters: float = Field(ge=0)


class PreferenceMatch(BaseModel):
    key: Literal["canopy", "shade", "noise", "allergy", "time"]
    matched: bool
    detail: str


class PlannedRoute(BaseModel):
    origin: Coordinates
    destination: Destination
    durationMinutes: float = Field(ge=0)
    distanceMeters: float = Field(ge=0)
    encodedPolyline: str
    denseZoneShare: float = Field(ge=0, le=1)
    summaryChips: list[str]
    matches: list[PreferenceMatch]
    explanation: str | None = None
    steps: list[RouteStep]
    message: str | None = None
