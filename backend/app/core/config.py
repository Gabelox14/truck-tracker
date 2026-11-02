from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    database_url: str
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    # URL pública del frontend, para los enlaces del Excel. Sin definir, se usa
    # el primer origen de CORS_ORIGINS.
    app_base_url: str | None = None

    # Claude (vision + extracción). Sin llave, los endpoints de /intake responden 503.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"

    # Transcripción de notas de voz: cualquier API compatible con OpenAI
    # (por defecto Groq whisper-large-v3). Sin llave, /intake/audio responde 503.
    transcription_api_key: str | None = None
    transcription_base_url: str = "https://api.groq.com/openai/v1"
    transcription_model: str = "whisper-large-v3"

    # Captura de fotos y audios.
    intake_bucket: str = "intake-media"
    intake_max_image_mb: float = 10
    intake_max_audio_mb: float = 25
    nhtsa_timeout_seconds: float = 4.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def resolved_app_base_url(self) -> str:
        return (self.app_base_url or self.cors_origins_list[0]).rstrip("/")


settings = Settings()
