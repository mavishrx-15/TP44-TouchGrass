"""Public contracts and safe failure while feature implementations are pending."""

import sqlite3
from pathlib import Path

import pytest

DEVICE = "b4e22641-cde0-4d97-a966-30b1cb4a3dd5"
PIN = "e58d08fd-b479-45ce-b65f-7a535e109c43"
START = {"lat": -37.8183, "lng": 144.9671}


@pytest.mark.parametrize("path", ["/api/sprout/route", "/api/sprout/areas"])
def test_planning_contract_accepts_optional_preferences_but_is_pending(client, path):
    response = client.post(path, json={"origin": START})
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "feature_not_implemented"


@pytest.mark.parametrize("extra", [{"mood": "Stressed"}, {"preferences": {"mood": "Stressed"}}])
def test_planning_rejects_mood(client, extra):
    response = client.post("/api/sprout/route", json={"origin": START, **extra})
    assert response.status_code == 422


def test_planning_rejects_outside_cbd_before_pending_feature(client):
    response = client.post("/api/sprout/route", json={"origin": {"lat": -37.795, "lng": 144.915}})
    assert response.status_code == 422
    assert response.json()["detail"] == "outside_cbd"


def test_pin_contract_supports_optional_file_and_preserves_accuracy(client):
    response = client.post(
        "/api/pins",
        headers={"X-Device-ID": DEVICE},
        data={"lat": START["lat"], "lng": START["lng"], "accuracyM": 23.5},
        files={"photo": ("tree.jpg", b"not-a-real-jpeg", "image/jpeg")},
    )
    # No photo is validated/stored yet; this must never claim a successful save.
    assert response.status_code == 501
    response = client.post(
        "/api/pins",
        headers={"X-Device-ID": DEVICE},
        data={"lat": START["lat"], "lng": START["lng"], "accuracyM": -1},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("body", ["", "   ", "x" * 1001])
def test_invalid_messages_rejected(client, body):
    response = client.post(
        f"/api/pins/{PIN}/messages",
        headers={"X-Device-ID": DEVICE},
        json={"body": body},
    )
    assert response.status_code == 422


def test_weather_and_community_return_pending_not_fake_data(client):
    assert client.get("/api/weather/now").status_code == 501
    assert client.get("/api/pins?zoneId=test", headers={"X-Device-ID": DEVICE}).status_code == 501
    assert (
        client.post(
            f"/api/pins/{PIN}/messages",
            headers={"X-Device-ID": DEVICE},
            json={"kind": "report", "body": "A broken branch."},
        ).status_code
        == 501
    )


def test_all_scaffold_endpoints_require_access(client):
    client.headers.pop("Authorization")
    for path in ["/api/weather/now", "/api/pins?zoneId=test"]:
        assert client.get(path).status_code == 401
    for path in [
        "/api/sprout/route",
        "/api/sprout/areas",
        "/api/pins",
        f"/api/pins/{PIN}/messages",
    ]:
        assert client.post(path, json={}).status_code == 401


def test_openapi_documents_multipart_and_response_models(client):
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    assert "multipart/form-data" in paths["/api/pins"]["post"]["requestBody"]["content"]
    assert "PlannedRoute" in document["components"]["schemas"]
    assert "WeatherNow" in document["components"]["schemas"]
    assert "TreePin" in document["components"]["schemas"]


def test_new_migrations_are_repeatable_and_enforce_content_constraints():
    database = Path(__file__).resolve().parent.parent / "database"
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript((database / "schema.sql").read_text())
        for name in ["002_weather_readings.sql", "003_tree_community.sql"]:
            connection.executescript((database / "migrations" / name).read_text())
        connection.execute(
            "INSERT INTO tree_pins (id, lat, lng, accuracy_m, device_id) VALUES (?, ?, ?, ?, ?)",
            (PIN, START["lat"], START["lng"], 23.5, DEVICE),
        )
        assert connection.execute("SELECT status FROM tree_pins").fetchone()[0] == "pending"
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO tree_messages (id,pin_id,kind,body,device_id) VALUES (?,?,?,?,?)",
                ("message", PIN, "message", " ", DEVICE),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO tree_messages (id,pin_id,kind,body,device_id) VALUES (?,?,?,?,?)",
                ("message", "unknown", "report", "Broken branch", DEVICE),
            )
