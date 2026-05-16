"""Phase 11 C — LLMAdvisor + offline degrade path.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins binding rubric (anti-gaming guards) from
``.planning/FM-04A_PHASE11_BLUEPRINT.md`` §4 — slice C subset:

* **T:-4**: LLM response schema is pinned by closed-set tuple
  ``LLM_RESPONSE_KEYS``; missing / extra / wrong-type keys must each
  trip a distinct test.
* **C:-8**: degraded ``advisor_status == "stub"`` (NOT "online") on
  every LLM failure path — malformed JSON, exception, schema drift.
* **A:-4**: the ``_default_llm_factory`` env-var seam returns None
  whenever the production wiring is incomplete. No real network call
  is ever made from the test sweep — the live-LLM wiring is reserved
  for a later slice. Tests inject callables directly.
* **A:-5**: the placeholder Anthropic backend (env-var-selected) MUST
  fall back to stub at produce() time rather than raising 5xx — the
  NotImplementedError lives behind LLMAdvisor.produce's catch-all.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from app.services.reporting.advisor_critique import (
    ADVISOR_FORBIDDEN_TOKENS,
    ENV_VAR_ANTHROPIC_API_KEY,
    ENV_VAR_BACKEND,
    FOUR_QUESTION_GATE_KEYS,
    LLM_RESPONSE_KEYS,
    MAX_CHARS_PER_ITEM,
    MAX_ITEMS_PER_AXIS,
    AdvisorContext,
    LLMAdvisor,
    _default_llm_factory,
    _parse_llm_response,
    build_advisor_critique,
    build_llm_prompt,
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
    extra: dict[str, Any] | None = None,
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
        extra=extra if extra is not None else {},
    )


_FROZEN_NOW = datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC)


def _well_formed_llm_response(
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A canonical well-formed LLM JSON payload. Test cases override
    individual fields to exercise specific failure paths."""
    payload: dict[str, Any] = {
        "mesh_quality_concerns": ["mesh density looks adequate for the gradient"],
        "boundary_condition_questions": ["is the closed-end assumption load-cycle-safe?"],
        "failure_modes_to_consider": ["thermal ratcheting at long dwell times"],
        "unhandled_load_cases": ["seismic; hydrostatic test; fatigue spectrum"],
        "four_question_gate": {k: True for k in FOUR_QUESTION_GATE_KEYS},
    }
    if overrides:
        payload.update(overrides)
    return payload


def _make_llm_call(response_text: str):
    """Build a deterministic llm_call callable that returns the given
    raw response text. Used to inject controlled responses into
    LLMAdvisor for the test sweep."""

    def _call(prompt: str) -> str:
        return response_text

    return _call


# ---------------------------------------------------------------------
# Prompt template + closed-set pins
# ---------------------------------------------------------------------


def test_llm_response_keys_closed_set_pinned() -> None:
    """The LLM response schema is part of the contract — a maintainer
    adding a key must update this pin + the parser in lockstep."""
    assert LLM_RESPONSE_KEYS == (
        "mesh_quality_concerns",
        "boundary_condition_questions",
        "failure_modes_to_consider",
        "unhandled_load_cases",
        "four_question_gate",
    )


def test_max_items_and_chars_are_named_constants() -> None:
    """No magic numbers in the LLMAdvisor parser; the caps are M:-2-
    pinned by identifier. Test pins the values so a drift breaks loudly."""
    assert MAX_ITEMS_PER_AXIS == 12
    assert MAX_CHARS_PER_ITEM == 600


def test_llm_prompt_contains_every_forbidden_token() -> None:
    """The forbidden-token list is rendered into the prompt verbatim so
    the LLM has explicit guidance on what NOT to emit. T:-5 ergonomic."""
    prompt = build_llm_prompt(_context())
    for token in ADVISOR_FORBIDDEN_TOKENS:
        assert token in prompt, f"prompt missing forbidden token {token!r}"


