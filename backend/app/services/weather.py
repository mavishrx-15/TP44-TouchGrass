"""Owner: weather developer. Cache and band rules belong here."""

from sqlalchemy.orm import Session

from app.errors import feature_pending
from app.schemas.weather import WeatherNow

FRESHNESS_MINUTES = 30
PROVIDER_TIMEOUT_SECONDS = 3


def current_weather(session: Session) -> WeatherNow:
    # TODO: newest reading under 30 minutes; otherwise loader + save; failure -> 503.
    # Band: >=25 warm, >=15 mild, otherwise cool, including fractional temperatures.
    feature_pending("weather.now")
