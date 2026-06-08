"""Phase 11 B — AdvisorCritique schema + stub advisor + four-question gate.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins binding rubric (anti-gaming guards) from
``.planning/FM-04A_PHASE11_BLUEPRINT.md`` §4:

* **M:-2**: every closed-set tuple and forbidden token list is pinned by
  identifier from the SSOT module.
* **T:-5**: every new advisor-specific forbidden token has its own test
  (the 5 Phase-11 additions: ``production ready``, ``certified``,
  ``approved for service``, ``ASME compliant``, ``signed off``).
* **C:-8**: the Tier 1 claim banners (``claim_tier`` / ``claim_boundary``
  / ``claim_impact``) appear on every emitted envelope.
* **C:-10**: the four-question gate is mandatory; missing / non-boolean
  / False = ValueError at envelope construction.
* **A:-2**: stub advisor must not produce a vacuous payload — a
  trust_score < 70 input MUST surface at least one mesh_quality_concern.
* **A:-3**: forbidden-claim audit refuses the envelope (rather than
  silently scrubbing).
* **E:-2**: schema_version pinned at 1.0.0 starting baseline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from app.services.reporting._schema_versions import (
    ADVISOR_CRITIQUE_SCHEMA_VERSION,
)
from app.services.reporting.advisor_critique import (
    ADVISOR_FORBIDDEN_TOKENS,
    ADVISOR_STATUS_TUPLE,
    CLAIM_BOUNDARY,
    CLAIM_IMPACT_DEFAULT,
    CLAIM_TIER,
    FOUR_QUESTION_GATE_KEYS,
    AdvisorContext,
    AdvisorCritique,
    AdvisorProvider,
    AdvisorRawCritique,
    StubAdvisor,
    _critique_to_dict,
    build_advisor_critique,
    render_advisor_critique_json,
)

# ---------------------------------------------------------------------
# fixtures + helpers
# ---------------------------------------------------------------------


def _context(
    *,
    case_id: str = "GS-PV-cyl-candidate",
    snapshot_label: str = "2026-05-16T00-00-00Z",
    trust_score: int | None = 83,
    completeness_score: int | None = 100,
    completeness_analysis_type: str | None = "linear_static_pv",
    energy_audit_status: str | None = "closed_aggregate",
    convergence_kind: str | None = "linear_static",
    convergence_combined_verdict: str | None = "candidate_observed_stable",
) -> AdvisorContext:
    return AdvisorContext(
        case_id=case_id,
        snapshot_label=snapshot_label,
        trust_score=trust_score,
        completeness_score=completeness_score,
        completeness_analysis_type=completeness_analysis_type,
        energy_audit_status=energy_audit_status,
        convergence_kind=convergence_kind,
        convergence_combined_verdict=convergence_combined_verdict,
        extra={},
    )


_FROZEN_NOW = datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC)


class _UnavailableProvider:
    """Backend that fails ``is_available()`` to exercise the fallback path."""

    name = "test-unavailable-provider"

    def is_available(self) -> bool:
        return False

    def produce(self, context: AdvisorContext) -> AdvisorRawCritique:  # pragma: no cover
        raise AssertionError("produce() must not be called when is_available() == False")


class _ScriptedProvider:
    """Backend that returns a caller-supplied raw critique. Used to inject
    a controlled raw payload so we can exercise envelope-level audits in
    isolation from any rule-based stub behaviour."""

    name = "test-scripted-provider"

    def __init__(self, raw: AdvisorRawCritique) -> None:
        self._raw = raw

    def is_available(self) -> bool:
        return True

    def produce(self, context: AdvisorContext) -> AdvisorRawCritique:
        return self._raw


# ---------------------------------------------------------------------
# E:-2 / M baseline pins
# ---------------------------------------------------------------------


def test_advisor_critique_schema_version_pinned_at_phase13_a_baseline() -> None:
    """Phase 11 B started at 1.0.0; Phase 13 A MINOR bump to 1.1.0
    adds the optional ``refused_claims`` field. The SSOT pin tracks
    the current version; the prior version is preserved in the
    bump-history docstring on ``_schema_versions.py``."""
    assert ADVISOR_CRITIQUE_SCHEMA_VERSION == "1.1.0"


def test_advisor_status_tuple_closed_set() -> None:
    """``advisor_status`` is a closed enum. Adding a value REQUIRES
    bumping this pin in lockstep (and a frontend mirror update)."""
    assert ADVISOR_STATUS_TUPLE == ("online", "offline", "stub")
    assert len(set(ADVISOR_STATUS_TUPLE)) == len(ADVISOR_STATUS_TUPLE)


def test_four_question_gate_keys_pinned_exactly() -> None:
    """The 4-Q gate keys ARE the project north-star posture statement;
    renaming any key without an SSOT update is a M:-2 drift defect."""
    assert FOUR_QUESTION_GATE_KEYS == (
        "llm_offline_ok",
        "artifacts_user_owned",
        "trustgate_explains",
        "advisor_only",
    )


def test_advisor_forbidden_tokens_extends_base_with_phase11_additions() -> None:
    """Token list extends Tier 1 base (4 tokens) with 5 Phase-11
    advisor-specific positive verbs. Total = 9."""
    base = {
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    }
    phase11 = {
        "production ready",
        "certified",
        "approved for service",
        "asme compliant",
        "signed off",
    }
    assert set(ADVISOR_FORBIDDEN_TOKENS) == base | phase11
    assert len(ADVISOR_FORBIDDEN_TOKENS) == 9


# ---------------------------------------------------------------------
# Envelope construction — happy path
# ---------------------------------------------------------------------


def test_envelope_carries_schema_version_and_claim_banners() -> None:
    """C:-8 — every emitted envelope stamps the Tier 1 disclaimer trio."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    assert envelope.schema_version == ADVISOR_CRITIQUE_SCHEMA_VERSION
    assert envelope.claim_tier == CLAIM_TIER
    assert envelope.claim_boundary == CLAIM_BOUNDARY
    assert envelope.claim_impact == CLAIM_IMPACT_DEFAULT
    assert "not signed validation" in envelope.claim_impact
    assert "not benchmark agreement" in envelope.claim_impact


