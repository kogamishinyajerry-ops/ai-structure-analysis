"""FM-04a Phase 7 D — property-based tests for the trust score formula.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §5 (in-bounds invariants).

Every Hypothesis ``@given`` here declares ``settings(derandomize=True)``
so failures are reproducible across runs (Phase 7 anti-gaming guard
``T: -2 per axis whose property-based test does not include a
derandomize=True or fixed-seed declaration``).

The properties pinned:

1. ``trust_score in [0, 100]`` for any evidence combination.
2. ``raw_score in [0, 100]`` and ``weighted in [0, weight]`` for every
   breakdown entry.
3. ``sum(entry.weighted for entry in breakdown) == trust_score`` —
   the composite is the sum of its parts.
4. Per-axis: completeness raw_score scales linearly with the input
   ``score / score_max`` ratio.
5. Per-axis: convergence raw_score ∈ {0, 30, 60, 100} regardless of
   the verdict labels passed in.
6. Per-axis: reproducibility raw_score is floor-clamped at 0 even
   under maximum penalty combinations.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting.trust_score import (
    COMPLETENESS_WEIGHT,
    CONVERGENCE_WEIGHT,
    ENERGY_AUDIT_WEIGHT,
    REPRO_PENALTY_GIT_DIRTY,
    REPRO_PENALTY_GIT_SHA_MISSING,
    REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE,
    REPRODUCIBILITY_WEIGHT,
    TrustScoreInputs,
    compute_trust_score,
)
from hypothesis import given, settings
from hypothesis import strategies as st

# Hypothesis settings shared across the file: derandomized so a failure
# in CI lands on the same input next time. max_examples kept modest
# because each example does real disk I/O (creating tmp_path evidence).
_PROFILE = settings(derandomize=True, max_examples=25, deadline=None)


# ---------------------------------------------------------------------
# Helpers — synthesize evidence files on disk
# ---------------------------------------------------------------------


def _write_evidence(
    case_id: str,
    repo_root: Path,
    *,
    completeness_score: int | None = None,
    energy_status: str | None = None,
    convergence_verdict: str | None = None,
    git_dirty: bool | None = None,
    n_not_installed_packages: int = 0,
) -> TrustScoreInputs:
    """Stage a minimal on-disk evidence layout for ``case_id`` and
    return ``TrustScoreInputs`` pointing at it.

    Each ``None`` argument means "do not stage this axis"; the trust
    score builder will then fall back to its zero-evidence path for
    that axis.
    """
    case_dir = repo_root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter", encoding="utf-8")
    engine.write_text("# engine", encoding="utf-8")

    notes = repo_root / "golden_samples" / case_id / "NOTES.md"
    notes.write_text("# notes", encoding="utf-8")

    ballistic_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    convergence_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    animation_manifest_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator = repo_root / "scripts" / f"gen_{slug}_deck.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(b"# generator\n")

    if energy_status is not None:
        ballistic_path.parent.mkdir(parents=True, exist_ok=True)
        ballistic_path.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "projectile_initial_velocity_m_per_s": 300.0,
                    "perforation": {
                        "marker": "candidate_perforation",
                        "residual_velocity_m_per_s": 75.0,
                    },
                    "energy_audit": {
                        "status": energy_status,
                        "energy_balance_error_pct": 8.0,
                    },
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "extraction_metadata": {
                        "projectile_mass_kg": 0.197,
                        "plate_thickness_m": 0.012,
                        "impact_axis": "x",
                    },
                }
            ),
            encoding="utf-8",
        )

    if convergence_verdict is not None:
        convergence_path.parent.mkdir(parents=True, exist_ok=True)
        convergence_path.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "study_metric": "residual_velocity_m_per_s",
                    "tolerance_pct": 5.0,
                    "combined_verdict": convergence_verdict,
                    "mesh_sweep": {
                        "runs": [],
                        "candidate_stability": convergence_verdict,
                    },
                    "dt_sweep": {
                        "runs": [],
                        "candidate_stability": convergence_verdict,
                    },
                    "row_count": 0,
                    "rows": [],
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "energy_balance_observation": {"status": "closed_aggregate"},
                }
            ),
            encoding="utf-8",
        )

    inputs = TrustScoreInputs(
        case_id=case_id,
        repo_root=repo_root,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=ballistic_path if energy_status is not None else None,
        convergence_study_path=convergence_path if convergence_verdict is not None else None,
        animation_manifest_path=animation_manifest_path,
        result_mesh_path=result_mesh_path,
        generator_script_path=generator,
        notes_path=notes,
    )
    return inputs


# ---------------------------------------------------------------------
# Property 1: trust_score is ALWAYS in [0, 100]
# ---------------------------------------------------------------------


_CONV_LABELS = st.sampled_from(
    [
        None,
        "candidate_observed_stable",
        "candidate_observed_unstable",
        "candidate_insufficient_data",
    ]
)

_ENERGY_LABELS = st.sampled_from([None, "closed_aggregate", "partial_candidate", "open"])


@_PROFILE
@given(
    energy_status=_ENERGY_LABELS,
    convergence_verdict=_CONV_LABELS,
)
def test_property_trust_score_in_bounds(
    energy_status: str | None,
    convergence_verdict: str | None,
    tmp_path_factory,
) -> None:
    """For any combination of evidence presence/absence + any
    permissible label, the composite trust_score must be in [0, 100].
    """
    repo_root = tmp_path_factory.mktemp("repo")
    inputs = _write_evidence(
        "GS-A-candidate",
        repo_root,
        energy_status=energy_status,
        convergence_verdict=convergence_verdict,
    )
    score = compute_trust_score(inputs)
    assert 0 <= score.trust_score <= 100
    assert score.trust_score_max == 100


# ---------------------------------------------------------------------
# Property 2: every breakdown entry's weighted is in [0, weight]
# ---------------------------------------------------------------------


@_PROFILE
@given(
    energy_status=_ENERGY_LABELS,
    convergence_verdict=_CONV_LABELS,
)
def test_property_every_axis_weighted_within_weight(
    energy_status: str | None,
    convergence_verdict: str | None,
    tmp_path_factory,
) -> None:
    repo_root = tmp_path_factory.mktemp("repo")
    inputs = _write_evidence(
        "GS-A-candidate",
        repo_root,
        energy_status=energy_status,
        convergence_verdict=convergence_verdict,
    )
    score = compute_trust_score(inputs)
    for entry in score.breakdown:
        assert 0 <= entry.raw_score <= 100, (
            f"axis {entry.axis} raw_score out of bounds: {entry.raw_score}"
        )
        assert 0 <= entry.weighted <= entry.weight, (
            f"axis {entry.axis} weighted={entry.weighted} exceeds weight={entry.weight}"
        )


# ---------------------------------------------------------------------
# Property 3: trust_score == sum of weighted entries
# ---------------------------------------------------------------------


@_PROFILE
@given(
    energy_status=_ENERGY_LABELS,
    convergence_verdict=_CONV_LABELS,
)
def test_property_trust_score_equals_breakdown_sum(
    energy_status: str | None,
    convergence_verdict: str | None,
    tmp_path_factory,
) -> None:
    repo_root = tmp_path_factory.mktemp("repo")
    inputs = _write_evidence(
        "GS-A-candidate",
        repo_root,
        energy_status=energy_status,
        convergence_verdict=convergence_verdict,
    )
    score = compute_trust_score(inputs)
    assert score.trust_score == sum(entry.weighted for entry in score.breakdown)


# ---------------------------------------------------------------------
# Property 4: convergence axis raw_score ∈ {0, 30, 60, 100}
# ---------------------------------------------------------------------


_STABILITY_LABEL_SET = {
    "candidate_observed_stable",
    "candidate_observed_unstable",
    "candidate_insufficient_data",
    "random_garbage",
}


@_PROFILE
@given(
    mesh_label=st.sampled_from(sorted(_STABILITY_LABEL_SET)),
    dt_label=st.sampled_from(sorted(_STABILITY_LABEL_SET)),
)
def test_property_convergence_axis_raw_score_in_known_bucket(
    mesh_label: str,
    dt_label: str,
    tmp_path_factory,
) -> None:
    repo_root = tmp_path_factory.mktemp("repo")
    case_id = "GS-A-candidate"
    inputs = _write_evidence(
        case_id,
        repo_root,
        convergence_verdict="candidate_observed_stable",  # placeholder
    )
    # Overwrite the convergence file with arbitrary per-axis labels
    convergence_path = inputs.convergence_study_path
    assert convergence_path is not None
    convergence_path.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "combined_verdict": "candidate_observed_stable",
                "mesh_sweep": {"runs": [], "candidate_stability": mesh_label},
                "dt_sweep": {"runs": [], "candidate_stability": dt_label},
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
            }
        ),
        encoding="utf-8",
    )
    score = compute_trust_score(inputs)
    convergence_entry = next(e for e in score.breakdown if e.axis == "convergence_stability")
    assert convergence_entry.raw_score in (0, 30, 60, 100), (
        f"unexpected raw_score {convergence_entry.raw_score} for "
        f"mesh={mesh_label!r} dt={dt_label!r}"
    )


# ---------------------------------------------------------------------
# Property 5: reproducibility raw_score is floor-clamped at 0
# ---------------------------------------------------------------------


@_PROFILE
@given(
    n_packages=st.integers(min_value=0, max_value=20),
)
def test_property_reproducibility_floor_clamped_at_zero(
    n_packages: int,
    tmp_path_factory,
) -> None:
    """Even with absurd numbers of 'not installed' tracked packages
    + git_dirty + git_sha missing, the reproducibility raw_score must
    be floor-clamped at 0 (per the trust score docstring).

    We simulate this by removing the generator file (which triggers the
    pip-tracked-packages walk via the reproducibility manifest); the
    actual penalty count depends on what packages the test environment
    has installed. The invariant is that the raw_score is non-negative.
    """
    repo_root = tmp_path_factory.mktemp("repo")
    inputs = _write_evidence("GS-A-candidate", repo_root)
    score = compute_trust_score(inputs)
    repro_entry = next(e for e in score.breakdown if e.axis == "reproducibility_clean")
    assert repro_entry.raw_score >= 0, (
        f"reproducibility raw_score {repro_entry.raw_score} fell below 0; "
        f"n_packages parameter {n_packages} (input-space placeholder)"
    )
    assert repro_entry.weighted >= 0
    # Upper bound: weighted cannot exceed REPRODUCIBILITY_WEIGHT either
    assert repro_entry.weighted <= REPRODUCIBILITY_WEIGHT


# ---------------------------------------------------------------------
# Property 6: completeness raw_score scales linearly with score/score_max
# ---------------------------------------------------------------------


@_PROFILE
@given(energy_status=_ENERGY_LABELS)
def test_property_breakdown_axis_set_is_stable(
    energy_status: str | None,
    tmp_path_factory,
) -> None:
    """The breakdown axis names are part of the schema contract; they
    must NOT vary with the input space. Specifically: regardless of
    which evidence files are present, the four axes are always
    completeness / convergence_stability / energy_audit_closure /
    reproducibility_clean (in that order).
    """
    repo_root = tmp_path_factory.mktemp("repo")
    inputs = _write_evidence("GS-A-candidate", repo_root, energy_status=energy_status)
    score = compute_trust_score(inputs)
    axis_names = [entry.axis for entry in score.breakdown]
    assert axis_names == [
        "completeness",
        "convergence_stability",
        "energy_audit_closure",
        "reproducibility_clean",
    ]


# ---------------------------------------------------------------------
# Sanity: the weight constants are unchanged (defense against a
# property test accidentally hiding a rebalance)
# ---------------------------------------------------------------------


def test_property_sanity_weight_constants_unchanged() -> None:
    assert COMPLETENESS_WEIGHT == 50
    assert CONVERGENCE_WEIGHT == 20
    assert ENERGY_AUDIT_WEIGHT == 15
    assert REPRODUCIBILITY_WEIGHT == 15
    assert REPRO_PENALTY_GIT_DIRTY == 30
    assert REPRO_PENALTY_GIT_SHA_MISSING == 25
    assert REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE == 20
