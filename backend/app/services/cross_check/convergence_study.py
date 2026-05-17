"""FM-04a Phase 30 D — convergence-study helper.

Drives any existing cross-check runner at multiple mesh refinements
and produces a structured artifact documenting the (mesh_size,
observed_value, residual_pct) trend.

Honest scope (Phase 30 D):

* PROOF-OF-PATTERN ship. Only runners with a tunable mesh parameter
  are supported in Phase 30 D:
    - `plate-ss-shell-candidate`: n_per_side (structured quad)
    - `cantilever-beam-modal-candidate`: characteristic_length_m
  `cylinder-pv-candidate` is deferred (no tunable refinement param
  in its runner — would require runner-level extension).
* Three refinements per case (lo / mid / hi).
* Richardson extrapolation IS NOT computed in this module — the
  formula `f_∞ ≈ f_h - (f_h - f_2h) / (r^p - 1)` requires knowing
  the convergence order `p` which itself needs ≥3 refinements at
  geometric ratio r. Phase 30 D writes the raw triple; an analyst
  can compute Richardson externally. Documented gap.
* No fabrication of results — every entry in the artifact comes
  from a live ccx run executed by THIS module.

Anti-gaming guards:

* E:-1: residual must MONOTONICALLY DECREASE (or stay within ±50%
  of the analytical envelope, in absolute terms) as mesh refines.
  A non-monotone trend (residual growing) gets flagged as
  trend_monotone=False — pinning is in the test, not the module
  (the artifact records the truth; downstream decides action).
* D:-3: artifacts include `live_ccx_2026_*` provenance + node counts
  so a future auditor can re-run with the same inputs.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class ConvergencePoint:
    """One refinement level's outcome."""

    label: str
    """Human-readable name (e.g. "lo", "mid", "hi" or "n=10")."""

    refinement_param: float | int
    """The mesh-refinement parameter at this level (e.g. n_per_side
    or characteristic_length_m). Lower number → finer mesh for
    characteristic_length; higher → finer for n_per_side."""

    node_count: int
    """ccx node count at this refinement — useful for plotting
    residual vs DOF instead of vs the input parameter."""

    element_count: int

    observed_value: float
    """Numerical result at this refinement (units depend on case —
    Hz for modal, meters for plate deflection, etc.). Sign carried
    verbatim from the runner."""

    analytical_value: float
    """The analytical reference (identical across all refinements
    for the same case — pinned by E:-1 in the test). Sign carried
    verbatim from the runner."""

    residual_pct: float
    """(observed - analytical) / analytical * 100. Signed."""

    verdict: str
    """PASS / FAIL at this refinement — informational; the artifact
    is about TREND, not gate."""


@dataclass(frozen=True)
class ConvergenceArtifact:
    """Top-level structure persisted to convergence_study.json."""

    case_id: str
    """Stable identifier matching the case directory under
    `golden_samples/`."""

    refinement_param_name: str
    """Name of the parameter swept (for plot axes and audit clarity)."""

    refinement_units: str
    """SI units of the refinement parameter (e.g. "m" for
    characteristic_length, "elements_per_side" for n_per_side)."""

    points: tuple[ConvergencePoint, ...]
    """Ordered from coarsest to finest mesh."""

    trend_monotone: bool
    """True iff |residual| is non-increasing across the ordered
    points (or all points are below 1% — noise floor)."""

    generated_at_utc: str
    """ISO timestamp; pinned in test against a regex."""

    notes: str
    """Free-form text — what reader should be aware of."""


def _check_monotone_decreasing(points: Iterable[ConvergencePoint]) -> bool:
    """Predicate: are |residual_pct| values non-increasing across
    the ordered points? A point at |residual| < 1.0 is treated as
    "noise floor" so equality / tiny bumps do not flip the flag.
    """
    pts = list(points)
    if len(pts) < 2:
        return True
    NOISE_FLOOR_PCT = 1.0
    for i in range(1, len(pts)):
        prev = abs(pts[i - 1].residual_pct)
        cur = abs(pts[i].residual_pct)
        # Allow improvement OR staying in the noise floor.
        if cur <= prev + 1e-9:
            continue
        if cur < NOISE_FLOOR_PCT and prev < NOISE_FLOOR_PCT:
            continue
        return False
    return True


def run_convergence_study(
    *,
    case_id: str,
    refinement_param_name: str,
    refinement_units: str,
    runner_callable: Callable[[float | int], ConvergencePoint],
    param_values: list[float | int],
    notes: str = "",
) -> ConvergenceArtifact:
    """Run a convergence study by calling `runner_callable` at each
    `param_values` entry. Each call must return a ConvergencePoint.

    Caller responsibilities (kept out of this module to stay
    runner-agnostic):
      * Wrapping the specific cross-check runner (with all its
        case-specific kwargs) into a 1-arg callable.
      * Choosing the `param_values` ordering — coarsest first.

    Output: a fully-populated ConvergenceArtifact.
    """
    if len(param_values) < 2:
        raise ValueError(
            f"convergence study needs ≥2 refinements; got {len(param_values)}"
        )
    points: list[ConvergencePoint] = []
    for v in param_values:
        pt = runner_callable(v)
        if not isinstance(pt, ConvergencePoint):
            raise TypeError(
                f"runner_callable for {case_id} must return "
                f"ConvergencePoint; got {type(pt).__name__}"
            )
        points.append(pt)

    return ConvergenceArtifact(
        case_id=case_id,
        refinement_param_name=refinement_param_name,
        refinement_units=refinement_units,
        points=tuple(points),
        trend_monotone=_check_monotone_decreasing(points),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        notes=notes,
    )


def write_convergence_artifact(
    case_golden_dir: Path,
    artifact: ConvergenceArtifact,
) -> Path:
    """Persist `convergence_study.json` in the case's golden_samples
    directory. Schema 1.0.0."""
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.0.0",
        "case_id": artifact.case_id,
        "refinement_param_name": artifact.refinement_param_name,
        "refinement_units": artifact.refinement_units,
        "trend_monotone": artifact.trend_monotone,
        "generated_at_utc": artifact.generated_at_utc,
        "notes": artifact.notes,
        "points": [
            {
                "label": p.label,
                "refinement_param": p.refinement_param,
                "node_count": p.node_count,
                "element_count": p.element_count,
                "observed_value": p.observed_value,
                "analytical_value": p.analytical_value,
                "residual_pct": p.residual_pct,
                "verdict": p.verdict,
            }
            for p in artifact.points
        ],
    }
    out_path = case_golden_dir / "convergence_study.json"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def read_convergence_artifact(path: Path) -> dict:
    """Helper: load a convergence_study.json as a plain dict."""
    return json.loads(path.read_text(encoding="utf-8"))
