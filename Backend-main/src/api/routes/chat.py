"""
The actual chain: Layer 1 -> Layer 2 (every attached provider) -> target.

Two routes, two pipeline names ("custom_model_default" and
"commercial_ai_default"), same shared execution function underneath -
`_run_pipeline`. Which providers actually run for each is entirely a
function of what's attached to that pipeline name in the registry; this
function has no hardcoded knowledge of guardrail_layer2, PEL, or any geo
pack, which is the point.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import decrypt_secret
from src.database.models import CommercialProviderCredential, CustomModelEndpoint
from src.database.session import get_db
from src.governance import input_guard, policy_engine
from src.models.router import call_custom_model
from src.schemas.api_schemas import ChatBlockedResponse, ChatResponse, CommercialChatRequest, CustomModelChatRequest, GovernanceTrail
from src.services.llm_service import call_commercial_provider

logger = logging.getLogger("modelise.chat")

chat_router = APIRouter(prefix="/api/v1/chat", tags=["Chat / Execution"])


@dataclass
class GovernanceOutcome:
    blocked_response: ChatBlockedResponse | None
    layer1: input_guard.Layer1Verdict | None
    layer2: policy_engine.Layer2Verdict | None


async def _run_governance(db: Session, pipeline_name: str, user_id: str, prompt: str, image_b64: str | None, image_mime: str) -> GovernanceOutcome:
    image_bytes = base64.b64decode(image_b64) if image_b64 else None

    layer1 = await input_guard.run_layer1(db, pipeline_name, prompt, image_bytes, image_mime)
    if layer1.blocked:
        blocked = ChatBlockedResponse(
            blocked_at="layer1",
            detail={"checks_run": layer1.checks_run, "matched_patterns": layer1.matched_patterns, "image_check": layer1.image_check},
        )
        return GovernanceOutcome(blocked_response=blocked, layer1=layer1, layer2=None)

    layer2 = await policy_engine.run_layer2(db, pipeline_name, user_id, prompt)
    if layer2.blocked:
        blocked = ChatBlockedResponse(
            blocked_at="layer2",
            detail={"providers_checked": layer2.providers_checked, "matched_provider": layer2.matched_provider, "info": layer2.detail},
        )
        return GovernanceOutcome(blocked_response=blocked, layer1=layer1, layer2=layer2)

    return GovernanceOutcome(blocked_response=None, layer1=layer1, layer2=layer2)


@chat_router.post("/custom", response_model=ChatResponse, responses={403: {"model": ChatBlockedResponse}})
async def chat_custom_model(payload: CustomModelChatRequest, db: Session = Depends(get_db)):
    """Feature 1: chain Layer 1 -> Layer 2 -> a registered self-hosted
    model endpoint. Every prompt hitting a custom model goes through this
    route, so it is always screened before it reaches your model."""
    endpoint = db.query(CustomModelEndpoint).filter(CustomModelEndpoint.id == payload.endpoint_id).first()
    if endpoint is None or not endpoint.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such enabled custom model endpoint")

    outcome = await _run_governance(
        db, "custom_model_default", payload.user_id, payload.prompt, payload.image_base64, payload.image_mime_type
    )
    if outcome.blocked_response is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=outcome.blocked_response.model_dump())
    layer1, layer2 = outcome.layer1, outcome.layer2

    generation = await call_custom_model(endpoint, payload.prompt, payload.max_output_tokens)

    return ChatResponse(
        generation=generation,
        governance=GovernanceTrail(
            layer1={"checks_run": layer1.checks_run, "image_check": layer1.image_check},
            layer2={"providers_checked": layer2.providers_checked},
        ),
    )


@chat_router.post("/commercial", response_model=ChatResponse, responses={403: {"model": ChatBlockedResponse}})
async def chat_commercial(payload: CommercialChatRequest, db: Session = Depends(get_db)):
    """Feature 2: chain Layer 1 -> Layer 2 -> commercial AI (OpenAI /
    Anthropic / Gemini, picked by whichever credential_id is passed). If
    either layer blocks, the commercial API is never called - no tokens
    spent on a rejected prompt."""
    credential = db.query(CommercialProviderCredential).filter(CommercialProviderCredential.id == payload.credential_id).first()
    if credential is None or not credential.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such enabled credential")

    outcome = await _run_governance(
        db, "commercial_ai_default", payload.user_id, payload.prompt, payload.image_base64, payload.image_mime_type
    )
    if outcome.blocked_response is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=outcome.blocked_response.model_dump())
    layer1, layer2 = outcome.layer1, outcome.layer2

    api_key = decrypt_secret(credential.encrypted_api_key)
    generation, prompt_tokens, completion_tokens = await call_commercial_provider(
        credential.provider, api_key, payload.prompt, payload.model, payload.max_output_tokens
    )

    return ChatResponse(
        generation=generation,
        governance=GovernanceTrail(
            layer1={"checks_run": layer1.checks_run, "image_check": layer1.image_check},
            layer2={
                "providers_checked": layer2.providers_checked,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        ),
    )