def test_envelope_rendered_json_round_trips_with_pinned_keys() -> None:
    """The JSON envelope shape is part of the schema 1.0.0 contract."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    rendered = render_advisor_critique_json(envelope)
    parsed = json.loads(rendered)
    # Phase 13 A — schema bumped 1.0.0 -> 1.1.0; the centralized
    # SSOT pin lives in tests/test_schema_versions_stamping.py.
    assert parsed["schema_version"] == ADVISOR_CRITIQUE_SCHEMA_VERSION
    assert parsed["case_id"] == "GS-PV-cyl-candidate"
    assert parsed["snapshot_label"] == "2026-05-16T00-00-00Z"
    assert parsed["advisor_status"] in ADVISOR_STATUS_TUPLE
    assert parsed["advisor_backend"] == "stub-rule-based"
    assert isinstance(parsed["four_question_gate"], dict)
    assert isinstance(parsed["mesh_quality_concerns"], list)
    assert isinstance(parsed["boundary_condition_questions"], list)
    assert isinstance(parsed["failure_modes_to_consider"], list)
    assert isinstance(parsed["unhandled_load_cases"], list)


def test_default_provider_is_stub_with_status_stub() -> None:
    """provider=None → StubAdvisor; advisor_status='stub' (caller-chosen)."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    assert envelope.advisor_status == "stub"
    assert envelope.advisor_backend == "stub-rule-based"
    assert envelope.degrade_reason is None


# ---------------------------------------------------------------------
# Stub advisor behaviour — A:-2 vacuous-stub guard
# ---------------------------------------------------------------------


def test_stub_advisor_is_runtime_checkable_advisor_provider() -> None:
    """``StubAdvisor`` must satisfy the AdvisorProvider Protocol so
    callers can swap LLMAdvisor in without conditional typing."""
    assert isinstance(StubAdvisor(), AdvisorProvider)


