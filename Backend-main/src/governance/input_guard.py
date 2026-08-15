"""
Layer 1: Instant Multimodal Security.

Two independent checks, both meant to be fast (no LLM call - Layer 2 is
where the heavier semantic check happens):

1. `screen_text` - a pattern-based prompt-injection / jailbreak screen.
   Runs in-process, no network hop, sub-millisecond. This is the piece
   that didn't exist anywhere in any uploaded repo, built fresh here.
2. `screen_image` - if the request includes an image, routes it through
   PolicyEnforcementService's InspectImage RPC (NSFW detection).

Both checks are gated by the provider registry (`provider_registry.py`):
if the corresponding InspectionProvider row is disabled or not attached to
the current pipeline, the check is skipped entirely rather than silently
running unconditionally - this is what makes Layer 1 itself pluggable,
not just Layer 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..integrations.pel.client import PELUnavailableError, inspect_image
from ..services import provider_registry

# Pattern categories, not an exhaustive or scored classifier - this is a
# fast pre-filter, not a replacement for Layer 2's semantic check. Each
# entry is (label, compiled pattern). A prompt matching any pattern is
# flagged; the caller decides whether "flagged" means block or just log,
# via BLOCK_ON_MATCH below.
_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("instruction_override", re.compile(r"\bignore (all|any|previous|prior|above|the) instructions?\b", re.I)),
    ("instruction_override", re.compile(r"\bdisregard (your|the|all|previous) (instructions?|rules?|guidelines?)\b", re.I)),
    ("persona_override", re.compile(r"\byou are now\b.{0,40}\b(dan|unrestricted|unfiltered|jailbroken)\b", re.I)),
    ("persona_override", re.compile(r"\b(developer|debug|god|admin)\s?mode\b.{0,30}\b(enable|activate|on)\b", re.I)),
    ("persona_override", re.compile(r"\bact as if you (have no|had no|had zero)\b.{0,20}\brestrictions?\b", re.I)),
    ("prompt_extraction", re.compile(r"\b(reveal|print|show|repeat|output) (your|the) (system prompt|instructions|initial prompt)\b", re.I)),
    ("prompt_extraction", re.compile(r"\bwhat (are|is) your (system prompt|instructions|rules)\b", re.I)),
    ("delimiter_stuffing", re.compile(r"(#{5,}|-{10,}|={10,})")),
    ("delimiter_stuffing", re.compile(r"(<\|.{0,30}\|>){3,}")),
]

BLOCK_ON_MATCH = {"instruction_override", "persona_override", "prompt_extraction"}


@dataclass
class Layer1Verdict:
    blocked: bool
    checks_run: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    image_check: dict | None = None
    skipped_reason: str | None = None


def screen_text(prompt: str) -> tuple[bool, list[str]]:
    """Returns (should_block, matched_pattern_labels)."""
    matched: list[str] = []
    for label, pattern in _INJECTION_PATTERNS:
        if pattern.search(prompt):
            matched.append(label)
    should_block = any(label in BLOCK_ON_MATCH for label in matched)
    return should_block, matched


async def screen_image(image_bytes: bytes, mime_type: str) -> dict:
    try:
        result = await inspect_image(image_bytes, mime_type)
        return {"blocked": result["action"] == "BLOCK", "action": result["action"], "risk_score": result["risk_score"]}
    except PELUnavailableError as exc:
        # Fail closed: an image we couldn't screen is treated as blocked
        # rather than silently passed through, consistent with the
        # fail-closed posture used throughout Layer 2 (guardrail_layer2's
        # cost guard does the same when its judge model is unreachable).
        return {"blocked": True, "action": "BLOCK", "risk_score": None, "error": str(exc)}


async def run_layer1(
    db: Session, pipeline_name: str, prompt: str, image_bytes: bytes | None = None, mime_type: str = "image/jpeg"
) -> Layer1Verdict:
    providers = {p.kind: p for p in provider_registry.get_providers_for_pipeline(db, pipeline_name)}
    checks_run: list[str] = []

    if "layer1_heuristic" in providers:
        checks_run.append("layer1_heuristic")
        should_block, matched = screen_text(prompt)
        if should_block:
            return Layer1Verdict(blocked=True, checks_run=checks_run, matched_patterns=matched)

    image_result = None
    if image_bytes is not None:
        if "layer1_image_nsfw_grpc" in providers:
            checks_run.append("layer1_image_nsfw_grpc")
            image_result = await screen_image(image_bytes, mime_type)
            if image_result["blocked"]:
                return Layer1Verdict(blocked=True, checks_run=checks_run, image_check=image_result)
        # else: an image provider isn't attached to this pipeline - the
        # image is simply not screened, not silently rejected. Whoever
        # manages the provider registry controls that trade-off.

    return Layer1Verdict(blocked=False, checks_run=checks_run, image_check=image_result)
