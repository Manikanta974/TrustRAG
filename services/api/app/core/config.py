from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API foundation.

    Future integrations belong here only after their implementation phase starts.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TrustRAG API"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql://trustrag:local-development-only@localhost:5432/trustrag"


@lru_cache
def get_settings() -> Settings:
    return Settings()
