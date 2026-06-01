from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    app_name: str = "PrimeTrade API"
    app_version: str = "0.0.1"
    debug: bool = False
    environment: str = "development"

    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/taskflow"
    database_echo: bool = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
