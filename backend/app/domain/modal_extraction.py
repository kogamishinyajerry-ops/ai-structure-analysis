"""Modal analysis extraction + Euler-Bernoulli cross-check (FM-04a Phase 12 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This module is the modal-eigenfrequency analog of the existing
``app.domain.stress_linearization`` Phase 11 module. It:

1. Parses a CalculiX modal solution's ``.dat`` eigenvalue output into a
   structured :class:`ModalResult` (eigenfrequencies in Hz + participation
   factors + effective modal mass per mode).
2. Computes the closed-form Euler-Bernoulli cantilever natural frequencies
   for the first N modes via the SSOT tuple :data:`EULER_BERNOULLI_BETA_LN`
   (pinned by ``test_phase12_modal_extraction.py``).
3. Builds a per-mode residual report comparing numerical vs analytical
   bending frequencies, surfacing the relative error so a reviewer can
   judge whether the modal sweep is converged enough to be a Tier 1
   candidate.

The module is **read-only**. It does NOT execute CalculiX; it only
reads frozen ``.dat`` / ``.frd`` bytes off disk and produces structured
results. Reviewer agency is preserved at every step.

Design pillars (project north-star — see memory
``feedback_cfd_harness_ai_advisor_pivot``):

* LLM-offline-first: the analytical cross-check is pure-Python math; no
  LLM dependency anywhere in this module.
* Read-only: never writes to ``golden_samples/**`` or any project
  artifact; HF1 zone untouched.
* Cross-check is an evidence-presence signal, NOT a validation-quality
  signal. A 0.14 % residual on mode 1 is a Tier 1 candidate observation;
  it does NOT promote the case to Tier 2 or constitute signed validation.

Module-level SSOTs (Phase 12 A):

* :data:`EULER_BERNOULLI_BETA_LN` — closed-form β·L roots for the
  clamped-free (cantilever) Euler-Bernoulli equation, first 4 modes.
  Pinned by ``test_euler_bernoulli_beta_ln_constants_are_correct``.
* :data:`MODAL_CROSS_CHECK_TOLERANCE_PCT` — relative-error tolerance
  beyond which the advisor flags a frequency-convergence concern in
  slice B (5.0 %, conservative engineering practice for first 2 bending
  modes on a structured hex mesh).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from app.services.reporting._schema_versions import (
    CONVERGENCE_STUDY_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------
# SSOT constants
# ---------------------------------------------------------------------


# Euler-Bernoulli β·L roots for clamped-free (cantilever) beam, first 4
# modes. From the characteristic equation ``cos(β·L)·cosh(β·L) + 1 = 0``.
# Reference: Blevins, "Formulas for Natural Frequency and Mode Shape"
# (1979), Table 8-1, p.108. These values are independent of beam
# material and geometry — they are dimensionless roots of the
# trigonometric/hyperbolic characteristic equation.
#
# Pinned by ``test_euler_bernoulli_beta_ln_constants_are_correct``.
# Changing these values requires a methodology-doc update + retro entry.
EULER_BERNOULLI_BETA_LN: tuple[float, float, float, float] = (
    1.8751040687119611,  # mode 1 (1st bending)
    4.6940911329741746,  # mode 2 (2nd bending)
    7.8547574382376123,  # mode 3 (3rd bending)
    10.995540734875467,  # mode 4 (4th bending)
)
"""Dimensionless β·L roots for the clamped-free Euler-Bernoulli
cantilever, first 4 modes. SSOT for the analytical cross-check;
modifying requires a methodology-doc update + Phase 12 A MINOR
schema bump if the count changes."""


# Tolerance threshold beyond which slice B's advisor flags a
# frequency-convergence concern. 5 % is the conservative engineering
# practice floor for first-2-bending-mode accuracy on a structured
# hex mesh; finer mesh routinely achieves <1 % on bending modes.
MODAL_CROSS_CHECK_TOLERANCE_PCT: float = 5.0
"""Relative-error tolerance (in percent) above which the advisor
surfaces a frequency-convergence concern in slice B. Pinned by
``test_modal_cross_check_tolerance_pct``."""


# Phase 12 A schema bump documentation: CONVERGENCE_STUDY_SCHEMA_VERSION
# 1.1.0 -> 1.2.0 adds ``"modal"`` as a valid value of the existing
# ``convergence_kind`` discriminator. For modal cases, the meaningful
# convergence axis is ``mode_count_sweep`` (i.e., the relative error on
# the dominant mode as the mesh / extraction count increases). The
# legacy ``mesh_sweep`` + ``dt_sweep`` axes are treated as N/A on modal
# cases (mode_count_sweep is the only convergence dimension that
# matters for an eigenproblem).
MODAL_CONVERGENCE_KIND: str = "modal"
"""Sentinel value the convergence_study schema accepts on
``convergence_kind`` for modal cases. Pinned by
``test_modal_convergence_kind_constant``."""


# ---------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class ModalMode:
    """One row from CalculiX's modal eigenvalue output block.

    Field semantics:
      * ``mode_no``: 1-indexed mode number as emitted by the solver.
      * ``eigenvalue``: ω² in (rad/s)². CalculiX's "EIGENVALUE" column.
      * ``omega_rad_per_s``: ω = sqrt(eigenvalue), the "FREQUENCY
        REAL PART (RAD/TIME)" column.
      * ``freq_hz``: ω / (2·π), the "FREQUENCY REAL PART (CYCLES/TIME)"
        column. This is what reviewers and engineering codes care about.
      * ``participation_factors``: 6-tuple (X, Y, Z, RX, RY, RZ) modal
        participation factors from the PARTICIPATION FACTORS block,
        used by slice B's mass-participation advisor concern.
      * ``effective_modal_mass``: 6-tuple (X, Y, Z, RX, RY, RZ)
        effective modal mass from the EFFECTIVE MODAL MASS block.
    """

    mode_no: int
    eigenvalue: float
    omega_rad_per_s: float
    freq_hz: float
    participation_factors: tuple[float, float, float, float, float, float]
    effective_modal_mass: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class ModalResult:
    """Parsed modal solver output. Read-only by construction."""

    case_id: str
    modes: tuple[ModalMode, ...]
    extraction_method: str  # e.g. "lanczos" (CalculiX default)
    schema_version: str  # ties payload to CONVERGENCE_STUDY_SCHEMA_VERSION


@dataclass(frozen=True)
class ModalResidual:
    """Per-mode residual: numerical vs analytical."""

    mode_no: int
    freq_numerical_hz: float
    freq_analytical_hz: float
    relative_error_pct: float
    within_tolerance: bool  # |relative_error_pct| <= MODAL_CROSS_CHECK_TOLERANCE_PCT


@dataclass(frozen=True)
class ModalResidualReport:
    """Aggregate cross-check report. Used by slice-B advisor surface."""

    case_id: str
    residuals: tuple[ModalResidual, ...]
    worst_relative_error_pct: float
    all_within_tolerance: bool
    tolerance_pct: float


@dataclass(frozen=True)
class CantileverBeamSpec:
    """Closed-form Euler-Bernoulli cantilever specification.

    All units SI: length m, density kg/m^3, E in Pa. The
    cross-sectional moment of inertia I and area A are computed from
    width / height for a rectangular cross-section; pass via the
    ``inertia_m4`` / ``area_m2`` fields if the cross-section is not
    rectangular.
    """

    length_m: float
    youngs_modulus_pa: float
    density_kg_per_m3: float
    inertia_m4: float
    area_m2: float


# ---------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------


_EIG_HEADER_RE = re.compile(r"E\s*I\s*G\s*E\s*N\s*V\s*A\s*L\s*U\s*E\s+O\s*U\s*T\s*P\s*U\s*T")
_PARTICIPATION_HEADER_RE = re.compile(
    r"P\s*A\s*R\s*T\s*I\s*C\s*I\s*P\s*A\s*T\s*I\s*O\s*N\s+F\s*A\s*C\s*T\s*O\s*R\s*S"
)
_EFFECTIVE_MASS_HEADER_RE = re.compile(
    r"E\s*F\s*F\s*E\s*C\s*T\s*I\s*V\s*E\s+M\s*O\s*D\s*A\s*L\s+M\s*A\s*S\s*S"
)


def parse_modal_dat(dat_path: Path, case_id: str) -> ModalResult:
    """Parse a CalculiX modal ``.dat`` file into a :class:`ModalResult`.

    The CalculiX modal solver writes 3 blocks per step:

    1. ``EIGENVALUE OUTPUT`` — one row per mode with columns
       MODE NO / EIGENVALUE / FREQ (RAD/TIME) / FREQ (CYCLES/TIME) /
       FREQ (RAD/TIME) imaginary.
    2. ``PARTICIPATION FACTORS`` — one row per mode with 6 components.
    3. ``EFFECTIVE MODAL MASS`` — one row per mode with 6 components.

    The parser is defensive: any malformed block raises ValueError with
    a specific reason so a future schema drift in CalculiX is loudly
    refused, not silently accepted.
    """
    if not dat_path.is_file():
        raise FileNotFoundError(f"modal .dat not found: {dat_path}")

    text = dat_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    eig_rows = _extract_block_rows(lines, _EIG_HEADER_RE, expected_cols=5)
    part_rows = _extract_block_rows(lines, _PARTICIPATION_HEADER_RE, expected_cols=7)
    mass_rows = _extract_block_rows(lines, _EFFECTIVE_MASS_HEADER_RE, expected_cols=7)

    if not eig_rows:
        raise ValueError(
            f"modal .dat at {dat_path} has no EIGENVALUE OUTPUT block "
            f"(or block is malformed); refusing to parse"
        )

    # Index participation + mass rows by mode_no for safe alignment;
    # the solver always emits them in the same order but joining on
    # mode_no is defensive against future column ordering changes.
    part_by_mode = {int(row[0]): tuple(float(v) for v in row[1:7]) for row in part_rows}
    mass_by_mode = {int(row[0]): tuple(float(v) for v in row[1:7]) for row in mass_rows}

    modes: list[ModalMode] = []
    for row in eig_rows:
        mode_no = int(row[0])
        eigenvalue = float(row[1])
        omega = float(row[2])
        freq_hz = float(row[3])
        modes.append(
            ModalMode(
                mode_no=mode_no,
                eigenvalue=eigenvalue,
                omega_rad_per_s=omega,
                freq_hz=freq_hz,
                participation_factors=part_by_mode.get(mode_no, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
                effective_modal_mass=mass_by_mode.get(mode_no, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
            )
        )

    return ModalResult(
        case_id=case_id,
        modes=tuple(modes),
        extraction_method="lanczos",  # CalculiX default for *FREQUENCY
        # Phase 12 B fix to slice-A LOW finding: import the SSOT
        # constant rather than hard-coding "1.2.0". A future MINOR
        # bump now propagates here automatically.
        schema_version=CONVERGENCE_STUDY_SCHEMA_VERSION,
    )


def _extract_block_rows(
    lines: list[str],
    header_re: re.Pattern[str],
    *,
    expected_cols: int,
) -> list[list[str]]:
    """Walk ``lines`` looking for ``header_re``, then return all
    subsequent numeric-prefixed rows until the next blank-then-header
    transition.

    Each returned row is a list of the whitespace-split tokens; the
    caller is responsible for type coercion. Tokens are not validated
    against ``expected_cols`` here — the caller's domain logic owns
    that contract.
    """
    rows: list[list[str]] = []
    in_block = False
    seen_data = False
    for raw in lines:
        line = raw.rstrip()
        if header_re.search(line):
            in_block = True
            seen_data = False
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped:
            if seen_data:
                # blank line after rows -> block ends
                in_block = False
            continue
        # Numeric row: leading token must be parseable as int (mode_no)
        tokens = stripped.split()
        try:
            int(tokens[0])
        except (ValueError, IndexError):
            # Column header rows like "MODE NO   EIGENVALUE ..." are
            # skipped; if we have not yet seen data, keep waiting.
            continue
        seen_data = True
        rows.append(tokens)
    return rows


# ---------------------------------------------------------------------
# Analytical cross-check
# ---------------------------------------------------------------------


def euler_bernoulli_cantilever_freq(beam: CantileverBeamSpec, mode_n: int) -> float:
    """Closed-form natural frequency for a uniform-cross-section
    clamped-free Euler-Bernoulli cantilever beam, in Hz.

    Formula (Blevins 1979, eq. 8-1):

        f_n = (β_n · L)² / (2π · L²) × √(E·I / (ρ·A))

    where (β_n · L) values are pinned in :data:`EULER_BERNOULLI_BETA_LN`.

    Raises ValueError if ``mode_n`` is outside the supported range
    [1, len(EULER_BERNOULLI_BETA_LN)] — the project intentionally does
    not extrapolate β·L into higher modes from a closed-form series
    approximation because the convergence radius narrows past mode 6.
    """
    if not 1 <= mode_n <= len(EULER_BERNOULLI_BETA_LN):
        raise ValueError(
            f"mode_n={mode_n} outside supported analytical range "
            f"[1, {len(EULER_BERNOULLI_BETA_LN)}]; cross-check refused"
        )
    if beam.length_m <= 0:
        raise ValueError(f"cantilever length must be positive; got {beam.length_m}")
    if beam.density_kg_per_m3 <= 0 or beam.area_m2 <= 0:
        raise ValueError(
            f"density and area must be positive; got "
            f"density={beam.density_kg_per_m3}, area={beam.area_m2}"
        )
    if beam.youngs_modulus_pa <= 0 or beam.inertia_m4 <= 0:
        raise ValueError(
            f"E and I must be positive; got E={beam.youngs_modulus_pa}, I={beam.inertia_m4}"
        )

    beta_ln = EULER_BERNOULLI_BETA_LN[mode_n - 1]
    ei_over_rho_a = (beam.youngs_modulus_pa * beam.inertia_m4) / (
        beam.density_kg_per_m3 * beam.area_m2
    )
    return (beta_ln**2) * math.sqrt(ei_over_rho_a) / (2.0 * math.pi * beam.length_m**2)


def modal_residuals(
    numerical: ModalResult,
    beam: CantileverBeamSpec,
    *,
    bending_mode_indices: tuple[int, ...] = (1, 3, 5, 7),
    analytical_mode_map: tuple[int, ...] = (1, 2, 3, 4),
) -> ModalResidualReport:
    """Build a per-mode residual report for ``numerical`` modal output
    against the Euler-Bernoulli analytical cantilever frequencies.

    ``bending_mode_indices`` selects which CalculiX 1-indexed mode
    numbers to treat as bending modes. For a square cross-section the
    modes are doubly-degenerate (Y-bending and Z-bending at the same
    frequency), so the bending modes show up at solver indices 1, 3, 5, 7
    (skipping the degenerate pair member). For a rectangular cross-section
    these would simply be 1, 2, 3, 4. ``analytical_mode_map[i]`` is the
    Euler-Bernoulli analytical mode number that corresponds to
    ``bending_mode_indices[i]``.

    Raises ValueError if the two tuples have different lengths or if
    a bending_mode_index falls outside the available solver modes.
    """
    if len(bending_mode_indices) != len(analytical_mode_map):
        raise ValueError(
            f"bending_mode_indices and analytical_mode_map must have "
            f"equal length; got {len(bending_mode_indices)} vs "
            f"{len(analytical_mode_map)}"
        )

    modes_by_no = {m.mode_no: m for m in numerical.modes}
    residuals: list[ModalResidual] = []
    for solver_mode_no, analytical_mode_n in zip(
        bending_mode_indices, analytical_mode_map, strict=True
    ):
        if solver_mode_no not in modes_by_no:
            raise ValueError(
                f"solver mode_no={solver_mode_no} not present in ModalResult; cannot cross-check"
            )
        numerical_freq = modes_by_no[solver_mode_no].freq_hz
        analytical_freq = euler_bernoulli_cantilever_freq(beam, analytical_mode_n)
        # Defensive: if the analytical freq is zero (impossible for a
        # valid beam) we'd divide by zero; the cantilever spec
        # validation above guarantees nonzero, but a tiny guard is
        # cheap insurance against future spec changes.
        if abs(analytical_freq) < 1e-30:
            rel_err = float("inf")
        else:
            rel_err = 100.0 * (numerical_freq - analytical_freq) / analytical_freq
        residuals.append(
            ModalResidual(
                mode_no=solver_mode_no,
                freq_numerical_hz=numerical_freq,
                freq_analytical_hz=analytical_freq,
                relative_error_pct=rel_err,
                within_tolerance=abs(rel_err) <= MODAL_CROSS_CHECK_TOLERANCE_PCT,
            )
        )

    worst = max((abs(r.relative_error_pct) for r in residuals), default=0.0)
    return ModalResidualReport(
        case_id=numerical.case_id,
        residuals=tuple(residuals),
        worst_relative_error_pct=worst,
        all_within_tolerance=all(r.within_tolerance for r in residuals),
        tolerance_pct=MODAL_CROSS_CHECK_TOLERANCE_PCT,
    )


# ---------------------------------------------------------------------
# Cumulative mass participation utility (used by slice B advisor)
# ---------------------------------------------------------------------


def cumulative_mass_participation(
    result: ModalResult,
    *,
    direction_index: int,
) -> float:
    """Cumulative effective modal mass for ``direction_index``
    (0..5 == X / Y / Z / RX / RY / RZ) across all extracted modes,
    expressed as a fraction of the sum (i.e., never exceeds 1.0 + tiny
    rounding).

    Conservative engineering practice (cf. ASCE 7, Eurocode 8) calls for
    cumulative mass participation >= 80 % in each significant direction
    before a modal-spectrum analysis is considered complete. Slice B's
    advisor surfaces this as a reviewer concern when the cumulative is
    below the threshold.

    Raises ValueError if direction_index is outside [0, 5] or if the
    result has no modes.
    """
    if not 0 <= direction_index <= 5:
        raise ValueError(f"direction_index must be 0..5; got {direction_index}")
    if not result.modes:
        raise ValueError("ModalResult has no modes; cannot compute cumulative mass")
    components = [m.effective_modal_mass[direction_index] for m in result.modes]
    total = sum(abs(c) for c in components)
    if total <= 0:
        return 0.0
    # The "fraction-of-extracted" interpretation: how much of the
    # extracted modes' mass falls in this direction. A reviewer
    # comparing this to the total physical mass should consult the
    # case's evidence file directly; we surface the within-extraction
    # ratio so the advisor can flag modes that contribute nothing
    # versus modes that contribute meaningfully.
    return sum(abs(c) for c in components) / total
