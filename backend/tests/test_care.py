"""Epic 7 acceptance tests: pins, photos, messages, damage reports and approval.

Pinned to the acceptance criteria rather than the implementation: a message is
hidden until approved, a damage report needs approval, and an unapproved
photo is never returned with an approved message.
"""

from app.config import settings

PHOTO = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
ZONE = "-37.795_144.915"
ADMIN = {"X-Care-Admin": "admin-secret"}
DEVICE = "device-0000001"


def _pin(client, **overrides):
    body = {
        "zoneId": ZONE,
        "latitude": -37.7951,
        "longitude": 144.9151,
        "accuracyM": 12.5,
        "photoDataUrl": PHOTO,
        "deviceId": DEVICE,
    }
    body.update(overrides)
    response = client.post("/api/care/pins", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _device_headers(pin: dict) -> dict:
    """The X-Device-Token a real client would store from the pin response and
    send back on later requests from the same device."""
    token = pin.get("deviceToken")
    return {"X-Device-Token": token} if token else {}


def _message(client, pin: dict, **overrides):
    body = {"body": "Thanks for the shade", "deviceId": DEVICE}
    body.update(overrides)
    return client.post(
        f"/api/care/pins/{pin['id']}/messages", json=body, headers=_device_headers(pin)
    )


def _admin_settings(monkeypatch):
    monkeypatch.setattr(settings, "care_admin_token", "admin-secret")


def test_pin_records_live_accuracy_and_photo_state(client):
    pin = _pin(client)
    assert pin["accuracyM"] == 12.5
    assert pin["hasPhoto"] is True
    assert pin["photoStatus"] == "pending"
    assert "photoDataUrl" not in pin


def test_pin_without_photo_is_valid(client):
    pin = _pin(client, photoDataUrl=None)
    assert pin["hasPhoto"] is False


def test_unknown_zone_is_rejected(client):
    response = client.post(
        "/api/care/pins",
        json={
            "zoneId": "nope",
            "latitude": -37.8,
            "longitude": 144.9,
            "accuracyM": 5,
            "deviceId": DEVICE,
        },
    )
    assert response.status_code == 404


def test_photo_must_be_an_allowed_image_type(client):
    response = client.post(
        "/api/care/pins",
        json={
            "latitude": -37.8,
            "longitude": 144.9,
            "accuracyM": 5,
            "photoDataUrl": "data:text/html;base64,PGgxPg==",
            "deviceId": DEVICE,
        },
    )
    assert response.status_code == 422


def test_photo_over_size_limit_is_rejected(client):
    huge = "data:image/png;base64," + "A" * 2_000_001
    response = client.post(
        "/api/care/pins",
        json={
            "latitude": -37.8,
            "longitude": 144.9,
            "accuracyM": 5,
            "photoDataUrl": huge,
            "deviceId": DEVICE,
        },
    )
    assert response.status_code == 422


def test_retaking_a_photo_sends_it_back_to_pending(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    client.post(
        f"/api/care/pins/{pin['id']}/photo/review", json={"status": "approved"}, headers=ADMIN
    )
    retaken = client.put(
        f"/api/care/pins/{pin['id']}/photo",
        json={"photoDataUrl": PHOTO, "deviceId": DEVICE},
        headers=_device_headers(pin),
    ).json()
    assert retaken["photoStatus"] == "pending"


def test_message_starts_pending_and_is_hidden_from_the_area(client):
    pin = _pin(client)
    message = _message(client, pin).json()
    assert message["status"] == "pending"
    assert client.get(f"/api/care/zones/{ZONE}/messages").json() == []


def test_approved_message_is_public_with_its_photo_only_if_photo_approved(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    message = _message(client, pin).json()
    client.post(
        f"/api/care/messages/{message['id']}/review", json={"status": "approved"}, headers=ADMIN
    )

    public = client.get(f"/api/care/zones/{ZONE}/messages").json()
    assert len(public) == 1
    assert public[0]["body"] == "Thanks for the shade"
    assert public[0]["photoDataUrl"] is None  # message approved, photo not yet

    client.post(
        f"/api/care/pins/{pin['id']}/photo/review", json={"status": "approved"}, headers=ADMIN
    )
    public = client.get(f"/api/care/zones/{ZONE}/messages").json()
    assert public[0]["photoDataUrl"] == PHOTO


def test_rejected_message_never_appears(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    message = _message(client, pin, body="spam").json()
    client.post(
        f"/api/care/messages/{message['id']}/review", json={"status": "rejected"}, headers=ADMIN
    )
    assert client.get(f"/api/care/zones/{ZONE}/messages").json() == []


def test_damage_report_is_public_only_after_approval(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    report = _message(
        client, pin, body="Large branch hanging over the path", kind="damage_report"
    ).json()
    assert report["kind"] == "damage_report"
    assert client.get(f"/api/care/zones/{ZONE}/messages").json() == []
    client.post(
        f"/api/care/messages/{report['id']}/review", json={"status": "approved"}, headers=ADMIN
    )
    public = client.get(f"/api/care/zones/{ZONE}/messages").json()
    assert len(public) == 1
    assert public[0]["kind"] == "damage_report"
    assert public[0]["photoDataUrl"] is None
    client.post(
        f"/api/care/pins/{pin['id']}/photo/review", json={"status": "approved"}, headers=ADMIN
    )
    assert client.get(f"/api/care/zones/{ZONE}/messages").json()[0]["photoDataUrl"] == PHOTO


def test_empty_message_is_rejected(client):
    pin = _pin(client)
    response = _message(client, pin, body="   ")
    assert response.status_code == 422


def test_message_over_limit_is_rejected(client):
    pin = _pin(client)
    response = _message(client, pin, body="x" * 501)
    assert response.status_code == 422


def test_review_needs_the_admin_token(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    message = _message(client, pin, body="hello").json()
    no_token = client.post(
        f"/api/care/messages/{message['id']}/review", json={"status": "approved"}
    )
    wrong_token = client.post(
        f"/api/care/messages/{message['id']}/review",
        json={"status": "approved"},
        headers={"X-Care-Admin": "guess"},
    )
    assert no_token.status_code == 403
    assert wrong_token.status_code == 403


def test_nobody_can_approve_when_admin_token_is_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "care_admin_token", "")
    pin = _pin(client)
    message = _message(client, pin, body="hello").json()
    response = client.post(
        f"/api/care/messages/{message['id']}/review",
        json={"status": "approved"},
        headers={"X-Care-Admin": ""},
    )
    assert response.status_code == 403


def test_care_routes_require_the_access_gate(client):
    client.headers.pop("Authorization")
    response = client.post(
        "/api/care/pins", json={"latitude": -37.8, "longitude": 144.9, "accuracyM": 5}
    )
    assert response.status_code == 401
