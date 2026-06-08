"""Phase 28 A — cantilever Euler buckling (k=2.0) tests.

Reuses Phase 23 A's `buckling_b31_runner` with end_condition=
'fixed-free' to validate the k-factor discipline at the second
point of the Euler family (k=2.0 cantilever vs Phase 22 A's
k=1.0 pinned-pinned).

Honest scope: NO new runner, NO new element type (still B31),
NO new solver kind (still *BUCKLE). The 8th validated case lifts
FEA Dim 2 (validated count 7 → 8) and FEA Dim 3 (k-factor
discipline at two points).

A C3D8 hex cantilever attempt in `buckling_runner.py` produced
256% residual due to shear locking; that path is documented as
rejected honest scope (NotImplementedError raised at runtime).

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Final

import pytest

from app.services.cross_check.buckling_euler import (
    EULER_K_FACTOR,
    compute_euler_critical_load,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
VERDICT_PATH: Final[Path] = (
    REPO_ROOT
    / "golden_samples"
    / "cantilever-buckle-candidate"
    / "cross_check_verdict.yaml"
)


# -- analytical k-factor pins ------------------------------------------


def test_phase28a_cantilever_k_factor_is_two() -> None:
    """The fixed-free end condition carries k = 2.0."""
    assert EULER_K_FACTOR["fixed-free"] == 2.0


def test_phase28a_cantilever_pcr_is_quarter_of_pinned_pinned() -> None:
    """P_cr ∝ 1/(kL)² → cantilever (k=2) P_cr = 1/4 of pinned (k=1)."""
    common = dict(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=0.020 * (0.020 ** 3) / 12.0,
    )
    pinned = compute_euler_critical_load(end_condition="pinned-pinned", **common)
    cantilever = compute_euler_critical_load(end_condition="fixed-free", **common)
    assert cantilever / pinned == pytest.approx(0.25, rel=1e-12)


def test_phase28a_canonical_cantilever_pcr_pin() -> None:
    """L=1m × 20mm × 20mm steel cantilever has P_cr ≈ 6908.72 N."""
    P_cr = compute_euler_critical_load(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=0.020 * (0.020 ** 3) / 12.0,
        end_condition="fixed-free",
    )
    assert P_cr == pytest.approx(6908.7231, abs=0.01)


# -- C3D8 honest-scope rejection guard --------------------------------


def test_phase28a_c3d8_runner_refuses_fixed_free() -> None:
    """The C3D8 hex runner (buckling_runner.py) does NOT support
    fixed-free because of severe shear locking. Attempting to
    invoke it MUST raise NotImplementedError pointing to the B31
    runner. This is honest scope discipline pinned at the test
    level."""
    from app.services.cross_check.buckling_runner import (
        run_buckling_cross_check,
    )
    with pytest.raises(NotImplementedError, match="fixed-free"):
        run_buckling_cross_check(
            Path("/tmp/never-called"),
            case_id="x",
            material_id="steel-s355",
            length_m=1.0,
            section_depth_m=0.020,
            section_width_m=0.020,
            end_condition="fixed-free",
        )


# -- verdict / registry pins ------------------------------------------


def test_phase28a_validated_count_is_eight() -> None:
    """After Phase 28 A persists the cantilever-buckle verdict, the
    overlay promotes 8 cases to tier_2_validated."""
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
    )

    _apply_verdict_overlay()

    validated = {
        case_id
        for case_id, tier in CLAIM_TIER_REGISTRY.items()
        if tier == "tier_2_validated"
    }
    expected = {
        "cylinder-pv-candidate",
        "cantilever-beam-candidate",
        "plate-with-hole-candidate",
        "euler-column-candidate",
        "plate-simply-supported-candidate",
        "cantilever-beam-modal-candidate",
        "cantilever-beam-modal-l50-candidate",
        "cantilever-buckle-candidate",
    }
    assert expected.issubset(validated), (
        f"Phase 28 A guard tripped — expected tier_2_validated cases "
        f"{expected} not contained in {validated}"
    )
    # FM-04a Phase 29 A — strict `== 8` loosened to `>= 8` using the
    # additive-promotion pattern (Phase 22/23/25/26/27/28 precedent).
    # Subset-of relationship preserves the original Phase 28 A intent
    # (the 8 expected cases above are still asserted via .issubset);
    # subsequent phases that add more validated cases (Phase 29 A:
    # plate-ss-shell-candidate, etc.) loosen this further. No
    # validated case is ever downgraded.
    assert len(validated) >= 8, (
        f"validated count = {len(validated)}, expected ≥8; cohort={validated}"
    )


def test_phase28a_verdict_yaml_persisted_on_disk() -> None:
    assert VERDICT_PATH.is_file(), f"missing Phase 28 A verdict at {VERDICT_PATH}"
    payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["case_id"] == "cantilever-buckle-candidate"
    assert payload["end_condition"] == "fixed-free"
    assert payload["k_factor"] == 2.0
    assert payload["cross_check_kind"] == "euler_column_buckling"
    assert payload["claim_tier"] == "tier_2_validated"
    # The residual is well within tolerance.
    assert abs(payload["residual_pct"]) <= payload["tolerance_pct"]
    # Verdict is the runner output, not an arbitrary value: pin the
    # observed value to within 1% of analytical (envelope-honesty
    # pin; trips if the B31 runner stops matching the analytical).
    assert (
        abs(payload["observed_p_cr_n"] - payload["analytical_p_cr_n"])
        / payload["analytical_p_cr_n"]
        < 0.01
    )


def test_phase28a_runner_is_b31_not_c3d8() -> None:
    """Pin the honest-scope discipline at the verdict-file level:
    the canonical Phase 28 A run was performed via the B31 runner,
    NOT the C3D8 hex runner."""
    payload = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    assert payload["runner"] == "buckling_b31_runner"


# -- live-solver E2E pin ----------------------------------------------


@pytest.mark.requires_solver
def test_phase28a_cantilever_buckle_residual_below_10pct(
    tmp_path: Path,
) -> None:
    """End-to-end real ccx run pin: cantilever (fixed-free) k=2.0
    must produce |residual_pct| ≤ 10% vs Euler analytical."""
    from app.services.cross_check.buckling_b31_runner import (
        run_buckling_b31_cross_check,
    )
    result = run_buckling_b31_cross_check(
        tmp_path,
        case_id="cantilever-buckle-candidate",
        material_id="steel-s355",
        length_m=1.0,
        section_depth_m=0.020,
        section_width_m=0.020,
        end_condition="fixed-free",
        n_elements=20,
        persist_verdict=False,
    )
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= result.tolerance_pct
    # Tight-residual pin: the 2026-05-17 run produced +0.0298%.
    # If a future change degrades the residual by > 100x (still
    # PASS but very different), this trips.
    assert abs(result.residual_pct) < 3.0, (
        f"cantilever residual {result.residual_pct:.3f}% — investigate; "
        f"the canonical run was +0.0298%"
    )
