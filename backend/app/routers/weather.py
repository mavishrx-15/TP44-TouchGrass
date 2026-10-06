from fastapi import APIRouter

from app.db import SessionDep
from app.schemas.weather import WeatherNow
from app.services import weather

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/now", response_model=WeatherNow)
def weather_now(session: SessionDep) -> WeatherNow:
    return weather.current_weather(session)
