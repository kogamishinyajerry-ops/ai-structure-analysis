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
* No fabrication of results — every entry in the artifact comes
  from a live ccx run executed by THIS module.

Phase 31 C addendum — Richardson extrapolation:

* Adds `richardson_extrapolate(h_sizes, observed_values)` (pure
  post-processing of the 3-tuple — no live ccx re-run required).
* Adds `compute_richardson_from_artifact(artifact, h_direction)`
  helper that derives h-sizes from refinement_param + a known
  proportionality direction (CLAUDE on caller).
* Schema bump 1.0.0 → 1.1.0: optional top-level `richardson` field.
* The previous "Phase 30 D documented gap" (Richardson deferred) is
  closed in Phase 31 C as the honest pivot from the cylinder-pv
  runner BC-redesign that the Phase 31 blueprint originally scoped.
  cylinder-pv-candidate remains the same deferral target — its
  runner BCs are designed for a SINGLE-element wall coupon
  (Saint-Venant statically-determinate); extending to a refinable
  mesh requires non-trivial BC redesign and is left for a future
  phase.

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
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Literal


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
class RichardsonEstimate:
    """Phase 31 C Richardson extrapolation outcome for a 3-point
    convergence triple.

    Given three observed values f_1, f_2, f_3 at decreasing mesh sizes
    h_1 > h_2 > h_3 with refinement ratio r_ij = h_i / h_{i+1}, the
    observed order of accuracy p and asymptotic limit f_∞ satisfy
    (when the ratio is constant, r_12 = r_23 = r):

        p = log((f_1 - f_2) / (f_2 - f_3)) / log(r)
        f_∞ = f_3 + (f_3 - f_2) / (r ** p - 1)

    When the ratio is non-constant (cantilever-modal cl=12/8/5 mm
    sweep, where r_12 = 1.5 and r_23 = 1.6 differ by ~7%) the
    generalized form uses r_23 as the final-step ratio and flags
    `refinement_ratio_constant=False` so a downstream auditor knows
    to treat the p estimate with care.

    `extrapolated_value` is None if the triple is non-monotone
    (sign(f_1 - f_2) != sign(f_2 - f_3) or division-by-zero) — the
    estimator does NOT fabricate a value to keep the field
    populated.
    """

    extrapolated_value: float | None
    """f_∞ — best estimate of the value at zero mesh size. None
    iff Richardson cannot be applied (non-monotone triple, etc.)."""

    observed_order_p: float | None
    """Estimated convergence order p. None when extrapolation fails."""

    refinement_ratio_r: float
    """Refinement ratio used in the extrapolation. For a constant-
    ratio sweep this is the single r; for non-constant it is the
    final-step ratio r_23."""

    refinement_ratio_constant: bool
    """True iff r_12 and r_23 agree within 5%. When False, the
    `notes` field flags the caveat."""

    extrapolated_residual_pct: float | None
    """Signed residual of f_∞ against the analytical reference, in
    percent. None iff f_∞ is None or analytical is zero."""

    notes: str
    """Free-form text — what reader should be aware of (e.g. the
    non-constant-ratio caveat, or why extrapolation failed)."""


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

    richardson: RichardsonEstimate | None = None
    """Phase 31 C: Richardson extrapolation outcome computed
    post-hoc from `points`. None for legacy schema 1.0.0 artifacts
    or when Richardson cannot be applied (need ≥3 points)."""


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


HDirection = Literal["param_is_h", "param_inverse_to_h"]
"""Phase 31 C: caller declares how `refinement_param` maps to the
physical mesh size h:

* `"param_is_h"`: param IS the mesh size (e.g. characteristic_length_m).
  Smaller param → finer mesh. h_size_i = param_i.
* `"param_inverse_to_h"`: param is 1/h-like (e.g. n_per_side).
  Larger param → finer mesh. h_size_i = 1 / param_i (or any
  inversely-proportional units — only ratios matter for Richardson).
"""

