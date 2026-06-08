"""ADR-028 P-fidelity — the machine-checkable Tier-0/Tier-1 fidelity discriminator.

This is the anti-over-claim primitive that UNBLOCKS honestly crossing the tool wall (the
deferred geometry.run dummy-mode): it lets the coverage model distinguish a real tool run
on DUMMY data (tier_0_dummy) from one on REAL data (tier_1_real), WITHOUT ever inflating
the N/13 agent-driven count (which is keyed purely on StageProvenance). The live PRODUCER
is deferred to the next slice; these tests are the discriminator's genuine in-slice consumer
(it ships exercised, not as orphaned infra). They prove:

* the vocabulary is a CLOSED 3-literal set and the tier is DERIVED from data_real (no drift);
* a no-tool stage emits NEITHER key (back-compat: existing runs byte-unchanged);
* the emitted metrics carry NO measurement-shaped keys (the anti-vacuous-pass invariant the
  next slice depends on) and NO provenance key (fidelity is orthogonal to the N/13 count);
* the wire shape mirrors metrics.recovery (flat fidelityTier survives, nested fidelity rides
  StageMetrics extra="allow"); and
* a live run_sync still reports exactly 6/13 agent-driven and emits no fidelity key (no
  producer yet) — the never-inflate-N/13 invariant, end-to-end.
"""

from __future__ import annotations

import pytest

from app.services.workflow.mock_pipeline import MockWorkflowStore
from schemas.workflow_state import StageMetrics, StageProvenance, StageStatus, WorkflowStage

from agents.state_projection import StageFidelityTier, fidelity_metrics

# Measurement-shaped keys a vacuous dummy pass must NEVER surface as the discriminator.
_MEASUREMENT_KEYS = (
    "watertight",
    "manifold",
    "volume_m3",
    "shortEdges",
    "slivers",
    "selfIntersections",
)
_CLOSED_SET = {"not_applicable", "tier_0_dummy", "tier_1_real"}


# --- the closed vocabulary + derive-from-data_real invariant -----------------


def test_fidelity_vocabulary_is_a_closed_three_literal_set() -> None:
    assert {t.value for t in StageFidelityTier} == _CLOSED_SET


def test_no_tool_stage_emits_nothing() -> None:
    # planning-only / scripted (no tool) -> implicit not_applicable -> byte-unchanged metrics
    assert fidelity_metrics(tool_ran=False, data_real=False, disclosure="x") == {}
    assert fidelity_metrics(tool_ran=False, data_real=True, disclosure="x") == {}


def test_dummy_data_is_tier_0_and_data_real_false() -> None:
    m = fidelity_metrics(tool_ran=True, data_real=False, disclosure="未运行真实 CAD 内核")
    assert m["fidelityTier"] == StageFidelityTier.TIER_0_DUMMY.value
    assert m["fidelity"]["tier"] == "tier_0_dummy"
    assert m["fidelity"]["toolRan"] is True
    assert m["fidelity"]["dataReal"] is False
    assert m["fidelity"]["disclosure"]  # a dummy run MUST carry a non-empty caveat


def test_dummy_disclosure_is_enforced_not_merely_conventional() -> None:
    """A tier_0_dummy result MUST carry a non-empty caveat — ENFORCED by the helper, not
    just asserted on a fixture (Codex P-fidelity R0 P2). A blank disclosure for a dummy run
    raises, so a dummy/sandbox result can never ship without an honesty hedge."""
    with pytest.raises(ValueError, match="tier_0_dummy requires a non-empty disclosure"):
        fidelity_metrics(tool_ran=True, data_real=False, disclosure="")
    with pytest.raises(ValueError):
        fidelity_metrics(tool_ran=True, data_real=False, disclosure="   ")


def test_real_data_is_tier_1_and_data_real_true() -> None:
    # a GENUINE (tier_1_real) result may omit the caveat — enforcement is dummy-only
    m = fidelity_metrics(tool_ran=True, data_real=True, disclosure="")
    assert m["fidelityTier"] == StageFidelityTier.TIER_1_REAL.value
    assert m["fidelity"]["dataReal"] is True


