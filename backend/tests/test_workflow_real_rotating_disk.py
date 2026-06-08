"""FM-05 — real ccx re-solve of the sealed rotating-disk centrifugal deck.

ccx-guarded (skipped when ccx is not on PATH, e.g. the required lint-and-test CI
job), so it never blocks the suite. When ccx IS present it re-solves the
canonical nr=48 deck under ``*DLOAD CENTRIF`` and must reproduce the bore hoop
stress σ_θ(a) ≈ 65.353 MPa (PASS vs the Timoshenko plane-stress closed form
65.312 MPa, ±1%) and hold a tight drift pin. Runs in the dedicated non-required
``real-rotating-disk-e2e`` CI job.
"""
from __future__ import annotations

import pytest
from app.services.workflow import real_rotating_disk

_needs_ccx = pytest.mark.skipif(
    not real_rotating_disk.rotating_disk_available(),
    reason="real rotating-disk solve requires ccx on PATH + the disk deck",
)


@_needs_ccx
def test_real_rotating_disk_module_solve_and_extract(tmp_path):
    """A fresh solve + extraction reproduces the rotating-disk benchmark agreement."""
    out = real_rotating_disk.run_rotating_disk_solve(tmp_path, timeout_s=900)
    assert out["converged"] is True
    bench = real_rotating_disk.extract_rotating_disk_benchmark(out["deck_path"], out["frd_path"])
    assert bench["verdict"] == "PASS"
    assert bench["sigma_theta_pa"] == pytest.approx(65.353e6, rel=0.02)
    assert bench["node_id"] is not None


@_needs_ccx
def test_real_rotating_disk_sigma_theta_drift_pin(tmp_path):
    """ADR-027 V2-0 (live re-solve): a fresh ccx re-solve of the canonical disk
    deck must hold BOTH gates — the hard benchmark gate (PASS within ±1% of the
    Timoshenko 65.312 MPa, never relaxed) AND a tight drift pin (±0.5%) against the
    frozen validated observation 65353300.0 Pa. The pin catches solver/toolchain
    drift the wide gate would mask; it is a regression watchdog, not a tighter
    truth claim (Tier 1, not signed)."""
    out = real_rotating_disk.run_rotating_disk_solve(tmp_path, timeout_s=900)
    assert out["converged"] is True
    bench = real_rotating_disk.extract_rotating_disk_benchmark(out["deck_path"], out["frd_path"])
    # hard gates — cross-ccx-version, never relaxed
    assert bench["verdict"] == "PASS"
    assert abs(bench["residual_pct"]) <= real_rotating_disk.DISK_TOLERANCE_PCT
    assert bench["sigma_theta_pa"] > 0  # tensile hoop stress at the bore
    # tight pin — version-window drift watchdog
    assert bench["sigma_theta_pa"] == pytest.approx(
        real_rotating_disk.DISK_OBSERVED_PA_PINNED, rel=real_rotating_disk.DISK_DRIFT_REL
    )
