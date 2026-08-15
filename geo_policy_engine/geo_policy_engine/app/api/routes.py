from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from ..core.security import create_access_token, get_admin, get_current_admin, verify_password
from ..core.pack_store import slugify_pack_id
from ..core.evaluator import evaluate_against_packs
from ..models.schemas import (
    CSVUploadResponse,
    EvaluateGeoRequest,
    EvaluateGeoResponse,
    LoginRequest,
    PackStats,
    PDFUploadResponse,
    TogglePackRequest,
    TokenResponse,
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
packs_router = APIRouter(prefix="/api/v1/packs", tags=["Policy Packs"], dependencies=[Depends(get_current_admin)])
eval_router = APIRouter(prefix="/api/v1", tags=["Evaluation"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    admin = get_admin(payload.username)
    if admin is None or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token, expires_in = create_access_token(subject=payload.username, role="admin")
    return TokenResponse(access_token=token, expires_in=expires_in)


@packs_router.get("", response_model=list[PackStats])
async def list_packs(request: Request) -> list[PackStats]:
    return [PackStats(**p) for p in request.app.state.pack_store.list_packs()]


@packs_router.post("/{pack_id}/upload-csv", response_model=CSVUploadResponse)
async def upload_pack_csv(
    pack_id: str, request: Request, display_name: str, country_code: str | None = None, file: UploadFile = File(...)
) -> CSVUploadResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .csv")
    slug = slugify_pack_id(pack_id)
    content = await file.read()
    store = request.app.state.pack_store
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, store.upload_csv_sync, slug, display_name, country_code, content, file.filename
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CSVUploadResponse(**result)


@packs_router.post("/{pack_id}/upload-pdf", response_model=PDFUploadResponse)
async def upload_pack_pdf(
    pack_id: str, request: Request, display_name: str, country_code: str | None = None, file: UploadFile = File(...)
) -> PDFUploadResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .pdf")
    slug = slugify_pack_id(pack_id)
    content = await file.read()
    store = request.app.state.pack_store
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, store.upload_pdf_sync, slug, display_name, country_code, content, file.filename
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PDFUploadResponse(**result)


@packs_router.put("/{pack_id}/toggle", response_model=PackStats)
async def toggle_pack(pack_id: str, payload: TogglePackRequest, request: Request) -> PackStats:
    store = request.app.state.pack_store
    pack = store.get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No pack '{pack_id}'")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pack.set_enabled_sync, payload.enabled)
    return PackStats(**pack.stats())


@packs_router.delete("/{pack_id}")
async def delete_pack(pack_id: str, request: Request) -> dict:
    deleted = request.app.state.pack_store.delete_pack(pack_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No pack '{pack_id}'")
    return {"status": "deleted", "pack_id": pack_id}


@eval_router.post("/evaluate", response_model=EvaluateGeoResponse, summary="Public: evaluate a prompt against enabled packs")
async def evaluate(payload: EvaluateGeoRequest, request: Request) -> EvaluateGeoResponse:
    """Unauthenticated, matching guardrail_layer2's evaluate endpoint - this
    is meant to be called by the orchestrator (Backend-main), not exposed
    directly to end users. See the README's Security Considerations."""
    app_state = request.app.state
    threshold = payload.threshold if payload.threshold is not None else app_state.default_threshold
    result = await evaluate_against_packs(
        payload.prompt, app_state.pack_store, app_state.pack_executor, threshold, payload.pack_ids
    )
    return EvaluateGeoResponse(
        blocked=result.blocked,
        packs_checked=result.packs_checked,
        chunks_evaluated=result.chunks_evaluated,
        matched_chunk=result.matched_chunk,
        matched_distance=result.matched_distance,
        matched_pack_id=result.matched_pack_id,
        matched_doc_ref=result.matched_doc_ref,
        threshold=threshold,
    )
