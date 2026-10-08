"""The shipped CBD outline, held to the places that decide where it goes.

The boundary is fitted to the Hoddle Grid streets and to these start points,
not to a zone count, so these are what it is tested against. Every other test
in the suite swaps in its own polygon; these check the real default, so a
local CBD_BOUNDARY override cannot make them pass.
"""

import pytest

from app.cbd import contains
from app.config import Settings, settings

SHIPPED = Settings.model_fields["cbd_boundary"].default


@pytest.fixture(autouse=True)
def shipped_boundary(monkeypatch):
    monkeypatch.setattr(settings, "cbd_boundary", SHIPPED)


@pytest.mark.parametrize(
    ("place", "lat", "lng"),
    [
        # US5.5's three quick-pick start points. Outside, "Grow my route"
        # would answer outside_cbd and US5.6 could not pass.
        ("Flinders Street Station", -37.8183, 144.9671),
        ("State Library", -37.8099, 144.9656),
        ("Melbourne Central", -37.8103, 144.9628),
        # A start point in the design doc's own destination check.
        ("Southern Cross", -37.8184, 144.9525),
    ],
)
def test_the_start_points_are_inside(place, lat, lng):
    assert contains(lat, lng), f"{place} should be inside the CBD"


@pytest.mark.parametrize(
    ("place", "lat", "lng"),
    [
        # The design doc names it as just outside the grid: the prototype's
        # sample walk ends here, and under the CBD rule it cannot.
        ("Birrarung Marr", -37.818, 144.974),
        ("Kensington", -37.795, 144.915),
    ],
)
def test_places_beyond_the_grid_are_outside(place, lat, lng):
    assert not contains(lat, lng), f"{place} should be outside the CBD"
