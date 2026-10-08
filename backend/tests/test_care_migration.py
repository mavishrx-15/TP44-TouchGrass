"""The missing-device-schema repair is additive and safe to repeat."""

from sqlalchemy import create_engine, inspect, text

from app.migrate_care_devices import migrate


def test_additive_device_migration_preserves_existing_pins_and_is_idempotent():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table in ("tree_pins", "tree_messages"):
            connection.execute(text(f"CREATE TABLE {table} (id TEXT, created_at TEXT)"))
            connection.execute(text(f"INSERT INTO {table} VALUES ('existing', '2026-10-09')"))
        assert len(migrate(connection)) == 3
        assert migrate(connection) == []
        assert "device_credentials" in inspect(connection).get_table_names()
        for table in ("tree_pins", "tree_messages"):
            row = connection.execute(text(f"SELECT id, created_at, device_id FROM {table}")).one()
            assert row == ("existing", "2026-10-09", None)
