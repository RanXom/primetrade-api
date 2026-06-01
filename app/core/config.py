from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    app_name: str = "Prime Trade API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "postgresql+asyncpg://prime_user:12123@localhost:5432/primedb"
    database_echo: bool = False

    secret_key: str = "change-this-to-a-secure-random-secret-key-at-least-32-characters"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    redis_url: str = "redis://localhost:6379/0"

    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    bcrypt_rounds: int = 12

    rate_limit_per_minute: int = 60

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
