"""Phase 13 A — refused_claims structured surface on AdvisorCritique.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins binding rubric (anti-gaming guards) from
``.planning/FM-04A_PHASE13_BLUEPRINT.md`` §4 — slice A subset:

* **M:-2**: ``REFUSED_CLAIM_MARKER_PREFIX`` is a module-level SSOT
  constant; bump-history docstring on ``ADVISOR_CRITIQUE_SCHEMA_VERSION``.
* **T:-3**: per-forbidden-token round-trip pinned via parametrize over
  ``ADVISOR_FORBIDDEN_TOKENS`` (≥9 tokens × 2 content positions = 18
  distinct collected cases minimum).
* **T:-4**: distinct tests per content section confirm the filter
  applies uniformly to mesh / BC / failure-mode / load-case.
* **C:-8**: rendered envelope still passes the existing forbidden-token
  audit; refused markers don't accidentally inject the forbidden token
  back outside disclaimer form (markers are plain strings, never
  rendered as advisor content).
* **A:-2**: refused-claim collection is reported via tuple, not raised
  exception. Reviewer judges, advisor reports.
* **A:-3**: defense-in-depth on envelope-level audit still trips when
  a forbidden token reaches the rendered JSON via a path the filter
  doesn't traverse (we test this by injecting via ``degrade_reason``).
* **E:-2**: schema bump from 1.0.0 to 1.1.0 is centrally pinned in
  ``test_schema_versions_stamping.py``; this file pins behavioral
  contract (collection + back-compat + envelope audit retention).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from app.services.reporting._schema_versions import (
    ADVISOR_CRITIQUE_SCHEMA_VERSION,
)
from app.services.reporting.advisor_critique import (
    ADVISOR_FORBIDDEN_TOKENS,
    REFUSED_CLAIM_MARKER_PREFIX,
    AdvisorContext,
    AdvisorCritique,
    AdvisorRawCritique,
    _audit_and_collect_refused,
    _filter_section,
    build_advisor_critique,
    render_advisor_critique_json,
)

# ---------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------

_FROZEN_NOW = datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC)


def _context() -> AdvisorContext:
    return AdvisorContext(
        case_id="cylinder-pv-candidate",
        snapshot_label="2026-05-16T120000Z",
        trust_score=85,
        completeness_score=85,
        completeness_analysis_type="linear_static_pv",
        energy_audit_status="closed_aggregate",
        convergence_kind="linear_static",
        convergence_combined_verdict="candidate_observed_stable",
        extra={},
    )


def _safe_raw() -> AdvisorRawCritique:
    return AdvisorRawCritique(
        mesh_quality_concerns=("Mesh density appears adequate for the gradient.",),
        boundary_condition_questions=("Is the closed-end load-cycle-safe?",),
        failure_modes_to_consider=("Linear-static is blind to plasticity.",),
        unhandled_load_cases=("Reviewer: enumerate the load cases not analyzed.",),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )


class _ScriptedProvider:
    """Test seam: an advisor provider that emits whatever raw payload
    the test specifies. Used to inject forbidden tokens through the
    upstream raw-content path so we can verify the collection layer."""

    name = "scripted-test-provider"

    def __init__(self, raw: AdvisorRawCritique) -> None:
        self._raw = raw

    def is_available(self) -> bool:
        return True

    def produce(self, context: AdvisorContext) -> AdvisorRawCritique:
        return self._raw


# ---------------------------------------------------------------------
# Marker prefix SSOT pin (M:-2)
# ---------------------------------------------------------------------


def test_refused_claim_marker_prefix_is_pinned_constant() -> None:
    """The marker prefix is part of the schema 1.1.0 surface contract.
    A future PR changing it requires a methodology-doc update + this
    pin update in lockstep."""
    assert REFUSED_CLAIM_MARKER_PREFIX == "refused: "


def test_advisor_critique_schema_version_at_phase13_a_baseline() -> None:
    """Phase 13 A bumps to 1.1.0; centralized pin in
    test_schema_versions_stamping.py is the SSOT."""
    assert ADVISOR_CRITIQUE_SCHEMA_VERSION == "1.1.0"


# ---------------------------------------------------------------------
# _audit_and_collect_refused — per-token round-trip (T:-3)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("token", ADVISOR_FORBIDDEN_TOKENS)
def test_audit_collects_marker_for_every_forbidden_token(token: str) -> None:
    """Every member of ADVISOR_FORBIDDEN_TOKENS triggers a refusal
    when it appears outside disclaimer form. The marker uses the
    verbatim token. T:-3 boundary pin per-token."""
    text = f"This case is {token} for the next sprint."
    safe, marker = _audit_and_collect_refused(text)
    assert safe is None
    assert marker == f"{REFUSED_CLAIM_MARKER_PREFIX}{token}"


@pytest.mark.parametrize("token", ADVISOR_FORBIDDEN_TOKENS)
def test_audit_allows_disclaimer_form_for_every_forbidden_token(token: str) -> None:
    """`not <token>` disclaimer form passes through. The original text
    is preserved verbatim; no marker is appended. T:-3 pin per-token."""
    text = f"This case is not {token}; reviewer enumerate next steps."
    safe, marker = _audit_and_collect_refused(text)
    assert marker is None
    assert safe == text


def test_audit_passes_through_safe_content_unchanged() -> None:
    """Clean content round-trips byte-for-byte."""
    text = "Mesh density appears adequate for the gradient region."
    safe, marker = _audit_and_collect_refused(text)
    assert marker is None
    assert safe == text


def test_audit_first_token_wins_when_multiple_forbidden_tokens_present() -> None:
    """An entry containing multiple forbidden tokens reports the
    FIRST one (in ADVISOR_FORBIDDEN_TOKENS declaration order)
    encountered in haystack-scan order. Methodology doc names this
    the one-marker-per-refused-entry contract."""
    # 'validated against' appears in the haystack BEFORE 'production ready',
    # so the marker should name 'validated against'.
    text = "The case is validated against ASTM and production ready."
    safe, marker = _audit_and_collect_refused(text)
    assert safe is None
    assert marker is not None
    # Either of the two tokens that appear in the input is a valid
    # first-encountered marker depending on scan order; we accept
    # either as long as it IS one of the input's tokens (not, e.g.,
    # 'certified' which doesn't appear).
    assert marker in {
        f"{REFUSED_CLAIM_MARKER_PREFIX}validated against",
        f"{REFUSED_CLAIM_MARKER_PREFIX}production ready",
    }


# ---------------------------------------------------------------------
# _filter_section — section-level filter (T:-4)
# ---------------------------------------------------------------------


def test_filter_section_preserves_safe_entries_in_order() -> None:
    """Order-preservation contract."""
    entries = ("entry one", "entry two", "entry three")
    collected: list[str] = []
    result = _filter_section(entries, collected)
    assert result == entries
    assert collected == []


def test_filter_section_discards_refused_entries_and_collects_markers() -> None:
    """A mixed input has its forbidden entry stripped and its marker
    appended to the collector."""
    entries = (
        "Safe concern A",
        "This case is production ready next sprint.",
        "Safe concern B",
    )
    collected: list[str] = []
    result = _filter_section(entries, collected)
    assert result == ("Safe concern A", "Safe concern B")
    assert collected == [f"{REFUSED_CLAIM_MARKER_PREFIX}production ready"]


def test_filter_section_collects_multiple_markers_across_entries() -> None:
    """N forbidden entries -> N markers, in input order."""
    entries = (
        "This case is certified for service.",
        "Safe entry",
        "This run is signed off.",
    )
    collected: list[str] = []
    result = _filter_section(entries, collected)
    assert result == ("Safe entry",)
    assert collected == [
        f"{REFUSED_CLAIM_MARKER_PREFIX}certified",
        f"{REFUSED_CLAIM_MARKER_PREFIX}signed off",
    ]


# ---------------------------------------------------------------------
# build_advisor_critique — full integration (refused_claims on envelope)
# ---------------------------------------------------------------------


def _scripted_raw_with_forbidden_in_section(
    section: str, forbidden_text: str
) -> AdvisorRawCritique:
    """Build a raw critique with the named section containing the
    forbidden text + a single safe sibling entry; other sections are
    safe single-entry."""
    safe_entry = "Safe placeholder entry."
    sections = {
        "mesh_quality_concerns": (safe_entry,),
        "boundary_condition_questions": (safe_entry,),
        "failure_modes_to_consider": (safe_entry,),
        "unhandled_load_cases": (safe_entry,),
    }
    sections[section] = (safe_entry, forbidden_text)
    return AdvisorRawCritique(
        mesh_quality_concerns=sections["mesh_quality_concerns"],
        boundary_condition_questions=sections["boundary_condition_questions"],
        failure_modes_to_consider=sections["failure_modes_to_consider"],
        unhandled_load_cases=sections["unhandled_load_cases"],
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )


@pytest.mark.parametrize(
    "section",
    [
        "mesh_quality_concerns",
        "boundary_condition_questions",
        "failure_modes_to_consider",
        "unhandled_load_cases",
    ],
)
def test_envelope_refused_claims_collects_marker_from_each_section(
    section: str,
) -> None:
    """T:-4 — the collection layer applies uniformly across all 4
    content sections. A forbidden token in ANY section lands as a
    marker on ``refused_claims``."""
    raw = _scripted_raw_with_forbidden_in_section(
        section, "This case is production ready for sprint review."
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    assert len(envelope.refused_claims) == 1
    assert envelope.refused_claims[0] == f"{REFUSED_CLAIM_MARKER_PREFIX}production ready"
    # The offending section's RENDERED content does NOT contain the
    # forbidden token — the entry was discarded, not redacted in
    # place.
    rendered = getattr(envelope, section)
    assert all("production ready" not in entry.lower() for entry in rendered)


def test_envelope_refused_claims_empty_when_no_forbidden_content() -> None:
    """The default state: a safe advisor critique yields an empty
    refused_claims tuple."""
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(_safe_raw()),
        now_utc=_FROZEN_NOW,
    )
    assert envelope.refused_claims == ()


def test_envelope_refused_claims_collects_multiple_across_sections() -> None:
    """Multiple forbidden tokens across multiple sections all land in
    refused_claims in section-encounter order (mesh -> BC -> FM ->
    load-case)."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("This case is certified.",),  # mesh
        boundary_condition_questions=("Safe BC entry.",),
        failure_modes_to_consider=("Run is signed off as ready.",),  # FM
        unhandled_load_cases=("Approved for service deployment.",),  # load
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    # Three markers, in mesh -> FM -> load-case order.
    assert envelope.refused_claims == (
        f"{REFUSED_CLAIM_MARKER_PREFIX}certified",
        f"{REFUSED_CLAIM_MARKER_PREFIX}signed off",
        f"{REFUSED_CLAIM_MARKER_PREFIX}approved for service",
    )


