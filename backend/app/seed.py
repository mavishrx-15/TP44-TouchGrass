"""Build a local SQLite database from the dataset JSON in the repo.

    python -m app.seed

Creates backend/touchgrass.db (replacing it if present), then point .env at
it:

    DATABASE_URL=sqlite:///./touchgrass.db

This exists so anyone can run the API and review pull requests without
Supabase credentials. It deliberately does NOT read DATABASE_URL: a seed
script that follows .env would rebuild the shared database the moment
someone runs it with the wrong env file. The shared database is loaded by
database/load_data.py instead.

Uses the same schema.sql as production. SQLite accepts the Postgres type
names (DOUBLE PRECISION, JSONB) as column affinities, so one schema file
serves both.
"""

import json
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATASET = BACKEND / "dataset" / "touch_grass_map_data.json"
SCHEMA = BACKEND / "database" / "schema.sql"
DB = BACKEND / "touchgrass.db"


def main() -> None:
    data = json.loads(DATASET.read_text())

    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA.read_text())

    conn.executemany(
        "INSERT INTO zones VALUES "
        "(:cluster_id, :center_lat, :center_lon, :tree_count, :precinct, :street_name)",
        [{**z, "street_name": z.get("street_name")} for z in data["zones"]],
    )
    conn.executemany(
        """
        INSERT INTO trees VALUES (
            :com_id, :common_name, :scientific_name, :family,
            :family_display_category, :latitude, :longitude, :display_category,
            :useful_life_expectency, :year_planted_display, :polygon_id,
            :match_type, :cluster_id, :precinct, :located_in
        )
        """,
        data["trees"],
    )
    conn.executemany(
        """
        INSERT INTO species VALUES (
            :scientific_name, :common_name, :family, :family_display_category,
            :display_category, :total_count, :zone_counts
        )
        """,
        [{**s, "zone_counts": json.dumps(s["zone_counts"])} for s in data["species"]],
    )

    conn.commit()
    for table in ("zones", "trees", "species"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")
    conn.close()
    print(f"done -> {DB}")


if __name__ == "__main__":
    main()
