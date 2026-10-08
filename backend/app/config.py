from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Values come from .env locally and from
    the runtime environment in Cloud Run. Nothing is hard-coded."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The Hoddle Grid, from the centreline intersections of its four streets in
    # OpenStreetMap, pushed out 20 m to take in the far kerb — and further on
    # the two sides where the main stations sit just outside the grid line:
    # 80 m past Flinders St for Flinders Street Station, 120 m past Spencer St
    # for Southern Cross. See database/CBD_API.md.
    # Coordinates are [longitude, latitude], as in GeoJSON. No user positions are stored.
    cbd_boundary: list[tuple[float, float]] = [
        (144.954098, -37.822128),  # Flinders St x Spencer St
        (144.975427, -37.815891),  # Flinders St x Spring St
        (144.971426, -37.807191),  # Spring St x La Trobe St
        (144.950070, -37.813376),  # La Trobe St x Spencer St
        (144.954098, -37.822128),
    ]

    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    google_maps_api_key: str = ""
    # Zero explicitly disables the posting limit for local testing.
    posts_per_device_per_hour: int = Field(default=10, ge=0, le=1000)
    access_password: str = ""
    access_token_secret: str = ""
    # Shared secret for approving public tree messages and photos (Epic 7).
    # Empty means nobody can approve, so nothing is ever published by accident.
    care_admin_token: str = ""
    access_token_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