def test_stub_advisor_low_trust_score_surfaces_mesh_concern() -> None:
    """A:-2 — anti-vacuous stub guard. trust_score < 70 must surface
    at least one mesh_quality_concern that references the score."""
    ctx = _context(trust_score=42)
    envelope = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    assert len(envelope.mesh_quality_concerns) >= 1
    joined = "\n".join(envelope.mesh_quality_concerns).lower()
    assert "trust_score" in joined
    assert "42" in joined


def test_stub_advisor_non_closed_energy_audit_surfaces_bc_question() -> None:
    """Same A:-2 family — non-closed_aggregate energy_audit must surface
    at least one boundary_condition_question, AND that question must
    cite the actual status value (not a generic prompt)."""
    ctx = _context(energy_audit_status="open_residual")
    envelope = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    assert len(envelope.boundary_condition_questions) >= 1
    joined = "\n".join(envelope.boundary_condition_questions).lower()
    assert "open_residual" in joined


def test_stub_advisor_linear_static_surfaces_failure_modes() -> None:
    """linear_static cases must surface the linear-static blind-spot
    list (plasticity / contact / large displacement / etc.) — a
    reviewer needs that prompt to catch out-of-scope load cases."""
    ctx = _context(convergence_kind="linear_static")
    envelope = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    assert len(envelope.failure_modes_to_consider) >= 1
    joined = "\n".join(envelope.failure_modes_to_consider).lower()
    assert "plasticity" in joined or "contact" in joined


def test_stub_advisor_explicit_dynamics_surfaces_mass_scaling_check() -> None:
    """explicit_dynamics cases must surface a mass-scaling / dt
    convergence question — distinct from the linear_static branch."""
    ctx = _context(
        convergence_kind="explicit_dynamics",
        convergence_combined_verdict="candidate_observed_stable",
        energy_audit_status="closed_aggregate",
    )
    envelope = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    failures = "\n".join(envelope.failure_modes_to_consider).lower()
    questions = "\n".join(envelope.boundary_condition_questions).lower()
    assert "mass scaling" in failures or "mass-scaled" in failures
    assert "dt" in questions or "hourglass" in questions


def test_stub_advisor_always_surfaces_unhandled_load_case_prompt() -> None:
    """The stub does not know which load cases were omitted; it asks
    rather than fabricating. Every payload must carry an open
    enumeration question so the reviewer is reminded."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    assert len(envelope.unhandled_load_cases) >= 1
    assert "enumerate" in envelope.unhandled_load_cases[0].lower()


def test_stub_advisor_deterministic_for_fixed_input() -> None:
    """Same context twice → identical content lists. (generated_at_utc
    differs in production, so we pin it via now_utc.)"""
    ctx = _context(trust_score=55, energy_audit_status="open_residual")
    a = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    b = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    assert a.mesh_quality_concerns == b.mesh_quality_concerns
    assert a.boundary_condition_questions == b.boundary_condition_questions
    assert a.failure_modes_to_consider == b.failure_modes_to_consider
    assert a.unhandled_load_cases == b.unhandled_load_cases
    assert a.generated_at_utc == b.generated_at_utc


def test_stub_advisor_high_trust_score_still_emits_mesh_baseline_prompt() -> None:
    """Even when no trust-score-correlated concern fires, the stub must
    not emit an empty mesh_quality_concerns list (anti-vacuous A:-2
    extension)."""
    ctx = _context(trust_score=98, completeness_score=100)
    envelope = build_advisor_critique(ctx, now_utc=_FROZEN_NOW)
    assert len(envelope.mesh_quality_concerns) >= 1


# ---------------------------------------------------------------------
# Provider fallback — degrade_reason + advisor_status='offline'
# ---------------------------------------------------------------------


def test_unavailable_provider_falls_back_to_stub_with_offline_status() -> None:
    """provider.is_available() == False → stub fallback, status='offline',
    degrade_reason names the provider that was unavailable."""
    envelope = build_advisor_critique(
        _context(),
        provider=_UnavailableProvider(),
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "offline"
    assert envelope.advisor_backend == "stub-rule-based"
    assert envelope.degrade_reason is not None
    assert "test-unavailable-provider" in envelope.degrade_reason
    assert "is_available" in envelope.degrade_reason


def test_available_scripted_provider_is_used_with_online_status() -> None:
    """is_available() == True → its raw critique reaches the envelope."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("scripted mesh concern",),
        boundary_condition_questions=("scripted bc question",),
        failure_modes_to_consider=("scripted failure mode",),
        unhandled_load_cases=("scripted load case",),
        four_question_gate={k: True for k in FOUR_QUESTION_GATE_KEYS},
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "online"
    assert envelope.advisor_backend == "test-scripted-provider"
    assert envelope.mesh_quality_concerns == ("scripted mesh concern",)
    assert envelope.degrade_reason is None


