from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Values come from .env locally and from
    the runtime environment in Cloud Run. Nothing is hard-coded."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    google_maps_api_key: str = ""
    access_token: str = ""
    cbd_boundary_geojson: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "tree-photos"
    high_pollen_species: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def high_pollen_list(self) -> list[str]:
        return [name.strip().casefold() for name in self.high_pollen_species.split(",") if name.strip()]


settings = Settings()
