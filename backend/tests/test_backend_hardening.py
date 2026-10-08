import struct
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import text

from app import cbd
from app.config import settings
from app.route_metrics import dense_zone_share, high_pollen_tree_count
from app.routers import pins, sprout


def _encode_polyline(points):
    encoded = []
    previous_lat = previous_lng = 0
    for lat, lng in points:
        for axis, value in enumerate((round(lat * 100_000), round(lng * 100_000))):
            previous = previous_lat if axis == 0 else previous_lng
            delta = value - previous
            if axis == 0:
                previous_lat = value
            else:
                previous_lng = value
            shifted = ~(delta << 1) if delta < 0 else delta << 1
            while shifted >= 0x20:
                encoded.append(chr((0x20 | (shifted & 0x1F)) + 63))
                shifted >>= 5
            encoded.append(chr(shifted + 63))
    return "".join(encoded)


def _boundary():
    return (
        '{"type":"Polygon","coordinates":[['
        "[144.90,-37.90],[145.00,-37.90],[145.00,-37.70],"
        "[144.90,-37.70],[144.90,-37.90]]]}"
    )


def _jpeg_with_gps_exif():
    image = Image.new("RGB", (40, 20), "blue")
    jpeg = BytesIO()
    image.save(jpeg, "JPEG")

    gps_ifd_offset = 38
    latitude_offset = 92
    longitude_offset = 116
    ifd0 = (
        struct.pack("<H", 2)
        + struct.pack("<HHI4s", 0x0112, 3, 1, struct.pack("<H", 6) + b"\0\0")
        + struct.pack("<HHII", 0x8825, 4, 1, gps_ifd_offset)
        + struct.pack("<I", 0)
    )
    gps_ifd = (
        struct.pack("<H", 4)
        + struct.pack("<HHI4s", 1, 2, 2, b"N\0\0\0")
        + struct.pack("<HHII", 2, 5, 3, latitude_offset)
        + struct.pack("<HHI4s", 3, 2, 2, b"E\0\0\0")
        + struct.pack("<HHII", 4, 5, 3, longitude_offset)
        + struct.pack("<I", 0)
    )
    coordinates = struct.pack("<IIIIII", 37, 1, 48, 1, 0, 1) + struct.pack(
        "<IIIIII", 144, 1, 57, 1, 0, 1
    )
    tiff = b"II" + struct.pack("<HI", 42, 8) + ifd0 + gps_ifd + coordinates
    payload = b"Exif\0\0" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    source = jpeg.getvalue()
    return source[:2] + app1 + source[2:]


def test_dense_zone_share_uses_intersected_route_distance(test_session_factory):
    with test_session_factory() as session:
        share = dense_zone_share([(-37.795, 144.914), (-37.795, 144.917)], session)
    assert share == pytest.approx(1 / 3, abs=0.002)


def test_high_pollen_count_uses_route_corridor_and_unset_is_unknown(
    test_session_factory, monkeypatch
):
    path = [(-37.795, 144.914), (-37.795, 144.917)]
    with test_session_factory() as session:
        assert high_pollen_tree_count(path, ["yellow box"], session) == 3
        assert high_pollen_tree_count(path, [], session) is None


