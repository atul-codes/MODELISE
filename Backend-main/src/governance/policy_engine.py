"""
Layer 2: Custom Policy Engine, generalized to be plug-and-play.

Rather than hardcoding "call guardrail_layer2", `run_layer2` looks up
whichever InspectionProvider rows are enabled AND attached to the given
pipeline, and consults every one of them concurrently: guardrail_layer2
(FAISS/REST) via /inspect, PolicyEnforcementService (gRPC classifier) if
it's been enabled, and any geo-compliance packs attached to this pipeline.
The instant any of them returns a block, evaluation stops and the rest are
cancelled - same worst-case, no-averaging philosophy as guardrail_layer2's
own Gate 2, just applied across providers instead of across chunks.

This is the concrete mechanism behind "it should be like guardrail layer 2
but plug and play, add anything anywhere through a simple interface" - a
provider is a row in a table, attaching it to a pipeline is a list append,
and this function doesn't know or care how many providers exist or what
kind they are.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..integrations import geo_policy_client, guardrail_layer2_client
from ..integrations.pel.client import PELUnavailableError, inspect_text
from ..services import provider_registry

logger = logging.getLogger("modelise.policy_engine")


@dataclass
class Layer2Verdict:
    blocked: bool
    providers_checked: list[str] = field(default_factory=list)
    matched_provider: str | None = None
    detail: dict = field(default_factory=dict)


async def _check_guardrail_layer2(user_id: str, prompt: str) -> tuple[bool, dict]:
    try:
        result = await guardrail_layer2_client.evaluate_prompt(user_id, prompt)
        return result["blocked"], result
    except guardrail_layer2_client.GuardrailLayer2UnavailableError as exc:
        logger.warning("guardrail_layer2 provider unreachable, failing closed: %s", exc)
        return True, {"error": str(exc)}


async def _check_pel_classifier(prompt: str) -> tuple[bool, dict]:
    try:
        result = await inspect_text(prompt)
        return result["action"] == "BLOCK", result
    except PELUnavailableError as exc:
        logger.warning("PolicyEnforcementService provider unreachable, failing closed: %s", exc)
        return True, {"error": str(exc)}


async def _check_geo_pack(prompt: str, pack_id: str) -> tuple[bool, dict]:
    try:
        result = await geo_policy_client.evaluate(prompt, pack_ids=[pack_id])
        return result["blocked"], result
    except geo_policy_client.GeoPolicyEngineUnavailableError as exc:
        logger.warning("Geo Policy Engine unreachable, failing closed: %s", exc)
        return True, {"error": str(exc)}


async def run_layer2(db: Session, pipeline_name: str, user_id: str, prompt: str) -> Layer2Verdict:
    providers = provider_registry.get_providers_for_pipeline(db, pipeline_name)
    layer2_providers = [p for p in providers if p.stage in ("layer2", "geo")]

    if not layer2_providers:
        return Layer2Verdict(blocked=False, providers_checked=[])

    async def _run_one(provider) -> tuple[str, bool, dict]:
        if provider.kind == "layer2_faiss_rest":
            blocked, detail = await _check_guardrail_layer2(user_id, prompt)
        elif provider.kind == "layer2_grpc_classifier":
            blocked, detail = await _check_pel_classifier(prompt)
        elif provider.kind == "geo_policy_pack":
            config = json.loads(provider.config_json or "{}")
            blocked, detail = await _check_geo_pack(prompt, config.get("pack_id", provider.id))
        else:
            logger.warning("Unknown Layer 2 provider kind '%s', skipping", provider.kind)
            return provider.name, False, {"skipped": "unknown provider kind"}
        return provider.name, blocked, detail

    tasks = [asyncio.ensure_future(_run_one(p)) for p in layer2_providers]
    checked: list[str] = []
    matched_provider = None
    matched_detail: dict = {}

    try:
        for finished in asyncio.as_completed(tasks):
            name, blocked, detail = await finished
            checked.append(name)
            if blocked:
                matched_provider = name
                matched_detail = detail
                break
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return Layer2Verdict(
        blocked=matched_provider is not None,
        providers_checked=checked,
        matched_provider=matched_provider,
        detail=matched_detail,
    )
