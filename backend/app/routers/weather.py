"""Live CBD temperature for Sprout's shade/thermal-comfort step (Epic 5,
US5.3): "a chip shows 'CBD now · [temperature]°C'... when it could not be
loaded, no temperature chip is shown".

Uses Open-Meteo, which needs no API key - one less secret to provision for a
feature that only ever reads one rounded number.
"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.cbd import center

router = APIRouter()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class CbdWeather(BaseModel):
    temperatureCelsius: float | None
    available: bool


@router.get("/cbd", response_model=CbdWeather)
def cbd_weather() -> CbdWeather:
    """Current temperature at the CBD centroid, or `available: false` if the
    upstream call fails - callers fall back to a neutral question rather than
    treating a missing reading as an error."""
    try:
        response = httpx.get(
            OPEN_METEO_URL,
            params={
                "latitude": center()["lat"],
                "longitude": center()["lng"],
                "current": "temperature_2m",
                "timezone": "Australia/Melbourne",
            },
            timeout=5.0,
        )
        response.raise_for_status()
        temperature = response.json()["current"]["temperature_2m"]
        return CbdWeather(temperatureCelsius=round(float(temperature), 1), available=True)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return CbdWeather(temperatureCelsius=None, available=False)
