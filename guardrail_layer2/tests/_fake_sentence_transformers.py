"""
A deterministic, dependency-free stand-in for sentence-transformers, used
ONLY by the test suite so it doesn't need to download torch + model weights
to exercise the real app.core.embeddings / app.core.vector_store code
paths. It reproduces the exact surface those modules call:

    SentenceTransformer(model_name)
    .get_sentence_embedding_dimension() -> int
    .encode(texts, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False) -> np.ndarray

Embeddings are a hashed bag-of-words: each token deterministically seeds a
pseudo-random unit vector, and a text's embedding is the normalized sum of
its tokens' vectors. This gives semantically-similar-ish behavior (texts
sharing words end up closer together) without any ML dependency, which is
enough to validate indexing, search, and short-circuit logic - it is NOT a
substitute for evaluating real embedding quality.
"""

from __future__ import annotations

import hashlib

import numpy as np

_DIM = 32


def _token_vector(token: str) -> np.ndarray:
    seed = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=_DIM)
    return vec


class SentenceTransformer:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def get_sentence_embedding_dimension(self) -> int:
        return _DIM

    def encode(
        self,
        texts,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ):
        vectors = []
        for text in texts:
            tokens = text.lower().split()
            if not tokens:
                vectors.append(np.zeros(_DIM))
                continue
            summed = np.sum([_token_vector(t) for t in tokens], axis=0)
            vectors.append(summed)
        arr = np.array(vectors, dtype="float32")
        if normalize_embeddings:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            arr = arr / norms
        return arr
