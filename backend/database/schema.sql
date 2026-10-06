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

-- Weather owner: apply to the intended database explicitly, not at app startup.
CREATE TABLE IF NOT EXISTS weather_readings (
    id TEXT PRIMARY KEY,
    observed_at TIMESTAMP NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_weather_observed ON weather_readings(observed_at);

-- Community owner: server generates UUID ids, UTC timestamps and pending status.
CREATE TABLE IF NOT EXISTS tree_pins (
    id TEXT PRIMARY KEY,
    lat DOUBLE PRECISION NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lng DOUBLE PRECISION NOT NULL CHECK (lng BETWEEN -180 AND 180),
    accuracy_m DOUBLE PRECISION NOT NULL CHECK (accuracy_m >= 0),
    cluster_id TEXT REFERENCES zones(cluster_id),
    photo_path TEXT,
    nearest_tree_id INTEGER REFERENCES trees(com_id),
    device_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'hidden')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tree_messages (
    id TEXT PRIMARY KEY,
    pin_id TEXT NOT NULL REFERENCES tree_pins(id),
    kind TEXT NOT NULL CHECK (kind IN ('message', 'report')),
    body TEXT NOT NULL CHECK (LENGTH(TRIM(body)) BETWEEN 1 AND 1000),
    device_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'hidden')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pins_zone_status ON tree_pins(cluster_id, status);
CREATE INDEX IF NOT EXISTS idx_pins_device_created ON tree_pins(device_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_pin_status ON tree_messages(pin_id, status);
CREATE INDEX IF NOT EXISTS idx_messages_device_created ON tree_messages(device_id, created_at);