_RATIO_CONSTANCY_TOLERANCE = 0.05
"""5% tolerance for declaring r_12 ≈ r_23 a constant refinement
ratio. Above this, the estimator switches to the generalized form
and sets refinement_ratio_constant=False."""


def richardson_extrapolate(
    h_sizes: list[float],
    observed_values: list[float],
    analytical_value: float | None = None,
) -> RichardsonEstimate:
    """Phase 31 C 3-point Richardson extrapolation.

    Args:
        h_sizes: Physical mesh sizes ordered coarsest-to-finest
            (strictly decreasing positives). Units cancel — only
            the ratios r_12 = h_1/h_2 and r_23 = h_2/h_3 enter the
            formula.
        observed_values: Observed scalar at each h, in the SAME
            order as `h_sizes`.
        analytical_value: Optional. When provided, the returned
            `extrapolated_residual_pct` is signed
            (f_∞ - analytical) / analytical * 100.

    Returns:
        RichardsonEstimate. When the triple is non-monotone or has a
        zero denominator the estimator returns `extrapolated_value`
        = None and explains in `notes`. NO FABRICATION.

    Raises:
        ValueError on wrong-length input or non-decreasing h_sizes.
    """
    if len(h_sizes) != 3 or len(observed_values) != 3:
        raise ValueError(
            f"richardson_extrapolate requires exactly 3 points; got "
            f"h={len(h_sizes)} obs={len(observed_values)}"
        )
    h1, h2, h3 = h_sizes
    if not (h1 > h2 > h3 > 0):
        raise ValueError(
            f"h_sizes must be strictly decreasing positives "
            f"(coarsest-to-finest); got {h_sizes!r}"
        )
    f1, f2, f3 = observed_values

    r12 = h1 / h2
    r23 = h2 / h3
    ratio_constant = (
        abs(r12 - r23) / max(r12, r23) < _RATIO_CONSTANCY_TOLERANCE
    )
    # When constant: use the canonical r (avg). When non-constant:
    # use r_23 as the "final-step" ratio for the f_∞ formula.
    r = (r12 + r23) / 2.0 if ratio_constant else r23

    diff_12 = f1 - f2
    diff_23 = f2 - f3

    fail_notes: list[str] = []
    if not ratio_constant:
        fail_notes.append(
            f"Refinement ratio non-constant: r_12={r12:.4f}, "
            f"r_23={r23:.4f}. Generalized Richardson applied with "
            f"r=r_23; treat p estimate with caution."
        )

    if diff_23 == 0.0:
        fail_notes.insert(
            0,
            "Richardson failed: f_2 == f_3 (noise floor reached or "
            "no further convergence detectable).",
        )
        return RichardsonEstimate(
            extrapolated_value=None,
            observed_order_p=None,
            refinement_ratio_r=r,
            refinement_ratio_constant=ratio_constant,
            extrapolated_residual_pct=None,
            notes=" ".join(fail_notes),
        )

    ratio = diff_12 / diff_23
    if ratio <= 0.0:
        fail_notes.insert(
            0,
            f"Richardson failed: (f_1-f_2)/(f_2-f_3) = {ratio:.4f} "
            f"≤ 0 (convergence reverses sign — no asymptotic order).",
        )
        return RichardsonEstimate(
            extrapolated_value=None,
            observed_order_p=None,
            refinement_ratio_r=r,
            refinement_ratio_constant=ratio_constant,
            extrapolated_residual_pct=None,
            notes=" ".join(fail_notes),
        )

    p = math.log(ratio) / math.log(r)
    f_inf = f3 + (f3 - f2) / (r ** p - 1.0)

    residual_pct: float | None = None
    if analytical_value is not None and analytical_value != 0.0:
        residual_pct = (f_inf - analytical_value) / analytical_value * 100.0

    return RichardsonEstimate(
        extrapolated_value=f_inf,
        observed_order_p=p,
        refinement_ratio_r=r,
        refinement_ratio_constant=ratio_constant,
        extrapolated_residual_pct=residual_pct,
        notes=" ".join(fail_notes),
    )


