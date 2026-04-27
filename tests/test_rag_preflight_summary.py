"""Tests for app.rag.preflight_summary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

try:
    from app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
    from app.rag.preflight_summary import (
        PreflightSummary,
        _aggregate_confidence,
        _format_advice_line,
        _format_quantity_line,
        combine,
    )
    from app.rag.reviewer_advisor import ReviewerAdvice, advise
    from app.rag.schemas import Document
except ImportError as e:
    pytest.skip(f"preflight_summary imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Duck-type stubs for SurrogateHint / HintQuantity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StubQuantity:
    name: str
    value: float
    unit: str
    confidence: str = "low"
    location: str | None = None


@dataclass(frozen=True)
class _StubHint:
    case_id: str = "GS-001"
    provider: str = "placeholder-mlp@v0"
    quantities: list = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _populated_kb() -> KnowledgeBase:
    kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())
    kb.ingest(
        [
            Document(
                doc_id="adr-fake-1",
                source="project-adr-fp",
                title="ADR-FAKE-1",
                text="solver convergence Newton residual tolerance",
                metadata={},
            ),
            Document(
                doc_id="theory-fake-1",
                source="gs-theory",
                title="GS-FAKE",
                text="cantilever beam Euler Bernoulli analytical theory",
                metadata={},
            ),
        ]
    )
    return kb


def _hint_with_predictions() -> _StubHint:
    return _StubHint(
        case_id="GS-001",
        provider="placeholder-mlp@v0",
        quantities=[
            _StubQuantity(
                name="max_displacement",
                value=1.234567,
                unit="mm",
                confidence="low",
                location="free_end",
            ),
            _StubQuantity(
                name="sigma_vm_max",
                value=210.0,
                unit="MPa",
                confidence="medium",
                location="root",
            ),
        ],
        notes="placeholder model — confidence intentionally low",
    )


# ---------------------------------------------------------------------------
# _format_quantity_line
# ---------------------------------------------------------------------------


def test_format_quantity_line_basic():
    q = _StubQuantity(name="x", value=1.234, unit="mm", confidence="low")
    line = _format_quantity_line(q)
    assert "x = 1.234 mm" in line
    assert "(low)" in line


def test_format_quantity_line_with_location():
    q = _StubQuantity(name="x", value=1.0, unit="mm", confidence="high", location="tip")
    line = _format_quantity_line(q)
    assert "@ tip" in line
    assert "(high)" in line


def test_format_quantity_line_handles_missing_fields():
    """A bare object missing fields shouldn't crash."""

    class _Bare:
        pass

    line = _format_quantity_line(_Bare())
    assert "?" in line  # name fallback


def test_format_quantity_line_handles_enum_confidence():
    """Enum-typed confidence (e.g. HintConfidence.HIGH) should still render."""

    class _Enum:
        value = "high"

    q = _StubQuantity(name="x", value=1.0, unit="mm", confidence=_Enum())
    line = _format_quantity_line(q)
    assert "(high)" in line


# ---------------------------------------------------------------------------
# _aggregate_confidence
# ---------------------------------------------------------------------------


def test_aggregate_confidence_empty_returns_na():
    assert _aggregate_confidence([]) == "n/a"


def test_aggregate_confidence_all_high():
    qs = [
        _StubQuantity(name="x", value=1.0, unit="mm", confidence="high"),
        _StubQuantity(name="y", value=2.0, unit="mm", confidence="high"),
    ]
    assert _aggregate_confidence(qs) == "high"


def test_aggregate_confidence_mixed_high_medium():
    qs = [
        _StubQuantity(name="x", value=1.0, unit="mm", confidence="high"),
        _StubQuantity(name="y", value=2.0, unit="mm", confidence="medium"),
    ]
    assert _aggregate_confidence(qs) == "medium"


