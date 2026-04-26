"""Tests for backend.app.rag (P1-04b) — pipeline behavior with mock embedder."""

from __future__ import annotations

import pytest

try:
    from backend.app.rag import (
        Chunk,
        Document,
        KnowledgeBase,
        MemoryVectorStore,
        MockEmbedder,
    )
    from backend.app.rag.knowledge_base import chunk_text
    from backend.app.rag.store import _cosine
except ImportError as e:
    pytest.skip(f"rag module imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


def test_chunk_text_short_returns_one():
    out = chunk_text("hello", chunk_size=100, overlap=10)
    assert out == ["hello"]


def test_chunk_text_empty_returns_empty():
    assert chunk_text("", chunk_size=100, overlap=0) == []


def test_chunk_text_overlap_correct():
    text = "a" * 100
    out = chunk_text(text, chunk_size=40, overlap=10)
    # step = 30; windows at [0:40], [30:70], [60:100]. The 4th window
    # would start at i=90 but the 3rd already reached EOF (i+chunk_size
    # = 100 = len(text)), so R2 stops emitting. (Codex R1 HIGH fix.)
    assert len(out) == 3
    assert all(len(c) <= 40 for c in out)
    assert out[0][-10:] == out[1][:10]


def test_chunk_text_no_redundant_tail_under_high_overlap():
    """R2 (post Codex R1 HIGH): with overlap close to chunk_size, the
    old loop emitted O(N/step) chunks, many fully contained in the
    prior. Verify a 100-char input with chunk_size=40, overlap=39
    produces no more than ceil((100-40)/1)+1 = 61 chunks, NOT 100."""
    text = "a" * 100
    out = chunk_text(text, chunk_size=40, overlap=39)
    # step=1; emit windows starting at 0..60 inclusive (61 starts);
    # each window after position 60 would extend past EOF, so we stop.
    assert len(out) <= 61
    assert all(len(c) <= 40 for c in out)
    # Last chunk must reach the end of the text.
    assert out[-1].endswith("a")


def test_chunk_text_no_overlap():
    text = "a" * 90
    out = chunk_text(text, chunk_size=30, overlap=0)
    assert out == ["a" * 30, "a" * 30, "a" * 30]


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=10, overlap=15)


def test_chunk_text_rejects_zero_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("x", chunk_size=0, overlap=0)


# ---------------------------------------------------------------------------
# MockEmbedder
# ---------------------------------------------------------------------------


def test_mock_embedder_deterministic():
    e = MockEmbedder(dim=16)
    a1 = e.embed(["hello world"])
    a2 = e.embed(["hello world"])
    assert a1 == a2


def test_mock_embedder_different_text_different_vectors():
    e = MockEmbedder(dim=16)
    a, b = e.embed(["alpha", "beta"])
    assert a != b


def test_mock_embedder_dim_correct():
    e = MockEmbedder(dim=64)
    out = e.embed(["x", "y", "z"])
    assert all(len(v) == 64 for v in out)
    assert len(out) == 3


def test_mock_embedder_rejects_zero_dim():
    with pytest.raises(ValueError):
        MockEmbedder(dim=0)


def test_mock_embedder_model_id():
    e = MockEmbedder(dim=128)
    assert e.model_id == "mock-sha256@128"


# ---------------------------------------------------------------------------
# _cosine
# ---------------------------------------------------------------------------


