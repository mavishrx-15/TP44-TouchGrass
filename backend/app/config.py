from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Values come from .env locally and from
    the runtime environment in Cloud Run. Nothing is hard-coded."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    google_maps_api_key: str = ""
    access_password: str = ""
    access_token_secret: str = "change-me-in-development"
    access_token_ttl_seconds: int = 3600

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
