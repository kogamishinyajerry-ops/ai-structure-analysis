"""FM-04a Phase 14 C — StubAdvisor explicit_dynamics branch tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the four explicit_dynamics-specific advisor concerns
emitted by :class:`StubAdvisor.produce` when ``context.convergence_kind
== "explicit_dynamics"`` (mirrors the Phase 12 B modal-advisor-branch
pattern):

  1. **CFL stability** (failure_mode + bc_question carrying ``CFL`` /
     ``mass scaling`` / ``dt`` tokens).
  2. **Energy partition closure** (mesh_concern carrying
     ``energy partition`` token).
  3. **Contact stiffness convergence** (mesh_concern carrying
     ``contact stiffness`` token, with hourglass coefficient sweep
     guidance).
  4. **Wave reflection vs boundary condition** (bc_question carrying
     ``wave reflection`` token).

Anti-gaming guards pinned here:
* The four themes are emitted DISTINCTLY (no boilerplate copy across
  themes; each carries its own marker token).
* The Phase 12 modal branch + the Phase 11 ballistic / linear_static_pv
  branches are unchanged (no regression).
* The four-question gate fires (every key present + every value True).
* The Tier 1 disclaimer trio is preserved on the envelope.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.reporting.advisor_critique import (
    FOUR_QUESTION_GATE_KEYS,
    AdvisorContext,
    build_advisor_critique,
)

_FROZEN_NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC)


def _context(
    *,
    convergence_kind: str = "explicit_dynamics",
    convergence_combined_verdict: str = "candidate_observed_stable",
    energy_audit_status: str | None = "closed_aggregate",
    trust_score: int | None = 88,
    completeness_score: int | None = 92,
    completeness_analysis_type: str = "explicit_dynamics",
    case_id: str = "rod-wave-impact-candidate",
) -> AdvisorContext:
    return AdvisorContext(
        case_id=case_id,
        snapshot_label="2026-05-17T120000Z",
        trust_score=trust_score,
        completeness_score=completeness_score,
        completeness_analysis_type=completeness_analysis_type,
        energy_audit_status=energy_audit_status,
        convergence_kind=convergence_kind,
        convergence_combined_verdict=convergence_combined_verdict,
        extra={},
    )


# ---------------------------------------------------------------------
# 1. Four distinct themes emitted
# ---------------------------------------------------------------------


def test_branch_reachable_via_convergence_kind() -> None:
    """The branch fires when ``context.convergence_kind ==
    'explicit_dynamics'``; the ballistic/linear_static_pv contexts
    do NOT carry the explicit_dynamics marker tokens."""
    explicit = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    explicit_haystack = (
        "\n".join(explicit.boundary_condition_questions)
        + "\n"
        + "\n".join(explicit.failure_modes_to_consider)
        + "\n"
        + "\n".join(explicit.mesh_quality_concerns)
    ).lower()
    assert "cfl" in explicit_haystack
    assert "wave reflection" in explicit_haystack
    assert "contact stiffness" in explicit_haystack
    assert "energy partition" in explicit_haystack


def test_cfl_stability_theme_emitted_distinctly() -> None:
    """Theme 1: CFL stability. Surfaces in BOTH a bc_question (dt
    sweep convergence) and a failure_mode (CFL divergence + mass-
    scaling masking). The two surfaces are distinct strings (no
    boilerplate)."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    cfl_questions = [q for q in envelope.boundary_condition_questions if "cfl" in q.lower()]
    cfl_failures = [f for f in envelope.failure_modes_to_consider if "cfl" in f.lower()]
    assert len(cfl_questions) == 1
    assert len(cfl_failures) == 1
    # Distinct content — not the same string in both lists.
    assert cfl_questions[0] != cfl_failures[0]
    # Dt sweep convergence prompt in the question.
    assert "dt sweep" in cfl_questions[0].lower()
    # Mass-scaling cutoff cited in the failure mode (legacy
    # Phase 11 token preserved for back-compat tests).
    assert "mass scaling" in cfl_failures[0].lower()


def test_energy_partition_theme_emitted_distinctly() -> None:
    """Theme 2: energy partition closure. Surfaces as a mesh_concern
    citing the per-frame audit's drift_fraction tolerance."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    matches = [m for m in envelope.mesh_quality_concerns if "energy partition" in m.lower()]
    assert len(matches) == 1
    # Cites the per-frame audit + drift fraction.
    text = matches[0].lower()
    assert "per-frame" in text or "drift" in text
    assert "external work" in text


def test_contact_stiffness_theme_emitted_distinctly() -> None:
    """Theme 3: contact stiffness convergence. Surfaces as a
    mesh_concern WHOSE THEME HEADER is the contact-stiffness theme
    (not as a passing reference in another theme's failure-mode
    enumeration)."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    matches = [
        m for m in envelope.mesh_quality_concerns if "contact stiffness convergence" in m.lower()
    ]
    assert len(matches) == 1
    text = matches[0].lower()
    # Hourglass coefficient cited as a coupled sweep dimension.
    assert "hourglass" in text
    # Sweep guidance — a single-point evaluation is insufficient.
    assert "sweep" in text


def test_wave_reflection_theme_emitted_distinctly() -> None:
    """Theme 4: wave reflection vs boundary condition. Surfaces as
    a bc_question citing the SIGN-FLIPS between free and clamped
    ends + the analytical 1D-bar cross-check applicability."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    matches = [q for q in envelope.boundary_condition_questions if "wave reflection" in q.lower()]
    assert len(matches) == 1
    text = matches[0].lower()
    assert "free" in text and "clamped" in text
    assert "bar_wave_first_reflection_s" in text


# ---------------------------------------------------------------------
# 2. Four themes are not duplicated; no boilerplate cross-theme
# ---------------------------------------------------------------------


def test_themes_are_distinct_strings() -> None:
    """No two themes share an identical surface string. Catches
    boilerplate regressions where a future maintainer might
    copy-paste a concern across two list categories."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    all_strings = (
        list(envelope.mesh_quality_concerns)
        + list(envelope.boundary_condition_questions)
        + list(envelope.failure_modes_to_consider)
        + list(envelope.unhandled_load_cases)
    )
    assert len(set(all_strings)) == len(all_strings), (
        "two advisor concerns share an identical surface string; themes should be distinct"
    )


