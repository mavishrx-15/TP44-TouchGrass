"""Shared coordinates: lat/lng objects; GeoJSON uses lng/lat arrays."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
