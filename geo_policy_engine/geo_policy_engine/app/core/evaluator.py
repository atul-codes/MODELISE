"""
Evaluates a prompt against every ENABLED policy pack at once. Chunking
happens once per prompt; each (chunk, pack) pair is then a separate
concurrent task. Both embedding and the FAISS search run inside a
ThreadPoolExecutor via loop.run_in_executor, same reasoning as
guardrail_layer2/app/core/evaluator.py - blocking calls inside `async def`
still block the whole event loop otherwise.

Short-circuit is global across packs, not just within one pack: the moment
ANY (chunk, pack) pair matches a BLOCK entry under that pack's threshold,
every other still-pending task (in any pack) is cancelled and evaluation
returns immediately.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.core.pack_store import BLOCK, MultiPackStore, PackEntry, PolicyPack

logger = logging.getLogger("geo_policy.evaluator")


@dataclass
class GeoEvaluationResult:
    blocked: bool
    packs_checked: list[str]
    chunks_evaluated: int
    matched_chunk: str | None = None
    matched_distance: float | None = None
    matched_pack_id: str | None = None
    matched_doc_ref: str | None = None


def split_prompt(prompt: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    chunks = [c.strip() for c in splitter.split_text(prompt) if c.strip()]
    return chunks or ([prompt.strip()] if prompt.strip() else [])


async def evaluate_against_packs(
    prompt: str,
    store: MultiPackStore,
    executor: ThreadPoolExecutor,
    threshold: float,
    pack_ids: list[str] | None = None,
) -> GeoEvaluationResult:
    if pack_ids:
        packs = [p for p in (store.get_pack(pid) for pid in pack_ids) if p is not None and p.meta.enabled]
    else:
        packs = store.enabled_packs()

    packs_checked = [p.meta.pack_id for p in packs]
    if not packs:
        return GeoEvaluationResult(blocked=False, packs_checked=[], chunks_evaluated=0)

    chunks = split_prompt(prompt)
    loop = asyncio.get_running_loop()

    @dataclass
    class _Outcome:
        chunk: str
        distance: float
        entry: PackEntry | None
        pack: PolicyPack

    # Embedding happens per-chunk-per-pack; packs share nothing with each
    # other so this fans out cleanly across the executor's worker threads.
    async def _evaluate_chunk_pack(chunk: str, pack: PolicyPack) -> "_Outcome":
        embed_fn = store._embedding_model.encode_normalized  # already thread-safe, read-only
        embedding = await loop.run_in_executor(executor, embed_fn, [chunk])
        distance, entry = await loop.run_in_executor(executor, pack.search_one_sync, embedding[0])
        return _Outcome(chunk=chunk, distance=distance, entry=entry, pack=pack)

    tasks = [asyncio.ensure_future(_evaluate_chunk_pack(chunk, pack)) for chunk in chunks for pack in packs]
    evaluated = 0
    blocked_outcome: "_Outcome | None" = None

    try:
        for finished in asyncio.as_completed(tasks):
            outcome = await finished
            evaluated += 1
            if outcome.entry is not None and outcome.entry.label == BLOCK and outcome.distance < threshold:
                blocked_outcome = outcome
                break
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    if blocked_outcome is not None:
        return GeoEvaluationResult(
            blocked=True,
            packs_checked=packs_checked,
            chunks_evaluated=evaluated,
            matched_chunk=blocked_outcome.chunk,
            matched_distance=blocked_outcome.distance,
            matched_pack_id=blocked_outcome.pack.meta.pack_id,
            matched_doc_ref=blocked_outcome.entry.doc_ref if blocked_outcome.entry else None,
        )

    return GeoEvaluationResult(blocked=False, packs_checked=packs_checked, chunks_evaluated=evaluated)