def test_aggregate_confidence_any_low_demotes_to_low():
    qs = [
        _StubQuantity(name="x", value=1.0, unit="mm", confidence="high"),
        _StubQuantity(name="y", value=2.0, unit="mm", confidence="low"),
    ]
    assert _aggregate_confidence(qs) == "low"


# ---------------------------------------------------------------------------
# _format_advice_line
# ---------------------------------------------------------------------------


def test_format_advice_line_truncates():
    long_text = "x" * 500
    line = _format_advice_line(0, 0.5, "src", "abc:0", long_text)
    assert "..." in line
    assert len(line) < 200  # bounded


def test_format_advice_line_includes_score():
    line = _format_advice_line(2, 0.789, "gs-theory", "GS-001:0", "snippet")
    assert "score=0.789" in line
    assert "#3" in line


# ---------------------------------------------------------------------------
# combine() — empty advisor + populated hint
# ---------------------------------------------------------------------------


def test_combine_empty_advice_populated_hint():
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="solver_convergence")
    summary = combine(_hint_with_predictions(), advice)
    assert summary.has_quantities()
    assert not summary.has_advice()
    assert summary.confidence_indicator == "low"  # mixed low+medium → low
    assert "max_displacement" in summary.markdown
    assert "_(no corpus hits)_" in summary.markdown


def test_combine_populated_advice_empty_hint():
    kb = _populated_kb()
    advice = advise(kb, "Reject", "solver_convergence", k=3)
    summary = combine(_StubHint(), advice)
    assert not summary.has_quantities()
    assert summary.has_advice()
    assert summary.confidence_indicator == "n/a"
    assert "_(no predictions)_" in summary.markdown


def test_combine_both_populated():
    kb = _populated_kb()
    advice = advise(kb, "Reject", "solver_convergence", k=3)
    summary = combine(_hint_with_predictions(), advice)
    assert summary.has_quantities()
    assert summary.has_advice()
    assert summary.case_id == "GS-001"
    assert summary.verdict == "Reject"
    assert summary.fault_class == "solver_convergence"
    # markdown has both sections
    assert "## Preflight — GS-001" in summary.markdown
    assert "Surrogate predictions" in summary.markdown
    assert "Corpus advice" in summary.markdown
    # quantity rendering
    assert "max_displacement" in summary.markdown
    assert "1.235 mm" in summary.markdown or "1.234 mm" in summary.markdown


# ---------------------------------------------------------------------------
# max_advice_lines cap
# ---------------------------------------------------------------------------


def test_max_advice_lines_caps_output():
    kb = _populated_kb()
    advice = advise(kb, "Reject", "solver_convergence", k=10)
    summary = combine(_hint_with_predictions(), advice, max_advice_lines=1)
    assert len(summary.advice_lines) <= 1


def test_max_advice_lines_zero_disables_cap():
    kb = _populated_kb()
    advice = advise(kb, "Reject", "solver_convergence", k=10)
    summary = combine(_hint_with_predictions(), advice, max_advice_lines=0)
    assert len(summary.advice_lines) == len(advice.results)


def test_max_advice_lines_negative_raises():
    advice = ReviewerAdvice(query="q", verdict="v", fault_class="fc")
    with pytest.raises(ValueError, match="max_advice_lines"):
        combine(_StubHint(), advice, max_advice_lines=-1)


# ---------------------------------------------------------------------------
# PreflightSummary frozen + helpers
# ---------------------------------------------------------------------------


def test_preflight_summary_is_frozen():
    s = PreflightSummary(case_id="x", verdict="v", fault_class="f")
    with pytest.raises((AttributeError, Exception)):
        s.case_id = "mutated"  # type: ignore[misc]


def test_preflight_summary_is_empty_when_both_empty():
    s = PreflightSummary(case_id="x", verdict="v", fault_class="f")
    assert s.is_empty()


def test_preflight_summary_not_empty_when_either_set():
    s = PreflightSummary(case_id="x", verdict="v", fault_class="f", quantity_lines=("a",))
    assert not s.is_empty()
    assert s.has_quantities()


