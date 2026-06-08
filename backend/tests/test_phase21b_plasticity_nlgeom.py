"""FM-04a Phase 21 B — plasticity NLGEOM `requires_solver` E2E pin.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Phase 20 B shipped the ``*PLASTIC`` keyword + bilinear hardening curves
for steel-s355 and aluminium-6061-t6. The Phase 20 retro flagged a real
gap: no @pytest.mark.requires_solver test verified that ccx ACTUALLY
solves the nonlinear problem under a yielding load — the keyword was
emitted but no real-solver E2E confirmed it engaged the hardening table.

This test closes that gap. The flow:

1. Compose a single-C3D8 hex coupon (100 mm cube of steel-s355) with
   the SSOT material library's bilinear curve [0.0 → 355 MPa, 0.2 →
   510 MPa] and ``*STEP, NLGEOM, INC=20`` so ccx promotes to a
   nonlinear incremental run.
2. Apply a tensile load > σ_y · A (i.e., 4.0 MN over 0.01 m² gives
   σ_applied = 400 MPa — above yield, well below ultimate).
3. Solve with real ccx.
4. Read max σ_xx from the .frd; assert σ_y ≤ |observed| ≤ σ_u · 1.10
   (proves the plastic branch fired AND ccx is using the hardening
   table, not the elastic extrapolation that would land at 400 MPa
   AND not blowing past the ultimate stress).
5. Compose a SECOND coupon — identical geometry + load but with
   plasticity DISABLED (no *PLASTIC block). Run elastic-only ccx.
   Assert the plastic run's displacement is materially larger than
   the elastic run's (the bilinear curve at 400 MPa predicts ~5.8%
   plastic strain ⇒ ~20× more tip displacement for a 100 mm coupon).

The second coupon is the anti-gaming guard: without it, a future bug
that silently drops the *PLASTIC emission would leave the observed σ
within [σ_y, σ_u] (linear-elastic happens to land at 400 MPa for our
load), and the first assertion alone would not catch it.

References:
* CalculiX User Manual, §6.41 ``*PLASTIC`` keyword
* CalculiX User Manual, §6.32 ``*STEP`` and ``NLGEOM`` parameter
* EN 1993-1-5 Annex C §C.6 (S355 bilinear hardening approximation)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.materials import get_material


_DEFAULT_CCX_BINARY = "/opt/homebrew/bin/ccx"


def _write_c3d8_plasticity_inp(
    case_dir: Path,
    *,
    jobname: str,
    edge_length_m: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    plastic_hardening_curve: tuple[tuple[float, float], ...] | None,
    top_face_load_n: float,
    nlgeom: bool,
    inc: int,
) -> Path:
    """Compose a single-C3D8 hex INP with optional *PLASTIC + NLGEOM.

    Geometry: unit cube of side ``edge_length_m`` aligned to the
    coordinate axes, bottom face (z=0) clamped, top face (z=L) loaded
    with a uniform z-direction nodal force totalling ``top_face_load_n``.

    Args:
        plastic_hardening_curve: optional bilinear/piecewise-linear
            curve as ``((plastic_strain, stress_pa), ...)``. If None,
            no *PLASTIC block is emitted (elastic-only run).
        nlgeom: if True, *STEP carries NLGEOM (large-deformation
            kinematics). Phase 21 B uses True for plastic runs.
        inc: max increments allowed inside the step. Plastic runs need
            ≥10 increments for the bilinear curve to actually engage.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case_dir {case_dir!s} must exist")
    if edge_length_m <= 0:
        raise ValueError(f"edge_length_m must be positive; got {edge_length_m}")

    nodes = (
        (1, 0.0, 0.0, 0.0),
        (2, edge_length_m, 0.0, 0.0),
        (3, edge_length_m, edge_length_m, 0.0),
        (4, 0.0, edge_length_m, 0.0),
        (5, 0.0, 0.0, edge_length_m),
        (6, edge_length_m, 0.0, edge_length_m),
        (7, edge_length_m, edge_length_m, edge_length_m),
        (8, 0.0, edge_length_m, edge_length_m),
    )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 21 B plasticity coupon ({jobname}; nlgeom={nlgeom})")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    lines.append("1, 1, 2, 3, 4, 5, 6, 7, 8")
    lines.append("*MATERIAL, NAME=STEEL_S355")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6f}")
    if plastic_hardening_curve is not None:
        lines.append("*PLASTIC")
        for plastic_strain, stress_pa in plastic_hardening_curve:
            lines.append(f"{stress_pa:.6e}, {plastic_strain:.6f}")
    lines.append("*SOLID SECTION, ELSET=EALL, MATERIAL=STEEL_S355")
    # Statically-determinate BCs that produce a UNIFORM σ_zz response
    # so the bilinear-plasticity check measures the BULK behaviour, not
    # corner stress concentrations from over-constraint:
    #   * z=0 face (nodes 1-4): fix DOF 3 (z) — reaction face
    #   * Node 1 (origin): also fix DOF 1 (x) + DOF 2 (y) → blocks x/y
    #     translation
    #   * Node 2 (L,0,0): also fix DOF 2 (y) → blocks z-axis rotation
    # Total = 4 (z) + 2 (xy at origin) + 1 (y at 2) = 7 DOFs constrained
    # (1 redundant by symmetry of the bottom face). All 6 rigid body
    # modes removed; lateral faces free for Poisson contraction.
    lines.append("*BOUNDARY")
    for nid in (1, 2, 3, 4):
        lines.append(f"{nid}, 3, 3, 0.0")
    lines.append("1, 1, 2, 0.0")
    lines.append("2, 2, 2, 0.0")
    # Step: NLGEOM + INC=N for the plastic run; default linear for
    # elastic-only.
    step_header = "*STEP"
    if nlgeom:
        step_header += f", NLGEOM, INC={inc}"
    lines.append(step_header)
    if nlgeom:
        # initial_inc, total_step_time, min_inc, max_inc
        lines.append("*STATIC")
        lines.append("0.05, 1.0, 1e-5, 0.2")
    else:
        lines.append("*STATIC")
    lines.append("*CLOAD")
    load_per_node = top_face_load_n / 4.0
    for nid in (5, 6, 7, 8):
        lines.append(f"{nid}, 3, {load_per_node:.6f}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


# ---------------------------------------------------------------------
# Pre-flight: SSOT carries the expected bilinear curve
# ---------------------------------------------------------------------


def test_steel_s355_carries_bilinear_curve_from_library() -> None:
    """The material's `plastic_hardening_curve` must match the EN
    1993-1-5 Annex C.6 bilinear approximation: 355 MPa @ 0% → 510 MPa
    @ 20%. A drive-by curve edit would trip this test BEFORE the E2E
    runner pin even gets a chance to fire."""
    mat = get_material("steel-s355")
    assert mat.yield_stress_pa == 355e6
    assert mat.ultimate_stress_pa == 510e6
    curve = mat.plastic_hardening_curve
    assert curve is not None
    assert curve == ((0.0, 355e6), (0.2, 510e6))


def test_aluminium_6061_t6_carries_bilinear_curve() -> None:
    mat = get_material("aluminium-6061-t6")
    curve = mat.plastic_hardening_curve
    assert curve is not None
    # MMPDS-2023 §9.2 bilinear approximation.
    assert curve[0][0] == 0.0
    assert curve[0][1] == pytest.approx(276e6, rel=1e-9)


# ---------------------------------------------------------------------
# INP composer — sanity-check NLGEOM + *PLASTIC emit correctly
# ---------------------------------------------------------------------


def test_inp_writer_emits_plastic_and_nlgeom_when_requested(
    tmp_path: Path,
) -> None:
    """The Phase 21 B composer must include both *PLASTIC and
    *STEP, NLGEOM, INC=20 when plastic curve + nlgeom are passed.
    Without these directives ccx would solve the problem linearly
    and the assertion that plastic strain develops would silently pass
    on a broken composer."""
    path = _write_c3d8_plasticity_inp(
        tmp_path,
        jobname="plastic_emit",
        edge_length_m=0.1,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.3,
        plastic_hardening_curve=((0.0, 355e6), (0.2, 510e6)),
        top_face_load_n=4.0e6,
        nlgeom=True,
        inc=20,
    )
    body = path.read_text(encoding="utf-8")
    assert "*PLASTIC" in body
    assert "*STEP, NLGEOM, INC=20" in body
    # First curve row: 355 MPa @ 0% plastic strain.
    assert "3.550000e+08, 0.000000" in body
    # Second curve row: 510 MPa @ 20% plastic strain.
    assert "5.100000e+08, 0.200000" in body


def test_inp_writer_omits_plastic_for_elastic_only_path(
    tmp_path: Path,
) -> None:
    """Anti-gaming guard: when plastic_hardening_curve is None, the
    INP must NOT carry a *PLASTIC block (and the *STEP stays linear
    without NLGEOM). This makes the elastic-only run a proper baseline
    against the plastic run."""
    path = _write_c3d8_plasticity_inp(
        tmp_path,
        jobname="elastic_only",
        edge_length_m=0.1,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.3,
        plastic_hardening_curve=None,
        top_face_load_n=4.0e6,
        nlgeom=False,
        inc=1,
    )
    body = path.read_text(encoding="utf-8")
    assert "*PLASTIC" not in body
    assert "NLGEOM" not in body


# =====================================================================
# T:-3 — requires_solver E2E pin (real ccx)
# =====================================================================


@pytest.mark.requires_solver
def test_real_ccx_engages_bilinear_plasticity_above_yield(
    tmp_path: Path,
) -> None:
    """The load-bearing Phase 21 B pin. Real ccx solves a steel-s355
    100 mm cube under a 4 MN tensile load (σ_applied = 400 MPa, ABOVE
    yield σ_y = 355 MPa, BELOW ultimate σ_u = 510 MPa). The *PLASTIC
    block + NLGEOM step must yield observed σ ∈ [σ_y, σ_u · 1.10].

    Anti-gaming sanity check: re-runs the SAME load on the SAME
    geometry WITHOUT the plastic curve (elastic-only). The plastic
    run's tip displacement must be substantially larger (≥3× per
    Phase 21 B target; the bilinear curve at 400 MPa predicts ~5.8%
    plastic strain on top of the ~0.2% elastic strain → ~30× extra
    displacement at this load level — we assert ≥3× to keep the
    pin robust to ccx convergence-step variations)."""
    from app.adapters.calculix import (
        CalculiXReader,
        CalculiXRunError,
        CalculiXRunner,
    )
    from app.core.types import CanonicalField, UnitSystem

    mat = get_material("steel-s355")
    assert mat.plastic_hardening_curve is not None
    edge_m = 0.1
    cross_section_m2 = edge_m * edge_m  # 0.01 m²
    applied_load_n = 4.0e6  # 4 MN → σ_applied = 400 MPa
    assert applied_load_n / cross_section_m2 > mat.yield_stress_pa
    assert applied_load_n / cross_section_m2 < mat.ultimate_stress_pa

    # --- Plastic run ---
    plastic_dir = tmp_path / "plastic-coupon-candidate"
    plastic_dir.mkdir()
    _write_c3d8_plasticity_inp(
        plastic_dir,
        jobname="plastic_run",
        edge_length_m=edge_m,
        youngs_modulus_pa=mat.youngs_modulus_pa,
        poisson_ratio=mat.poisson_ratio,
        plastic_hardening_curve=mat.plastic_hardening_curve,
        top_face_load_n=applied_load_n,
        nlgeom=True,
        inc=20,
    )
    plastic_ccx = CalculiXRunner(
        ccx_binary=_DEFAULT_CCX_BINARY, timeout_sec=180.0
    )
    try:
        plastic_result = plastic_ccx.run(plastic_dir, "plastic_run")
    except CalculiXRunError as exc:
        pytest.fail(f"plastic ccx run failed: {exc}")
    assert plastic_result.returncode == 0
    assert plastic_result.frd_path is not None

    p_reader = CalculiXReader(
        plastic_result.frd_path, unit_system=UnitSystem.SI
    )
    # NLGEOM ccx writes one FRD block per converged increment. The
    # reader's `solution_states` lists them; we read the LAST (the
    # converged final state at 100% applied load), not step_id=1 which
    # is the first 5% sub-increment.
    p_states = p_reader.solution_states
    assert len(p_states) >= 2, (
        f"plastic NLGEOM run produced {len(p_states)} solution state(s); "
        f"expected ≥2 sub-increments. If 1, the NLGEOM step likely "
        f"didn't engage — check *STEP, NLGEOM, INC directive"
    )
    p_final_step_id = p_states[-1].step_id
    p_stress = p_reader.get_field(
        CanonicalField.STRESS_TENSOR, step_id=p_final_step_id
    )
    assert p_stress is not None
    p_sigma_zz = p_stress.at_nodes()[:, 2]
    p_sigma_zz_max = float(abs(p_sigma_zz).max())
    assert p_sigma_zz_max >= mat.yield_stress_pa, (
        f"plastic run did NOT reach yield ({p_sigma_zz_max:.3e} Pa "
        f"< {mat.yield_stress_pa:.3e} Pa); *PLASTIC block may not be "
        f"engaging — verify *STEP carries NLGEOM"
    )
    # Hardening curve caps σ around the ultimate. Allow 10% headroom
    # for nodal extrapolation noise + ccx's internal Voigt-stress
    # post-processing.
    assert p_sigma_zz_max <= mat.ultimate_stress_pa * 1.10, (
        f"plastic run blew past hardening curve ({p_sigma_zz_max:.3e} "
        f"Pa > {mat.ultimate_stress_pa * 1.10:.3e} Pa); *PLASTIC "
        f"table may not be loaded — verify curve rows in INP"
    )

    p_disp = p_reader.get_field(
        CanonicalField.DISPLACEMENT, step_id=p_final_step_id
    )
    assert p_disp is not None
    p_uz_top = float(abs(p_disp.at_nodes()[:, 2]).max())

    # --- Elastic-only run (anti-gaming reference) ---
    elastic_dir = tmp_path / "elastic-coupon-candidate"
    elastic_dir.mkdir()
    _write_c3d8_plasticity_inp(
        elastic_dir,
        jobname="elastic_run",
        edge_length_m=edge_m,
        youngs_modulus_pa=mat.youngs_modulus_pa,
        poisson_ratio=mat.poisson_ratio,
        plastic_hardening_curve=None,  # ← no plasticity
        top_face_load_n=applied_load_n,
        nlgeom=False,
        inc=1,
    )
    elastic_ccx = CalculiXRunner(
        ccx_binary=_DEFAULT_CCX_BINARY, timeout_sec=60.0
    )
    try:
        elastic_result = elastic_ccx.run(elastic_dir, "elastic_run")
    except CalculiXRunError as exc:
        pytest.fail(f"elastic ccx run failed: {exc}")
    assert elastic_result.returncode == 0
    assert elastic_result.frd_path is not None

    e_reader = CalculiXReader(
        elastic_result.frd_path, unit_system=UnitSystem.SI
    )
    e_disp = e_reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    assert e_disp is not None
    e_uz_top = float(abs(e_disp.at_nodes()[:, 2]).max())
    assert e_uz_top > 0, "elastic run displacement is zero — model unloaded?"

    # The honest assertion: plastic deformation is materially larger
    # than the elastic-only baseline. ε_plastic ≈ (400-355)/(510-355) ·
    # 0.20 ≈ 5.8% on top of ε_elastic ≈ 0.19% → ratio ≈ (5.8 + 0.19)/
    # 0.19 ≈ 31×. Asserting ≥3× keeps this robust to ccx convergence-
    # step variation and any nodal-extrapolation differences.
    ratio = p_uz_top / e_uz_top
    assert ratio >= 3.0, (
        f"plastic displacement {p_uz_top:.3e} m only {ratio:.2f}× "
        f"elastic {e_uz_top:.3e} m; expected ≥3× — *PLASTIC block "
        f"may not be engaging"
    )
