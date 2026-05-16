"""Read solve.frd, extract the SCL stress tensors, run the project's
Layer-3 stress linearization, and compare against Lame's analytical solution.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Writes:
  - results.json: machine-readable summary of every comparison.
  - results.txt:  human-readable Tier-1 candidate engineering report.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "backend"))

from app.domain.stress_derivatives import von_mises
from app.domain.stress_linearization import linearize_through_thickness
from app.parsers.frd_parser import FRDParser

# Problem constants (must mirror cylinder.geo + assemble_deck.py).
Ri = 100.0
Ro = 150.0
L = 100.0
THETA = math.radians(5.0)
P_INTERNAL = 10.0
SM_AT_TEMP = 138.0  # SA-516 Gr.70 design stress intensity, MPa.

K_FACTOR = Ri**2 / (Ro**2 - Ri**2)


# ---------------------------------------------------------------------
# Lame's analytical solution for closed-end thick-walled cylinder
# ---------------------------------------------------------------------


def lame(r: float) -> dict[str, float]:
    """Return analytical (sigma_r, sigma_theta, sigma_z) at radius r."""
    sigma_r = K_FACTOR * P_INTERNAL * (1.0 - (Ro / r) ** 2)
    sigma_t = K_FACTOR * P_INTERNAL * (1.0 + (Ro / r) ** 2)
    sigma_z = K_FACTOR * P_INTERNAL  # closed-end axial stress (uniform).
    return {"sigma_r": sigma_r, "sigma_theta": sigma_t, "sigma_z": sigma_z}


def lame_vm(r: float) -> float:
    """Von Mises stress from Lame at radius r (closed-end cylinder)."""
    s = lame(r)
    sr, st, sz = s["sigma_r"], s["sigma_theta"], s["sigma_z"]
    return math.sqrt(0.5 * ((sr - st) ** 2 + (st - sz) ** 2 + (sz - sr) ** 2))


# ---------------------------------------------------------------------
# Tensor rotation: ccx output is in global (X, Y, Z); we need cylindrical
# (r, theta, z) at each SCL point so we can compare apples to apples.
# ---------------------------------------------------------------------


def rotate_global_to_cyl(stress_xyz: np.ndarray, x: float, y: float) -> np.ndarray:
    """Rotate a 3x3 stress tensor from (X, Y, Z) into cylindrical (r, t, z).

    stress_xyz: shape (3, 3) in global Cartesian basis.
    (x, y): node coordinates used to derive the local angle.
    Returns 3x3 in (r, t, z) basis.
    """
    theta = math.atan2(y, x)
    c, s = math.cos(theta), math.sin(theta)
    R = np.array(
        [[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    return R @ stress_xyz @ R.T


def tensor_voigt_to_full(v: np.ndarray) -> np.ndarray:
    """CalculiX voigt order = [sxx, syy, szz, sxy, syz, szx]."""
    sxx, syy, szz, sxy, syz, szx = v
    return np.array(
        [[sxx, sxy, szx], [sxy, syy, syz], [szx, syz, szz]],
        dtype=np.float64,
    )


def tensor_full_to_voigt(M: np.ndarray) -> np.ndarray:
    """Inverse of tensor_voigt_to_full."""
    return np.array(
        [M[0, 0], M[1, 1], M[2, 2], M[0, 1], M[1, 2], M[0, 2]],
        dtype=np.float64,
    )


# ---------------------------------------------------------------------
# Pull SCL node IDs back out of solve.inp (we already wrote them there
# under NSET=SCL_LINE in inner-to-outer order).
# ---------------------------------------------------------------------


def read_scl_nodes(deck: Path) -> list[int]:
    out: list[int] = []
    in_block = False
    for raw in deck.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("*"):
            in_block = line.upper().startswith("*NSET,NSET=SCL_LINE")
            continue
        if in_block:
            for tok in line.replace(",", " ").split():
                if tok.isdigit():
                    out.append(int(tok))
    return out


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


def main() -> None:
    deck = HERE / "solve.inp"
    frd = HERE / "solve.frd"

    scl_ids = read_scl_nodes(deck)
    print(f"SCL line: {len(scl_ids)} nodes (NSET=SCL_LINE)")
    if len(scl_ids) < 5:
        raise RuntimeError("SCL has fewer than 5 nodes — re-check assembler.")

    parser = FRDParser()
    result = parser.parse(str(frd))
    print(f"Parsed FRD: {len(result.nodes)} nodes, {len(result.increments)} increment(s)")
    inc = result.increments[-1]
    # inc.stresses -> {node_id: FRDStress(S11..S23, von_mises, ...)}
    s_blocks: dict[int, tuple[float, float, float, float, float, float]] = {}
    for nid, fs in inc.stresses.items():
        # CalculiX FRD voigt order: SXX, SYY, SZZ, SXY, SYZ, SZX.
        s_blocks[nid] = (
            float(fs.S11),
            float(fs.S22),
            float(fs.S33),
            float(fs.S12),
            float(fs.S23),
            float(fs.S13),
        )
    print(f"Increment has stress data for {len(s_blocks)} nodes")
    if not s_blocks:
        raise RuntimeError("No stress data in increment; ccx did not write *EL FILE S.")

    # Gather coordinates + global-frame stress tensors at each SCL node
    # (already inner-to-outer ordered by assemble_deck.py).
    rows = []
    for nid in scl_ids:
        node = result.nodes[nid]
        x, y, z = node.coords
        r = math.hypot(x, y)
        v = np.array(s_blocks[nid], dtype=np.float64)  # (6,) in xyz voigt
        M_xyz = tensor_voigt_to_full(v)
        M_cyl = rotate_global_to_cyl(M_xyz, x, y)
        v_cyl = tensor_full_to_voigt(M_cyl)
        rows.append((r, v_cyl, lame(r)))
    rows.sort(key=lambda t: t[0])  # ascending r

    radii = np.array([r for r, _, _ in rows], dtype=np.float64)
    sigma_cyl = np.stack([v for _, v, _ in rows], axis=0)
    print(
        f"SCL radii: {radii[0]:.2f} .. {radii[-1]:.2f} mm "
        f"({len(radii)} pts, dr={radii[1] - radii[0]:.3f} mm)"
    )

    # ---- 1) Pointwise comparison (sigma_r / sigma_theta / sigma_z) vs Lame ----
    print("\n=== Pointwise stress vs Lame analytical solution ===")
    print(
        f"{'r [mm]':>9} {'σ_r FEA':>9} {'σ_r exact':>10} {'σ_t FEA':>9} {'σ_t exact':>10} "
        f"{'σ_z FEA':>9} {'σ_z exact':>10}"
    )
    pointwise = []
    for r, v_cyl, ex in rows:
        sr_fea, st_fea, sz_fea = v_cyl[0], v_cyl[1], v_cyl[2]
        pointwise.append(
            {
                "r_mm": r,
                "sigma_r_FEA": sr_fea,
                "sigma_r_exact": ex["sigma_r"],
                "sigma_theta_FEA": st_fea,
                "sigma_theta_exact": ex["sigma_theta"],
                "sigma_z_FEA": sz_fea,
                "sigma_z_exact": ex["sigma_z"],
                "von_mises_FEA": float(von_mises(v_cyl.reshape(1, 6))[0]),
                "von_mises_exact": lame_vm(r),
            }
        )
        print(
            f"{r:9.2f} {sr_fea:9.3f} {ex['sigma_r']:10.3f} "
            f"{st_fea:9.3f} {ex['sigma_theta']:10.3f} "
            f"{sz_fea:9.3f} {ex['sigma_z']:10.3f}"
        )

    # Worst-case error metrics. For sigma_r the outer-wall exact value
    # is 0, so the relative-error denominator collapses; we report the
    # max relative error only for points where |exact| > 0.5 MPa (i.e.
    # ≥ 5% of the peak load), AND we also report the worst absolute
    # error on every component for engineering transparency.
    REL_ERR_FLOOR_MPA = 0.5

    def rel_err(fea: float, exact: float) -> float:
        scale = max(abs(exact), 1e-6)
        return abs(fea - exact) / scale

    def abs_err(fea: float, exact: float) -> float:
        return abs(fea - exact)

    def max_rel(key_fea: str, key_exact: str) -> float:
        masked = [p for p in pointwise if abs(p[key_exact]) > REL_ERR_FLOOR_MPA]
        if not masked:
            return 0.0
        return max(rel_err(p[key_fea], p[key_exact]) for p in masked)

    def max_abs(key_fea: str, key_exact: str) -> float:
        return max(abs_err(p[key_fea], p[key_exact]) for p in pointwise)

    err_r = max_rel("sigma_r_FEA", "sigma_r_exact")
    err_t = max_rel("sigma_theta_FEA", "sigma_theta_exact")
    err_z = max_rel("sigma_z_FEA", "sigma_z_exact")
    err_vm = max_rel("von_mises_FEA", "von_mises_exact")
    abs_r = max_abs("sigma_r_FEA", "sigma_r_exact")
    abs_t = max_abs("sigma_theta_FEA", "sigma_theta_exact")
    abs_z = max_abs("sigma_z_FEA", "sigma_z_exact")
    abs_vm = max_abs("von_mises_FEA", "von_mises_exact")
    print(
        f"\nWorst-case error over SCL (rel% applied only where |exact| > {REL_ERR_FLOOR_MPA} MPa):"
    )
    print(f"  sigma_r   : {err_r * 100:6.2f} %     |abs| ≤ {abs_r:6.3f} MPa")
    print(f"  sigma_t   : {err_t * 100:6.2f} %     |abs| ≤ {abs_t:6.3f} MPa")
    print(f"  sigma_z   : {err_z * 100:6.2f} %     |abs| ≤ {abs_z:6.3f} MPa")
    print(f"  von Mises : {err_vm * 100:6.2f} %     |abs| ≤ {abs_vm:6.3f} MPa")

    # ---- 2) ASME VIII Div 2 §5.5 SCL linearization ----
    print("\n=== ASME VIII Div 2 §5.5 SCL linearization ===")
    # Linearize the cylindrical-basis tensors. The distance parameter is
    # the through-thickness coordinate s = r - Ri. gmsh's extrude can
    # leave the radial node spacing slightly non-uniform (the C3D20
    # quadratic mid-side nodes are placed by gmsh, not by us), and the
    # project's linearize_through_thickness rejects non-uniform grids
    # (Codex R1 HIGH — antisymmetric-integrand leak biases bending).
    # We resample onto a uniform 17-point grid via numpy.interp.
    s_raw = radii - radii[0]
    n_resamp = 17  # 8 cells * 2 + 1 -> recovers the natural Lobatto grid.
    s = np.linspace(0.0, s_raw[-1], n_resamp)
    sigma_resamp = np.zeros((n_resamp, 6), dtype=np.float64)
    for k in range(6):
        sigma_resamp[:, k] = np.interp(s, s_raw, sigma_cyl[:, k])
    print(f"Resampled SCL: {n_resamp} points, uniform Δs = {s[1] - s[0]:.4f} mm")
    sigma_cyl = sigma_resamp
    lin = linearize_through_thickness(sigma_cyl, s)
    print("membrane (sigma_r, sigma_t, sigma_z, sigma_rt, sigma_tz, sigma_rz):")
    print(f"  {lin.membrane}")
    # Sanity check vs Lame: closed-end averages can be computed analytically.
    # Through-thickness mean of sigma_r = -p/2 (avg of 0 at outer and -p at inner)
    # Actually exact average: (1/t) ∫_Ri^Ro K*p*(1 - (Ro/r)^2) dr
    #   = K*p * (1 - Ro^2 * (1/Ri - 1/Ro)/t) = K*p * (1 - Ro * (Ro-Ri)/(Ri*t))
    sigma_r_mean = K_FACTOR * P_INTERNAL * (1.0 - Ro / Ri)  # = -p (from above algebra)
    sigma_t_mean = K_FACTOR * P_INTERNAL * (1.0 + Ro / Ri)
    sigma_z_mean = K_FACTOR * P_INTERNAL  # uniform.
    print("Lame analytical means:")
    print(
        f"  sigma_r = {sigma_r_mean:.4f}  sigma_t = {sigma_t_mean:.4f}  sigma_z = {sigma_z_mean:.4f}"
    )

    pm = float(von_mises(lin.membrane.reshape(1, 6))[0])
    # P_m + P_b at outer (membrane + bending_outer) and inner (membrane - bending_outer).
    pmpb_outer = float(von_mises((lin.membrane + lin.bending_outer).reshape(1, 6))[0])
    pmpb_inner = float(von_mises((lin.membrane - lin.bending_outer).reshape(1, 6))[0])
    pmpb = max(pmpb_outer, pmpb_inner)
    # P_m + P_b + Q ≈ worst-case von Mises over the SCL.
    pmpbq = max(p["von_mises_FEA"] for p in pointwise)
    pmpbq_exact = max(lame_vm(r) for r, _, _ in rows)
    print("\nCategorized stress intensities (von Mises of tensor):")
    print(
        f"  P_m            = {pm:9.3f} MPa     allowable S_m  = {SM_AT_TEMP:.1f} MPa    "
        f"ratio = {pm / SM_AT_TEMP:.3f}"
    )
    print(
        f"  P_m + P_b      = {pmpb:9.3f} MPa     allowable 1.5*S_m = {1.5 * SM_AT_TEMP:.1f} MPa    "
        f"ratio = {pmpb / (1.5 * SM_AT_TEMP):.3f}"
    )
    print(
        f"  P_m + P_b + Q  = {pmpbq:9.3f} MPa     allowable 3.0*S_m = {3.0 * SM_AT_TEMP:.1f} MPa    "
        f"ratio = {pmpbq / (3.0 * SM_AT_TEMP):.3f}"
    )
    print(f"  (Exact P_m+P_b+Q via Lame max VM = {pmpbq_exact:.3f} MPa)")

    # ---- 3) Write outputs ----
    summary = {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
        "claim_impact": (
            "Tier 1 candidate thick-walled-cylinder benchmark; not signed "
            "validation; not benchmark agreement. ASME VIII Div 2 §5.5 "
            "categorized stresses computed from CalculiX 2.23 + project's "
            "Layer-3 stress linearization module; compared against Lame's "
            "analytical solution for verification only. Does not authorize "
            "Tier 2 promotion."
        ),
        "geometry": {"Ri_mm": Ri, "Ro_mm": Ro, "L_mm": L, "wedge_deg": math.degrees(THETA)},
        "load": {
            "internal_pressure_MPa": P_INTERNAL,
            "closed_end_axial_stress_MPa": K_FACTOR * P_INTERNAL,
        },
        "material": {"name": "SA-516 Gr.70", "E_MPa": 200_000.0, "nu": 0.3, "S_m_MPa": SM_AT_TEMP},
        "solver": {
            "name": "calculix",
            "version": "2.23",
            "n_nodes": len(result.nodes),
            "n_C3D20_elements": 32,
        },
        "scl": {"r_mm": [p["r_mm"] for p in pointwise], "pointwise": pointwise},
        "convergence": {
            "rel_err_floor_MPa": REL_ERR_FLOOR_MPA,
            "max_rel_err_sigma_r_pct": err_r * 100,
            "max_rel_err_sigma_t_pct": err_t * 100,
            "max_rel_err_sigma_z_pct": err_z * 100,
            "max_rel_err_von_mises_pct": err_vm * 100,
            "max_abs_err_sigma_r_MPa": abs_r,
            "max_abs_err_sigma_t_MPa": abs_t,
            "max_abs_err_sigma_z_MPa": abs_z,
            "max_abs_err_von_mises_MPa": abs_vm,
        },
        "asme_section_5_5": {
            "P_m_MPa": pm,
            "P_m_P_b_MPa": pmpb,
            "P_m_P_b_Q_MPa": pmpbq,
            "P_m_P_b_Q_exact_MPa": pmpbq_exact,
            "S_m_MPa": SM_AT_TEMP,
            "ratio_P_m_over_S_m": pm / SM_AT_TEMP,
            "ratio_P_m_P_b_over_1_5_S_m": pmpb / (1.5 * SM_AT_TEMP),
            "ratio_P_m_P_b_Q_over_3_S_m": pmpbq / (3.0 * SM_AT_TEMP),
            "membrane_tensor_rtz": lin.membrane.tolist(),
            "bending_outer_tensor_rtz": lin.bending_outer.tolist(),
        },
    }
    (HERE / "results.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\nWrote results.json ({(HERE / 'results.json').stat().st_size} bytes).")


if __name__ == "__main__":
    main()
