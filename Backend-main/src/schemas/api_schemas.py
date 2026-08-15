from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --- providers (plug-and-play registry) ---
class ProviderOut(BaseModel):
    id: str
    name: str
    description: str | None
    kind: str
    stage: str
    config: dict
    attached_pipelines: list[str]
    enabled: bool
    priority: int
    created_at: str | None
    updated_at: str | None


class ProviderCreateRequest(BaseModel):
    name: str
    description: str = ""
    kind: str
    stage: str = "layer2"
    config: dict = Field(default_factory=dict)
    attached_pipelines: list[str] = Field(default_factory=list)
    priority: int = 100


class ProviderToggleRequest(BaseModel):
    enabled: bool


class ProviderAttachmentsRequest(BaseModel):
    attached_pipelines: list[str]


# --- custom model endpoints (Feature 1) ---
class CustomModelCreateRequest(BaseModel):
    name: str
    base_url: str = Field(..., description="e.g. http://localhost:11434/v1/chat/completions")
    request_style: Literal["openai_chat", "raw_text"] = "openai_chat"
    auth_header_name: str | None = None
    auth_header_value: str | None = Field(default=None, description="Sent once for encryption, never returned")


class CustomModelOut(BaseModel):
    id: str
    name: str
    base_url: str
    request_style: str
    auth_header_name: str | None
    has_auth: bool
    enabled: bool
    created_at: str | None


# --- commercial provider credentials (Feature 2) ---
class CredentialCreateRequest(BaseModel):
    provider: Literal["openai", "anthropic", "gemini"]
    label: str
    api_key: str


class CredentialOut(BaseModel):
    id: str
    provider: str
    label: str
    masked_key: str
    enabled: bool
    created_at: str | None


# --- chat / execution ---
class CustomModelChatRequest(BaseModel):
    user_id: str
    endpoint_id: str
    prompt: str = Field(..., min_length=1, max_length=20000)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)
    image_base64: str | None = Field(default=None, description="Optional, for Layer 1's multimodal NSFW check")
    image_mime_type: str = "image/jpeg"


class CommercialChatRequest(BaseModel):
    user_id: str
    credential_id: str
    prompt: str = Field(..., min_length=1, max_length=20000)
    model: str | None = None
    max_output_tokens: int = Field(default=512, ge=1, le=8192)
    image_base64: str | None = Field(default=None, description="Optional, for Layer 1's multimodal NSFW check")
    image_mime_type: str = "image/jpeg"


class GovernanceTrail(BaseModel):
    layer1: dict
    layer2: dict


class ChatResponse(BaseModel):
    status: Literal["approved"] = "approved"
    generation: str
    governance: GovernanceTrail


class ChatBlockedResponse(BaseModel):
    status: Literal["blocked"] = "blocked"
    blocked_at: Literal["layer1", "layer2"]
    detail: dict


# --- geo policy (proxied to GeoPolicyEngine) ---
class GeoPackOut(BaseModel):
    pack_id: str
    display_name: str
    country_code: str | None
    enabled: bool
    total_vectors: int
    allow_entries: int
    block_entries: int


class GeoToggleRequest(BaseModel):
    enabled: bool
