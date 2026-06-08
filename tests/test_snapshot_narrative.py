"""Tests for the Phase 6 C snapshot drift narrative builder.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Anti-gaming guard from the Phase 6 blueprint: every templated line
emitted by ``snapshot_narrative.build_snapshot_narrative`` MUST be
exercised by at least one positive test case in this file.
"""

from __future__ import annotations

import json

from app.services.reporting._schema_versions import (
    SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot_diff import (
    CohortSnapshotDiff,
    CompletenessDelta,
    NumericalDelta,
    ReproducibilityDelta,
)
from app.services.reporting.snapshot_narrative import (
    build_snapshot_narrative,
    render_snapshot_narrative_json,
)


def _stable_pair(value: float | None = None) -> dict:
    return {"a": value, "b": value, "delta": None, "delta_pct": None}


def _make_diff(
    *,
    cohort_added: list[str] | None = None,
    cohort_removed: list[str] | None = None,
    cohort_shared: list[str] | None = None,
    completeness_deltas: list[CompletenessDelta] | None = None,
    reproducibility_deltas: list[ReproducibilityDelta] | None = None,
    numerical_deltas: list[NumericalDelta] | None = None,
) -> CohortSnapshotDiff:
    return CohortSnapshotDiff(
        schema_version="1.1.0",
        generated_at_utc="2026-05-16T00:00:00+00:00",
        claim_tier="Tier 1 engineering candidate",
        claim_boundary=(
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        snapshot_a_label="2026-05-16T100000Z",
        snapshot_b_label="2026-05-16T200000Z",
        a_cohort_count=1,
        b_cohort_count=1,
        cohort_added=cohort_added or [],
        cohort_removed=cohort_removed or [],
        cohort_shared=cohort_shared or [],
        completeness_deltas=completeness_deltas or [],
        reproducibility_deltas=reproducibility_deltas or [],
        numerical_deltas=numerical_deltas or [],
        claim_impact=(
            "Tier 1 candidate cohort snapshot diff only; not signed "
            "validation; not benchmark agreement"
        ),
    )


def _make_numerical(
    case_id: str,
    *,
    rv_a: float | None = None,
    rv_b: float | None = None,
    eb_a: float | None = None,
    eb_b: float | None = None,
    cv_a: str | None = None,
    cv_b: str | None = None,
    pm_a: str | None = None,
    pm_b: str | None = None,
) -> NumericalDelta:
    rv_delta = None if rv_a is None or rv_b is None else round(rv_b - rv_a, 6)
    rv_pct = None if rv_a in (None, 0) or rv_b is None else round((rv_b - rv_a) / rv_a * 100.0, 6)
    eb_delta = None if eb_a is None or eb_b is None else round(eb_b - eb_a, 6)
    eb_abs = None if eb_delta is None else round(abs(eb_delta), 6)
    return NumericalDelta(
        case_id=case_id,
        residual_velocity_m_per_s={
            "a": rv_a,
            "b": rv_b,
            "delta": rv_delta,
            "delta_pct": rv_pct,
        },
        energy_balance_error_pct={
            "a": eb_a,
            "b": eb_b,
            "delta": eb_delta,
            "delta_abs_pct": eb_abs,
        },
        convergence_combined_verdict={
            "a": cv_a,
            "b": cv_b,
            "same_verdict": cv_a is not None and cv_a == cv_b,
        },
        perforation_marker={
            "a": pm_a,
            "b": pm_b,
            "same_marker": pm_a is not None and pm_a == pm_b,
        },
    )


def _make_repro(
    case_id: str,
    *,
    git_sha_changed: bool = False,
    dirty_changed: bool = False,
    a_git_dirty: bool | None = None,
    b_git_dirty: bool | None = None,
    python_version_changed: bool = False,
    a_python_version: str | None = None,
    b_python_version: str | None = None,
    script_changes: list[dict] | None = None,
) -> ReproducibilityDelta:
    return ReproducibilityDelta(
        case_id=case_id,
        a_git_sha="a" * 40 if git_sha_changed else None,
        b_git_sha="b" * 40 if git_sha_changed else None,
        git_sha_changed=git_sha_changed,
        a_git_dirty=a_git_dirty,
        b_git_dirty=b_git_dirty,
        dirty_changed=dirty_changed,
        a_python_version=a_python_version,
        b_python_version=b_python_version,
        python_version_changed=python_version_changed,
        package_version_changes=[],
        script_sha_changes=script_changes or [],
    )


# ---------------------------------------------------------------------
# envelope + payload assertions
# ---------------------------------------------------------------------


def test_narrative_stamps_schema_version() -> None:
    diff = _make_diff(cohort_added=["GS-A-candidate"])
    narrative = build_snapshot_narrative(diff)
    rendered = json.loads(render_snapshot_narrative_json(narrative))
    assert rendered["schema_version"] == SNAPSHOT_NARRATIVE_SCHEMA_VERSION
    assert rendered["snapshot_a_label"] == "2026-05-16T100000Z"
    assert rendered["snapshot_b_label"] == "2026-05-16T200000Z"


def test_narrative_preserves_tier1_disclaimer() -> None:
    diff = _make_diff(cohort_added=["GS-A-candidate"])
    rendered = render_snapshot_narrative_json(build_snapshot_narrative(diff))
    assert "Tier 1 engineering candidate" in rendered
    assert "not signed validation" in rendered
    assert "not benchmark agreement" in rendered


# ---------------------------------------------------------------------
# template firing tests (anti-gaming guard from Phase 6 blueprint:
# every template MUST have a positive test case)
# ---------------------------------------------------------------------


def test_template_cohort_added_fires() -> None:
    narrative = build_snapshot_narrative(_make_diff(cohort_added=["GS-X-candidate"]))
    line = narrative.narratives[0].lines[0]
    assert line.template_id == "cohort_added"
    assert line.severity == "info"
    assert "GS-X-candidate" in line.text


def test_template_cohort_removed_fires() -> None:
    narrative = build_snapshot_narrative(_make_diff(cohort_removed=["GS-X-candidate"]))
    line = narrative.narratives[0].lines[0]
    assert line.template_id == "cohort_removed"
    assert line.severity == "warn"


def test_template_residual_velocity_delta_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[_make_numerical("GS-A-candidate", rv_a=75.0, rv_b=80.0)],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "residual_velocity_delta" in ids


def test_template_residual_velocity_unchanged_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[_make_numerical("GS-A-candidate", rv_a=75.0, rv_b=75.0)],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "residual_velocity_unchanged" in ids


def test_template_energy_balance_improved_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[_make_numerical("GS-A-candidate", eb_a=12.0, eb_b=8.5)],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "energy_balance_improved" in ids


def test_template_energy_balance_degraded_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[_make_numerical("GS-A-candidate", eb_a=8.5, eb_b=12.0)],
    )
    narrative = build_snapshot_narrative(diff)
    lines = narrative.narratives[0].lines
    degraded = next(line for line in lines if line.template_id == "energy_balance_degraded")
    assert degraded.severity == "warn"


def test_template_energy_balance_unchanged_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[_make_numerical("GS-A-candidate", eb_a=8.5, eb_b=8.5)],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "energy_balance_unchanged" in ids


def test_template_convergence_verdict_changed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[
            _make_numerical(
                "GS-A-candidate",
                cv_a="candidate_observed_stable",
                cv_b="candidate_observed_unstable",
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    line = next(
        line
        for line in narrative.narratives[0].lines
        if line.template_id == "convergence_verdict_changed"
    )
    # regression to unstable elevates to danger
    assert line.severity == "danger"


def test_template_convergence_verdict_changed_warn_only_when_not_to_unstable() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[
            _make_numerical(
                "GS-A-candidate",
                cv_a="candidate_observed_unstable",
                cv_b="candidate_observed_stable",
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    line = next(
        line
        for line in narrative.narratives[0].lines
        if line.template_id == "convergence_verdict_changed"
    )
    assert line.severity == "warn"


def test_template_perforation_marker_changed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        numerical_deltas=[
            _make_numerical(
                "GS-A-candidate",
                pm_a="candidate_perforation",
                pm_b="no_perforation",
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "perforation_marker_changed" in ids


def test_template_completeness_improved_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        completeness_deltas=[
            CompletenessDelta(case_id="GS-A-candidate", a_score=70, b_score=85, delta=15)
        ],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "completeness_improved" in ids


def test_template_completeness_regressed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        completeness_deltas=[
            CompletenessDelta(case_id="GS-A-candidate", a_score=85, b_score=70, delta=-15)
        ],
    )
    narrative = build_snapshot_narrative(diff)
    line = next(
        line
        for line in narrative.narratives[0].lines
        if line.template_id == "completeness_regressed"
    )
    assert line.severity == "warn"


def test_template_completeness_unchanged_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        completeness_deltas=[
            CompletenessDelta(case_id="GS-A-candidate", a_score=85, b_score=85, delta=0)
        ],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "completeness_unchanged" in ids


def test_template_git_sha_changed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        reproducibility_deltas=[_make_repro("GS-A-candidate", git_sha_changed=True)],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "git_sha_changed" in ids


def test_template_git_dirty_introduced_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        reproducibility_deltas=[
            _make_repro(
                "GS-A-candidate",
                dirty_changed=True,
                a_git_dirty=False,
                b_git_dirty=True,
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    ids = [line.template_id for line in narrative.narratives[0].lines]
    assert "git_dirty_introduced" in ids


def test_template_python_version_changed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        reproducibility_deltas=[
            _make_repro(
                "GS-A-candidate",
                python_version_changed=True,
                a_python_version="3.11.15",
                b_python_version="3.11.16",
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    line = next(
        line
        for line in narrative.narratives[0].lines
        if line.template_id == "python_version_changed"
    )
    assert line.severity == "warn"


def test_template_script_sha_changed_fires() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        reproducibility_deltas=[
            _make_repro(
                "GS-A-candidate",
                script_changes=[
                    {
                        "relpath": "scripts/gen_gsa_deck.py",
                        "a_sha256": "a" * 64,
                        "b_sha256": "b" * 64,
                    }
                ],
            )
        ],
    )
    narrative = build_snapshot_narrative(diff)
    line = next(
        line for line in narrative.narratives[0].lines if line.template_id == "script_sha_changed"
    )
    assert "scripts/gen_gsa_deck.py" in line.text


def test_narrative_emits_no_lines_when_nothing_changed() -> None:
    diff = _make_diff(
        cohort_shared=["GS-A-candidate"],
        # no deltas, no reproducibility drift, no numerical changes
    )
    narrative = build_snapshot_narrative(diff)
    assert narrative.narratives[0].case_id == "GS-A-candidate"
    assert narrative.narratives[0].lines == []


def test_narrative_no_forbidden_claim_in_any_template() -> None:
    """Anti-gaming guard: every template's text must remain factual.
    We fire the widest possible set of templates and inspect the rendered
    JSON for forbidden phrases.
    """
    diff = _make_diff(
        cohort_added=["GS-X-candidate"],
        cohort_removed=["GS-Y-candidate"],
        cohort_shared=["GS-A-candidate"],
        completeness_deltas=[
            CompletenessDelta(case_id="GS-A-candidate", a_score=70, b_score=85, delta=15)
        ],
        reproducibility_deltas=[
            _make_repro(
                "GS-A-candidate",
                git_sha_changed=True,
                dirty_changed=True,
                a_git_dirty=False,
                b_git_dirty=True,
                python_version_changed=True,
                a_python_version="3.11.15",
                b_python_version="3.12.0",
                script_changes=[
                    {
                        "relpath": "scripts/gen_gsa_deck.py",
                        "a_sha256": "a" * 64,
                        "b_sha256": "b" * 64,
                    }
                ],
            )
        ],
        numerical_deltas=[
            _make_numerical(
                "GS-A-candidate",
                rv_a=75.0,
                rv_b=80.0,
                eb_a=12.0,
                eb_b=8.5,
                cv_a="candidate_observed_stable",
                cv_b="candidate_observed_unstable",
                pm_a="candidate_perforation",
                pm_b="no_perforation",
            )
        ],
    )
    rendered = render_snapshot_narrative_json(build_snapshot_narrative(diff))
    for token in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert token not in rendered.lower()


def test_narrative_groups_lines_per_case() -> None:
    """Two cases in the cohort_shared list must produce two
    CaseNarrative entries, each with its own lines."""
    diff = _make_diff(
        cohort_shared=["GS-A-candidate", "GS-B-candidate"],
        completeness_deltas=[
            CompletenessDelta(case_id="GS-A-candidate", a_score=70, b_score=85, delta=15),
            CompletenessDelta(case_id="GS-B-candidate", a_score=85, b_score=70, delta=-15),
        ],
    )
    narrative = build_snapshot_narrative(diff)
    assert [n.case_id for n in narrative.narratives] == [
        "GS-A-candidate",
        "GS-B-candidate",
    ]
    assert narrative.narratives[0].lines[0].template_id == "completeness_improved"
    assert narrative.narratives[1].lines[0].template_id == "completeness_regressed"
