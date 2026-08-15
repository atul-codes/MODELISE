"""
In-memory FAISS index (IndexFlatL2) over normalized MiniLM embeddings, with
parallel metadata describing each vector's origin and allow/block label.

Concurrency model
------------------
All FAISS/metadata mutation and search is guarded by a `threading.RLock`
(not an asyncio.Lock) because every method in this class is synchronous and
is meant to be invoked from a worker thread via `loop.run_in_executor(...)`,
never directly from the event loop. A `threading.RLock` is what actually
provides mutual exclusion across those real OS threads; an asyncio.Lock
would not, since it only coordinates coroutines on a single event loop.

Reads (search_one_sync) hold the lock only for the few milliseconds the
native FAISS call takes, so concurrent chunk evaluations barely contend
with each other. Writes (CSV rebuild / PDF append) replace `self._metadata`
with a new list object rather than mutating in place, and swap `self._index`
to a fully-built new index before releasing the lock, so a reader can never
observe a half-updated state.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import faiss
import numpy as np
from fastapi import Request
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.core.embeddings import EmbeddingModel

logger = logging.getLogger("modelise.vector_store")

ALLOW = 1
BLOCK = 0


@dataclass
class PolicyEntry:
    text: str
    label: int  # 1 = ALLOW, 0 = BLOCK
    source: Literal["csv", "pdf"]
    doc_ref: str

    def to_dict(self) -> dict:
        return asdict(self)


class PolicyVectorStore:
    def __init__(self, embedding_model: EmbeddingModel, index_dir: Path):
        self._embedding_model = embedding_model
        self._dimension = embedding_model.dimension
        self._index_dir = index_dir
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._index_dir / "policy.index"
        self._metadata_path = self._index_dir / "policy_metadata.json"

        self._index: faiss.IndexFlatL2 | None = None
        self._metadata: list[PolicyEntry] = []
        self._lock = threading.RLock()

        self._load_from_disk()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load_from_disk(self) -> None:
        if self._index_path.exists() and self._metadata_path.exists():
            try:
                index = faiss.read_index(str(self._index_path))
                with open(self._metadata_path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                metadata = [PolicyEntry(**row) for row in raw]
                self._index = index
                self._metadata = metadata
                logger.info(
                    "Loaded persisted policy index: %d vectors, %d metadata rows",
                    index.ntotal,
                    len(metadata),
                )
            except Exception:
                logger.exception("Failed to load persisted policy index; starting empty")
                self._index = None
                self._metadata = []

    def _persist_locked(self) -> None:
        """Caller must already hold self._lock."""
        if self._index is not None:
            faiss.write_index(self._index, str(self._index_path))
        with open(self._metadata_path, "w", encoding="utf-8") as fh:
            json.dump([entry.to_dict() for entry in self._metadata], fh, indent=2)

    # ------------------------------------------------------------------ #
    # Ingestion (synchronous - callers must run these via run_in_executor)
    # ------------------------------------------------------------------ #
    def rebuild_from_csv_sync(self, csv_bytes: bytes, source_name: str) -> dict:
        """CSV upload INITIALIZES OR OVERWRITES the base policy index, per
        spec. Any previously-appended PDF chunks are replaced along with it -
        CSV establishes a new base; PDFs layer on top of whatever base is
        currently active."""
        rows, skipped = self._parse_policy_csv(csv_bytes)
        if not rows:
            raise ValueError("CSV contained no valid (prompt, allow/block) rows")

        texts = [r[0] for r in rows]
        labels = [r[1] for r in rows]
        embeddings = self._embedding_model.encode_normalized(texts)

        new_index = faiss.IndexFlatL2(self._dimension)
        new_index.add(embeddings)
        new_metadata = [
            PolicyEntry(text=t, label=l, source="csv", doc_ref=source_name) for t, l in zip(texts, labels)
        ]

        with self._lock:
            self._index = new_index
            self._metadata = new_metadata
            self._persist_locked()

        return {
            "indexed_rows": len(rows),
            "skipped_rows": skipped,
            "allow_count": sum(1 for l in labels if l == ALLOW),
            "block_count": sum(1 for l in labels if l == BLOCK),
        }

    def append_pdf_chunks_sync(self, pdf_bytes: bytes, source_name: str) -> dict:
        """PDF upload APPENDS to the active index without rebuilding.
        Every chunk is forced to label=0 (BLOCK), since PDFs represent
        compliance/restriction documentation per spec."""
        chunks = self._load_and_split_pdf(pdf_bytes)
        if not chunks:
            raise ValueError("No extractable text chunks found in PDF")

        embeddings = self._embedding_model.encode_normalized(chunks)
        new_entries = [PolicyEntry(text=c, label=BLOCK, source="pdf", doc_ref=source_name) for c in chunks]

        with self._lock:
            if self._index is None:
                self._index = faiss.IndexFlatL2(self._dimension)
            self._index.add(embeddings)
            self._metadata = self._metadata + new_entries  # new list -> safe for concurrent readers
            self._persist_locked()
            total = self._index.ntotal

        return {"appended_chunks": len(chunks), "total_vectors": total}

    def _parse_policy_csv(self, csv_bytes: bytes) -> tuple[list[tuple[str, int]], int]:
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            return [], 0

        normalized_fields = {f.strip().lower(): f for f in reader.fieldnames}
        prompt_key = normalized_fields.get("prompt")
        label_key = (
            normalized_fields.get("allow/block")
            or normalized_fields.get("allow_block")
            or normalized_fields.get("label")
        )
        if prompt_key is None or label_key is None:
            raise ValueError(
                "CSV must contain a 'prompt' column and an 'allow/block' "
                "(or 'label') column with values 1 (ALLOW) or 0 (BLOCK)"
            )

        rows: list[tuple[str, int]] = []
        skipped = 0
        for raw_row in reader:
            prompt_value = (raw_row.get(prompt_key) or "").strip()
            label_raw = (raw_row.get(label_key) or "").strip()
            if not prompt_value or label_raw not in {"0", "1"}:
                skipped += 1
                continue
            rows.append((prompt_value, int(label_raw)))
        return rows, skipped

    def _load_and_split_pdf(self, pdf_bytes: bytes) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        # PyPDFLoader requires a filesystem path, so the upload is staged to
        # a temp file for the duration of the parse only.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            loader = PyPDFLoader(tmp.name)
            documents = loader.load()

        chunks: list[str] = []
        for doc in documents:
            for split in splitter.split_text(doc.page_content):
                cleaned = split.strip()
                if cleaned:
                    chunks.append(cleaned)
        return chunks

    # ------------------------------------------------------------------ #
    # Search (synchronous - callers must run these via run_in_executor)
    # ------------------------------------------------------------------ #
    def embed_sync(self, texts: list[str]) -> np.ndarray:
        return self._embedding_model.encode_normalized(texts)

    def search_one_sync(self, embedding: np.ndarray) -> tuple[float, PolicyEntry | None]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return float("inf"), None
            distances, indices = self._index.search(embedding.reshape(1, -1), 1)
            idx = int(indices[0][0])
            if idx == -1 or idx >= len(self._metadata):
                return float("inf"), None
            return float(distances[0][0]), self._metadata[idx]

    # ------------------------------------------------------------------ #
    # Misc
    # ------------------------------------------------------------------ #
    @property
    def total_vectors(self) -> int:
        with self._lock:
            return 0 if self._index is None else self._index.ntotal

    def stats(self) -> dict:
        with self._lock:
            allow_count = sum(1 for e in self._metadata if e.label == ALLOW)
            block_count = sum(1 for e in self._metadata if e.label == BLOCK)
            return {
                "total_vectors": 0 if self._index is None else self._index.ntotal,
                "allow_entries": allow_count,
                "block_entries": block_count,
                "csv_entries": sum(1 for e in self._metadata if e.source == "csv"),
                "pdf_entries": sum(1 for e in self._metadata if e.source == "pdf"),
            }


def get_vector_store(request: Request) -> PolicyVectorStore:
    """FastAPI dependency accessor. The store instance itself lives on
    `app.state`, created once in main.py's lifespan handler and shared
    across all requests for the life of the process."""
    return request.app.state.vector_store
