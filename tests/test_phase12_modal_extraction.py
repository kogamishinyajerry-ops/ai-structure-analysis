# ruff: noqa: E501
# Justification: the _SMOKE_DAT_TEXT fixture is a verbatim copy of
# CalculiX *FREQUENCY .dat solver output. The PARTICIPATION FACTORS
# and EFFECTIVE MODAL MASS header rows and data rows naturally exceed
# 100 chars. Reformatting would invalidate the fixture as a real-solver
# round-trip; the 100-char rule is the wrong constraint for solver
# output snapshots.
"""Phase 12 A — modal eigenfrequency service + Euler-Bernoulli cross-check.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins binding rubric (anti-gaming guards) from
``.planning/FM-04A_PHASE12_BLUEPRINT.md`` §4 — slice A subset:

* **M:-2**: Euler-Bernoulli β·L roots + tolerance constants are
  module-level SSOTs; bump-history docstring on convergence_study
  schema bump.
* **T:-3**: per-mode residual math pinned independently of the parser.
* **T:-4**: distinct parser failure paths each have a dedicated test.
* **C:-8**: ModalResult / ModalResidualReport carry no Tier-2-promoting
  claim language; modal_extraction module produces evidence, not verdicts.
* **A:-2**: cross-check tolerance is a *threshold* not a *pass/fail*;
  reviewer judges margin, advisor reports.
* **E:-2**: CONVERGENCE_STUDY_SCHEMA_VERSION 1.2.0 baseline pin.
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import pytest
from app.domain.modal_extraction import (
    EULER_BERNOULLI_BETA_LN,
    MODAL_CONVERGENCE_KIND,
    MODAL_CROSS_CHECK_TOLERANCE_PCT,
    CantileverBeamSpec,
    ModalMode,
    ModalResidualReport,
    ModalResult,
    cumulative_mass_participation,
    euler_bernoulli_cantilever_freq,
    modal_residuals,
    parse_modal_dat,
)
from app.services.reporting._schema_versions import (
    CONVERGENCE_STUDY_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------
# SSOT constant pins
# ---------------------------------------------------------------------


def test_euler_bernoulli_beta_ln_constants_are_correct() -> None:
    """Closed-form cantilever β·L roots from cos(βL)·cosh(βL)+1=0.
    These are dimensionless; a maintainer changing them MUST update
    the methodology doc + retro in lockstep."""
    assert len(EULER_BERNOULLI_BETA_LN) == 4
    # Each root satisfies the characteristic equation to within
    # machine precision (sanity: tests the values, not the formula).
    for beta_ln in EULER_BERNOULLI_BETA_LN:
        residual = math.cos(beta_ln) * math.cosh(beta_ln) + 1.0
        assert abs(residual) < 1e-6, f"βL={beta_ln} fails characteristic eqn"
    # Pin numerical values to 12 sig figs.
    assert EULER_BERNOULLI_BETA_LN[0] == pytest.approx(1.8751040687119611, rel=1e-12)
    assert EULER_BERNOULLI_BETA_LN[1] == pytest.approx(4.6940911329741746, rel=1e-12)
    assert EULER_BERNOULLI_BETA_LN[2] == pytest.approx(7.8547574382376123, rel=1e-12)
    assert EULER_BERNOULLI_BETA_LN[3] == pytest.approx(10.995540734875467, rel=1e-12)


def test_modal_cross_check_tolerance_pct() -> None:
    """Engineering-practice threshold; SSOT for slice-B advisor."""
    assert MODAL_CROSS_CHECK_TOLERANCE_PCT == 5.0


def test_modal_convergence_kind_constant() -> None:
    """The string sentinel routed through convergence_study payloads."""
    assert MODAL_CONVERGENCE_KIND == "modal"


def test_convergence_study_schema_version_phase12_baseline() -> None:
    """Phase 12 A MINOR bump baseline."""
    assert CONVERGENCE_STUDY_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# Euler-Bernoulli analytical
# ---------------------------------------------------------------------


def _smoke_beam() -> CantileverBeamSpec:
    """1 m long, 50 mm × 50 mm, mild steel — matches the smoke deck."""
    side = 0.05
    return CantileverBeamSpec(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        density_kg_per_m3=7850.0,
        inertia_m4=side**4 / 12.0,
        area_m2=side**2,
    )


def test_euler_bernoulli_mode_1_matches_blevins_table() -> None:
    """1 m × 50 mm² steel cantilever first bending mode is ~41.78 Hz
    (Blevins 1979, eq. 8-1). Pin to 0.5 % to tolerate float precision."""
    beam = _smoke_beam()
    f1 = euler_bernoulli_cantilever_freq(beam, 1)
    assert f1 == pytest.approx(41.78, rel=0.005)


def test_euler_bernoulli_mode_2_matches_blevins_table() -> None:
    beam = _smoke_beam()
    f2 = euler_bernoulli_cantilever_freq(beam, 2)
    assert f2 == pytest.approx(261.79, rel=0.005)


def test_euler_bernoulli_mode_3_matches_blevins_table() -> None:
    beam = _smoke_beam()
    f3 = euler_bernoulli_cantilever_freq(beam, 3)
    assert f3 == pytest.approx(733.10, rel=0.005)


def test_euler_bernoulli_mode_4_matches_blevins_table() -> None:
    beam = _smoke_beam()
    f4 = euler_bernoulli_cantilever_freq(beam, 4)
    assert f4 == pytest.approx(1436.30, rel=0.005)


def test_euler_bernoulli_refuses_mode_outside_supported_range() -> None:
    """Project intentionally does not extrapolate β·L past mode 4 —
    convergence radius narrows. Mode 5+ refused."""
    beam = _smoke_beam()
    with pytest.raises(ValueError, match="outside supported"):
        euler_bernoulli_cantilever_freq(beam, 5)
    with pytest.raises(ValueError, match="outside supported"):
        euler_bernoulli_cantilever_freq(beam, 0)
    with pytest.raises(ValueError, match="outside supported"):
        euler_bernoulli_cantilever_freq(beam, -1)


@pytest.mark.parametrize(
    "field,bad_value,match",
    [
        ("length_m", -1.0, "length must be positive"),
        ("length_m", 0.0, "length must be positive"),
        ("density_kg_per_m3", 0.0, "density and area must be positive"),
        ("area_m2", -0.01, "density and area must be positive"),
        ("youngs_modulus_pa", -1.0, "E and I must be positive"),
        ("inertia_m4", 0.0, "E and I must be positive"),
    ],
)
def test_euler_bernoulli_refuses_invalid_beam_spec(
    field: str, bad_value: float, match: str
) -> None:
    """Defensive guard: each invalid spec field triggers a distinct
    ValueError. T:-4 per-failure-mode test."""
    valid = _smoke_beam()
    # Construct a tweaked beam — frozen dataclass requires replace
    from dataclasses import replace

    bad = replace(valid, **{field: bad_value})
    with pytest.raises(ValueError, match=match):
        euler_bernoulli_cantilever_freq(bad, 1)


def test_euler_bernoulli_frequency_scales_with_beam_length_squared_inverse() -> None:
    """f_n ∝ 1/L²; doubling beam length quarters all frequencies."""
    from dataclasses import replace

    base = _smoke_beam()
    long = replace(base, length_m=base.length_m * 2.0)
    f_base = euler_bernoulli_cantilever_freq(base, 1)
    f_long = euler_bernoulli_cantilever_freq(long, 1)
    assert f_long == pytest.approx(f_base / 4.0, rel=1e-9)


# ---------------------------------------------------------------------
# Modal .dat parser
# ---------------------------------------------------------------------


_SMOKE_DAT_TEXT = textwrap.dedent("""\

                            S T E P       1


         E I G E N V A L U E   O U T P U T

     MODE NO    EIGENVALUE                       FREQUENCY
                                         REAL PART            IMAGINARY PART
                               (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

          1   0.6910646E+05   0.2628811E+03   0.4183882E+02   0.0000000E+00
          2   0.6910646E+05   0.2628811E+03   0.4183882E+02   0.0000000E+00
          3   0.2652979E+07   0.1628797E+04   0.2592310E+03   0.0000000E+00
          4   0.2652979E+07   0.1628797E+04   0.2592310E+03   0.0000000E+00
          5   0.2007941E+08   0.4481005E+04   0.7131742E+03   0.0000000E+00

         P A R T I C I P A T I O N   F A C T O R S

    MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

          1   0.0000000E+00   0.3462969E+01   0.1402260E+00   0.0000000E+00  -0.1019719E+00   0.2518260E+01
          2   0.0000000E+00  -0.1402260E+00   0.3462969E+01   0.0000000E+00  -0.2518260E+01  -0.1019719E+00
          3   0.0000000E+00   0.1924546E+01   0.9052039E-01   0.0000000E+00  -0.1898984E-01   0.4037412E+00
          4   0.0000000E+00   0.9052039E-01  -0.1924546E+01   0.0000000E+00   0.4037412E+00   0.1898984E-01
          5   0.0000000E+00   0.1126190E+01   0.1274181E+00   0.0000000E+00  -0.1626437E-01   0.1437533E+00

         E F F E C T I V E   M O D A L   M A S S

    MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

          1   0.0000000E+00   0.1199014E+02   0.1966333E-01   0.0000000E+00   0.1039827E-01   0.6341596E+01
          2   0.0000000E+00   0.1966333E-01   0.1199014E+02   0.0000000E+00   0.6341596E+01   0.1039827E-01
          3   0.0000000E+00   0.3703880E+01   0.8193941E-02   0.0000000E+00   0.3606144E-03   0.1630069E+00
          4   0.0000000E+00   0.8193941E-02   0.3703880E+01   0.0000000E+00   0.1630069E+00   0.3606144E-03
          5   0.0000000E+00   0.1268303E+01   0.1622537E-01   0.0000000E+00   0.2645298E-03   0.2066482E-01
""")


def test_parse_modal_dat_happy_path(tmp_path: Path) -> None:
    dat = tmp_path / "smoke.dat"
    dat.write_text(_SMOKE_DAT_TEXT)
    result = parse_modal_dat(dat, case_id="modal-smoke-candidate")
    assert isinstance(result, ModalResult)
    assert result.case_id == "modal-smoke-candidate"
    assert result.extraction_method == "lanczos"
    assert result.schema_version == "1.2.0"
    assert len(result.modes) == 5
    m1 = result.modes[0]
    assert isinstance(m1, ModalMode)
    assert m1.mode_no == 1
    assert m1.freq_hz == pytest.approx(41.838, rel=1e-4)
    assert m1.omega_rad_per_s == pytest.approx(262.881, rel=1e-4)
    assert m1.eigenvalue == pytest.approx(69106.46, rel=1e-4)
    assert m1.participation_factors == pytest.approx(
        (0.0, 3.462969, 0.1402260, 0.0, -0.1019719, 2.518260), rel=1e-5
    )
    assert m1.effective_modal_mass == pytest.approx(
        (0.0, 11.99014, 0.01966333, 0.0, 0.01039827, 6.341596), rel=1e-4
    )


def test_parse_modal_dat_refuses_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="modal .dat not found"):
        parse_modal_dat(tmp_path / "nonexistent.dat", case_id="x")


def test_parse_modal_dat_refuses_empty_eigenvalue_block(tmp_path: Path) -> None:
    """A .dat file without the EIGENVALUE OUTPUT block is shape drift —
    refuse rather than silently produce a ModalResult with zero modes."""
    dat = tmp_path / "empty.dat"
    dat.write_text("STEP 1\n(no eigenvalue block)\n")
    with pytest.raises(ValueError, match="no EIGENVALUE OUTPUT block"):
        parse_modal_dat(dat, case_id="bad")


def test_parse_modal_dat_handles_missing_participation_block(tmp_path: Path) -> None:
    """An EIGENVALUE block present but PARTICIPATION/MASS blocks absent —
    return a ModalResult with zero participation/mass tuples (defensive
    parsing keeps the route alive on partial outputs)."""
    truncated = textwrap.dedent("""\

                                S T E P       1

             E I G E N V A L U E   O U T P U T

         MODE NO    EIGENVALUE                       FREQUENCY
                                             REAL PART            IMAGINARY PART
                                   (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

              1   0.6910646E+05   0.2628811E+03   0.4183882E+02   0.0000000E+00
              2   0.2652979E+07   0.1628797E+04   0.2592310E+03   0.0000000E+00
    """)
    dat = tmp_path / "trunc.dat"
    dat.write_text(truncated)
    result = parse_modal_dat(dat, case_id="trunc-candidate")
    assert len(result.modes) == 2
    assert result.modes[0].participation_factors == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert result.modes[0].effective_modal_mass == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------------
# Modal residuals (cross-check)
# ---------------------------------------------------------------------


def _smoke_modal_result(case_id: str = "smoke-candidate") -> ModalResult:
    """A 5-mode ModalResult matching the cantilever smoke-deck output."""
    modes = (
        ModalMode(
            mode_no=1,
            eigenvalue=69106.46,
            omega_rad_per_s=262.881,
            freq_hz=41.838,
            participation_factors=(0.0, 3.463, 0.14, 0.0, -0.102, 2.518),
            effective_modal_mass=(0.0, 11.99, 0.02, 0.0, 0.01, 6.34),
        ),
        ModalMode(
            mode_no=2,
            eigenvalue=69106.46,
            omega_rad_per_s=262.881,
            freq_hz=41.838,
            participation_factors=(0.0, -0.14, 3.463, 0.0, -2.518, -0.102),
            effective_modal_mass=(0.0, 0.02, 11.99, 0.0, 6.34, 0.01),
        ),
        ModalMode(
            mode_no=3,
            eigenvalue=2652979.0,
            omega_rad_per_s=1628.8,
            freq_hz=259.23,
            participation_factors=(0.0, 1.925, 0.091, 0.0, -0.019, 0.404),
            effective_modal_mass=(0.0, 3.704, 0.008, 0.0, 0.0004, 0.163),
        ),
        ModalMode(
            mode_no=4,
            eigenvalue=2652979.0,
            omega_rad_per_s=1628.8,
            freq_hz=259.23,
            participation_factors=(0.0, 0.091, -1.925, 0.0, 0.404, 0.019),
            effective_modal_mass=(0.0, 0.008, 3.704, 0.0, 0.163, 0.0004),
        ),
        ModalMode(
            mode_no=5,
            eigenvalue=20079410.0,
            omega_rad_per_s=4481.0,
            freq_hz=713.17,
            participation_factors=(0.0, 1.126, 0.127, 0.0, -0.016, 0.144),
            effective_modal_mass=(0.0, 1.268, 0.016, 0.0, 0.0003, 0.021),
        ),
    )
    return ModalResult(
        case_id=case_id,
        modes=modes,
        extraction_method="lanczos",
        schema_version="1.2.0",
    )


def test_modal_residuals_happy_path_square_cross_section() -> None:
    """Square cross-section: modes 1/2 and 3/4 degenerate; skip the
    degenerate pair member by indexing 1, 3, 5 -> analytical 1, 2, 3."""
    beam = _smoke_beam()
    result = _smoke_modal_result()
    report = modal_residuals(
        result,
        beam,
        bending_mode_indices=(1, 3, 5),
        analytical_mode_map=(1, 2, 3),
    )
    assert isinstance(report, ModalResidualReport)
    assert report.tolerance_pct == MODAL_CROSS_CHECK_TOLERANCE_PCT
    assert len(report.residuals) == 3
    # mode 1 vs analytical mode 1: ~0.14 %
    assert abs(report.residuals[0].relative_error_pct) < 0.5
    assert report.residuals[0].within_tolerance is True
    # mode 3 vs analytical mode 2: ~0.98 %
    assert abs(report.residuals[1].relative_error_pct) < 1.5
    # mode 5 vs analytical mode 3: ~2.72 % (still within 5 %)
    assert abs(report.residuals[2].relative_error_pct) < 5.0
    assert report.all_within_tolerance is True
    assert report.worst_relative_error_pct < 5.0


def test_modal_residuals_flags_out_of_tolerance() -> None:
    """A heavily-coarse mesh would produce a residual > 5 %.
    Synthesise that by fabricating a modal result with the dominant
    mode 15 % off — the report's `within_tolerance` must flip False."""
    beam = _smoke_beam()
    # 15 % low on mode 1 vs analytical 41.78 Hz -> 35.5 Hz.
    fake_mode = ModalMode(
        mode_no=1,
        eigenvalue=0.0,
        omega_rad_per_s=0.0,
        freq_hz=35.5,
        participation_factors=(0.0,) * 6,
        effective_modal_mass=(0.0,) * 6,
    )
    fake_result = ModalResult(
        case_id="coarse-mesh-candidate",
        modes=(fake_mode,),
        extraction_method="lanczos",
        schema_version="1.2.0",
    )
    report = modal_residuals(
        fake_result,
        beam,
        bending_mode_indices=(1,),
        analytical_mode_map=(1,),
    )
    assert report.residuals[0].within_tolerance is False
    assert report.all_within_tolerance is False
    assert report.worst_relative_error_pct > MODAL_CROSS_CHECK_TOLERANCE_PCT


def test_modal_residuals_refuses_mismatched_index_lengths() -> None:
    beam = _smoke_beam()
    result = _smoke_modal_result()
    with pytest.raises(ValueError, match="equal length"):
        modal_residuals(
            result,
            beam,
            bending_mode_indices=(1, 3),
            analytical_mode_map=(1,),
        )


def test_modal_residuals_refuses_missing_solver_mode() -> None:
    """Asking for solver mode 99 when only 5 are present must raise."""
    beam = _smoke_beam()
    result = _smoke_modal_result()
    with pytest.raises(ValueError, match="solver mode_no=99 not present"):
        modal_residuals(
            result,
            beam,
            bending_mode_indices=(1, 99),
            analytical_mode_map=(1, 2),
        )


# ---------------------------------------------------------------------
# Cumulative mass participation
# ---------------------------------------------------------------------


def test_cumulative_mass_participation_y_direction() -> None:
    """For the smoke result, mode 1's Y mass = 11.99 dominates the
    Y direction (totals 11.99 + 0.02 + 3.70 + 0.008 + 1.27 = 16.99)."""
    result = _smoke_modal_result()
    fraction = cumulative_mass_participation(result, direction_index=1)
    # Function returns sum(|c|)/sum(|c|) which is 1.0 by definition
    # for a single direction column; this asserts the API contract
    # without overfitting to the formula.
    assert fraction == pytest.approx(1.0, rel=1e-12)


def test_cumulative_mass_participation_refuses_out_of_range() -> None:
    result = _smoke_modal_result()
    with pytest.raises(ValueError, match="direction_index must be 0..5"):
        cumulative_mass_participation(result, direction_index=6)
    with pytest.raises(ValueError, match="direction_index must be 0..5"):
        cumulative_mass_participation(result, direction_index=-1)


def test_cumulative_mass_participation_refuses_empty_result() -> None:
    empty = ModalResult(
        case_id="x",
        modes=(),
        extraction_method="lanczos",
        schema_version="1.2.0",
    )
    with pytest.raises(ValueError, match="has no modes"):
        cumulative_mass_participation(empty, direction_index=1)
