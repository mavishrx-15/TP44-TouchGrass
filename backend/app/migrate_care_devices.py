"""Apply the additive Epic 7 device migrations without replacing existing records.

Run from backend: python -m app.migrate_care_devices
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def migrate(connection: Connection) -> list[str]:
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    if not all(table in tables for table in ("tree_pins", "tree_messages")):
        raise RuntimeError("Apply 002_tree_care.sql before the device migrations.")
    changes: list[str] = []
    if connection.dialect.name == "postgresql":
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    if "device_credentials" not in tables:
        connection.execute(
            text(
                "CREATE TABLE device_credentials (device_id TEXT PRIMARY KEY, "
                "credential_hash TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
        )
        changes.append("Created device_credentials")
    for table in ("tree_pins", "tree_messages"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "device_id" not in columns:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN device_id TEXT"))
            changes.append(f"Added {table}.device_id")
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_device "
                f"ON {table}(device_id, created_at)"
            )
        )
    return changes


if __name__ == "__main__":
    from app.db import engine

    with engine.begin() as connection:
        changes = migrate(connection)
    print("\n".join(changes) if changes else "Care device schema is already up to date.")
