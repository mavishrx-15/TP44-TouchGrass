"""CBD boundaries, complete coverage, true species facts and provider isolation."""

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.cbd import contains, require_inside
from app.config import settings
from app.db import get_session
from app.main import app
from app.routers import routes


@pytest.fixture
def cbd_client(client, monkeypatch):
    # A rotated polygon: its enclosing box contains points outside coverage.
    monkeypatch.setattr(
        settings,
        "cbd_boundary",
        [(144.95, -37.815), (144.965, -37.805), (144.98, -37.815), (144.965, -37.825)],
    )
    with next(app.dependency_overrides[get_session]()) as session:
        for index in range(55):
            session.execute(
                text("INSERT INTO zones VALUES (:id, :lat, :lng, :n, 'Melbourne', :street)"),
                {
                    "id": f"-37.815_144.965{index:02d}",
                    "lat": -37.815,
                    "lng": 144.965,
                    "n": 38 if index == 0 else 37 if index == 1 else 9,
                    "street": "Collins Street" if index == 0 else None,
                },
            )
        # In the bounding rectangle, but outside the actual polygon.
        session.execute(
            text(
                "INSERT INTO zones VALUES "
                "('-37.806_144.951', -37.806, 144.951, 999, 'Outside', NULL)"
            )
        )
        session.commit()
    return client


def test_cbd_map_is_complete_and_uses_polygon_not_precinct(cbd_client):
    response = cbd_client.get("/api/cbd/zones")
    assert response.status_code == 200
    data = response.json()
    assert data["zoneCount"] == 55  # exceeds the old default limit of 50
    assert len(data["zones"]) == 55
    assert data["densityCounts"] == {"High": 1, "Medium": 1, "Low": 53}
    assert data["boundary"]["type"] == "Polygon"
    ring = data["boundary"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert data["zones"][0]["label"] == "Melbourne · Collins Street"
    assert data["zones"][1]["label"] == "Melbourne"
    assert data["zones"][0]["metrics"]["canopy"] == 100
    assert data["zones"][-1]["metrics"]["canopy"] == 0


def test_empty_cbd_map_has_zero_counts(client):
    data = client.get("/api/cbd/zones").json()
    assert data["zones"] == []
    assert data["zoneCount"] == 0
    assert data["densityCounts"] == {"High": 0, "Medium": 0, "Low": 0}


def test_boundary_edges_and_nonfinite_positions(cbd_client):
    assert contains(-37.815, 144.965)
    assert contains(-37.815, 144.95)  # vertex
    assert contains(-37.81, 144.9575)  # edge
    assert not contains(-37.806, 144.951)
    assert not contains(float("nan"), 144.965)
    assert not contains(-37.815, float("inf"))
    with pytest.raises(HTTPException) as error:
        require_inside(-37.806, 144.951)
    assert error.value.status_code == 422
    assert error.value.detail == "outside_cbd"


def test_facts_aggregate_common_names_and_preserve_zone_id(client):
    with next(app.dependency_overrides[get_session]()) as session:
        session.execute(text("UPDATE trees SET common_name='London Plane' WHERE com_id IN (1, 2)"))
        session.execute(text("UPDATE trees SET common_name='Silver Wattle' WHERE com_id=3"))
        session.commit()
    data = client.get("/api/zones/-37.795_144.915/facts").json()
    assert data == {
        "zoneId": "-37.795_144.915",
        "treeCount": 38,
        "density": "High",
        "topSpecies": [
            {"commonName": "London Plane", "count": 2},
            {"commonName": "Silver Wattle", "count": 1},
        ],
    }
    assert client.get("/api/zones/unknown/facts").status_code == 404


def test_facts_handle_float_noise_and_no_trees(cbd_client):
    zone_id = "-37.815_144.96500000000002"
    with next(app.dependency_overrides[get_session]()) as session:
        session.execute(
            text("INSERT INTO zones VALUES (:id, -37.815, 144.965, 0, 'Melbourne', NULL)"),
            {"id": zone_id},
        )
        session.commit()
    data = cbd_client.get(f"/api/zones/{zone_id}/facts").json()
    assert data["zoneId"] == zone_id
    assert data["topSpecies"] == []
    assert data["treeCount"] == 0


def test_facts_return_only_top_two_with_stable_ties(client):
    with next(app.dependency_overrides[get_session]()) as session:
        for tree_id, name in [(1, "C species"), (2, "A species"), (3, "B species")]:
            session.execute(
                text("UPDATE trees SET common_name=:name WHERE com_id=:id"),
                {"id": tree_id, "name": name},
            )
        session.commit()
    species = client.get("/api/zones/-37.795_144.915/facts").json()["topSpecies"]
    assert species == [
        {"commonName": "A species", "count": 1},
        {"commonName": "B species", "count": 1},
    ]


def test_invalid_boundary_fails_explicitly(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary", [])
    assert client.get("/api/cbd/zones").status_code == 503


def test_places_use_restriction_and_filter_actual_positions(cbd_client, monkeypatch):
    calls = []

    def google(method, url, field_mask, json=None):
        calls.append((url, json))
        if url.endswith(":autocomplete"):
            return {
                "suggestions": [
                    {"placePrediction": {"placeId": p, "text": {"text": p}}}
                    for p in ["inside", "outside"]
                ]
            }
        place_id = url.rsplit("/", 1)[-1]
        return {
            "id": place_id,
            "displayName": {"text": place_id},
            "location": {
                "latitude": -37.815 if place_id == "inside" else -37.806,
                "longitude": 144.965 if place_id == "inside" else 144.951,
            },
        }

    monkeypatch.setattr(routes, "_google_request", google)
    assert cbd_client.get("/api/places/autocomplete?query=st").json() == [
        {"id": "inside", "label": "inside"}
    ]
    payload = calls[0][1]
    assert "locationBias" not in payload
    assert "rectangle" in payload["locationRestriction"]
    response = cbd_client.get("/api/places/outside")
    assert response.status_code == 422
    assert response.json()["detail"] == "outside_cbd"


@pytest.mark.parametrize("field", ["origin", "destination"])
def test_outside_route_rejected_before_paid_api(cbd_client, monkeypatch, field):
    def unexpected_call(*args, **kwargs):
        pytest.fail("An outside-CBD request must not call Google.")

    monkeypatch.setattr(routes.httpx, "post", unexpected_call)
    payload = {
        "origin": {"lat": -37.815, "lng": 144.965},
        "destination": {"lat": -37.815, "lng": 144.965},
    }
    payload[field] = {"lat": -37.806, "lng": 144.951}
    response = cbd_client.post("/api/routes", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "outside_cbd"


def test_inside_route_reaches_existing_planner(cbd_client, monkeypatch):
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key")
    calls = []

    class GoogleResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"routes": []}

    def google(*args, **kwargs):
        calls.append(kwargs["json"])
        return GoogleResponse()

    monkeypatch.setattr(routes.httpx, "post", google)
    response = cbd_client.post(
        "/api/routes",
        json={
            "origin": {"lat": -37.815, "lng": 144.965},
            "destination": {"lat": -37.816, "lng": 144.965},
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No route was found."
    assert len(calls) == 1


def test_new_endpoints_require_access(client):
    client.headers.pop("Authorization")
    for url in ["/api/cbd/zones", "/api/zones/-37.795_144.915/facts"]:
        assert client.get(url).status_code == 401