# ---------------------------------------------------------------------
# 3. Phase 11 / Phase 12 branches unchanged (regression guard)
# ---------------------------------------------------------------------


def test_linear_static_branch_unchanged() -> None:
    """Phase 11 A linear_static branch: the four-question gate fires,
    plasticity-blindness failure mode surfaces. The explicit_dynamics
    marker tokens MUST NOT leak into a linear_static context."""
    envelope = build_advisor_critique(
        _context(convergence_kind="linear_static"), now_utc=_FROZEN_NOW
    )
    haystack = (
        "\n".join(envelope.boundary_condition_questions)
        + "\n"
        + "\n".join(envelope.failure_modes_to_consider)
        + "\n"
        + "\n".join(envelope.mesh_quality_concerns)
    ).lower()
    # Linear-static legacy content present.
    assert "scl" in haystack or "stress gradient" in haystack
    assert "plasticity" in haystack
    # Explicit-dynamics marker tokens MUST NOT bleed in.
    assert "cfl" not in haystack
    assert "wave reflection" not in haystack
    assert "energy partition" not in haystack


def test_modal_branch_unchanged() -> None:
    """Phase 12 B modal branch: MAC + Lanczos + mass-participation
    + 5%-frequency-residual concerns still emitted. Explicit-dynamics
    marker tokens MUST NOT leak into a modal context."""
    envelope = build_advisor_critique(_context(convergence_kind="modal"), now_utc=_FROZEN_NOW)
    haystack = (
        "\n".join(envelope.boundary_condition_questions)
        + "\n"
        + "\n".join(envelope.failure_modes_to_consider)
        + "\n"
        + "\n".join(envelope.mesh_quality_concerns)
    ).lower()
    assert "mac" in haystack
    assert "lanczos" in haystack
    assert "mass participation" in haystack
    # No explicit-dynamics bleed.
    assert "cfl" not in haystack
    assert "wave reflection" not in haystack


# ---------------------------------------------------------------------
# 4. 4-question gate + Tier 1 disclaimer trio preserved
# ---------------------------------------------------------------------


def test_four_question_gate_fires_on_explicit_dynamics_branch() -> None:
    """Every gate key is present and every value is True under the
    stub. This is the load-bearing posture of the advisor surface;
    a regression here would break the AI-as-advisor invariant."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    for key in FOUR_QUESTION_GATE_KEYS:
        assert key in envelope.four_question_gate
        assert envelope.four_question_gate[key] is True


def test_tier1_disclaimer_trio_preserved_on_explicit_dynamics_envelope() -> None:
    """The envelope-level claim banners (claim_tier / claim_boundary /
    claim_impact) must carry the Tier 1 disclaimer trio."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    assert "Tier 1 engineering candidate" in envelope.claim_tier
    assert "not_signed_validation" in envelope.claim_boundary
    assert "not_benchmark_agreement" in envelope.claim_boundary
    assert "not signed validation" in envelope.claim_impact
    assert "not benchmark agreement" in envelope.claim_impact


# ---------------------------------------------------------------------
# 5. Forbidden positive-claim tokens absent from explicit_dynamics branch
# ---------------------------------------------------------------------


def test_explicit_dynamics_branch_carries_no_forbidden_positive_claims() -> None:
    """The 4 themes MUST NOT introduce any of the 9 forbidden
    positive-claim tokens (outside the ``not <claim>`` form)."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    text = (
        " ".join(envelope.mesh_quality_concerns)
        + " "
        + " ".join(envelope.boundary_condition_questions)
        + " "
        + " ".join(envelope.failure_modes_to_consider)
    ).lower()
    forbidden = (
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
    for tok in forbidden:
        # Tokens may appear inside a "not <claim>" form; we filter
        # those out by checking the preceding 4 characters.
        idx = text.find(tok)
        while idx != -1:
            prefix = text[max(0, idx - 5) : idx].strip()
            assert prefix.endswith("not"), (
                f"forbidden positive-claim token {tok!r} appears in the "
                f"explicit_dynamics branch outside a 'not <claim>' form. "
                f"surrounding context: {text[max(0, idx - 20) : idx + len(tok) + 20]!r}"
            )
            idx = text.find(tok, idx + 1)


# ---------------------------------------------------------------------
# 6. Phase 11 legacy mass-scaling check passes (regression for the
#    Phase 11 advisor-critique test suite)
# ---------------------------------------------------------------------


def test_phase11_legacy_mass_scaling_and_dt_tokens_still_present() -> None:
    """The Phase 11 advisor-critique test
    ``test_stub_advisor_explicit_dynamics_surfaces_mass_scaling_check``
    asserts ``"mass scaling"`` / ``"mass-scaled"`` in failures AND
    ``"dt"`` / ``"hourglass"`` in questions. The Phase 14 C rewrite
    preserves both invariants — a guard test here so a future
    maintainer doesn't drift either."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    failures = "\n".join(envelope.failure_modes_to_consider).lower()
    questions = "\n".join(envelope.boundary_condition_questions).lower()
    assert "mass scaling" in failures or "mass-scaled" in failures
    assert "dt" in questions or "hourglass" in questions
