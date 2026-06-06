"""ADR-028 P-handoff — the FIRST real upstream→downstream inter-agent data dependency.

Before this slice every wired agent node produced its output from the user request alone;
the geometry node FABRICATED its own ``AI-FEA-P0-05`` case number, ignoring the case id the
upstream PROJECT_INTAKE node had already derived. P-handoff threads intake's request-derived
case id through the facade into the geometry stage so the geometry projection CONSUMES intake's
decision instead of inventing its own — a genuine inter-agent data dependency, not a cosmetic
relabel.

These tests pin the honesty floor of that handoff (it is real ONLY at the wire/projection
layer; the geometry computation itself still reads only ``plan.geometry``, never the case id):

* end-to-end the live pipeline's GEOMETRY_VALIDATION.caseId EQUALS PROJECT_INTAKE.caseId and is
  NOT the legacy ``AI-FEA-P0-05`` stand-in (the dependency is exercised, not asserted in the
  abstract);
* the handoff adds NO measurement key and does NOT touch provenance or the N/13 count
  (it threads ONE field — the case number — not analysis_type/objectives);
* an absent OR invalid upstream case id falls back to the stand-in AND the disclosure says so,
  so a fallback can never be misread as a real handoff (and vice-versa).
"""

from __future__ import annotations

from app.services.workflow.mock_pipeline import MockWorkflowStore

from agents.state_projection import (
    geometry_dummy_exec_to_stage_state,
    geometry_stage_state,
)
from schemas.workflow_state import StageProvenance, WorkflowStage

_STAND_IN = "AI-FEA-P0-05"
# A measurement-shaped key must NEVER ride alongside the handoff — the case id is plumbing,
# not a measured geometry result (the P-geomrun anti-vacuous-pass invariant must hold).
_MEASUREMENT_KEYS = (
    "watertight",
    "manifold",
    "volume_m3",
    "minFeatureSizeM",
    "boundingBoxMm",
    "valid",
)
_NACA_REQUEST = "分析这个机翼 NACA0012 的结构强度"


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def _stage(run, stage: WorkflowStage):
    return next(s for s in run.stages if s.stage is stage)


# --- end-to-end: the live pipeline consumes intake's case id -----------------


def test_intake_geometry_case_id_handoff(monkeypatch) -> None:
    """The geometry stage's caseId is the SAME case id the intake node derived — and is NOT
    the fabricated ``AI-FEA-P0-05`` stand-in. The first real upstream→downstream dependency."""
    # force the dummy regime so the crossing is deterministic regardless of a local FreeCAD
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    run = MockWorkflowStore().run_sync(user_request=_NACA_REQUEST)

    intake = _stage(run, WorkflowStage.PROJECT_INTAKE)
    geom = _stage(run, WorkflowStage.GEOMETRY_VALIDATION)
    intake_m = intake.metrics.model_dump(by_alias=True, exclude_none=True)
    geom_m = geom.metrics.model_dump(by_alias=True, exclude_none=True)

    # both nodes are genuinely agent-driven (intake derived the id; geometry consumed it)
    assert intake.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert geom.provenance is StageProvenance.DETERMINISTIC_AGENT

    # the data dependency: geometry consumes intake's exact case id, not the stand-in
    assert intake_m["caseId"] == geom_m["caseId"]
    assert geom_m["caseId"] != _STAND_IN
    assert geom_m["caseId"].startswith("AI-FEA-P")  # naming-compliant wire string

    # the handoff threads ONE plain string — it must not smuggle a measurement in
    for k in _MEASUREMENT_KEYS:
        assert k not in geom_m
    # ...nor touch the fidelity tier (still the dummy crossing) or the N/13 count
    assert geom_m["fidelityTier"] == "tier_0_dummy"
    assert _agent_driven(run) == 6


def test_handoff_disclosed_as_real_dependency_not_a_capability(monkeypatch) -> None:
    """The disclosure must state the case id was CONSUMED from intake (接力消费) AND that only
    the case number flows (analysis_type/objectives are NOT threaded) — so a reader can never
    mistake the handoff for a geometry capability or a full state handoff."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    run = MockWorkflowStore().run_sync(user_request=_NACA_REQUEST)
    expl = _stage(run, WorkflowStage.GEOMETRY_VALIDATION).agent_explanation or ""
    assert "接力消费" in expl  # consumed from the upstream node
    assert "partial honest handoff" in expl  # only the case number flows
    # the P-geomrun honesty pins are UNTOUCHED by P-handoff (no regression)
    assert "固定 NACA0012" in expl and "非从请求" in expl
    assert "tier_0_dummy" in expl


# --- the honest fallback: no handoff is disclosed as a stand-in --------------


def test_no_upstream_falls_back_to_stand_in(monkeypatch) -> None:
    """With no upstream case id the geometry node falls back to the stand-in — and the
    disclosure says it is a FALLBACK (非真实接力), never a handoff."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    stage = geometry_stage_state("r", _NACA_REQUEST)  # upstream_case_id defaults to None
    m = stage.metrics.model_dump(by_alias=True, exclude_none=True)
    assert m["caseId"] == _STAND_IN
    expl = stage.agent_explanation or ""
    assert "回退" in expl and "非真实接力" in expl
    assert "接力消费" not in expl  # a fallback must NOT claim a real handoff


def test_valid_upstream_is_consumed_directly(monkeypatch) -> None:
    """A valid upstream case id is consumed verbatim by the dummy projector."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    stage = geometry_dummy_exec_to_stage_state("r", _NACA_REQUEST, upstream_case_id="AI-FEA-P0-42")
    m = stage.metrics.model_dump(by_alias=True, exclude_none=True)
    assert m["caseId"] == "AI-FEA-P0-42"
    assert "接力消费" in (stage.agent_explanation or "")


def test_invalid_upstream_case_id_falls_back_not_crashes(monkeypatch) -> None:
    """Defense-in-depth: a malformed upstream value (e.g. a stray label) is REJECTED by the
    same _valid_case_id gate the intake node uses, so it falls back to the stand-in rather
    than crash SimPlan validation or ship a non-compliant case id."""
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    stage = geometry_dummy_exec_to_stage_state("r", _NACA_REQUEST, upstream_case_id="not-a-case-id")
    m = stage.metrics.model_dump(by_alias=True, exclude_none=True)
    assert m["caseId"] == _STAND_IN
    assert "非真实接力" in (stage.agent_explanation or "")
