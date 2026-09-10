"""
Enriches touch_grass_map_data.json zones with a human-readable street name.

For each zone, reverse-geocodes the zone's (center_lat, center_lon) using the
OpenStreetMap Nominatim API to find the nearest road, and writes that back
into the zone's "street_name" field (e.g. "Macaulay Road").

This is a one-off/offline enrichment step: run it whenever the dataset is
regenerated, BEFORE load_data.py. load_data.py itself does not call any
external API - it only loads whatever is already in the JSON.

Usage:
    python enrich_zones.py
    python enrich_zones.py --input ../dataset/touch_grass_map_data.json \
                            --output ../dataset/touch_grass_map_data.json \
                            --cache zone_geocode_cache.json

Notes:
- Nominatim's usage policy requires max 1 request/second and a descriptive
  User-Agent identifying the app/contact - both are set below. Do not remove
  the rate limit or raise concurrency without switching to a paid provider
  (e.g. Google Maps Geocoding API) or self-hosted Nominatim instance.
- Results are cached by cluster_id to disk (zone_geocode_cache.json) so
  re-runs after a partial failure don't re-hit the API for zones already
  resolved, and so re-running after the underlying dataset changes slightly
  doesn't cost a full re-geocode.
- Some zones (e.g. centered in a park or reserve) may not have a nearby
  road; these are left with street_name = null and should be reviewed
  manually.
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "TouchGrass-TP44/1.0 (contact: ginulidd@gmail.com)"
REQUEST_DELAY_SECONDS = 1.1  # stay under Nominatim's 1 req/sec limit


def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_cache(cache_path: Path, cache: dict) -> None:
    with open(cache_path, "w") as f:
        json.dump(cache, f)


def reverse_geocode_street(lat: float, lon: float) -> str | None:
    """Look up the nearest street name for a coordinate via Nominatim.

    Returns the road name (e.g. "Macaulay Road") or None if no road was
    found in the response.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 17,  # street level
        "addressdetails": 1,
    }
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read())

    address = data.get("address", {})
    # Nominatim uses "road" for streets; fall back to other locality fields
    # if a zone centre happens to fall somewhere without a road (e.g. a park).
    return address.get("road") or address.get("pedestrian") or address.get("footway")


def enrich_zones(zones: list[dict], cache: dict, cache_path: Path) -> None:
    total = len(zones)
    for i, zone in enumerate(zones, start=1):
        cluster_id = zone["cluster_id"]

        if cluster_id in cache:
            zone["street_name"] = cache[cluster_id]
            continue

        try:
            street_name = reverse_geocode_street(zone["center_lat"], zone["center_lon"])
        except Exception as exc:
            print(f"[{i}/{total}] {cluster_id}: FAILED ({exc}) - leaving street_name=null")
            street_name = None

        zone["street_name"] = street_name
        cache[cluster_id] = street_name

        print(f"[{i}/{total}] {cluster_id} -> {street_name!r}")

        # Persist the cache as we go so a crash/interrupt doesn't lose progress.
        save_cache(cache_path, cache)

        time.sleep(REQUEST_DELAY_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="../dataset/touch_grass_map_data.json",
        help="Path to the dataset JSON to read zones from.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write the enriched JSON to. Defaults to overwriting --input.",
    )
    parser.add_argument(
        "--cache",
        default="zone_geocode_cache.json",
        help="Path to a JSON cache file mapping cluster_id -> street_name.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path
    cache_path = Path(args.cache)

    with open(input_path) as f:
        data = json.load(f)

    cache = load_cache(cache_path)
    enrich_zones(data["zones"], cache, cache_path)

    with open(output_path, "w") as f:
        json.dump(data, f)

    resolved = sum(1 for z in data["zones"] if z.get("street_name"))
    print(f"\nDone. {resolved}/{len(data['zones'])} zones resolved to a street name.")
    print(f"Wrote enriched dataset to {output_path}")


if __name__ == "__main__":
    main()
