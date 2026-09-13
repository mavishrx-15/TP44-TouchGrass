import time
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.route_scoring import Preferences, allergy_score, park_score
from app.routers import routes
from app.security import _encode_token


def test_access_correct_wrong_unicode_and_config(client, monkeypatch):
    assert client.post("/api/access/verify", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/access/verify", json={"password": "中文"}).status_code == 401
    monkeypatch.setattr(settings, "access_password", "中文")
    result = client.post("/api/access/verify", json={"password": "中文"})
    assert result.status_code == 200
    assert result.json()["expires_in"] == 3600
    monkeypatch.setattr(settings, "access_token_secret", "")
    assert client.post("/api/access/verify", json={"password": "中文"}).status_code == 503


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/precincts",
        "/api/species",
        "/api/zones?precinct=kensington",
        "/api/places/autocomplete?query=park",
        "/api/db-check",
    ],
)
def test_get_endpoints_require_access(client, endpoint):
    client.headers.pop("Authorization")
    assert client.get(endpoint).status_code == 401


@pytest.mark.parametrize("kind", ["missing", "expired", "tampered", "malformed"])
def test_post_endpoints_require_valid_access(client, kind):
    token = _encode_token({"exp": int(time.time()) + 100})
    tokens = {
        "missing": "",
        "expired": _encode_token({"exp": int(time.time()) - 1}),
        "tampered": token + "x",
        "malformed": "garbage",
    }
    client.headers["Authorization"] = f"Bearer {tokens[kind]}"
    for path in ["/api/routes", "/api/ai/chat"]:
        assert client.post(path, json={}).status_code == 401


def test_street_and_profiles_are_passed_through(client):
    zones = client.get("/api/zones?precinct=kensington").json()
    assert zones[0]["nearestStreet"] == "Test Street"
    assert zones[1]["nearestStreet"] is None
    assert sum(row["count"] for row in zones[0]["treeProfile"]) == 3


def encode(points):
    previous = [0, 0]
    result = ""
    for point in points:
        for axis, coordinate in enumerate(point):
            value = round(coordinate * 100000)
            delta = value - previous[axis]
            previous[axis] = value
            delta = ~(delta << 1) if delta < 0 else delta << 1
            while delta >= 32:
                result += chr((32 | (delta & 31)) + 63)
                delta >>= 5
            result += chr(delta + 63)
    return result


@pytest.fixture
def google(monkeypatch):
    calls = []
    first = {
        "duration": "600s",
        "distanceMeters": 800,
        "polyline": {"encodedPolyline": encode([(-37.795, 144.915), (-37.796, 144.916)])},
    }
    second = {
        "duration": "1200s",
        "distanceMeters": 1200,
        "polyline": {"encodedPolyline": encode([(-37.797, 144.917), (-37.798, 144.918)])},
    }

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            200, json={"routes": [first, second]}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(routes.httpx, "post", post)
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key")
    return calls


def body(**kwargs):
    return {
        "origin": {"lat": -37.79, "lng": 144.91},
        "destination": {"lat": -37.80, "lng": 144.93},
        **kwargs,
    }


def preferences(**kwargs):
    return {"canopy": 0, "shade": 0, "noise": 0, "allergy": 0, "walkingMinutes": 30, **kwargs}


def test_single_route_changes_with_canopy_vs_allergy(client, google):
    canopy = client.post("/api/routes", json=body(preferences=preferences(canopy=5))).json()
    allergy = client.post(
        "/api/routes", json=body(preferences=preferences(allergy=5, avoidFamilies=["Myrtaceae"]))
    ).json()
    assert len(canopy) == len(allergy) == 1
    assert canopy[0]["id"] == "recommended"
    # Both corridors contain Myrtaceae in the fixture: no fabricated allergy match.
    assert allergy[0]["scores"]["allergy"] == 0
    assert canopy[0]["treeCount"] >= allergy[0]["treeCount"]
    assert allergy[0]["bestMatch"] is False


def test_park_preference_selects_different_route(client, google):
    canopy = client.post("/api/routes", json=body(preferences=preferences(canopy=5))).json()[0]
    park = client.post("/api/routes", json=body(preferences=preferences(shade=5, noise=5))).json()[
        0
    ]
    assert canopy["durationMinutes"] == 10
    assert park["durationMinutes"] == 20
    assert park["scores"]["shade"] == park["scores"]["noise"] == 1


def test_budget_fallback_and_transit_mode(client, google):
    walk = client.post("/api/routes", json=body(preferences=preferences(walkingMinutes=5))).json()[
        0
    ]
    assert not walk["withinTimeBudget"] and not walk["bestMatch"]
    assert "time budget" in walk["message"]
    transit = client.post("/api/routes", json=body(travelMode="TRANSIT")).json()[0]
    assert google[-1]["travelMode"] == "TRANSIT"
    assert transit["travelMode"] == "TRANSIT"
    assert any("Public transport" in reason for reason in transit["explanation"])


def test_time_budget_takes_priority_over_weighted_score(client, google):
    result = client.post(
        "/api/routes", json=body(preferences=preferences(shade=5, walkingMinutes=15))
    ).json()[0]
    assert result["durationMinutes"] == 10 and result["withinTimeBudget"]


def test_bad_request_validation(client):
    for extra in [
        {"travelMode": "DRIVE"},
        {"preferences": {"canopy": -1}},
        {"preferences": {"allergy": 5}},
        {"origin": {"lat": 91, "lng": 1}},
        {"destination": {"lat": -37.79, "lng": 144.91}},
    ]:
        assert client.post("/api/routes", json=body(**extra)).status_code == 422


def test_no_route_error(client, monkeypatch, google):
    monkeypatch.setattr(
        routes.httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            200, json={"routes": []}, request=httpx.Request("POST", url)
        ),
    )
    assert client.post("/api/routes", json=body()).status_code == 404


def test_scoring_avoids_double_count_and_handles_no_data():
    rows = [
        SimpleNamespace(display_category="Acacia", family="Fabaceae", located_in="Park"),
        SimpleNamespace(display_category="Ulmus", family="Ulmaceae", located_in="Street"),
    ]
    p = Preferences(allergy=5, avoidGenera=["acacia"], avoidFamilies=["FABACEAE"])
    assert allergy_score(rows, p) == 0.5
    assert park_score(rows) == 0.5
    assert park_score([]) == allergy_score([], p) == 0


def test_corridor_checks_between_vertices():
    assert routes._path_distance_m(-37.795, 144.915, [(-37.795, 144.91), (-37.795, 144.92)]) < 1


def test_genus_avoidance_changes_route(client, google):
    result = client.post(
        "/api/routes",
        json=body(preferences=preferences(allergy=5, avoidGenera=["Eucalyptus"])),
    ).json()[0]
    assert result["durationMinutes"] == 20
    assert result["scores"]["allergy"] == 1
