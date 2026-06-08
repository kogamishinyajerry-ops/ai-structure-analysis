"""ADR-027 V2-2 — the ``reproduce <case_id>`` CLI + structured audit log.

V2-2 (G-2 evidence-packet item 6) requires a CLI that re-derives a committed
case's result + verdict from its sealed inputs, plus a structured audit-trail
log. These tests pin the honesty floor of that mechanism:

* the ccx-free RECOMPUTE path re-derives ``residual_pct`` from the committed
  observed/analytical values and re-checks tolerance (always runnable in CI);
* the sealed-hash INTEGRITY GATE refuses to call a reproduction successful when
  a sealed input drifted from its manifest hash;
* a committed FAIL (or out-of-tolerance) verdict never counts as reproduced;
* the audit-log writer refuses to write under ``golden_samples/**`` and emits
  the documented schema;
* when ccx is present the REAL_SOLVE path re-solves the NAFEMS LE10 deck from
  scratch and reproduces the published benchmark agreement within drift.

Honesty boundary: a green reproduction means the committed evidence reproduces
from sealed inputs — NOT signed validation (G-2 item 7 stays open).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reproduce_case as rc  # noqa: E402

_FIXED_NOW = datetime(2026, 6, 7, 4, 0, 0, tzinfo=UTC)
_LE10 = "nafems-le10-thick-plate-candidate"
_LE11 = "nafems-le11-solid-cyl-temperature-candidate"
_DISK = "rotating-disk-centrifugal-candidate"

_needs_ccx = pytest.mark.skipif(
    not rc._ccx_available(),
    reason="real re-solve requires ccx on PATH",
)


def _synthetic_case(
    root: Path,
    case_id: str,
    *,
    observed: float,
    analytical: float,
    residual_pct: float,
    tolerance_pct: float,
    verdict: str,
    seal: bool = False,
    manifest: dict | None = None,
) -> None:
    case_dir = root / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    verdict_bytes = json.dumps(
        {
            "case_id": case_id,
            "verdict": verdict,
            "observed_pa": observed,
            "analytical_pa": analytical,
            "residual_pct": residual_pct,
            "tolerance_pct": tolerance_pct,
        }
    ).encode()
    (case_dir / "cross_check_verdict.yaml").write_bytes(verdict_bytes)
    if seal and manifest is None:
        manifest = {
            "sealed_artifacts": {
                "cross_check_verdict.yaml": {
                    "sha256": hashlib.sha256(verdict_bytes).hexdigest(),
                    "bytes": len(verdict_bytes),
                }
            }
        }
    if manifest is not None:
        (case_dir / "artifact_manifest.json").write_text(json.dumps(manifest))


# --- recompute path (ccx-free, always runs) ---------------------------------


def test_recompute_with_seal_is_reproduced(tmp_path: Path) -> None:
    """A sealed case (manifest hash matches) reproduces: recompute is correct,
    integrity verified, verdict PASS."""
    _synthetic_case(
        tmp_path,
        "synthetic-pass",
        observed=110.0,
        analytical=100.0,
        residual_pct=10.0,
        tolerance_pct=15.0,
        verdict="PASS",
        seal=True,
    )
    rec = rc.reproduce_case(
        "synthetic-pass", repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW
    )
    assert rec["reproduction_kind"] == "recompute"
    assert rec["rederived"]["residual_pct"] == pytest.approx(10.0, abs=1e-9)
    assert rec["rederived"]["verdict"] == "PASS"
    assert rec["agreement"]["verdict_matches_committed"] is True
    assert rec["inputs_integrity"]["all_hashes_match"] is True
    assert rec["reproduced"] is True
    # no fabricated ccx version on the recompute path
    assert rec["ccx"]["version"] is None


def test_recompute_without_manifest_is_not_reproduced(tmp_path: Path) -> None:
    """No manifest = the inputs cannot be proven canonical, so 'reproduced from
    SEALED inputs' is withheld even though the recompute math is consistent."""
    _synthetic_case(
        tmp_path,
        "synthetic-unsealed",
        observed=110.0,
        analytical=100.0,
        residual_pct=10.0,
        tolerance_pct=15.0,
        verdict="PASS",
    )
    rec = rc.reproduce_case(
        "synthetic-unsealed", repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW
    )
    assert rec["inputs_integrity"]["manifest_present"] is False
    assert rec["rederived"]["verdict"] == "PASS"  # math is still consistent
    assert rec["agreement"]["residual_matches_committed"] is True
    assert rec["reproduced"] is False  # but no seal -> not reproduced
    assert any("artifact_manifest" in n for n in rec["notes"])


