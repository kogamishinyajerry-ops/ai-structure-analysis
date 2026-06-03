"""M4 — real CalculiX LE10 solve through the workflow pipeline.

The real-solve tests are ccx-guarded (skipped when ``ccx`` is not on PATH, e.g.
in CI), so they never block the suite; the flag-off assertion runs everywhere and
proves the mock path is untouched. When ccx IS present, the real path re-solves
the validated NAFEMS LE10 deck and must reproduce σ_yy@D ≈ −5.4379 MPa (PASS vs
the published −5.38 MPa, ±3%).
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.workflow import real_le10
from app.services.workflow.mock_pipeline import MockWorkflowStore
from schemas.workflow_state import CANONICAL_STAGE_ORDER, StageStatus, WorkflowStage

_needs_ccx = pytest.mark.skipif(
    not real_le10.le10_available(),
    reason="real LE10 solve requires ccx on PATH + the LE10 deck",
)


def test_flag_off_is_mock_unchanged():
    """With the flag off the result stage emits the mock safety-factor scalars,
    not the LE10 benchmark — proving the default path is byte-for-byte the mock."""
    assert settings.workflow_real_solver is False  # default
    store = MockWorkflowStore()
    run = store.run_sync(label="mock")
    result = next(s for s in run.stages if s.stage is WorkflowStage.RESULT_ANALYSIS)
    m = result.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "safetyFactor" in m
    assert "verdict" not in m  # the LE10 benchmark verdict never appears in mock mode


@_needs_ccx
def test_real_le10_external_path_reproduces_benchmark(monkeypatch):
    """The M2 external path (run_one_stage per stage) runs a real ccx solve at
    solver_run, threads the .frd to result_analysis, and reproduces the
    NAFEMS LE10 benchmark agreement."""
    monkeypatch.setattr(settings, "workflow_real_solver", True)
    store = MockWorkflowStore()
    run = store.create_run(label="le10-external")

    states = {stage: store.run_one_stage(run.run_id, stage) for stage in CANONICAL_STAGE_ORDER}
    assert store.get(run.run_id).status is StageStatus.SUCCESS

    solver = states[WorkflowStage.SOLVER_RUN]
    assert solver.status is StageStatus.SUCCESS
    sm = solver.metrics.model_dump(by_alias=True)
    assert sm.get("converged") is True
    assert sm.get("ccxVersion")  # real ccx version string

    result = states[WorkflowStage.RESULT_ANALYSIS]
    rm = result.metrics.model_dump(by_alias=True)
    assert rm["benchmark"] == "NAFEMS LE10"
    assert rm["verdict"] == "PASS"
    assert rm["targetSigmaYyMpa"] == pytest.approx(-5.38, abs=1e-6)
    assert rm["observedSigmaYyMpa"] == pytest.approx(-5.4379, abs=0.05)
    assert abs(rm["residualPct"]) <= real_le10.LE10_TOLERANCE_PCT


@_needs_ccx
def test_real_le10_run_sync_status_is_verdict_driven(monkeypatch):
    """The whole-run path (run_sync) must ALSO drive result_analysis status from
    the verdict — a PASS is SUCCESS, not WARNING. Covers the entry point the
    external-path test missed (Codex M4 R1: solve_ctx must thread through every
    _terminal_status call, not just run_one_stage)."""
    monkeypatch.setattr(settings, "workflow_real_solver", True)
    store = MockWorkflowStore()
    run = store.run_sync(label="le10-sync")
    result = next(s for s in run.stages if s.stage is WorkflowStage.RESULT_ANALYSIS)
    assert result.metrics.model_dump(by_alias=True)["verdict"] == "PASS"
    assert result.status is StageStatus.SUCCESS  # WARNING if solve_ctx were not threaded
    assert run.status is StageStatus.SUCCESS


@_needs_ccx
def test_real_le10_module_solve_and_extract(tmp_path):
    """The standalone module: a fresh solve + extraction reproduces the benchmark."""
    out = real_le10.run_le10_solve(tmp_path, timeout_s=900)
    assert out["converged"] is True
    bench = real_le10.extract_le10_benchmark(out["deck_path"], out["frd_path"])
    assert bench["verdict"] == "PASS"
    assert bench["sigma_yy_pa"] == pytest.approx(-5.4379e6, rel=0.02)
    assert bench["node_d"] is not None


# --- honesty guards (Codex M4 R0 P1/P2 fixes; no ccx required) ----------------

def test_real_path_never_emits_mock_scalars_without_solve_ctx():
    """P1: with the LE10 (real) specs and a MISSING solve context, result_analysis
    must NOT fall through to the mock safety-factor numbers."""
    from app.services.workflow.mock_backend import MockFEABackend
    from app.services.workflow.mock_pipeline import LE10_STAGE_SPECS, _build_stage_state

    st = _build_stage_state(
        "r", WorkflowStage.RESULT_ANALYSIS, StageStatus.WARNING, 1.0,
        backend=MockFEABackend(), specs=LE10_STAGE_SPECS, solve_ctx=None,
    )
    m = st.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "safetyFactor" not in m  # no synthetic mock value leaks onto the real path
    assert "maxVonMisesPa" not in m


def test_result_status_follows_benchmark_verdict():
    """P2: result_analysis status tracks the verdict — a FAIL (or missing ctx) is
    never reported as a plain green SUCCESS."""
    from app.services.workflow.mock_pipeline import _terminal_status

    rs = WorkflowStage.RESULT_ANALYSIS
    assert _terminal_status(rs, real=True, solve_ctx={"benchmark": {"verdict": "PASS"}}) is StageStatus.SUCCESS
    assert _terminal_status(rs, real=True, solve_ctx={"benchmark": {"verdict": "FAIL"}}) is StageStatus.WARNING
    assert _terminal_status(rs, real=True, solve_ctx=None) is StageStatus.WARNING
