"""FM-04a Phase 18 B — Tier 1 → Tier 2 posture pivot tests (ADR-025).

Pins:

* **M:-2** — :data:`CLAIM_TIER_REGISTRY` is the single SSOT for which
  case_id gets which tier (no duplicate registry elsewhere).
* **T:-4** — every Phase 18 B baseline registry entry is still
  ``tier_1_candidate`` (cylinder-pv-candidate stays Tier 1 until
  Slice C-or-later end-to-end ccx + analytical cross-check is wired).
* **C:-1** — advisor-class forbidden tokens refused regardless of
  tier; solver-class forbidden tokens refused on tier_1_candidate
  and allowed on tier_2_validated.
* **A:-3** — pre-Phase 18 envelopes without a ``tier`` field default
  to ``tier_1_candidate`` (back-compat read).

Phase 18 B is **additive**: the existing Phase 1-17 inline
``ADVISOR_FORBIDDEN_TOKENS`` tuple, ``CLAIM_TIER = "Tier 1 engineering
candidate"`` strings, and ``_audit_four_question_gate`` hard-raise
function are NOT removed. Tests below also verify the new SSOT modules
agree with those inline strings byte-identical (so a future de-
duplication is safe).
"""

from __future__ import annotations

import pytest
from app.services.reporting._claim_tier import (
    CLAIM_BOUNDARIES,
    CLAIM_TIER_LABELS,
    CLAIM_TIER_REGISTRY,
    CLAIM_TIER_TIER_1_CANDIDATE,
    CLAIM_TIER_TIER_2_VALIDATED,
    claim_boundary_for,
    claim_tier_label_for,
    get_claim_tier,
    register_tier_2_validated,
)
from app.services.reporting._forbidden_tokens import (
    FORBIDDEN_TOKENS_ADVISOR_CLASS,
    FORBIDDEN_TOKENS_ALL,
    FORBIDDEN_TOKENS_SOLVER_CLASS,
    forbidden_tokens_for,
    is_token_allowed,
)
from app.services.reporting.advisor_critique import (
    ADVISOR_FORBIDDEN_TOKENS,
)
from app.services.reporting.gate_audit import (
    FOUR_QUESTION_GATE_KEYS,
    GateAuditRecord,
    build_gate_audit_record,
)

from tests._test_utils import assert_tier1_trio, assert_tier2_trio


# ---------------------------------------------------------------------
# M:-2 — claim_tier SSOT
# ---------------------------------------------------------------------


def test_claim_tier_literal_values_pinned() -> None:
    """Closed set of tier values: a future maintainer adding a third
    tier value lands in :mod:`_claim_tier` (single SSOT)."""
    assert CLAIM_TIER_TIER_1_CANDIDATE == "tier_1_candidate"
    assert CLAIM_TIER_TIER_2_VALIDATED == "tier_2_validated"
    # Labels are exactly 2 — no orphan third value lurking.
    assert set(CLAIM_TIER_LABELS) == {
        "tier_1_candidate",
        "tier_2_validated",
    }
    assert set(CLAIM_BOUNDARIES) == {
        "tier_1_candidate",
        "tier_2_validated",
    }


def test_tier_1_label_byte_identical_to_phase_1_17_inline_constant() -> None:
    """Back-compat: Phases 1-17 inline ``CLAIM_TIER = "Tier 1
    engineering candidate"``; the new SSOT label must match exactly
    so existing envelopes don't drift."""
    assert (
        CLAIM_TIER_LABELS["tier_1_candidate"]
        == "Tier 1 engineering candidate"
    )


def test_tier_1_boundary_byte_identical_to_phase_1_17_boundary_string() -> None:
    """Back-compat: Phases 1-17 inline boundary strings (e.g.,
    ``"tier1_engineering_candidate; not_signed_validation;
    not_benchmark_agreement"``) must match the SSOT byte-identical."""
    assert (
        CLAIM_BOUNDARIES["tier_1_candidate"]
        == "tier1_engineering_candidate; not_signed_validation; "
        "not_benchmark_agreement"
    )


