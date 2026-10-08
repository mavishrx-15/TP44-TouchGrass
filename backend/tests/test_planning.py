"""Route planning: choosing a destination, then a route to it.

Google is never called. Zones are built in memory and Google's alternatives
are canned, so every test pins one rule from section 2 of the design doc —
in particular the three bugs it was written to fix: a 20+ min choice getting
a 7 min walk, pollen never changing the pick, and the destination being chosen
by nearest precinct.
"""

import pytest

from app.routers.routes import Corridor
from app.schemas.cbd import CbdZone
from app.schemas.common import Coordinates
from app.schemas.map_data import AreaMetrics, Bounds
from app.schemas.planning import AreasRequest, PlanningRequest, Preferences
from app.services import planning, sprout

START = Coordinates(lat=-37.8183, lng=144.9671)  # Flinders Street Station


def zone(
    zone_id: str,
    lat: float = -37.8150,
    lng: float = 144.9650,
    trees: int = 40,
    density: str = "Medium",
    park: int = 50,
    pollen: int = 0,
) -> CbdZone:
    return CbdZone(
        id=zone_id,
        precinctId="melbourne",
        precinctName="Melbourne",
        center=Coordinates(lat=lat, lng=lng),
        bounds=Bounds(north=lat + 0.0005, south=lat - 0.0005, east=lng + 0.0005, west=lng - 0.0005),
        treeCount=trees,
        density=density,
        dominantGenus=None,
        distanceKm=0,
        nearestStreet=None,
        metrics=AreaMetrics(
            canopy=50,
            parkShare=park,
            lowAllergyShare=round(100 * (trees - pollen) / trees),
            highPollenTrees=pollen,
        ),
        genera=[],
        dataNotes=[],
        label=f"Melbourne · {zone_id}",
    )


def google(minutes: float, metres: int = 900, polyline: str = "") -> dict:
    return {
        "duration": f"{round(minutes * 60)}s",
        "distanceMeters": metres,
        "polyline": {"encodedPolyline": polyline},
        "legs": [
            {
                "steps": [
                    {
                        "navigationInstruction": {"instructions": "Head east on Flinders St"},
                        "startLocation": {
                            "latLng": {"latitude": START.lat, "longitude": START.lng}
                        },
                        "distanceMeters": metres,
                    }
                ]
            }
        ],
    }


@pytest.fixture
def plan(monkeypatch):
    """Run plan_route against given zones, routes and corridors.

    routes maps a zone id to Google's alternatives for it; corridors maps a
    polyline to what _corridor would measure along it.
    """

    def run(zones, routes, corridors, **preferences):
        monkeypatch.setattr(planning.repository, "candidate_zones", lambda session: zones)
        monkeypatch.setattr(
            planning.google_routes,
            "walking_alternatives",
            lambda origin, destination: next(
                alts for z, alts in routes.items() if _at(zones, z) == destination
            ),
        )
        monkeypatch.setattr(planning, "_decode_polyline", lambda value: value)
        monkeypatch.setattr(planning, "_corridor", lambda path, session: corridors[path])
        return planning.plan_route(
            PlanningRequest(origin=START, preferences=Preferences(**preferences)), None
        )

    return run


def _at(zones, zone_id):
    return next(z.center for z in zones if z.id == zone_id)


def corridor(
    pollen: int = 0, canopy: int = 50, park: int = 50, dense: float = 0.5, trees: int = 100
) -> Corridor:
    return Corridor(trees=trees, park=park, high_pollen=pollen, canopy=canopy, dense_share=dense)


# --- the bugs the design doc names ------------------------------------------


def test_twenty_plus_does_not_settle_for_a_seven_minute_walk(plan):
    """The old rule treated 20 as a maximum, so 7 min "fitted" and won on being
    closest. 20+ is a target band, 18-30."""
    zones = [zone("near", lat=-37.8160, lng=144.9671), zone("far", lat=-37.8090, lng=144.9671)]
    result = plan(
        zones,
        {"near": [google(7, polyline="a")], "far": [google(19, polyline="b")]},
        {"a": corridor(), "b": corridor()},
        walkingTime=20,
    )
    assert result.destination.zoneId == "far"
    assert result.message is None