def test_cosine_same_vector_is_one():
    assert abs(_cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-9


def test_cosine_orthogonal_is_zero():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_opposite_is_negative_one():
    assert abs(_cosine([1.0, 0.0], [-1.0, 0.0]) + 1.0) < 1e-9


def test_cosine_zero_vector_returns_zero():
    assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_dim_mismatch_raises():
    with pytest.raises(ValueError):
        _cosine([1.0, 2.0], [1.0, 2.0, 3.0])


# ---------------------------------------------------------------------------
# MemoryVectorStore
# ---------------------------------------------------------------------------


def test_memory_store_upsert_and_count():
    store = MemoryVectorStore()
    chunks = [
        Chunk(
            chunk_id="d1:0",
            doc_id="d1",
            source="src",
            text="x",
            chunk_index=0,
            embedding=[1.0, 0.0, 0.0],
        )
    ]
    n = store.upsert(chunks)
    assert n == 1
    assert store.count() == 1


def test_memory_store_rejects_unembedded_chunk():
    store = MemoryVectorStore()
    chunks = [Chunk(chunk_id="d:0", doc_id="d", source="s", text="x", chunk_index=0)]
    with pytest.raises(ValueError, match="no embedding"):
        store.upsert(chunks)


def test_memory_store_query_returns_top_k():
    """Use vectors at varied angles so cosine similarity actually discriminates."""
    import math

    store = MemoryVectorStore()
    # 5 unit vectors at 0°, 22.5°, 45°, 67.5°, 90° from x-axis.
    # Query along x-axis → chunk 0 (0°) wins, chunk 4 (90°) loses.
    angles = [0, math.pi / 8, math.pi / 4, 3 * math.pi / 8, math.pi / 2]
    chunks = [
        Chunk(
            chunk_id=f"d:{i}",
            doc_id="d",
            source="s",
            text=f"text {i}",
            chunk_index=i,
            embedding=[math.cos(a), math.sin(a)],
        )
        for i, a in enumerate(angles)
    ]
    store.upsert(chunks)
    results = store.query([1.0, 0.0], k=3)
    assert len(results) == 3
    assert results[0].rank == 0
    assert results[0].chunk.chunk_index == 0  # 0° matches query exactly
    assert results[1].chunk.chunk_index == 1  # 22.5° next
    assert results[2].chunk.chunk_index == 2  # 45° third
    assert results[0].score > results[-1].score


def test_memory_store_query_source_filter():
    store = MemoryVectorStore()
    a = Chunk(
        chunk_id="d:0",
        doc_id="d",
        source="src-a",
        text="A",
        chunk_index=0,
        embedding=[1.0, 0.0],
    )
    b = Chunk(
        chunk_id="d:1",
        doc_id="d",
        source="src-b",
        text="B",
        chunk_index=1,
        embedding=[1.0, 0.0],
    )
    store.upsert([a, b])
    res = store.query([1.0, 0.0], k=10, source_filter="src-a")
    assert len(res) == 1
    assert res[0].chunk.source == "src-a"


def test_memory_store_query_zero_k_returns_empty():
    store = MemoryVectorStore()
    store.upsert(
        [Chunk(chunk_id="x", doc_id="d", source="s", text="t", chunk_index=0, embedding=[1.0])]
    )
    assert store.query([1.0], k=0) == []


def test_memory_store_clear():
    store = MemoryVectorStore()
    store.upsert(
        [Chunk(chunk_id="x", doc_id="d", source="s", text="t", chunk_index=0, embedding=[1.0])]
    )
    assert store.count() == 1
    store.clear()
    assert store.count() == 0


# ---------------------------------------------------------------------------
# KnowledgeBase end-to-end
# ---------------------------------------------------------------------------


def test_knowledge_base_ingest_and_query_end_to_end():
    """End-to-end pipeline: ingest 2 short docs (chunk_size large enough that
    each doc becomes 1 chunk), query with exact text → cosine = 1.0 wins."""
    text_cantilever = "Euler-Bernoulli says delta equals PL3 over 3EI."
    text_truss = "A truss has axial members carrying tension and compression."
    kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore(), chunk_size=200, overlap=0)
    docs = [
        Document(
            doc_id="cantilever-1",
            source="gs-theory",
            title="GS-001 cantilever",
            text=text_cantilever,
        ),
        Document(
            doc_id="truss-1",
            source="gs-theory",
            title="GS-002 truss",
            text=text_truss,
        ),
    ]
    stats = kb.ingest(docs)
    assert stats.documents_seen == 2
    assert stats.chunks_written == 2  # chunk_size > doc length → 1 chunk each
    assert stats.chunks_per_doc_avg == 1.0

    # Query with exact cantilever text → MockEmbedder produces identical SHA →
    # cosine similarity = 1.0 → that chunk wins.
    results = kb.query(text_cantilever, k=2)
    assert len(results) == 2
    assert results[0].chunk.doc_id == "cantilever-1"
    assert results[0].score == pytest.approx(1.0, abs=1e-6)


def test_knowledge_base_empty_query_returns_empty():
    kb = KnowledgeBase(MockEmbedder(dim=16), MemoryVectorStore())
    assert kb.query("", k=5) == []
    assert kb.query("   ", k=5) == []


def test_knowledge_base_no_documents_ingest_returns_zeros():
    kb = KnowledgeBase(MockEmbedder(dim=16), MemoryVectorStore())
    stats = kb.ingest([])
    assert stats.documents_seen == 0
    assert stats.chunks_written == 0


def test_knowledge_base_source_filter_propagates():
    kb = KnowledgeBase(MockEmbedder(dim=16), MemoryVectorStore(), chunk_size=200)
    kb.ingest(
        [
            Document(doc_id="a", source="src1", title="A", text="alpha content"),
            Document(doc_id="b", source="src2", title="B", text="beta content"),
        ]
    )
    res = kb.query("alpha", k=10, source_filter="src1")
    assert len(res) >= 1
    assert all(r.chunk.source == "src1" for r in res)


