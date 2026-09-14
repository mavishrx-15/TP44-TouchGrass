import time

import pytest

from app.config import settings
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
