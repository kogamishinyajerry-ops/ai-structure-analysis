# Codex Review — ADR-028 P-geomplan: deterministic geometry-PLANNING node (R0 APPROVE)

**Scope (core honesty surface, NOT HF1):** wire the GEOMETRY_VALIDATION demo stage to a NEW
deterministic rule-based agent `agents.state_projection.analyze_geometry_plan` (mirrors the shipped
analyze_intake / analyze_setup), flipping its provenance scripted_demo → deterministic_agent on a
genuine-request run and raising honest coverage **5/13 → 6/13**. CALL-ONLY: `agents.geometry.run` /
`tools.generate_geometry` / `checkers.geometry_checker` are NOT called — no CAD kernel runs, no STEP
is generated. No HF1 file edited (path-guard EXIT=0).

## Provenance: 11-agent pre-flight chose this over the riskier dummy-STEP path

A pre-flight scoping Workflow (run `wf_495fdd69-035`; 4 grounded readers → 3 lens-diverse proposers
→ 3 adversarial verifiers → synthesizer) **DEFERRED** the higher-coverage alternative (Proposal 2:
wire the real `geometry.run` in FreeCAD-absent "dummy" mode) as a honesty hazard: the dummy
`check_geometry` pass is **vacuous** (`build_geometry_metadata(solid=None)` hardcodes
watertight/manifold/volume; `model.step` is a 10-byte literal `"Dummy STEP"`; the driver itself logs
"NOT valid for Demo Gate" per ADR-008 N-3), and the coverage model has **no machine-checkable
Tier-0 discriminator**, so a dummy result would read as a real validation. It chose **Proposal 1
(P-geomplan)** — the only option that raises coverage WITHOUT touching the dummy STEP — and gated
Proposal 2 behind a future machine-checkable dummy/Tier-0 discriminator.

## The central honesty question (and why the flip is defensible)

Is it honest to flip a stage **named** "GEOMETRY_VALIDATION" to `deterministic_agent` when the agent
only PLANS (decides geometry family), not validates? The contract says StageProvenance labels the
**text source** of `agent_explanation`/`next_action` — and that text IS genuinely agent-authored. Six
mitigations narrow the claim so the flip cannot be read as "geometry was validated":
1. the explanation states verbatim `未运行 CAD 内核、未生成 STEP、未做缺陷校验 —— 仅确定性几何规划（未调用 LLM）`;
2. metrics carry machine-checkable honesty flags `cadKernelRan=False` / `defectCheckRun=False` +
   planning-intent fields (`geometryFamily`/`refSource`/`fromHint`) ONLY — never measurement-shaped
   keys (`shortEdges`/`slivers`/`selfIntersections`);
3. it **REPLACES the scripted spec's FABRICATED** `{shortEdges:2, slivers:0, selfIntersections:0}`
   (which implied a defect check found 2 short edges) on the genuine-request path — a **net honesty
   improvement** over the status quo;
4. `current_object` is `geometry_plan`, NOT the scripted `bracket_solid` (which implies a validated solid);
5. the no-request path is UNCHANGED (stays scripted_demo with its scripted Tier-0 metrics);
6. failure-injection / real-LE10 paths stay scripted (same delegation guard chain as P-setup).

**Residual caveat (Codex-noted, not a finding):** the stage *name* itself remains potentially
misleading independent of the (correctly narrowed) text/metrics. Accepted as an interpretive residual,
not a code defect; the real CAD-kernel geometry validation remains OWED (Proposal 2, deferred).

## Files

- `agents/state_projection.py` — `analyze_geometry_plan(user_request)` + `GeometryPlanOutcome` +
  `_GEOMETRY_RULES`/`_GEOMETRY_DEFAULT` family rule table + `geometry_plan_to_stage_state` projector.
  Agent layer (imports schemas freely, no backend). `__all__` + module docstring updated.
- `backend/app/workbench/agent_facade.py` — `run_node` GEOMETRY_VALIDATION branch (sole `agents.*`
  importer; request-string-in / StageState-out; no `schemas.sim_state` import). Docstring updated.
- `backend/app/services/workflow/mock_pipeline.py` — `GEOMETRY_VALIDATION` added to the local
  `_AGENT_REQUEST_STAGES` frozenset (no `agents.*` import); delegation comment updated. STAGE_SPECS
  GEOMETRY_VALIDATION (the scripted no-request fallback) left intact.
- `backend/tests/test_agent_facade_geometry_plan.py` — **new**, 9 tests (input-dependence,
  default-disclosure, no-CAD-kernel disclosure, no-measurement-keys, facade provenance,
  current_object≠bracket_solid, live agent-driven-on-request, scripted-without-request,
  scripted-on-failure-injection).
- `backend/tests/test_agent_facade_intake.py` — `_AGENT_STAGES` expanded 5→6 (additive coverage
  assertion; the OTHER 7 stages still asserted scripted_demo — NOT a threshold loosening).

## R0 — **APPROVE** (no findings)

Verbatim: *"APPROVE. Findings: none. The honesty mitigations are sufficient for this slice. The stage
name remains potentially misleading, but the implementation narrows the claim in the emitted
explanation, metrics, and current_object, and removes fabricated defect metrics on the genuine-request
path. Given the stated contract that provenance labels the stage text source, flipping
GEOMETRY_VALIDATION to deterministic_agent is defensible here. ADR-015 boundaries also look preserved …
The _AGENT_STAGES test change is additive rather than a threshold loosening."* (gpt-5.5 xhigh,
contained relay, 12,975 tokens.)

## Honest coverage delta (D2)

Genuine-request success run: **5/13 → 6/13** agent-driven (intake + **geometry plan** + material + BC
+ load + routing). Default no-request run unchanged (routing only); label-only / failure-injection /
real-LE10 keep GEOMETRY_VALIDATION scripted_demo. Claim tier UNCHANGED: Tier-0 demo with honest
per-stage provenance; the planner claims ONLY the geometry-FAMILY decision, with `cadKernelRan=False`
disclosed — **no CAD validation is claimed**, the artifact/tool wall is NOT crossed.

## Gates

- geometry (9) + setup (13) + intake (14) + routing (12) + recovery (10) + pipeline (10) → 68 pass.
- ADR-015 facade-discipline (root) → 27 pass. m2_fake_orchestrator + geometry + mock regression → 41 pass.
- Full backend suite → **1263 pass, 24 skip, 1 xfailed** (minus pre-existing local openai/httpx
  `proxies` collection errors in test_report/test_solver/test_api).
- Frontend `workflowClient` provenance-coverage → 6 pass (counter unchanged; correctly counts the new
  deterministic stage with no frontend edit). `ruff check/format agents` clean. `hf1_path_guard` EXIT=0.

**Closure:** R0 **APPROVE** — no fix iterations needed. Local commit, `confidence: med`, no push.
