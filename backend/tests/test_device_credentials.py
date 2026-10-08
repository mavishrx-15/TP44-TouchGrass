"""Epic 7 hardening: a pin or message can't be posted under a device_id that
isn't yours, and a device can't flood the area with posts.
"""

from app.config import settings

PHOTO = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
ZONE = "-37.795_144.915"
DEVICE = "device-0000001"
OTHER_DEVICE = "device-0000002"


def _pin_body(**overrides):
    body = {
        "zoneId": ZONE,
        "latitude": -37.7951,
        "longitude": 144.9151,
        "accuracyM": 12.5,
        "deviceId": DEVICE,
    }
    body.update(overrides)
    return body


def test_first_post_from_a_device_issues_a_token(client):
    response = client.post("/api/care/pins", json=_pin_body())
    assert response.status_code == 201
    assert response.json()["deviceToken"]


def test_a_second_post_without_the_token_is_rejected(client):
    client.post("/api/care/pins", json=_pin_body())
    response = client.post("/api/care/pins", json=_pin_body(zoneId=None))
    assert response.status_code == 403


def test_a_second_post_with_the_right_token_succeeds_and_issues_no_new_token(client):
    first = client.post("/api/care/pins", json=_pin_body()).json()
    second = client.post(
        "/api/care/pins",
        json=_pin_body(zoneId=None),
        headers={"X-Device-Token": first["deviceToken"]},
    )
    assert second.status_code == 201
    assert second.json()["deviceToken"] is None


def test_a_wrong_token_is_rejected(client):
    client.post("/api/care/pins", json=_pin_body())
    response = client.post(
        "/api/care/pins", json=_pin_body(zoneId=None), headers={"X-Device-Token": "guessed"}
    )
    assert response.status_code == 403


def test_another_device_cannot_message_someone_elses_pin(client):
    pin = client.post("/api/care/pins", json=_pin_body()).json()
    other_pin = client.post("/api/care/pins", json=_pin_body(deviceId=OTHER_DEVICE)).json()
    response = client.post(
        f"/api/care/pins/{pin['id']}/messages",
        json={"body": "not mine to say", "deviceId": OTHER_DEVICE},
        headers={"X-Device-Token": other_pin["deviceToken"]},
    )
    assert response.status_code == 403


def test_another_device_cannot_retake_someone_elses_photo(client):
    pin = client.post("/api/care/pins", json=_pin_body()).json()
    other_pin = client.post("/api/care/pins", json=_pin_body(deviceId=OTHER_DEVICE)).json()
    response = client.put(
        f"/api/care/pins/{pin['id']}/photo",
        json={"photoDataUrl": PHOTO, "deviceId": OTHER_DEVICE},
        headers={"X-Device-Token": other_pin["deviceToken"]},
    )
    assert response.status_code == 403


def test_the_pin_owner_can_message_its_own_pin(client):
    pin = client.post("/api/care/pins", json=_pin_body()).json()
    response = client.post(
        f"/api/care/pins/{pin['id']}/messages",
        json={"body": "my own pin", "deviceId": DEVICE},
        headers={"X-Device-Token": pin["deviceToken"]},
    )
    assert response.status_code == 201


def test_rate_limit_caps_posts_per_device_per_hour(client, monkeypatch):
    monkeypatch.setattr(settings, "posts_per_device_per_hour", 2)
    first = client.post("/api/care/pins", json=_pin_body())
    token = first.json()["deviceToken"]
    client.post("/api/care/pins", json=_pin_body(zoneId=None), headers={"X-Device-Token": token})
    third = client.post(
        "/api/care/pins", json=_pin_body(zoneId=None), headers={"X-Device-Token": token}
    )
    assert third.status_code == 429


def test_rate_limit_counts_pins_and_messages_together(client, monkeypatch):
    monkeypatch.setattr(settings, "posts_per_device_per_hour", 1)
    pin = client.post("/api/care/pins", json=_pin_body()).json()
    response = client.post(
        f"/api/care/pins/{pin['id']}/messages",
        json={"body": "second post this hour", "deviceId": DEVICE},
        headers={"X-Device-Token": pin["deviceToken"]},
    )
    assert response.status_code == 429
