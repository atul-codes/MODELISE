from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, Integer, Text
from datetime import datetime, timezone
import uuid

from .session import Base


class ModelRegistry(Base):
    __tablename__ = "models"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name = Column(String(100), nullable=False)

    framework = Column(String(50))

    artifact_path = Column(String(500))

    checksum = Column(String(64))

    size = Column(BigInteger)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    status = Column(
        String(20),
        default="ACTIVE"
    )


class InspectionProvider(Base):
    """
    One row = one pluggable policy/inspection backend the orchestrator can
    call: the Layer 1 heuristic screen, Layer 1's image/NSFW check, either
    Layer 2 implementation (guardrail_layer2 or PolicyEnforcementService),
    or any geo-compliance pack. This table is the actual mechanism behind
    "plug and play, add anything anywhere" - a provider is written once and
    then attached to whichever pipelines need it, toggled independently,
    with no code changes required to rewire the pipeline.
    """
    __tablename__ = "inspection_providers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    # "layer1_heuristic" | "layer1_image_nsfw_grpc" | "layer2_faiss_rest" |
    # "layer2_grpc_classifier" | "geo_policy_engine" | "custom_http"
    kind = Column(String(50), nullable=False)

    # "layer1" | "layer2" | "geo" - purely a display/grouping hint, does
    # not restrict which pipelines can attach this provider.
    stage = Column(String(20), nullable=False, default="layer2")

    # JSON string: shape depends on `kind` (e.g. {"base_url": "..."} for
    # REST providers, {"grpc_address": "..."} for gRPC ones). Never store
    # secrets in here in plaintext - use CustomModelEndpoint /
    # CommercialProviderCredential's encrypted columns for that instead.
    config_json = Column(Text, nullable=False, default="{}")

    # JSON list of pipeline names this provider is currently active for,
    # e.g. ["custom_model_default", "commercial_ai_default"]. A pipeline
    # name is just a free-form string the chat routes reference - there is
    # no separate "pipelines" table to keep this genuinely simple to wire
    # up from the GUI.
    attached_pipelines_json = Column(Text, nullable=False, default="[]")

    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CustomModelEndpoint(Base):
    """Feature 1: a self-hosted model reachable at a URL the user already
    has running - distinct from ModelRegistry's file-upload/sandbox-run
    path, this is 'point us at your endpoint', not 'run this for us'."""
    __tablename__ = "custom_model_endpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)

    # "openai_chat" (POSTs {"messages":[...]} and reads .choices[0].message.content,
    # matches Ollama/vLLM/most self-hosted servers) | "raw_text" (POSTs
    # {"prompt": "..."} and reads the whole response body as text)
    request_style = Column(String(20), nullable=False, default="openai_chat")

    auth_header_name = Column(String(100), nullable=True)
    encrypted_auth_value = Column(Text, nullable=True)

    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CommercialProviderCredential(Base):
    """Feature 2: encrypted-at-rest API keys for commercial AI providers."""
    __tablename__ = "commercial_provider_credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(20), nullable=False)  # "openai" | "anthropic" | "gemini"
    label = Column(String(100), nullable=False)
    encrypted_api_key = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))