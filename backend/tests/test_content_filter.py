import pytest
from test_care import ADMIN, ZONE, _admin_settings, _message, _pin

from app.services.content_filter import is_unsafe_text


@pytest.mark.parametrize(
    "body", ["fuck you", "ＦＵＣＫ you", "f\u200buck you", "sh1t", "色情", "kill yourself"]
)
def test_unsafe_text(body):
    assert is_unsafe_text(body)


@pytest.mark.parametrize(
    "body",
    ["Thanks for the shade", "A branch has split", "Beautiful canopy", "This class is lovely"],
)
def test_normal_tree_messages(body):
    assert not is_unsafe_text(body)


def test_unsafe_message_is_rejected_by_api(client):
    pin = _pin(client)
    response = _message(client, pin, body="fuck you")
    assert response.status_code == 422
    assert client.get(f"/api/care/zones/{ZONE}/messages").json() == []


def test_filter_also_applies_to_existing_messages_and_admin_approval(client, monkeypatch):
    _admin_settings(monkeypatch)
    pin = _pin(client)
    message = _message(client, pin).json()
    endpoint = f"/api/care/messages/{message['id']}/review"
    assert client.post(endpoint, json={"status": "approved"}, headers=ADMIN).status_code == 200
    assert len(client.get(f"/api/care/zones/{ZONE}/messages").json()) == 1
    # A later rule update must cover previously approved rows as well.
    monkeypatch.setattr("app.routers.care.is_unsafe_text", lambda body: True)
    assert client.get(f"/api/care/zones/{ZONE}/messages").json() == []
    assert client.post(endpoint, json={"status": "approved"}, headers=ADMIN).status_code == 422
