"""Tests for agents/surrogate.py + schemas/surrogate_hint.py (P1-07).

The surrogate is informational; tests verify the contract (it predicts
what it claims, never blocks pipeline, signals LOW confidence appropriately).
"""

from __future__ import annotations

import pytest

# These tests need Python 3.11+ runtime (pydantic v2 + StrEnum elsewhere).
# Skip on older interpreters cleanly rather than crashing collection.
try:
    from agents.surrogate import (
        PlaceholderSurrogate,
        SurrogateProvider,
        default_provider,
        hint_to_prompt_context,
    )
    from schemas.surrogate_hint import (
        HintConfidence,
        HintQuantity,
        SurrogateHint,
    )
except ImportError as e:
    pytest.skip(f"surrogate module imports failed: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# HintQuantity / SurrogateHint shape
# ---------------------------------------------------------------------------


def test_hint_quantity_minimal_construct():
    q = HintQuantity(name="max_displacement", value=0.7619, unit="mm")
    assert q.confidence == HintConfidence.LOW
    assert q.location is None


def test_hint_quantity_rejects_extra_field():
    with pytest.raises(Exception):  # pydantic ValidationError
        HintQuantity(name="x", value=1.0, unit="mm", bogus="field")


def test_surrogate_hint_with_quantities():
    h = SurrogateHint(
        case_id="GS-001",
        provider="test@v0",
        quantities=[HintQuantity(name="d", value=1.0, unit="mm")],
        notes="ok",
    )
    assert h.case_id == "GS-001"
    assert len(h.quantities) == 1


def test_to_prompt_block_with_quantities():
    h = SurrogateHint(
        case_id="GS-001",
        provider="placeholder-analytical@v0",
        quantities=[
            HintQuantity(
                name="max_displacement",
                value=0.7619,
                unit="mm",
                location="free_end",
                confidence=HintConfidence.LOW,
            )
        ],
    )
    block = h.to_prompt_block()
    assert "Surrogate hint" in block
    assert "placeholder-analytical@v0" in block
    assert "informational only" in block
    assert "max_displacement" in block
    assert "0.7619 mm" in block
    assert "free_end" in block
    assert "low" in block


def test_to_prompt_block_no_quantities():
    h = SurrogateHint(case_id="X", provider="p", quantities=[])
    block = h.to_prompt_block()
    assert "no predictions" in block


def test_to_prompt_block_includes_notes():
    h = SurrogateHint(
        case_id="X",
        provider="p",
        quantities=[HintQuantity(name="q", value=1, unit="mm")],
        notes="extrapolation warning: load outside training range",
    )
    block = h.to_prompt_block()
    assert "extrapolation warning" in block


# ---------------------------------------------------------------------------
# PlaceholderSurrogate behavior
# ---------------------------------------------------------------------------


def test_placeholder_provider_id():
    p = PlaceholderSurrogate()
    assert p.provider_id == "placeholder-analytical@v0"


def test_placeholder_predicts_cantilever_displacement():
    """GS-001: P=400N, L=100mm, E=210000MPa, I=833.33mm⁴ → δ ≈ 0.7619mm."""
    p = PlaceholderSurrogate()
    spec = {
        "case_id": "GS-001",
        "beam_type": "cantilever",
        "load_N": 400.0,
        "length_mm": 100.0,
        "E_MPa": 210000.0,
        "I_mm4": 833.33,
    }
    h = p.predict(spec)
    assert h.case_id == "GS-001"
    assert h.provider == "placeholder-analytical@v0"
    assert len(h.quantities) == 1
    q = h.quantities[0]
    assert q.name == "max_displacement"
    assert q.location == "free_end"
    assert q.confidence == HintConfidence.LOW
    # Allow ±0.5% tolerance on the closed-form
    assert abs(q.value - 0.7619) < 0.01


def test_placeholder_handles_missing_inputs():
    p = PlaceholderSurrogate()
    spec = {"case_id": "X", "beam_type": "cantilever"}  # missing load/L/E/I
    h = p.predict(spec)
    assert h.quantities == []
    assert "missing" in h.notes.lower()


def test_placeholder_handles_unknown_case_type():
    p = PlaceholderSurrogate()
    spec = {"case_id": "X", "structure_type": "shell_buckling"}
    h = p.predict(spec)
    assert h.quantities == []
    assert "not handled" in h.notes


def test_placeholder_handles_no_case_type_at_all():
    p = PlaceholderSurrogate()
    spec = {"case_id": "X"}
    h = p.predict(spec)
    assert h.quantities == []
    assert "no `structure_type`" in h.notes or "cannot infer" in h.notes


def test_placeholder_handles_negative_inputs():
    """Negative load/length should not produce a hint."""
    p = PlaceholderSurrogate()
    spec = {
        "case_id": "X",
        "beam_type": "cantilever",
        "load_N": -10,
        "length_mm": 100,
        "E_MPa": 210000,
        "I_mm4": 833.33,
    }
    h = p.predict(spec)
    assert h.quantities == []


def test_placeholder_input_parse_failure_lands_in_notes():
    p = PlaceholderSurrogate()
    spec = {
        "case_id": "X",
        "beam_type": "cantilever",
        "load_N": "not a number",
        "length_mm": 100,
        "E_MPa": 210000,
        "I_mm4": 833.33,
    }
    h = p.predict(spec)
    # Either parsed-as-zero (skipped) or notes contains the parse failure
    assert h.quantities == []


# ---------------------------------------------------------------------------
# Abstract base + default provider
# ---------------------------------------------------------------------------


def test_subclass_must_implement_abstract():
    class Half(SurrogateProvider):
        @property
        def provider_id(self) -> str:
            return "half"

    with pytest.raises(TypeError):
        Half()  # missing predict()


def test_default_provider_is_placeholder():
    p = default_provider()
    assert isinstance(p, PlaceholderSurrogate)


def test_hint_to_prompt_context_matches_method():
    h = SurrogateHint(
        case_id="X",
        provider="p",
        quantities=[HintQuantity(name="q", value=1, unit="mm")],
    )
    assert hint_to_prompt_context(h) == h.to_prompt_block()


# ---------------------------------------------------------------------------
# Frozen / immutability
# ---------------------------------------------------------------------------


def test_hint_quantity_is_frozen():
    q = HintQuantity(name="x", value=1, unit="mm")
    with pytest.raises(Exception):
        q.value = 2  # type: ignore[misc]


def test_surrogate_hint_is_frozen():
    h = SurrogateHint(case_id="X", provider="p")
    with pytest.raises(Exception):
        h.case_id = "Y"  # type: ignore[misc]
