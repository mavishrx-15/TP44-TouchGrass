-- Epic 7 (Care for the Canopy): pinned trees, photos and messages.
-- Apply to the shared database by hand; the test suite and local seed read
-- schema.sql, which carries the same tables.

CREATE TABLE tree_pins (
    id TEXT PRIMARY KEY,
    zone_id TEXT REFERENCES zones(cluster_id),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy_m DOUBLE PRECISION NOT NULL,
    photo_data TEXT,
    photo_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE tree_messages (
    id TEXT PRIMARY KEY,
    pin_id TEXT NOT NULL REFERENCES tree_pins(id),
    zone_id TEXT REFERENCES zones(cluster_id),
    body TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