def test_tier_2_boundary_carries_not_signed_validation() -> None:
    """Tier 2 = real-solver-validated; NOT signed. The
    ``not_signed_validation`` clause MUST remain in the Tier 2
    boundary copy (ADR-025 §2)."""
    boundary = CLAIM_BOUNDARIES["tier_2_validated"]
    assert "not_signed_validation" in boundary
    assert "tier2_real_solver_validated" in boundary
    assert "cross_check_against_analytical" in boundary


@pytest.mark.parametrize(
    "case_id",
    [
        # Phase 19 B promoted cylinder-pv-candidate via the verdict
        # overlay — it is NO LONGER in the all-tier-1 set. The other
        # 4 cohort cases stay at the Phase 18 B baseline.
        "rod-wave-impact-candidate",
        "swing-arm-fatigue-candidate",
        "ballistic-plate-candidate",
        "leak-shell-candidate",
    ],
)
def test_un_cross_checked_cases_stay_tier_1(case_id: str) -> None:
    """T:-4 (Phase 18 B baseline preservation) — every case WITHOUT a
    `golden_samples/<case_id>/cross_check_verdict.yaml` artifact stays
    at tier_1_candidate. Phase 19 B promotion only fires for the case
    whose verdict overlay says PASS."""
    assert get_claim_tier(case_id) == "tier_1_candidate"


def test_phase_19b_cylinder_pv_promoted_to_tier_2_validated() -> None:
    """Phase 19 B verdict-overlay-driven promotion. The
    `golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml`
    artifact (written by `scripts/cross_check_cylinder_pv.py` against
    real ccx) records the analytical-vs-observed residual <
    CROSS_CHECK_TOLERANCE_PCT (5%). The registry loader reads it at
    module-load and promotes the case. This test pins that the
    promotion is in effect."""
    assert get_claim_tier("cylinder-pv-candidate") == "tier_2_validated"


def test_unregistered_case_id_defaults_to_tier_1_candidate() -> None:
    """A:-3 conservative back-compat: unknown cases read as Tier 1."""
    assert get_claim_tier("brand-new-unregistered-case") == "tier_1_candidate"


@pytest.mark.parametrize(
    "signed_id", ["GS-001", "GS-099", "GS-999"]
)
def test_get_claim_tier_refuses_signed_registry_shape(signed_id: str) -> None:
    """HF1.7a defense composes with the tier lookup: signed cases
    must not be reachable via this SSOT (they carry their own
    signed-validation provenance)."""
    with pytest.raises(ValueError, match="signed-registry"):
        get_claim_tier(signed_id)


def test_claim_tier_label_for_returns_tier_1_human_string() -> None:
    """``claim_tier_label_for`` composes the registry + labels; for
    cases still at the Phase 18 B baseline (no cross-check verdict)
    it returns the Phase 1-17 string. cylinder-pv-candidate was
    promoted by Phase 19 B; pick a still-tier-1 case for this pin."""
    assert (
        claim_tier_label_for("rod-wave-impact-candidate")
        == "Tier 1 engineering candidate"
    )


def test_claim_boundary_for_returns_tier_1_boundary_string() -> None:
    """``claim_boundary_for`` composes the registry + boundaries; for
    cases still at the Phase 18 B baseline (no cross-check verdict)
    it returns the Phase 1-17 string."""
    assert (
        claim_boundary_for("rod-wave-impact-candidate")
        == "tier1_engineering_candidate; not_signed_validation; "
        "not_benchmark_agreement"
    )


def test_claim_tier_label_for_returns_tier_2_label_after_promotion() -> None:
    """Phase 19 B — cylinder-pv-candidate carries the Tier 2 human
    label via the verdict overlay."""
    assert (
        claim_tier_label_for("cylinder-pv-candidate")
        == "Tier 2 real-solver validated"
    )


