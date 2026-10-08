CREATE TABLE device_credentials (
    device_id TEXT PRIMARY KEY,
    credential_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
