"""Shared test utilities for FM-04a Phase 15+ test suite.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 15 retrospective §7 (forbidden-token tuple as SSOT) +
§8 (``_assert_tier1_trio`` helper as SSOT). Each phase's test files
import from this module rather than inlining the same data + helpers.

A meta-test in this module's test pair (``tests/test_phase16_test_utils_ssot.py``)
enforces that Phase 16+ test files do NOT inline duplicate copies of
the SSOT (a future maintainer who tries to local-copy the 8-tuple
trips the meta-test).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------
# Forbidden positive-claim tokens (SSOT)
# ---------------------------------------------------------------------

FORBIDDEN_POSITIVE_CLAIM_TOKENS_9: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    "production ready",
    "certified",
    "approved for service",
    "asme compliant",
    "signed off",
)
"""Full 9-token forbidden-positive-claim list (Phase 14 retro §1 + Phase
15 C). Each token MUST NOT appear in any new module / methodology doc
/ rendered envelope outside ``not <claim>`` / ``no <claim>`` form.
``certified`` IS in this list because the most-strict source-file grep
applies it. The narrower 8-tuple
``FORBIDDEN_POSITIVE_CLAIM_TOKENS_8`` skips ``certified`` for
envelope-rendering audits where CLAIM_BOUNDARY variants legitimately
use ``not_signed_validation_or_certified_simulation``."""

FORBIDDEN_POSITIVE_CLAIM_TOKENS_8: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    "production ready",
    "approved for service",
    "asme compliant",
    "signed off",
)
"""Narrower 8-token forbidden-positive-claim list for envelope-
rendering audits. Skips ``certified`` because CLAIM_BOUNDARY variants
carry ``not_signed_validation_or_certified_simulation`` legitimately
(the ``certified`` token there is inside ``not_signed_validation_or_``
+ ``_simulation`` markers, not a standalone positive claim). For
source-file grep on new modules, use
``FORBIDDEN_POSITIVE_CLAIM_TOKENS_9`` to apply the stricter rule."""


# ---------------------------------------------------------------------
# Tier 1 disclaimer trio audit (SSOT)
# ---------------------------------------------------------------------


def assert_tier1_trio(envelope: dict[str, Any], *, check_impact: bool = True) -> None:
    """Audit a rendered envelope for the Tier 1 disclaimer trio.

    Args:
        envelope: parsed JSON dict from a Tier 1 candidate endpoint.
        check_impact: when ``True``, also asserts ``claim_impact``
            carries one of the ``not <claim>`` tokens. Set to ``False``
            for envelopes that legitimately omit ``claim_impact`` (the
            Phase 15 D Journey 2 PV cases under the linear_static_pv
            rubric).

    Asserts:
        * ``claim_tier == "Tier 1 engineering candidate"``.
        * ``claim_boundary`` carries ``not_signed_validation`` AND
          ``not_benchmark_agreement``.
        * (optional) ``claim_impact`` carries ``not signed validation``
          OR ``not benchmark agreement``.

    Raises ``AssertionError`` with a load-bearing diagnostic on
    failure.
    """
    claim_tier = envelope.get("claim_tier")
    assert claim_tier == "Tier 1 engineering candidate", (
        f"claim_tier missing or wrong: {claim_tier!r}"
    )
    boundary = envelope.get("claim_boundary", "")
    assert "not_signed_validation" in boundary and "not_benchmark_agreement" in boundary, (
        f"claim_boundary missing tokens: {boundary!r}"
    )
    if check_impact:
        impact = envelope.get("claim_impact", "")
        assert (
            "not signed validation" in impact.lower() or "not benchmark agreement" in impact.lower()
        ), f"claim_impact missing tokens: {impact!r}"


# ---------------------------------------------------------------------
# Forbidden-token grep helper (SSOT)
# ---------------------------------------------------------------------


def assert_no_forbidden_positive_claims(
    text: str,
    *,
    tokens: tuple[str, ...] = FORBIDDEN_POSITIVE_CLAIM_TOKENS_8,
    allow_no: bool = True,
) -> None:
    """Grep ``text`` for the forbidden positive-claim tokens; each
    occurrence MUST be in ``not <claim>`` / ``no <claim>`` form.

    Args:
        text: the source text to grep (e.g., a rendered JSON envelope
            string, a module docstring, a methodology doc).
        tokens: the forbidden-token tuple to enforce. Defaults to the
            8-tuple (envelope-rendering audit); pass
            ``FORBIDDEN_POSITIVE_CLAIM_TOKENS_9`` for strict source-file
            grep.
        allow_no: when ``True``, both ``not <claim>`` and ``no <claim>``
            prefixes are accepted (the ``no <claim>`` form appears in
            "Forbidden wording" module docstrings legitimately).

    Raises ``AssertionError`` with a load-bearing diagnostic on
    failure.
    """
    lowered = text.lower()
    for token in tokens:
        idx = lowered.find(token)
        while idx != -1:
            prefix_raw = lowered[max(0, idx - 8) : idx]
            prefix = prefix_raw.replace("`", " ").replace('"', " ").strip()
            allowed = prefix.endswith("not")
            if allow_no:
                allowed = allowed or prefix.endswith("no")
            assert allowed, (
                f"forbidden token {token!r} appears outside the "
                f"negated form; context: "
                f"...{lowered[max(0, idx - 30) : idx + len(token) + 30]}..."
            )
            idx = lowered.find(token, idx + 1)