def test_avoiding_pollen_changes_which_route_is_picked(plan):
    """Pollen used to be explained afterwards but never weighed. Here the leafier
    route loses to the one with fewer high-pollen trees."""
    zones = [zone("a")]
    result = plan(
        zones,
        {"a": [google(12, polyline="leafy"), google(12, polyline="clean")]},
        {"leafy": corridor(pollen=40, canopy=90), "clean": corridor(pollen=2, canopy=40)},
        allergy="avoid",
    )
    assert result.encodedPolyline == "clean"


def test_route_pollen_is_judged_by_share_not_by_count(plan):
    """Measured on Flinders Street Station, 20+ min: a route past 279 trees, 68%
    high-pollen, beat one past 412 trees at 52% — on count it had fewer, but the
    route that is mostly low-pollen trees is the better answer to Deep canopy and
    Avoid high pollen together."""
    zones = [zone("a")]
    result = plan(
        zones,
        {"a": [google(25, polyline="bare"), google(24, polyline="leafy")]},
        {
            "bare": corridor(pollen=190, trees=279),
            "leafy": corridor(pollen=214, trees=412),
        },
        allergy="avoid",
    )
    assert result.encodedPolyline == "leafy"
    assert result.matches[0].detail == "Lowest-pollen route"


def test_lowest_pollen_is_claimed_on_the_measure_the_route_was_picked_by(plan):
    """If the pick is by share, the card must not say "lowest" by count."""
    zones = [zone("a")]
    result = plan(
        zones,
        {"a": [google(25, polyline="bare"), google(24, polyline="leafy")]},
        {
            "bare": corridor(pollen=190, trees=279),
            "leafy": corridor(pollen=214, trees=412),
        },
        allergy="avoid",
    )
    assert result.matches[0].matched is True


def test_without_the_pollen_preference_canopy_decides(plan):
    zones = [zone("a")]
    result = plan(
        zones,
        {"a": [google(12, polyline="leafy"), google(12, polyline="clean")]},
        {"leafy": corridor(pollen=40, canopy=90), "clean": corridor(pollen=2, canopy=40)},
    )
    assert result.encodedPolyline == "leafy"


# --- step 2 and 3: ranking areas --------------------------------------------


def test_areas_inside_the_time_band_rank_first():
    """About 280 m and about 1.1 km from Flinders Street Station."""
    near = zone("near", lat=-37.8160, lng=144.9671)
    far = zone("far", lat=-37.8090, lng=144.9671)
    ranked = planning._ranked(START, Preferences(walkingTime=15), [near, far])
    assert [c.zone.id for c in ranked] == ["far", "near"]


def test_with_no_area_in_the_band_the_nearest_to_it_leads():
    """There is always a closest answer, never an empty list."""
    near = zone("near", lat=-37.8160, lng=144.9671)
    nearer = zone("nearer", lat=-37.8175, lng=144.9671)
    ranked = planning._ranked(START, Preferences(walkingTime=20), [nearer, near])
    assert ranked[0].zone.id == "near"


def test_dense_canopy_leaves_out_low_zones():
    low = zone("low", density="Low", trees=5)
    medium = zone("medium", density="Medium", trees=20)
    ranked = planning._ranked(START, Preferences(canopy="dense"), [low, medium])
    assert [c.zone.id for c in ranked] == ["medium"]


def test_dense_canopy_falls_back_rather_than_finding_nothing():
    only_low = [zone("low", density="Low", trees=5)]
    assert planning._ranked(START, Preferences(canopy="dense"), only_low)