def test_committed_fail_is_not_a_reproduction(tmp_path: Path) -> None:
    """A committed FAIL (or out-of-tolerance) verdict must never count as a
    successful reproduction, even if the recompute matches it exactly."""
    _synthetic_case(
        tmp_path,
        "synthetic-fail",
        observed=200.0,
        analytical=100.0,
        residual_pct=100.0,
        tolerance_pct=3.0,
        verdict="FAIL",
        seal=True,  # sealed, so the ONLY reason it is not reproduced is the FAIL verdict
    )
    rec = rc.reproduce_case(
        "synthetic-fail", repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW
    )
    assert rec["inputs_integrity"]["all_hashes_match"] is True
    assert rec["rederived"]["verdict"] == "FAIL"
    assert rec["reproduced"] is False


def test_integrity_gate_blocks_tampered_inputs(tmp_path: Path) -> None:
    """A sealed file whose bytes drifted from the manifest hash fails the gate,
    so the case is reported NOT reproduced."""
    case_id = "synthetic-tampered"
    manifest = {
        "sealed_artifacts": {
            "cross_check_verdict.yaml": {"sha256": "0" * 64, "bytes": 1},
        }
    }
    _synthetic_case(
        tmp_path,
        case_id,
        observed=110.0,
        analytical=100.0,
        residual_pct=10.0,
        tolerance_pct=15.0,
        verdict="PASS",
        manifest=manifest,
    )
    rec = rc.reproduce_case(
        case_id, repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW
    )
    assert rec["inputs_integrity"]["manifest_present"] is True
    assert rec["inputs_integrity"]["all_hashes_match"] is False
    assert rec["inputs_integrity"]["mismatches"]
    assert rec["reproduced"] is False


def test_unknown_case_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rc.reproduce_case(
            "does-not-exist", repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW
        )


@pytest.mark.parametrize("bad", ["../etc", "a/b", "/abs/path", "..", ".", ""])
def test_case_id_rejects_path_traversal(tmp_path: Path, bad: str) -> None:
    """case_id must be a bare golden_samples/ dir name — no traversal escape."""
    with pytest.raises(ValueError):
        rc.reproduce_case(bad, repo_root=tmp_path, do_solve=False, timeout_s=1, now=_FIXED_NOW)


# --- audit-log writer -------------------------------------------------------


def test_audit_writer_refuses_golden_samples(tmp_path: Path) -> None:
    rec = {"case_id": "x", "schema": rc.AUDIT_SCHEMA}
    with pytest.raises(SystemExit):
        rc._write_audit(rec, tmp_path / "golden_samples" / "audit", _FIXED_NOW, repo_root=tmp_path)


def test_audit_writer_refuses_outside_repo(tmp_path: Path) -> None:
    """An absolute/escaped output dir outside the repo tree is refused."""
    rec = {"case_id": "x", "schema": rc.AUDIT_SCHEMA}
    outside = tmp_path.parent / "escape_audit"
    with pytest.raises(SystemExit):
        rc._write_audit(rec, outside, _FIXED_NOW, repo_root=tmp_path)


def test_audit_writer_emits_schema(tmp_path: Path) -> None:
    rec = {"case_id": "x", "schema": rc.AUDIT_SCHEMA}
    out = rc._write_audit(
        rec, tmp_path / "reports" / "reproduce_audit", _FIXED_NOW, repo_root=tmp_path
    )
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded["schema"] == rc.AUDIT_SCHEMA
    assert out.name.startswith("x_") and out.name.endswith("Z.json")


# --- real-solver degradation (no ccx) ---------------------------------------


