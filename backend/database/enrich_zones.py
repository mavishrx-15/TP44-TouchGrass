"""Resumable, opt-in street enrichment of the local dataset; never writes a DB.

One request per second maximum, identifiable user agent and persistent cache.
https://operations.osmfoundation.org/policies/nominatim/
"""

import argparse
import json
import time
from pathlib import Path

import httpx

DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "dataset/touch_grass_map_data.json"


def save(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--contact", required=True, help="Contact email for the request User-Agent")
    parser.add_argument("--endpoint", default="https://nominatim.openstreetmap.org/reverse")
    parser.add_argument("--limit", type=int, default=100, help="Max uncached requests per run")
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text())
    cache = json.loads(args.cache.read_text()) if args.cache.exists() else {}
    requests = 0
    with httpx.Client(
        headers={"User-Agent": f"TouchGrass-zone-enrichment/1.0 ({args.contact})"}, timeout=20
    ) as client:
        for zone in data["zones"]:
            if zone.get("street_name"):
                continue
            key = zone["cluster_id"]
            if key not in cache:
                if requests >= args.limit:
                    break
                response = client.get(
                    args.endpoint,
                    params={
                        "lat": zone["center_lat"],
                        "lon": zone["center_lon"],
                        "format": "jsonv2",
                        "zoom": 17,
                    },
                )
                response.raise_for_status()
                address = response.json().get("address", {})
                cache[key] = next(
                    (
                        address.get(k)
                        for k in ("road", "pedestrian", "footway", "path")
                        if address.get(k)
                    ),
                    None,
                )
                save(args.cache, cache)
                requests += 1
                time.sleep(1.1)
            zone["street_name"] = cache[key]
    save(args.dataset, data)
    print(f"Saved street names; {requests} uncached requests. Re-run to resume.")


if __name__ == "__main__":
    main()
