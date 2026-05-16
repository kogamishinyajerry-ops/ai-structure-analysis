"""Tier 1 candidate evidence completeness scoring (FM-04a Phase 4 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Scores how *complete* a Tier 1 candidate case's on-disk evidence
inventory is — strictly an evidence-presence signal, NOT a validation
quality signal. Even a 100/100 score keeps every FM-04b blocker
visible in the rendered output. The score is bounded to 100 and
deterministic given the same inputs.

Rubric (sums to 100):

* Starter deck present: 15 pts
* Engine deck present: 15 pts
* `ballistic_metrics.json` present: 20 pts
* Energy audit `closed_aggregate` (vs `partial_candidate` / `unavailable`): 15 pts
  (10 pts for `partial_candidate`; 0 for `unavailable` / unknown)
* `convergence_study.json` present with `candidate_observed_stable`
  verdict: 15 pts (10 if present but `candidate_observed_unstable`;
  5 if present with any other verdict; 0 if absent)
* Animation manifest: 5 pts
* Result mesh: 5 pts
* Generator script: 5 pts
* NOTES.md: 5 pts

Forbidden wording: ``validated against``, ``benchmark agreement``,
``signed validation``, ``perforation completed``,
``bullet-through-steel complete``, ``validated physics``. The builder
asserts the rendered JSON stays clean against these positive claims;
``not <claim>`` disclaimers remain allowed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import (
    CASE_COMPLETENESS_SCHEMA_VERSION,
    COMPLETENESS_RUBRIC_VERSION,
)
from .acceptance_packet import (
    CLAIM_BOUNDARY,
    DEFAULT_TIER2_BLOCKERS_REMAINING,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate evidence-presence score only; not signed validation; "
    "not benchmark agreement; not a measure of validation quality. Even a "
    "100/100 score does NOT authorize promotion to Tier 2 — every FM-04b "
    "prerequisite remains gated."
)

# Rubric weights (sum = 100). These are the BALLISTIC rubric and remain
# the back-compat default for callers that do not pass an analysis_type
# argument; the FM-04a milestone scaffold ships with this rubric pinned.
WEIGHT_STARTER_DECK = 15
WEIGHT_ENGINE_DECK = 15
WEIGHT_BALLISTIC_METRICS = 20
WEIGHT_ENERGY_AUDIT_CLOSED = 15
WEIGHT_ENERGY_AUDIT_PARTIAL = 10
WEIGHT_CONVERGENCE_STABLE = 15
WEIGHT_CONVERGENCE_UNSTABLE = 10
WEIGHT_CONVERGENCE_OTHER = 5
WEIGHT_ANIMATION_MANIFEST = 5
WEIGHT_RESULT_MESH = 5
WEIGHT_GENERATOR_SCRIPT = 5
WEIGHT_NOTES = 5

# Phase 11 A — multi-analysis-type rubric. The tuple is the SSOT for the
# closed enum of analysis types we score. New analysis_type values get
# added here AND in ANALYSIS_TYPE_RUBRIC_WEIGHTS in lock-step; a value
# in one but not the other is a build-time inconsistency that fails the
# import-time audit `_assert_rubric_weights_consistent`.
ANALYSIS_TYPE_TUPLE: tuple[str, ...] = (
    "ballistic",
    "linear_static_pv",
    "explicit_dynamics",
    "modal",
)
"""Closed set of supported analysis types. Pinned by Python identifier
in `.planning/methodology/analysis_type_completeness_rubric.md`."""

DEFAULT_ANALYSIS_TYPE: str = "ballistic"
"""Back-compat default for legacy callers that do not pass an
analysis_type. Pinned by `test_default_analysis_type_is_ballistic`."""

# Linear-static-PV-specific rubric weights — replace ballistic-irrelevant
# axes (animation_manifest, result_mesh, notes) with PV-relevant axes
# (lame_cross_check, scl_convergence, allowable_margin).
WEIGHT_LAME_CROSS_CHECK = 10
WEIGHT_SCL_CONVERGENCE = 10
WEIGHT_ALLOWABLE_MARGIN = 5

# Phase 12 A — close Phase 11 retrospective carry-forward §1.
# These were inlined as `15` and `10` in the linear_static_pv rubric;
# named constants make a future rebalance a typed identifier rename
# rather than a magic-number chase.
WEIGHT_BALLISTIC_METRICS_PV = 15
"""linear_static_pv reweight: 'ballistic_metrics' axis carries the
PV summary block (Lamé cross-check, ASME-style SCL block, allowable
margin) under the inherited filename. Reduced from 20 (ballistic
default) to 15 to make room for the PV-specific axes that sum to 25."""
WEIGHT_CONVERGENCE_STABLE_PV = 10
"""linear_static_pv reweight: 'convergence_study' axis weight reduced
from 15 (ballistic default) to 10 because linear_static cases only
score mesh_sweep (dt_sweep is N/A — no time integration), so the axis
carries less information per point of weight than on a transient case."""

ANALYSIS_TYPE_RUBRIC_WEIGHTS: dict[str, dict[str, int]] = {
    "ballistic": {
        "starter_deck": WEIGHT_STARTER_DECK,
        "engine_deck": WEIGHT_ENGINE_DECK,
        "ballistic_metrics": WEIGHT_BALLISTIC_METRICS,
        "energy_audit": WEIGHT_ENERGY_AUDIT_CLOSED,
        "convergence_study": WEIGHT_CONVERGENCE_STABLE,
        "animation_manifest": WEIGHT_ANIMATION_MANIFEST,
        "result_mesh": WEIGHT_RESULT_MESH,
        "generator_script": WEIGHT_GENERATOR_SCRIPT,
        "notes": WEIGHT_NOTES,
    },
    "linear_static_pv": {
        # PV rubric reweights to sum to 100. The PV-specific quality
        # gates (lame_cross_check, scl_convergence, allowable_margin)
        # collectively get 25 points; this replaces the
        # animation_manifest + result_mesh + notes triplet (which
        # would have been 15 points) and pulls 10 more from a
        # ballistic_metrics weight reduction (20 -> 15) and a
        # convergence_study weight reduction (15 -> 10). The
        # convergence axis is lighter here because linear_static
        # cases have only mesh_sweep meaningful (no dt sweep).
        "starter_deck": WEIGHT_STARTER_DECK,                  # 15
        "engine_deck": WEIGHT_ENGINE_DECK,                    # 15
        "ballistic_metrics": WEIGHT_BALLISTIC_METRICS_PV,     # 15 — Phase 12 A named constant
        "energy_audit": WEIGHT_ENERGY_AUDIT_CLOSED,           # 15
        "convergence_study": WEIGHT_CONVERGENCE_STABLE_PV,    # 10 — Phase 12 A named constant
        "lame_cross_check": WEIGHT_LAME_CROSS_CHECK,          # 10
        "scl_convergence": WEIGHT_SCL_CONVERGENCE,            # 10
        "generator_script": WEIGHT_GENERATOR_SCRIPT,          # 5
        "allowable_margin": WEIGHT_ALLOWABLE_MARGIN,          # 5
    },
    "explicit_dynamics": {
        # Explicit dynamics shares the ballistic rubric (animation +
        # mesh playback + per-frame energy partition are all relevant
        # for transient analyses).
        "starter_deck": WEIGHT_STARTER_DECK,
        "engine_deck": WEIGHT_ENGINE_DECK,
        "ballistic_metrics": WEIGHT_BALLISTIC_METRICS,
        "energy_audit": WEIGHT_ENERGY_AUDIT_CLOSED,
        "convergence_study": WEIGHT_CONVERGENCE_STABLE,
        "animation_manifest": WEIGHT_ANIMATION_MANIFEST,
        "result_mesh": WEIGHT_RESULT_MESH,
        "generator_script": WEIGHT_GENERATOR_SCRIPT,
        "notes": WEIGHT_NOTES,
    },
    "modal": {
        "starter_deck": WEIGHT_STARTER_DECK,
        "engine_deck": WEIGHT_ENGINE_DECK,
        "ballistic_metrics": WEIGHT_BALLISTIC_METRICS,   # filename inheritance; holds modal participation factors
        "energy_audit": WEIGHT_ENERGY_AUDIT_CLOSED,      # modal strain-energy distribution closed-aggregate
        "convergence_study": WEIGHT_CONVERGENCE_STABLE,  # mode-count convergence
        "animation_manifest": WEIGHT_ANIMATION_MANIFEST, # mode-shape animations
        "result_mesh": WEIGHT_RESULT_MESH,
        "generator_script": WEIGHT_GENERATOR_SCRIPT,
        "notes": WEIGHT_NOTES,
    },
}
"""Per-analysis-type rubric weights. Each inner dict must sum to 100.

