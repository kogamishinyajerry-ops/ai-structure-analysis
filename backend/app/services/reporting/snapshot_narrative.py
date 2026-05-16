"""Tier 1 candidate snapshot drift narrative (FM-04a Phase 6 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Turns a snapshot diff (Phase 5 D + 6 A) into a list of plain-English
sentences a reviewer can scan in a glance.

Every sentence is built from a *fixed template* with structured slot
values from the diff. Templates are enumerated below; there is no
free-form prose generation and no LLM call.

Templates (finite set; the audit guard from the Phase 6 blueprint
asserts each template fires under at least one positive test case):

* ``residual_velocity_delta``        — info
* ``residual_velocity_unchanged``    — info
* ``energy_balance_improved``        — info
* ``energy_balance_degraded``        — warn
* ``energy_balance_unchanged``       — info
* ``convergence_verdict_changed``    — warn  (any non-equal pair)
* ``perforation_marker_changed``     — warn
* ``script_sha_changed``             — warn
* ``python_version_changed``         — warn
* ``git_sha_changed``                — info  (commit advance is normal)
* ``git_dirty_introduced``           — warn
* ``completeness_improved``          — info
* ``completeness_regressed``         — warn
* ``completeness_unchanged``         — info
* ``cohort_added``                   — info
* ``cohort_removed``                 — warn

Severity escalation: ``info`` (numerical / expected delta), ``warn``
(something a reviewer should look at), ``danger`` (rare; only fires
today if convergence verdict regresses to ``candidate_observed_unstable``).

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``. The
audit asserts no template emits text that could be parsed as a Tier 2
positive claim (Phase 6 anti-gaming guard ``C: -3``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from ._schema_versions import SNAPSHOT_NARRATIVE_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .cohort_snapshot_diff import CohortSnapshotDiff

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate snapshot drift narrative only; not signed "
    "validation; not benchmark agreement. Each line is a templated "
    "delta description; templates are factual, not endorsements."
)

Severity = Literal["info", "warn", "danger"]


@dataclass(frozen=True)
class NarrativeLine:
    template_id: str
    severity: Severity
    text: str


@dataclass(frozen=True)
class CaseNarrative:
    case_id: str
    lines: list[NarrativeLine]


@dataclass
class SnapshotNarrative:
    schema_version: str
    snapshot_a_label: str
    snapshot_b_label: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    narratives: list[CaseNarrative]
    claim_impact: str


def build_snapshot_narrative(diff: CohortSnapshotDiff) -> SnapshotNarrative:
    """Compose templated narrative lines from a cohort snapshot diff."""
    narratives: list[CaseNarrative] = []

    # cohort membership additions / removals get their own dedicated
    # case stubs so a reviewer can see "GS-C was added" without having
    # to scan completeness deltas for evidence.
    for case_id in diff.cohort_added:
        narratives.append(
            CaseNarrative(
                case_id=case_id,
                lines=[
                    NarrativeLine(
                        template_id="cohort_added",
                        severity="info",
                        text=f"Case {case_id} added to the cohort between snapshots.",
                    )
                ],
            )
        )
    for case_id in diff.cohort_removed:
        narratives.append(
            CaseNarrative(
                case_id=case_id,
                lines=[
                    NarrativeLine(
                        template_id="cohort_removed",
                        severity="warn",
                        text=f"Case {case_id} removed from the cohort between snapshots.",
                    )
                ],
            )
        )

    # shared cases — accumulate lines from each signal type
    repro_by_case = {d.case_id: d for d in diff.reproducibility_deltas}
    numerical_by_case = {d.case_id: d for d in diff.numerical_deltas}
    completeness_by_case = {d.case_id: d for d in diff.completeness_deltas}

    for case_id in diff.cohort_shared:
        lines: list[NarrativeLine] = []
        lines.extend(_numerical_lines(numerical_by_case.get(case_id)))
        lines.extend(_completeness_lines(completeness_by_case.get(case_id)))
        lines.extend(_reproducibility_lines(repro_by_case.get(case_id)))
        narratives.append(CaseNarrative(case_id=case_id, lines=lines))

    narrative = SnapshotNarrative(
        schema_version=SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
        snapshot_a_label=diff.snapshot_a_label,
        snapshot_b_label=diff.snapshot_b_label,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        narratives=narratives,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(narrative)
    return narrative


def render_snapshot_narrative_json(narrative: SnapshotNarrative) -> str:
    """Return the narrative as a JSON string."""
    return json.dumps(_narrative_to_dict(narrative), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# template emitters
# ---------------------------------------------------------------------


def _numerical_lines(delta: Any) -> list[NarrativeLine]:
    if delta is None:
        return []
    out: list[NarrativeLine] = []

    # residual velocity
    rv = delta.residual_velocity_m_per_s
    a, b = rv.get("a"), rv.get("b")
    if a is not None and b is not None:
        if a != b:
            out.append(
                NarrativeLine(
                    template_id="residual_velocity_delta",
                    severity="info",
                    text=(
                        f"Residual velocity changed from {a:g} to {b:g} m/s "
                        f"({_format_pct(rv.get('delta_pct'))})."
                    ),
                )
            )
        else:
            out.append(
                NarrativeLine(
                    template_id="residual_velocity_unchanged",
                    severity="info",
                    text=f"Residual velocity unchanged at {a:g} m/s.",
                )
            )

    # energy balance
    eb = delta.energy_balance_error_pct
    a, b = eb.get("a"), eb.get("b")
    if a is not None and b is not None:
        if b < a:
            out.append(
                NarrativeLine(
                    template_id="energy_balance_improved",
                    severity="info",
                    text=(
                        f"Energy balance error tightened from {a:g}% to {b:g}% "
                        f"(absolute delta {eb.get('delta_abs_pct'):g}%)."
                    ),
                )
            )
        elif b > a:
            out.append(
                NarrativeLine(
                    template_id="energy_balance_degraded",
                    severity="warn",
                    text=(
                        f"Energy balance error widened from {a:g}% to {b:g}% "
                        f"(absolute delta {eb.get('delta_abs_pct'):g}%)."
                    ),
                )
            )
        else:
            out.append(
                NarrativeLine(
                    template_id="energy_balance_unchanged",
                    severity="info",
                    text=f"Energy balance error unchanged at {a:g}%.",
                )
            )

    # convergence verdict
    cv = delta.convergence_combined_verdict
    a, b = cv.get("a"), cv.get("b")
    if a is not None and b is not None and a != b:
        severity: Severity = (
            "danger" if b == "candidate_observed_unstable" else "warn"
        )
        out.append(
            NarrativeLine(
                template_id="convergence_verdict_changed",
                severity=severity,
                text=f"Convergence verdict changed from {a!r} to {b!r}.",
            )
        )

    # perforation marker
    pm = delta.perforation_marker
    a, b = pm.get("a"), pm.get("b")
    if a is not None and b is not None and a != b:
        out.append(
            NarrativeLine(
                template_id="perforation_marker_changed",
                severity="warn",
                text=f"Perforation marker changed from {a!r} to {b!r}.",
            )
        )

    return out


def _completeness_lines(delta: Any) -> list[NarrativeLine]:
    if delta is None or delta.delta is None:
        return []
    if delta.delta > 0:
        return [
            NarrativeLine(
                template_id="completeness_improved",
                severity="info",
                text=(
                    f"Completeness score lifted from {delta.a_score} to "
                    f"{delta.b_score} (+{delta.delta})."
                ),
            )
        ]
    if delta.delta < 0:
        return [
            NarrativeLine(
                template_id="completeness_regressed",
                severity="warn",
                text=(
                    f"Completeness score regressed from {delta.a_score} to "
                    f"{delta.b_score} ({delta.delta})."
                ),
            )
        ]
    return [
        NarrativeLine(
            template_id="completeness_unchanged",
            severity="info",
            text=f"Completeness score unchanged at {delta.a_score}.",
        )
    ]


def _reproducibility_lines(delta: Any) -> list[NarrativeLine]:
    if delta is None:
        return []
    out: list[NarrativeLine] = []

    if delta.git_sha_changed:
        out.append(
            NarrativeLine(
                template_id="git_sha_changed",
                severity="info",
                text=(
                    f"Git commit advanced from {_short(delta.a_git_sha)} to "
                    f"{_short(delta.b_git_sha)}."
                ),
            )
        )

    if (
        delta.dirty_changed
        and delta.a_git_dirty is False
        and delta.b_git_dirty is True
    ):
        out.append(
            NarrativeLine(
                template_id="git_dirty_introduced",
                severity="warn",
                text="Working tree went from clean to dirty between snapshots.",
            )
        )

    if delta.python_version_changed:
        out.append(
            NarrativeLine(
                template_id="python_version_changed",
                severity="warn",
                text=(
                    f"Python interpreter changed from {delta.a_python_version} "
                    f"to {delta.b_python_version}; regression risk on numerical "
                    "output."
                ),
            )
        )

    if delta.script_sha_changes:
        relpaths = ", ".join(s.get("relpath", "?") for s in delta.script_sha_changes)
        out.append(
            NarrativeLine(
                template_id="script_sha_changed",
                severity="warn",
                text=(
                    f"Generator script SHA-256 changed ({relpaths}); "
                    "regression risk."
                ),
            )
        )

    return out


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _format_pct(value: float | None) -> str:
    if value is None:
        return "delta_pct unavailable"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _short(sha: str | None) -> str:
    if sha is None:
        return "unknown"
    return sha[:7] if len(sha) >= 7 else sha


def _line_to_dict(line: NarrativeLine) -> dict[str, Any]:
    return {
        "template_id": line.template_id,
        "severity": line.severity,
        "text": line.text,
    }


def _case_narrative_to_dict(case: CaseNarrative) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "lines": [_line_to_dict(line) for line in case.lines],
    }


def _narrative_to_dict(narrative: SnapshotNarrative) -> dict[str, Any]:
    return {
        "schema_version": narrative.schema_version,
        "snapshot_a_label": narrative.snapshot_a_label,
        "snapshot_b_label": narrative.snapshot_b_label,
        "generated_at_utc": narrative.generated_at_utc,
        "claim_tier": narrative.claim_tier,
        "claim_boundary": narrative.claim_boundary,
        "narratives": [_case_narrative_to_dict(c) for c in narrative.narratives],
        "claim_impact": narrative.claim_impact,
    }


def _assert_no_overclaim(narrative: SnapshotNarrative) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_narrative_to_dict(narrative), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Snapshot narrative contains forbidden positive claim: {token!r}"
            )
