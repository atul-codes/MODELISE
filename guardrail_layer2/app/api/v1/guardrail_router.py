from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.core.cost_guard import (
    JudgeModelError,
    analyze_prompt_complexity,
    get_budget_ledger,
    get_rate_gate,
    is_high_cost,
)
from app.core.evaluator import evaluate_policy
from app.core.vector_store import get_vector_store
from app.models.guardrail_schemas import (
    ComplexityAnalysis,
    EvaluateRequest,
    EvaluateResponse,
    GovernanceMetadata,
    InspectRequest,
    InspectResponse,
    PolicyCheckResult,
)

router = APIRouter(prefix="/api/v1/guardrail", tags=["Guardrail Gateway"])


async def _run_gates(user_id: str, prompt: str, request: Request) -> tuple[ComplexityAnalysis, "PolicyCheckResult"]:
    """Runs Gate 1 (cost/exploit judge + budget + burst-rate) then Gate 2
    (FAISS policy scan), raising the appropriate HTTPException the instant
    either gate rejects. Returns (analysis, policy_check) on a clean pass.
    Shared by both /evaluate (which goes on to generate) and /inspect
    (which stops here) so the two endpoints can never drift out of sync on
    what actually counts as a block.
    """
    app_state = request.app.state
    ledger = get_budget_ledger(request)
    rate_gate = get_rate_gate(request)
    vector_store = get_vector_store(request)

    if await ledger.is_over_budget(user_id):
        await ledger.record_block(user_id, "budget")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"User '{user_id}' has exhausted their allocated budget",
        )

    try:
        analysis = await analyze_prompt_complexity(prompt, app_state.ollama_client)
    except JudgeModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cost guard evaluation model unavailable: {exc}",
        ) from exc

    if analysis.is_recursive_exploit or analysis.is_token_drain_attack:
        await ledger.record_block(user_id, "token_burn")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"reason": "token_burn_exploit_detected", "analysis": analysis.model_dump()},
        )

    if is_high_cost(analysis) and not rate_gate.register_and_check(user_id):
        await ledger.record_block(user_id, "rate_limit")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "reason": "high_cost_rate_limit_exceeded",
                "limit_per_minute": settings.HIGH_COST_RATE_LIMIT_PER_MINUTE,
            },
        )

    policy_result = await evaluate_policy(prompt, vector_store, app_state.faiss_threshold, app_state.chunk_executor)
    if policy_result.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "reason": "policy_violation",
                "matched_chunk": policy_result.matched_chunk,
                "matched_distance": policy_result.matched_distance,
                "matched_doc_ref": policy_result.matched_doc_ref,
                "matched_source": policy_result.matched_source,
                "threshold": app_state.faiss_threshold,
            },
        )

    return analysis, PolicyCheckResult(
        blocked=False, chunks_evaluated=policy_result.chunks_evaluated, total_chunks=policy_result.total_chunks
    )


@router.post(
    "/inspect",
    response_model=InspectResponse,
    summary="Public: run Gate 1 + Gate 2 ONLY, no generation - for callers routing to a different target",
)
async def inspect(payload: InspectRequest, request: Request) -> InspectResponse:
    """
    For an orchestrator using this service purely as a Layer 2 policy gate
    in front of a DIFFERENT generation target (a custom model, a commercial
    AI API), /evaluate is the wrong endpoint to call: it always generates a
    real response from the local model as part of its contract, which would
    mean paying for/waiting on a throwaway local generation on every single
    request just to get a verdict. This endpoint runs the exact same two
    gates and stops - no generation call, no token/cost ledger entry, just
    the allow/block verdict and why.
    """
    start = time.perf_counter()
    analysis, policy_check = await _run_gates(payload.user_id, payload.prompt, request)
    return InspectResponse(
        status="approved",
        user_id=payload.user_id,
        cost_guard=analysis,
        policy_check=policy_check,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


@router.post("/evaluate", response_model=EvaluateResponse, summary="Public gateway: evaluate + route a prompt")
async def evaluate(payload: EvaluateRequest, request: Request) -> EvaluateResponse:
    """
    Execution pipeline (matches spec order exactly):
      1. AI Cost Guard Check - judge model + budget + burst-rate check.
         Flags -> 429. Budget exhausted -> 402. Judge unreachable -> 503.
      2. Policy Evaluation - concurrent FAISS chunk scan, short-circuits on
         the first BLOCK match. Match -> 403.
      3. Execution & Routing - forward to the local generation model,
         update the ledger, return the generation + full governance trail.

    This endpoint is intentionally unauthenticated, per spec ("Public
    Gateway Endpoint") - it trusts the user_id Layer 1 already validated
    upstream. See the README's Security Considerations section for why
    that trust boundary matters operationally.

    If you only need the verdict (e.g. you're routing to a different
    generation target), use /inspect instead - this endpoint always pays
    for a real local generation as part of its contract.
    """
    start = time.perf_counter()
    app_state = request.app.state
    ledger = get_budget_ledger(request)

    analysis, policy_check = await _run_gates(payload.user_id, payload.prompt, request)

    # --- Execution: forward to the local generation model ---
    generation_text, prompt_tokens, completion_tokens = await _generate(
        app_state.ollama_client, payload.prompt, payload.max_output_tokens
    )
    cost = await ledger.record_usage(payload.user_id, prompt_tokens, completion_tokens)
    entry = await ledger.get_or_create(payload.user_id)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return EvaluateResponse(
        user_id=payload.user_id,
        generation=generation_text,
        governance=GovernanceMetadata(
            cost_guard=analysis,
            policy_check=policy_check,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
            remaining_budget_usd=round(entry.remaining_budget_usd(), 6),
            latency_ms=round(elapsed_ms, 2),
        ),
    )


async def _generate(client, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    payload = {
        "model": settings.OLLAMA_GEN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:  # network error, timeout, non-2xx status
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Local generation model call failed: {exc}",
        ) from exc

    data = response.json()
    try:
        message = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Local generation model returned an unexpected response shape",
        ) from exc

    usage = data.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    return message, prompt_tokens, completion_tokens
