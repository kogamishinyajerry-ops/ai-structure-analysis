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
from .snapshot_narrative_catalogs import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    render_template,
)

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
    locale: str
    narratives: list[CaseNarrative]
    claim_impact: str


def build_snapshot_narrative(
    diff: CohortSnapshotDiff, locale: str = DEFAULT_LOCALE
) -> SnapshotNarrative:
    """Compose templated narrative lines from a cohort snapshot diff.

    Phase 7 B — ``locale`` selects from a hand-translated catalog
    (en-US default; zh-CN pilot). Unknown locale → ``ValueError``.
    The ``template_id`` and ``severity`` are locale-independent;
    only the rendered ``text`` varies.
    """
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(
            f"unsupported locale {locale!r}; "
            f"expected one of {SUPPORTED_LOCALES!r}"
        )
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
                        text=render_template(
                            "cohort_added", locale, {"case_id": case_id}
                        ),
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
                        text=render_template(
                            "cohort_removed", locale, {"case_id": case_id}
                        ),
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
        lines.extend(_numerical_lines(numerical_by_case.get(case_id), locale))
        lines.extend(_completeness_lines(completeness_by_case.get(case_id), locale))
        lines.extend(_reproducibility_lines(repro_by_case.get(case_id), locale))
        narratives.append(CaseNarrative(case_id=case_id, lines=lines))

    narrative = SnapshotNarrative(
        schema_version=SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
        snapshot_a_label=diff.snapshot_a_label,
        snapshot_b_label=diff.snapshot_b_label,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        locale=locale,
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


def _numerical_lines(delta: Any, locale: str) -> list[NarrativeLine]:
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
                    text=render_template(
                        "residual_velocity_delta",
                        locale,
                        {
                            "a": a,
                            "b": b,
                            "delta_pct": _format_pct(rv.get("delta_pct")),
                        },
                    ),
                )
            )
        else:
            out.append(
                NarrativeLine(
                    template_id="residual_velocity_unchanged",
                    severity="info",
                    text=render_template(
                        "residual_velocity_unchanged", locale, {"a": a}
                    ),
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
                    text=render_template(
                        "energy_balance_improved",
                        locale,
                        {
                            "a": a,
                            "b": b,
                            "delta_abs_pct": eb.get("delta_abs_pct"),
                        },
                    ),
                )
            )
        elif b > a:
            out.append(
                NarrativeLine(
                    template_id="energy_balance_degraded",
                    severity="warn",
                    text=render_template(
                        "energy_balance_degraded",
                        locale,
                        {
                            "a": a,
                            "b": b,
                            "delta_abs_pct": eb.get("delta_abs_pct"),
                        },
                    ),
                )
            )
        else:
            out.append(
                NarrativeLine(
                    template_id="energy_balance_unchanged",
                    severity="info",
                    text=render_template(
                        "energy_balance_unchanged", locale, {"a": a}
                    ),
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
                text=render_template(
                    "convergence_verdict_changed", locale, {"a": a, "b": b}
                ),
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
                text=render_template(
                    "perforation_marker_changed", locale, {"a": a, "b": b}
                ),
            )
        )

    return out


def _completeness_lines(delta: Any, locale: str) -> list[NarrativeLine]:
    if delta is None or delta.delta is None:
        return []
    if delta.delta > 0:
        return [
            NarrativeLine(
                template_id="completeness_improved",
                severity="info",
                text=render_template(
                    "completeness_improved",
                    locale,
                    {
                        "a_score": delta.a_score,
                        "b_score": delta.b_score,
                        "delta": delta.delta,
                    },
                ),
            )
        ]
    if delta.delta < 0:
        return [
            NarrativeLine(
                template_id="completeness_regressed",
                severity="warn",
                text=render_template(
                    "completeness_regressed",
                    locale,
                    {
                        "a_score": delta.a_score,
                        "b_score": delta.b_score,
                        "delta": delta.delta,
                    },
                ),
            )
        ]
    return [
        NarrativeLine(
            template_id="completeness_unchanged",
            severity="info",
            text=render_template(
                "completeness_unchanged", locale, {"a_score": delta.a_score}
            ),
        )
    ]


def _reproducibility_lines(delta: Any, locale: str) -> list[NarrativeLine]:
    if delta is None:
        return []
    out: list[NarrativeLine] = []

    if delta.git_sha_changed:
        out.append(
            NarrativeLine(
                template_id="git_sha_changed",
                severity="info",
                text=render_template(
                    "git_sha_changed",
                    locale,
                    {
                        "a_short_sha": _short(delta.a_git_sha),
                        "b_short_sha": _short(delta.b_git_sha),
                    },
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
                text=render_template("git_dirty_introduced", locale, {}),
            )
        )

    if delta.python_version_changed:
        out.append(
            NarrativeLine(
                template_id="python_version_changed",
                severity="warn",
                text=render_template(
                    "python_version_changed",
                    locale,
                    {
                        "a_python_version": delta.a_python_version,
                        "b_python_version": delta.b_python_version,
                    },
                ),
            )
        )

    if delta.script_sha_changes:
        relpaths = ", ".join(s.get("relpath", "?") for s in delta.script_sha_changes)
        out.append(
            NarrativeLine(
                template_id="script_sha_changed",
                severity="warn",
                text=render_template(
                    "script_sha_changed", locale, {"relpaths": relpaths}
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
        "locale": narrative.locale,
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