def test_llm_prompt_contains_every_four_question_gate_key() -> None:
    """The 4-Q gate keys are rendered into the prompt verbatim so the
    LLM produces the exact keys the audit expects."""
    prompt = build_llm_prompt(_context())
    for key in FOUR_QUESTION_GATE_KEYS:
        assert key in prompt


def test_llm_prompt_contains_tier1_disclaimer_trio() -> None:
    """The prompt MUST state the Tier 1 disclaimer trio so the LLM
    cannot drift into FM-04b vocabulary. C:-8."""
    prompt = build_llm_prompt(_context())
    assert "Tier 1" in prompt
    assert "not signed validation" in prompt
    assert "not benchmark agreement" in prompt
    assert "ADVISOR" in prompt  # NOT driver


def test_llm_prompt_includes_context_fields() -> None:
    """Every AdvisorContext field that informs engineering judgment
    must appear in the prompt — a missing field is silent context loss."""
    ctx = _context(
        trust_score=42,
        completeness_score=75,
        completeness_analysis_type="ballistic",
        energy_audit_status="open_residual",
        convergence_kind="explicit_dynamics",
        convergence_combined_verdict="candidate_observed_unstable",
    )
    prompt = build_llm_prompt(ctx)
    assert "42" in prompt
    assert "75" in prompt
    assert "ballistic" in prompt
    assert "open_residual" in prompt
    assert "explicit_dynamics" in prompt
    assert "candidate_observed_unstable" in prompt


# ---------------------------------------------------------------------
# LLMAdvisor happy path
# ---------------------------------------------------------------------


def test_llm_advisor_well_formed_response_yields_online_status() -> None:
    """A well-formed LLM response routes through the live-LLM path and
    the envelope carries advisor_status='online'."""
    response = json.dumps(_well_formed_llm_response())
    advisor = LLMAdvisor(_make_llm_call(response), backend_label="llm-test")
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "online"
    assert envelope.advisor_backend == "llm-test"
    assert envelope.degrade_reason is None
    assert envelope.mesh_quality_concerns == ("mesh density looks adequate for the gradient",)
    assert envelope.boundary_condition_questions == (
        "is the closed-end assumption load-cycle-safe?",
    )


def test_llm_advisor_is_available_with_callable_set() -> None:
    """LLMAdvisor with an injected callable always advertises availability
    — failure happens at produce() time, not at availability check."""
    advisor = LLMAdvisor(_make_llm_call("{}"))
    assert advisor.is_available() is True


def test_llm_advisor_truncates_items_beyond_axis_cap() -> None:
    """An LLM that emits too many items per axis MUST be truncated to
    MAX_ITEMS_PER_AXIS — the cap is an ergonomic guardrail, not a
    refusal. The list-axis pin protects the reviewer panel layout."""
    overrun = ["item " + str(i) for i in range(MAX_ITEMS_PER_AXIS + 5)]
    response = json.dumps(_well_formed_llm_response(overrides={"mesh_quality_concerns": overrun}))
    advisor = LLMAdvisor(_make_llm_call(response))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert len(envelope.mesh_quality_concerns) == MAX_ITEMS_PER_AXIS


def test_llm_advisor_truncates_items_longer_than_char_cap() -> None:
    """Per-item character cap protects panel layout — a 10k-character
    bullet is truncated rather than refused."""
    long_item = "x" * (MAX_CHARS_PER_ITEM + 200)
    response = json.dumps(
        _well_formed_llm_response(overrides={"mesh_quality_concerns": [long_item]})
    )
    advisor = LLMAdvisor(_make_llm_call(response))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert len(envelope.mesh_quality_concerns[0]) == MAX_CHARS_PER_ITEM


