from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WeatherNow(BaseModel):
    temperatureC: float = Field(allow_inf_nan=False)
    band: Literal["warm", "mild", "cool"]
    observedAt: datetime
    source: str
