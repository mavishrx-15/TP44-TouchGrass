"""Route selection.

The endpoint itself talks to Google, so what is asserted here is the choosing
that happens after the response comes back — the part US3.2 actually changed.
Everything below is a pure function over candidates shaped like Google's.
"""

from app.routers.routes import _best, _decode_polyline, _duration_seconds, _result


def _candidate(seconds: int) -> dict:
    return {"duration": f"{seconds}s", "distanceMeters": 900, "polyline": {"encodedPolyline": ""}}


def test_the_highest_scoring_candidate_wins():
    """The route that passes the most trees, not the quickest one.

    Returning the fastest route and the green one side by side was the old
    behaviour; picking between them is now this function's whole job.
    """
    quick = (10, _candidate(600))
    leafy = (95, _candidate(780))
    assert _best([quick, leafy]) is leafy


def test_duration_breaks_a_tie():
    """Two alternatives often pass the same trees — hand back the shorter walk."""
    longer = (40, _candidate(900))
    shorter = (40, _candidate(660))
    assert _best([longer, shorter]) is shorter


def test_a_single_candidate_is_returned_unchanged():
    """AC6: Google sometimes finds only one route.

    It still comes back as the chosen route. Nothing in the response says how
    many candidates there were, so this cannot read as a comparison that did
    not happen.
    """
    only = (7, _candidate(540))
    assert _best([only]) is only


def test_duration_is_read_from_googles_seconds_string():
    assert _duration_seconds("780s") == 780
    assert _duration_seconds("779.4s") == 779


def test_an_empty_polyline_decodes_to_no_points():
    """A route with no geometry scores zero rather than raising."""
    assert _decode_polyline("") == []


def test_the_candidate_count_is_reported():
    """The panel reads "best match among the N routes Google found".

    N is the number of alternatives Google returned, not the number that were
    scored or shown, so it comes straight from the response length.
    """
    assert _result("WALK", (40, _candidate(600)), 2).candidateCount == 2
    assert _result("WALK", (40, _candidate(600)), 1).candidateCount == 1


def test_transit_makes_no_environmental_claim():
    """AC: no tree, noise or allergy claim about a transit leg.

    metrics and match carry that, not treeCount — trees near the path is a true
    count either way, it is simply not what chose this route.
    """
    transit = _result("TRANSIT", (40, _candidate(600)), 3)
    assert transit.metrics is None
    assert transit.match is None
    assert transit.label == "Personalised transit route"
