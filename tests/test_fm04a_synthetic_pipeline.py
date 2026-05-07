"""Test for the FM-04a Tier 1 synthetic ballistic candidate pipeline.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

The pipeline lives at ``scripts/fm04a_synthetic_pipeline.py``; this test
imports its ``main`` entry point and runs it against a temporary repo
copy that contains exactly enough of the real layout (a synthetic case
directory + the GS-001 FRD fixture symlinked into place) to exercise the
end-to-end Tier 1 contract without OpenRadioss installed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = REPO_ROOT / "scripts" / "fm04a_synthetic_pipeline.py"
GS001_FRD = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"


def _load_pipeline_module():
    spec = importlib.util.spec_from_file_location("fm04a_synthetic_pipeline", PIPELINE_SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"could not load pipeline module from {PIPELINE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("fm04a_synthetic_pipeline", module)
    spec.loader.exec_module(module)
    return module


def _seed_repo(tmp_path: Path) -> Path:
    """Seed a minimal fake repo root containing the GS-001 FRD fixture."""
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    repo_root = tmp_path / "fake_repo"
    gs001_dir = repo_root / "golden_samples" / "GS-001"
    gs001_dir.mkdir(parents=True)
    target = gs001_dir / "gs001_result.frd"
    # Use a hard symlink to avoid copying ~MB of FRD bytes per test invocation
    target.symlink_to(GS001_FRD)
    return repo_root


def test_synthetic_pipeline_returns_zero_and_populates_spine(tmp_path: Path) -> None:
    repo_root = _seed_repo(tmp_path)
    module = _load_pipeline_module()

    rc = module.main(["--repo-root", str(repo_root), "--case-id", "CASE-FM04A-PYTEST"])
    assert rc == 0

    sidecar_dir = repo_root / "project_state" / "graph_executor" / "CASE-FM04A-PYTEST" / "ballistic"
    metrics_path = sidecar_dir / "ballistic_metrics.json"
    dt_path = sidecar_dir / "time_step_convergence.json"
    mesh_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / "CASE-FM04A-PYTEST"
        / "mesh"
        / "mesh_convergence.json"
    )

    assert metrics_path.exists()
    assert dt_path.exists()
    assert mesh_path.exists()

    metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics_payload["status"] == "candidate_observed"
    assert metrics_payload["perforation_marker"] == "perforated_candidate"
    assert "tier1_engineering_candidate" in metrics_payload["claim_boundary"]

    dt_payload = json.loads(dt_path.read_text(encoding="utf-8"))
    assert dt_payload["candidate_stability"] == "candidate_observed_stable"
    assert dt_payload["parameter"] == "time_step_dt"

    mesh_payload = json.loads(mesh_path.read_text(encoding="utf-8"))
    assert mesh_payload["candidate_stability"] == "candidate_observed_stable"
    assert mesh_payload["parameter"] == "mesh_level"


def test_synthetic_pipeline_does_not_pollute_real_golden_samples(tmp_path: Path) -> None:
    """Sanity check: pipeline writes ONLY under project_state/ — never golden_samples/."""
    repo_root = _seed_repo(tmp_path)
    module = _load_pipeline_module()

    rc = module.main(["--repo-root", str(repo_root), "--case-id", "CASE-FM04A-NOPOLLUTE"])
    assert rc == 0

    # No new entries appear under golden_samples/ besides the seeded GS-001 link
    gs_entries = sorted((repo_root / "golden_samples").iterdir())
    assert [p.name for p in gs_entries] == ["GS-001"]
    # synthetic case landed under project_state/synthetic_cases/, NOT golden_samples/
    assert (repo_root / "project_state" / "synthetic_cases" / "CASE-FM04A-NOPOLLUTE").is_dir()


def test_synthetic_pipeline_carries_tier1_wording_in_payload(tmp_path: Path) -> None:
    repo_root = _seed_repo(tmp_path)
    module = _load_pipeline_module()

    rc = module.main(["--repo-root", str(repo_root), "--case-id", "CASE-FM04A-TIER1-WORDING"])
    assert rc == 0

    expected_path = (
        repo_root
        / "project_state"
        / "synthetic_cases"
        / "CASE-FM04A-TIER1-WORDING"
        / "expected_results.json"
    )
    payload = json.loads(expected_path.read_text(encoding="utf-8"))
    assert payload["status"] == "insufficient_evidence"
    assert "Tier 2 promotion deferred to FM-04b" in payload["status_reason"]
    assert payload["analysis_type"] == "explicit_dynamics_ballistic_candidate"