def test_dense_canopy_ranks_more_trees_first():
    ranked = planning._ranked(
        START,
        Preferences(canopy="dense"),
        [zone("some", trees=20), zone("most", trees=90)],
    )
    assert ranked[0].zone.id == "most"


def test_avoiding_pollen_ranks_areas_with_a_smaller_pollen_share_first():
    ranked = planning._ranked(
        START,
        Preferences(allergy="avoid"),
        [zone("pollen", pollen=30), zone("clean", pollen=1)],
    )
    assert ranked[0].zone.id == "clean"


def test_pollen_is_ranked_by_share_so_a_big_zone_is_not_penalised_for_size():
    """Counting would pick the 12-tree patch: 3 high-pollen trees beat 9. But
    that is 25% of it against 10% of the big zone — counting rewards being small,
    and with Deep canopy chosen too it walks the user to the sparsest patch."""
    small = zone("small", trees=12, pollen=3)
    big = zone("big", trees=90, pollen=9)
    ranked = planning._ranked(START, Preferences(canopy="dense", allergy="avoid"), [small, big])
    assert ranked[0].zone.id == "big"


def test_with_similar_pollen_shares_deep_canopy_takes_the_bigger_zone():
    """Shares compared in 10-point steps: 20% and 22% are alike, so tree count
    decides."""
    smaller = zone("smaller", trees=20, pollen=4)
    bigger = zone("bigger", trees=50, pollen=11)
    ranked = planning._ranked(
        START, Preferences(canopy="dense", allergy="avoid"), [smaller, bigger]
    )
    assert ranked[0].zone.id == "bigger"


def test_with_no_canopy_preference_the_destination_is_still_tree_dense():
    """The journey ends at "your tree-dense area" (US6.5), so a Low zone is not a
    destination unless the user asked for open sky."""
    low = zone("low", density="Low", trees=7)
    medium = zone("medium", density="Medium", trees=20)
    ranked = planning._ranked(START, Preferences(), [low, medium])
    assert [c.zone.id for c in ranked] == ["medium"]


def test_open_sky_admits_low_zones():
    low = zone("low", density="Low", trees=7)
    medium = zone("medium", density="Medium", trees=20)
    ranked = planning._ranked(START, Preferences(canopy="open"), [low, medium])
    assert {c.zone.id for c in ranked} == {"low", "medium"}


def test_areas_leaves_out_zones_already_visited_today():
    zones = [zone("visited"), zone("new")]
    ranked = planning._ranked(START, Preferences(), zones, excluded={"visited"})
    assert [c.zone.id for c in ranked] == ["new"]


def test_areas_and_route_share_one_ranking(monkeypatch):
    """US8.4: "Find more trees near you" ranks the way "See other options" does."""
    zones = [zone("a", park=20), zone("b", park=85), zone("c", park=50)]
    monkeypatch.setattr(planning.repository, "candidate_zones", lambda session: zones)
    preferences = Preferences(shade="cool")
    areas = planning.recommend_areas(AreasRequest(origin=START, preferences=preferences), None)
    ranked = planning._ranked(START, preferences, zones)
    assert [a.destination.zoneId for a in areas.areas] == [c.zone.id for c in ranked]


def test_shade_and_noise_targets_combine():
    assert planning._park_share_target(Preferences(shade="cool")) == 85
    assert planning._park_share_target(Preferences(noise="lively")) == 20
    assert planning._park_share_target(Preferences(shade="cool", noise="lively")) == 52.5
    assert planning._park_share_target(Preferences()) is None


# --- step 5 and 6: choosing among the real routes ---------------------------


def test_when_nothing_fits_the_band_the_closest_is_returned_and_said(plan):
    zones = [zone("a")]
    result = plan(
        zones,
        {"a": [google(14, polyline="x"), google(25, polyline="y")]},
        {"x": corridor(), "y": corridor()},
        walkingTime=5,
    )
    assert result.encodedPolyline == "x"
    assert result.message == "No route fitted your 5 min walk, so this is the closest."
    assert "walking time" in result.explanation


