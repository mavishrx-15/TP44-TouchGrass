"""Adds zones.street_name to a database that already holds data.

load_data.py is a plain INSERT: it fills empty tables. Once the shared database
holds 82,058 trees and 2,388 zones, re-running it is not an option, so this
script brings an existing database up to the current schema instead — add the
column, then write the street names the dataset already carries.

Run enrich_zones.py FIRST. It is what puts "street_name" into the dataset JSON;
this script only copies what is already there and reaches no external API.

Usage:
    python backfill_street_names.py                 # apply
    python backfill_street_names.py --dry-run       # report, change nothing

DATABASE_URL comes from backend/.env, the same place the API reads it.

Safe to re-run. The column is added only if missing, and the writes are plain
UPDATEs keyed on cluster_id — no row is inserted, deleted, or renumbered, and
trees and species are never touched. Zones whose street_name is null in the
dataset are skipped rather than written as null, so a partial enrichment run
cannot wipe names an earlier full run resolved.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.config import Settings  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
DATASET = BACKEND / "dataset" / "touch_grass_map_data.json"


def database_url() -> str:
    """Read DATABASE_URL from backend/.env whatever directory we were run from.

    app.config resolves ".env" against the working directory, which is right for
    the API — it always starts in backend/ — and wrong here, where the sibling
    scripts are run from backend/database/.
    """
    url = Settings(_env_file=BACKEND / ".env").database_url
    if not url:
        raise SystemExit(f"DATABASE_URL is not set in {BACKEND / '.env'}")
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DATASET))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    zones = json.loads(Path(args.dataset).read_text())["zones"]
    named = [
        {"cluster_id": zone["cluster_id"], "street_name": zone["street_name"]}
        for zone in zones
        if zone.get("street_name")
    ]
    print(f"Dataset holds {len(zones):,} zones, {len(named):,} with a street name.")

    if args.dry_run:
        print("Dry run: nothing written.")
        return

    engine = create_engine(database_url())
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS street_name TEXT"))
        connection.execute(
            text("UPDATE zones SET street_name = :street_name WHERE cluster_id = :cluster_id"),
            named,
        )

    with engine.connect() as connection:
        total = connection.execute(text("SELECT COUNT(*) FROM zones")).scalar()
        filled = connection.execute(text("SELECT COUNT(street_name) FROM zones")).scalar()
    print(f"Database now has {filled:,}/{total:,} zones with a street name.")


if __name__ == "__main__":
    main()
