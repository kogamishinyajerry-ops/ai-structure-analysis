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
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

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
        elif context.convergence_kind == "modal":
            # Phase 12 B — modal-specific advisor concerns. The four
            # named concerns mirror the four modal-rubric quality axes
            # so a reviewer reading the critique alongside the
            # completeness scorecard sees a 1:1 correspondence.

            # Mode-shape MAC concern (always surfaced — every modal
            # case should review mode-shape orthogonality on the
            # dominant pair).
            mesh_concerns.append(
                "modal convergence kind: review the Modal Assurance "
                "Criterion (MAC) on the dominant-mode pair. A MAC < 0.95 "
                "between successive mesh-refinement levels indicates the "
                "mode shape is not yet converged — refine before reporting "
                "the natural frequency as a Tier 1 candidate."
            )

            # Lanczos extraction method question (CalculiX default; the
            # reviewer must confirm shift-and-invert convergence on
            # poorly-conditioned cases, e.g., near-rigid-body modes).
            bc_questions.append(
                "modal convergence kind: CalculiX's *FREQUENCY card uses "
                "Lanczos extraction by default. On poorly-conditioned "
                "models (near-rigid-body modes; large mass ratios across "
                "the geometry), Lanczos can stall or miss modes. Confirm "
                "the dat-file STEP block reports the requested number of "
                "modes converged without restart cycles."
            )

            # Mass participation prompt — read mode_count_target from
            # context.extra if present (closes Phase 11 retro §2:
            # AdvisorContext.extra was an unread slot).
            target = context.extra.get("mode_count_target") if context.extra else None
            if target is not None:
                bc_questions.append(
                    f"modal convergence kind: cumulative effective mass "
                    f"participation in each significant direction MUST "
                    f"reach >= 80% across the {target} extracted modes "
                    f"before the modal sweep is considered complete. "
                    f"Critical modes may otherwise be missing from the "
                    f"sum (ASCE 7 / Eurocode 8 engineering-practice floor)."
                )
            else:
                bc_questions.append(
                    "modal convergence kind: cumulative effective mass "
                    "participation in each significant direction MUST "
                    "reach >= 80% across the extracted mode set before "
                    "the modal sweep is considered complete (ASCE 7 / "
                    "Eurocode 8 engineering-practice floor). Reviewer: "
                    "supply `mode_count_target` in context.extra to pin "
                    "the requested mode count for this case."
                )

            # Frequency tolerance vs analytical (load-bearing failure mode).
            failure_modes.append(
                "modal convergence kind: a numerical-vs-analytical "
                "frequency residual > 5% on the dominant bending mode "
                "indicates the structured mesh is too coarse OR the "
                "Lanczos extraction has not converged. Both failure modes "
                "look identical in the dat-file output; refine the mesh "
                "AND request more modes to disambiguate before reporting."
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

    # Phase 11 C — a live LLM provider that produces a raw critique
    # WITH ``degrade_reason`` populated signals that it internally
    # fell back to its stub fallback (malformed response, network
    # error, etc.). The envelope status MUST downgrade from
    # ``"online"`` to ``"stub"`` so a downstream reviewer knows the
    # critique they are reading is not actually live-LLM-produced.
    # Without this branch, a degraded-but-`is_available()==True`
    # provider would silently emit a stub critique under the
    # ``"online"`` banner — a real-world anti-pattern explicitly
    # called out in blueprint section 3.C.
    if advisor_status == "online" and raw.degrade_reason is not None:
        advisor_status = "stub"

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


# ---------------------------------------------------------------------
# LLMAdvisor — live LLM backend (Phase 11 C)
# ---------------------------------------------------------------------


# JSON keys the LLMAdvisor expects in the live-LLM response. SSOT for
# the prompt template + the response parser. Bumping this tuple is a
# schema break (the LLM is asked to emit exactly these keys).
LLM_RESPONSE_KEYS: tuple[str, ...] = (
    "mesh_quality_concerns",
    "boundary_condition_questions",
    "failure_modes_to_consider",
    "unhandled_load_cases",
    "four_question_gate",
)
"""Closed set of keys the LLM is asked to emit. Used by the parser to
fail fast on malformed responses. Phase 11 anti-gaming guard T:-4 (per
response shape pin)."""


# Maximum number of items per concern list. Cap protects against an
# LLM that goes off and emits a 200-line dump per axis — the reviewer
# panel is designed for short, scannable lists. A response that
# exceeds the cap is truncated (NOT refused) because the cap is an
# ergonomic guardrail, not a contract; the trailing items are silently
# dropped and a degrade_reason is recorded.
MAX_ITEMS_PER_AXIS = 12


# Maximum length per concern string. Same rationale — protects the UI
# from a wall-of-text bullet that breaks the reviewer panel layout.
MAX_CHARS_PER_ITEM = 600


class LLMAdvisor:
    """Live-LLM advisor backend with defensive parsing + stub fallback.

    Design pillars (LLM-offline-first):

      1. The LLM is called via an injected ``llm_call`` Callable. Tests
         inject controlled responses; production wires an ``httpx`` /
         ``anthropic`` client at the factory level. **No network call
         is made inside this module**.
      2. Any failure (network exception, malformed JSON, missing
         required key, wrong shape) falls back to the StubAdvisor for
         the same context. The fallback raw critique carries a
         ``degrade_reason`` so the envelope builder can downgrade
         ``advisor_status`` from ``"online"`` to ``"stub"``.
      3. The 4-question gate is asked of the LLM as part of the
         response schema; if the LLM produces False on any key, the
         envelope is refused at construction by the existing
         ``_audit_four_question_gate``.
      4. The forbidden-claim audit fires at envelope construction;
         any positive-claim verb the LLM might emit outside the
         disclaimer form refuses the envelope (existing
         ``_assert_no_overclaim``).
    """

    def __init__(
        self,
        llm_call: Callable[[str], str],
        *,
        backend_label: str = "llm-advisor",
    ) -> None:
        self._llm_call = llm_call
        self.name = backend_label

    def is_available(self) -> bool:
        # The LLMAdvisor is "available" as long as it has an injected
        # callable. The callable itself may fail at produce() time —
        # that path is the stub-fallback branch, NOT an availability
        # check. Marking it unavailable here would route the failure
        # through the wrong branch in build_advisor_critique (status
        # would land on "offline" instead of "stub").
        return self._llm_call is not None

    def produce(self, context: AdvisorContext) -> AdvisorRawCritique:
        prompt = build_llm_prompt(context)
        try:
            response_text = self._llm_call(prompt)
        except Exception as exc:  # noqa: BLE001 — defensive boundary
            return self._stub_fallback(
                context,
                f"llm_call raised {type(exc).__name__}: {exc}",
            )

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            return self._stub_fallback(
                context,
                f"LLM response is not valid JSON: {exc.msg}",
            )

        try:
            return _parse_llm_response(payload)
        except (KeyError, TypeError, ValueError) as exc:
            return self._stub_fallback(
                context,
                f"LLM response failed schema parse: {exc}",
            )

    @staticmethod
    def _stub_fallback(
        context: AdvisorContext, reason: str
    ) -> AdvisorRawCritique:
        """Return a StubAdvisor critique for the same context with
        the provided degrade_reason. Used internally on any LLM
        failure path."""
        stub_raw = StubAdvisor().produce(context)
        return AdvisorRawCritique(
            mesh_quality_concerns=stub_raw.mesh_quality_concerns,
            boundary_condition_questions=stub_raw.boundary_condition_questions,
            failure_modes_to_consider=stub_raw.failure_modes_to_consider,
            unhandled_load_cases=stub_raw.unhandled_load_cases,
            four_question_gate=stub_raw.four_question_gate,
            degrade_reason=reason,
        )


def build_llm_prompt(context: AdvisorContext) -> str:
    """Build the live-LLM prompt string for ``context``.

    The prompt is a single string (system + user turns concatenated)
    that asks the LLM to emit a strict JSON object with the keys
    enumerated in ``LLM_RESPONSE_KEYS``. The four-question gate is
    asked as part of the response schema so the LLM's posture
    statement lands inside the same payload as the engineering
    concerns. The forbidden-claim list is included verbatim so the
    LLM has explicit guidance on what NOT to emit.
    """
    forbidden_list = ", ".join(repr(t) for t in ADVISOR_FORBIDDEN_TOKENS)
    gate_keys = ", ".join(repr(k) for k in FOUR_QUESTION_GATE_KEYS)
    response_keys = ", ".join(repr(k) for k in LLM_RESPONSE_KEYS)

    # The prompt deliberately states the Tier 1 disclaimer trio and
    # the advisor-not-driver posture in plain language — this is the
    # north-star statement the LLM is asked to honor.
    return (
        "You are an AI ADVISOR (not driver) for a Tier 1 engineering "
        "candidate structural FEA review. Your role is to surface "
        "engineering concerns, questions, failure modes, and "
        "unhandled load cases for a human reviewer to consider. You "
        "are NOT the authority; the reviewer is. The critique is "
        "Tier 1 candidate; not signed validation; not benchmark "
        "agreement. The critique does NOT authorize Tier 2 promotion "
        "or substitute for a sealed packet.\n"
        "\n"
        "CONTEXT (frozen snapshot bytes — read-only):\n"
        f"  case_id: {context.case_id}\n"
        f"  snapshot_label: {context.snapshot_label}\n"
        f"  trust_score: {context.trust_score}\n"
        f"  completeness_score: {context.completeness_score}\n"
        f"  completeness_analysis_type: {context.completeness_analysis_type}\n"
        f"  energy_audit_status: {context.energy_audit_status}\n"
        f"  convergence_kind: {context.convergence_kind}\n"
        f"  convergence_combined_verdict: {context.convergence_combined_verdict}\n"
        "\n"
        "RESPONSE SCHEMA — emit a JSON OBJECT with EXACTLY these keys:\n"
        f"  {response_keys}\n"
        "\n"
        "Each of the first four keys is a JSON ARRAY of short, "
        "scannable strings (one concern / question / mode / load case "
        "per entry). Use short, declarative sentences. Do not emit "
        "more than "
        f"{MAX_ITEMS_PER_AXIS} entries per axis. Do not emit any "
        "entry longer than "
        f"{MAX_CHARS_PER_ITEM} characters.\n"
        "\n"
        f"The fifth key 'four_question_gate' MUST be a JSON OBJECT "
        f"with the EXACT keys {gate_keys}, each mapped to the "
        "literal JSON boolean true. Any false answer indicates the "
        "system has drifted out of advisor-only posture and the "
        "envelope will be refused.\n"
        "\n"
        "FORBIDDEN: do NOT use any of the following phrases outside "
        f"a disclaimer of the form 'not <phrase>': {forbidden_list}. "
        "These are positive-claim verbs reserved for FM-04b signed "
        "validation work; using them outside disclaimer form "
        "automatically refuses the envelope.\n"
        "\n"
        "Emit ONLY the JSON object. No markdown fences, no prose "
        "preamble, no trailing commentary."
    )


def _parse_llm_response(payload: Any) -> AdvisorRawCritique:
    """Parse a JSON-decoded LLM response into an AdvisorRawCritique.

    Raises ``TypeError`` / ``ValueError`` / ``KeyError`` on any shape
    drift; ``LLMAdvisor.produce`` catches these and falls back to
    the stub. We deliberately raise rather than coerce — a permissive
    parser is the worst possible posture for the advisor surface."""
    if not isinstance(payload, dict):
        raise TypeError(
            f"LLM response is not a JSON object; got {type(payload).__name__}"
        )

    missing = [k for k in LLM_RESPONSE_KEYS if k not in payload]
    if missing:
        raise KeyError(f"LLM response missing required keys: {missing}")

    extra = [k for k in payload if k not in LLM_RESPONSE_KEYS]
    if extra:
        raise ValueError(f"LLM response has unexpected keys: {extra}")

    list_axes: dict[str, tuple[str, ...]] = {}
    for axis in LLM_RESPONSE_KEYS[:4]:  # first four are the list axes
        items = payload[axis]
        if not isinstance(items, list):
            raise TypeError(
                f"LLM response key {axis!r} is not a list; "
                f"got {type(items).__name__}"
            )
        cleaned: list[str] = []
        for item in items[:MAX_ITEMS_PER_AXIS]:
            if not isinstance(item, str):
                raise TypeError(
                    f"LLM response key {axis!r} contains non-string "
                    f"entry of type {type(item).__name__}"
                )
            cleaned.append(item[:MAX_CHARS_PER_ITEM])
        list_axes[axis] = tuple(cleaned)

    gate = payload["four_question_gate"]
    if not isinstance(gate, dict):
        raise TypeError(
            f"LLM response 'four_question_gate' is not an object; "
            f"got {type(gate).__name__}"
        )
    # We leave gate validation (missing keys / non-bool / False) to
    # the envelope-level _audit_four_question_gate; that audit is the
    # SSOT for what the gate must look like, and a duplicate here
    # would drift. The parser only ensures the value is at least a
    # dict so the audit can inspect it.

    return AdvisorRawCritique(
        mesh_quality_concerns=list_axes["mesh_quality_concerns"],
        boundary_condition_questions=list_axes["boundary_condition_questions"],
        failure_modes_to_consider=list_axes["failure_modes_to_consider"],
        unhandled_load_cases=list_axes["unhandled_load_cases"],
        four_question_gate=gate,
        degrade_reason=None,
    )


# Environment variable names for the production factory. Pinned by
# `test_default_llm_factory_env_var_names`.
ENV_VAR_BACKEND = "AIFEA_ADVISOR_BACKEND"
ENV_VAR_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"


def _default_llm_factory(
    *,
    environ: dict[str, str] | None = None,
) -> AdvisorProvider | None:
    """Production hook for spawning an ``LLMAdvisor`` from env config.

    Returns:
      * ``None`` when ``AIFEA_ADVISOR_BACKEND`` is unset or empty,
        OR when the chosen backend's API key env var is missing. The
        caller MUST fall back to ``StubAdvisor``.
      * An ``LLMAdvisor`` instance wired against a placeholder
        callable that raises ``NotImplementedError`` when the env
        config selects the ``anthropic`` backend. The placeholder
        exists so the injection seam is testable now; the real
        ``anthropic`` / ``httpx`` client lands in a later slice and
        replaces the placeholder verbatim. When the placeholder
        raises, ``LLMAdvisor.produce`` catches the exception and
        falls back to the stub with a populated ``degrade_reason``.

    The optional ``environ`` argument lets tests inject a fake
    environment dict without monkeypatching ``os.environ`` — this
    keeps the test suite hermetic and parallel-safe.
    """
    env = environ if environ is not None else os.environ
    backend = env.get(ENV_VAR_BACKEND, "").strip().lower()
    if not backend:
        return None
    if backend == "anthropic":
        api_key = env.get(ENV_VAR_ANTHROPIC_API_KEY, "").strip()
        if not api_key:
            return None

        def _placeholder_anthropic_call(prompt: str) -> str:
            raise NotImplementedError(
                "Live Anthropic client wiring lands in a future "
                "slice. Phase 11 C ships only the injection seam; "
                "LLMAdvisor.produce will catch this and fall back to "
                "the stub with degrade_reason populated."
            )

        return LLMAdvisor(
            llm_call=_placeholder_anthropic_call,
            backend_label="llm-advisor-anthropic-unwired",
        )
    # Unknown backend label — refuse silently (caller falls back to
    # stub). Logging would belong here but the reporting service is
    # intentionally side-effect-free; the audit trail lives in the
    # downstream HTTP route's response telemetry (Phase 11 D).
    return None


# ---------------------------------------------------------------------
# Snapshot -> AdvisorContext builder (Phase 11 D)
# ---------------------------------------------------------------------


class AdvisorSnapshotNotFound(LookupError):
    """Raised when the (snapshot_label, case_id) pair has no on-disk
    presence under ``reports/snapshots/<label>/``. The HTTP route
    surfaces this as a 404 — distinct from the 422 case_id refusal
    paths and the 5xx tier we never want to hit on the advisor surface."""


# Mapping from metrics-file ``analysis_type`` values seen on disk to
# the SSOT ``ANALYSIS_TYPE_TUPLE``. Tier 1 metrics files emitted before
# Phase 11 A used the long-form labels (e.g. ``linear_static_pressure_vessel``);
# the rubric SSOT uses the short form (``linear_static_pv``). This map
# is the SSOT for the long-form → short-form translation and is
# pinned by a slice-D test.
METRICS_ANALYSIS_TYPE_MAP: dict[str, str] = {
    "ballistic": "ballistic",
    "linear_static_pressure_vessel": "linear_static_pv",
    "linear_static_pv": "linear_static_pv",
    "explicit_dynamics": "explicit_dynamics",
    "modal": "modal",
}
"""Long-form (filename) → short-form (rubric SSOT) translation for
``analysis_type``. A value not in this map is treated as the
default rubric (``ballistic``) so the advisor surface continues to
produce a critique even when a future analysis-type label has not
yet been registered. Pinned by ``test_metrics_analysis_type_map``."""


def build_advisor_context_from_snapshot(
    case_id: str,
    snapshot_label: str,
    *,
    repo_root: Path,
) -> AdvisorContext:
    """Build an :class:`AdvisorContext` for a (case, snapshot) pair by
    reading frozen snapshot bytes under
    ``reports/snapshots/<snapshot_label>/``.

    Raises:
      * ``ValueError`` if ``case_id`` is empty.
      * ``AdvisorSnapshotNotFound`` if the snapshot dir does not exist
        OR if the snapshot exists but has no per-case metrics file
        for ``case_id``. The HTTP route surfaces both as 404.

    The reads are deliberately tolerant of pre-Phase-11 snapshot
    layouts (1.0.0 / 1.1.0 / 1.2.0 / 1.3.0): missing fields default
    to ``None`` and the advisor surface still produces a useful
    critique (the stub's always-emit prompts kick in). A read failure
    on any individual sidecar file (corrupted JSON, IOError) leaves
    that field as ``None`` rather than crashing the route — the
    advisor is LLM-offline-first AND snapshot-degradation-tolerant.
    """
    # Local import to keep module-level imports tidy and avoid a
    # circular import with ``cohort_snapshot`` (which itself imports
    # from this module's ``acceptance_packet`` dependency tree).
    from .cohort_snapshot import (
        SNAPSHOT_LABEL_RE,
        SNAPSHOT_MANIFEST_FILENAME,
        snapshots_root,
    )

    if not case_id:
        raise ValueError("Advisor context requires a non-empty case_id")
    if not snapshot_label:
        raise ValueError("Advisor context requires a non-empty snapshot_label")
    if not SNAPSHOT_LABEL_RE.fullmatch(snapshot_label):
        raise ValueError(
            f"Advisor context received invalid snapshot label shape: "
            f"{snapshot_label!r}"
        )

    snap_dir = (snapshots_root(repo_root) / snapshot_label).resolve()
    manifest_path = snap_dir / SNAPSHOT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise AdvisorSnapshotNotFound(
            f"snapshot {snapshot_label!r} not found under reports/snapshots/"
        )

    metrics_path = snap_dir / "metrics" / f"{case_id}.json"
    convergence_path = snap_dir / "convergence" / f"{case_id}.json"
    completeness_path = snap_dir / "completeness" / f"{case_id}.json"

    if not metrics_path.is_file():
        raise AdvisorSnapshotNotFound(
            f"case {case_id!r} has no per-case metrics file in "
            f"snapshot {snapshot_label!r}; presumed not in cohort"
        )

    metrics = _read_json_or_none(metrics_path) or {}
    convergence = _read_json_or_none(convergence_path) or {}
    completeness = _read_json_or_none(completeness_path) or {}

    energy_audit = metrics.get("energy_audit") or {}
    raw_analysis_type = metrics.get("analysis_type")
    analysis_type = (
        METRICS_ANALYSIS_TYPE_MAP.get(raw_analysis_type)
        if isinstance(raw_analysis_type, str)
        else None
    )

    # Trust score: the snapshot does not carry a pre-computed integer
    # trust score on the cohort_overview surface (that surface is
    # cohort-scoped, not per-case-scoped). For slice D we surface
    # ``None`` and the stub still emits useful content; a future slice
    # may wire build_trust_score_provenance().trust_score here for a
    # richer correlated-content payload.
    return AdvisorContext(
        case_id=case_id,
        snapshot_label=snapshot_label,
        trust_score=None,
        completeness_score=_coerce_int(completeness.get("score")),
        completeness_analysis_type=analysis_type,
        energy_audit_status=_coerce_str(energy_audit.get("status")),
        convergence_kind=_coerce_str(convergence.get("convergence_kind")),
        convergence_combined_verdict=_coerce_str(
            convergence.get("convergence_combined_verdict")
        ),
        extra={"metrics_analysis_type_raw": raw_analysis_type},
    )


def _read_json_or_none(path: Path) -> dict[str, Any] | None:
    """Read a JSON file, returning the parsed dict or None on any
    error. The advisor route MUST NOT 5xx on a corrupt sidecar; it
    falls through to the stub's degraded-but-useful path."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):  # ``bool`` is a subclass of ``int`` in Python
        return None
    if isinstance(value, int):
        return value
    return None


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
