"""Shared test helpers — FM-04a Phase 18 B (ADR-025).

The Tier 1 / Tier 2 envelope discriminator (per ADR-025 §2) introduces
the assertion pattern "envelope claims tier X AND boundary copy matches
tier X AND impact copy matches tier X". The two ``assert_tierN_trio``
helpers below pin that pattern in a single place so a future tier
addition lands in one location, not scattered across N test files.

Phases 1-17 used the inline pattern
``assert envelope["claim_tier"] == "Tier 1 engineering candidate"``;
the Phase 18 helpers below are the modern path. The inline pattern is
NOT removed (Phase 18 B is additive) — existing tests continue to use
it; new tests at the Tier 1/2 boundary use the helpers.
"""

from __future__ import annotations

from typing import Any

from app.services.reporting._claim_tier import (
    CLAIM_BOUNDARIES,
    CLAIM_TIER_LABELS,
)

_TIER_1_LABEL = CLAIM_TIER_LABELS["tier_1_candidate"]
_TIER_2_LABEL = CLAIM_TIER_LABELS["tier_2_validated"]
_TIER_1_BOUNDARY = CLAIM_BOUNDARIES["tier_1_candidate"]
_TIER_2_BOUNDARY = CLAIM_BOUNDARIES["tier_2_validated"]


def assert_tier1_trio(envelope: dict[str, Any]) -> None:
    """Assert that ``envelope`` is a well-formed Tier 1 candidate
    envelope:

      * ``claim_tier`` field equals ``"Tier 1 engineering candidate"``
        (the Phase 1-17 SSOT label).
      * ``claim_boundary`` field contains the Tier 1 boundary copy
        (``"tier1_engineering_candidate; not_signed_validation; ...
        not_benchmark_agreement"``).
      * No tokens from the solver-class forbidden list appear as
        positive claims anywhere in the rendered string fields
        (defense-in-depth; the per-section filter upstream is
        primary).

    Raises:
        AssertionError: with the specific failed sub-assertion in the
            message; the message includes the envelope keys observed
            for quick triage.
    """
    assert "claim_tier" in envelope, (
        f"envelope missing 'claim_tier' field; keys={sorted(envelope)}"
    )
    assert envelope["claim_tier"] == _TIER_1_LABEL, (
        f"expected claim_tier=={_TIER_1_LABEL!r}; "
        f"got {envelope['claim_tier']!r}"
    )
    assert "claim_boundary" in envelope, (
        f"envelope missing 'claim_boundary' field; "
        f"keys={sorted(envelope)}"
    )
    boundary = envelope["claim_boundary"]
    assert "tier1_engineering_candidate" in boundary, (
        f"expected Tier 1 boundary marker in claim_boundary; "
        f"got {boundary!r}"
    )
    assert "not_signed_validation" in boundary, (
        f"expected 'not_signed_validation' in Tier 1 boundary; "
        f"got {boundary!r}"
    )


def assert_tier2_trio(envelope: dict[str, Any]) -> None:
    """Assert that ``envelope`` is a well-formed Tier 2 validated
    envelope:

      * ``claim_tier`` field equals ``"Tier 2 real-solver validated"``
        (the Phase 18 B SSOT label).
      * ``claim_boundary`` field contains the Tier 2 boundary copy
        (``"tier2_real_solver_validated; not_signed_validation;
        cross_check_against_analytical"``).
      * ``claim_boundary`` STILL carries ``"not_signed_validation"`` —
        Tier 2 is real-solver-validated, NOT signed (per ADR-025 §2).

    Raises:
        AssertionError: with the specific failed sub-assertion in the
            message.
    """
    assert "claim_tier" in envelope, (
        f"envelope missing 'claim_tier' field; keys={sorted(envelope)}"
    )
    assert envelope["claim_tier"] == _TIER_2_LABEL, (
        f"expected claim_tier=={_TIER_2_LABEL!r}; "
        f"got {envelope['claim_tier']!r}"
    )
    assert "claim_boundary" in envelope, (
        f"envelope missing 'claim_boundary' field; "
        f"keys={sorted(envelope)}"
    )
    boundary = envelope["claim_boundary"]
    assert "tier2_real_solver_validated" in boundary, (
        f"expected Tier 2 boundary marker in claim_boundary; "
        f"got {boundary!r}"
    )
    assert "cross_check_against_analytical" in boundary, (
        f"expected 'cross_check_against_analytical' in Tier 2 "
        f"boundary; got {boundary!r}"
    )
    assert "not_signed_validation" in boundary, (
        f"Tier 2 validated is NOT signed; "
        f"expected 'not_signed_validation' in boundary; got {boundary!r}"
    )


__all__ = ["assert_tier1_trio", "assert_tier2_trio"]
