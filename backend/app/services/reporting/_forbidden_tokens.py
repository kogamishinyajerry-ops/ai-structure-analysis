"""Tier-scoped forbidden-token policy — FM-04a Phase 18 B (ADR-025 §2.1).

Splits the Phase 11 monolithic 9-token forbidden list into two
disjoint classes whose treatment differs by claim tier:

* **Advisor-class tokens** (5) — represent **reviewer authority**
  (certification, sign-off, production readiness). Refused
  **regardless of tier**, because that authority lives outside this
  harness entirely; neither a candidate nor a real-solver-validated
  envelope can legitimately claim it.
* **Solver-class tokens** (4) — represent **solver evidence claims**
  ("validated against the analytical solution to within 2%"). Refused
  on ``tier_1_candidate`` envelopes (synthetic-only data, no real
  solver provenance) and **allowed** on ``tier_2_validated`` envelopes
  that cite an analytical cross-check verdict.

This SSOT is the **new consumer-facing** policy. The Phase 11 inline
``ADVISOR_FORBIDDEN_TOKENS`` tuple in
``backend/app/services/reporting/advisor_critique.py`` is NOT removed
in Phase 18 B — it remains the defense-in-depth path for advisor
critique envelopes (which never carry a real-solver result and hence
never legitimately need solver-class tokens). New consumers that need
tier-aware policy import :func:`is_token_allowed` here.

The token strings are pinned by the Phase 18 B test
``test_phase18b_tier_pivot.py`` to prevent silent drift.
"""

from __future__ import annotations

from typing import Final

from ._claim_tier import ClaimTier

FORBIDDEN_TOKENS_ADVISOR_CLASS: Final[tuple[str, ...]] = (
    "production ready",
    "certified",
    "approved for service",
    "asme compliant",  # case-folded (consumer haystacks are lowered)
    "signed off",
)
"""Tokens carrying reviewer-class authority. Refused on EVERY tier;
this harness never delegates that authority."""

FORBIDDEN_TOKENS_SOLVER_CLASS: Final[tuple[str, ...]] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)
"""Tokens carrying solver-evidence-class claims. Refused on
``tier_1_candidate`` (synthetic data path), allowed on
``tier_2_validated`` envelopes that cite analytical cross-check."""

FORBIDDEN_TOKENS_ALL: Final[tuple[str, ...]] = (
    FORBIDDEN_TOKENS_ADVISOR_CLASS + FORBIDDEN_TOKENS_SOLVER_CLASS
)
"""Union of both classes. Matches (byte-identical) the Phase 11
``ADVISOR_FORBIDDEN_TOKENS`` tuple — preserved here as the back-compat
single-list view for callers that don't (yet) want tier-aware policy."""


def is_token_allowed(token: str, *, tier: ClaimTier) -> bool:
    """Return whether ``token`` is allowed to appear (as a positive
    claim, not in a ``not <claim>`` disclaimer) on an envelope
    claiming ``tier``.

    Args:
        token: a single forbidden-list token, lowercased. The function
            does not validate that the input is in either class; tokens
            not in either class are treated as allowed (this function
            is a tier-scoped REFUSAL helper, not an allow-list).
        tier: the envelope's claim tier.

    Returns:
        ``True`` if the token is allowed, ``False`` if refused. For
        consumers that want the inverse (refusal check), negate the
        return.

    Policy (ADR-025 §2.1):

    * Advisor-class token → always ``False`` (refused regardless of
      tier).
    * Solver-class token → ``False`` if tier is ``tier_1_candidate``;
      ``True`` if tier is ``tier_2_validated``.
    * Anything else → ``True`` (this function is not an allow-list;
      it only refuses tokens in the two known classes).
    """
    needle = token.lower()
    if needle in (t.lower() for t in FORBIDDEN_TOKENS_ADVISOR_CLASS):
        return False
    if needle in (t.lower() for t in FORBIDDEN_TOKENS_SOLVER_CLASS):
        return tier == "tier_2_validated"
    return True


def forbidden_tokens_for(tier: ClaimTier) -> tuple[str, ...]:
    """Return the tuple of tokens that are refused on ``tier``.

    Convenience accessor for consumers that want to iterate
    explicitly over the refusal set (e.g., to build a per-tier audit
    haystack scan).

    On ``tier_1_candidate`` returns the full 9-token union (matches
    the Phase 11 ADVISOR_FORBIDDEN_TOKENS behavior byte-identical).
    On ``tier_2_validated`` returns the 5 advisor-class tokens only.
    """
    if tier == "tier_2_validated":
        return FORBIDDEN_TOKENS_ADVISOR_CLASS
    return FORBIDDEN_TOKENS_ALL


__all__ = [
    "FORBIDDEN_TOKENS_ADVISOR_CLASS",
    "FORBIDDEN_TOKENS_SOLVER_CLASS",
    "FORBIDDEN_TOKENS_ALL",
    "is_token_allowed",
    "forbidden_tokens_for",
]
