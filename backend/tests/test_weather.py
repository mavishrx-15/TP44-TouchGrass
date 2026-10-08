"""GET /api/weather/now: bands, rounding, the 503 case and the 30-minute cache."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text

from app.db import get_session
from app.main import app
from app.routers import weather


def _fake_response(temperature: float, observed: str = "2026-01-01T00:00:00+00:00"):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"current": {"temperature_2m": temperature, "time": observed}}

    return FakeResponse()


def test_rounds_before_banding_so_24_6_is_warm_not_mild(client, monkeypatch):
    monkeypatch.setattr(weather.httpx, "get", lambda *a, **k: _fake_response(24.6))
    body = client.get("/api/weather/now").json()
    assert body["temperatureC"] == 25
    assert body["band"] == "warm"


def test_mild_band(client, monkeypatch):
    monkeypatch.setattr(weather.httpx, "get", lambda *a, **k: _fake_response(20.0))
    body = client.get("/api/weather/now").json()
    assert body["temperatureC"] == 20
    assert body["band"] == "mild"


def test_cool_band(client, monkeypatch):
    monkeypatch.setattr(weather.httpx, "get", lambda *a, **k: _fake_response(9.6))
    body = client.get("/api/weather/now").json()
    assert body["temperatureC"] == 10
    assert body["band"] == "cool"


def test_returns_503_when_open_meteo_is_unreachable(client, monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(weather.httpx, "get", fail)
    response = client.get("/api/weather/now")
    assert response.status_code == 503


def test_returns_503_on_a_malformed_upstream_response(client, monkeypatch):
    class EmptyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {}

    monkeypatch.setattr(weather.httpx, "get", lambda *a, **k: EmptyResponse())
    response = client.get("/api/weather/now")
    assert response.status_code == 503


def test_second_call_within_30_minutes_uses_the_cache(client, monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return _fake_response(18.0)

    monkeypatch.setattr(weather.httpx, "get", fake_get)
    first = client.get("/api/weather/now").json()
    second = client.get("/api/weather/now").json()
    assert first == second
    assert len(calls) == 1


def test_a_stale_cached_reading_triggers_a_fresh_call(client, monkeypatch):
    stale = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    with next(app.dependency_overrides[get_session]()) as session:
        session.execute(
            text(
                """
                INSERT INTO weather_readings (id, observed_at, temperature_c, source, created_at)
                VALUES ('old', :observed, 5.0, 'open-meteo', :observed)
                """
            ),
            {"observed": stale},
        )
        session.commit()

    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return _fake_response(18.0)

    monkeypatch.setattr(weather.httpx, "get", fake_get)
    body = client.get("/api/weather/now").json()
    assert body["temperatureC"] == 18
    assert len(calls) == 1
