"""Embedders for the RAG knowledge base (P1-04b).

Public API:
    Embedder         — abstract base
    MockEmbedder     — deterministic-hash embedding for tests
    BgeM3Embedder    — production via sentence-transformers (lazy import,
                       requires `[rag]` extra)
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


class Embedder(ABC):
    """Abstract embedder."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """Embedding dimensionality."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier for the embedding model (used in store metadata)."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one dense vector per input text."""


class MockEmbedder(Embedder):
    """Deterministic mock embedder using SHA-256 of the input text.

    Same text → same vector; different text → orthogonal-enough
    vectors for unit tests. NOT suitable for real retrieval — use
    BgeM3Embedder in production.
    """

    def __init__(self, dim: int = 32) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return f"mock-sha256@{self._dim}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            # Repeat-and-trim digest bytes to fill `dim` floats; normalize to [-1, 1].
            vec: list[float] = []
            i = 0
            while len(vec) < self._dim:
                b = digest[i % len(digest)]
                vec.append((b - 128) / 128.0)
                i += 1
            out.append(vec[: self._dim])
        return out


class BgeM3Embedder(Embedder):
    """BGE-M3 via sentence-transformers (lazy import).

    Requires `pip install -e ".[rag]"` (sentence-transformers + torch).
    Picked per Notion task next-action: "P1-04b rebuild begins on
    BGE-M3". Multilingual, supports Chinese + English, 1024-dim
    dense + sparse + colbert outputs. We use dense-only for now.
    """

    MODEL_NAME = "BAAI/bge-m3"
    DIM = 1024

    def __init__(self, model_path: str | None = None) -> None:
        # Lazy import — sentence-transformers is heavy and optional.
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:
            raise ImportError(
                "BgeM3Embedder requires sentence-transformers. "
                "Install with: pip install -e \".[rag]\""
            ) from e

        self._model = SentenceTransformer(model_path or self.MODEL_NAME)

    @property
    def dim(self) -> int:
        return self.DIM

    @property
    def model_id(self) -> str:
        return f"bge-m3@{self.DIM}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        emb = self._model.encode(texts, normalize_embeddings=True)
        return emb.tolist() if hasattr(emb, "tolist") else [list(v) for v in emb]
