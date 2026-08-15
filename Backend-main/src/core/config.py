from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "MODELISE"
    APP_VERSION: str = "1.0.0"

    # --- Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_BEFORE_ANY_REAL_DEPLOYMENT"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-admin-password"

    # --- Secret-at-rest encryption for stored credentials (commercial AI
    # API keys, custom-endpoint auth headers). Separate key from
    # JWT_SECRET_KEY on purpose - one signs tokens, the other encrypts data
    # at rest, and a leak of one shouldn't automatically compromise the
    # other. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # --- Downstream service locations (Layer 1 / Layer 2 / Geo engine) ---
    # Layer 2 default provider: guardrail_layer2 (FAISS/REST)
    GUARDRAIL_LAYER2_BASE_URL: str = "http://localhost:8000"
    # Layer 2 alternate provider: PolicyEnforcementService (gRPC/Keras classifier)
    PEL_GRPC_ADDRESS: str = "localhost:50051"
    # Geo-compliance engine, independently pluggable into any pipeline
    GEO_POLICY_ENGINE_BASE_URL: str = "http://localhost:8100"
    # Service-account credentials Backend-main uses to call GeoPolicyEngine's
    # admin endpoints on behalf of whichever human is logged into THIS
    # service - keeps the GUI to a single login instead of asking the admin
    # to separately authenticate against every downstream service.
    GEO_POLICY_ENGINE_ADMIN_USERNAME: str = "admin"
    GEO_POLICY_ENGINE_ADMIN_PASSWORD: str = "change-this-admin-password"

    DOWNSTREAM_TIMEOUT_SECONDS: float = 30.0

    # --- Commercial AI provider endpoints (overridable for testing / proxies) ---
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    ANTHROPIC_API_BASE: str = "https://api.anthropic.com/v1"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta"

    CORS_ALLOW_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
