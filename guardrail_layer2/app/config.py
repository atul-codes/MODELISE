"""
Central configuration for MODELISE Layer 2, loaded from environment
variables / a local .env file via pydantic-settings.

Nothing in this module talks to the network or the filesystem beyond
resolving paths - it just describes the shape of the configuration and
provides sane local-hardware defaults so the service is runnable out of
the box with `cp .env.example .env`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service identity ---
    APP_NAME: str = "MODELISE Layer 2 - Guardrail Proxy"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production"] = "development"

    # --- Ollama / local LLM endpoints ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EVAL_MODEL: str = "gemma2:2b"
    OLLAMA_GEN_MODEL: str = "gemma:2b"
    OLLAMA_REQUEST_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_EVAL_TIMEOUT_SECONDS: float = 15.0
    # Gate 1 is a security-relevant gate. If the local judge model can't be
    # reached or won't return usable output, the safe default is to refuse
    # the request (fail CLOSED) rather than silently letting it through.
    # Flip this only if availability matters more than strict enforcement
    # for your deployment.
    FAIL_OPEN_ON_JUDGE_ERROR: bool = False

    # --- Embeddings / FAISS (Gate 2) ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_INDEX_DIR: Path = BASE_DIR / "vector_indices"
    FAISS_DISTANCE_THRESHOLD: float = 0.75
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    # Thread pool used for the CPU-bound embedding + FAISS search calls so
    # they never block the asyncio event loop. See core/evaluator.py.
    VECTOR_EXECUTOR_MAX_WORKERS: int = 4

    # --- Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_BEFORE_ANY_REAL_DEPLOYMENT"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-admin-password"

    # --- Cost / budget (Gate 1) ---
    DEFAULT_USER_BUDGET_USD: float = 5.0
    # Illustrative per-token rates for simulated cost allocation. Local
    # inference has no real per-token cost, but many orgs still want to
    # attribute compute usage across teams/users - tune these to whatever
    # your internal chargeback model expects.
    PROMPT_TOKEN_RATE_USD: float = 0.0000005
    COMPLETION_TOKEN_RATE_USD: float = 0.0000015
    HIGH_COST_RATE_LIMIT_PER_MINUTE: int = 10
    HIGH_COST_RISK_SCORE_THRESHOLD: float = 0.55

    # --- Persistence ---
    DATA_DIR: Path = BASE_DIR / "data"
    LEDGER_FILE: Path = BASE_DIR / "data" / "ledger.json"

    # --- CORS ---
    CORS_ALLOW_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
