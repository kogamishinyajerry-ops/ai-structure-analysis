"""Tier 1 candidate explicit-dynamics extraction service (FM-04a Phase 14 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Parses the canonical explicit-dynamics output shape — an animation manifest
of per-frame energy partition + first-impact response — AND provides a
1D bar wave-propagation analytical cross-check that pins the expected
first-reflection timing for an axial-impact rod.

What this is NOT:
* This is NOT a real solver. The parser READS solver-emitted manifests;
  it does NOT run CalculiX *DYNAMIC, LS-DYNA, OpenRadioss, or any
  explicit-integration kernel.
* The analytical cross-check is the 1D elastic-bar wave equation
  (``c = sqrt(E/rho)``, ``t_refl = L/c``). It is NOT a benchmark
  agreement: a Tier 1 candidate may legitimately differ from the
  closed-form bar speed because of (a) lateral inertia (Rayleigh
  dispersion), (b) plasticity, (c) contact-stiffness softening,
  (d) 3D geometric effects. The 5%-tolerance constant
  ``WAVE_CROSS_CHECK_TOLERANCE_PCT`` reflects "should be in the
  analytical ballpark for a 1D rod with small lateral cross-section",
  not "matches Tier 2 benchmark".
* The energy-partition audit checks per-frame kinetic + internal energy
  versus external work using a small float tolerance; it does NOT
  certify energy conservation — only flags non-physical injection
  beyond machine epsilon.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``,
no ``production ready``, no ``certified``, no ``approved for service``,
no ``asme compliant``, no ``signed off``. Disclaimer ``not <claim>``
forms remain allowed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# -- SSOT constants -------------------------------------------------------

WAVE_CROSS_CHECK_TOLERANCE_PCT: float = 5.0
"""Maximum percentage deviation of the observed first-reflection time
from the analytical 1D-bar prediction before the cross-check is flagged
as DRIFTED.

