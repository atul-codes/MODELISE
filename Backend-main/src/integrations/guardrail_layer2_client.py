from __future__ import annotations

import logging

import httpx

from ..core.config import settings

logger = logging.getLogger("modelise.guardrail_layer2_client")


class GuardrailLayer2UnavailableError(RuntimeError):
    pass


async def evaluate_prompt(user_id: str, prompt: str) -> dict:
    """
    Calls guardrail_layer2's /guardrail/inspect - the policy-only endpoint,
    which runs both of guardrail_layer2's own gates (its cost/budget guard
    AND its FAISS policy match) but never generates a response. Using
    /evaluate here instead would trigger a real local-model generation on
    every single orchestrator request just to get a verdict, which is
    exactly what /inspect exists to avoid.

    Note: because this still runs guardrail_layer2's own Gate 1, a user
    whose budget is exhausted *within guardrail_layer2's own ledger* will
    also get blocked here, even if the orchestrator has no budget concept
    of its own for this pipeline. That's a real interaction to be aware of
    if you use guardrail_layer2 as a Layer 2 provider and also expose it
    directly elsewhere under the same user_id scheme.
    """
    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.GUARDRAIL_LAYER2_BASE_URL}/api/v1/guardrail/inspect",
                json={"user_id": user_id, "prompt": prompt},
            )
            if response.status_code == 403:
                body = response.json()
                return {"blocked": True, "detail": body.get("detail")}
            response.raise_for_status()
            body = response.json()
            return {"blocked": False, "policy_check": body.get("policy_check")}
    except httpx.HTTPError as exc:
        logger.warning("guardrail_layer2 inspect call failed: %s", exc)
        raise GuardrailLayer2UnavailableError(str(exc)) from exc
