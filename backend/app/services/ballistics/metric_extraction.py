"""Candidate ballistic metric extraction (Tier 1 engineering candidate).

Writes ``ballistic_metrics.json`` with the exact shape consumed by
``candidate_report_spine.build_candidate_report_spine``. Real OpenRadioss
output parsing happens elsewhere; this module operates on a flat,
structured input so it can be exercised end-to-end without solver binaries.

Allowed wording (per ADR-023 + ADR-024 lite):

* Tier 1 engineering candidate
* not signed validation
* not benchmark agreement
* candidate residual velocity / perforation marker / energy balance

Forbidden wording:

* "validated against <anything>"
* "benchmark agreement"
* "signed validation"
* "perforation completed"
* "bullet-through-steel complete"
* "validated physics"
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
)
DEFAULT_RESIDUAL_VELOCITY_FLOOR_M_PER_S = 5.0
PERFORATION_STATES = {
    "still",
    "embedded_candidate",
    "perforated_candidate",
    "stopped_candidate",
    "unknown",
}


@dataclass(frozen=True)
class BallisticTimeSample:
    """Single time sample for a representative projectile node.

    Coordinates are in metres; velocities in metres per second. The
    extractor assumes the projectile travels along +x by default; pass
    ``impact_axis`` to ``BallisticExtractionInput`` to override.
    """

    t_s: float
    position_m: tuple[float, float, float]
    velocity_m_per_s: tuple[float, float, float]


@dataclass(frozen=True)
class BallisticEnergyAudit:
    """Energy audit values pulled from OpenRadioss output.

    All values are in joules. Missing values default to ``None``; the
    extractor will mark ``status=unavailable`` for ``energy_balance`` if
    ``initial_kinetic_energy_j`` is missing.
    """

    initial_kinetic_energy_j: Optional[float] = None
    plastic_dissipation_j: Optional[float] = None
    contact_friction_j: Optional[float] = None
    hourglass_energy_j: Optional[float] = None
    residual_kinetic_energy_j: Optional[float] = None


@dataclass
class BallisticExtractionInput:
    """Structured input for ``write_ballistic_metrics``."""

    case_id: str
    projectile_mass_kg: float
    plate_back_face_x_m: float
    plate_thickness_m: float
    samples: list[BallisticTimeSample] = field(default_factory=list)
    impact_axis: str = "x"
    energy_audit: BallisticEnergyAudit = field(default_factory=BallisticEnergyAudit)
    residual_velocity_floor_m_per_s: float = DEFAULT_RESIDUAL_VELOCITY_FLOOR_M_PER_S
    claim_boundary: str = CLAIM_BOUNDARY

    def __post_init__(self) -> None:
        if self.impact_axis not in ("x", "y", "z"):
            raise ValueError(f"impact_axis must be 'x', 'y', or 'z'; got {self.impact_axis!r}")
        if self.projectile_mass_kg <= 0:
            raise ValueError("projectile_mass_kg must be > 0")
        if self.plate_thickness_m <= 0:
            raise ValueError("plate_thickness_m must be > 0")
        if self.residual_velocity_floor_m_per_s < 0:
            raise ValueError("residual_velocity_floor_m_per_s must be >= 0")


def write_ballistic_metrics(
    inp: BallisticExtractionInput,
    output_dir: Path | str,
) -> Path:
    """Compute candidate ballistic metrics and write the sidecar.

    Returns the absolute path of the written ``ballistic_metrics.json``.

    The sidecar shape matches the read contract in
    ``candidate_report_spine.build_candidate_report_spine``:

    * ``status`` = ``candidate_observed``
    * ``projectile_initial_velocity_m_per_s`` (magnitude of first sample)
    * ``residual_velocity_candidate_m_per_s`` (magnitude of last sample)
    * ``perforation_marker`` ∈ ``PERFORATION_STATES``
    * ``energy_balance`` block (when initial_kinetic_energy_j is provided)
    * ``claim_boundary`` (Tier 1 candidate, never signed validation)
    """
    if not inp.samples:
        raise ValueError("BallisticExtractionInput.samples must not be empty")

    initial = inp.samples[0]
    final = inp.samples[-1]
    initial_speed = _speed(initial.velocity_m_per_s)
    residual_speed = _speed(final.velocity_m_per_s)
    marker = _classify_perforation(inp, initial, final)

    energy_block = _energy_balance(inp, initial_speed, residual_speed)

    payload: dict[str, Any] = {
        "case_id": inp.case_id,
        "status": "candidate_observed",
        "claim_boundary": inp.claim_boundary,
        "projectile_initial_velocity_m_per_s": _round(initial_speed, 6),
        "residual_velocity_candidate_m_per_s": _round(residual_speed, 6),
        "perforation_marker": marker,
        "extraction_metadata": {
            "impact_axis": inp.impact_axis,
            "plate_back_face_axis_value_m": inp.plate_back_face_x_m,
            "plate_thickness_m": inp.plate_thickness_m,
            "projectile_mass_kg": inp.projectile_mass_kg,
            "sample_count": len(inp.samples),
            "first_sample_t_s": initial.t_s,
            "last_sample_t_s": final.t_s,
            "residual_velocity_floor_m_per_s": inp.residual_velocity_floor_m_per_s,
            "claim_impact": (
                "Tier 1 candidate ballistic metrics; not benchmark agreement; "
                "not signed validation"
            ),
        },
    }
    if energy_block is not None:
        payload["energy_balance"] = energy_block

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ballistic_metrics.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------


def _speed(velocity: Iterable[float]) -> float:
    return math.sqrt(sum(component * component for component in velocity))


def _round(value: float, digits: int) -> float:
    return round(float(value), digits)


def _axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[axis]


def _classify_perforation(
    inp: BallisticExtractionInput,
    initial: BallisticTimeSample,
    final: BallisticTimeSample,
) -> str:
    axis_idx = _axis_index(inp.impact_axis)
    initial_axis_pos = initial.position_m[axis_idx]
    final_axis_pos = final.position_m[axis_idx]
    final_speed = _speed(final.velocity_m_per_s)
    plate_back = inp.plate_back_face_x_m
    plate_front = plate_back - inp.plate_thickness_m

    direction_sign = 1.0 if initial_axis_pos < plate_back else -1.0

    crossed_plate = (
        direction_sign > 0 and final_axis_pos > plate_back
    ) or (direction_sign < 0 and final_axis_pos < plate_front)

    inside_plate = (
        plate_front - 1e-9 <= final_axis_pos <= plate_back + 1e-9
    )

    if crossed_plate and final_speed > inp.residual_velocity_floor_m_per_s:
        return "perforated_candidate"
    if crossed_plate and final_speed <= inp.residual_velocity_floor_m_per_s:
        # crossed but lost almost all speed — Tier 1 marks this as stopped_candidate
        # rather than perforated_candidate to keep the residual-velocity claim honest
        return "stopped_candidate"
    if inside_plate:
        return "embedded_candidate"
    if final_speed <= inp.residual_velocity_floor_m_per_s:
        return "stopped_candidate"
    return "unknown"


def _energy_balance(
    inp: BallisticExtractionInput,
    initial_speed: float,
    residual_speed: float,
) -> Optional[dict[str, Any]]:
    audit = inp.energy_audit
    initial_ke = audit.initial_kinetic_energy_j
    if initial_ke is None and inp.projectile_mass_kg > 0:
        initial_ke = 0.5 * inp.projectile_mass_kg * initial_speed * initial_speed
    if initial_ke is None or initial_ke <= 0:
        return None

    residual_ke = audit.residual_kinetic_energy_j
    if residual_ke is None and inp.projectile_mass_kg > 0:
        residual_ke = 0.5 * inp.projectile_mass_kg * residual_speed * residual_speed

    return {
        "initial_kinetic_energy_j": _round(initial_ke, 6),
        "plastic_dissipation_j": _maybe_round(audit.plastic_dissipation_j, 6),
        "contact_friction_j": _maybe_round(audit.contact_friction_j, 6),
        "hourglass_energy_j": _maybe_round(audit.hourglass_energy_j, 6),
        "residual_kinetic_energy_j": _maybe_round(residual_ke, 6),
    }


def _maybe_round(value: Optional[float], digits: int) -> Optional[float]:
    return _round(value, digits) if isinstance(value, (int, float)) else None
