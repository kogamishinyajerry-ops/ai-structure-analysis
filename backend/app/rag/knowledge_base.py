"""KnowledgeBase orchestrator for the RAG pipeline (P1-04b).

End-to-end ingest → embed → store → query loop. Composes:
    Embedder + VectorStore + chunker
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.rag.embedder import Embedder
from app.rag.schemas import Chunk, Document, RetrievalResult
from app.rag.store import VectorStore


@dataclass(frozen=True)
class IngestStats:
    documents_seen: int
    chunks_written: int
    chunks_per_doc_avg: float


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[str]:
    """Simple character-based chunker with overlap.

    Real RAG would use sentence/paragraph boundaries (langchain's
    RecursiveCharacterTextSplitter etc.); this is the minimum viable
    splitter that's deterministic and dependency-free.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    # R2 (post Codex R1 HIGH): stop emitting once the current window
    # has reached EOF. Without this, `chunk_size=40, overlap=10` on a
    # 100-char input emitted a 4th chunk fully contained in the 3rd
    # (text[60:100] vs text[90:130]→[90:100]). With overlap close to
    # chunk_size, the bloat became O(text_len/step) duplicate chunks.
    chunks: list[str] = []
    step = chunk_size - overlap
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        if i + chunk_size >= len(text):
            break
        i += step
    return chunks


class KnowledgeBase:
    """Glue between embedder + store + chunker."""

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        *,
        chunk_size: int = 800,
        overlap: int = 100,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._chunk_size = chunk_size
        self._overlap = overlap

    @property
    def embedder_id(self) -> str:
        return self._embedder.model_id

    def ingest(self, documents: Iterable[Document]) -> IngestStats:
        docs = list(documents)
        all_chunks: list[Chunk] = []

        for doc in docs:
            pieces = chunk_text(
                doc.text, chunk_size=self._chunk_size, overlap=self._overlap
            )
            for idx, piece in enumerate(pieces):
                all_chunks.append(
                    Chunk(
                        chunk_id=f"{doc.doc_id}:{idx}",
                        doc_id=doc.doc_id,
                        source=doc.source,
                        text=piece,
                        chunk_index=idx,
                        # R2 (post Codex R1 MEDIUM): propagate title +
                        # metadata so the chunk carries citation-quality
                        # provenance through the store layer.
                        title=doc.title,
                        metadata=doc.metadata,
                        embedding=None,
                    )
                )

        if not all_chunks:
            return IngestStats(documents_seen=len(docs), chunks_written=0, chunks_per_doc_avg=0.0)

        # Batch-embed for efficiency.
        embeddings = self._embedder.embed([c.text for c in all_chunks])
        if len(embeddings) != len(all_chunks):
            raise RuntimeError(
                f"embedder returned {len(embeddings)} vectors for {len(all_chunks)} chunks"
            )
        embedded = [
            c.model_copy(update={"embedding": emb})
            for c, emb in zip(all_chunks, embeddings)
        ]

        written = self._store.upsert(embedded)
        return IngestStats(
            documents_seen=len(docs),
            chunks_written=written,
            chunks_per_doc_avg=written / len(docs) if docs else 0.0,
        )

    def query(
        self,
        question: str,
        k: int = 5,
        source_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Embed the question and retrieve top-k chunks."""
        if not question.strip():
            return []
        embedding = self._embedder.embed([question])[0]
        return self._store.query(embedding, k=k, source_filter=source_filter)
