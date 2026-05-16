"""Tier 1 candidate AI advisor critique service (FM-04a Phase 11 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This module produces an *advisor critique* for a (case, snapshot) pair —
a structured, machine-readable list of engineering concerns + questions
+ failure-modes-to-consider + unhandled-load-cases that a reviewer
should think about before signing off. The advisor is **never** the
authority: it reads frozen snapshot bytes + trust score + completeness +
provenance, and writes nothing. Reviewer agency is preserved.

Design pillars (project north star — see memory
`feedback_cfd_harness_ai_advisor_pivot` and the four-question gate):

  1. **LLM-offline-first**. The workbench must complete every reviewer
     flow without a live LLM. ``StubAdvisor`` (rule-based, always
     available) is the ground truth; ``LLMAdvisor`` (Phase 11 C) is an
     optional augmentation.
  2. **Read-only**. Advisor never writes to ``golden_samples/``,
     ``reports/``, ``project_state/``, or anywhere else.
  3. **Four-question gate**. Every critique answers the four
     project-level questions about its own scope before any
     engineering content is allowed in the payload.
  4. **Forbidden-claim envelope audit**. Same Tier 1 token list as
     the base reporting surface, PLUS advisor-specific tokens
     (``production ready``, ``certified``, ``approved for service``,
     ``ASME compliant``, ``signed off``). Positive claim outside
     ``not <claim>`` form refuses the envelope at construction.

Module-level SSOT constants (Phase 11 B):

* :data:`ADVISOR_CRITIQUE_SCHEMA_VERSION` — schema version of the
  emitted JSON. Bump policy lives in ``_schema_versions.py``.
* :data:`ADVISOR_STATUS_TUPLE` — closed set of advisor_status values
  ({"online", "offline", "stub"}). Tuple is the SSOT for the
  frontend Phase 11 E tuple ``ADVISOR_STATUS_TUPLE`` in
  ``frontend/src/advisorCritiqueClient.ts``.
* :data:`FOUR_QUESTION_GATE_KEYS` — the four required question keys
  every critique must answer. SSOT for the frontend mirror.
* :data:`ADVISOR_FORBIDDEN_TOKENS` — extended forbidden-claim list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ._schema_versions import ADVISOR_CRITIQUE_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate AI advisor critique; not signed validation; "
    "not benchmark agreement. The advisor surfaces engineering "
    "concerns + questions for the reviewer to consider; the advisor "
    "is NOT the authority. Reviewer agency is preserved at every "
    "step. The critique does NOT authorize Tier 2 promotion or "
    "substitute for the FM-04b sealed packet."
)

# Closed enum of advisor status values. Pinned by
# `test_advisor_status_tuple_closed_set`. Frontend Phase 11 E
# `ADVISOR_STATUS_TUPLE` in `advisorCritiqueClient.ts` mirrors this
# tuple byte-for-byte.
ADVISOR_STATUS_TUPLE: tuple[str, ...] = ("online", "offline", "stub")
"""Closed set of advisor_status values. ``online`` = live LLM produced
the critique. ``offline`` = LLM was unavailable at request time;
critique is a stub. ``stub`` = caller explicitly chose stub backend
or live LLM produced a malformed response and the system degraded."""

# Four-question gate keys. Each critique payload must answer all four
# with a boolean. A missing key OR a non-boolean value fails the
# envelope construction (raises ValueError). Phase 11 anti-gaming
# guard C:-10.
FOUR_QUESTION_GATE_KEYS: tuple[str, str, str, str] = (
    "llm_offline_ok",
    "artifacts_user_owned",
    "trustgate_explains",
    "advisor_only",
)
"""Project four-question gate. The bare semantics:
  - ``llm_offline_ok``: the workbench would still function if the LLM
    were unavailable for this case.
  - ``artifacts_user_owned``: no advisor pathway writes to
    user-owned golden_samples / reports / project_state directories.
  - ``trustgate_explains``: the reviewer still gets a trust-score +
    provenance trail explaining the score, with or without the
    advisor critique.
  - ``advisor_only``: the advisor produces ADVISORY content only;
    no signoff, no promotion, no certification claim.