# ---------------------------------------------------------------------------
# Markdown formatting invariants
# ---------------------------------------------------------------------------


def test_markdown_includes_provider_name():
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="fc")
    summary = combine(_hint_with_predictions(), advice)
    assert "placeholder-mlp@v0" in summary.markdown


def test_markdown_includes_notes_when_present():
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="fc")
    summary = combine(_hint_with_predictions(), advice)
    assert "placeholder model" in summary.markdown


def test_markdown_omits_notes_block_when_empty():
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="fc")
    hint = _StubHint(quantities=[_StubQuantity(name="x", value=1, unit="mm")])
    summary = combine(hint, advice)
    assert "_notes:_" not in summary.markdown


def test_markdown_ends_with_newline():
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="fc")
    summary = combine(_hint_with_predictions(), advice)
    assert summary.markdown.endswith("\n")


# ---------------------------------------------------------------------------
# Real-corpus integration smoke
# ---------------------------------------------------------------------------


def test_combine_with_real_repo_corpus():
    repo_root = Path(__file__).resolve().parent.parent
    kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())

    # Ingest live corpus via the registry
    from app.rag.sources import ALL_SOURCES

    for _label, iter_fn in ALL_SOURCES:
        docs = list(iter_fn(repo_root))
        if docs:
            kb.ingest(docs)

    advice = advise(kb, "Reject", "solver_convergence", k=5)
    summary = combine(_hint_with_predictions(), advice)
    assert summary.has_quantities()
    assert summary.has_advice()
    # markdown should be non-trivial
    assert len(summary.markdown) > 200


# ---------------------------------------------------------------------------
# R2 (post Codex R1 on PR #63) — confidence enums, markdown escaping,
# quantities container validation, plus coverage gaps Codex flagged.
# ---------------------------------------------------------------------------


def test_confidence_int_enum_value_does_not_crash():
    """R2 MED-1: a normal `Enum(auto())` produces int .value. Pre-fix
    `_format_quantity_line` called `.lower()` on the int and crashed
    with AttributeError. After fix: coerce via str() before lower."""
    import enum

    class IntConf(enum.Enum):
        LOW = enum.auto()
        HIGH = enum.auto()

    @dataclass(frozen=True)
    class _Q:
        name: str
        value: float
        unit: str
        confidence: IntConf
        location: str | None = None

    q = _Q(name="x", value=1.0, unit="mm", confidence=IntConf.HIGH)
    line = _format_quantity_line(q)
    assert "x = 1" in line
    # The int value of the enum should be coerced to a string and lowercased
    assert "(2)" in line or "2)" in line  # IntConf.HIGH = 2 by auto()


def test_aggregate_confidence_int_enum_does_not_crash():
    """R2 MED-1 sibling: _aggregate_confidence must also handle int enums."""
    import enum

    class IntConf(enum.Enum):
        LOW = enum.auto()
        HIGH = enum.auto()

    @dataclass(frozen=True)
    class _Q:
        confidence: IntConf

    # Should not raise; treats int values as unknown → rolls down to "low"
    result = _aggregate_confidence([_Q(confidence=IntConf.HIGH), _Q(confidence=IntConf.LOW)])
    assert result == "low"


def test_markdown_injection_in_notes_does_not_break_block():
    """R2 MED-2: a notes field containing markdown directives must not
    create new headings or list items in the rendered block."""
    hint = _StubHint(
        case_id="GS-INJ",
        provider="evil@v0",
        notes="## hi\n- boom\n* injected\n# heading",
        quantities=[],
    )
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(hint, advice)
    md = summary.markdown
    # Only the original `## Preflight ...` heading at offset 0 must
    # appear. Pre-fix, a notes value with `\n## hi` injected a second
    # `\n## ` line. After md_escape, newlines are collapsed so the
    # `## hi` text becomes inline within the notes line.
    assert md.count("\n## ") == 0, f"injection created a new heading line: {md!r}"
    # The injected text remains visible (escaped) inline within the notes
    assert "## hi" in md
    # `### ` headings present are only the structural ones (Surrogate /
    # Corpus advice). Injected text shouldn't add any.
    assert md.count("\n### ") == 2


