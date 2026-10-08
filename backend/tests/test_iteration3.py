from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image, PngImagePlugin

from app import cbd
from app.config import settings
from app.routers.pins import _clean_photo
from app.routers.sprout import Preferences, _unmet, _unverified_preferences
from app.routers.weather import _band


def test_hoddle_polygon_contains_only_configured_area(monkeypatch):
    monkeypatch.setattr(
        settings,
        "cbd_boundary_geojson",
        '{"type":"Polygon","coordinates":[[[144.9,-37.9],[145.0,-37.9],[145.0,-37.8],[144.9,-37.8],[144.9,-37.9]]]}',
    )
    assert cbd.contains(-37.85, 144.95)
    with pytest.raises(HTTPException) as error:
        cbd.require_inside(-37.95, 144.95)
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "outside_cbd"


def test_missing_boundary_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary_geojson", "")
    with pytest.raises(HTTPException) as error:
        cbd.contains(-37.81, 144.96)
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "cbd_boundary_unconfigured"


@pytest.mark.parametrize(
    ("temperature", "expected"), [(25, "warm"), (24.9, "mild"), (15, "mild"), (14.9, "cool")]
)
def test_temperature_bands(temperature, expected):
    assert _band(temperature) == expected


def test_photo_is_reencoded_without_source_metadata():
    info = PngImagePlugin.PngInfo()
    info.add_text("GPS", "private-location")
    image = Image.new("RGB", (12, 8), "green")
    source = BytesIO()
    image.save(source, "PNG", pnginfo=info)
    cleaned = _clean_photo(source.getvalue(), "image/png")
    result = Image.open(BytesIO(cleaned))
    assert result.format == "JPEG"
    assert "GPS" not in result.info
    assert result.size == (12, 8)


def test_preferences_without_data_are_marked_unverified_not_measured_as_unmet(monkeypatch):
    monkeypatch.setattr(settings, "high_pollen_species", "")
    preferences = Preferences(allergy="avoid", noise="quiet")
    missed = _unmet(preferences, "High", None, True)
    unverified = _unverified_preferences(preferences, False, True)
    assert missed == []
    assert {item["preference"] for item in unverified} == {"noise", "allergy"}