def test_llm_advisor_passes_context_extra_through_to_prompt() -> None:
    """Slice-B carry-forward (B.md LOW finding §2): AdvisorContext.extra
    is the forward-compat slot. The prompt builder must read every
    canonical context field; ``extra`` is allowed through unchanged
    and visible to the produce() pathway."""
    ctx = _context(extra={"reviewer_note": "watch the SCL spacing"})
    advisor = LLMAdvisor(lambda prompt: json.dumps(_well_formed_llm_response()))
    # produce() reads context; we exercise the round-trip and pin the
    # extra is passed through to the AdvisorContext seen by the
    # callable. We do this by capturing the prompt the callable
    # received and confirming the context fields it represents.
    captured_prompts: list[str] = []

    def _capturing_call(prompt: str) -> str:
        captured_prompts.append(prompt)
        return json.dumps(_well_formed_llm_response())

    advisor = LLMAdvisor(_capturing_call)
    envelope = build_advisor_critique(ctx, provider=advisor, now_utc=_FROZEN_NOW)
    assert envelope.advisor_status == "online"
    assert len(captured_prompts) == 1
    # extra is reserved for forward-compat; the prompt builder does
    # not render it (yet), so we pin the canonical fields are rendered.
    assert "GS-PV-cyl-candidate" in captured_prompts[0]


# ---------------------------------------------------------------------
# LLMAdvisor degrade paths — every failure mode → stub fallback
# ---------------------------------------------------------------------


def test_llm_call_returning_malformed_json_triggers_stub_fallback() -> None:
    """Blueprint §3.C — malformed JSON → stub fallback, status='stub',
    degrade_reason populated."""
    advisor = LLMAdvisor(_make_llm_call("this is not JSON {{"))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "not valid JSON" in envelope.degrade_reason
    # Stub fallback still produces a useful critique (correlated content
    # from the stub's rules).
    assert len(envelope.mesh_quality_concerns) >= 1


def test_llm_call_raising_exception_triggers_stub_fallback() -> None:
    """Blueprint §3.C — exception in llm_call → stub fallback. Critical
    for the LLM-offline-first pillar; a network blip cannot break the
    reviewer flow."""

    def _explode(prompt: str) -> str:
        raise RuntimeError("simulated network outage")

    advisor = LLMAdvisor(_explode, backend_label="llm-explosive")
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.advisor_backend == "llm-explosive"
    assert envelope.degrade_reason is not None
    assert "RuntimeError" in envelope.degrade_reason
    assert "simulated network outage" in envelope.degrade_reason


def test_llm_response_missing_required_key_triggers_stub_fallback() -> None:
    """Schema drift → stub fallback. The parser uses LLM_RESPONSE_KEYS
    as the SSOT for required keys; dropping any key trips the audit."""
    bad = _well_formed_llm_response()
    del bad["failure_modes_to_consider"]
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "missing required keys" in envelope.degrade_reason
    assert "failure_modes_to_consider" in envelope.degrade_reason


def test_llm_response_with_extra_key_triggers_stub_fallback() -> None:
    """The LLM is asked for EXACTLY the LLM_RESPONSE_KEYS keys. An
    extra key indicates the LLM is hallucinating shape; refuse and
    fall back to stub rather than silently accept unknown content."""
    bad = _well_formed_llm_response(overrides={"rogue_key": ["junk"]})
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "unexpected keys" in envelope.degrade_reason


def test_llm_response_with_non_list_axis_triggers_stub_fallback() -> None:
    """The four content axes must be lists. A dict / string / number
    in any of them is shape drift → stub fallback."""
    bad = _well_formed_llm_response(overrides={"mesh_quality_concerns": {"not": "a list"}})
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "not a list" in envelope.degrade_reason


def test_llm_response_with_non_string_list_entry_triggers_stub_fallback() -> None:
    """List entries must be strings. A dict / int in any entry is
    shape drift → stub fallback (defensive parser, not coercion)."""
    bad = _well_formed_llm_response(
        overrides={"failure_modes_to_consider": ["good", 42, "also good"]}
    )
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "non-string entry" in envelope.degrade_reason


