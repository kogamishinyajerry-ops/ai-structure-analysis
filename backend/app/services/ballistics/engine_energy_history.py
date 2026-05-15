"""OpenRadioss engine `.out` energy time-history parser (Tier 1 candidate).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

OpenRadioss writes a per-cycle progress table to `model_00_0001.out` whose
header line is::

    CYCLE    TIME      TIME-STEP  ELEMENT          ERROR  I-ENERGY    K-ENERGY T  K-ENERGY R  EXT-WORK     MAS.ERR     TOTAL MASS  MASS ADDED

Each subsequent line under that header is a 13-token row::

    0   0.000   0.1084E-03   INTER   1   0.0%   0.000   0.1731E+10   0.000   0.000   0.000   0.2028E+05   0.000

This module gives the FM-04a Tier 1 pipeline an honest aggregate energy
history without claiming a per-term (plastic / contact / hourglass)
breakdown. Per-term breakdown requires explicit ``/TH/PART`` or
``/TH/MAT`` cards in the starter and a `.thy` parser; both are reserved
for a future slice (and ultimately FM-04b).

Values are reported in the OpenRadioss deck's own unit system (kg/mm/ms
in the GS-102-candidate family). The audit consumer is expected to
either trust the deck units or attach an explicit unit-system note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement; "
    "values_in_openradioss_deck_unit_system"
)

_HEADER_RE = re.compile(
    r"CYCLE\s+TIME\s+TIME-STEP\s+ELEMENT\s+ERROR\s+I-ENERGY\s+"
    r"K-ENERGY\s+T\s+K-ENERGY\s+R\s+EXT-WORK\s+MAS\.ERR\s+TOTAL MASS\s+MASS ADDED",
    re.IGNORECASE,
)
_FLOAT_RE = re.compile(r"^[+\-]?\d+(?:\.\d*)?(?:[Ee][+\-]?\d+)?$")
_INT_RE = re.compile(r"^[+\-]?\d+$")


@dataclass(frozen=True)
class EngineEnergyRow:
    """One row of the OpenRadioss engine `.out` progress table."""

    cycle: int
    time_s: float
    time_step_s: float
    element_kind: str
    element_id: int
    error_pct: float
    internal_energy: float
    kinetic_energy_translational: float
    kinetic_energy_rotational: float
    external_work: float
    mass_error: float
    total_mass: float
    mass_added: float


@dataclass(frozen=True)
class EngineEnergyHistory:
    """Aggregate energy history parsed from `model_00_0001.out`."""

    rows: tuple[EngineEnergyRow, ...] = field(default_factory=tuple)
    source_path: str = ""
    claim_boundary: str = CLAIM_BOUNDARY

    @property
    def has_history(self) -> bool:
        return len(self.rows) > 0

    @property
    def initial_row(self) -> EngineEnergyRow | None:
        return self.rows[0] if self.rows else None

    @property
    def final_row(self) -> EngineEnergyRow | None:
        return self.rows[-1] if self.rows else None


def parse_engine_out_energy_history(out_path: Path | str) -> EngineEnergyHistory:
    """Parse the engine `.out` progress table into an energy history.

    Returns an ``EngineEnergyHistory`` whose ``rows`` is empty when the
    file does not contain the table (e.g. the engine never reached its
    first row). Never raises on missing files; returns empty history
    instead so the caller can mark ``energy_audit_status=unavailable``.
    """
    path = Path(out_path)
    if not path.is_file():
        return EngineEnergyHistory(rows=(), source_path=str(path))

    text = path.read_text(encoding="utf-8", errors="replace")
    rows = tuple(_iter_rows(text))
    return EngineEnergyHistory(rows=rows, source_path=str(path))


def summarize_energy_history(history: EngineEnergyHistory) -> dict[str, float | None]:
    """Compute aggregate energy summary from a parsed history.

    Returns a dict with these keys (all ``None`` when the history is
    empty):

    * ``initial_kinetic_energy_t`` — KE_T at the first row
    * ``residual_kinetic_energy_t`` — KE_T at the last row
    * ``initial_kinetic_energy_r`` — KE_R at the first row
    * ``residual_kinetic_energy_r`` — KE_R at the last row
    * ``final_internal_energy_total`` — I-ENERGY at the last row (plastic +
      elastic + hourglass aggregate; not separately broken down here)
    * ``final_external_work`` — EXT-WORK at the last row
    * ``energy_balance_error_pct`` — abs balance error vs initial KE_T
    """
    if not history.has_history:
        return {
            "initial_kinetic_energy_t": None,
            "residual_kinetic_energy_t": None,
            "initial_kinetic_energy_r": None,
            "residual_kinetic_energy_r": None,
            "final_internal_energy_total": None,
            "final_external_work": None,
            "energy_balance_error_pct": None,
        }

    initial = history.initial_row
    final = history.final_row
    assert initial is not None and final is not None  # guarded by has_history

    initial_ke_t = float(initial.kinetic_energy_translational)
    residual_ke_t = float(final.kinetic_energy_translational)
    final_internal = float(final.internal_energy)
    final_ext_work = float(final.external_work)

    # Energy conservation: KE_initial + EXT_WORK ≈ KE_residual + I_internal.
    # When initial KE is the only thing we trust as known, balance error is the
    # absolute residual of that equation normalized by initial KE.
    balance_error_pct: float | None
    if initial_ke_t > 0.0:
        residual_balance = (initial_ke_t + final_ext_work) - (
            residual_ke_t + final_internal
        )
        balance_error_pct = 100.0 * abs(residual_balance) / initial_ke_t
    else:
        balance_error_pct = None

    return {
        "initial_kinetic_energy_t": initial_ke_t,
        "residual_kinetic_energy_t": residual_ke_t,
        "initial_kinetic_energy_r": float(initial.kinetic_energy_rotational),
        "residual_kinetic_energy_r": float(final.kinetic_energy_rotational),
        "final_internal_energy_total": final_internal,
        "final_external_work": final_ext_work,
        "energy_balance_error_pct": balance_error_pct,
    }


def _iter_rows(text: str) -> Iterable[EngineEnergyRow]:
    in_table = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not in_table:
            if _HEADER_RE.search(line):
                in_table = True
            continue
        row = _try_parse_row(line)
        if row is not None:
            yield row


def _try_parse_row(line: str) -> EngineEnergyRow | None:
    tokens = line.split()
    if len(tokens) < 13:
        return None
    cycle_tok = tokens[0]
    if not _INT_RE.match(cycle_tok):
        return None
    # Row layout: cycle, time, time-step, element_kind, element_id, error_pct,
    # i_energy, ke_t, ke_r, ext_work, mass_err, total_mass, mass_added
    try:
        cycle = int(cycle_tok)
        time_s = _parse_float(tokens[1])
        time_step_s = _parse_float(tokens[2])
        element_kind = tokens[3]
        element_id = int(tokens[4])
        error_pct = _parse_percent(tokens[5])
        i_energy = _parse_float(tokens[6])
        ke_t = _parse_float(tokens[7])
        ke_r = _parse_float(tokens[8])
        ext_work = _parse_float(tokens[9])
        mass_err = _parse_float(tokens[10])
        total_mass = _parse_float(tokens[11])
        mass_added = _parse_float(tokens[12])
    except (ValueError, KeyError):
        return None
    return EngineEnergyRow(
        cycle=cycle,
        time_s=time_s,
        time_step_s=time_step_s,
        element_kind=element_kind,
        element_id=element_id,
        error_pct=error_pct,
        internal_energy=i_energy,
        kinetic_energy_translational=ke_t,
        kinetic_energy_rotational=ke_r,
        external_work=ext_work,
        mass_error=mass_err,
        total_mass=total_mass,
        mass_added=mass_added,
    )


def _parse_float(token: str) -> float:
    if not _FLOAT_RE.match(token):
        raise ValueError(f"not a float: {token!r}")
    return float(token)


def _parse_percent(token: str) -> float:
    raw = token.rstrip("%")
    return _parse_float(raw)
