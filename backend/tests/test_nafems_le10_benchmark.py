"""V2-1 / ADR-027 — NAFEMS LE10 public-benchmark agreement regression floor.

The project's FIRST public-benchmark agreement: a real ccx solve of the NAFEMS
LE10 thick-plate-pressure benchmark whose sigma_yy at point D agrees with the
PUBLISHED reference (-5.38 MPa) within tolerance. These tests pin that agreement
(G-1 regression floor) and the tier promotion. The fast tests read the committed
verdict; `test_le10_residual_reproduces` (requires_solver) re-runs the real solve.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CASE = REPO / "golden_samples" / "nafems-le10-thick-plate-candidate"
PUBLISHED_TARGET_PA = -5_380_000.0  # NAFEMS LE10 sigma_yy(D), TNSB Rev.3


def _verdict() -> dict:
    return json.loads((CASE / "cross_check_verdict.yaml").read_text())


def test_le10_verdict_is_pass_within_tolerance() -> None:
    v = _verdict()
    assert v["verdict"] == "PASS"
    assert abs(v["residual_pct"]) <= v["tolerance_pct"], (
        f"LE10 residual {v['residual_pct']}% exceeds tolerance {v['tolerance_pct']}%"
    )
    # agreement is genuinely tight (well inside the 3% hex band)
    assert abs(v["residual_pct"]) <= 3.0


def test_le10_sign_and_point_are_correct() -> None:
    """Compressive (negative) sigma_yy at the UPPER-surface point D = (2,0,+0.3).

    Guards the two errors the 2026-06-03 spec triangulation caught in the prior
    records: D is the UPPER surface (not lower) and observed must be NEGATIVE.
    """
    v = _verdict()
    assert v["observed_pa"] < 0, "sigma_yy(D) must be compressive (negative)"
    assert PUBLISHED_TARGET_PA < 0
    assert v["point_d_surface"] == "upper"
    assert v["point_d_m"] == [2.0, 0.0, 0.3]
    # both observed and target share the same (compressive) sign
    assert (v["observed_pa"] < 0) == (v["analytical_pa"] < 0)


def test_le10_promotes_to_tier_2_validated() -> None:
    sys.path.insert(0, str(REPO))
    from backend.app.services.reporting._claim_tier import get_claim_tier

    assert get_claim_tier("nafems-le10-thick-plate-candidate") == "tier_2_validated"


def test_le10_convergence_is_monotone() -> None:
    conv = json.loads((CASE / "convergence_study.json").read_text())
    resids = [abs(p["residual_pct"]) for p in conv["points"]]
    assert conv["trend_monotone"] is True
    assert resids == sorted(resids, reverse=True), (
        f"LE10 convergence branch not monotone-decreasing: {resids}"
    )
    assert resids[-1] <= 1.5  # finest mesh well-converged


@pytest.mark.requires_solver
def test_le10_residual_reproduces(tmp_path: Path) -> None:
    """Re-run the canonical generator and confirm the recorded residual holds.

    The real regression guard for the benchmark agreement (slow: runs gmsh + ccx).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "le10_generator", CASE / "data" / "generator.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    gen.HERE = tmp_path  # write scratch meshes under tmp, not the repo
    out = gen.solve_one(40, 20, 6, "C3D20")
    assert out["converged"] is True
    assert out["sigma_yy_pa"] < 0
    assert abs(out["residual_pct"]) <= 3.0
