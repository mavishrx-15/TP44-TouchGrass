"""SQL access owned by the weather developer. Do not call HTTP endpoints."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.integrations.weather_provider import WeatherReading


def newest_reading(session: Session) -> WeatherReading | None:
    raise NotImplementedError("weather_readings query pending")


def save_reading(session: Session, reading: WeatherReading, created_at: datetime) -> None:
    raise NotImplementedError("weather_readings insert pending")
