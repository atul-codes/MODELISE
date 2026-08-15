from __future__ import annotations

from pydantic import BaseModel, Field


class PackStats(BaseModel):
    pack_id: str
    display_name: str
    country_code: str | None
    enabled: bool
    total_vectors: int
    allow_entries: int
    block_entries: int
    created_at: str
    updated_at: str


class CSVUploadResponse(PackStats):
    skipped_rows: int


class PDFUploadResponse(PackStats):
    appended_chunks: int


class TogglePackRequest(BaseModel):
    enabled: bool


class EvaluateGeoRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    pack_ids: list[str] | None = Field(
        default=None, description="Restrict evaluation to these packs. Omit to check every enabled pack."
    )
    threshold: float | None = Field(default=None, gt=0.0, le=2.0)


class EvaluateGeoResponse(BaseModel):
    blocked: bool
    packs_checked: list[str]
    chunks_evaluated: int
    matched_chunk: str | None = None
    matched_distance: float | None = None
    matched_pack_id: str | None = None
    matched_doc_ref: str | None = None
    threshold: float


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
