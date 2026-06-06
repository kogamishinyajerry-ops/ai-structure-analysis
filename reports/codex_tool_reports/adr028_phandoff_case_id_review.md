# Codex Review — ADR-028 P-handoff: intake→geometry case_id data dependency (R0 APPROVE)

**Scope (risk-tier: cross-file + agent-layer; same gate as P-geomrun/P-fidelity):** thread the
PROJECT_INTAKE node's request-derived `caseId` into the GEOMETRY_VALIDATION stage so the geometry
projection CONSUMES intake's decision instead of fabricating its own `AI-FEA-P0-05` — the FIRST
real upstream→downstream inter-agent data dependency in the live pipeline. CALL/wire-only; no HF1
override (agents/geometry.py untouched; it still reads `plan.geometry` only, never `plan.case_id`).

## Honesty floor (the deliverable)

The handoff is real ONLY at the wire/projection layer. End-user value ~zero (the case number was
already correct via intake) — its value is INTERNAL ADR-028 architecture progress (proving the
first genuine inter-agent data seam). It threads ONE field (the case number), NOT
analysis_type/objectives. Machine-pinned invariants (all upheld, Codex-confirmed):

- **N/13 UNCHANGED at 6/13** — provenance stays `deterministic_agent`; `caseId` is a plain wire
  string in metrics, NOT a StageProvenance flip (the SOLE N/13 input).
- **NO measurement key added** — `caseId` is not watertight/manifold/volume/valid; the
  anti-vacuous-pass invariant from P-geomrun holds (test-pinned).
- **Fidelity tier unchanged** — still `tier_0_dummy` on the crossing path; the case number does
  not upgrade fidelity.
- **Honest fallback** — an absent OR invalid `upstream_case_id` falls back to the `AI-FEA-P0-05`
  stand-in, and the disclosure says so (`非真实接力`), never claiming a handoff; a real handoff
  says `接力消费` + `partial honest handoff`. Neither can be misread as the other (test-pinned).
- **ADR-015 intact** — `mock_pipeline.py` reads the already-projected intake `caseId` via
  `_intake_case_id(run.stages)` (plain `model_dump(by_alias=True)` read); NO `agents.*` import
  (line-57 pin). The facade (`agent_facade.py`) stays the sole `agents.*` importer.
- **Defensive gate** — `_valid_case_id` (the same gate intake's `_canonical_case_id` uses) rejects
  a malformed upstream value BEFORE `SimPlan` construction, so a garbage id falls back rather than
  raising a pydantic ValidationError.

## Plumbing (grounded, not assumed)

All 3 drivers (`run_one_stage` M2, `run_sync` M1-sync, `_advance` M1-async) build `run.stages[idx]`
in canonical stage order; PROJECT_INTAKE is idx 0, GEOMETRY_VALIDATION idx 2 — so at geometry-build
time the intake stage is already projected into `run.stages[0]`. `_intake_case_id` reads it back.
When building intake ITSELF, `run.stages[0]` is still the initial PENDING stage (no `caseId`) →
returns None → intake gets `existing_case_id=None` (unchanged behavior). The setup stages ignore
`existing_case_id`. So forwarding `existing_case_id=upstream_case_id` for all agent stages is safe.

## R0 — **APPROVE** (gpt-5.5 xhigh, static diff review, no fix rounds)

Verbatim: *"APPROVE. No P1/P2/P3 findings from the provided diffs/tests. Key checks pass textually:
`mock_pipeline.py` still avoids `agents.*`; `_intake_case_id` reads projected metrics only;
stale/self-read paths fall back to `None`; malformed IDs are gated before `SimPlan`; disclosure
distinguishes consumed handoff vs fallback; provenance and agent-driven count logic are not changed."*

## Files

- `agents/state_projection.py` — `geometry_dummy_exec_to_stage_state(+upstream_case_id)` consumes
  the intake case id (valid → use it; else `AI-FEA-P0-05` fallback), emits `caseId` metric, extends
  disclosure with a handoff/fallback clause; `geometry_stage_state(+upstream_case_id)` passthrough;
  imports `_valid_case_id`.
- `backend/app/workbench/agent_facade.py` — GEOMETRY_VALIDATION branch forwards
  `upstream_case_id=existing_case_id`.
- `backend/app/services/workflow/mock_pipeline.py` — `_intake_case_id(stages)` helper (no agents.*);
  `_build_stage_state(+upstream_case_id)` forwards it as `existing_case_id=` in the facade delegation;
  4 success-build call sites pass `upstream_case_id=_intake_case_id(run.stages)`. NOTE: this file
  carried PRE-EXISTING ruff-format drift (magic-trailing-comma) from earlier local slices; `ruff
  format` normalized it (mechanical one-arg-per-line reflow of untouched `_build_stage_state` calls).
- `backend/tests/test_intake_geometry_handoff.py` — NEW (6 tests): e2e caseId equals intake's and
  != stand-in; no measurement key / tier unchanged / N/13==6; disclosure distinguishes handoff vs
  fallback; valid upstream consumed; absent + malformed upstream fall back.

## Gates

- Handoff suite 6 pass; P-geomrun fidelity discriminator + geomplan + intake + recovery facade
  tests **53 pass**; ADR-015 facade-discipline **27 pass**; HF1 path guard EXIT=0; FE workflowClient
  **8 pass**; full backend **1312 pass / 21 skip / 1 xfail / 4 fail**. The 4 failures
  (`test_parsers` NL-intent ×3, `test_compliance` knowledge_base_linkage) are PRE-EXISTING +
  environmental (`code: invalid_api_key` — require a live LLM key; same family as the 3
  `proxies`-TypeError files always ignored) — VERIFIED by re-running them on clean HEAD with the
  P-handoff edits stashed: identical 4 failures. NOT a P-handoff regression.

## Open risks (carried)

- End-user value of this slice ~zero (case number was already correct via intake). Its value is
  INTERNAL architecture progress: the first genuine inter-agent data seam, de-risking the later
  analysis_type/objectives threading. Commit/UI narrative frames it as ARCHITECTURE progress, NOT a
  user capability, NOT a coverage increase.

**Closure:** R0 **APPROVE** (no fix rounds). Local commit, `confidence: med`, no push, no HF1 override.