def test_real_solver_case_degrades_to_recompute_without_ccx(monkeypatch, tmp_path: Path) -> None:
    """A registered real-solver case with ccx absent must NOT claim a real solve:
    it degrades to recompute and says so honestly in the notes."""
    monkeypatch.setattr(rc, "_ccx_available", lambda: False)
    _synthetic_case(
        tmp_path,
        _LE10,
        observed=-5437900.0,
        analytical=-5380000.0,
        residual_pct=1.0762,
        tolerance_pct=3.0,
        verdict="PASS",
        seal=True,
    )
    rec = rc.reproduce_case(_LE10, repo_root=tmp_path, do_solve=True, timeout_s=1, now=_FIXED_NOW)
    assert rec["reproduction_kind"] == "recompute"
    assert any("ccx absent" in n for n in rec["notes"])
    assert rec["ccx"]["available"] is False
    assert rec["reproduced"] is True  # sealed + consistent recompute (NOT a fresh solve)


def test_real_solve_fail_is_not_reproduced(monkeypatch, tmp_path: Path) -> None:
    """Even a real solve whose verdict is FAIL must not count as reproduced — the
    real_solve gate is PASS-gated (a both-FAIL match is not a benchmark agreement).
    Uses a stubbed solver so no ccx is needed."""
    monkeypatch.setattr(rc, "_ccx_available", lambda: True)
    fake = {
        "observed_pa": -5_000_000.0,
        "analytical_pa": -5_380_000.0,
        "residual_pct": 7.06,
        "tolerance_pct": 3.0,
        "verdict": "FAIL",
        "sigma_yy_mpa": -5.0,
        "ccx_version": "2.23",
        "converged": True,
        "node_d": 6,
        "point_d_m": [2.0, 0.0, 0.3],
    }
    monkeypatch.setitem(rc._REAL_SOLVERS, _LE10, lambda timeout_s: fake)
    _synthetic_case(
        tmp_path,
        _LE10,
        observed=-5_000_000.0,
        analytical=-5_380_000.0,
        residual_pct=7.06,
        tolerance_pct=3.0,
        verdict="FAIL",
        seal=True,
    )
    rec = rc.reproduce_case(_LE10, repo_root=tmp_path, do_solve=True, timeout_s=1, now=_FIXED_NOW)
    assert rec["reproduction_kind"] == "real_solve"
    assert rec["agreement"]["verdict_matches_committed"] is True  # both FAIL
    assert rec["rederived"]["verdict"] == "FAIL"
    assert rec["reproduced"] is False  # PASS-gated, so not a reproduction


# --- real solve (ccx-guarded) -----------------------------------------------


@_needs_ccx
def test_real_solve_reproduces_le10_benchmark() -> None:
    """With ccx present, a fresh re-solve of the sealed LE10 deck reproduces the
    published −5.38 MPa σ_yy@D agreement within drift of the committed value."""
    rec = rc.reproduce_case(
        _LE10, repo_root=REPO_ROOT, do_solve=True, timeout_s=900, now=_FIXED_NOW
    )
    assert rec["reproduction_kind"] == "real_solve"
    assert rec["ccx"]["available"] is True
    assert rec["ccx"]["version"]  # recorded from the actual solve
    assert rec["inputs_integrity"]["all_hashes_match"] is True
    assert rec["rederived"]["verdict"] == "PASS"
    assert rec["agreement"]["within_drift_tolerance"] is True
    assert rec["agreement"]["verdict_matches_committed"] is True
    assert rec["reproduced"] is True


@_needs_ccx
@pytest.mark.parametrize("case_id", [_LE11, _DISK])
def test_real_solve_reproduces_benchmark(case_id: str) -> None:
    """With ccx present, a fresh re-solve of each newer sealed public-benchmark
    deck (LE11 thermal-stress, rotating-disk centrifugal) reproduces its committed
    headline within drift of the committed value — closing G-2 item 6 so all three
    tier_2 benchmarks are live-solver re-derivable, not just LE10."""
    rec = rc.reproduce_case(
        case_id, repo_root=REPO_ROOT, do_solve=True, timeout_s=900, now=_FIXED_NOW
    )
    assert rec["reproduction_kind"] == "real_solve"
    assert rec["ccx"]["available"] is True
    assert rec["ccx"]["version"]  # recorded from the actual solve
    assert rec["inputs_integrity"]["all_hashes_match"] is True
    assert rec["rederived"]["verdict"] == "PASS"
    assert rec["agreement"]["within_drift_tolerance"] is True
    assert rec["agreement"]["verdict_matches_committed"] is True
    assert rec["reproduced"] is True
