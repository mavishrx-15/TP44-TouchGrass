"""Test fixtures.

Tests run against a temporary SQLite database built from database/schema.sql,
never against Supabase: CI has no credentials, and a test suite that writes to
the shared database would be a liability even if it did.

The rows are hand-written rather than sampled from the real dataset so that
each acceptance-criteria boundary is hit exactly — a zone of 38 trees and one
of 37, a zone holding nothing but "Other", a precinct with trees but no zones.
Real-data figures are asserted in the assertions of test_contract.py where
they matter, not carried around as fixtures.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_session
from app.main import app

SCHEMA = Path(__file__).resolve().parent.parent / "database" / "schema.sql"

# cluster_id is the rounded centre of a 0.001-degree cell, so these ids also
# fix where each zone's square lies.
# street_name is nullable: enrich_zones.py leaves it empty for a zone centred
# in a park or reserve, with no road near enough to reverse-geocode. The last
# row is that case, so the API contract is exercised both ways.
ZONES = [
    # cluster_id,          lat,      lon,       tree_count, precinct, street_name
    ("-37.795_144.915", -37.795, 144.915, 38, "Kensington", "Macaulay Road"),  # High: boundary
    ("-37.796_144.916", -37.796, 144.916, 37, "Kensington", "Bellair Street"),  # Medium: boundary
    ("-37.797_144.917", -37.797, 144.917, 10, "Kensington", "Rankins Road"),  # Medium: boundary
    ("-37.798_144.918", -37.798, 144.918, 9, "Kensington", "Altona Street"),  # Low: boundary
    ("-37.800_144.960", -37.800, 144.960, 50, "Carlton", None),  # all trees "Other"
]


def _tree(com_id, zone, precinct, genus, sci, located_in, year, family="Myrtaceae"):
    lat, lon = float(zone.split("_")[0]), float(zone.split("_")[1])
    return (
        com_id,
        "Yellow Box",
        sci,
        family,
        # family_display_category files anything outside the nine display
        # genera under "Other" — including the two families the high-pollen
        # proxy names, which is why that rule reads the raw family column.
        "Other" if family != "Myrtaceae" else "Myrtaceae",
        lat,
        lon,
        genus,
        "> 41 years",
        year,
        None,
        "exact",
        zone,
        precinct,
        located_in,
    )


TREES = [
    _tree(
        1, "-37.795_144.915", "Kensington", "Eucalyptus", "Eucalyptus melliodora", "Park", "2012"
    ),
    _tree(2, "-37.795_144.915", "Kensington", "Eucalyptus", "Eucalyptus regnans", "Street", "2020"),
    _tree(3, "-37.795_144.915", "Kensington", "Acacia", "Acacia dealbata", "Park", "Established"),
    _tree(4, "-37.796_144.916", "Kensington", "Other", "Ficus obliqua", "Street", "2015"),
    # trees.precinct disagrees with its zone's precinct — the 1,586-tree case.
    _tree(5, "-37.797_144.917", "Richmond", "Quercus", "Quercus robur", "Park", "2000"),
    # A zone holding nothing but "Other" gets no dominantGenus.
    _tree(6, "-37.800_144.960", "Carlton", "Other", "Ficus macrophylla", "Park", "1998"),
    _tree(7, "-37.800_144.960", "Carlton", "Other", "Ficus obliqua", "Street", "2005"),
    # High-pollen by family, not by genus: display_category is "Other", so only
    # the raw family column can see this one.
    _tree(
        8,
        "-37.800_144.960",
        "Carlton",
        "Other",
        "Cupressus macrocarpa",
        "Street",
        "1990",
        family="Cupressaceae",
    ),
]


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db = tmp_path / "test.db"
    raw = sqlite3.connect(db)
    raw.executescript(SCHEMA.read_text())
    raw.executemany("INSERT INTO zones VALUES (?, ?, ?, ?, ?, ?)", ZONES)
    raw.executemany("INSERT INTO trees VALUES (" + ", ".join(["?"] * 15) + ")", TREES)
    raw.commit()
    raw.close()

    engine = create_engine(f"sqlite:///{db}")
    TestSession = sessionmaker(bind=engine)

    def override():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
