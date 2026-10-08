"""Live CBD temperature for Sprout's shade/thermal-comfort step (Epic 5,
US5.3) and the agreed GET /api/weather/now contract:

    {temperatureC, band, observedAt, source}

band is "warm" (>=25C), "mild" (15-24C) or "cool" (<15C), computed here so
every caller agrees on the cutoffs. Open-Meteo needs no API key - one less
secret to provision for a feature that only ever reads one rounded number.

A reading is cached in the weather_readings table for 30 minutes, so a burst
of page loads doesn't hammer Open-Meteo for the same number. The cache lives
in the database, not in memory, so it survives a server restart and is shared
across instances. A live call that fails with no fresh cached reading to fall
back on returns 503; the frontend shows no chip and asks a neutral question
rather than guessing a temperature (US5.3).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.cbd import center
from app.db import SessionDep

router = APIRouter()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_MINUTES = 30
SOURCE = "open-meteo"


class Weather(BaseModel):
    temperatureC: int
    band: str
    observedAt: str
    source: str


def _band(rounded_celsius: int) -> str:
    """Bands the already-rounded whole degree, not the raw reading - a raw
    24.6C rounds to 25C and is warm, not mild."""
    if rounded_celsius >= 25:
        return "warm"
    if rounded_celsius >= 15:
        return "mild"
    return "cool"


def _as_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _fetch_live() -> tuple[float, datetime]:
    """Calls Open-Meteo. Raises 503 on any failure - at this point there is
    no fresher reading left to fall back on."""
    try:
        response = httpx.get(
            OPEN_METEO_URL,
            params={
                "latitude": center()["lat"],
                "longitude": center()["lng"],
                "current": "temperature_2m",
                "timezone": "UTC",
            },
            timeout=3.0,
        )
        response.raise_for_status()
        data = response.json()["current"]
        return float(data["temperature_2m"]), _as_utc(data["time"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Weather is temporarily unavailable.") from exc


def _response(temperature: float, observed: datetime, source: str) -> Weather:
    rounded = round(temperature)
    return Weather(
        temperatureC=rounded,
        band=_band(rounded),
        observedAt=observed.isoformat(),
        source=source,
    )


@router.get("/now", response_model=Weather)
def weather_now(session: SessionDep) -> Weather:
    """Current CBD temperature, banded, cached for 30 minutes."""
    now = datetime.now(UTC)
    row = session.execute(
        text(
            "SELECT observed_at, temperature_c, source, created_at FROM weather_readings "
            "ORDER BY created_at DESC LIMIT 1"
        )
    ).first()
    if row is not None:
        # Cache freshness is judged by when *we* fetched it, not Open-Meteo's
        # own observed_at - that reading can already be a few minutes old by
        # the time it reaches us, which would shrink the cache window.
        fetched = _as_utc(row.created_at)
        if fetched >= now - timedelta(minutes=CACHE_MINUTES):
            return _response(row.temperature_c, _as_utc(row.observed_at), row.source)
    temperature, observed = _fetch_live()
    session.execute(
        text(
            """
            INSERT INTO weather_readings (id, observed_at, temperature_c, source, created_at)
            VALUES (:id, :observed, :temperature, :source, :created)
            """
        ),
        {
            "id": str(uuid4()),
            "observed": observed.isoformat(),
            "temperature": temperature,
            "source": SOURCE,
            "created": now.isoformat(),
        },
    )
    session.commit()
    return _response(temperature, observed, SOURCE)