def test_the_band_is_judged_on_the_minutes_the_card_shows():
    """7.4 min reads "7 min", which fits a 5 min walk (3-7). Judging the raw 7.4
    would pick it as fitting and then report it as too long."""
    assert planning._band_gap(round(7.4), 3, 7) == 0
    assert planning._time_match(5, 7.4, 3, 7).matched is True
    assert planning._band_gap(round(7.6), 3, 7) == 1


# --- wording on the card ----------------------------------------------------


def test_twenty_plus_wording_from_the_design_doc():
    assert planning._time_match(20, 18, 18, 30).detail == "18 min · fits your 20+ min walk"
    shorter = planning._time_match(20, 7, 18, 30)
    assert shorter.detail == "7 min · shorter than your 20+ min walk"
    assert shorter.matched is False


def test_pollen_wording_never_shows_a_count():
    def option(pollen):
        return planning.Option(None, google(10), corridor(pollen=pollen))

    none, lowest, worse = option(0), option(3), option(9)
    assert planning._pollen_match(none, [none, lowest]).detail == sprout.NO_POLLEN
    assert planning._pollen_match(lowest, [lowest, worse]).detail == sprout.LOWEST_POLLEN
    assert planning._pollen_match(lowest, [lowest]).detail == sprout.LOWEST_AVAILABLE


def test_lowest_pollen_is_not_claimed_when_a_cleaner_route_lost_on_time():
    """The chosen route won on fitting the time; a lower-pollen one existed."""
    chosen = planning.Option(None, google(10), corridor(pollen=9))
    cleaner = planning.Option(None, google(40), corridor(pollen=2))
    match = planning._pollen_match(chosen, [chosen, cleaner])
    assert match.matched is False
    assert match.detail == "A lower-pollen route didn't fit your walking time"


def test_chips_are_only_the_preferences_chosen():
    chips = planning._chips(Preferences(canopy="dense", allergy="avoid", walkingTime=20))
    assert chips == ["Deep canopy", "Avoid high pollen", "20+ min"]
    assert planning._chips(Preferences()) == []


def test_steps_come_from_googles_legs(plan):
    zones = [zone("a")]
    result = plan(zones, {"a": [google(12, polyline="x")]}, {"x": corridor()})
    assert result.steps[0].instruction == "Head east on Flinders St"
    assert result.steps[0].start == START


def test_dense_zone_share_is_carried_through(plan):
    zones = [zone("a")]
    result = plan(zones, {"a": [google(12, polyline="x")]}, {"x": corridor(dense=0.36)})
    assert result.denseZoneShare == 0.36


# --- Sprout's explanation ---------------------------------------------------


def test_explanation_names_a_preference_and_a_fact(plan):
    zones = [zone("a", density="High")]
    result = plan(zones, {"a": [google(12, polyline="x")]}, {"x": corridor()}, canopy="dense")
    assert "deep canopy" in result.explanation
    assert "12 min" in result.explanation


def test_explanation_admits_a_missed_preference(plan):
    zones = [zone("a")]
    result = plan(zones, {"a": [google(12, polyline="x")]}, {"x": corridor(park=10)}, shade="cool")
    assert "doesn't quite fit your shade" in result.explanation


def test_explanation_without_preferences_is_not_called_personalised(plan):
    zones = [zone("a")]
    result = plan(zones, {"a": [google(12, polyline="x")]}, {"x": corridor()})
    assert result.explanation.startswith("Here's a walk to")
    assert "your" not in result.explanation


def test_explanation_adds_the_pollen_caveat_when_only_one_route_was_found(plan):
    zones = [zone("a")]
    result = plan(
        zones, {"a": [google(12, polyline="x")]}, {"x": corridor(pollen=5)}, allergy="avoid"
    )
    assert "a few pollen trees are still on the way" in result.explanation.lower()
