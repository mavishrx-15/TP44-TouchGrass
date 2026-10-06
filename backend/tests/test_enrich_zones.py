"""Street-name cleanup in the offline enrichment script.

database/ is a folder of scripts, not a package, so the module is loaded from
its path rather than imported.
"""

import importlib.util
import json
from pathlib import Path

DATABASE = Path(__file__).resolve().parent.parent / "database"

_spec = importlib.util.spec_from_file_location("enrich_zones", DATABASE / "enrich_zones.py")
enrich_zones = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(enrich_zones)
first_street_name = enrich_zones.first_street_name


def test_two_trails_run_together_keep_the_first():
    """Where two named trails share a path, Nominatim returns both names in one
    string. The card should show one."""
    assert first_street_name("Main Yarra Trail Capital City Trail") == "Main Yarra Trail"
    assert first_street_name("Capital City Trail Main Yarra Trail") == "Capital City Trail"
    assert first_street_name("Capital City Trail Moonee Ponds Creek Trail") == "Capital City Trail"


def test_slash_separated_names_keep_the_first():
    assert first_street_name("Capital City Trail / Main Yarra Trail") == "Capital City Trail"


def test_a_real_multi_word_name_is_left_whole():
    """The reason the rule only looks for a second Trail: cutting after the first
    road suffix would turn this real road into "Federation Square"."""
    name = "Federation Square Eastern Access Road"
    assert first_street_name(name) == name


def test_ordinary_names_and_gaps_pass_through():
    assert first_street_name("Flinders Street") == "Flinders Street"
    assert first_street_name("Capital City Trail") == "Capital City Trail"
    assert first_street_name(None) is None
    assert first_street_name("") == ""


def test_the_committed_cache_holds_no_joined_names():
    """The cache is committed so a re-run costs seconds instead of 45 minutes of
    Nominatim calls — which also means a dirty value would come straight back.
    Every value in it must already be clean."""
    cache = json.loads((DATABASE / "zone_geocode_cache.json").read_text())
    dirty = {zone: name for zone, name in cache.items() if first_street_name(name) != name}
    assert dirty == {}