def test_tier_iff_data_real_invariant() -> None:
    dummy = fidelity_metrics(tool_ran=True, data_real=False, disclosure="d")
    real = fidelity_metrics(tool_ran=True, data_real=True, disclosure="d")
    assert dummy["fidelityTier"] == "tier_0_dummy"
    assert real["fidelityTier"] == "tier_1_real"
    # both emitted tiers are members of the closed vocabulary (no drift)
    assert dummy["fidelityTier"] in _CLOSED_SET
    assert real["fidelityTier"] in _CLOSED_SET


# --- anti-vacuous-pass + orthogonal-to-provenance invariants -----------------


def test_emitted_metrics_carry_no_measurement_keys() -> None:
    """The discriminator must NEVER carry measurement-shaped keys — a dummy producer that
    surfaced watertight/manifold/volume would launder a vacuous pass into a measured
    validation. Pinned here so the deferred geometry.run slice cannot regress it."""
    m = fidelity_metrics(tool_ran=True, data_real=False, disclosure="d")
    all_keys = set(m) | set(m["fidelity"])
    for key in _MEASUREMENT_KEYS:
        assert key not in all_keys


def test_fidelity_never_carries_provenance() -> None:
    # fidelity is orthogonal to StageProvenance (the SOLE N/13 input); it must never carry
    # a provenance key that could be mistaken for an agent-driven flip.
    m = fidelity_metrics(tool_ran=True, data_real=False, disclosure="d")
    assert "provenance" not in m
    assert "provenance" not in m["fidelity"]


def test_wire_shape_mirrors_recovery_through_stagemetrics() -> None:
    """StageMetrics (extra="allow") accepts the fidelity keys; on the wire the flat
    fidelityTier survives as a string while fidelity is a nested object — so the FE parser
    keeps the disclosure but drops the nested evidence (the never-inflate-N/13 mechanism)."""
    m = fidelity_metrics(tool_ran=True, data_real=False, disclosure="未运行真实 CAD 内核")
    dumped = StageMetrics.model_validate(m).model_dump(by_alias=True, exclude_none=True)
    assert dumped["fidelityTier"] == "tier_0_dummy"  # flat string -> survives FE parser
    assert isinstance(dumped["fidelity"], dict)  # nested -> dropped by FE parser


# --- the live pipeline: never-inflate-N/13, end-to-end -----------------------


def _agent_driven(run) -> int:
    return sum(1 for s in run.stages if s.provenance is not StageProvenance.SCRIPTED_DEMO)


def test_default_run_emits_no_fidelity_key() -> None:
    run = MockWorkflowStore().run_sync(label=None)
    for s in run.stages:
        assert "fidelityTier" not in s.metrics.model_dump(by_alias=True, exclude_none=True)


def test_non_naca_request_emits_no_fidelity_and_stays_six_of_thirteen() -> None:
    # A NON-NACA family (bracket) stays on the planning stand-in — no tool runs, so no
    # fidelity key is emitted (the P-geomrun crossing is NACA-gated). Coverage stays 6/13.
    run = MockWorkflowStore().run_sync(user_request="对支架做静力分析，关注应力与位移")
    assert _agent_driven(run) == 6  # intake + geometry-plan + material + BC + load + routing
    for s in run.stages:
        assert "fidelityTier" not in s.metrics.model_dump(by_alias=True, exclude_none=True)


# --- the real geometry-node dummy crossing (P-geomrun) -----------------------

_GEOM_MEASUREMENT_KEYS = (
    "watertight",
    "manifold",
    "volume_m3",
    "minFeatureSizeM",
    "boundingBoxMm",
    "valid",
)


