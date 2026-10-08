from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db import SessionDep

router = APIRouter()


def _band(value: float) -> str:
    return "warm" if value >= 25 else "mild" if value >= 15 else "cool"


def load_temperature() -> tuple[float, datetime]:
    try:
        response = httpx.get("https://api.open-meteo.com/v1/forecast",
            params={"latitude": -37.8136, "longitude": 144.9631, "current": "temperature_2m", "timezone": "UTC"}, timeout=3)
        response.raise_for_status()
        data = response.json()["current"]
        return float(data["temperature_2m"]), datetime.fromisoformat(data["time"]).replace(tzinfo=timezone.utc)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail={"code": "weather_unavailable"}) from exc


@router.get("/weather/now")
def weather_now(session: SessionDep) -> dict:
    now = datetime.now(timezone.utc)
    row = session.execute(text("SELECT id, observed_at, temperature_c, source FROM weather_readings ORDER BY observed_at DESC LIMIT 1")).first()
    if row:
        observed = row.observed_at
        if isinstance(observed, str):
            observed = datetime.fromisoformat(observed)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        if observed >= now - timedelta(minutes=30):
            return _response(row.temperature_c, observed, row.source)
    temperature, observed = load_temperature()
    if observed < now - timedelta(minutes=30):
        raise HTTPException(status_code=503, detail={"code": "weather_unavailable"})
    session.execute(text("INSERT INTO weather_readings (id, observed_at, temperature_c, source, created_at) VALUES (:id, :at, :temp, :source, :now)"),
                    {"id": str(uuid4()), "at": observed, "temp": temperature, "source": "open-meteo", "now": now})
    session.commit()
    return _response(temperature, observed, "open-meteo")


def _response(value: float, observed: datetime, source: str) -> dict:
    return {"temperatureC": value, "band": _band(value), "observedAt": observed.isoformat(), "source": source}