# ---------------------------------------------------------------------
# C:-10 — four-question gate audit
# ---------------------------------------------------------------------


def _raw_with_gate(gate: dict[str, Any]) -> AdvisorRawCritique:
    return AdvisorRawCritique(
        mesh_quality_concerns=("m",),
        boundary_condition_questions=("b",),
        failure_modes_to_consider=("f",),
        unhandled_load_cases=("u",),
        four_question_gate=gate,
        degrade_reason=None,
    )


@pytest.mark.parametrize("missing_key", list(FOUR_QUESTION_GATE_KEYS))
def test_four_question_gate_refuses_each_missing_key(missing_key: str) -> None:
    """C:-10 — every single key is mandatory. Drop any one → ValueError."""
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS if k != missing_key}
    raw = _raw_with_gate(gate)
    with pytest.raises(ValueError, match="missing keys"):
        build_advisor_critique(
            _context(),
            provider=_ScriptedProvider(raw),
            now_utc=_FROZEN_NOW,
        )


def test_four_question_gate_refuses_unknown_key() -> None:
    """An extra key is also a defect — the SSOT tuple is closed."""
    gate: dict[str, Any] = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["rogue_key"] = True
    raw = _raw_with_gate(gate)
    with pytest.raises(ValueError, match="unknown keys"):
        build_advisor_critique(
            _context(),
            provider=_ScriptedProvider(raw),
            now_utc=_FROZEN_NOW,
        )


def test_four_question_gate_refuses_non_boolean_value() -> None:
    """Non-bool value (e.g. truthy string) is refused at construction."""
    gate: dict[str, Any] = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["llm_offline_ok"] = "yes"  # truthy but not bool
    raw = _raw_with_gate(gate)
    with pytest.raises(ValueError, match="non-boolean"):
        build_advisor_critique(
            _context(),
            provider=_ScriptedProvider(raw),
            now_utc=_FROZEN_NOW,
        )


def test_four_question_gate_refuses_false_answer() -> None:
    """A False answer means the system has drifted out of advisor-only
    posture; we refuse the envelope rather than emit it. C:-10."""
    gate: dict[str, Any] = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    gate["advisor_only"] = False
    raw = _raw_with_gate(gate)
    with pytest.raises(ValueError, match="False answer"):
        build_advisor_critique(
            _context(),
            provider=_ScriptedProvider(raw),
            now_utc=_FROZEN_NOW,
        )


# ---------------------------------------------------------------------
# T:-5 / A:-3 — per-token forbidden-claim audit
# ---------------------------------------------------------------------