def test_markdown_injection_in_quantity_name_neutralized():
    """R2 MED-2: a quantity name containing newline + heading marker
    must not reshape the rendered block."""
    q = _StubQuantity(
        name="evil\n## broken_heading",
        value=1.0,
        unit="mm",
        confidence="high",
    )
    hint = _StubHint(quantities=[q])
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(hint, advice)
    md = summary.markdown
    # No injected `\n## ` line; the `##` text is escaped/inline within
    # the quantity bullet line.
    assert md.count("\n## ") == 0
    # The escaped text is still visible inline (just not as a heading)
    assert "## broken_heading" in md


def test_quantities_string_rejected(tmp_path):
    """R2 LOW: hint.quantities = 'abc' is iterable but produces 3 bogus
    lines. Must raise ValueError with a clear message instead."""
    hint = _StubHint(quantities="abc")  # type: ignore[arg-type]
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    with pytest.raises(ValueError, match="quantities must be"):
        combine(hint, advice)


def test_quantities_int_rejected():
    """R2 LOW: a non-iterable like 123 must raise a clear ValueError."""

    @dataclass(frozen=True)
    class _BadHint:
        case_id: str = "GS-X"
        provider: str = "p"
        quantities: int = 123  # type: ignore[assignment]
        notes: str = ""

    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    with pytest.raises(ValueError, match="quantities must be"):
        combine(_BadHint(), advice)


def test_quantities_none_treated_as_empty():
    """A None quantities (missing-field-via-getattr-default) must be
    treated as empty, not raise."""

    @dataclass(frozen=True)
    class _MissingHint:
        case_id: str = "GS-X"
        provider: str = "p"
        notes: str = ""
        # No quantities attribute at all

    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(_MissingHint(), advice)
    assert not summary.has_quantities()


def test_combine_both_inputs_empty():
    """R2 coverage gap: empty hint + empty advice must produce a
    well-formed (if minimal) summary, not crash or empty output."""
    hint = _StubHint(case_id="GS-EMPTY", provider="none", quantities=[], notes="")
    advice = ReviewerAdvice(query="q", verdict="Accept", fault_class="none")
    summary = combine(hint, advice)
    assert summary.is_empty()
    # markdown still renders the headings + placeholders
    assert "## Preflight — GS-EMPTY" in summary.markdown
    assert "_(no predictions)_" in summary.markdown
    assert "_(no corpus hits)_" in summary.markdown


def test_combine_handles_nan_value():
    """R2 coverage gap: a NaN value in a quantity must render without
    crashing. `:.4g` formats NaN as 'nan'."""
    q = _StubQuantity(name="x", value=float("nan"), unit="mm", confidence="low")
    hint = _StubHint(quantities=[q])
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(hint, advice)
    assert "nan" in summary.markdown.lower()


def test_combine_handles_inf_value():
    q = _StubQuantity(name="x", value=float("inf"), unit="mm", confidence="low")
    hint = _StubHint(quantities=[q])
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(hint, advice)
    assert "inf" in summary.markdown.lower()


def test_summary_is_pickle_round_trip():
    """R2: PreflightSummary must survive pickle for log/event surfaces."""
    import pickle

    hint = _StubHint(quantities=[_StubQuantity(name="x", value=1.0, unit="mm")])
    advice = ReviewerAdvice(query="q", verdict="Reject", fault_class="unknown")
    summary = combine(hint, advice)
    restored = pickle.loads(pickle.dumps(summary))
    assert restored.case_id == summary.case_id
    assert restored.markdown == summary.markdown
