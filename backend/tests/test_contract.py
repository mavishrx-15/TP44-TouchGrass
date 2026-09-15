"""Locks the API contract agreed with the frontend and the rules in
"16 Acceptance Criteria".

Each test names the criterion it defends. If one fails, the question is not
"is the test wrong" but "did the criteria change" — and if they did, this file
changes with them and the frontend is told.
"""

from datetime import date

# --- US1.1: search and neighbourhood snapshot -------------------------------


def test_all_precincts_are_searchable_including_those_without_zones(client):
    """Epic 1 DoD: a clear message shows when a precinct has no matching data.

    Richmond owns no zones. Hiding it would leave that criterion untestable,
    so it must still appear in the dropdown.
    """
    names = {p["name"] for p in client.get("/api/precincts").json()}
    assert names == {"Kensington", "Carlton", "Richmond"}


def test_snapshot_counts_through_tree_precinct(client):
    """US1.1 counts trees, zones and species through trees.precinct.

    Tree 5 sits in a Kensington zone but records Richmond, so it counts
    towards Richmond here — and not towards Kensington.
    """
    by_id = {p["id"]: p for p in client.get("/api/precincts").json()}
    assert by_id["kensington"]["treeCount"] == 4
    assert by_id["richmond"]["treeCount"] == 1
    assert by_id["richmond"]["zoneCount"] == 1


def test_species_count_uses_scientific_name_not_display_genus(client):
    """US1.1 counts distinct scientific_name.

    Kensington's four trees are three display genera but four distinct
    scientific names. Counting genera would give every precinct the same 8
    or 9 and tell the reader nothing.
    """
    by_id = {p["id"]: p for p in client.get("/api/precincts").json()}
    assert by_id["kensington"]["speciesCount"] == 4


def test_reference_point_is_the_mean_of_tree_coordinates(client):
    """US1.1: mean latitude and longitude of the precinct's trees."""
    by_id = {p["id"]: p for p in client.get("/api/precincts").json()}
    expected_lat = (-37.795 * 3 + -37.796) / 4
    assert by_id["kensington"]["referencePoint"]["lat"] == expected_lat


# --- US1.2: ranked zones on the home page -----------------------------------


def test_density_tiers_split_on_the_percentile_boundaries(client):
    """US1.2: Low below 10, Medium 10-37, High above 37."""
    tiers = {z["treeCount"]: z["density"] for z in _zones(client, "kensington")}
    assert tiers == {38: "High", 37: "Medium", 10: "Medium", 9: "Low"}


def test_zones_are_ranked_by_tree_count_descending(client):
    """US1.2: highest to lowest tree count."""
    counts = [z["treeCount"] for z in _zones(client, "kensington")]
    assert counts == sorted(counts, reverse=True)


def test_density_filter_returns_only_that_tier(client):
    counts = [z["treeCount"] for z in _zones(client, "kensington", density="Medium")]
    assert sorted(counts) == [10, 37]


def test_distance_is_measured_from_the_precinct_reference_point(client):
    """US1.2: distance from the search location to the zone centre.

    The reference point sits within metres of the first zone's centre, so its
    distance rounds to zero while a further zone does not.
    """
    zones = {z["treeCount"]: z["distanceKm"] for z in _zones(client, "kensington")}
    assert zones[38] == 0.0
    assert zones[9] > 0


def test_zones_list_through_zone_precinct_not_tree_precinct(client):
    """US1.2 lists zones by zones.precinct.

    Tree 5 records Richmond but its zone is Kensington, so the zone stays in
    Kensington's list and Richmond's list is empty. The two definitions are
    implemented as the criteria are written; see the router docstring.
    """
    assert len(_zones(client, "kensington")) == 4
    assert _zones(client, "richmond") == []


def test_limit_caps_the_home_page_list(client):
    """US1.2: at most three cards on the home page."""
    assert len(_zones(client, "kensington", limit=3)) == 3


# --- US1.3: the map ---------------------------------------------------------


def test_zone_bounds_are_the_grid_cell_around_the_cluster_id(client):
    """US1.3: overlays are the real 100m grid squares, not circles."""
    zone = next(z for z in _zones(client, "kensington") if z["treeCount"] == 38)
    assert zone["bounds"] == {
        "north": -37.7945,
        "south": -37.7955,
        "east": 144.9155,
        "west": 144.9145,
    }


