from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    database_url: str
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

    # Claude (vision + extracción). Sin llave, los endpoints de /intake responden 503.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"

    # Captura de fotos y audios.
    intake_bucket: str = "intake-media"
    intake_max_image_mb: float = 10
    nhtsa_timeout_seconds: float = 4.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
