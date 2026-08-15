"""
Manages many independent, named policy packs (one per country/regime,
typically), each backed by its own FAISS index and metadata file.

This is the piece that makes the "pre-build embeddings, don't redo work"
requirement concrete: uploading or updating pack B never touches pack A's
index, on disk or in memory. Each pack's embeddings are computed exactly
once, at upload time, and every evaluation after that just searches the
already-built index - no re-embedding happens on the request path.

Concurrency model matches guardrail_layer2/app/core/vector_store.py: a
`threading.RLock` PER PACK (not one global lock) guards that pack's index +
metadata, since every method here is synchronous and meant to be invoked
from a worker thread via `loop.run_in_executor`. Per-pack locking means
evaluating against pack A and updating pack B can genuinely happen at the
same time - they don't contend with each other.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import faiss
import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.core.embeddings import EmbeddingModel

logger = logging.getLogger("geo_policy.pack_store")

ALLOW = 1
BLOCK = 0

_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def slugify_pack_id(raw: str) -> str:
    slug = _SLUG_RE.sub("_", raw.strip().lower()).strip("_")
    if not slug:
        raise ValueError("pack_id must contain at least one letter or digit")
    return slug


@dataclass
class PackEntry:
    text: str
    label: int
    source: Literal["csv", "pdf"]
    doc_ref: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PackMeta:
    pack_id: str
    display_name: str
    country_code: str | None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PolicyPack:
    """One country/regime's index. Every public method is synchronous and
    thread-safe via its own RLock - callers (the evaluator, the API routes)
    run these through an executor."""

    def __init__(self, meta: PackMeta, dimension: int, packs_dir: Path):
        self.meta = meta
        self._dimension = dimension
        self._dir = packs_dir / meta.pack_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.faiss"
        self._metadata_path = self._dir / "metadata.json"
        self._meta_path = self._dir / "pack.json"

        self._index: faiss.IndexFlatL2 | None = None
        self._entries: list[PackEntry] = []
        self._lock = threading.RLock()

    # -- persistence -----------------------------------------------------
    def load_from_disk(self) -> None:
        if self._index_path.exists() and self._metadata_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            self._entries = [PackEntry(**row) for row in json.loads(self._metadata_path.read_text())]
        if self._meta_path.exists():
            self.meta = PackMeta(**json.loads(self._meta_path.read_text()))

    def _persist_locked(self) -> None:
        if self._index is not None:
            faiss.write_index(self._index, str(self._index_path))
        self._metadata_path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))
        self._meta_path.write_text(json.dumps(asdict(self.meta), indent=2))

    # -- ingestion (sync, call via executor) ------------------------------
    def rebuild_from_csv_sync(self, texts: list[str], labels: list[int], source_name: str) -> None:
        with self._lock:
            new_index = faiss.IndexFlatL2(self._dimension)
            embedder = EmbeddingModel()
            new_index.add(embedder.encode_normalized(texts))
            self._index = new_index
            self._entries = [
                PackEntry(text=t, label=l, source="csv", doc_ref=source_name) for t, l in zip(texts, labels)
            ]
            self.meta.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_locked()

    def append_pdf_chunks_sync(self, chunks: list[str], source_name: str) -> int:
        with self._lock:
            embedder = EmbeddingModel()
            embeddings = embedder.encode_normalized(chunks)
            if self._index is None:
                self._index = faiss.IndexFlatL2(self._dimension)
            self._index.add(embeddings)
            self._entries = self._entries + [
                PackEntry(text=c, label=BLOCK, source="pdf", doc_ref=source_name) for c in chunks
            ]
            self.meta.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_locked()
            return self._index.ntotal

    def set_enabled_sync(self, enabled: bool) -> None:
        with self._lock:
            self.meta.enabled = enabled
            self.meta.updated_at = datetime.now(timezone.utc).isoformat()
            self._persist_locked()

    # -- search (sync, call via executor) ---------------------------------
    def search_one_sync(self, embedding: np.ndarray) -> tuple[float, PackEntry | None]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return float("inf"), None
            distances, indices = self._index.search(embedding.reshape(1, -1), 1)
            idx = int(indices[0][0])
            if idx == -1 or idx >= len(self._entries):
                return float("inf"), None
            return float(distances[0][0]), self._entries[idx]

    def stats(self) -> dict:
        with self._lock:
            return {
                "pack_id": self.meta.pack_id,
                "display_name": self.meta.display_name,
                "country_code": self.meta.country_code,
                "enabled": self.meta.enabled,
                "total_vectors": 0 if self._index is None else self._index.ntotal,
                "allow_entries": sum(1 for e in self._entries if e.label == ALLOW),
                "block_entries": sum(1 for e in self._entries if e.label == BLOCK),
                "created_at": self.meta.created_at,
                "updated_at": self.meta.updated_at,
            }


class MultiPackStore:
    """Owns the whole collection of packs. Adding/updating pack B never
    acquires pack A's lock, so they don't block each other."""

    def __init__(self, embedding_model: EmbeddingModel, packs_dir: Path):
        self._embedding_model = embedding_model
        self._dimension = embedding_model.dimension
        self._packs_dir = packs_dir
        self._packs_dir.mkdir(parents=True, exist_ok=True)
        self._packs: dict[str, PolicyPack] = {}
        self._registry_lock = threading.RLock()  # guards the dict itself, not pack internals
        self._discover_existing_packs()

    def _discover_existing_packs(self) -> None:
        for child in self._packs_dir.iterdir():
            if not child.is_dir():
                continue
            meta_path = child / "pack.json"
            if not meta_path.exists():
                continue
            meta = PackMeta(**json.loads(meta_path.read_text()))
            pack = PolicyPack(meta, self._dimension, self._packs_dir)
            pack.load_from_disk()
            self._packs[meta.pack_id] = pack
        logger.info("Discovered %d existing policy pack(s) on disk", len(self._packs))

    def _get_or_create_pack(self, pack_id: str, display_name: str, country_code: str | None) -> PolicyPack:
        with self._registry_lock:
            if pack_id not in self._packs:
                meta = PackMeta(pack_id=pack_id, display_name=display_name, country_code=country_code)
                self._packs[pack_id] = PolicyPack(meta, self._dimension, self._packs_dir)
            return self._packs[pack_id]

    def get_pack(self, pack_id: str) -> PolicyPack | None:
        with self._registry_lock:
            return self._packs.get(pack_id)

    def delete_pack(self, pack_id: str) -> bool:
        import shutil

        with self._registry_lock:
            pack = self._packs.pop(pack_id, None)
        if pack is None:
            return False
        shutil.rmtree(pack._dir, ignore_errors=True)
        return True

    def list_packs(self) -> list[dict]:
        with self._registry_lock:
            packs = list(self._packs.values())
        return [p.stats() for p in packs]

    def enabled_packs(self) -> list[PolicyPack]:
        with self._registry_lock:
            packs = list(self._packs.values())
        return [p for p in packs if p.meta.enabled]

    # -- ingestion entry points (sync, call via executor) ------------------
    def upload_csv_sync(self, pack_id: str, display_name: str, country_code: str | None, csv_bytes: bytes, source_name: str) -> dict:
        texts, labels, skipped = _parse_policy_csv(csv_bytes)
        if not texts:
            raise ValueError("CSV contained no valid (prompt, allow/block) rows")
        pack = self._get_or_create_pack(pack_id, display_name, country_code)
        pack.rebuild_from_csv_sync(texts, labels, source_name)
        stats = pack.stats()
        stats["skipped_rows"] = skipped
        return stats

    def upload_pdf_sync(self, pack_id: str, display_name: str, country_code: str | None, pdf_bytes: bytes, source_name: str) -> dict:
        chunks = _load_and_split_pdf(pdf_bytes)
        if not chunks:
            raise ValueError("No extractable text chunks found in PDF")
        pack = self._get_or_create_pack(pack_id, display_name, country_code)
        total = pack.append_pdf_chunks_sync(chunks, source_name)
        stats = pack.stats()
        stats["appended_chunks"] = len(chunks)
        stats["total_vectors"] = total
        return stats


def _parse_policy_csv(csv_bytes: bytes) -> tuple[list[str], list[int], int]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], [], 0
    normalized = {f.strip().lower(): f for f in reader.fieldnames}
    prompt_key = normalized.get("prompt")
    label_key = normalized.get("allow/block") or normalized.get("allow_block") or normalized.get("label")
    if prompt_key is None or label_key is None:
        raise ValueError("CSV must contain a 'prompt' column and an 'allow/block' (or 'label') column")

    texts, labels, skipped = [], [], 0
    for row in reader:
        prompt_value = (row.get(prompt_key) or "").strip()
        label_raw = (row.get(label_key) or "").strip()
        if not prompt_value or label_raw not in {"0", "1"}:
            skipped += 1
            continue
        texts.append(prompt_value)
        labels.append(int(label_raw))
    return texts, labels, skipped


def _load_and_split_pdf(pdf_bytes: bytes) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        documents = PyPDFLoader(tmp.name).load()
    chunks = []
    for doc in documents:
        for split in splitter.split_text(doc.page_content):
            cleaned = split.strip()
            if cleaned:
                chunks.append(cleaned)
    return chunks
