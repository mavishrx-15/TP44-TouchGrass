# pip install psycopg2-binary
#
# Loads touch_grass_map_data.json into the zones/trees/species tables.
# Run schema.sql FIRST to create the tables before running this.

import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DATA_PATH = Path(__file__).resolve().parent.parent / "dataset" / "touch_grass_map_data.json"


def main():
    # Prefer a single DATABASE_URL. If not provided, fall back to classic
    # PG* environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD).
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ.get("PGDATABASE")
        user = os.environ.get("PGUSER")
        password = os.environ.get("PGPASSWORD")
        if not (dbname and user and password):
            raise RuntimeError(
                "DATABASE_URL not set and one or more of PGDATABASE/PGUSER/PGPASSWORD missing"
            )
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        with DATA_PATH.open(encoding="utf-8") as f:
            data = json.load(f)

        zone_rows = [
            (
                z["cluster_id"],
                z["center_lat"],
                z["center_lon"],
                z["tree_count"],
                z["precinct"],
            )
            for z in data["zones"]
        ]
        execute_values(
            cur,
            """INSERT INTO zones
               (cluster_id, center_lat, center_lon, tree_count, precinct)
               VALUES %s""",
            zone_rows,
        )

        tree_rows = [
            (
                t["com_id"],
                t["common_name"],
                t["scientific_name"],
                t["family"],
                t["family_display_category"],
                t["latitude"],
                t["longitude"],
                t["display_category"],
                t["useful_life_expectency"],
                t["year_planted_display"],
                t["polygon_id"],
                t["match_type"],
                t["cluster_id"],
                t["precinct"],
                t["located_in"],
            )
            for t in data["trees"]
        ]
        execute_values(
            cur,
            """INSERT INTO trees (com_id, common_name, scientific_name, family,
               family_display_category, latitude, longitude, display_category,
               useful_life_expectency, year_planted_display, polygon_id, match_type,
               cluster_id, precinct, located_in) VALUES %s""",
            tree_rows,
        )

        species_rows = [
            (
                s["scientific_name"],
                s["common_name"],
                s["family"],
                s["family_display_category"],
                s["display_category"],
                s["total_count"],
                json.dumps(s["zone_counts"]),
            )
            for s in data["species"]
        ]
        execute_values(
            cur,
            """INSERT INTO species (scientific_name, common_name, family,
               family_display_category, display_category, total_count, zone_counts)
               VALUES %s""",
            species_rows,
        )

        conn.commit()
        print(
            f"Loaded {len(zone_rows)} zones, "
            f"{len(tree_rows)} trees, {len(species_rows)} species"
        )
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
