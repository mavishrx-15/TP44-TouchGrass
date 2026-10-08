-- GET /api/weather/now's 30-minute cache (Epic 5).
-- Apply to the shared database by hand; the test suite and local seed read
-- schema.sql, which carries the same table.

CREATE TABLE weather_readings (
    id TEXT PRIMARY KEY,
    observed_at TEXT NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_weather_readings_observed_at ON weather_readings(observed_at);
