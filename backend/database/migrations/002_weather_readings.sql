CREATE TABLE weather_readings (
    id TEXT PRIMARY KEY,
    observed_at TIMESTAMP NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_weather_readings_observed_at ON weather_readings(observed_at);
