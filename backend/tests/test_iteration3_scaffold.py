"""Public contract for route planning: what it accepts and refuses."""

import pytest

from app.integrations import google_routes

START = {"lat": -37.8183, "lng": 144.9671}


@pytest.fixture
def walking_routes(monkeypatch):
    monkeypatch.setattr(
        google_routes,
        "walking_alternatives",
        lambda origin, destination: [
            {
                "duration": "720s",
                "distanceMeters": 900,
                "polyline": {"encodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"},
            }
        ],
    )


@pytest.mark.parametrize("extra", [{"mood": "Stressed"}, {"preferences": {"mood": "Stressed"}}])
def test_planning_rejects_mood(client, extra):
    response = client.post("/api/sprout/route", json={"origin": START, **extra})
    assert response.status_code == 422


def test_planning_is_no_longer_cbd_only(client, walking_routes):
    """Team decision: candidates are every zone citywide, not CBD-only, so a
    Kensington origin (well outside the old Hoddle Grid polygon) now reaches
    a real destination instead of a 422 outside_cbd."""
    response = client.post("/api/sprout/route", json={"origin": {"lat": -37.795, "lng": 144.915}})
    assert response.status_code == 200
    assert response.json()["destination"]["zoneId"] is not None


def test_recommendation_pick_is_accepted_and_keeps_the_selected_zone(client, walking_routes):
    origin = {"lat": -37.795, "lng": 144.915}
    areas = client.post("/api/sprout/areas", json={"origin": origin})
    assert areas.status_code == 200
    selected = areas.json()["areas"][0]["destination"]["zoneId"]
    response = client.post(
        "/api/sprout/route", json={"origin": origin, "destinationZoneId": selected}
    )
    assert response.status_code == 200
    assert response.json()["destination"]["zoneId"] == selected


def test_planning_endpoints_require_access(client):
    client.headers.pop("Authorization")
    for path in ["/api/sprout/route", "/api/sprout/areas"]:
        assert client.post(path, json={}).status_code == 401


def test_openapi_documents_the_planning_response(client):
    assert "PlannedRoute" in client.get("/openapi.json").json()["components"]["schemas"]
