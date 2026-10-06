"""Route selection and preference matching.

The endpoint itself talks to Google, so what is asserted here is everything
that happens after the response comes back — the choosing and the scoring,
which is what US3.2 actually changed. All of it is pure functions over
candidates shaped like Google's.
"""

from app.db import get_session
from app.main import app
from app.routers.routes import (
    AreaMetrics,
    Bounds,
    Corridor,
    Preferences,
    _best,
    _decode_polyline,
    _dense_zone_share,
    _duration_seconds,
    _match,
    _result,
    _samples_along,
    _share_inside,
)


def _corridor(trees: int, park: int = 0, high_pollen: int = 0, canopy: int = 0) -> Corridor:
    return Corridor(trees=trees, park=park, high_pollen=high_pollen, canopy=canopy)


def _candidate(seconds: int, metres: int = 900) -> dict:
    return {
        "duration": f"{seconds}s",
        "distanceMeters": metres,
        "polyline": {"encodedPolyline": ""},
    }


# --- choosing between Google's alternatives ---------------------------------


def test_the_leafiest_candidate_wins_not_the_quickest():
    """Returning a fast route beside a green one was the old behaviour.

    Picking between them is now this function's whole job.
    """
    quick = (_corridor(10, canopy=20), _candidate(600))
    leafy = (_corridor(95, canopy=88), _candidate(780))
    assert _best([quick, leafy]) is leafy


def test_a_longer_route_cannot_win_by_passing_more_trees():
    """Ranking on a percentile keeps length out of the comparison.

    The detour passes twice the trees over three times the distance — more
    trees, no leafier. A raw total would reward it for being long.
    """
    short = (_corridor(100, canopy=70), _candidate(600, metres=500))
    detour = (_corridor(200, canopy=45), _candidate(900, metres=1500))
    assert _best([short, detour]) is short


def test_duration_breaks_a_tie():
    """Two alternatives often cross the same zones — return the shorter walk."""
    longer = (_corridor(40, canopy=60), _candidate(900))
    shorter = (_corridor(40, canopy=60), _candidate(660))
    assert _best([longer, shorter]) is shorter


def test_a_single_candidate_is_returned_unchanged():
    """AC6: Google sometimes finds only one route. It is still the chosen one."""
    only = (_corridor(7, canopy=30), _candidate(540))
    assert _best([only]) is only


# --- turning the corridor counts into scores --------------------------------


def test_park_share_is_the_proportion_of_park_trees():
    assert _corridor(200, park=150).metrics().parkShare == 75


def test_low_allergy_share_is_everything_not_flagged():
    """Two of these ten are high-pollen, so eight in ten are not."""
    metrics = _corridor(10, high_pollen=2).metrics()
    assert metrics.lowAllergyShare == 80
    assert metrics.highPollenTrees == 2


def test_an_empty_corridor_does_not_divide_by_zero():
    empty = _corridor(0).metrics()
    assert empty.parkShare == 0
    assert empty.lowAllergyShare == 0
    assert empty.canopy == 0


# --- matching against what the user asked for -------------------------------


def _metrics(canopy: int, park: int, low_allergy: int | None = None) -> AreaMetrics:
    return AreaMetrics(canopy=canopy, parkShare=park, lowAllergyShare=low_allergy)


def test_only_selected_preferences_are_scored():
    """An unset preference is absent, not a zero.

    Leaving the canopy slider alone must not read as "wants no trees", and it
    must not drag the overall score down either.
    """
    summary = _match(Preferences(canopy=60), _metrics(80, 10), minutes=12)
    assert [item.key for item in summary.matches] == ["canopy"]
    assert summary.score == 80


def test_no_preferences_at_all_produce_no_summary():
    assert _match(Preferences(), _metrics(80, 50), minutes=12) is None
    assert _match(None, _metrics(80, 50), minutes=12) is None


def test_a_near_miss_is_not_reported_as_a_match():
    """Partial shade cannot be labelled a match for "cooler and shaded"."""
    summary = _match(Preferences(shade=80), _metrics(90, 79), minutes=12)
    assert summary.matches[0].matched is False


def test_lively_is_scored_as_the_inverse_of_quiet():
    """Same corridor, opposite preference, opposite reading."""
    quiet = _match(Preferences(noise="quiet"), _metrics(50, 70), minutes=12)
    lively = _match(Preferences(noise="lively"), _metrics(50, 70), minutes=12)
    assert quiet.matches[0].value == 70
    assert lively.matches[0].value == 30
    assert quiet.matches[0].matched and not lively.matches[0].matched


def test_walking_time_allows_the_agreed_tolerance():
    """15 min budget, 2 min tolerance: 17 passes, 18 does not."""
    inside = _match(Preferences(walkingTime=15), _metrics(50, 50), minutes=17)
    outside = _match(Preferences(walkingTime=15), _metrics(50, 50), minutes=18)
    assert inside.matches[0].matched is True
    assert outside.matches[0].matched is False


def test_time_is_a_constraint_and_stays_out_of_the_score():
    """Minutes are not a 0-100 dimension; averaging them in would be nonsense."""
    summary = _match(Preferences(canopy=40, walkingTime=15), _metrics(60, 20), minutes=11)
    assert summary.score == 60


