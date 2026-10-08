CREATE TABLE tree_pins (
    id TEXT PRIMARY KEY,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    accuracy_m DOUBLE PRECISION NOT NULL,
    cluster_id TEXT NOT NULL REFERENCES zones(cluster_id),
    photo_path TEXT,
    nearest_tree_id INTEGER REFERENCES trees(com_id),
    device_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','hidden')),
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_tree_pins_zone ON tree_pins(cluster_id);
CREATE INDEX idx_tree_pins_device ON tree_pins(device_id, created_at);
CREATE TABLE tree_messages (
    id TEXT PRIMARY KEY,
    pin_id TEXT NOT NULL REFERENCES tree_pins(id),
    kind TEXT NOT NULL CHECK (kind IN ('message','report')),
    body TEXT NOT NULL CHECK (length(body) <= 1000),
    device_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','hidden')),
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_tree_messages_pin ON tree_messages(pin_id);
CREATE INDEX idx_tree_messages_device ON tree_messages(device_id, created_at);
