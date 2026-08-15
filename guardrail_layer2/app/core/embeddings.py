"""
Thread-safe singleton around sentence-transformers/all-MiniLM-L6-v2.

SentenceTransformer.encode() is a blocking, CPU-bound call. It is NOT safe
to call directly from inside an `async def` route or coroutine - doing so
blocks the single asyncio event loop for every in-flight request on the
service, not just the caller. Every call site in this codebase invokes
`encode_normalized` through `loop.run_in_executor(...)` (see
core/vector_store.py and core/evaluator.py) so the CPU work happens on a
worker thread while the event loop stays free to handle other requests.
"""

from __future__ import annotations

import threading
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingModel:
    _instance: "EmbeddingModel | None" = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "EmbeddingModel":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
                    instance._dimension = instance._model.get_sentence_embedding_dimension()
                    cls._instance = instance
        return cls._instance

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode_normalized(self, texts: list[str]) -> np.ndarray:
        """Synchronous and blocking by design - call only from a worker
        thread via loop.run_in_executor. Returns L2-normalized float32
        vectors of shape (len(texts), dimension)."""
        if not texts:
            return np.zeros((0, self._dimension), dtype="float32")
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.astype("float32")


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