Rationale: a 1D rod with a small cross-section under axial impact has
a closed-form first-reflection time of ``t = L/c`` where
``c = sqrt(E/rho)``. Real Tier 1 candidates introduce dispersion
(lateral inertia), small geometric effects, and time-step quantization
that legitimately move the observed reflection time by a few percent.
5.0% is the engineering rule of thumb for "still on the 1D-bar
manifold" and matches the Phase 11 ballistic-axis tolerance posture.
NOT a Tier 2 benchmark threshold."""

EXPLICIT_DYNAMICS_CONVERGENCE_KIND: str = "explicit_dynamics"
"""SSOT for the ``convergence_kind`` discriminator value used by
``case_completeness`` and ``advisor_critique`` when an analysis is an
explicit-integration transient solve. The string MUST match
``ANALYSIS_TYPE_TUPLE[3]`` in ``case_completeness.py``."""

ENERGY_PARTITION_EPSILON: float = 1e-9
"""Absolute floor (Joules) below which energy-partition discrepancies
are NOT flagged. Sub-nano-Joule drift is float arithmetic; flagging it
would create false positives on every frame of every fixture."""

ENERGY_PARTITION_DRIFT_FRACTION: float = 0.01
"""Relative tolerance (1% of external work) above which the per-frame
energy partition is flagged as NON-PHYSICAL. Below this floor the
partition is treated as CLEAN. Mirrors the closure-aggregate posture
``case_completeness`` uses for ``energy_audit.closed_aggregate``."""

# -- dataclasses ----------------------------------------------------------


@dataclass(frozen=True)
class AnimationManifest:
    """Per-frame energy partition + first-impact response for an
    explicit-dynamics transient solve."""

    frame_count: int
    frame_dt_s: float
    total_duration_s: float
    per_frame_kinetic_energy_j: tuple[float, ...]
    per_frame_internal_energy_j: tuple[float, ...]
    per_frame_external_work_j: tuple[float, ...]
    first_reflection_frame_index: int | None = None
    """Frame index (0-based) at which the response indicates the wave
    front has reflected from the far boundary. ``None`` when the
    fixture does not pin a first-reflection frame."""


@dataclass(frozen=True)
class WaveResiduals:
    """Residuals between observed first-reflection time and the 1D-bar
    analytical prediction."""

    observed_first_reflection_s: float
    analytical_first_reflection_s: float
    residual_s: float
    residual_pct: float
    tolerance_pct: float
    within_tolerance: bool


@dataclass(frozen=True)
class EnergyPartitionAudit:
    """Per-frame energy-partition audit summary."""

    frame_count: int
    max_abs_drift_j: float
    max_rel_drift_fraction: float
    flagged_frame_indices: tuple[int, ...]
    clean: bool
    drift_fraction_tolerance: float = field(
        default=ENERGY_PARTITION_DRIFT_FRACTION
    )


# -- parser ---------------------------------------------------------------


def parse_animation_manifest(path: Path | str) -> AnimationManifest:
    """Parse a canonical explicit-dynamics animation manifest JSON.

    Required top-level keys:
    * ``frame_count: int``
    * ``frame_dt_s: float``
    * ``total_duration_s: float``
    * ``per_frame_kinetic_energy_j: list[float]``
    * ``per_frame_internal_energy_j: list[float]``
    * ``per_frame_external_work_j: list[float]``

    Optional top-level key:
    * ``first_reflection_frame_index: int | None``

    Raises:
        FileNotFoundError: when the manifest file is missing.
        ValueError: when a required key is absent, when the per-frame
            arrays have inconsistent lengths, or when ``frame_count``
            disagrees with the array length.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"animation manifest not found: {p}")
    try:
        raw: Any = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"animation manifest is not valid JSON: {p} ({exc.msg})"
        ) from exc
    if not isinstance(raw, dict):
        raise ValueError(
            f"animation manifest top-level must be an object: {p}"
        )

    required = (
        "frame_count",
        "frame_dt_s",
        "total_duration_s",
        "per_frame_kinetic_energy_j",
        "per_frame_internal_energy_j",
        "per_frame_external_work_j",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(
            f"animation manifest {p} missing required keys: {missing!r}"
        )

    frame_count = int(raw["frame_count"])
    frame_dt_s = float(raw["frame_dt_s"])
    total_duration_s = float(raw["total_duration_s"])
    kin = tuple(float(x) for x in raw["per_frame_kinetic_energy_j"])
    inn = tuple(float(x) for x in raw["per_frame_internal_energy_j"])
    ext = tuple(float(x) for x in raw["per_frame_external_work_j"])

    if not (len(kin) == len(inn) == len(ext) == frame_count):
        raise ValueError(
            f"animation manifest {p}: per-frame array lengths "
            f"({len(kin)}, {len(inn)}, {len(ext)}) inconsistent with "
            f"frame_count={frame_count}"
        )
    if frame_count < 1:
        raise ValueError(
            f"animation manifest {p}: frame_count must be >= 1, "
            f"got {frame_count}"
        )
    if frame_dt_s <= 0.0:
        raise ValueError(
            f"animation manifest {p}: frame_dt_s must be > 0, "
            f"got {frame_dt_s}"
        )

    refl_raw = raw.get("first_reflection_frame_index")
    refl: int | None
    if refl_raw is None:
        refl = None
    else:
        refl = int(refl_raw)
        if not 0 <= refl < frame_count:
            raise ValueError(
                f"animation manifest {p}: "
                f"first_reflection_frame_index={refl} out of range "
                f"[0, {frame_count})"
            )

    return AnimationManifest(
        frame_count=frame_count,
        frame_dt_s=frame_dt_s,
        total_duration_s=total_duration_s,
        per_frame_kinetic_energy_j=kin,
        per_frame_internal_energy_j=inn,
        per_frame_external_work_j=ext,
        first_reflection_frame_index=refl,
    )


# -- analytical 1D bar wave --------------------------------------------------


def bar_wave_speed_m_per_s(E_Pa: float, rho_kg_per_m3: float) -> float:
    """Closed-form 1D-bar wave speed ``c = sqrt(E/rho)``.

    Inputs MUST be positive; non-positive inputs raise ``ValueError``
    (this is a numerical defense, not a physics check). The result
    is the elementary 1D-rod wave speed, NOT the bulk 3D dilatational
    speed (which is sqrt((K+4G/3)/rho)).
    """
    if E_Pa <= 0.0 or rho_kg_per_m3 <= 0.0:
        raise ValueError(
            f"bar_wave_speed_m_per_s: E and rho must be > 0; got "
            f"E={E_Pa}, rho={rho_kg_per_m3}"
        )
    return math.sqrt(E_Pa / rho_kg_per_m3)


def bar_wave_first_reflection_s(L_m: float, c_m_per_s: float) -> float:
    """Analytical first-reflection time for a 1D rod of length ``L_m``
    with wave speed ``c_m_per_s``: ``t = L/c``.

    This is the time for the wave front to traverse the rod once
    (origin to far boundary). The far-boundary reflection arrives back
    at the impact face at ``2*t`` — the function returns the
    one-way-travel time because Tier 1 candidates pin the FIRST
    reflection ARRIVAL at the far boundary, not the round trip.
    """
    if L_m <= 0.0 or c_m_per_s <= 0.0:
        raise ValueError(
            f"bar_wave_first_reflection_s: L and c must be > 0; got "
            f"L={L_m}, c={c_m_per_s}"
        )
    return L_m / c_m_per_s


def wave_propagation_residuals(
    observed_first_reflection_s: float,
    analytical_first_reflection_s: float,
    tolerance_pct: float = WAVE_CROSS_CHECK_TOLERANCE_PCT,
) -> WaveResiduals:
    """Residuals + tolerance verdict for the 1D-bar wave-propagation
    cross-check.

    Tier 1 candidate posture: "observed lands within
    ``tolerance_pct``% of analytical" is the engineering ballpark
    pin, NOT a Tier 2 benchmark agreement.
    """
    if analytical_first_reflection_s <= 0.0:
        raise ValueError(
            f"wave_propagation_residuals: analytical reflection time "
            f"must be > 0; got {analytical_first_reflection_s}"
        )
    if tolerance_pct <= 0.0:
        raise ValueError(
            f"wave_propagation_residuals: tolerance_pct must be > 0; "
            f"got {tolerance_pct}"
        )
    residual = observed_first_reflection_s - analytical_first_reflection_s
    residual_pct = (
        100.0 * abs(residual) / analytical_first_reflection_s
    )
    return WaveResiduals(
        observed_first_reflection_s=observed_first_reflection_s,
        analytical_first_reflection_s=analytical_first_reflection_s,
        residual_s=residual,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        within_tolerance=residual_pct <= tolerance_pct,
    )


# -- energy-partition audit -----------------------------------------------


def energy_partition_audit(
    manifest: AnimationManifest,
    drift_fraction_tolerance: float = ENERGY_PARTITION_DRIFT_FRACTION,
) -> EnergyPartitionAudit:
    """Per-frame energy-partition audit.

    The 1D-rod conservation expectation is::

        kinetic[f] + internal[f] - external_work[f] ~= 0

    Frames with absolute drift below ``ENERGY_PARTITION_EPSILON`` are
    ALWAYS clean (float-arithmetic noise). Frames whose relative
    drift exceeds ``drift_fraction_tolerance`` are flagged.
    Relative drift is computed against ``max(|external_work|, eps)``
    so a frame with zero external work and non-zero kinetic +
    internal is flagged with infinite drift (correctly: energy
    injection without source is non-physical).
    """
    kin = manifest.per_frame_kinetic_energy_j
    inn = manifest.per_frame_internal_energy_j
    ext = manifest.per_frame_external_work_j
    flagged: list[int] = []
    max_abs = 0.0
    max_rel = 0.0
    for idx in range(manifest.frame_count):
        drift = kin[idx] + inn[idx] - ext[idx]
        abs_drift = abs(drift)
        if abs_drift > max_abs:
            max_abs = abs_drift
        denom = max(abs(ext[idx]), ENERGY_PARTITION_EPSILON)
        rel = abs_drift / denom
        if rel > max_rel:
            max_rel = rel
        if abs_drift > ENERGY_PARTITION_EPSILON:
            if rel > drift_fraction_tolerance:
                flagged.append(idx)
    return EnergyPartitionAudit(
        frame_count=manifest.frame_count,
        max_abs_drift_j=max_abs,
        max_rel_drift_fraction=max_rel,
        flagged_frame_indices=tuple(flagged),
        clean=len(flagged) == 0,
        drift_fraction_tolerance=drift_fraction_tolerance,
    )
