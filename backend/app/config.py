from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Values come from .env locally and from
    the runtime environment in Cloud Run. Nothing is hard-coded."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provisional Hoddle Grid outline; replace with the team's agreed GeoJSON ring.
    # Coordinates are [longitude, latitude], as in GeoJSON. No user positions are stored.
    cbd_boundary: list[tuple[float, float]] = [
        (144.9514, -37.8141),
        (144.9665, -37.8075),
        (144.9740, -37.8154),
        (144.9590, -37.8220),
        (144.9514, -37.8141),
    ]

    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    google_maps_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_photo_bucket: str = "tree-photos"
    posts_per_device_per_hour: int = Field(default=10, ge=1, le=1000)
    access_password: str = ""
    access_token_secret: str = ""
    access_token_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