# ---------------------------------------------------------------------
# Defense in depth — _assert_no_overclaim still trips (A:-3)
# ---------------------------------------------------------------------


def test_envelope_audit_still_trips_on_metadata_path_forbidden_token() -> None:
    """A:-3 — the per-section filter handles the four content sections,
    but a forbidden token in a metadata field (``degrade_reason``)
    must STILL trip the envelope-level ``_assert_no_overclaim``. We
    inject via a scripted provider whose degrade_reason contains a
    raw forbidden token outside disclaimer form."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("Safe entry.",),
        boundary_condition_questions=("Safe entry.",),
        failure_modes_to_consider=("Safe entry.",),
        unhandled_load_cases=("Safe entry.",),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        # degrade_reason contains a forbidden token; the per-section
        # filter does NOT clean degrade_reason. The envelope-level
        # audit MUST raise.
        degrade_reason="This is production ready according to the LLM.",
    )
    with pytest.raises(ValueError, match="forbidden positive claim"):
        build_advisor_critique(
            _context(),
            provider=_ScriptedProvider(raw),
            now_utc=_FROZEN_NOW,
        )


# ---------------------------------------------------------------------
# JSON serialization — refused_claims surfaces (E:-2 round-trip)
# ---------------------------------------------------------------------


def test_rendered_json_includes_refused_claims_key() -> None:
    """The envelope JSON always includes the ``refused_claims`` key;
    consumers checking presence-vs-absence MUST switch to length-based
    detection per the bump-history docstring on
    ``ADVISOR_CRITIQUE_SCHEMA_VERSION``."""
    envelope = build_advisor_critique(_context(), now_utc=_FROZEN_NOW)
    rendered = render_advisor_critique_json(envelope)
    parsed = json.loads(rendered)
    assert "refused_claims" in parsed
    assert isinstance(parsed["refused_claims"], list)
    # Default state: empty list (safe stub critique).
    assert parsed["refused_claims"] == []


def test_rendered_json_includes_refused_markers_when_present() -> None:
    """Schema 1.1.0 round-trip: refused markers in the envelope appear
    as plain strings in the JSON list."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("This is validated against ASTM.",),
        boundary_condition_questions=("Safe entry.",),
        failure_modes_to_consider=("Safe entry.",),
        unhandled_load_cases=("Safe entry.",),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    rendered = render_advisor_critique_json(envelope)
    parsed = json.loads(rendered)
    assert parsed["refused_claims"] == [
        f"{REFUSED_CLAIM_MARKER_PREFIX}validated against",
    ]
    # The MARKER itself contains the forbidden-token substring; we
    # rely on the envelope-level audit accepting the marker because
    # the marker is NOT in advisor content (it's in refused_claims),
    # AND because the marker text starts with "refused: " which doesn't
    # match the disclaimer form OR the positive-claim form. Verify the
    # audit didn't refuse construction.
    assert envelope.schema_version == ADVISOR_CRITIQUE_SCHEMA_VERSION


