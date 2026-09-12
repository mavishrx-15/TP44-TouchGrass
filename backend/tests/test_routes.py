"""Route selection and preference matching.

The endpoint itself talks to Google, so what is asserted here is everything
that happens after the response comes back — the choosing and the scoring,
which is what US3.2 actually changed. All of it is pure functions over
candidates shaped like Google's.
"""

from app.routers.routes import (
    AreaMetrics,
    Corridor,
    Preferences,
    _best,
    _decode_polyline,
    _duration_seconds,
    _match,
    _result,
)


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
    quick = (Corridor(trees=10, park=0), _candidate(600))
    leafy = (Corridor(trees=95, park=0), _candidate(780))
    assert _best([quick, leafy]) is leafy


def test_density_is_per_kilometre_so_a_detour_cannot_win_on_length():
    """Twice the trees over three times the distance is a thinner walk.

    Ranking on the raw count would reward the long way round for being long.
    """
    short = (Corridor(trees=100, park=0), _candidate(600, metres=500))
    detour = (Corridor(trees=200, park=0), _candidate(900, metres=1500))
    assert _best([short, detour]) is short


def test_duration_breaks_a_tie():
    """Two alternatives often pass the same trees — return the shorter walk."""
    longer = (Corridor(trees=40, park=0), _candidate(900))
    shorter = (Corridor(trees=40, park=0), _candidate(660))
    assert _best([longer, shorter]) is shorter


def test_a_single_candidate_is_returned_unchanged():
    """AC6: Google sometimes finds only one route. It is still the chosen one."""
    only = (Corridor(trees=7, park=0), _candidate(540))
    assert _best([only]) is only


# --- normalising the corridor counts ----------------------------------------


def test_park_share_is_the_proportion_of_park_trees():
    assert Corridor(trees=200, park=150).metrics(1.0).parkShare == 75


def test_an_empty_corridor_does_not_divide_by_zero():
    empty = Corridor(trees=0, park=0).metrics(1.0)
    assert empty.parkShare == 0
    assert empty.canopy == 0


def test_canopy_is_capped_at_one_hundred():
    """A corridor far denser than the full mark is 100, not 240."""
    assert Corridor(trees=2000, park=0).metrics(1.0).canopy == 100


# --- matching against what the user asked for -------------------------------


def _metrics(canopy: int, park: int) -> AreaMetrics:
    return AreaMetrics(canopy=canopy, parkShare=park)


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


def test_allergy_is_never_scored_until_the_taxonomy_is_agreed():
    """Absent reads as unknown. A zero would render as "does not match", which
    is a claim about pollen that nothing in the data supports."""
    summary = _match(Preferences(allergy="lower"), _metrics(70, 40), minutes=12)
    assert summary is None


def test_the_sentence_names_what_was_met_and_what_was_not():
    summary = _match(Preferences(canopy=40, shade=90), _metrics(70, 30), minutes=12)
    assert summary.sentence == "Matches your tree canopy, but not your shade & thermal comfort."


def test_the_sentence_says_closest_available_when_nothing_matched():
    summary = _match(Preferences(canopy=90), _metrics(20, 30), minutes=12)
    assert summary.sentence.startswith("The closest available route")


# --- the response shape -----------------------------------------------------


def test_the_candidate_count_is_reported():
    """The panel reads "best match among the N routes Google found"."""
    scored = (Corridor(trees=40, park=0), _candidate(600))
    assert _result("WALK", scored, 2).candidateCount == 2
    assert _result("WALK", scored, 1).candidateCount == 1


def test_transit_makes_no_environmental_claim():
    """AC: no tree, noise or allergy claim about a transit leg.

    metrics and match carry that, not treeCount — trees near the path is a true
    count either way, it is simply not what chose this route.
    """
    transit = _result("TRANSIT", (Corridor(trees=40, park=20), _candidate(600)), 3)
    assert transit.metrics is None
    assert transit.match is None
    assert transit.label == "Personalised transit route"


def test_duration_is_read_from_googles_seconds_string():
    assert _duration_seconds("780s") == 780
    assert _duration_seconds("779.4s") == 779


def test_an_empty_polyline_decodes_to_no_points():
    """A route with no geometry scores zero rather than raising."""
    assert _decode_polyline("") == []
