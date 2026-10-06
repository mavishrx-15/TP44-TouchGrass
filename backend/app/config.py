from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Values come from .env locally and from
    the runtime environment in Cloud Run. Nothing is hard-coded."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    google_maps_api_key: str = ""
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