The keys of each inner dict name the axes scored for that analysis
type. The keys differ across types: the linear-static-PV rubric
replaces `animation_manifest` / `result_mesh` / `notes` (irrelevant
for steady-state stress analysis) with `lame_cross_check` /
`scl_convergence` / `allowable_margin` (the PV-specific quality
gates). Tuple-style values would not survive a future minor schema
bump — a dict keyed by axis name makes additions/removals explicit."""


def _assert_rubric_weights_consistent() -> None:
    """Import-time audit. Each rubric in ANALYSIS_TYPE_RUBRIC_WEIGHTS:
      - has a key matching every ANALYSIS_TYPE_TUPLE entry exactly,
      - has weights that sum to 100 (the Phase 11 anti-gaming guard
        M:-2 cannot be bypassed by silent rubric drift),
      - has at least the 5 always-present axes (starter_deck,
        engine_deck, ballistic_metrics, energy_audit, convergence_study).
    """
    if set(ANALYSIS_TYPE_RUBRIC_WEIGHTS.keys()) != set(ANALYSIS_TYPE_TUPLE):
        raise RuntimeError(
            f"ANALYSIS_TYPE_TUPLE / ANALYSIS_TYPE_RUBRIC_WEIGHTS drift; "
            f"tuple={ANALYSIS_TYPE_TUPLE!r} vs weights "
            f"keys={tuple(sorted(ANALYSIS_TYPE_RUBRIC_WEIGHTS))!r}"
        )
    required_axes = {"starter_deck", "engine_deck", "ballistic_metrics",
                     "energy_audit", "convergence_study"}
    for atype, weights in ANALYSIS_TYPE_RUBRIC_WEIGHTS.items():
        total = sum(weights.values())
        if total != 100:
            raise RuntimeError(
                f"Rubric for analysis_type={atype!r} sums to {total}, not 100"
            )
        missing_axes = required_axes - set(weights.keys())
        if missing_axes:
            raise RuntimeError(
                f"Rubric for analysis_type={atype!r} missing required axes "
                f"{sorted(missing_axes)!r}"
            )


_assert_rubric_weights_consistent()


@dataclass(frozen=True)
class CaseCompletenessInputs:
    """Paths probed for evidence presence. All optional except case_id.

    Phase 11 A — added ``analysis_type`` (default ``"ballistic"`` for
    back-compat with every existing caller). The scorer dispatches
    on this value to the matching rubric in
    ``ANALYSIS_TYPE_RUBRIC_WEIGHTS``.
    """

    case_id: str
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    ballistic_metrics_path: Path | None = None
    convergence_study_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    generator_script_path: Path | None = None
    notes_path: Path | None = None
    analysis_type: str = DEFAULT_ANALYSIS_TYPE


@dataclass(frozen=True)
class CompletenessBreakdownEntry:
    """One rubric line in the score breakdown."""

    label: str
    points_awarded: int
    points_max: int
    evidence_status: str  # e.g. "present", "absent", "closed_aggregate"
    notes: str | None = None


@dataclass(frozen=True)
class CaseCompletenessScore:
    """Tier 1 evidence-presence score for one candidate case.

    Phase 11 A — added ``analysis_type``. Defaults to ``"ballistic"``
    so a legacy de-serialization of a 1.0.0 payload (which had no
    ``analysis_type`` envelope key) materializes as the ballistic
    rubric, preserving back-compat.
    """

    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    score: int
    score_max: int
    breakdown: list[CompletenessBreakdownEntry]
    missing_evidence: list[str]
    tier2_blockers_remaining: list[str]
    claim_impact: str
    analysis_type: str = DEFAULT_ANALYSIS_TYPE


def score_case_completeness(inputs: CaseCompletenessInputs) -> CaseCompletenessScore:
    """Score one case's evidence completeness against the rubric for
    its declared ``analysis_type``.

    Phase 11 A — multi-analysis-type dispatch. Unknown analysis_type
    raises ValueError; the closed set is ``ANALYSIS_TYPE_TUPLE``.
    """
    if inputs.analysis_type not in ANALYSIS_TYPE_TUPLE:
        raise ValueError(
            f"analysis_type={inputs.analysis_type!r} is not in the supported "
            f"set {ANALYSIS_TYPE_TUPLE!r}"
        )

    weights = ANALYSIS_TYPE_RUBRIC_WEIGHTS[inputs.analysis_type]
    breakdown: list[CompletenessBreakdownEntry] = []
    missing: list[str] = []

    # Universal axes (present in every rubric).
    breakdown.append(
        _score_simple_presence(
            "starter_deck", inputs.starter_deck_path, weights["starter_deck"], missing
        )
    )
    breakdown.append(
        _score_simple_presence(
            "engine_deck", inputs.engine_deck_path, weights["engine_deck"], missing
        )
    )
    metrics_entry, audit_entry = _score_ballistic_metrics_with_weights(
        inputs.ballistic_metrics_path, missing,
        metrics_weight=weights["ballistic_metrics"],
        energy_audit_weight=weights["energy_audit"],
    )
    breakdown.append(metrics_entry)
    breakdown.append(audit_entry)
    breakdown.append(
        _score_convergence_study_with_weights(
            inputs.convergence_study_path, missing,
            stable_weight=weights["convergence_study"],
        )
    )
    breakdown.append(
        _score_simple_presence(
            "generator_script", inputs.generator_script_path,
            weights["generator_script"], missing
        )
    )

    # Analysis-type-specific axes — dispatched per rubric key set.
    if inputs.analysis_type == "linear_static_pv":
        # PV-specific axes read from inside ballistic_metrics.json
        # under a `pv_summary` block.
        pv_lame, pv_scl, pv_margin = _score_pv_specific_axes(
            inputs.ballistic_metrics_path, missing,
            lame_weight=weights["lame_cross_check"],
            scl_weight=weights["scl_convergence"],
            margin_weight=weights["allowable_margin"],
        )
        breakdown.append(pv_lame)
        breakdown.append(pv_scl)
        breakdown.append(pv_margin)
    else:
        # ballistic / explicit_dynamics / modal — keep
        # animation_manifest + result_mesh + notes.
        breakdown.append(
            _score_simple_presence(
                "animation_manifest", inputs.animation_manifest_path,
                weights["animation_manifest"], missing
            )
        )
        breakdown.append(
            _score_simple_presence(
                "result_mesh", inputs.result_mesh_path,
                weights["result_mesh"], missing
            )
        )
        breakdown.append(
            _score_simple_presence(
                "notes", inputs.notes_path, weights["notes"], missing
            )
        )

    total = sum(entry.points_awarded for entry in breakdown)
    score = CaseCompletenessScore(
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        score=total,
        score_max=100,
        breakdown=breakdown,
        missing_evidence=missing,
        tier2_blockers_remaining=list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        claim_impact=CLAIM_IMPACT_DEFAULT,
        analysis_type=inputs.analysis_type,
    )
    _assert_no_overclaim(score)
    return score


def render_case_completeness_json(score: CaseCompletenessScore) -> str:
    """Return the completeness score as a JSON string."""
    return json.dumps(_score_to_dict(score), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _score_simple_presence(
    label: str, path: Path | None, weight: int, missing: list[str]
) -> CompletenessBreakdownEntry:
    if path is not None and path.is_file():
        return CompletenessBreakdownEntry(
            label=label,
            points_awarded=weight,
            points_max=weight,
            evidence_status="present",
        )
    missing.append(label)
    return CompletenessBreakdownEntry(
        label=label,
        points_awarded=0,
        points_max=weight,
        evidence_status="absent",
    )


def _score_ballistic_metrics_with_weights(
    metrics_path: Path | None,
    missing: list[str],
    *,
    metrics_weight: int,
    energy_audit_weight: int,
) -> tuple[CompletenessBreakdownEntry, CompletenessBreakdownEntry]:
    """Phase 11 A — weight-parameterized version of the metrics + energy
    audit scorer. Internal helper to the multi-analysis-type rubric."""
    # Compute partial-credit floor proportional to the type's weight.
    # The closed_aggregate award uses the full weight; partial_candidate
    # gets 2/3 of full (matching the historical 10/15 -> 0.667 ratio).
    partial_weight = int(round(energy_audit_weight * (
        WEIGHT_ENERGY_AUDIT_PARTIAL / WEIGHT_ENERGY_AUDIT_CLOSED
    )))
    if metrics_path is None or not metrics_path.is_file():
        missing.append("ballistic_metrics")
        missing.append("energy_audit")
        return (
            CompletenessBreakdownEntry(
                label="ballistic_metrics",
                points_awarded=0,
                points_max=metrics_weight,
                evidence_status="absent",
            ),
            CompletenessBreakdownEntry(
                label="energy_audit",
                points_awarded=0,
                points_max=energy_audit_weight,
                evidence_status="absent",
            ),
        )

    try:
        raw = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        missing.append("ballistic_metrics")
        missing.append("energy_audit")
        return (
            CompletenessBreakdownEntry(
                label="ballistic_metrics",
                points_awarded=0,
                points_max=metrics_weight,
                evidence_status="unreadable",
            ),
            CompletenessBreakdownEntry(
                label="energy_audit",
                points_awarded=0,
                points_max=energy_audit_weight,
                evidence_status="unreadable",
            ),
        )

    metrics_entry = CompletenessBreakdownEntry(
        label="ballistic_metrics",
        points_awarded=metrics_weight,
        points_max=metrics_weight,
        evidence_status="present",
    )
    audit = raw.get("energy_audit") or raw.get("partial_energy_audit") or {}
    audit_status = audit.get("status", "unavailable")
    if audit_status == "closed_aggregate":
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=energy_audit_weight,
            points_max=energy_audit_weight,
            evidence_status="closed_aggregate",
        )
    elif audit_status == "partial_candidate":
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=partial_weight,
            points_max=energy_audit_weight,
            evidence_status="partial_candidate",
            notes="KE-only audit; per-term split blocked on /TH/PART cards.",
        )
        missing.append("energy_audit_closed_aggregate")
    else:
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=0,
            points_max=energy_audit_weight,
            evidence_status=audit_status or "unavailable",
        )
        missing.append("energy_audit")
    return metrics_entry, audit_entry


def _score_convergence_study_with_weights(
    convergence_path: Path | None,
    missing: list[str],
    *,
    stable_weight: int,
) -> CompletenessBreakdownEntry:
    """Phase 11 A — weight-parameterized version of the convergence
    study scorer. Partial verdicts get 2/3 and 1/3 of full, matching
    the historical 10/15 and 5/15 ratios."""
    unstable_weight = int(round(stable_weight * (
        WEIGHT_CONVERGENCE_UNSTABLE / WEIGHT_CONVERGENCE_STABLE
    )))
    other_weight = int(round(stable_weight * (
        WEIGHT_CONVERGENCE_OTHER / WEIGHT_CONVERGENCE_STABLE
    )))
    if convergence_path is None or not convergence_path.is_file():
        missing.append("convergence_study")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=0,
            points_max=stable_weight,
            evidence_status="absent",
        )
    try:
        raw = json.loads(convergence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        missing.append("convergence_study")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=0,
            points_max=stable_weight,
            evidence_status="unreadable",
        )
    verdict = raw.get("combined_verdict", "insufficient_data")
    # Phase 11 A — also accept convergence_combined_verdict alias.
    if verdict == "insufficient_data":
        verdict = raw.get("convergence_combined_verdict", "insufficient_data")
    if verdict == "candidate_observed_stable":
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=stable_weight,
            points_max=stable_weight,
            evidence_status=verdict,
        )
    if verdict == "candidate_observed_unstable":
        missing.append("convergence_study_stable")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=unstable_weight,
            points_max=stable_weight,
            evidence_status=verdict,
            notes="sweep crosses tolerance; refine grid before reporting.",
        )
    missing.append("convergence_study_verdict")
    return CompletenessBreakdownEntry(
        label="convergence_study",
        points_awarded=other_weight,
        points_max=stable_weight,
        evidence_status=verdict,
    )


def _score_pv_specific_axes(
    metrics_path: Path | None,
    missing: list[str],
    *,
    lame_weight: int,
    scl_weight: int,
    margin_weight: int,
) -> tuple[CompletenessBreakdownEntry, CompletenessBreakdownEntry, CompletenessBreakdownEntry]:
    """Phase 11 A — score the three linear-static-PV-specific axes that
    replace the ballistic animation_manifest / result_mesh / notes
    triplet:

      - ``lame_cross_check``: present + max relative error <=5% on every
        component (σ_r / σ_θ / σ_z / vM) -> full credit; present but
        any component >5% -> half credit; absent -> 0.
      - ``scl_convergence``: present + max relative error on σ_t / σ_z
        / vM all <=2% -> full credit; <=5% -> half credit; >5% or
        absent -> 0.
      - ``allowable_margin``: P_m / S_m ratio present and <1.0 -> full
        credit; ratio >=1.0 -> 0 (margin failure); absent -> 0.
    """
    if metrics_path is None or not metrics_path.is_file():
        missing.append("lame_cross_check")
        missing.append("scl_convergence")
        missing.append("allowable_margin")
        return (
            CompletenessBreakdownEntry(
                label="lame_cross_check",
                points_awarded=0,
                points_max=lame_weight,
                evidence_status="absent",
            ),
            CompletenessBreakdownEntry(
                label="scl_convergence",
                points_awarded=0,
                points_max=scl_weight,
                evidence_status="absent",
            ),
            CompletenessBreakdownEntry(
                label="allowable_margin",
                points_awarded=0,
                points_max=margin_weight,
                evidence_status="absent",
            ),
        )

    try:
        raw = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        missing.append("lame_cross_check")
        missing.append("scl_convergence")
        missing.append("allowable_margin")
        return (
            CompletenessBreakdownEntry(
                label="lame_cross_check",
                points_awarded=0,
                points_max=lame_weight,
                evidence_status="unreadable",
            ),
            CompletenessBreakdownEntry(
                label="scl_convergence",
                points_awarded=0,
                points_max=scl_weight,
                evidence_status="unreadable",
            ),
            CompletenessBreakdownEntry(
                label="allowable_margin",
                points_awarded=0,
                points_max=margin_weight,
                evidence_status="unreadable",
            ),
        )

    pv = raw.get("pv_summary") or {}
    conv = pv.get("convergence_vs_lame") or {}
    asme = pv.get("asme_section_5_5") or {}

    # Lame cross-check axis.
    if not conv:
        missing.append("lame_cross_check")
        lame_entry = CompletenessBreakdownEntry(
            label="lame_cross_check",
            points_awarded=0,
            points_max=lame_weight,
            evidence_status="absent",
        )
    else:
        max_err_r = float(conv.get("max_rel_err_sigma_r_pct", 100.0))
        max_err_t = float(conv.get("max_rel_err_sigma_t_pct", 100.0))
        max_err_z = float(conv.get("max_rel_err_sigma_z_pct", 100.0))
        max_err_vm = float(conv.get("max_rel_err_von_mises_pct", 100.0))
        worst = max(max_err_r, max_err_t, max_err_z, max_err_vm)
        if worst <= 5.0:
            lame_entry = CompletenessBreakdownEntry(
                label="lame_cross_check",
                points_awarded=lame_weight,
                points_max=lame_weight,
                evidence_status="within_engineering_tolerance",
                notes=f"worst |rel err| <= {worst:.2f}% over r, t, z, vM",
            )
        else:
            missing.append("lame_cross_check_tight")
            lame_entry = CompletenessBreakdownEntry(
                label="lame_cross_check",
                points_awarded=lame_weight // 2,
                points_max=lame_weight,
                evidence_status="exceeds_engineering_tolerance",
                notes=f"worst |rel err| = {worst:.2f}% > 5% engineering bound",
            )

    # SCL convergence axis (tighter — looks at σ_t / σ_z / vM only).
    if not conv:
        missing.append("scl_convergence")
        scl_entry = CompletenessBreakdownEntry(
            label="scl_convergence",
            points_awarded=0,
            points_max=scl_weight,
            evidence_status="absent",
        )
    else:
        max_err_t = float(conv.get("max_rel_err_sigma_t_pct", 100.0))
        max_err_z = float(conv.get("max_rel_err_sigma_z_pct", 100.0))
        max_err_vm = float(conv.get("max_rel_err_von_mises_pct", 100.0))
        worst_load_bearing = max(max_err_t, max_err_z, max_err_vm)
        if worst_load_bearing <= 2.0:
            scl_entry = CompletenessBreakdownEntry(
                label="scl_convergence",
                points_awarded=scl_weight,
                points_max=scl_weight,
                evidence_status="converged_tight",
                notes=f"worst σ_t/σ_z/vM rel err <= {worst_load_bearing:.2f}%",
            )
        elif worst_load_bearing <= 5.0:
            missing.append("scl_convergence_tight")
            scl_entry = CompletenessBreakdownEntry(
                label="scl_convergence",
                points_awarded=scl_weight // 2,
                points_max=scl_weight,
                evidence_status="converged_engineering",
                notes=f"worst σ_t/σ_z/vM rel err <= {worst_load_bearing:.2f}%",
            )
        else:
            missing.append("scl_convergence")
            scl_entry = CompletenessBreakdownEntry(
                label="scl_convergence",
                points_awarded=0,
                points_max=scl_weight,
                evidence_status="not_converged",
                notes=f"worst σ_t/σ_z/vM rel err = {worst_load_bearing:.2f}% > 5%",
            )

    # Allowable margin axis.
    if not asme or "ratio_P_m_over_S_m" not in asme:
        missing.append("allowable_margin")
        margin_entry = CompletenessBreakdownEntry(
            label="allowable_margin",
            points_awarded=0,
            points_max=margin_weight,
            evidence_status="absent",
        )
    else:
        ratio = float(asme["ratio_P_m_over_S_m"])
        if ratio < 1.0:
            margin_entry = CompletenessBreakdownEntry(
                label="allowable_margin",
                points_awarded=margin_weight,
                points_max=margin_weight,
                evidence_status="margin_clear",
                notes=f"P_m / S_m = {ratio:.3f} < 1.0",
            )
        else:
            missing.append("allowable_margin")
            margin_entry = CompletenessBreakdownEntry(
                label="allowable_margin",
                points_awarded=0,
                points_max=margin_weight,
                evidence_status="margin_failure",
                notes=f"P_m / S_m = {ratio:.3f} >= 1.0",
            )

    return lame_entry, scl_entry, margin_entry


def _entry_to_dict(entry: CompletenessBreakdownEntry) -> dict[str, Any]:
    out: dict[str, Any] = {
        "label": entry.label,
        "points_awarded": entry.points_awarded,
        "points_max": entry.points_max,
        "evidence_status": entry.evidence_status,
    }
    if entry.notes is not None:
        out["notes"] = entry.notes
    return out


def _score_to_dict(score: CaseCompletenessScore) -> dict[str, Any]:
    return {
        "schema_version": CASE_COMPLETENESS_SCHEMA_VERSION,
        "rubric_version": COMPLETENESS_RUBRIC_VERSION,
        "case_id": score.case_id,
        "generated_at_utc": score.generated_at_utc,
        "claim_tier": score.claim_tier,
        "claim_boundary": score.claim_boundary,
        "analysis_type": score.analysis_type,
        "score": score.score,
        "score_max": score.score_max,
        "breakdown": [_entry_to_dict(entry) for entry in score.breakdown],
        "missing_evidence": score.missing_evidence,
        "tier2_blockers_remaining": score.tier2_blockers_remaining,
        "claim_impact": score.claim_impact,
    }


def _assert_no_overclaim(score: CaseCompletenessScore) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_score_to_dict(score), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Completeness score contains forbidden claim: {token!r}")