def test_tree_detail_carries_what_the_popup_shows(client):
    """US1.3: common name, scientific name and planting age description."""
    tree = _trees(client, zoneId="-37.795_144.915")[0]
    assert tree["commonName"] == "Yellow Box"
    assert tree["scientificName"] == "Eucalyptus melliodora"
    assert tree["plantingAge"] == f"~{date.today().year - 2012} yrs"


def test_planting_age_says_established_when_the_year_is_unknown(client):
    """A third of the real dataset has no year. Those must not get a number."""
    ages = {t["id"]: t["plantingAge"] for t in _trees(client, zoneId="-37.795_144.915")}
    assert ages["3"] == "Established"


def test_genus_filter(client):
    """US1.3: filter the map by species/genus."""
    trees = _trees(client, zoneId="-37.795_144.915", genus="Acacia")
    assert [t["scientificName"] for t in trees] == ["Acacia dealbata"]


def test_located_in_filter(client):
    """US1.3: the map search box accepts a location type (Street/Park)."""
    trees = _trees(client, zoneId="-37.795_144.915", locatedIn="Street")
    assert [t["id"] for t in trees] == ["2"]


def test_species_legend_keeps_other_last(client):
    """US1.3 names the legend order; "Other" is a bucket, not a genus."""
    genera = [g["genus"] for g in client.get("/api/species").json()]
    assert genera[-1] == "Other"


def test_dominant_genus_is_null_when_a_zone_is_all_other(client):
    """270 of 2,388 real zones hold nothing but "Other".

    The frontend type must allow null here or those cards break.
    """
    zone = _zones(client, "carlton")[0]
    assert zone["dominantGenus"] is None


# --- shapes and errors ------------------------------------------------------


def test_response_fields_are_camel_case(client):
    """The frontend reads these names directly from types/discovery.ts.

    Renaming any of them silently blanks the page rather than raising, so the
    whole set is asserted, not spot-checked.
    """
    assert set(client.get("/api/precincts").json()[0]) == {
        "id",
        "name",
        "referencePoint",
        "treeCount",
        "zoneCount",
        "speciesCount",
    }
    assert set(_zones(client, "kensington")[0]) == {
        "id",
        "precinctId",
        "center",
        "bounds",
        "treeCount",
        "density",
        "dominantGenus",
        "nearestStreet",
        "treeProfile",
        "distanceKm",
    }
    assert set(_trees(client, zoneId="-37.795_144.915")[0]) == {
        "id",
        "precinctId",
        "zoneId",
        "coordinates",
        "commonName",
        "scientificName",
        "family",
        "genus",
        "plantingAge",
        "lifeExpectancy",
        "locatedIn",
    }


def test_unknown_precinct_is_404_not_an_empty_list(client):
    """A typo and a precinct with no zones are different answers."""
    assert client.get("/api/zones", params={"precinct": "hogwarts"}).status_code == 404


def test_trees_needs_exactly_one_of_zone_id_or_precinct(client):
    assert client.get("/api/trees").status_code == 422
    assert client.get("/api/trees", params={"zoneId": "x", "precinct": "y"}).status_code == 422


def test_invalid_enum_values_are_rejected(client):
    """Density is capitalised; lowercase is a frontend bug worth surfacing."""
    p = {"precinct": "kensington", "density": "high"}
    assert client.get("/api/zones", params=p).status_code == 422
    assert client.get("/api/trees", params={"zoneId": "x", "locatedIn": "Beach"}).status_code == 422


def test_limit_is_bounded(client):
    p = {"precinct": "kensington", "limit": 9999}
    assert client.get("/api/zones", params=p).status_code == 422


# --- helpers ----------------------------------------------------------------


def _zones(client, precinct, **params):
    response = client.get("/api/zones", params={"precinct": precinct, **params})
    assert response.status_code == 200, response.text
    return response.json()


def _trees(client, **params):
    response = client.get("/api/trees", params=params)
    assert response.status_code == 200, response.text
    return response.json()
