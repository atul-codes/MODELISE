"""
Gate 2: Concurrent chunking & min-distance worst-case policy engine.

`evaluate_policy` splits the incoming prompt with RecursiveCharacterTextSplitter,
then evaluates every chunk against the FAISS index concurrently. Both the
embedding call and the FAISS search run inside a ThreadPoolExecutor (passed
in from app.state, see main.py) via `loop.run_in_executor` - this is what
makes the concurrency real rather than cosmetic. An `async def` function
that calls a blocking numpy/FAISS routine directly still blocks the event
loop for the whole process; wrapping the same call in an executor lets
multiple chunks' embedding+search work happen in parallel OS threads while
the event loop keeps serving other requests.

The short-circuit is implemented with `asyncio.as_completed` plus explicit
`task.cancel()`: as soon as any chunk resolves to a BLOCK match under the
threshold, the loop breaks and every still-pending chunk task is cancelled.
Distances are never averaged - a single bad chunk blocks the whole prompt.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.core.vector_store import BLOCK, PolicyEntry, PolicyVectorStore

logger = logging.getLogger("modelise.evaluator")


@dataclass
class ChunkOutcome:
    chunk: str
    distance: float
    matched_entry: PolicyEntry | None


@dataclass
class PolicyEvaluationResult:
    blocked: bool
    chunks_evaluated: int
    total_chunks: int
    matched_chunk: str | None = None
    matched_distance: float | None = None
    matched_doc_ref: str | None = None
    matched_source: str | None = None


def split_prompt(prompt: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = [c.strip() for c in splitter.split_text(prompt) if c.strip()]
    return chunks or ([prompt.strip()] if prompt.strip() else [])


async def evaluate_policy(
    prompt: str,
    store: PolicyVectorStore,
    threshold: float,
    executor: ThreadPoolExecutor,
) -> PolicyEvaluationResult:
    chunks = split_prompt(prompt)
    if store.total_vectors == 0:
        logger.warning("Policy index is empty - no BLOCK/ALLOW rules loaded, allowing by default")
        return PolicyEvaluationResult(blocked=False, chunks_evaluated=0, total_chunks=len(chunks))

    loop = asyncio.get_running_loop()

    async def _evaluate_chunk(chunk: str) -> ChunkOutcome:
        embedding = await loop.run_in_executor(executor, store.embed_sync, [chunk])
        distance, matched_entry = await loop.run_in_executor(executor, store.search_one_sync, embedding[0])
        return ChunkOutcome(chunk=chunk, distance=distance, matched_entry=matched_entry)

    tasks = [asyncio.ensure_future(_evaluate_chunk(chunk)) for chunk in chunks]
    evaluated = 0
    blocked_outcome: ChunkOutcome | None = None

    try:
        for finished in asyncio.as_completed(tasks):
            outcome = await finished
            evaluated += 1
            entry = outcome.matched_entry
            if entry is not None and entry.label == BLOCK and outcome.distance < threshold:
                blocked_outcome = outcome
                break
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    if blocked_outcome is not None:
        entry = blocked_outcome.matched_entry
        assert entry is not None
        return PolicyEvaluationResult(
            blocked=True,
            chunks_evaluated=evaluated,
            total_chunks=len(chunks),
            matched_chunk=blocked_outcome.chunk,
            matched_distance=blocked_outcome.distance,
            matched_doc_ref=entry.doc_ref,
            matched_source=entry.source,
        )

    return PolicyEvaluationResult(blocked=False, chunks_evaluated=evaluated, total_chunks=len(chunks))
