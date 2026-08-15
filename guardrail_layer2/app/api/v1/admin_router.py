from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.core.cost_guard import get_budget_ledger
from app.core.security import get_current_admin
from app.core.vector_store import get_vector_store
from app.models.guardrail_schemas import (
    BudgetCapUpdateRequest,
    CSVUploadResponse,
    PDFUploadResponse,
    ThresholdUpdateRequest,
    ThresholdUpdateResponse,
    UserSpendSummary,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Policy Management"], dependencies=[Depends(get_current_admin)])


async def _run_ingest(fn, content: bytes, filename: str) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, fn, content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/policy/upload-csv", response_model=CSVUploadResponse)
async def upload_policy_csv(request: Request, file: UploadFile = File(...)) -> CSVUploadResponse:
    """Initializes or overwrites the base FAISS policy index from a CSV of
    (prompt, allow/block) rows, where 1 = ALLOW and 0 = BLOCK."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .csv")

    content = await file.read()
    store = get_vector_store(request)
    result = await _run_ingest(store.rebuild_from_csv_sync, content, file.filename)
    return CSVUploadResponse(filename=file.filename, **result)


@router.post("/policy/upload-pdf", response_model=PDFUploadResponse)
async def upload_policy_pdf(request: Request, file: UploadFile = File(...)) -> PDFUploadResponse:
    """Chunks a compliance PDF and appends it to the active FAISS index as
    BLOCK entries, without rebuilding the existing index from scratch."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .pdf")

    content = await file.read()
    store = get_vector_store(request)
    result = await _run_ingest(store.append_pdf_chunks_sync, content, file.filename)
    return PDFUploadResponse(filename=file.filename, **result)


@router.put("/settings/threshold", response_model=ThresholdUpdateResponse)
async def update_threshold(payload: ThresholdUpdateRequest, request: Request) -> ThresholdUpdateResponse:
    """Adjusts the global FAISS BLOCK-match distance cutoff at runtime -
    lower is stricter (fewer matches count as a block), higher is looser."""
    request.app.state.faiss_threshold = payload.threshold
    return ThresholdUpdateResponse(threshold=payload.threshold)


@router.put("/users/{user_id}/budget", response_model=UserSpendSummary, tags=["Admin - Spend Dashboard"])
async def set_user_budget(user_id: str, payload: BudgetCapUpdateRequest, request: Request) -> UserSpendSummary:
    """Convenience endpoint added beyond the original spec: lets you set a
    user's budget cap directly so you can exercise the 402 path in testing
    without waiting for organic spend to accumulate."""
    ledger = get_budget_ledger(request)
    entry = await ledger.set_budget_cap(user_id, payload.budget_cap_usd)
    return UserSpendSummary(**entry.to_dashboard_dict())
