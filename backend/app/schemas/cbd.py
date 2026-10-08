"""CBD response contracts; preserve existing field names for frontend callers."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.map_data import Bounds, Density, Zone


class Outline(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]]


class CbdZone(Zone):
    label: str


class CbdZones(BaseModel):
    boundary: Outline
    bounds: Bounds
    zoneCount: int
    densityCounts: dict[Density, int]
    zones: list[CbdZone]


class SpeciesFact(BaseModel):
    commonName: str
    count: int


class ZoneFacts(BaseModel):
    zoneId: str
    treeCount: int
    density: Density
    topSpecies: list[SpeciesFact]
