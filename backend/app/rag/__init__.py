"""RAG knowledge base for AI-Structure-FEA (P1-04b).

Replaces the audited-and-flagged P1-04a corpus with a clean rebuild
using BGE-M3 embeddings + ChromaDB persistence. Five corpus sources
documented in `backend/app/rag/sources/README.md`.

Public API:
    Document       — schema for a corpus document
    Chunk          — schema for an embedded chunk
    Embedder       — abstract embedder; MockEmbedder ships for tests;
                     BgeM3Embedder is the production implementation
                     gated behind `[rag]` optional dep group.
    VectorStore    — abstract retrieval store; MemoryVectorStore for
                     tests; ChromaVectorStore for production.
    KnowledgeBase  — orchestrator (ingest, query, persist).
"""

from backend.app.rag.schemas import Chunk, Document, RetrievalResult
from backend.app.rag.embedder import Embedder, MockEmbedder
from backend.app.rag.store import MemoryVectorStore, VectorStore
from backend.app.rag.knowledge_base import KnowledgeBase

__all__ = [
    "Chunk",
    "Document",
    "RetrievalResult",
    "Embedder",
    "MockEmbedder",
    "VectorStore",
    "MemoryVectorStore",
    "KnowledgeBase",
]
