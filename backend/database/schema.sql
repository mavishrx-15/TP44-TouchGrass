-- Touch Grass database schema
-- Populated from touch_grass_map_data.json (see backend/dataset/)

CREATE TABLE zones (
    cluster_id TEXT PRIMARY KEY,
    center_lat DOUBLE PRECISION NOT NULL,
    center_lon DOUBLE PRECISION NOT NULL,
    tree_count INTEGER NOT NULL,
    precinct TEXT NOT NULL,
    street_name TEXT
);

CREATE TABLE trees (
    com_id INTEGER PRIMARY KEY,
    common_name TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    family TEXT NOT NULL,
    family_display_category TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    display_category TEXT NOT NULL,
    useful_life_expectency TEXT,
    year_planted_display TEXT,
    polygon_id DOUBLE PRECISION,
    match_type TEXT NOT NULL,
    cluster_id TEXT REFERENCES zones(cluster_id),
    precinct TEXT NOT NULL,
    located_in TEXT NOT NULL
);

CREATE TABLE species (
    scientific_name TEXT PRIMARY KEY,
    common_name TEXT NOT NULL,
    family TEXT NOT NULL,
    family_display_category TEXT NOT NULL,
    display_category TEXT NOT NULL,
    total_count INTEGER NOT NULL,
    zone_counts JSONB NOT NULL
);

CREATE INDEX idx_trees_precinct ON trees(precinct);
CREATE INDEX idx_trees_cluster_id ON trees(cluster_id);
CREATE INDEX idx_trees_display_category ON trees(display_category);
CREATE INDEX idx_zones_precinct ON zones(precinct);

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
    device_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_tree_pins_device ON tree_pins(device_id, created_at);

CREATE TABLE tree_messages (
    id TEXT PRIMARY KEY,
    pin_id TEXT NOT NULL REFERENCES tree_pins(id),
    zone_id TEXT REFERENCES zones(cluster_id),
    body TEXT NOT NULL,
    kind TEXT NOT NULL,
    device_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE INDEX idx_tree_messages_device ON tree_messages(device_id, created_at);

-- GET /api/weather/now's 30-minute cache (Epic 5).
CREATE TABLE weather_readings (
    id TEXT PRIMARY KEY,
    observed_at TEXT NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_weather_readings_observed_at ON weather_readings(observed_at);

-- Proves a device_id belongs to whoever first used it, so a tree pin or
-- message can't be posted under someone else's device_id (Epic 7 hardening).
CREATE TABLE device_credentials (
    device_id TEXT PRIMARY KEY,
    credential_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
