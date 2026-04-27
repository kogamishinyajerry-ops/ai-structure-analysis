"""Layer-3 stress-derivatives tests — RFC-001 §4.2 + ADR-001."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.domain.stress_derivatives import max_shear, principals, von_mises

# ---- shape validation ------------------------------------------------------


def test_von_mises_rejects_wrong_column_count() -> None:
    bad = np.zeros((3, 5), dtype=np.float64)
    with pytest.raises(ValueError, match=r"shape \(N, 6\)"):
        von_mises(bad)


def test_principals_rejects_1d_input() -> None:
    bad = np.zeros(6, dtype=np.float64)
    with pytest.raises(ValueError):
        principals(bad)


def test_max_shear_rejects_3d_input() -> None:
    bad = np.zeros((2, 3, 6), dtype=np.float64)
    with pytest.raises(ValueError):
        max_shear(bad)


# ---- analytical smoke cases ------------------------------------------------


def test_von_mises_uniaxial_tension_equals_axial_stress() -> None:
    # Pure σ11 = 100 MPa, all other zero. σ_vm should equal |σ11|.
    t = np.array([[100.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    assert np.isclose(von_mises(t)[0], 100.0)


def test_von_mises_pure_shear_yields_sqrt3_factor() -> None:
    # σ12 = τ, all else zero. σ_vm = sqrt(3) * τ.
    tau = 50.0
    t = np.array([[0.0, 0.0, 0.0, tau, 0.0, 0.0]])
    assert np.isclose(von_mises(t)[0], np.sqrt(3.0) * tau)


def test_von_mises_hydrostatic_is_zero() -> None:
    # Equal triaxial stress: σ11=σ22=σ33=p, no shear → σ_vm = 0.
    t = np.array([[10.0, 10.0, 10.0, 0.0, 0.0, 0.0]])
    assert np.isclose(von_mises(t)[0], 0.0)


def test_von_mises_batch_independent() -> None:
    # Two independent rows in one call must equal two single-row calls.
    a = np.array([[100.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    b = np.array([[0.0, 0.0, 0.0, 50.0, 0.0, 0.0]])
    batch = np.vstack([a, b])
    expected = np.concatenate([von_mises(a), von_mises(b)])
    assert np.allclose(von_mises(batch), expected)


# ---- principals -----------------------------------------------------------


def test_principals_diagonal_tensor_is_already_principal() -> None:
    # Diagonal tensor with σ11>σ22>σ33: principals == diagonal sorted.
    t = np.array([[3.0, 1.0, -2.0, 0.0, 0.0, 0.0]])
    s_max, s_mid, s_min = principals(t)
    assert np.isclose(s_max[0], 3.0)
    assert np.isclose(s_mid[0], 1.0)
    assert np.isclose(s_min[0], -2.0)


def test_principals_sorted_descending() -> None:
    rng = np.random.default_rng(seed=42)
    n = 50
    t = rng.standard_normal((n, 6)) * 100.0
    s_max, s_mid, s_min = principals(t)
    assert np.all(s_max >= s_mid - 1e-9)
    assert np.all(s_mid >= s_min - 1e-9)


def test_principals_pure_shear_known_eigenvalues() -> None:
    # Pure σ12 = τ with σ11=σ22=σ33=0 has eigenvalues (τ, 0, -τ).
    tau = 75.0
    t = np.array([[0.0, 0.0, 0.0, tau, 0.0, 0.0]])
    s_max, s_mid, s_min = principals(t)
    assert np.isclose(s_max[0], tau)
    assert np.isclose(s_mid[0], 0.0)
    assert np.isclose(s_min[0], -tau)


def test_principals_distinguishes_s13_from_s23_indices() -> None:
    """Codex R1 NIT: pin the S13/S23 column ordering at row indexing time.

    Swapping ``S13`` and ``S23`` in the tensor assembly would still pass
    the pure-shear analytical cases (eigenvalues are τ, 0, -τ for any
    single off-diagonal). This test feeds an asymmetric tensor whose
    S13-vs-S23 swap shifts the principal-stress decomposition, so a
    transposition regression breaks the assertion.

    Tensor:    diag(5, 3, 1), S13=2 (others 0)
    Principal axis decoupled at y → one eigenvalue is 3.
    The xz-plane 2x2 submatrix [[5, 2], [2, 1]] has eigenvalues
    3 ± 2√2  ≈ 5.828427, 0.171573.
    Sorted descending: (3 + 2√2,  3,  3 - 2√2).
    """
    t = np.array([[5.0, 3.0, 1.0, 0.0, 0.0, 2.0]])  # S13 = 2, S23 = 0
    s_max, s_mid, s_min = principals(t)
    assert np.isclose(s_max[0], 3.0 + 2.0 * np.sqrt(2.0))
    assert np.isclose(s_mid[0], 3.0)
    assert np.isclose(s_min[0], 3.0 - 2.0 * np.sqrt(2.0))


def test_principals_invariants_match_trace_and_det() -> None:
    """Per the docstring: sum of eigs == trace, product of eigs == det."""
    rng = np.random.default_rng(seed=7)
    t = rng.standard_normal((30, 6)) * 50.0
    s_max, s_mid, s_min = principals(t)
    trace = t[:, 0] + t[:, 1] + t[:, 2]
    assert np.allclose(s_max + s_mid + s_min, trace)
    # Determinant invariant — Codex R1 NIT closure.
    s11, s22, s33, s12, s23, s13 = (t[:, i] for i in range(6))
    det = (
        s11 * (s22 * s33 - s23 * s23)
        - s12 * (s12 * s33 - s23 * s13)
        + s13 * (s12 * s23 - s22 * s13)
    )
    assert np.allclose(s_max * s_mid * s_min, det)


# ---- max_shear -------------------------------------------------------------


def test_max_shear_uniaxial_tension() -> None:
    # σ1=σ, σ2=σ3=0 → τ_max = σ/2.
    t = np.array([[80.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    assert np.isclose(max_shear(t)[0], 40.0)


def test_max_shear_pure_shear_equals_input() -> None:
    # σ12=τ, all else zero → eigenvalues (τ, 0, -τ) → τ_max = τ.
    tau = 30.0
    t = np.array([[0.0, 0.0, 0.0, tau, 0.0, 0.0]])
    assert np.isclose(max_shear(t)[0], tau)


def test_max_shear_non_negative() -> None:
    rng = np.random.default_rng(seed=99)
    t = rng.standard_normal((40, 6)) * 25.0
    out = max_shear(t)
    assert np.all(out >= -1e-9)


# ---- input not mutated ----------------------------------------------------


def test_inputs_are_not_mutated() -> None:
    original = np.array([[5.0, -2.0, 1.0, 0.5, 0.3, 0.1]], dtype=np.float64)
    before = original.copy()
    _ = von_mises(original)
    _ = principals(original)
    _ = max_shear(original)
    assert np.array_equal(original, before)


# ---- end-to-end with the CalculiX adapter ---------------------------------

GS001_FRD = (
    Path(__file__).resolve().parents[2] / "golden_samples" / "GS-001" / "gs001_result.frd"
)


def test_layer3_consumes_layer1_calculix_stress_tensor() -> None:
    """Cross-layer smoke: CalculiXReader (W2) → stress_derivatives (W3).

    Verifies the canonical-field layout contract holds end-to-end —
    Layer-1 emits ``(N, 6)`` per RFC §4.4 ordering, Layer-3 consumes
    it without reshaping.
    """
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {GS001_FRD}")

    from app.adapters.calculix import CalculiXReader
    from app.core.types import CanonicalField, UnitSystem

    reader = CalculiXReader(GS001_FRD, unit_system=UnitSystem.SI_MM)
    try:
        step = reader.solution_states[0]
        fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)
        assert fd is not None
        tensor = fd.values()
        assert tensor.shape == (44, 6)

        vm = von_mises(tensor)
        assert vm.shape == (44,)
        assert np.all(vm >= -1e-9)

        s_max, s_mid, s_min = principals(tensor)
        assert s_max.shape == s_mid.shape == s_min.shape == (44,)
        assert np.all(s_max >= s_mid - 1e-9)
        assert np.all(s_mid >= s_min - 1e-9)

        tau = max_shear(tensor)
        assert np.all(tau >= -1e-9)
    finally:
        reader.close()