def compute_richardson_from_artifact(
    artifact: ConvergenceArtifact,
    h_direction: HDirection,
) -> RichardsonEstimate | None:
    """Phase 31 C: derive a Richardson estimate from a populated
    ConvergenceArtifact.

    `h_direction` declares how `refinement_param` relates to the
    physical mesh size — see `HDirection`. The analytical reference
    is taken from `points[-1].analytical_value` (pinned identical
    across all refinements by Phase 30 D E:-1; an assertion enforces
    this).

    Returns None when the artifact has fewer than 3 points
    (Richardson needs 3); otherwise always returns a
    RichardsonEstimate (possibly with `extrapolated_value=None`
    when the triple is non-monotone).
    """
    if len(artifact.points) < 3:
        return None
    # Phase 30 D E:-1: analytical should be identical across points.
    analyticals = {p.analytical_value for p in artifact.points[:3]}
    if len(analyticals) != 1:
        raise ValueError(
            f"convergence artifact for {artifact.case_id} has "
            f"divergent analytical_value across points: {analyticals}"
        )
    (analytical_value,) = analyticals

    params = [float(p.refinement_param) for p in artifact.points[:3]]
    observed = [p.observed_value for p in artifact.points[:3]]

    if h_direction == "param_is_h":
        h_sizes = params
    elif h_direction == "param_inverse_to_h":
        h_sizes = [1.0 / x for x in params]
    else:  # pragma: no cover — Literal exhaustiveness
        raise ValueError(f"unknown h_direction {h_direction!r}")

    # Align the analytical reference's SIGN with the observed-value
    # convention so the residual is computed in the same direction
    # as Phase 30 D's `residual_pct` field. The plate-ss-shell
    # artifact has observed_value > 0 (.frd uz positive in the +z
    # convention) and analytical_value < 0 (Timoshenko's a^4 series
    # signed for downward deflection); Phase 30 D's residual_pct
    # is therefore (|obs|-|ana|)/|ana|. The observed values flow
    # through Richardson math verbatim (sign preserved) and only
    # the analytical sign is flipped when convention disagrees.
    analytical_signed = analytical_value
    if observed[0] != 0.0 and analytical_value != 0.0:
        observed_sign_pos = observed[0] > 0.0
        analytical_sign_pos = analytical_value > 0.0
        if observed_sign_pos != analytical_sign_pos:
            analytical_signed = -analytical_value

    return richardson_extrapolate(
        h_sizes=h_sizes,
        observed_values=observed,
        analytical_value=analytical_signed,
    )


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


def _richardson_to_payload(r: RichardsonEstimate) -> dict:
    """Phase 31 C: serialize a RichardsonEstimate to the JSON shape
    written under the artifact's top-level `richardson` field."""
    return {
        "extrapolated_value": r.extrapolated_value,
        "observed_order_p": r.observed_order_p,
        "refinement_ratio_r": r.refinement_ratio_r,
        "refinement_ratio_constant": r.refinement_ratio_constant,
        "extrapolated_residual_pct": r.extrapolated_residual_pct,
        "notes": r.notes,
    }


def write_convergence_artifact(
    case_golden_dir: Path,
    artifact: ConvergenceArtifact,
) -> Path:
    """Persist `convergence_study.json` in the case's golden_samples
    directory.

    Schema versioning:

    * 1.0.0 (Phase 30 D): no `richardson` field. Equivalent to
      `artifact.richardson is None`.
    * 1.1.0 (Phase 31 C): optional `richardson` top-level field.
      `schema_version` is bumped to "1.1.0" UNCONDITIONALLY because
      the writer now always emits the field key (value may be null).
      Old 1.0.0 readers seeing a 1.1.0 artifact with `richardson:
      null` get the same semantics as a 1.0.0 artifact.
    """
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.1.0",
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
        "richardson": (
            _richardson_to_payload(artifact.richardson)
            if artifact.richardson is not None
            else None
        ),
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
