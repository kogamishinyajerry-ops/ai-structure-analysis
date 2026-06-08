"""Tier 1 energy audit extractor (FM-04a Phase 2 A).

Builds a ``BallisticEnergyAudit`` from the OpenRadioss engine `.out`
energy progress table parsed by ``engine_energy_history``. Closes the
``partial_energy_audit_status: partial_candidate`` gap on every existing
GS-102 candidate run that has a `model_00_0001.out` file.

Honest limitations preserved at the audit-status level:

* The ``.out`` progress table aggregates plastic + elastic + hourglass
  energies into a single ``I-ENERGY`` column. The per-term breakdown
  requires explicit ``/TH/PART`` (or ``/TH/MAT``) cards in the starter
  and a `.thy` parser. Both are deferred work and noted in the audit
  ``claim_impact`` field.
* Values are reported in the OpenRadioss deck's own unit system
  (kg/mm/ms in the GS-102-candidate family). The audit's
  ``unit_system_note`` field carries that boundary forward.

Tier 1 engineering candidate; not signed validation; not benchmark
agreement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .engine_energy_history import (
    EngineEnergyHistory,
    parse_engine_out_energy_history,
    summarize_energy_history,
)
from .metric_extraction import BallisticEnergyAudit


CLAIM_IMPACT_CLOSED_AGGREGATE = (
    "Tier 1 closed aggregate energy audit: kinetic energies (translational + "
    "rotational), aggregate internal energy (plastic + elastic + hourglass), "
    "and external work extracted from the OpenRadioss engine .out progress "
    "table. Per-term plastic / contact / hourglass breakdown requires "
    "/TH/PART or /TH/MAT cards in the starter; not signed validation; not "
    "benchmark agreement."
)
CLAIM_IMPACT_PARTIAL_KE_ONLY = (
    "Tier 1 partial energy audit: kinetic energies derived from projectile "
    "frame samples only; aggregate internal energy and external work "
    "unavailable (engine .out energy table missing); not signed validation; "
    "not benchmark agreement."
)
CLAIM_IMPACT_UNAVAILABLE = (
    "Energy audit unavailable: neither projectile mass + sample velocities "
    "nor an engine .out energy table was available; not signed validation."
)

UNIT_SYSTEM_NOTE_DEFAULT = (
    "OpenRadioss deck unit system (e.g. kg/mm/ms in the GS-102-candidate "
    "family); audit consumers must trust deck units or attach an explicit "
    "unit conversion note."
)


def build_energy_audit_from_engine_out(
    out_path: Path | str,
    *,
    history: EngineEnergyHistory | None = None,
) -> BallisticEnergyAudit:
    """Build a ``BallisticEnergyAudit`` from the engine `.out` file.

    Parses the engine `.out` energy table (or accepts a pre-parsed
    ``history``) and returns a ``BallisticEnergyAudit`` populated with
    initial / residual kinetic energy plus the aggregate internal
    energy and external work, all in the OpenRadioss deck unit system.
    Per-term plastic / contact / hourglass fields stay ``None``.

    Returns an audit with every term ``None`` when the engine `.out`
    energy table is unreachable.
    """
    parsed = history if history is not None else parse_engine_out_energy_history(out_path)
    summary = summarize_energy_history(parsed)
    return BallisticEnergyAudit(
        initial_kinetic_energy_j=_or_none(summary["initial_kinetic_energy_t"]),
        residual_kinetic_energy_j=_or_none(summary["residual_kinetic_energy_t"]),
        # Per-term breakdown stays None; aggregate goes into the audit summary
        # surfaced by ``assess_energy_audit``.
        plastic_dissipation_j=None,
        contact_friction_j=None,
        hourglass_energy_j=None,
    )


def assess_energy_audit(
    audit: BallisticEnergyAudit,
    *,
    history: EngineEnergyHistory | None,
) -> dict[str, Any]:
    """Return a structured audit summary block for the metrics sidecar.

    Status field values:

    * ``closed_aggregate`` — KE_initial / KE_residual + final aggregate
      internal energy + external work all present; per-term breakdown
      explicitly noted as aggregated.
    * ``partial_candidate`` — only KE_initial / KE_residual present
      (e.g. via projectile-mass + sample-velocity fallback). Aggregate
      internal energy unavailable.
    * ``unavailable`` — no kinetic energy data; audit cannot proceed.

    The shape is additive on top of the legacy ``partial_energy_audit``
    block consumed by 33 existing GS-102 run reports: every legacy key
    (``initial_kinetic_energy_j``, ``residual_kinetic_energy_j``,
    ``plastic_dissipation_j``, ``contact_friction_j``,
    ``hourglass_energy_j``, ``missing_terms``) is preserved.
    """
    summary = summarize_energy_history(history) if history is not None else {
        "initial_kinetic_energy_t": None,
        "residual_kinetic_energy_t": None,
        "initial_kinetic_energy_r": None,
        "residual_kinetic_energy_r": None,
        "final_internal_energy_total": None,
        "final_external_work": None,
        "energy_balance_error_pct": None,
    }

    initial_ke = _first_present(
        audit.initial_kinetic_energy_j,
        summary["initial_kinetic_energy_t"],
    )
    residual_ke = _first_present(
        audit.residual_kinetic_energy_j,
        summary["residual_kinetic_energy_t"],
    )
    aggregate_internal = summary["final_internal_energy_total"]
    external_work = summary["final_external_work"]
    balance_error_pct = summary["energy_balance_error_pct"]

    legacy_missing_terms = [
        key
        for key, value in (
            ("plastic_dissipation_j", audit.plastic_dissipation_j),
            ("contact_friction_j", audit.contact_friction_j),
            ("hourglass_energy_j", audit.hourglass_energy_j),
        )
        if value is None
    ]

    status = _classify(
        initial_ke=initial_ke,
        residual_ke=residual_ke,
        aggregate_internal=aggregate_internal,
        external_work=external_work,
    )
    claim_impact = _claim_impact(status)

    return {
        "status": status,
        "initial_kinetic_energy_j": _round_or_none(initial_ke),
        "residual_kinetic_energy_j": _round_or_none(residual_ke),
        "plastic_dissipation_j": audit.plastic_dissipation_j,
        "contact_friction_j": audit.contact_friction_j,
        "hourglass_energy_j": audit.hourglass_energy_j,
        "aggregate_internal_energy_j": _round_or_none(aggregate_internal),
        "external_work_j": _round_or_none(external_work),
        "energy_balance_error_pct": _round_or_none(balance_error_pct),
        "missing_terms": legacy_missing_terms,
        "breakdown_status": (
            "aggregated_into_internal_energy"
            if aggregate_internal is not None
            else "unavailable"
        ),
        "unit_system_note": UNIT_SYSTEM_NOTE_DEFAULT,
        "claim_impact": claim_impact,
    }


def _classify(
    *,
    initial_ke: float | None,
    residual_ke: float | None,
    aggregate_internal: float | None,
    external_work: float | None,
) -> str:
    if initial_ke is None or residual_ke is None:
        return "unavailable"
    if aggregate_internal is None or external_work is None:
        return "partial_candidate"
    return "closed_aggregate"


def _claim_impact(status: str) -> str:
    if status == "closed_aggregate":
        return CLAIM_IMPACT_CLOSED_AGGREGATE
    if status == "partial_candidate":
        return CLAIM_IMPACT_PARTIAL_KE_ONLY
    return CLAIM_IMPACT_UNAVAILABLE


def _or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _first_present(*values: object) -> float | None:
    for value in values:
        if value is not None:
            return float(value)
    return None


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)
