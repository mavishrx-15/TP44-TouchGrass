"""Replace this one loader when the temperature dataset is ready."""

from datetime import datetime
from typing import NamedTuple


class WeatherReading(NamedTuple):
    temperature_c: float
    observed_at: datetime
    source: str


def load_current_reading() -> WeatherReading:
    # TODO: Open-Meteo CBD current temperature, 3s timeout; validate time/value.
    raise NotImplementedError("Weather provider is not implemented.")
