-- Proves a device_id belongs to whoever first used it, so a tree pin or
-- message can't be posted under someone else's device_id (Epic 7 hardening).
-- Apply to the shared database by hand; the test suite and local seed read
-- schema.sql, which carries the same table.

CREATE TABLE device_credentials (
    device_id TEXT PRIMARY KEY,
    credential_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