def test_claim_boundary_for_returns_tier_2_boundary_after_promotion() -> None:
    """Phase 19 B — cylinder-pv-candidate boundary copy carries the
    cross-check substantiation marker."""
    assert (
        claim_boundary_for("cylinder-pv-candidate")
        == "tier2_real_solver_validated; not_signed_validation; "
        "cross_check_against_analytical"
    )


def test_register_tier_2_validated_promotes_known_case() -> None:
    """Promotion seam works; registry mutates; subsequent lookup
    returns tier_2_validated. We pick a case that's still at
    tier_1_candidate baseline (Phase 19 B promoted cylinder-pv via
    the verdict overlay; pick rod-wave-impact here for an
    independent promotion test) and restore the entry after."""
    case_id = "rod-wave-impact-candidate"
    original = CLAIM_TIER_REGISTRY[case_id]
    try:
        register_tier_2_validated(case_id)
        assert get_claim_tier(case_id) == "tier_2_validated"
        assert (
            claim_tier_label_for(case_id)
            == "Tier 2 real-solver validated"
        )
        assert (
            claim_boundary_for(case_id)
            == CLAIM_BOUNDARIES["tier_2_validated"]
        )
    finally:
        CLAIM_TIER_REGISTRY[case_id] = original


def test_register_tier_2_validated_refuses_unknown_case() -> None:
    """The registry is the SSOT of which cases exist; promotion can't
    invent a new case_id."""
    with pytest.raises(KeyError, match="unknown case_id"):
        register_tier_2_validated("does-not-exist-candidate")


def test_register_tier_2_validated_refuses_signed_registry() -> None:
    """HF1.7a defense composes with promotion seam."""
    with pytest.raises(ValueError, match="signed-registry"):
        register_tier_2_validated("GS-042")


# ---------------------------------------------------------------------
# C:-1 — tier-scoped forbidden token policy
# ---------------------------------------------------------------------


def test_forbidden_tokens_advisor_class_pinned() -> None:
    """5 advisor-class tokens; pinned per token for byte-stability."""
    assert FORBIDDEN_TOKENS_ADVISOR_CLASS == (
        "production ready",
        "certified",
        "approved for service",
        "asme compliant",
        "signed off",
    )


def test_forbidden_tokens_solver_class_pinned() -> None:
    """4 solver-class tokens; pinned per token for byte-stability."""
    assert FORBIDDEN_TOKENS_SOLVER_CLASS == (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )


def test_forbidden_tokens_classes_are_disjoint() -> None:
    """No token in both classes; class-membership decides policy
    deterministically."""
    advisor_set = set(FORBIDDEN_TOKENS_ADVISOR_CLASS)
    solver_set = set(FORBIDDEN_TOKENS_SOLVER_CLASS)
    assert advisor_set.isdisjoint(solver_set)


def test_forbidden_tokens_all_is_union_byte_identical_to_phase_11() -> None:
    """Back-compat: the union of advisor + solver classes must match
    the Phase 11 ``ADVISOR_FORBIDDEN_TOKENS`` tuple AS A SET (order is
    a Phase 11 implementation choice; the set is what consumers
    semantically care about)."""
    assert set(FORBIDDEN_TOKENS_ALL) == set(ADVISOR_FORBIDDEN_TOKENS)


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS_ADVISOR_CLASS)
def test_advisor_class_token_refused_on_tier_1(token: str) -> None:
    assert is_token_allowed(token, tier="tier_1_candidate") is False


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS_ADVISOR_CLASS)
def test_advisor_class_token_refused_on_tier_2(token: str) -> None:
    """C:-1: advisor-class tokens carry reviewer authority and are
    refused REGARDLESS of tier."""
    assert is_token_allowed(token, tier="tier_2_validated") is False


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS_SOLVER_CLASS)
def test_solver_class_token_refused_on_tier_1(token: str) -> None:
    """Tier 1 = synthetic; solver-class claims have no provenance."""
    assert is_token_allowed(token, tier="tier_1_candidate") is False


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS_SOLVER_CLASS)
def test_solver_class_token_allowed_on_tier_2(token: str) -> None:
    """Tier 2 = real solver; solver-class claims carry analytical
    cross-check substantiation (per ADR-025 §2.1)."""
    assert is_token_allowed(token, tier="tier_2_validated") is True


