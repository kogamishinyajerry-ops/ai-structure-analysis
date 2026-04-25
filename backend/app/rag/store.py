"""Vector stores for the RAG knowledge base (P1-04b).

Public API:
    VectorStore         — abstract retrieval store
    MemoryVectorStore   — in-memory cosine-similarity (tests + small corpora)
    ChromaVectorStore   — persistent via chromadb (lazy import; needs `[rag]`)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.rag.schemas import Chunk, RetrievalResult


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"dim mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore(ABC):
    """Abstract vector store."""

    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> int:
        """Insert or update chunks; return count written."""

    @abstractmethod
    def query(
        self, embedding: list[float], k: int, source_filter: str | None = None
    ) -> list[RetrievalResult]:
        """Top-k retrieval by similarity to `embedding`."""

    @abstractmethod
    def count(self) -> int:
        """Total chunk count currently stored."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all chunks (testing convenience)."""


class MemoryVectorStore(VectorStore):
    """In-memory store. O(N) query — fine for tests + small corpora."""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}

    def upsert(self, chunks: list[Chunk]) -> int:
        for c in chunks:
            if c.embedding is None:
                raise ValueError(
                    f"chunk {c.chunk_id} has no embedding; embed before upserting"
                )
            self._chunks[c.chunk_id] = c
        return len(chunks)

    def query(
        self, embedding: list[float], k: int, source_filter: str | None = None
    ) -> list[RetrievalResult]:
        if k <= 0:
            return []
        candidates = (
            [c for c in self._chunks.values() if c.source == source_filter]
            if source_filter
            else list(self._chunks.values())
        )
        scored = [(c, _cosine(embedding, c.embedding or [])) for c in candidates]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [
            RetrievalResult(chunk=c, score=s, rank=i)
            for i, (c, s) in enumerate(scored[:k])
        ]

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()


class ChromaVectorStore(VectorStore):
    """Persistent vector store via chromadb (lazy import).

    Requires `pip install -e ".[rag]"` (chromadb).
    """

    def __init__(self, persist_dir: Path, collection_name: str = "ai_fea_kb") -> None:
        try:
            import chromadb  # type: ignore
        except ImportError as e:
            raise ImportError(
                "ChromaVectorStore requires chromadb. "
                "Install with: pip install -e \".[rag]\""
            ) from e

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        for c in chunks:
            if c.embedding is None:
                raise ValueError(f"chunk {c.chunk_id} has no embedding")
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "source": c.source,
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ],
        )
        return len(chunks)

    def query(
        self, embedding: list[float], k: int, source_filter: str | None = None
    ) -> list[RetrievalResult]:
        if k <= 0:
            return []
        where = {"source": source_filter} if source_filter else None
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
        )
        out: list[RetrievalResult] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        for i, (cid, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            chunk = Chunk(
                chunk_id=cid,
                doc_id=str(meta.get("doc_id", "")),
                source=str(meta.get("source", "")),
                text=doc,
                chunk_index=int(meta.get("chunk_index", 0)),
                embedding=None,  # chromadb doesn't return embeddings on query
            )
            # chromadb returns distance; convert to cosine similarity (1-distance)
            score = max(0.0, 1.0 - float(dist))
            out.append(RetrievalResult(chunk=chunk, score=score, rank=i))
        return out

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        # chromadb doesn't have a single-call clear; delete + recreate collection.
        name = self._collection.name
        self._client.delete_collection(name=name)
        self._collection = self._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )
