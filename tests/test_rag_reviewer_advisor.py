"""Tests for backend.app.rag.reviewer_advisor."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
    from backend.app.rag.reviewer_advisor import (
        FAULT_QUERY_SEEDS,
        GOVERNANCE_BIASING_VERDICTS,
        KNOWN_VERDICTS,
        ReviewerAdvice,
        _build_query,
        _summarise,
        advise,
    )
    from backend.app.rag.schemas import Document
    from backend.app.rag.sources import ALL_SOURCES
except ImportError as e:
    pytest.skip(f"reviewer_advisor imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_kb() -> KnowledgeBase:
    return KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())


def _populated_kb_real_repo() -> KnowledgeBase:
    kb = _empty_kb()
    repo_root = Path(__file__).resolve().parent.parent
    for _label, iter_fn in ALL_SOURCES:
        docs = list(iter_fn(repo_root))
        if docs:
            kb.ingest(docs)
    return kb


def _populated_kb_synthetic() -> KnowledgeBase:
    kb = _empty_kb()
    kb.ingest(
        [
            Document(
                doc_id="adr-fake-1",
                source="project-adr-fp",
                title="ADR-FAKE-1",
                text="solver convergence Newton residual tolerance text",
                metadata={},
            ),
            Document(
                doc_id="theory-fake-1",
                source="gs-theory",
                title="GS-FAKE",
                text="cantilever beam Euler Bernoulli analytical theory text",
                metadata={},
            ),
        ]
    )
    return kb


# ---------------------------------------------------------------------------
# Constants / data integrity
# ---------------------------------------------------------------------------


def test_fault_query_seeds_cover_all_fault_class_values():
    """Every FaultClass value must have a query seed."""
    try:
        from schemas.sim_state import FaultClass
    except ImportError:
        pytest.skip("schemas.sim_state requires Python 3.11+ (StrEnum)")

    for fc in FaultClass:
        assert fc.value in FAULT_QUERY_SEEDS, f"missing seed for {fc.value}"


def test_governance_biasing_verdicts_includes_reject():
    assert "Reject" in GOVERNANCE_BIASING_VERDICTS
    assert "Re-run" in GOVERNANCE_BIASING_VERDICTS


# ---------------------------------------------------------------------------
# _build_query
# ---------------------------------------------------------------------------


def test_build_query_governance_verdict_appends_adr_fp():
    q = _build_query("Reject", "solver_convergence")
    assert "Reject" in q
    assert "ADR" in q
    assert "FailurePattern" in q
    assert "Newton" in q  # from seed


def test_build_query_accept_does_not_append_adr_fp():
    q = _build_query("Accept", "none")
    assert "Accept" in q
    assert "ADR" not in q
    assert "FailurePattern" not in q


def test_build_query_unknown_fault_class_falls_back():
    """A fault class outside FAULT_QUERY_SEEDS still produces a query."""
    q = _build_query("Reject", "totally_made_up_fault")
    assert "totally made up fault" in q  # underscores → spaces


# ---------------------------------------------------------------------------
# _summarise
# ---------------------------------------------------------------------------


def test_summarise_empty_results():
    s = _summarise((), "Reject", "solver_convergence")
    assert "No corpus hits" in s
    assert "verdict=Reject" in s


def test_summarise_with_results():
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence", k=2)
    s = advice.summary
    assert "verdict=Reject" in s
    assert "hit(s)" in s
    assert "score=" in s


# ---------------------------------------------------------------------------
# advise() — input validation
# ---------------------------------------------------------------------------


def test_advise_empty_verdict_raises():
    with pytest.raises(ValueError, match="verdict"):
        advise(_empty_kb(), "", "unknown")


def test_advise_whitespace_verdict_raises():
    with pytest.raises(ValueError, match="verdict"):
        advise(_empty_kb(), "   ", "unknown")


def test_advise_zero_k_raises():
    with pytest.raises(ValueError, match="k"):
        advise(_empty_kb(), "Reject", "unknown", k=0)


def test_advise_negative_k_raises():
    with pytest.raises(ValueError, match="k"):
        advise(_empty_kb(), "Reject", "unknown", k=-1)


# ---------------------------------------------------------------------------
# advise() — empty KB
# ---------------------------------------------------------------------------


def test_advise_empty_kb_returns_empty_advice():
    advice = advise(_empty_kb(), "Reject", "solver_convergence")
    assert advice.is_empty()
    assert advice.results == ()
    assert advice.grouped_by_source == {}
    assert "No corpus hits" in advice.summary
    assert advice.top_governance_hit() is None
    assert advice.top_theory_hit() is None


# ---------------------------------------------------------------------------
# advise() — synthetic KB
# ---------------------------------------------------------------------------


def test_advise_synthetic_returns_results():
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence", k=5)
    assert not advice.is_empty()
    assert len(advice.results) >= 1


def test_advise_synthetic_groups_by_source():
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence", k=5)
    sources = set(advice.grouped_by_source.keys())
    # Both sources are in the synthetic corpus
    assert sources <= {"project-adr-fp", "gs-theory"}


def test_advise_source_filter_restricts():
    kb = _populated_kb_synthetic()
    advice = advise(
        kb,
        "Reject",
        "solver_convergence",
        k=5,
        source_filter="gs-theory",
    )
    for r in advice.results:
        assert r.chunk.source == "gs-theory"


# ---------------------------------------------------------------------------
# advise() — frozen dataclass invariants
# ---------------------------------------------------------------------------


def test_reviewer_advice_is_frozen():
    advice = ReviewerAdvice(query="q", verdict="v", fault_class="fc")
    with pytest.raises((AttributeError, Exception)):
        advice.query = "mutated"  # type: ignore[misc]


def test_reviewer_advice_default_empty():
    advice = ReviewerAdvice(query="q", verdict="v", fault_class="fc")
    assert advice.is_empty()
    assert advice.results == ()
    assert advice.grouped_by_source == {}


# ---------------------------------------------------------------------------
# advise() — real-repo smoke
# ---------------------------------------------------------------------------


def test_advise_real_repo_solver_convergence_smoke():
    kb = _populated_kb_real_repo()
    advice = advise(kb, "Reject", "solver_convergence", k=5)
    # Real repo has 10 docs / 114 chunks — query should return at least 1
    assert not advice.is_empty()
    assert len(advice.results) >= 1
    # Summary should be informative
    assert "verdict=Reject" in advice.summary


def test_advise_real_repo_top_hit_helpers_work():
    kb = _populated_kb_real_repo()
    advice = advise(kb, "Reject", "solver_convergence", k=10)
    # In a corpus with both sources, at least one helper should yield something
    gov_hit = advice.top_governance_hit()
    theory_hit = advice.top_theory_hit()
    assert gov_hit is not None or theory_hit is not None


def test_advise_query_string_in_advice():
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Re-run", "mesh_jacobian", k=2)
    assert advice.query
    assert "Re-run" in advice.query
    assert "ADR" in advice.query  # Re-run is governance-biasing


# ---------------------------------------------------------------------------
# Stable behavior across calls (idempotent within a single KB)
# ---------------------------------------------------------------------------


def test_advise_is_deterministic_for_same_query():
    kb = _populated_kb_synthetic()
    a1 = advise(kb, "Reject", "solver_convergence", k=3)
    a2 = advise(kb, "Reject", "solver_convergence", k=3)
    assert a1.query == a2.query
    assert len(a1.results) == len(a2.results)
    for r1, r2 in zip(a1.results, a2.results, strict=False):
        assert r1.chunk.chunk_id == r2.chunk.chunk_id


# ---------------------------------------------------------------------------
# Pre-emptive R2 hardening — mirrors the rejection-on-typo + immutability
# patterns enforced in backend.app.rag.cli (PR #59) and backend.app.rag.
# query_cli (PR #60). Locked in here BEFORE Codex R1 to anticipate the
# same class of findings and shorten the review cycle.
# ---------------------------------------------------------------------------


def test_advise_rejects_unknown_source_filter():
    """A typo on `source_filter` must raise, not silently return [].
    Pre-PR-#60 lesson: silent empties hide real bugs in caller code.
    """
    kb = _populated_kb_synthetic()
    with pytest.raises(ValueError, match="unknown source_filter"):
        advise(kb, "Reject", "solver_convergence", source_filter="bogus-label")


def test_advise_rejects_unknown_source_filter_lists_available():
    """The error message must list the available labels so the caller
    can fix the typo without having to grep ALL_SOURCES."""
    kb = _populated_kb_synthetic()
    available_labels = {lbl for (lbl, _) in ALL_SOURCES}
    with pytest.raises(ValueError) as exc_info:
        advise(kb, "Reject", "unknown", source_filter="project-adr-fb-typo")
    msg = str(exc_info.value)
    for lbl in available_labels:
        assert lbl in msg, f"available label {lbl!r} missing from error msg"


def test_advise_accepts_each_known_source_label():
    """Every label in ALL_SOURCES must be accepted by the validator."""
    kb = _populated_kb_synthetic()
    for label, _ in ALL_SOURCES:
        # Should not raise. May return is_empty depending on synthetic content.
        advice = advise(kb, "Reject", "solver_convergence", source_filter=label)
        for r in advice.results:
            assert r.chunk.source == label


def test_advise_source_filter_none_still_works():
    """Regression: source_filter=None (default) must NOT trip the
    new validator path."""
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence")
    assert not advice.is_empty()


# ---------------------------------------------------------------------------
# R2 (post Codex R1 MED-1 on PR #61) — serialization friendliness.
#
# The earlier MappingProxyType wrapping enforced runtime immutability but
# broke `pickle.dumps()` and `dataclasses.asdict()`, both of which the
# advisor output is expected to flow through (log surfaces, PR-comment
# pipelines, event payloads). MED-1 fix: keep grouped_by_source as a
# plain dict; immutability is communicated by frozen=True on the binding
# + caller convention.
# ---------------------------------------------------------------------------


def test_advice_pickles_round_trip():
    import pickle

    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence", k=3)
    blob = pickle.dumps(advice)
    restored = pickle.loads(blob)
    assert restored.query == advice.query
    assert restored.verdict == advice.verdict
    assert restored.fault_class == advice.fault_class
    assert len(restored.results) == len(advice.results)
    assert dict(restored.grouped_by_source) == dict(advice.grouped_by_source)
    assert restored.summary == advice.summary


def test_advice_asdict_round_trip():
    """`dataclasses.asdict` must work for downstream JSON / event surfaces.
    MappingProxyType broke this; plain dict does not."""
    from dataclasses import asdict

    kb = _populated_kb_synthetic()
    advice = advise(kb, "Reject", "solver_convergence", k=2)
    d = asdict(advice)
    assert d["verdict"] == "Reject"
    assert d["fault_class"] == "solver_convergence"
    assert "grouped_by_source" in d
    assert isinstance(d["grouped_by_source"], dict)


def test_default_advice_pickles_and_asdicts():
    """Pickle/asdict must work even on the empty-default advice."""
    import pickle
    from dataclasses import asdict

    advice = ReviewerAdvice(query="q", verdict="Accept", fault_class="none")
    pickle.loads(pickle.dumps(advice))
    asdict(advice)


# ---------------------------------------------------------------------------
# R2 (post Codex R1 MED-2 on PR #61) — verdict normalization + validation.
#
# Strip surrounding whitespace, then validate against KNOWN_VERDICTS
# (mirrors `schemas.ws_events.ReviewerVerdict` Literal). Pre-fix, callers
# could pass " Reject " or "Re-run\n" and silently bypass governance bias
# because the comparison set is exact-match.
# ---------------------------------------------------------------------------


def test_known_verdicts_match_canonical_set():
    """KNOWN_VERDICTS must match the 5 canonical ws_events.ReviewerVerdict
    Literal values."""
    assert (
        frozenset({"Accept", "Accept with Note", "Reject", "Needs Review", "Re-run"})
        == KNOWN_VERDICTS
    )


def test_advise_rejects_unknown_verdict_string():
    kb = _populated_kb_synthetic()
    with pytest.raises(ValueError, match="unknown verdict"):
        advise(kb, "FullyRejected", "unknown")


def test_advise_rejects_lowercase_verdict():
    """'reject' lowercase is NOT canonical; must fail loud."""
    kb = _populated_kb_synthetic()
    with pytest.raises(ValueError, match="unknown verdict"):
        advise(kb, "reject", "solver_convergence")


def test_advise_strips_whitespace_around_verdict():
    """' Reject ' must be normalized to 'Reject' so governance bias
    actually fires (the pre-fix bug was a silent bias-bypass)."""
    kb = _populated_kb_synthetic()
    advice = advise(kb, "  Reject  ", "solver_convergence", k=2)
    assert advice.verdict == "Reject"
    # Bias must fire on the normalized verdict
    assert "ADR" in advice.query
    assert "FailurePattern" in advice.query


def test_advise_strips_trailing_newline_in_verdict():
    """'Re-run\\n' must be normalized to 'Re-run'."""
    kb = _populated_kb_synthetic()
    advice = advise(kb, "Re-run\n", "mesh_jacobian", k=2)
    assert advice.verdict == "Re-run"
    assert "ADR" in advice.query


def test_advise_rejects_non_string_verdict():
    kb = _populated_kb_synthetic()
    with pytest.raises(ValueError, match="must be a string"):
        advise(kb, 42, "unknown")  # type: ignore[arg-type]


def test_advise_unknown_verdict_error_lists_known_set():
    kb = _populated_kb_synthetic()
    with pytest.raises(ValueError) as exc_info:
        advise(kb, "BogusVerdict", "unknown")
    msg = str(exc_info.value)
    for v in KNOWN_VERDICTS:
        assert v in msg, f"{v!r} not listed in error message"
