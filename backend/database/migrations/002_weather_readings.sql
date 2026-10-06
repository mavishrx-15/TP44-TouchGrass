-- Weather owner: apply to the intended database explicitly, not at app startup.
CREATE TABLE IF NOT EXISTS weather_readings (
    id TEXT PRIMARY KEY,
    observed_at TIMESTAMP NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_weather_observed ON weather_readings(observed_at);
