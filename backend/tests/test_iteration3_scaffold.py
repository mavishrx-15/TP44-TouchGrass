"""Public contract for route planning: what it accepts and refuses."""

import pytest

START = {"lat": -37.8183, "lng": 144.9671}


@pytest.mark.parametrize("extra", [{"mood": "Stressed"}, {"preferences": {"mood": "Stressed"}}])
def test_planning_rejects_mood(client, extra):
    response = client.post("/api/sprout/route", json={"origin": START, **extra})
    assert response.status_code == 422


def test_planning_rejects_outside_cbd_before_pending_feature(client):
    response = client.post("/api/sprout/route", json={"origin": {"lat": -37.795, "lng": 144.915}})
    assert response.status_code == 422
    assert response.json()["detail"] == "outside_cbd"


def test_planning_endpoints_require_access(client):
    client.headers.pop("Authorization")
    for path in ["/api/sprout/route", "/api/sprout/areas"]:
        assert client.post(path, json={}).status_code == 401


def test_openapi_documents_the_planning_response(client):
    assert "PlannedRoute" in client.get("/openapi.json").json()["components"]["schemas"]
