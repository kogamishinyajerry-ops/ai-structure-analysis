"""Pydantic v2 schemas for the RAG knowledge base (P1-04b).

Models are frozen + extra=forbid per Golden Rule #7 (schema-first).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """One source document before chunking + embedding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str = Field(..., description="stable id, e.g. 'calculix-manual-ch3'")
    source: str = Field(..., description="corpus source label (one of the 5 sources)")
    title: str
    text: str = Field(..., description="full document text (utf-8)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """One chunk of a Document, ready for embedding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(
        ..., description="`{doc_id}:{chunk_index}` for stable retrieval cross-ref"
    )
    doc_id: str
    source: str
    text: str
    chunk_index: int = Field(..., ge=0)
    embedding: list[float] | None = Field(
        default=None,
        description="dense embedding; None until embedder runs",
    )


class RetrievalResult(BaseModel):
    """One retrieved chunk + similarity score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: Chunk
    score: float = Field(..., description="similarity (cosine, higher is better)")
    rank: int = Field(..., ge=0)
