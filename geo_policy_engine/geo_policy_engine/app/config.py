from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "MODELISE Geo-Compliance Policy Engine"
    APP_VERSION: str = "1.0.0"

    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    PACKS_DIR: Path = BASE_DIR / "policy_packs"
    DEFAULT_DISTANCE_THRESHOLD: float = 0.75
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    PACK_EXECUTOR_MAX_WORKERS: int = 4

    JWT_SECRET_KEY: str = "CHANGE_ME_BEFORE_ANY_REAL_DEPLOYMENT"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-admin-password"

    CORS_ALLOW_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