def test_unknown_token_treated_as_allowed() -> None:
    """The function is a tier-scoped REFUSAL helper, not an allow-
    list. Tokens outside both classes are allowed."""
    assert is_token_allowed("hello world", tier="tier_1_candidate") is True
    assert is_token_allowed("hello world", tier="tier_2_validated") is True


def test_forbidden_tokens_for_tier_1_returns_full_union() -> None:
    """On tier_1_candidate, the refusal set is the full 9-token union
    (byte-identical with Phase 11 behavior)."""
    assert set(forbidden_tokens_for("tier_1_candidate")) == set(
        FORBIDDEN_TOKENS_ALL
    )


def test_forbidden_tokens_for_tier_2_returns_advisor_only() -> None:
    """On tier_2_validated, the refusal set shrinks to the 5
    advisor-class tokens."""
    assert forbidden_tokens_for("tier_2_validated") == (
        FORBIDDEN_TOKENS_ADVISOR_CLASS
    )


def test_is_token_allowed_handles_uppercase_input() -> None:
    """Tokens are stored lowercased; the helper lowercases input so
    casing doesn't sneak past the refusal check."""
    assert is_token_allowed("Production Ready", tier="tier_2_validated") is False
    assert is_token_allowed("ASME COMPLIANT", tier="tier_2_validated") is False


# ---------------------------------------------------------------------
# Reporting-only 4Q gate (ADR-025 §2.2)
# ---------------------------------------------------------------------


def test_four_question_gate_keys_byte_identical_to_phase_11() -> None:
    """Phase 11 SSOT must match Phase 18 sibling byte-identical."""
    from app.services.reporting.advisor_critique import (
        FOUR_QUESTION_GATE_KEYS as PHASE_11_KEYS,
    )

    assert FOUR_QUESTION_GATE_KEYS == PHASE_11_KEYS


def test_gate_audit_record_all_true_on_complete_true_gate() -> None:
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    record = build_gate_audit_record(gate)
    assert isinstance(record, GateAuditRecord)
    assert record.all_true is True
    assert set(record.true_keys) == set(FOUR_QUESTION_GATE_KEYS)
    assert record.false_keys == ()
    assert record.missing_keys == ()
    assert record.unknown_keys == ()
    assert record.non_boolean_keys == ()


def test_gate_audit_record_reports_false_without_raising() -> None:
    """The reporting-only sibling does NOT raise on a False answer
    (per ADR-025 §2.2); it surfaces the False key."""
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["advisor_only"] = False
    record = build_gate_audit_record(gate)
    assert record.all_true is False
    assert record.false_keys == ("advisor_only",)
    assert "advisor_only" not in record.true_keys


def test_gate_audit_record_reports_missing_keys() -> None:
    gate = {"llm_offline_ok": True}
    record = build_gate_audit_record(gate)
    assert record.all_true is False
    assert set(record.missing_keys) == {
        "artifacts_user_owned",
        "trustgate_explains",
        "advisor_only",
    }
    assert record.true_keys == ("llm_offline_ok",)


def test_gate_audit_record_reports_unknown_keys() -> None:
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["bogus_extra"] = True
    record = build_gate_audit_record(gate)
    assert record.all_true is True  # all required keys are True
    assert record.unknown_keys == ("bogus_extra",)


def test_gate_audit_record_reports_non_boolean_values() -> None:
    gate: dict[str, object] = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["advisor_only"] = "yes"  # string truthy, not bool
    record = build_gate_audit_record(gate)
    assert record.all_true is False
    assert record.non_boolean_keys == ("advisor_only",)


def test_gate_audit_record_is_frozen() -> None:
    record = build_gate_audit_record(
        {k: True for k in FOUR_QUESTION_GATE_KEYS}
    )
    with pytest.raises(Exception):
        record.all_true = False  # type: ignore[misc]