def test_naca_request_crosses_to_real_geometry_node_as_tier_0_dummy(monkeypatch) -> None:
    """A NACA/wing request crosses to the REAL agents.geometry.run node (dummy regime). The
    ONLY net-new claim is toolRan=True (tier_0_dummy) — NOT a validation: NO measurement
    keys, honesty flags pinned False, disclosure substrings present, N/13 still 6/13."""
    # force the dummy regime so the test is deterministic regardless of a local FreeCAD
    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    run = MockWorkflowStore().run_sync(user_request="分析这个机翼 NACA0012 的结构强度")
    geom = next(s for s in run.stages if s.stage is WorkflowStage.GEOMETRY_VALIDATION)
    assert geom.provenance is StageProvenance.DETERMINISTIC_AGENT
    # Rank-3 honesty pin: a tier_0_dummy ran-clean crossing is WARNING (passing-with-caveats),
    # never a green SUCCESS — the badge must not visually imply a real (tier_1+) validation.
    assert geom.status is StageStatus.WARNING
    m = geom.metrics.model_dump(by_alias=True, exclude_none=True)
    assert m["fidelityTier"] == "tier_0_dummy"  # the net-new fact: real node ran, dummy data
    # anti-vacuous-pass: NO measurement / valid key is surfaced as a result
    for k in _GEOM_MEASUREMENT_KEYS:
        assert k not in m
    assert m["cadKernelRan"] is False  # no real kernel ran (FREECAD_AVAILABLE=False)
    assert m["defectCheckRun"] is False  # the check was vacuous (sidecar tautology)
    # disclosure substrings machine-pinned so the claim cannot silently inflate (Codex
    # P-geomrun R0 P2: pin the FULL contract, not just the FREECAD_AVAILABLE token)
    expl = geom.agent_explanation or ""
    assert "ADR-008 N-3" in expl
    assert "FREECAD_AVAILABLE=False" in expl  # the no-kernel fact, not just the token
    assert "10 字节" in expl  # the placeholder STEP size
    assert "tautology" in expl  # the vacuous valid=True
    assert "defectCheckRun=False" in expl  # no meaningful defect check
    assert "未验证" in expl  # explicit "no geometry validated"
    assert "固定 NACA0012" in expl and "非从请求" in expl  # fixed stand-in profile disclosed
    # N/13 UNCHANGED: the crossing UPGRADES geometry's fidelity, it does not add a count
    assert _agent_driven(run) == 6
    # ONLY GEOMETRY_VALIDATION carries the fidelity flag
    for s in run.stages:
        if s.stage is not WorkflowStage.GEOMETRY_VALIDATION:
            assert "fidelityTier" not in s.metrics.model_dump(by_alias=True, exclude_none=True)


def test_geometry_stage_state_gates_naca_only(monkeypatch) -> None:
    from agents.state_projection import geometry_stage_state

    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    naca = geometry_stage_state("r", "分析机翼 NACA0012")
    bracket = geometry_stage_state("r", "分析钢制支架")
    nm = naca.metrics.model_dump(by_alias=True, exclude_none=True)
    bm = bracket.metrics.model_dump(by_alias=True, exclude_none=True)
    assert nm["fidelityTier"] == "tier_0_dummy"  # naca crosses to the real node
    assert "fidelityTier" not in bm  # bracket stays on the planning stand-in
    assert bm["cadKernelRan"] is False  # planning stand-in unchanged


def test_missing_geometry_path_refuses_to_claim_tool_ran(monkeypatch) -> None:
    """If agents.geometry.run returns without the geometry_path wiring fact, the projector
    must REFUSE to build a success stage that hard-claims toolRan=True (Codex P-geomrun R0
    P1) — it raises rather than fabricate the wiring claim."""
    from agents import state_projection

    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", False)
    monkeypatch.setattr("agents.geometry.run", lambda state: {"fault_class": None})
    with pytest.raises(RuntimeError, match="no geometry_path"):
        state_projection.geometry_dummy_exec_to_stage_state("r", "分析机翼 NACA0012")


def test_freecad_present_falls_back_to_planning_not_mislabeled_tier_0(monkeypatch) -> None:
    """Defense-in-depth: a host WITH a real FreeCAD kernel would produce real geometry — the
    tier_0_dummy projector must never run against it, so the dispatcher falls back to the
    planning stand-in (no fidelity flag) rather than mislabel a real result tier_0_dummy."""
    from agents.state_projection import geometry_stage_state

    monkeypatch.setattr("tools.freecad_driver.FREECAD_AVAILABLE", True)
    naca = geometry_stage_state("r", "分析机翼 NACA0012")
    nm = naca.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "fidelityTier" not in nm  # fell back to planning; no tier_0 mislabel