def test_allergy_is_scored_from_the_low_allergy_share():
    summary = _match(Preferences(allergy="lower"), _metrics(70, 40, low_allergy=85), minutes=12)
    assert summary.matches[0].key == "allergy"
    assert summary.matches[0].matched is True


def test_allergy_is_skipped_when_the_share_is_unknown():
    """A transit leg has no corridor metrics, so there is nothing to score.

    Absent reads as unknown; a zero would render as "does not match", which is
    a claim about pollen that nothing in the data supports.
    """
    assert _match(Preferences(allergy="lower"), _metrics(70, 40), minutes=12) is None


def test_the_sentence_names_what_was_met_and_what_was_not():
    summary = _match(Preferences(canopy=40, shade=90), _metrics(70, 30), minutes=12)
    assert summary.sentence == "Matches your tree canopy, but not your shade & thermal comfort."


def test_the_sentence_says_closest_available_when_nothing_matched():
    summary = _match(Preferences(canopy=90), _metrics(20, 30), minutes=12)
    assert summary.sentence.startswith("The closest available route")


# --- the response shape -----------------------------------------------------


def test_the_candidate_count_is_reported():
    """The panel reads "best match among the N routes Google found"."""
    scored = (_corridor(40, park=0), _candidate(600))
    assert _result("WALK", scored, 2).candidateCount == 2
    assert _result("WALK", scored, 1).candidateCount == 1


def test_transit_makes_no_environmental_claim():
    """AC: no tree, noise or allergy claim about a transit leg.

    metrics and match carry that, not treeCount — trees near the path is a true
    count either way, it is simply not what chose this route.
    """
    transit = _result("TRANSIT", (_corridor(40, park=20), _candidate(600)), 3)
    assert transit.metrics is None
    assert transit.match is None
    assert transit.label == "Personalised transit route"


def test_duration_is_read_from_googles_seconds_string():
    assert _duration_seconds("780s") == 780
    assert _duration_seconds("779.4s") == 779


def test_an_empty_polyline_decodes_to_no_points():
    """A route with no geometry scores zero rather than raising."""
    assert _decode_polyline("") == []


# --- denseZoneShare: how much of the walk runs through dense zones ----------


def test_samples_are_spaced_by_distance_not_by_vertex():
    """Two vertices or eleven, the same 100 m of route yields the same samples."""
    two = [(-37.8100, 144.9600), (-37.8091, 144.9600)]
    eleven = [(-37.8100 + i * 0.00009, 144.9600) for i in range(11)]
    assert abs(len(_samples_along(two, 5)) - len(_samples_along(eleven, 5))) <= 1


def test_dense_share_weights_distance_not_vertices():
    """Google bunches vertices on a bend. Counting vertices would call this walk
    almost entirely dense; walking it, most of the distance is outside the zone.
    """
    cell = Bounds(north=-37.8095, south=-37.8105, east=144.9605, west=144.9595)
    bend = [(-37.8100 + i * 0.00001, 144.9600 + (i % 2) * 0.00001) for i in range(10)]
    path = [*bend, (-37.8080, 144.9600)]  # then ~210 m straight north, out of the cell

    vertices_inside = sum(
        cell.south <= lat <= cell.north and cell.west <= lng <= cell.east for lat, lng in path
    )
    assert vertices_inside / len(path) > 0.9
    assert _share_inside(_samples_along(path, 5), [cell]) < 0.35


def test_dense_share_handles_empty_input():
    cell = Bounds(north=-37.8095, south=-37.8105, east=144.9605, west=144.9595)
    assert _samples_along([], 5) == []
    assert _samples_along([(-37.81, 144.96)], 5) == [(-37.81, 144.96)]
    assert _share_inside([], [cell]) == 0.0
    assert _share_inside([(-37.81, 144.96)], []) == 0.0


def _session():
    return next(app.dependency_overrides[get_session]())


def test_a_walk_inside_a_high_zone_is_all_dense(client):
    """Fixture zone -37.795_144.915 holds 38 trees: High."""
    path = [(-37.7952, 144.9148), (-37.7948, 144.9152)]
    assert _dense_zone_share(path, path, _session()) == 1.0


def test_low_zones_do_not_count_as_dense(client):
    """Fixture zone -37.798_144.918 holds 9 trees: Low, below DENSITY_LOW."""
    path = [(-37.7982, 144.9178), (-37.7978, 144.9182)]
    assert _dense_zone_share(path, path, _session()) == 0.0


def test_a_walk_leaving_a_dense_zone_is_partly_dense(client):
    """Starts in the middle of the High cell and walks east past its edge into
    an empty cell: about half the distance is inside."""
    path = [(-37.7950, 144.9150), (-37.7950, 144.9160)]
    assert 0.4 <= _dense_zone_share(path, path, _session()) <= 0.6


def test_transit_carries_no_dense_share():
    """Like metrics: a share of the route walked through trees is not a claim to
    make about a tram ride."""
    scored = (
        Corridor(trees=40, park=0, high_pollen=0, canopy=0, dense_share=0.36),
        _candidate(600),
    )
    assert _result("WALK", scored, 1).denseZoneShare == 0.36
    assert _result("TRANSIT", scored, 1).denseZoneShare is None