def test_gate_audit_preserves_raw_gate_provenance() -> None:
    """Record carries a frozen copy of the input dict so an auditor
    can see the raw answer set without mutation risk."""
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["advisor_only"] = False
    record = build_gate_audit_record(gate)
    raw_as_dict = dict(record.gate_raw)
    assert raw_as_dict == gate
    # The dataclass field itself is a tuple, not a mutable dict.
    assert isinstance(record.gate_raw, tuple)


# ---------------------------------------------------------------------
# Tier trio helpers (sanity checks)
# ---------------------------------------------------------------------


def test_assert_tier1_trio_passes_on_phase_1_17_envelope() -> None:
    envelope = {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; "
            "not_benchmark_agreement"
        ),
    }
    assert_tier1_trio(envelope)  # must not raise


def test_assert_tier1_trio_fails_on_tier_2_envelope() -> None:
    envelope = {
        "claim_tier": CLAIM_TIER_LABELS["tier_2_validated"],
        "claim_boundary": CLAIM_BOUNDARIES["tier_2_validated"],
    }
    with pytest.raises(AssertionError, match="Tier 1 engineering candidate"):
        assert_tier1_trio(envelope)


def test_assert_tier2_trio_passes_on_tier_2_envelope() -> None:
    envelope = {
        "claim_tier": CLAIM_TIER_LABELS["tier_2_validated"],
        "claim_boundary": CLAIM_BOUNDARIES["tier_2_validated"],
    }
    assert_tier2_trio(envelope)  # must not raise


def test_assert_tier2_trio_fails_on_tier_1_envelope() -> None:
    envelope = {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; "
            "not_benchmark_agreement"
        ),
    }
    with pytest.raises(AssertionError, match="Tier 2 real-solver validated"):
        assert_tier2_trio(envelope)


def test_assert_tier2_trio_fails_on_envelope_missing_cross_check_marker() -> None:
    """A Tier 2 envelope that drops ``cross_check_against_analytical``
    from its boundary copy is malformed and trips the trio."""
    envelope = {
        "claim_tier": CLAIM_TIER_LABELS["tier_2_validated"],
        "claim_boundary": (
            "tier2_real_solver_validated; not_signed_validation"
            # missing cross_check_against_analytical
        ),
    }
    with pytest.raises(AssertionError, match="cross_check_against_analytical"):
        assert_tier2_trio(envelope)


def test_assert_tier2_trio_fails_on_envelope_dropping_not_signed_marker() -> None:
    """Tier 2 is NOT signed; dropping ``not_signed_validation`` from
    the boundary trips the trio (defense against silently presenting
    a real-solver result as a signed-validation claim)."""
    envelope = {
        "claim_tier": CLAIM_TIER_LABELS["tier_2_validated"],
        "claim_boundary": (
            "tier2_real_solver_validated; cross_check_against_analytical"
            # missing not_signed_validation
        ),
    }
    with pytest.raises(AssertionError, match="not_signed_validation"):
        assert_tier2_trio(envelope)


# ---------------------------------------------------------------------
# ADR cross-reference smoke (no I/O; sanity that ADR exists in repo)
# ---------------------------------------------------------------------


def test_adr_025_exists_in_repo() -> None:
    """ADR-025 is the SSOT documentation for this slice; tests pin
    its presence so a delete-and-forget doesn't leave the code chain
    without rationale."""
    from pathlib import Path

    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    adr_path = repo_root / "docs" / "adr" / "ADR-025-tier2-transition.md"
    assert adr_path.is_file(), (
        f"ADR-025 not found at expected path {adr_path}"
    )
    body = adr_path.read_text(encoding="utf-8")
    # Pin the load-bearing structural anchors so a future edit
    # doesn't silently drop the tier discriminator section.
    assert "ClaimTier" in body
    assert "tier_1_candidate" in body
    assert "tier_2_validated" in body
    assert "HF1.7a" in body  # signed-registry preservation called out