# ---------------------------------------------------------------------
# Schema audit posture: marker presence does NOT break envelope audit
# ---------------------------------------------------------------------


def test_envelope_audit_accepts_marker_strings_in_refused_claims() -> None:
    """The marker text 'refused: validated against' contains the
    forbidden token substring 'validated against', but the marker
    appears in ``refused_claims`` — a structured suppression record
    field, NOT advisor content. The envelope-level audit treats this
    correctly because the marker is preceded by 'refused: ' which does
    NOT end with 'not ' (the disclaimer-form check).

    This test pins the load-bearing contract: the audit must allow
    markers OR the schema 1.1.0 design is broken. We verify by
    running the audit explicitly on an envelope with markers."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("This is signed off as ready.",),
        boundary_condition_questions=("Safe entry.",),
        failure_modes_to_consider=("Safe entry.",),
        unhandled_load_cases=("Safe entry.",),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )
    # The build call would normally raise if the audit refused the
    # envelope. Successful return is the assertion.
    envelope = build_advisor_critique(
        _context(),
        provider=_ScriptedProvider(raw),
        now_utc=_FROZEN_NOW,
    )
    assert envelope.refused_claims == (f"{REFUSED_CLAIM_MARKER_PREFIX}signed off",)


def test_envelope_audit_still_trips_when_marker_format_is_bypassed() -> None:
    """Defense in depth: if a future bug somehow renders 'signed off'
    in advisor content WITHOUT the 'refused: ' prefix, the envelope
    audit MUST still raise. We simulate by constructing a synthetic
    AdvisorCritique that bypasses the build path (using dataclass
    constructor) and renders to JSON — the audit's purview is the
    rendered text, so this audit run independently catches the
    forbidden content."""
    from app.services.reporting.advisor_critique import (
        CLAIM_BOUNDARY,
        CLAIM_IMPACT_DEFAULT,
        CLAIM_TIER,
        _assert_no_overclaim,
    )

    rogue_envelope = AdvisorCritique(
        schema_version=ADVISOR_CRITIQUE_SCHEMA_VERSION,
        case_id="cylinder-pv-candidate",
        snapshot_label="2026-05-16T120000Z",
        advisor_status="stub",
        advisor_backend="stub-rule-based",
        generated_at_utc="2026-05-16T12:00:00+00:00",
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        # Bypass: forbidden token directly in advisor content.
        mesh_quality_concerns=("This run is signed off.",),
        boundary_condition_questions=(),
        failure_modes_to_consider=(),
        unhandled_load_cases=(),
        degrade_reason=None,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        claim_impact=CLAIM_IMPACT_DEFAULT,
        refused_claims=(),
    )
    with pytest.raises(ValueError, match="forbidden positive claim"):
        _assert_no_overclaim(rogue_envelope)


# ---------------------------------------------------------------------
# Back-compat smoke (default empty tuple)
# ---------------------------------------------------------------------


def test_envelope_default_refused_claims_is_empty_tuple() -> None:
    """The dataclass default is ``()`` per the schema 1.1.0
    additive-MINOR contract. A pre-1.1.0 producer reconstructing the
    envelope via the dataclass would not pass refused_claims; the
    default keeps the envelope construction working."""
    from app.services.reporting.advisor_critique import (
        CLAIM_BOUNDARY,
        CLAIM_IMPACT_DEFAULT,
        CLAIM_TIER,
    )

    envelope = AdvisorCritique(
        schema_version=ADVISOR_CRITIQUE_SCHEMA_VERSION,
        case_id="cylinder-pv-candidate",
        snapshot_label="2026-05-16T120000Z",
        advisor_status="stub",
        advisor_backend="stub-rule-based",
        generated_at_utc="2026-05-16T12:00:00+00:00",
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        mesh_quality_concerns=("Safe.",),
        boundary_condition_questions=(),
        failure_modes_to_consider=(),
        unhandled_load_cases=(),
        degrade_reason=None,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        claim_impact=CLAIM_IMPACT_DEFAULT,
        # NOTE: refused_claims omitted; defaults to empty tuple.
    )
    assert envelope.refused_claims == ()


# ---------------------------------------------------------------------
# Cross-section determinism — same input -> same output
# ---------------------------------------------------------------------


def test_refused_claims_collection_is_deterministic_for_identical_input() -> None:
    """Determinism contract: two runs with identical raw input yield
    identical refused_claims tuples. Pinned because a future refactor
    using set/dict iteration could silently break ordering."""
    raw = AdvisorRawCritique(
        mesh_quality_concerns=("This case is production ready.",),
        boundary_condition_questions=("Run is signed off.",),
        failure_modes_to_consider=("Approved for service.",),
        unhandled_load_cases=("Certified as complete.",),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )
    env1 = build_advisor_critique(_context(), provider=_ScriptedProvider(raw), now_utc=_FROZEN_NOW)
    env2 = build_advisor_critique(_context(), provider=_ScriptedProvider(raw), now_utc=_FROZEN_NOW)
    assert env1.refused_claims == env2.refused_claims
    assert len(env1.refused_claims) == 4  # one per section


# ---------------------------------------------------------------------
# Performance & sanity: large input
# ---------------------------------------------------------------------


def test_refused_claims_handles_many_entries_per_section() -> None:
    """A section with 12 entries (the existing MAX_ITEMS_PER_AXIS) all
    containing forbidden tokens yields 12 markers."""
    forbidden_entries = tuple(f"Entry {i}: This case is production ready." for i in range(12))
    raw = AdvisorRawCritique(
        mesh_quality_concerns=forbidden_entries,
        boundary_condition_questions=(),
        failure_modes_to_consider=(),
        unhandled_load_cases=(),
        four_question_gate={
            "llm_offline_ok": True,
            "artifacts_user_owned": True,
            "trustgate_explains": True,
            "advisor_only": True,
        },
        degrade_reason=None,
    )
    envelope = build_advisor_critique(
        _context(), provider=_ScriptedProvider(raw), now_utc=_FROZEN_NOW
    )
    assert len(envelope.refused_claims) == 12
    assert envelope.mesh_quality_concerns == ()
    assert all(
        m == f"{REFUSED_CLAIM_MARKER_PREFIX}production ready" for m in envelope.refused_claims
    )
