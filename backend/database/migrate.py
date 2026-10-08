"""Apply numbered SQL migrations once, for PostgreSQL or local SQLite."""

import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import settings

MIGRATIONS = Path(__file__).parent / "migrations"
BASE_TABLES = {"zones", "trees"}
MIGRATION_TABLES = {
    "002_weather_readings.sql": {"weather_readings"},
    "003_tree_pins_messages.sql": {"tree_pins", "tree_messages"},
    "004_device_credentials.sql": {"device_credentials"},
}
MIGRATION_COLUMNS = {
    "002_weather_readings.sql": {
        "weather_readings": {"id", "observed_at", "temperature_c", "source", "created_at"}
    },
    "003_tree_pins_messages.sql": {
        "tree_pins": {
            "id",
            "lat",
            "lng",
            "accuracy_m",
            "cluster_id",
            "photo_path",
            "nearest_tree_id",
            "device_id",
            "status",
            "created_at",
        },
        "tree_messages": {"id", "pin_id", "kind", "body", "device_id", "status", "created_at"},
    },
    "004_device_credentials.sql": {
        "device_credentials": {"device_id", "credential_hash", "created_at"}
    },
}
MIGRATION_INDEXES = {
    "002_weather_readings.sql": {"idx_weather_readings_observed_at"},
    "003_tree_pins_messages.sql": {
        "idx_tree_pins_zone",
        "idx_tree_pins_device",
        "idx_tree_messages_pin",
        "idx_tree_messages_device",
    },
    "004_device_credentials.sql": set(),
}


def main() -> None:
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite"):
        connection = sqlite3.connect(url.database or ":memory:")
        try:
            _migrate_sqlite(connection)
        finally:
            connection.close()
        return

    import psycopg2

    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    connection = psycopg2.connect(dsn)
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)"
                )
                _require_postgres_base_schema(cursor)
                for path in sorted(MIGRATIONS.glob("*.sql")):
                    cursor.execute("SELECT 1 FROM schema_migrations WHERE name=%s", (path.name,))
                    recorded = cursor.fetchone() is not None
                    existing = _postgres_tables(cursor, MIGRATION_TABLES.get(path.name, set()))
                    complete = _postgres_migration_complete(cursor, path.name)
                    _validate_migration_state(path.name, existing, recorded, complete)
                    expected = MIGRATION_TABLES.get(path.name, set())
                    if recorded or (expected and complete):
                        if not recorded:
                            cursor.execute(
                                "INSERT INTO schema_migrations VALUES (%s)", (path.name,)
                            )
                        continue
                    cursor.execute(path.read_text())
                    existing = _postgres_tables(cursor, expected)
                    if expected and not _postgres_migration_complete(cursor, path.name):
                        raise RuntimeError(
                            f"Migration {path.name} did not create its expected tables."
                        )
                    cursor.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))
    finally:
        connection.close()


def _migrate_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    _require_sqlite_base_schema(connection)
    for path in sorted(MIGRATIONS.glob("*.sql")):
        recorded = (
            connection.execute(
                "SELECT 1 FROM schema_migrations WHERE name=?", (path.name,)
            ).fetchone()
            is not None
        )
        expected = MIGRATION_TABLES.get(path.name, set())
        existing = _sqlite_tables(connection, expected)
        complete = _sqlite_migration_complete(connection, path.name)
        _validate_migration_state(path.name, existing, recorded, complete)
        if recorded or (expected and complete):
            if not recorded:
                connection.execute("INSERT INTO schema_migrations VALUES (?)", (path.name,))
            connection.commit()
            continue
        connection.executescript(path.read_text())
        existing = _sqlite_tables(connection, expected)
        if expected and not _sqlite_migration_complete(connection, path.name):
            raise RuntimeError(f"Migration {path.name} did not create its expected tables.")
        connection.execute("INSERT INTO schema_migrations VALUES (?)", (path.name,))
        connection.commit()


def _validate_migration_state(
    name: str, existing: set[str], recorded: bool, complete: bool
) -> None:
    expected = MIGRATION_TABLES.get(name, set())
    if recorded and not complete:
        raise RuntimeError(f"Migration {name} is recorded as applied but its schema is incomplete.")
    if existing and not complete:
        missing = ", ".join(sorted(expected - existing)) or "expected columns or indexes"
        raise RuntimeError(f"Migration {name} is partially applied; missing {missing}.")


def _sqlite_tables(connection: sqlite3.Connection, names: set[str]) -> set[str]:
    return {
        name
        for name in names
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
    }


def _postgres_tables(cursor, names: set[str]) -> set[str]:
    existing = set()
    for name in names:
        cursor.execute("SELECT to_regclass(%s)", (name,))
        if cursor.fetchone()[0] is not None:
            existing.add(name)
    return existing


def _sqlite_migration_complete(connection: sqlite3.Connection, name: str) -> bool:
    required_columns = MIGRATION_COLUMNS.get(name, {})
    for table, required in required_columns.items():
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if not required.issubset(columns):
            return False
    indexes = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    return MIGRATION_INDEXES.get(name, set()).issubset(indexes)


def _postgres_migration_complete(cursor, name: str) -> bool:
    for table, required in MIGRATION_COLUMNS.get(name, {}).items():
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema=current_schema() AND table_name=%s
            """,
            (table,),
        )
        columns = {row[0] for row in cursor.fetchall()}
        if not required.issubset(columns):
            return False
    cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema()")
    indexes = {row[0] for row in cursor.fetchall()}
    return MIGRATION_INDEXES.get(name, set()).issubset(indexes)


def _require_sqlite_base_schema(connection: sqlite3.Connection) -> None:
    existing = _sqlite_tables(connection, BASE_TABLES)
    if existing != BASE_TABLES:
        raise RuntimeError("Run database/schema.sql before applying migrations.")


def _require_postgres_base_schema(cursor) -> None:
    existing = _postgres_tables(cursor, BASE_TABLES)
    if existing != BASE_TABLES:
        raise RuntimeError("Run database/schema.sql before applying migrations.")


if __name__ == "__main__":
    main()
