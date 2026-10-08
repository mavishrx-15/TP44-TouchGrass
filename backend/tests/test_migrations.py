import sqlite3
from pathlib import Path

import pytest

from database import migrate

BACKEND = Path(__file__).resolve().parent.parent
SCHEMA = BACKEND / "database" / "schema.sql"
SUPPLEMENTAL_TABLES = (
    "weather_readings",
    "tree_pins",
    "tree_messages",
    "device_credentials",
)


def _core_schema(connection):
    connection.executescript(
        """
        CREATE TABLE zones (cluster_id TEXT PRIMARY KEY);
        CREATE TABLE trees (com_id INTEGER PRIMARY KEY);
        """
    )


def _table_signature(connection, table):
    columns = tuple(row[1:6] for row in connection.execute(f"PRAGMA table_info({table})"))
    indexes = tuple(
        sorted(
            row[1]
            for row in connection.execute(f"PRAGMA index_list({table})")
            if not row[1].startswith("sqlite_autoindex")
        )
    )
    return columns, indexes


def test_incremental_sqlite_migrations_are_idempotent_and_match_schema():
    incremental = sqlite3.connect(":memory:")
    _core_schema(incremental)
    migrate._migrate_sqlite(incremental)
    migrate._migrate_sqlite(incremental)

    schema_based = sqlite3.connect(":memory:")
    schema_based.executescript(SCHEMA.read_text())
    migrate._migrate_sqlite(schema_based)

    for table in SUPPLEMENTAL_TABLES:
        assert _table_signature(incremental, table) == _table_signature(schema_based, table)
    applied = {row[0] for row in schema_based.execute("SELECT name FROM schema_migrations")}
    assert applied == {
        "002_weather_readings.sql",
        "003_tree_pins_messages.sql",
        "004_device_credentials.sql",
    }


def test_partial_existing_migration_fails_with_actionable_error():
    connection = sqlite3.connect(":memory:")
    _core_schema(connection)
    connection.execute("CREATE TABLE weather_readings (id TEXT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="partially applied"):
        migrate._migrate_sqlite(connection)