Per the project north star, all four must be True at every critique
construction. A False on any of them indicates the system has drifted
out of "AI is advisor, not driver" posture."""

# Forbidden-claim token list — extends the Tier 1 reporting base list
# with advisor-specific positive-claim verbs the LLM might emit if
# unconstrained. Same `not <claim>` disclaimer rule applies as
# elsewhere in the project (substring match + 4-char prefix check).
# Pinned per-token by tests in test_phase11_advisor_critique.py.
ADVISOR_FORBIDDEN_TOKENS: tuple[str, ...] = (
    # Base Tier 1 list (shared with trust_score_provenance envelope).
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    # Phase 11 B extension — advisor-specific positive verbs.
    "production ready",
    "certified",
    "approved for service",
    "asme compliant",        # case-folded (haystack is lowered)
    "signed off",
)
"""Tokens forbidden in advisor critique JSON payloads outside the
``not <claim>`` disclaimer form. Phase 11 anti-gaming guard T:-5
requires each new token to have its own test (the per-token tests
live in test_phase11_advisor_critique.py)."""


# ---------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class AdvisorContext:
    """Input bundle handed to an advisor backend. Read-only.

    Fields hold the *frozen* snapshot bytes + the trust-score /
    provenance / completeness payloads (whichever the orchestrator
    chose to pass). The advisor must not request additional disk
    reads beyond this bundle."""

    case_id: str
    snapshot_label: str
    trust_score: int | None
    completeness_score: int | None
    completeness_analysis_type: str | None
    energy_audit_status: str | None
    convergence_kind: str | None
    convergence_combined_verdict: str | None
    extra: dict[str, Any]  # forward-compat slot; advisor backends may
                           # request additional structured context here
                           # without bumping the dataclass.


@dataclass(frozen=True)
class AdvisorRawCritique:
    """Raw content produced by an advisor backend, BEFORE envelope
    construction. The builder wraps this into an :class:`AdvisorCritique`
    with claim banners + four-question gate + forbidden-claim audit."""

    mesh_quality_concerns: tuple[str, ...]
    boundary_condition_questions: tuple[str, ...]
    failure_modes_to_consider: tuple[str, ...]
    unhandled_load_cases: tuple[str, ...]
    four_question_gate: dict[str, bool]
    degrade_reason: str | None = None  # populated when backend fell
                                       # back to stub mid-flight.


@dataclass(frozen=True)
class AdvisorCritique:
    """Envelope ready for JSON emission to the route layer."""

    schema_version: str
    case_id: str
    snapshot_label: str
    advisor_status: str
    advisor_backend: str
    generated_at_utc: str
    four_question_gate: dict[str, bool]
    mesh_quality_concerns: tuple[str, ...]
    boundary_condition_questions: tuple[str, ...]
    failure_modes_to_consider: tuple[str, ...]
    unhandled_load_cases: tuple[str, ...]
    degrade_reason: str | None
    claim_tier: str
    claim_boundary: str
    claim_impact: str


@runtime_checkable
class AdvisorProvider(Protocol):
    """Pluggable backend Protocol. ``StubAdvisor`` always implements;
    ``LLMAdvisor`` (Phase 11 C) implements via injected callable."""

    name: str

    def is_available(self) -> bool: ...
    def produce(self, context: AdvisorContext) -> AdvisorRawCritique: ...


# ---------------------------------------------------------------------
# StubAdvisor — rule-based, always available, deterministic
# ---------------------------------------------------------------------


class StubAdvisor:
    """Rule-based advisor that produces concerns directly from the
    input context, with no LLM dependency.

    The stub is the **load-bearing fallback** for the LLM-offline-first
    pillar. It must:

      * always be available (``is_available()`` returns True);
      * never raise on a well-formed context;
      * produce content that is *correlated* with the input data
        (Phase 11 anti-gaming guard A:-2 — vacuous stub guard); a
        trust score < 70 must surface at least one mesh_quality_concern,
        a non-closed_aggregate energy audit must surface at least one
        boundary_condition_question, etc.

    The stub does not call any external service. Its rules are
    intentionally narrow + transparent — every produced concern can
    be traced back to a specific input field.
    """

    name = "stub-rule-based"

    def is_available(self) -> bool:
        return True

    def produce(self, context: AdvisorContext) -> AdvisorRawCritique:
        mesh_concerns: list[str] = []
        bc_questions: list[str] = []
        failure_modes: list[str] = []
        unhandled_loads: list[str] = []

        # Trust-score correlated concerns.
        if context.trust_score is not None and context.trust_score < 70:
            mesh_concerns.append(
                f"trust_score = {context.trust_score} / 100 is below the "
                f"watching threshold; the snapshot may be missing evidence "
                f"axes (completeness, convergence, energy audit, or "
                f"reproducibility). Cross-check the trust-score-provenance "
                f"trace to identify which axis is starved."
            )
        if context.completeness_score is not None and context.completeness_score < 60:
            mesh_concerns.append(
                f"completeness_score = {context.completeness_score} / 100 "
                f"indicates substantial evidence absence. Reviewer should "
                f"trace which axes scored zero before forming a verdict."
            )

        # Energy-audit correlated questions.
        if context.energy_audit_status not in ("closed_aggregate", None):
            bc_questions.append(
                f"energy_audit.status = "
                f"{context.energy_audit_status!r}. Is the per-term energy "
                f"partition (kinetic / internal / contact / hourglass) "
                f"available, or is only the aggregate KE balance known? "
                f"A non-closed_aggregate audit increases boundary-condition "
                f"sensitivity."
            )

        # Convergence-kind specific questions.
        if context.convergence_kind == "linear_static":
            bc_questions.append(
                "linear_static convergence kind: confirm the mesh-refinement "
                "sweep covers the through-thickness stress gradient at the "
                "location of interest. SCL spacing at >=5 quadratic elements "
                "is the ASME VIII Div 2 §5.5 minimum."
            )
            failure_modes.append(
                "Linear static analysis is BLIND to: plasticity, contact "
                "separation, large displacement, instability, fatigue, "
                "creep, dynamic amplification, and material non-linearity. "
                "If any of these are credible at the design load, a follow-up "
                "analysis is required."
            )
        elif context.convergence_kind == "explicit_dynamics":
            bc_questions.append(
                "explicit_dynamics convergence kind: was the dt sweep "
                "converged to within 5% on the metric of interest? Was "
                "hourglass control reviewed?"
            )
            failure_modes.append(
                "Explicit dynamics is sensitive to mass scaling. Confirm "
                "the mass-scaled-to-physical ratio is within accepted "
                "engineering practice (<2-5% added mass typical) and "
                "that the time step is dominated by the smallest "
                "element rather than by mass scaling cutoff."
            )

        # Convergence-verdict correlated concerns.
        if context.convergence_combined_verdict == "candidate_observed_unstable":
            mesh_concerns.append(
                "convergence_combined_verdict = candidate_observed_unstable. "
                "The mesh OR dt sweep crossed the tolerance band; refine "
                "before reporting any quantitative result."
            )

        # Always emit at least one unhandled-load-case prompt — load
        # cases are case-specific and the stub doesn't know which to
        # surface, so it asks an open question rather than fabricating.
        unhandled_loads.append(
            "Reviewer: enumerate the load cases NOT analyzed in this "
            "snapshot. Common omissions: thermal transients, accident "
            "scenarios, fatigue spectrum, seismic, hydrostatic test, "
            "vacuum, and erection / handling loads. Tier 1 candidate "
            "does NOT certify completeness of the load envelope."
        )

        # If we have not surfaced ANY mesh concern, add a baseline
        # prompt asking the reviewer to confirm the mesh density was
        # checked against the stress-gradient length scale. This
        # prevents a vacuous empty-list payload while still being
        # honest about what we don't know.
        if not mesh_concerns:
            mesh_concerns.append(
                "Reviewer: confirm the mesh density satisfies the stress-"
                "gradient length scale at the location of interest "
                "(typical guideline: >=4 quadratic elements per "
                "characteristic length of the stress field)."
            )

        # 4-Q gate: every stub-produced critique answers ALL four with
        # True. This is the load-bearing posture statement of the
        # advisor surface; if any of these would be False, the system
        # has drifted out of the "AI is advisor, not driver" pattern
        # and the stub itself signals that (rather than asking the
        # reviewer to notice).
        gate: dict[str, bool] = {k: True for k in FOUR_QUESTION_GATE_KEYS}

        return AdvisorRawCritique(
            mesh_quality_concerns=tuple(mesh_concerns),
            boundary_condition_questions=tuple(bc_questions),
            failure_modes_to_consider=tuple(failure_modes),
            unhandled_load_cases=tuple(unhandled_loads),
            four_question_gate=gate,
            degrade_reason=None,
        )


# ---------------------------------------------------------------------
# Envelope builder + audits
# ---------------------------------------------------------------------


def build_advisor_critique(
    context: AdvisorContext,
    *,
    provider: AdvisorProvider | None = None,
    now_utc: datetime | None = None,
) -> AdvisorCritique:
    """Build an advisor critique for ``context``.

    Choice of backend:
      * If ``provider`` is None -> ``StubAdvisor`` is used.
      * If ``provider`` is supplied AND ``is_available()`` -> the
        provided backend is used.
      * If ``provider`` is supplied but NOT available -> falls back
        to ``StubAdvisor`` and sets ``advisor_status = "offline"`` +
        records the degrade_reason.

    The envelope construction:
      1. four-question gate audit (every key present + all True);
      2. forbidden-claim envelope audit on the rendered JSON;
      3. claim banners stamped onto the envelope.
    """
    selected_provider: AdvisorProvider
    advisor_status: str
    degrade_reason_override: str | None = None
    if provider is None:
        selected_provider = StubAdvisor()
        advisor_status = "stub"
    elif provider.is_available():
        selected_provider = provider
        advisor_status = "online"
    else:
        selected_provider = StubAdvisor()
        advisor_status = "offline"
        degrade_reason_override = f"provider {provider.name!r} is_available() == False"

    raw = selected_provider.produce(context)
    degrade_reason = raw.degrade_reason or degrade_reason_override

    # 4-Q gate audit — every key present, every value boolean, every
    # value True. The gate has explicit semantic; a False indicates
    # the system has drifted out of advisor-only posture. We REFUSE
    # the envelope rather than emit a "drifted" critique.
    _audit_four_question_gate(raw.four_question_gate)

    moment = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    envelope = AdvisorCritique(
        schema_version=ADVISOR_CRITIQUE_SCHEMA_VERSION,
        case_id=context.case_id,
        snapshot_label=context.snapshot_label,
        advisor_status=advisor_status,
        advisor_backend=selected_provider.name,
        generated_at_utc=moment,
        four_question_gate=dict(raw.four_question_gate),
        mesh_quality_concerns=raw.mesh_quality_concerns,
        boundary_condition_questions=raw.boundary_condition_questions,
        failure_modes_to_consider=raw.failure_modes_to_consider,
        unhandled_load_cases=raw.unhandled_load_cases,
        degrade_reason=degrade_reason,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(envelope)
    return envelope


def render_advisor_critique_json(critique: AdvisorCritique) -> str:
    """JSON-serialize a critique envelope (sorted keys, 2-space indent)."""
    return json.dumps(_critique_to_dict(critique), indent=2, sort_keys=True)


def _critique_to_dict(critique: AdvisorCritique) -> dict[str, Any]:
    return {
        "schema_version": critique.schema_version,
        "case_id": critique.case_id,
        "snapshot_label": critique.snapshot_label,
        "advisor_status": critique.advisor_status,
        "advisor_backend": critique.advisor_backend,
        "generated_at_utc": critique.generated_at_utc,
        "four_question_gate": critique.four_question_gate,
        "mesh_quality_concerns": list(critique.mesh_quality_concerns),
        "boundary_condition_questions": list(critique.boundary_condition_questions),
        "failure_modes_to_consider": list(critique.failure_modes_to_consider),
        "unhandled_load_cases": list(critique.unhandled_load_cases),
        "degrade_reason": critique.degrade_reason,
        "claim_tier": critique.claim_tier,
        "claim_boundary": critique.claim_boundary,
        "claim_impact": critique.claim_impact,
    }


def _audit_four_question_gate(gate: dict[str, bool]) -> None:
    """Phase 11 anti-gaming guard C:-10. Every key in
    FOUR_QUESTION_GATE_KEYS must appear with a boolean True value.

    Refusing a False answer (rather than tolerating it) is intentional:
    the gate is a *posture* statement, not a sensor. If a backend
    wanted to report a False, the system has lost the advisor-only
    posture entirely, and we want loud failure rather than silent
    drift."""
    missing = [k for k in FOUR_QUESTION_GATE_KEYS if k not in gate]
    if missing:
        raise ValueError(
            f"Advisor four-question gate is missing keys: {missing!r}"
        )
    extra = [k for k in gate if k not in FOUR_QUESTION_GATE_KEYS]
    if extra:
        raise ValueError(
            f"Advisor four-question gate has unknown keys: {extra!r}"
        )
    not_bool = [k for k, v in gate.items() if not isinstance(v, bool)]
    if not_bool:
        raise ValueError(
            f"Advisor four-question gate has non-boolean values for keys "
            f"{not_bool!r}"
        )
    not_true = [k for k, v in gate.items() if v is not True]
    if not_true:
        raise ValueError(
            f"Advisor four-question gate has False answer(s) for "
            f"{not_true!r}; advisor envelope refused (system has drifted "
            f"out of advisor-only posture)"
        )


def _assert_no_overclaim(critique: AdvisorCritique) -> None:
    """Refuse advisor critique JSON containing any ADVISOR_FORBIDDEN_TOKENS
    outside the ``not <claim>`` disclaimer form (4-char prefix check)."""
    payload = json.dumps(_critique_to_dict(critique))
    haystack = payload.lower()
    for token in ADVISOR_FORBIDDEN_TOKENS:
        start = 0
        while True:
            idx = haystack.find(token, start)
            if idx == -1:
                break
            prefix = haystack[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Advisor critique contains forbidden positive claim "
                    f"{token!r} outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)
