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
