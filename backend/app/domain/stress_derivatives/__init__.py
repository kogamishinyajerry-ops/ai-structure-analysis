"""Stress-tensor derived quantities — RFC-001 §4.2 + ADR-001.

These functions take canonical-form 6-component symmetric stress
tensors (per ``CanonicalField.STRESS_TENSOR``, layout
``[S11, S22, S33, S12, S23, S13]``) and return scalar derived
quantities — von Mises, principal stresses, max shear.

ADR-001 reminder: derived-quantity computation lives HERE (Layer 3),
not in any solver adapter (Layer 1). Adapters expose the raw tensor
and Layer 3 chooses when to derive. ASME VIII Div 2 stress
linearization (SCL) lands in M4+ per RFC §6.4 — out of MVP scope.

The component layout is the closed-set CanonicalField convention; if
an adapter wants to feed in a different ordering it must re-pack
first. We intentionally validate shape rather than silently re-order.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

__all__ = ["von_mises", "principals", "max_shear"]


def _validate_tensor(tensor: npt.NDArray[np.float64]) -> None:
    """``tensor`` must be ``(N, 6)`` — ``[S11, S22, S33, S12, S23, S13]``."""
    if tensor.ndim != 2 or tensor.shape[1] != 6:
        raise ValueError(
            f"stress tensor must have shape (N, 6) per CanonicalField "
            f"layout [S11,S22,S33,S12,S23,S13]; got shape {tensor.shape}"
        )


def von_mises(tensor: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Per-row von Mises equivalent stress.

    Closed-form:
        σ_vm = sqrt( 0.5 [(σ11-σ22)² + (σ22-σ33)² + (σ33-σ11)²]
                       + 3 (σ12² + σ23² + σ13²) )

    Returns a ``(N,)`` 1-D array. Inputs are NOT mutated.
    """
    _validate_tensor(tensor)
    s11, s22, s33, s12, s23, s13 = (tensor[:, i] for i in range(6))
    deviatoric = (s11 - s22) ** 2 + (s22 - s33) ** 2 + (s33 - s11) ** 2
    shear = s12**2 + s23**2 + s13**2
    result: npt.NDArray[np.float64] = np.sqrt(0.5 * deviatoric + 3.0 * shear)
    return result


def principals(
    tensor: npt.NDArray[np.float64],
) -> tuple[
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]:
    """Per-row principal stresses ``(σ_max, σ_mid, σ_min)``.

    Diagonalises each row's 3×3 symmetric tensor via ``numpy.linalg.eigvalsh``
    (real symmetric → real eigenvalues). Returned arrays are sorted such
    that ``σ_max ≥ σ_mid ≥ σ_min`` element-wise.

    Each output is a ``(N,)`` 1-D array. Inputs are NOT mutated.
    """
    _validate_tensor(tensor)
    n = tensor.shape[0]
    s11, s22, s33, s12, s23, s13 = (tensor[:, i] for i in range(6))
    # Build the (N, 3, 3) symmetric tensor stack.
    mat = np.empty((n, 3, 3), dtype=np.float64)
    mat[:, 0, 0] = s11
    mat[:, 1, 1] = s22
    mat[:, 2, 2] = s33
    mat[:, 0, 1] = mat[:, 1, 0] = s12
    mat[:, 1, 2] = mat[:, 2, 1] = s23
    mat[:, 0, 2] = mat[:, 2, 0] = s13
    eigs = np.linalg.eigvalsh(mat)  # ascending order: (N, 3)
    return eigs[:, 2], eigs[:, 1], eigs[:, 0]  # max, mid, min


def max_shear(tensor: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Per-row maximum shear stress ``τ_max = (σ_max - σ_min) / 2``.

    Uses the principal-stress decomposition; passes ADR-001 muster
    because no solver-specific guess is involved — pure tensor algebra.
    Returns a ``(N,)`` 1-D array.
    """
    s_max, _, s_min = principals(tensor)
    return 0.5 * (s_max - s_min)