@pytest.mark.parametrize("token", list(ADVISOR_FORBIDDEN_TOKENS))
def test_forbidden_claim_audit_fires_per_token(token: str) -> None:
    """T:-5 — each forbidden token (base 4 + Phase-11 5) has its own
    test that injects the token *outside* the ``not <claim>`` form
    and confirms the envelope refuses the OFFENDING CONTENT.

    Phase 13 A contract evolution: the per-section filter REPLACES
    the offending entry with a structured marker in
    ``refused_claims`` (was: raise at construction in Phase 11 B).
    This is a strictly stronger guarantee — the original positive
    claim never reaches the rendered surface AT ALL, whereas the
    Phase 11 raise behavior depended on the envelope-level audit
    catching it. The per-token T:-5 anti-gaming guard remains
    binding: each token must lead to a refusal, with the refusal now
    surfaced as a structured marker rather than an exception.
    """
    from app.services.reporting.advisor_critique import REFUSED_CLAIM_MARKER_PREFIX

    raw = AdvisorRawCritique(
        mesh_quality_concerns=(f"The structure is {token} for service.",),
        boundary_condition_questions=("b",),
        failure_modes_to_consider=("f",),
        unhandled_load_cases=("u",),
        four_question_gate={k: True for k in FOUR_QUESTION_GATE_KEYS},
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    # Phase 13 A: forbidden token is filtered, not raised.
    assert envelope.mesh_quality_concerns == ()  # offending entry stripped
    assert envelope.refused_claims == (f"{REFUSED_CLAIM_MARKER_PREFIX}{token}",)


@pytest.mark.parametrize("token", list(ADVISOR_FORBIDDEN_TOKENS))
def test_forbidden_claim_audit_allows_not_claim_disclaimer_form(token: str) -> None:
    """The same token wrapped in the ``not <claim>`` disclaimer form is
    legal — this is how the Tier 1 trio communicates posture."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=(f"This snapshot is not {token}; reviewer judges.",),
        boundary_condition_questions=("b",),
        failure_modes_to_consider=("f",),
        unhandled_load_cases=("u",),
        four_question_gate={k: True for k in FOUR_QUESTION_GATE_KEYS},
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "online"


def test_forbidden_claim_audit_is_case_insensitive() -> None:
    """``ASME Compliant`` (mixed case) is still forbidden — the audit
    folds case so a maintainer can't slip past via capitalization.

    Phase 13 A contract evolution: the case-insensitive match now
    fires inside the per-section filter (not at envelope-audit
    raise time). The mixed-case forbidden text is filtered into
    a refused-claim marker; the lowercased token in the marker is
    canonical. Original entry is discarded."""
    from app.services.reporting.advisor_critique import REFUSED_CLAIM_MARKER_PREFIX

    raw = AdvisorRawCritique(
        mesh_quality_concerns=("This design is ASME Compliant per inspection.",),
        boundary_condition_questions=("b",),
        failure_modes_to_consider=("f",),
        unhandled_load_cases=("u",),
        four_question_gate={k: True for k in FOUR_QUESTION_GATE_KEYS},
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    # Mixed-case forbidden text caught by case-folded scan; refused
    # marker uses the canonical lowercase token form.
    assert envelope.mesh_quality_concerns == ()
    assert envelope.refused_claims == (f"{REFUSED_CLAIM_MARKER_PREFIX}asme compliant",)


# ---------------------------------------------------------------------
# Schema-stamping audit (mirrors test_schema_versions_stamping.py format)
# ---------------------------------------------------------------------


def test_critique_to_dict_pins_top_level_envelope_keys() -> None:
    """If a maintainer adds an envelope field, this audit fails until
    they update the pin — making the schema contract auditable.

    Phase 13 A MINOR bump: ``refused_claims`` was added per the
    1.0.0 -> 1.1.0 schema evolution; the key set is updated in
    lockstep with the version pin in
    ``test_advisor_critique_schema_version_pinned_at_phase13_a_baseline``."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    keys = set(_critique_to_dict(envelope).keys())
    assert keys == {
        "schema_version",
        "case_id",
        "snapshot_label",
        "advisor_status",
        "advisor_backend",
        "generated_at_utc",
        "four_question_gate",
        "mesh_quality_concerns",
        "boundary_condition_questions",
        "failure_modes_to_consider",
        "unhandled_load_cases",
        "degrade_reason",
        "claim_tier",
        "claim_boundary",
        "claim_impact",
        "refused_claims",
    }


def test_envelope_isinstance_pins_dataclass_contract() -> None:
    """The return type of ``build_advisor_critique`` is contractually
    ``AdvisorCritique`` — pinned so a maintainer can't silently swap
    to a different return shape."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    assert isinstance(envelope, AdvisorCritique)