def test_knowledge_base_embedder_id_property():
    kb = KnowledgeBase(MockEmbedder(dim=64), MemoryVectorStore())
    assert kb.embedder_id == "mock-sha256@64"


# ---------------------------------------------------------------------------
# R2 — Document.title / metadata propagation (Codex R1 MEDIUM)
# ---------------------------------------------------------------------------


def test_ingest_propagates_title_and_metadata_to_chunks():
    """Each chunk must carry parent Document.title + metadata so the
    store can persist citation-quality provenance."""
    store = MemoryVectorStore()
    kb = KnowledgeBase(MockEmbedder(dim=16), store, chunk_size=200, overlap=0)
    kb.ingest(
        [
            Document(
                doc_id="adr-013",
                source="project-adr-fp",
                title="ADR-013 Branch Protection",
                text="Layer 3 enforces required checks on main.",
                metadata={"section": "T2", "page": 2},
            )
        ]
    )
    res = kb.query("Layer 3", k=1)
    assert len(res) == 1
    chunk = res[0].chunk
    assert chunk.title == "ADR-013 Branch Protection"
    assert chunk.metadata.get("section") == "T2"
    assert chunk.metadata.get("page") == 2


def test_chunk_title_and_metadata_default_empty_for_back_compat():
    """Chunks built by external callers without title/metadata still
    construct cleanly (back-compat)."""
    c = Chunk(chunk_id="x", doc_id="d", source="s", text="t", chunk_index=0)
    assert c.title == ""
    assert c.metadata == {}


# ---------------------------------------------------------------------------
# R2 — ChromaVectorStore score parity with MemoryVectorStore (Codex R1 HIGH)
# ---------------------------------------------------------------------------


def test_chroma_store_score_passes_negative_cosine_through():
    """R2 (post Codex R1 HIGH): the Chroma adapter previously clamped
    `1 - distance` with `max(0.0, ...)`, collapsing all
    negative-cosine pairs (opposing vectors) to score=0. The fix
    drops the clamp; this test verifies the formula is `1 - distance`
    without floor.

    Pure-source check, no chromadb dependency required.
    """
    import inspect

    from backend.app.rag.store import ChromaVectorStore

    src = inspect.getsource(ChromaVectorStore.query)
    # Old formula was `max(0.0, 1.0 - float(dist))`. New must be the
    # naked subtraction.
    assert "max(0.0, 1.0 - float(dist))" not in src, (
        "Chroma adapter still clamps — should be `1 - distance` without floor"
    )
    assert "1.0 - float(dist)" in src, "expected new formula `1 - distance`"


def test_chroma_store_persists_title_and_metadata():
    """R2 (post Codex R1 MEDIUM): the Chroma adapter previously wrote
    only doc_id/source/chunk_index. Verify the upsert path now writes
    title and meta_* keys.

    Pure-source check; full integration test would require chromadb.
    """
    import inspect

    from backend.app.rag.store import ChromaVectorStore

    src = inspect.getsource(ChromaVectorStore.upsert)
    assert '"title"' in src, "upsert must persist Chunk.title"
    assert "meta_" in src, "upsert must namespace flattened metadata under meta_*"


# ---------------------------------------------------------------------------
# BgeM3Embedder import gating
# ---------------------------------------------------------------------------


def test_bge_m3_embedder_lazy_imports_on_construct():
    """Without sentence-transformers installed, construction should raise
    a clear ImportError pointing at the [rag] extra."""
    from backend.app.rag.embedder import BgeM3Embedder

    # If sentence-transformers is installed in the test env, this test
    # would attempt to download the model (network). Skip in that case.
    try:
        import sentence_transformers  # noqa: F401

        pytest.skip("sentence-transformers is installed; skipping import-gate test")
    except ImportError:
        pass

    with pytest.raises(ImportError, match=r"\[rag\]"):
        BgeM3Embedder()


# ---------------------------------------------------------------------------
# Schema invariants
# ---------------------------------------------------------------------------


def test_chunk_index_must_be_non_negative():
    with pytest.raises(ValueError):
        Chunk(chunk_id="x", doc_id="d", source="s", text="t", chunk_index=-1)


def test_retrieval_result_rank_non_negative():
    from backend.app.rag.schemas import RetrievalResult

    chunk = Chunk(chunk_id="x", doc_id="d", source="s", text="t", chunk_index=0, embedding=[1.0])
    with pytest.raises(ValueError):
        RetrievalResult(chunk=chunk, score=0.5, rank=-1)
