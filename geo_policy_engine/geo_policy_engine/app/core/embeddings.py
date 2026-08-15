"""
Thread-safe singleton around sentence-transformers/all-MiniLM-L6-v2.

Same rationale as guardrail_layer2/app/core/embeddings.py: encode() is
blocking and CPU-bound, so every call site here goes through
loop.run_in_executor rather than calling it directly inside an `async def`.
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
        if not texts:
            return np.zeros((0, self._dimension), dtype="float32")
        embeddings = self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.astype("float32")


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
