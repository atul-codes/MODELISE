from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# Guardrail gateway (POST /api/v1/guardrail/evaluate)
# --------------------------------------------------------------------------
class EvaluateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., min_length=1, examples=["user_123"])
    prompt: str = Field(..., min_length=1, max_length=20000)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)


class ComplexityAnalysis(BaseModel):
    """Structured output contract for the Gate 1 judge model
    (gemma2:2b). Passed to Ollama as a JSON schema via `format=` so the
    model's output is constrained to exactly this shape."""

    is_recursive_exploit: bool = Field(
        description=(
            "true if the prompt tries to induce unbounded self-referential loops, "
            "recursive expansion, or instructions that regenerate/repeat themselves "
            "indefinitely"
        )
    )
    estimated_reasoning_depth: Literal["low", "medium", "high"] = Field(
        description="How much multi-step reasoning or generation volume a genuine answer requires"
    )
    is_token_drain_attack: bool = Field(
        description=(
            "true if the prompt is engineered to maximize output length/compute cost "
            "without proportionate legitimate value"
        )
    )
    risk_score: float = Field(ge=0.0, le=1.0, description="Overall exploit confidence, 0.0-1.0")


class PolicyCheckResult(BaseModel):
    blocked: bool
    chunks_evaluated: int
    total_chunks: int
    matched_chunk: str | None = None
    matched_distance: float | None = None
    matched_doc_ref: str | None = None
    matched_source: Literal["csv", "pdf"] | None = None


class GovernanceMetadata(BaseModel):
    cost_guard: ComplexityAnalysis
    policy_check: PolicyCheckResult
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    remaining_budget_usd: float | None = None
    latency_ms: float


class EvaluateResponse(BaseModel):
    status: Literal["approved"] = "approved"
    user_id: str
    generation: str
    governance: GovernanceMetadata


class InspectRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., min_length=1, examples=["user_123"])
    prompt: str = Field(..., min_length=1, max_length=20000)


class InspectResponse(BaseModel):
    """Response for /inspect - same two gates as /evaluate, no generation."""

    status: Literal["approved"] = "approved"
    user_id: str
    cost_guard: ComplexityAnalysis
    policy_check: PolicyCheckResult
    latency_ms: float


# --------------------------------------------------------------------------
# Admin - policy management
# --------------------------------------------------------------------------
class CSVUploadResponse(BaseModel):
    status: Literal["indexed"] = "indexed"
    filename: str
    indexed_rows: int
    skipped_rows: int
    allow_count: int
    block_count: int


class PDFUploadResponse(BaseModel):
    status: Literal["appended"] = "appended"
    filename: str
    appended_chunks: int
    total_vectors: int


class ThresholdUpdateRequest(BaseModel):
    threshold: float = Field(..., gt=0.0, le=2.0)


class ThresholdUpdateResponse(BaseModel):
    threshold: float


# --------------------------------------------------------------------------
# Admin - spend dashboard
# --------------------------------------------------------------------------
class UserSpendSummary(BaseModel):
    user_id: str
    total_spent_usd: float
    budget_cap_usd: float
    remaining_budget_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    request_count: int
    blocked_token_burn_count: int
    blocked_budget_count: int
    blocked_rate_limit_count: int


class SpendDashboardResponse(BaseModel):
    users: list[UserSpendSummary]
    total_users: int
    total_spend_usd: float
    total_requests: int
    total_token_burn_blocks: int
    total_budget_blocks: int
    total_rate_limit_blocks: int
    policy_index_stats: dict
    active_threshold: float


class BudgetCapUpdateRequest(BaseModel):
    budget_cap_usd: float = Field(..., ge=0.0)