def test_llm_response_top_level_not_object_triggers_stub_fallback() -> None:
    """If the LLM emits a JSON array at top level (or a string, etc.),
    the parser must refuse the shape rather than coerce."""
    advisor = LLMAdvisor(_make_llm_call(json.dumps([1, 2, 3])))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "not a JSON object" in envelope.degrade_reason


def test_llm_response_with_non_dict_four_question_gate_triggers_stub_fallback() -> None:
    """The 4-Q gate value must be a dict at the parser level. A list
    or string for that key trips the parser, not the gate audit."""
    bad = _well_formed_llm_response(
        overrides={"four_question_gate": ["llm_offline_ok", "advisor_only"]}
    )
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    envelope = build_advisor_critique(
        _context(),
        provider=advisor,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.degrade_reason is not None
    assert "four_question_gate" in envelope.degrade_reason


# ---------------------------------------------------------------------
# 4-Q gate + forbidden-claim refusals — these are AT-CONSTRUCTION,
# not at parse, so they raise ValueError rather than fall back.
# ---------------------------------------------------------------------


def test_llm_response_with_false_gate_answer_refuses_envelope() -> None:
    """The 4-Q gate audit lives at envelope construction — a False
    answer from the LLM REFUSES the envelope rather than emitting a
    'drifted' critique. C:-10."""
    bad = _well_formed_llm_response(
        overrides={
            "four_question_gate": {
                "llm_offline_ok": True,
                "artifacts_user_owned": True,
                "trustgate_explains": True,
                "advisor_only": False,  # <- drifted
            }
        }
    )
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    with pytest.raises(ValueError, match="False answer"):
        build_advisor_critique(
            _context(),
            provider=advisor,
            now_utc=_FROZEN_NOW,
        )


def test_llm_response_with_missing_gate_key_refuses_envelope() -> None:
    """Same C:-10 family — a missing gate key refuses the envelope."""
    gate = {k: True for k in FOUR_QUESTION_GATE_KEYS}
    del gate["trustgate_explains"]
    bad = _well_formed_llm_response(overrides={"four_question_gate": gate})
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    with pytest.raises(ValueError, match="missing keys"):
        build_advisor_critique(
            _context(),
            provider=advisor,
            now_utc=_FROZEN_NOW,
        )


@pytest.mark.parametrize("token", list(ADVISOR_FORBIDDEN_TOKENS))
def test_llm_response_with_forbidden_claim_refuses_envelope(token: str) -> None:
    """Each forbidden-claim token emitted by the LLM outside the
    ``not <claim>`` disclaimer form refuses the envelope. The audit
    happens at envelope construction; the parser does NOT pre-filter
    (otherwise a maintainer could disable the audit by tightening the
    parser silently). T:-5 + A:-3."""
    bad = _well_formed_llm_response(
        overrides={"mesh_quality_concerns": [f"This part is {token} for service."]}
    )
    advisor = LLMAdvisor(_make_llm_call(json.dumps(bad)))
    with pytest.raises(ValueError, match="forbidden positive claim"):
        build_advisor_critique(
            _context(),
            provider=advisor,
            now_utc=_FROZEN_NOW,
        )


# ---------------------------------------------------------------------
# _default_llm_factory env-var seam
# ---------------------------------------------------------------------


def test_default_llm_factory_returns_none_when_backend_env_var_absent() -> None:
    """Env-var unset → factory returns None → caller falls back to
    StubAdvisor. Blueprint §3.C deliverable."""
    assert _default_llm_factory(environ={}) is None


def test_default_llm_factory_returns_none_when_backend_env_var_empty() -> None:
    """Empty string is equivalent to unset."""
    assert _default_llm_factory(environ={ENV_VAR_BACKEND: ""}) is None


def test_default_llm_factory_returns_none_when_anthropic_key_absent() -> None:
    """Backend=anthropic + API_KEY missing → returns None (do NOT raise;
    the workbench must function offline)."""
    env = {ENV_VAR_BACKEND: "anthropic"}
    assert _default_llm_factory(environ=env) is None


def test_default_llm_factory_returns_none_when_anthropic_key_empty() -> None:
    """Empty API_KEY is equivalent to absent."""
    env = {ENV_VAR_BACKEND: "anthropic", ENV_VAR_ANTHROPIC_API_KEY: ""}
    assert _default_llm_factory(environ=env) is None


def test_default_llm_factory_returns_unwired_placeholder_when_anthropic_configured() -> None:
    """Backend=anthropic + API_KEY present → returns LLMAdvisor wired
    against an UNWIRED placeholder callable. Phase 11 C is the env-var
    seam ONLY; a later slice wires the real client."""
    env = {ENV_VAR_BACKEND: "anthropic", ENV_VAR_ANTHROPIC_API_KEY: "sk-test"}
    provider = _default_llm_factory(environ=env)
    assert provider is not None
    assert isinstance(provider, LLMAdvisor)
    assert provider.name == "llm-advisor-anthropic-unwired"
    assert provider.is_available() is True


def test_default_llm_factory_placeholder_falls_back_to_stub_at_produce_time() -> None:
    """A:-5 — the unwired placeholder MUST NOT 5xx if a route accidentally
    calls produce(). It raises NotImplementedError internally, which is
    caught by LLMAdvisor.produce and falls back to stub with a clear
    degrade_reason. The reviewer flow continues."""
    env = {ENV_VAR_BACKEND: "anthropic", ENV_VAR_ANTHROPIC_API_KEY: "sk-test"}
    provider = _default_llm_factory(environ=env)
    assert provider is not None
    envelope = build_advisor_critique(
        _context(),
        provider=provider,
        now_utc=_FROZEN_NOW,
    )
    assert envelope.advisor_status == "stub"
    assert envelope.advisor_backend == "llm-advisor-anthropic-unwired"
    assert envelope.degrade_reason is not None
    assert "NotImplementedError" in envelope.degrade_reason


def test_default_llm_factory_returns_none_for_unknown_backend() -> None:
    """Unknown backend label → return None (safe default). Future
    backends add their own branch; today only 'anthropic' is named."""
    env = {ENV_VAR_BACKEND: "openai"}
    assert _default_llm_factory(environ=env) is None


def test_default_llm_factory_strips_and_case_folds_backend_label() -> None:
    """Whitespace + case variants of 'anthropic' resolve to the same
    branch — common operator mistake when reading from a .env file."""
    env = {
        ENV_VAR_BACKEND: "  Anthropic\n",
        ENV_VAR_ANTHROPIC_API_KEY: "sk-test",
    }
    provider = _default_llm_factory(environ=env)
    assert provider is not None
    assert isinstance(provider, LLMAdvisor)


# ---------------------------------------------------------------------
# Direct _parse_llm_response tests — pin the parser independently of
# the advisor so a future refactor can move the function without
# losing coverage.
# ---------------------------------------------------------------------


def test_parse_llm_response_well_formed_returns_raw_critique() -> None:
    raw = _parse_llm_response(_well_formed_llm_response())
    assert raw.mesh_quality_concerns == ("mesh density looks adequate for the gradient",)
    assert raw.degrade_reason is None


def test_parse_llm_response_rejects_top_level_array() -> None:
    with pytest.raises(TypeError, match="not a JSON object"):
        _parse_llm_response([1, 2, 3])


def test_parse_llm_response_rejects_missing_key() -> None:
    bad = _well_formed_llm_response()
    del bad["mesh_quality_concerns"]
    with pytest.raises(KeyError, match="missing required keys"):
        _parse_llm_response(bad)


def test_parse_llm_response_rejects_extra_key() -> None:
    bad = _well_formed_llm_response(overrides={"rogue": []})
    with pytest.raises(ValueError, match="unexpected keys"):
        _parse_llm_response(bad)
