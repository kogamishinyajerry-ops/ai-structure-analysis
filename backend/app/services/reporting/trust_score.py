"""Tier 1 candidate evidence trust score (FM-04a Phase 6 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Composite 0–100 number that surfaces "is this case in good shape today"
without conflating "evidence-presence" (Phase 4 A) with "drift-stability"
(Phase 5 D) with "reproducibility-cleanliness" (Phase 5 B). Each axis is
read from the same on-disk sources the live cohort endpoints already
read, then weighted into one trust_score with a transparent breakdown.

============================================
Formula (formula_version = "1.0.0")
============================================

Composite weights (sum to 100):

    COMPLETENESS_WEIGHT           = 50
    CONVERGENCE_WEIGHT            = 20
    ENERGY_AUDIT_WEIGHT           = 15
    REPRODUCIBILITY_WEIGHT        = 15

Per-axis raw subscore (each 0–100, mapped to weighted via
``weighted = raw * weight / 100``):

* completeness:
      raw = completeness_score / completeness_score_max * 100
* convergence_stability:
      both axes "candidate_observed_stable" -> 100
      one stable, one not                   -> 60
      both "candidate_observed_unstable"    -> 30
      otherwise (insufficient_data / absent) -> 0
* energy_audit_closure:
      status == "closed_aggregate" -> 100
      status == "partial_candidate" -> 60
      otherwise -> 0
* reproducibility_clean:
      starts at 100;
      -30 if git_dirty;
      -25 if git_commit_sha is None;
      -20 per "not_installed" tracked package, floor 0

Bump policy: the formula version is SEPARATE from
``TRUST_SCORE_SCHEMA_VERSION``. Changing a weight, a sub-formula, or a
threshold bumps ``TRUST_SCORE_FORMULA_VERSION`` (semver) AND requires
the closing retrospective to call out the rebalance + rationale.

============================================
Sensitivity & Rebalance Methodology (FM-04a Phase 7 D)
============================================

The constants above (``COMPLETENESS_WEIGHT``, ``CONVERGENCE_WEIGHT``,
``ENERGY_AUDIT_WEIGHT``, ``REPRODUCIBILITY_WEIGHT``, and the three
``REPRO_PENALTY_*`` constants) are an opinionated first cut, called out
in Phase 6 retrospective carry-forward §5. The pinning + sensitivity
contract is:

1. **Sum-to-100 invariant** — pinned by
   ``tests/test_trust_score.py::test_composite_weights_sum_to_100``.
   Silent rebalance trips a failing test.
2. **In-bounds invariant** — pinned by property-based tests in
   ``tests/test_phase7_trust_score_properties.py`` using
   ``Hypothesis``: regardless of the input space (any combination of
   present/absent evidence on any of the four axes), the returned
   ``trust_score`` is in ``[0, 100]`` and each ``weighted`` is in
   ``[0, weight]``. Strategies use ``derandomize=True`` or fixed seeds
   so failures are reproducible across runs (Phase 7 anti-gaming
   guard ``T: -2``).
3. **Weight-delta linearity** — pinned by sensitivity tests in
   ``tests/test_phase7_trust_score_formula_sensitivity.py``: given
   identical evidence inputs, swapping a single weight constant by a
   known delta produces exactly the corresponding score delta. This
   IS the rebalance methodology: any future weight change is
   testable in isolation by monkey-patching the constant in a
   dedicated test and asserting the expected score shift.

A rebalance therefore proceeds in four mechanical steps:

a. Author the new weights, ensuring the constants still sum to 100.
b. Bump ``TRUST_SCORE_FORMULA_VERSION`` from ``"1.0.0"`` to ``"1.1.0"``
   (or higher, by magnitude) AND amend the bump-history note in
   ``_schema_versions.py``.
c. Run the property-based tests; in-bounds invariants must still hold.
d. Add a sensitivity test that asserts the rebalance's expected effect
   on at least one canonical input case; include the rationale in the
   closing retrospective per the documented bump policy.

This is NOT a substitute for the FM-04b P8 sealed-packet trust
signal. The claim_impact string preserves the Tier 1 disclaimer trio.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_SCHEMA_VERSION,
)
from .acceptance_packet import CLAIM_BOUNDARY, DEFAULT_TIER2_BLOCKERS_REMAINING
from .case_completeness import (
    CaseCompletenessInputs,
    score_case_completeness,
)
from .reproducibility_manifest import (
    ReproducibilityManifestInputs,
    build_reproducibility_manifest,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate evidence trust score only; not signed validation; "
    "not benchmark agreement; not a substitute for the FM-04b P8 sealed "
    "trust signal. The composite axes (completeness / convergence / "
    "energy audit / reproducibility) remain evidence-presence and "
    "evidence-cleanliness signals; they do not certify physical validity."
)

# ----- weight constants (sum must equal 100) -----

COMPLETENESS_WEIGHT = 50
CONVERGENCE_WEIGHT = 20
ENERGY_AUDIT_WEIGHT = 15
REPRODUCIBILITY_WEIGHT = 15

_ALL_WEIGHTS = (
    COMPLETENESS_WEIGHT,
    CONVERGENCE_WEIGHT,
    ENERGY_AUDIT_WEIGHT,
    REPRODUCIBILITY_WEIGHT,
)

# ----- reproducibility penalty constants -----

REPRO_PENALTY_GIT_DIRTY = 30
REPRO_PENALTY_GIT_SHA_MISSING = 25
REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE = 20


@dataclass(frozen=True)
class TrustScoreBreakdownEntry:
    axis: str
    weight: int
    raw_score: int
    weighted: int
    rationale: str


@dataclass
class TrustScore:
    schema_version: str
    formula_version: str
    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    trust_score: int
    trust_score_max: int
    breakdown: list[TrustScoreBreakdownEntry]
    tier2_blockers_remaining: list[str]
    claim_impact: str


@dataclass(frozen=True)
class TrustScoreInputs:
    case_id: str
    repo_root: Path
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    ballistic_metrics_path: Path | None = None
    convergence_study_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    generator_script_path: Path | None = None
    notes_path: Path | None = None


def compute_trust_score(inputs: TrustScoreInputs) -> TrustScore:
    """Compute the Tier 1 candidate trust score for ``inputs.case_id``.

    Reads the same on-disk evidence sources as the live Phase 4 A / 5 B
    builders. Returns a TrustScore with a transparent breakdown across
    the four named axes.
    """
    assert sum(_ALL_WEIGHTS) == 100, "trust score weights must sum to 100"

    completeness_entry = _score_completeness_axis(inputs)
    convergence_entry = _score_convergence_axis(inputs.convergence_study_path)
    energy_entry = _score_energy_audit_axis(inputs.ballistic_metrics_path)
    repro_entry = _score_reproducibility_axis(
        inputs.case_id, inputs.repo_root, inputs.generator_script_path
    )

    breakdown = [completeness_entry, convergence_entry, energy_entry, repro_entry]
    trust = sum(entry.weighted for entry in breakdown)

    score = TrustScore(
        schema_version=TRUST_SCORE_SCHEMA_VERSION,
        formula_version=TRUST_SCORE_FORMULA_VERSION,
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        trust_score=trust,
        trust_score_max=100,
        breakdown=breakdown,
        tier2_blockers_remaining=list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(score)
    return score


def render_trust_score_json(score: TrustScore) -> str:
    """Return the trust score as a JSON string."""
    return json.dumps(_score_to_dict(score), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# axis scorers
# ---------------------------------------------------------------------


def _score_completeness_axis(inputs: TrustScoreInputs) -> TrustScoreBreakdownEntry:
    completeness = score_case_completeness(
        CaseCompletenessInputs(
            case_id=inputs.case_id,
            starter_deck_path=inputs.starter_deck_path,
            engine_deck_path=inputs.engine_deck_path,
            ballistic_metrics_path=inputs.ballistic_metrics_path,
            convergence_study_path=inputs.convergence_study_path,
            animation_manifest_path=inputs.animation_manifest_path,
            result_mesh_path=inputs.result_mesh_path,
            generator_script_path=inputs.generator_script_path,
            notes_path=inputs.notes_path,
        )
    )
    if completeness.score_max == 0:
        raw = 0
    else:
        raw = int(round(completeness.score / completeness.score_max * 100))
    weighted = int(round(raw * COMPLETENESS_WEIGHT / 100))
    return TrustScoreBreakdownEntry(
        axis="completeness",
        weight=COMPLETENESS_WEIGHT,
        raw_score=raw,
        weighted=weighted,
        rationale=(
            f"completeness scorecard reported {completeness.score}/"
            f"{completeness.score_max} ({raw}/100 normalized); "
            "evidence-presence signal only, NOT physical validation"
        ),
    )


def _score_convergence_axis(
    convergence_path: Path | None,
) -> TrustScoreBreakdownEntry:
    payload = _load_optional_json(convergence_path)
    if payload is None:
        return TrustScoreBreakdownEntry(
            axis="convergence_stability",
            weight=CONVERGENCE_WEIGHT,
            raw_score=0,
            weighted=0,
            rationale="convergence_study.json absent; cannot judge mesh/dt stability",
        )
    mesh_stable = _stability_label(payload.get("mesh_sweep"))
    dt_stable = _stability_label(payload.get("dt_sweep"))
    if (
        mesh_stable == "candidate_observed_stable"
        and dt_stable == "candidate_observed_stable"
    ):
        raw = 100
        rationale = "both mesh and dt sweeps reported candidate_observed_stable"
    elif (
        mesh_stable == "candidate_observed_unstable"
        and dt_stable == "candidate_observed_unstable"
    ):
        raw = 30
        rationale = "both mesh and dt sweeps reported candidate_observed_unstable"
    elif (
        "candidate_observed_stable" in (mesh_stable, dt_stable)
        and "candidate_observed_unstable" in (mesh_stable, dt_stable)
    ):
        raw = 60
        rationale = (
            "one sweep stable, one unstable — partial credit reflects "
            "discordant per-axis verdicts"
        )
    elif "candidate_observed_stable" in (mesh_stable, dt_stable):
        raw = 60
        rationale = "one sweep stable, the other inconclusive"
    else:
        raw = 0
        rationale = "convergence study present but neither axis reached a stable verdict"
    weighted = int(round(raw * CONVERGENCE_WEIGHT / 100))
    return TrustScoreBreakdownEntry(
        axis="convergence_stability",
        weight=CONVERGENCE_WEIGHT,
        raw_score=raw,
        weighted=weighted,
        rationale=rationale,
    )


def _score_energy_audit_axis(
    metrics_path: Path | None,
) -> TrustScoreBreakdownEntry:
    payload = _load_optional_json(metrics_path)
    if payload is None:
        return TrustScoreBreakdownEntry(
            axis="energy_audit_closure",
            weight=ENERGY_AUDIT_WEIGHT,
            raw_score=0,
            weighted=0,
            rationale="ballistic_metrics.json absent; cannot judge energy closure",
        )
    block = payload.get("energy_audit") or {}
    status = block.get("status")
    if status == "closed_aggregate":
        raw = 100
        rationale = "energy_audit.status == closed_aggregate"
    elif status == "partial_candidate":
        raw = 60
        rationale = "energy_audit.status == partial_candidate"
    else:
        raw = 0
        rationale = f"energy_audit.status = {status!r}; closure not demonstrated"
    weighted = int(round(raw * ENERGY_AUDIT_WEIGHT / 100))
    return TrustScoreBreakdownEntry(
        axis="energy_audit_closure",
        weight=ENERGY_AUDIT_WEIGHT,
        raw_score=raw,
        weighted=weighted,
        rationale=rationale,
    )


def _score_reproducibility_axis(
    case_id: str, repo_root: Path, generator_script_path: Path | None
) -> TrustScoreBreakdownEntry:
    manifest = build_reproducibility_manifest(
        ReproducibilityManifestInputs(
            case_id=case_id,
            repo_root=repo_root,
            generator_script_path=generator_script_path,
        )
    )
    raw = 100
    reasons: list[str] = []
    if manifest.git_dirty:
        raw -= REPRO_PENALTY_GIT_DIRTY
        reasons.append(
            f"git_dirty -> -{REPRO_PENALTY_GIT_DIRTY}"
        )
    if manifest.git_commit_sha is None:
        raw -= REPRO_PENALTY_GIT_SHA_MISSING
        reasons.append(
            f"git_commit_sha absent -> -{REPRO_PENALTY_GIT_SHA_MISSING}"
        )
    not_installed = sum(
        1 for pkg in manifest.tracked_packages if pkg.version == "not_installed"
    )
    if not_installed:
        delta = not_installed * REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE
        raw -= delta
        reasons.append(
            f"{not_installed} tracked package(s) not installed -> -{delta}"
        )
    raw = max(0, raw)
    weighted = int(round(raw * REPRODUCIBILITY_WEIGHT / 100))
    rationale = "; ".join(reasons) if reasons else "clean checkout, all tracked packages installed"
    return TrustScoreBreakdownEntry(
        axis="reproducibility_clean",
        weight=REPRODUCIBILITY_WEIGHT,
        raw_score=raw,
        weighted=weighted,
        rationale=rationale,
    )


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _stability_label(sweep_block: Any) -> str | None:
    if not isinstance(sweep_block, dict):
        return None
    value = sweep_block.get("candidate_stability")
    if isinstance(value, str):
        return value
    return None


def _load_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _entry_to_dict(entry: TrustScoreBreakdownEntry) -> dict[str, Any]:
    return {
        "axis": entry.axis,
        "weight": entry.weight,
        "raw_score": entry.raw_score,
        "weighted": entry.weighted,
        "rationale": entry.rationale,
    }


def _score_to_dict(score: TrustScore) -> dict[str, Any]:
    return {
        "schema_version": score.schema_version,
        "formula_version": score.formula_version,
        "case_id": score.case_id,
        "generated_at_utc": score.generated_at_utc,
        "claim_tier": score.claim_tier,
        "claim_boundary": score.claim_boundary,
        "trust_score": score.trust_score,
        "trust_score_max": score.trust_score_max,
        "breakdown": [_entry_to_dict(e) for e in score.breakdown],
        "tier2_blockers_remaining": score.tier2_blockers_remaining,
        "claim_impact": score.claim_impact,
    }


def _assert_no_overclaim(score: TrustScore) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_score_to_dict(score), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Trust score contains forbidden positive claim: {token!r}"
            )