def test_candidate_destinations_use_zone_labels_and_mark_pollen_unverified(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    monkeypatch.setattr(settings, "high_pollen_species", "")
    response = client.post(
        "/api/sprout/areas",
        json={
            "origin": {"lat": -37.795, "lng": 144.915},
            "preferences": {"allergy": "avoid", "noise": "quiet"},
        },
    )
    assert response.status_code == 200, response.text
    area = response.json()[0]
    assert area["label"].startswith("Kensington · Tree zone ")
    assert "CBD ·" not in area["label"]
    assert {item["preference"] for item in area["unverifiedPreferences"]} == {
        "allergy",
        "noise",
    }
    assert "allergy" not in area["unmetPreferences"]


def test_route_explanation_does_not_claim_unmeasured_preferences(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key")
    monkeypatch.setattr(settings, "high_pollen_species", "")
    monkeypatch.setattr(
        sprout,
        "_google_route",
        lambda *_: {
            "duration": "480s",
            "distanceMeters": 1200,
            "polyline": {
                "encodedPolyline": _encode_polyline([(-37.795, 144.914), (-37.795, 144.917)])
            },
            "legs": [],
        },
    )
    response = client.post(
        "/api/sprout/route",
        json={
            "origin": {"lat": -37.795, "lng": 144.915},
            "preferences": {
                "walkingTime": 5,
                "allergy": "avoid",
                "noise": "quiet",
                "shade": "cool",
            },
        },
    )
    assert response.status_code == 200, response.text
    route = response.json()
    assert route["unmetPreferences"] == ["walkingTime"]
    assert {item["preference"] for item in route["unverifiedPreferences"]} == {
        "allergy",
        "noise",
        "shade",
    }
    assert route["denseZoneShare"] == pytest.approx(1 / 3, abs=0.002)
    assert "outside your 5-minute target" in route["explanation"]
    assert "33% of the route distance" in route["explanation"]
    assert "could not be verified" in route["explanation"]
    assert "through tree-dense areas" not in route["explanation"]
    assert "low-pollen route" not in route["explanation"]


def test_route_selection_uses_pollen_trees_along_each_candidate_path(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key")
    monkeypatch.setattr(settings, "high_pollen_species", "Yellow Box")
    zone_with_pollen = "-37.795_144.915"
    zone_without_pollen = "-37.796_144.916"

    def google_route(_origin, destination):
        if destination["lng"] == 144.915:
            points = [(-37.795, 144.914), (-37.795, 144.917)]
        else:
            points = [(-37.8, 144.94), (-37.8, 144.95)]
        return {
            "duration": "300s",
            "distanceMeters": 500,
            "polyline": {"encodedPolyline": _encode_polyline(points)},
            "legs": [],
        }

    monkeypatch.setattr(sprout, "_google_route", google_route)
    response = client.post(
        "/api/sprout/route",
        json={
            "origin": {"lat": -37.8, "lng": 144.94},
            "preferences": {"walkingTime": 5, "allergy": "avoid"},
            "excludeZoneIds": [
                "-37.797_144.917",
                "-37.798_144.918",
                "-37.800_144.960",
            ],
        },
    )
    assert response.status_code == 200, response.text
    route = response.json()
    assert route["destination"]["id"] == zone_without_pollen
    assert route["unmetPreferences"] == []
    assert route["unverifiedPreferences"] == []
    assert "no configured high-pollen trees" in route["explanation"]
    assert zone_with_pollen != route["destination"]["id"]


def test_missing_access_token_configuration_fails_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "access_token", "")
    response = client.get("/api/precincts")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "access_token_unconfigured"


def test_api_requires_token_but_health_remains_public(client):
    assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 200
    response = client.get(
        "/api/zones",
        params={"precinct": "kensington"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_routes_and_places_fail_with_explicit_missing_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", "")
    response = client.get("/api/places/autocomplete", params={"query": "Melbourne"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "cbd_boundary_unconfigured"

    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    monkeypatch.setattr(settings, "google_maps_api_key", "")
    response = client.post(
        "/api/routes",
        json={
            "origin": {"lat": -37.795, "lng": 144.915},
            "destination": {"lat": -37.796, "lng": 144.916},
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "google_maps_unconfigured"


def test_cbd_polygon_holes_are_excluded(monkeypatch):
    monkeypatch.setattr(
        settings,
        "cbd_boundary_geojson",
        '{"type":"Polygon","coordinates":['
        "[[144.9,-37.9],[145.0,-37.9],[145.0,-37.8],[144.9,-37.8],[144.9,-37.9]],"
        "[[144.94,-37.86],[144.96,-37.86],[144.96,-37.84],[144.94,-37.84],[144.94,-37.86]]]}",
    )
    assert cbd.contains(-37.85, 144.93)
    assert not cbd.contains(-37.85, 144.95)


def test_hidden_pins_and_messages_are_never_visible_to_their_author(client, test_session_factory):
    now = datetime.now(UTC).isoformat()
    owner_token = "owner-secret-token"
    with test_session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO device_credentials (device_id, credential_hash, created_at)
                VALUES (:device, :hash, :created)
                """
            ),
            {
                "device": "device-owner-01",
                "hash": sha256(owner_token.encode()).hexdigest(),
                "created": now,
            },
        )
        for pin_id, device, status in (
            ("pending-own", "device-owner-01", "pending"),
            ("hidden-own", "device-owner-01", "hidden"),
            ("approved-public", "device-other-01", "approved"),
        ):
            session.execute(
                text(
                    """
                    INSERT INTO tree_pins
                    (id,lat,lng,accuracy_m,cluster_id,device_id,status,created_at)
                    VALUES (:id,-37.795,144.915,5,'-37.795_144.915',:device,:status,:created)
                    """
                ),
                {"id": pin_id, "device": device, "status": status, "created": now},
            )
        for message_id, pin_id, device, status in (
            ("pending-message", "pending-own", "device-owner-01", "pending"),
            ("hidden-message", "pending-own", "device-owner-01", "hidden"),
            ("approved-message", "pending-own", "device-other-01", "approved"),
        ):
            session.execute(
                text(
                    """
                    INSERT INTO tree_messages
                    (id,pin_id,kind,body,device_id,status,created_at)
                    VALUES (:id,:pin,'message','safe text',:device,:status,:created)
                    """
                ),
                {
                    "id": message_id,
                    "pin": pin_id,
                    "device": device,
                    "status": status,
                    "created": now,
                },
            )
        session.commit()

    response = client.get(
        "/api/pins",
        params={"zoneId": "-37.795_144.915"},
        headers={
            "X-Device-ID": "device-owner-01",
            "X-Device-Token": owner_token,
        },
    )
    assert response.status_code == 200, response.text
    pins_by_id = {pin["id"]: pin for pin in response.json()}
    assert set(pins_by_id) == {"pending-own", "approved-public"}
    assert {message["id"] for message in pins_by_id["pending-own"]["messages"]} == {
        "pending-message",
        "approved-message",
    }
    public_response = client.get("/api/pins", params={"zoneId": "-37.795_144.915"})
    assert public_response.status_code == 200
    assert {pin["id"] for pin in public_response.json()} == {"approved-public"}


def test_nearest_tree_id_is_saved_internally_but_not_returned(
    client, test_session_factory, monkeypatch
):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    response = client.post(
        "/api/pins",
        data={
            "lat": "-37.795",
            "lng": "144.915",
            "accuracyM": "5",
            "deviceId": "device-owner-02",
        },
    )
    assert response.status_code == 200, response.text
    assert "nearestTreeId" not in response.json()
    assert response.json()["deviceToken"]
    with test_session_factory() as session:
        tree_id = session.execute(
            text("SELECT nearest_tree_id FROM tree_pins WHERE id=:id"),
            {"id": response.json()["id"]},
        ).scalar_one()
        stored_hash = session.execute(
            text("SELECT credential_hash FROM device_credentials WHERE device_id=:id"),
            {"id": "device-owner-02"},
        ).scalar_one()
    assert tree_id is not None
    assert stored_hash == sha256(response.json()["deviceToken"].encode()).hexdigest()


def test_damage_report_stays_pending_in_touchgrass(client, test_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    calls = []
    monkeypatch.setattr(pins.httpx, "post", lambda *args, **kwargs: calls.append(args))
    pin = client.post(
        "/api/pins",
        data={
            "lat": "-37.795",
            "lng": "144.915",
            "accuracyM": "5",
            "deviceId": "device-report-01",
        },
    )
    assert pin.status_code == 200, pin.text
    report = client.post(
        f"/api/pins/{pin.json()['id']}/messages",
        data={
            "kind": "report",
            "body": "Tree damage near the base",
            "deviceId": "device-report-01",
        },
        headers={"X-Device-Token": pin.json()["deviceToken"]},
    )
    assert report.status_code == 200, report.text
    assert report.json()["status"] == "pending"
    assert calls == []
    with test_session_factory() as session:
        row = session.execute(
            text("SELECT kind, status FROM tree_messages WHERE id=:id"),
            {"id": report.json()["id"]},
        ).one()
    assert row == ("report", "pending")


def test_known_device_id_cannot_be_claimed_or_used_without_its_credential(client, monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    created = client.post(
        "/api/pins",
        data={
            "lat": "-37.795",
            "lng": "144.915",
            "accuracyM": "5",
            "deviceId": "device-private-01",
        },
    )
    assert created.status_code == 200, created.text

    read_without_token = client.get(
        "/api/pins",
        params={"zoneId": "-37.795_144.915"},
        headers={"X-Device-ID": "device-private-01"},
    )
    assert read_without_token.status_code == 403
    assert read_without_token.json()["detail"]["code"] == "device_credential_required"

    forged_read = client.get(
        "/api/pins",
        params={"zoneId": "-37.795_144.915"},
        headers={
            "X-Device-ID": "device-private-01",
            "X-Device-Token": "wrong-token",
        },
    )
    assert forged_read.status_code == 403
    assert forged_read.json()["detail"]["code"] == "invalid_device_credential"

    forged_message = client.post(
        f"/api/pins/{created.json()['id']}/messages",
        data={
            "kind": "report",
            "body": "Forged report",
            "deviceId": "device-private-01",
        },
        headers={"X-Device-Token": "wrong-token"},
    )
    assert forged_message.status_code == 403
    assert forged_message.json()["detail"]["code"] == "invalid_device_credential"


def test_uncredentialed_legacy_device_id_cannot_be_reclaimed(
    client, test_session_factory, monkeypatch
):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", _boundary())
    with test_session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO tree_pins
                (id,lat,lng,accuracy_m,cluster_id,device_id,status,created_at)
                VALUES ('legacy-pin',-37.795,144.915,5,'-37.795_144.915',
                        'legacy-device-01','pending',:created)
                """
            ),
            {"created": datetime.now(UTC).isoformat()},
        )
        session.commit()
    response = client.post(
        "/api/pins",
        data={
            "lat": "-37.795",
            "lng": "144.915",
            "accuracyM": "5",
            "deviceId": "legacy-device-01",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_credential_required"


def test_rate_limit_still_caps_activity_for_one_device(test_session_factory):
    now = datetime.now(UTC).isoformat()
    with test_session_factory() as session:
        for index in range(pins.DEVICE_LIMIT):
            session.execute(
                text(
                    """
                    INSERT INTO tree_pins
                    (id,lat,lng,accuracy_m,cluster_id,device_id,status,created_at)
                    VALUES (:id,-37.795,144.915,5,'-37.795_144.915',
                            'rate-limited-device','pending',:created)
                    """
                ),
                {"id": f"rate-pin-{index}", "created": now},
            )
        session.commit()
        with pytest.raises(HTTPException) as error:
            pins._rate_limit(session, "rate-limited-device")
    assert error.value.status_code == 429


def test_jpeg_gps_and_exif_metadata_are_removed_on_reencoding():
    source = _jpeg_with_gps_exif()
    original = Image.open(BytesIO(source))
    assert original.getexif().get(274) == 6
    assert 2 in original.getexif().get_ifd(34853)

    cleaned = pins._clean_photo(source, "image/jpeg")
    result = Image.open(BytesIO(cleaned))
    assert result.size == (20, 40)
    assert not result.getexif()


def test_signed_photo_requires_storage_configuration(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    with pytest.raises(HTTPException) as error:
        pins._signed_photo("private.jpg")
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "photo_storage_unconfigured"


def test_public_supabase_bucket_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "test-secret")
    monkeypatch.setattr(settings, "supabase_storage_bucket", "tree-photos")
    monkeypatch.setattr(
        pins.httpx,
        "get",
        lambda *_args, **_kwargs: _StorageResponse({"public": True}),
    )
    with pytest.raises(HTTPException) as error:
        pins._require_private_bucket()
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "photo_bucket_must_be_private"


class _StorageResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload
