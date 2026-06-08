"""FM-05 — real ccx re-solve of the sealed NAFEMS LE11 thermal-stress deck.

ccx-guarded (skipped when ccx is not on PATH, e.g. the required lint-and-test CI
job), so it never blocks the suite. When ccx IS present it re-solves the
canonical r4 deck and must reproduce σ_zz@A ≈ −105.398 MPa (PASS vs the published
−105 MPa, ±3%) and hold a tight drift pin. Runs in the dedicated non-required
``real-le11-e2e`` CI job.
"""
from __future__ import annotations

import pytest
from app.services.workflow import real_le11

_needs_ccx = pytest.mark.skipif(
    not real_le11.le11_available(),
    reason="real LE11 solve requires ccx on PATH + the LE11 deck",
)


@_needs_ccx
def test_real_le11_module_solve_and_extract(tmp_path):
    """A fresh solve + extraction reproduces the LE11 benchmark agreement."""
    out = real_le11.run_le11_solve(tmp_path, timeout_s=900)
    assert out["converged"] is True
    bench = real_le11.extract_le11_benchmark(out["deck_path"], out["frd_path"])
    assert bench["verdict"] == "PASS"
    assert bench["sigma_zz_pa"] == pytest.approx(-105.398e6, rel=0.02)
    assert bench["node_a"] is not None


@_needs_ccx
def test_real_le11_sigma_zz_drift_pin(tmp_path):
    """ADR-027 V2-0 (live re-solve): a fresh ccx re-solve of the canonical LE11
    deck must hold BOTH gates — the hard benchmark gate (PASS within ±3% of the
    published −105 MPa, never relaxed) AND a tight drift pin (±0.5%) against the
    frozen validated observation −105398000.0 Pa. The pin catches solver/toolchain
    drift the wide gate would mask; it is a regression watchdog, not a tighter
    truth claim (Tier 1, not signed)."""
    out = real_le11.run_le11_solve(tmp_path, timeout_s=900)
    assert out["converged"] is True
    bench = real_le11.extract_le11_benchmark(out["deck_path"], out["frd_path"])
    # hard gates — cross-ccx-version, never relaxed
    assert bench["verdict"] == "PASS"
    assert abs(bench["residual_pct"]) <= real_le11.LE11_TOLERANCE_PCT
    assert bench["sigma_zz_pa"] < 0  # compression at A (ccx tension-positive)
    # tight pin — version-window drift watchdog
    assert bench["sigma_zz_pa"] == pytest.approx(
        real_le11.LE11_OBSERVED_PA_PINNED, rel=real_le11.LE11_DRIFT_REL
    )
