"""FM-04a Phase 16 D — SSOT meta-test for ``tests/_test_utils``.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 15 retrospective §7 (forbidden-token 8-tuple SSOT)
and §8 (Tier 1 disclaimer trio audit helper SSOT).

What this audit enforces
------------------------

A future maintainer who *re-inlines* either piece of the SSOT in a
Phase 15+ test file trips this meta-test. The intent is to keep
:mod:`tests._test_utils` as the load-bearing single source of truth
across every Phase 15+ journey + slice test.

Two anti-gaming forbidden shapes (LEXICAL detection — the meta-test
looks for the SSOT HELPER bodies being copy-pasted, NOT ad-hoc
inline 3-assert blocks in unit tests):

* **forbidden-token tuple literal** — any Phase 15+ test file
  containing a parenthesized tuple-literal carrying at least 5 of
  the 9 SSOT tokens as comma-separated string entries (the
  fingerprint of a duplicated SSOT tuple). Ad-hoc usage of any
  single token as an expected-value string in an assertion does
  NOT trip this because the fingerprint requires 5+ tokens
  together in a `(... , ... , ...)` shape.
* **trio-audit helper function definition** — any Phase 15+ test
  file that DEFINES a function named ``_assert_tier1_trio`` or
  ``assert_tier1_trio`` LOCALLY without immediately delegating to
  the SSOT helper of the same name. Thin per-file wrappers that
  call ``assert_tier1_trio(envelope, check_impact=False)`` are
  accepted because they DELEGATE to the SSOT rather than
  re-implementing the 3-assert body. Ad-hoc inline 3-assert
  blocks within individual test functions (not wrapped in a
  helper) are NOT in scope — the SSOT exists to consolidate
  HELPERS, not to ban inline assertions.

Files audited: ``tests/test_phase15_*.py`` and ``tests/test_phase16_*.py``
modulo the SSOT module itself + this audit file (which legitimately
references the tokens by name to document the discipline).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._test_utils import (
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_8,
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_9,
    assert_no_forbidden_positive_claims,
    assert_tier1_trio,
)

TESTS_DIR = Path(__file__).resolve().parent
SSOT_MODULE_PATH = TESTS_DIR / "_test_utils" / "__init__.py"
THIS_FILE = Path(__file__).resolve()

# Files in scope for the meta-test: every Phase 15+ test file living
# directly under ``tests/`` (NOT under ``tests/_test_utils/``).
PHASE_15_PLUS_GLOBS: tuple[str, ...] = (
    "test_phase15_*.py",
    "test_phase16_*.py",
)

# Files exempt from the audit:
EXEMPT_FILES: frozenset[Path] = frozenset(
    {
        THIS_FILE,
        SSOT_MODULE_PATH,
    }
)

# Tokens that fingerprint the SSOT forbidden-token tuple. A file
# carrying >= TOKEN_TUPLE_FINGERPRINT_MIN of these as quoted string
# entries (each followed by a comma — the tuple-item shape) is
# inlining the SSOT. Ad-hoc single-token usage in assertion
# expected-values does NOT trip this.
TOKEN_TUPLE_FINGERPRINT: tuple[str, ...] = (
    '"validated against",',
    '"perforation completed",',
    '"bullet-through-steel complete",',
    '"validated physics",',
    '"production ready",',
    '"approved for service",',
    '"asme compliant",',
    '"signed off",',
)
TOKEN_TUPLE_FINGERPRINT_MIN = 5

# Function-definition prefixes that signal a local trio-audit helper.
# A file containing one of these AND also delegating to the SSOT
# (``from tests._test_utils`` + ``assert_tier1_trio(``) is a
# thin-wrapper shape and is ACCEPTED.
LOCAL_TRIO_DEF_PREFIXES: tuple[str, ...] = (
    "def _assert_tier1_trio(",
    "def assert_tier1_trio(",
)


def _gather_phase15_plus_files() -> list[Path]:
    files: list[Path] = []
    for pattern in PHASE_15_PLUS_GLOBS:
        files.extend(TESTS_DIR.glob(pattern))
    return sorted(p for p in files if p not in EXEMPT_FILES)


# ---------------------------------------------------------------------
# M:-1 / V:-3 — SSOT module is importable + exports the canonical names
# ---------------------------------------------------------------------


def test_ssot_module_exports_canonical_names() -> None:
    """The SSOT module exposes the 4 canonical names that Phase 15+
    consumers import. A rename that drops one of these trips this
    pin BEFORE downstream consumers break at import time."""
    assert isinstance(FORBIDDEN_POSITIVE_CLAIM_TOKENS_8, tuple)
    assert isinstance(FORBIDDEN_POSITIVE_CLAIM_TOKENS_9, tuple)
    assert callable(assert_no_forbidden_positive_claims)
    assert callable(assert_tier1_trio)


def test_ssot_token_tuple_lengths_pinned() -> None:
    """The 8-tuple has 8 entries; the 9-tuple has 9 entries (the
    extra entry is ``certified``). A future drift in the tuple
    contents trips this pin."""
    assert len(FORBIDDEN_POSITIVE_CLAIM_TOKENS_8) == 8, FORBIDDEN_POSITIVE_CLAIM_TOKENS_8
    assert len(FORBIDDEN_POSITIVE_CLAIM_TOKENS_9) == 9, FORBIDDEN_POSITIVE_CLAIM_TOKENS_9
    assert "certified" in FORBIDDEN_POSITIVE_CLAIM_TOKENS_9
    assert "certified" not in FORBIDDEN_POSITIVE_CLAIM_TOKENS_8
    # The 8-tuple is a strict subset of the 9-tuple.
    assert set(FORBIDDEN_POSITIVE_CLAIM_TOKENS_8).issubset(set(FORBIDDEN_POSITIVE_CLAIM_TOKENS_9))


# ---------------------------------------------------------------------
# M:-2 — no Phase 15+ test file inlines the forbidden-token tuple
# ---------------------------------------------------------------------


def test_no_phase15_plus_file_inlines_forbidden_token_tuple() -> None:
    """No Phase 15+ test file may carry the FINGERPRINT shape of the
    SSOT forbidden-token tuple (>= 5 of the 9 tokens appearing as
    comma-suffixed string-literal tuple entries). Ad-hoc usage of
    any single token as an assertion expected-value does NOT trip
    this because the fingerprint requires 5+ entries in tuple-shape
    together — that's the shape that names the SSOT
    :data:`FORBIDDEN_POSITIVE_CLAIM_TOKENS_8` /
    :data:`FORBIDDEN_POSITIVE_CLAIM_TOKENS_9` tuple."""
    offenders: list[tuple[Path, int]] = []
    for path in _gather_phase15_plus_files():
        text = path.read_text(encoding="utf-8")
        hits = sum(1 for sentinel in TOKEN_TUPLE_FINGERPRINT if sentinel in text)
        if hits >= TOKEN_TUPLE_FINGERPRINT_MIN:
            offenders.append((path, hits))
    rel = [(str(p.relative_to(TESTS_DIR.parent)), n) for p, n in offenders]
    assert not offenders, (
        f"Phase 15+ test files re-inlining the forbidden-token "
        f"SSOT tuple (Phase 15 retro §7 violation; >= "
        f"{TOKEN_TUPLE_FINGERPRINT_MIN} of 9 fingerprint tokens "
        f"present in tuple-shape): {rel}; import "
        f"FORBIDDEN_POSITIVE_CLAIM_TOKENS_8 / _9 from "
        f"tests._test_utils instead."
    )


# ---------------------------------------------------------------------
# M:-2 — no Phase 15+ test file inlines the trio-audit body
# ---------------------------------------------------------------------


def test_no_phase15_plus_file_inlines_trio_audit_helper() -> None:
    """No Phase 15+ test file may DEFINE a local
    ``_assert_tier1_trio`` / ``assert_tier1_trio`` helper function
    without delegating to the SSOT. Thin per-file wrappers that
    call ``assert_tier1_trio(...)`` AND import from
    ``tests._test_utils`` are accepted; they route the audit
    through the SSOT helper, which is the load-bearing single
    source of truth.

    Ad-hoc inline 3-assert blocks inside individual test functions
    are NOT in scope — the Phase 15 retro §8 closure consolidates
    HELPERS, not all inline assertions."""
    offenders: list[tuple[Path, str]] = []
    for path in _gather_phase15_plus_files():
        text = path.read_text(encoding="utf-8")
        defines_local = any(prefix in text for prefix in LOCAL_TRIO_DEF_PREFIXES)
        if not defines_local:
            continue
        # A thin wrapper delegating to the SSOT is acceptable: it
        # MUST both import from the SSOT module AND call the SSOT
        # helper somewhere in the file.
        delegates = "from tests._test_utils" in text and "assert_tier1_trio(" in text
        if delegates:
            continue
        offenders.append((path, "local helper defined without SSOT delegation"))
    assert not offenders, (
        f"Phase 15+ test files defining a local Tier 1 trio audit "
        f"helper without delegating to the SSOT "
        f"(Phase 15 retro §8 violation): {offenders}; "
        f"import assert_tier1_trio from tests._test_utils instead."
    )


# ---------------------------------------------------------------------
# C:-8 — SSOT helper enforces the negated-form contract
# ---------------------------------------------------------------------


def test_ssot_grep_helper_accepts_negated_form() -> None:
    """The SSOT grep helper accepts ``not <claim>`` / ``no <claim>``
    occurrences silently. Sanity-pin so a future drift in the
    negation-detection logic trips this BEFORE downstream consumers
    fail at module-load time."""
    accepted_text = (
        "this envelope is not signed off and carries no perforation completed "
        "claim. not validated against any benchmark; not validated physics."
    )
    # Should NOT raise.
    assert_no_forbidden_positive_claims(accepted_text)


def test_ssot_grep_helper_rejects_bare_positive_claim() -> None:
    """The SSOT grep helper RAISES on a bare forbidden token. A
    future drift that accepts a bare positive claim would trip this
    pin BEFORE silently letting a Tier 1 envelope through with a
    falsified claim."""
    offending_text = "this candidate is production ready and approved for service."
    with pytest.raises(AssertionError):
        assert_no_forbidden_positive_claims(offending_text)


def test_ssot_grep_helper_strict_9_tuple_rejects_certified() -> None:
    """When called with the 9-tuple, a bare ``certified`` occurrence
    is REJECTED (used for source-file grep). The 8-tuple default
    SKIPS ``certified`` so the CLAIM_BOUNDARY token
    ``not_signed_validation_or_certified_simulation`` does NOT trip
    envelope audits."""
    offending = "this candidate is certified for service."
    # 9-tuple rejects.
    with pytest.raises(AssertionError):
        assert_no_forbidden_positive_claims(offending, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_9)
    # 8-tuple accepts (no ``certified`` in the tuple).
    assert_no_forbidden_positive_claims(offending, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_8)


# ---------------------------------------------------------------------
# C:-8 — Tier 1 trio audit helper rejects missing fields
# ---------------------------------------------------------------------


def test_ssot_trio_audit_rejects_missing_tier() -> None:
    """The SSOT trio audit raises AssertionError when claim_tier is
    missing or wrong. A future drift that accepts a wrong-tier
    envelope trips this pin."""
    bad_envelope = {
        "claim_tier": "Tier 2 benchmark validation",
        "claim_boundary": "not_signed_validation_and_not_benchmark_agreement",
        "claim_impact": "not signed validation; not benchmark agreement",
    }
    with pytest.raises(AssertionError):
        assert_tier1_trio(bad_envelope)


def test_ssot_trio_audit_rejects_missing_boundary_tokens() -> None:
    """The SSOT trio audit raises when claim_boundary is missing the
    load-bearing tokens (``not_signed_validation`` AND
    ``not_benchmark_agreement``)."""
    bad_envelope = {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "no_disclaimers",
        "claim_impact": "not signed validation",
    }
    with pytest.raises(AssertionError):
        assert_tier1_trio(bad_envelope)


def test_ssot_trio_audit_check_impact_false_skips_impact() -> None:
    """``check_impact=False`` skips the claim_impact audit (the
    linear_static_pv cases under Phase 15 D Journey 2's rubric
    legitimately omit a canonical impact token; the boundary +
    tier still carry the discipline)."""
    pv_shape = {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "not_signed_validation_and_not_benchmark_agreement",
        # claim_impact intentionally absent.
    }
    # Should NOT raise with check_impact=False.
    assert_tier1_trio(pv_shape, check_impact=False)
    # But DOES raise with check_impact=True (default).
    with pytest.raises(AssertionError):
        assert_tier1_trio(pv_shape)


# ---------------------------------------------------------------------
# V:-3 — the SSOT module path is stable + the file is non-empty
# ---------------------------------------------------------------------


def test_ssot_module_exists_and_is_non_empty() -> None:
    """The SSOT module lives at ``tests/_test_utils/__init__.py``
    and is non-trivial. A future drift that moves the module (or
    accidentally truncates it) trips this pin BEFORE downstream
    imports fail."""
    assert SSOT_MODULE_PATH.is_file(), SSOT_MODULE_PATH
    contents = SSOT_MODULE_PATH.read_text(encoding="utf-8")
    assert len(contents) > 1000, (
        f"SSOT module unexpectedly short ({len(contents)} bytes); path: {SSOT_MODULE_PATH}"
    )
    assert "FORBIDDEN_POSITIVE_CLAIM_TOKENS_9" in contents
    assert "FORBIDDEN_POSITIVE_CLAIM_TOKENS_8" in contents
    assert "def assert_tier1_trio" in contents
    assert "def assert_no_forbidden_positive_claims" in contents
