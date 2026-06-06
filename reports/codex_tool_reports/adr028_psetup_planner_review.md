# Codex Review — ADR-028 P-setup: analyze_setup planner node (R0 → R1 APPROVE)

**Scope (core honesty surface, NOT HF1):** wire the MATERIAL_ASSIGNMENT / BOUNDARY_CONDITIONS
/ LOAD_CASES demo stages to a NEW deterministic rule-based planner agent
(`agents.state_projection.analyze_setup`), mirroring the shipped `analyze_intake` (P1) and
`decide_route` (P3). Raises honest agent coverage from **2/13 → 5/13** on a genuine-request run.
No HF1 file is edited.

## Provenance: workflow-decided, then implemented

The slice was chosen by a 13-agent decision Workflow (4 grounded readers → 4 lens-diverse
proposers → 4 adversarial verifiers → synthesizer). It **resolved an honesty concern raised
earlier in-session** ("projecting material/BC/load from the rule-based intake would be
fabrication"): the accepted design is NOT a projection of intake output — it is a DEDICATED
planner doing its own rule-based derivation, and when the request gives no hint it falls back to
a documented default WHILE DISCLOSING it. The adversarial phase also rejected the runner-up
("fail-path routing") for a real honesty trap (a hard-injected demo failure has no reviewer, so
`verdict='re-run'` would fabricate a reviewer decision).

## Files

- `agents/state_projection.py` — `analyze_setup()` + `SetupOutcome`/`SetupDecision` + 3 keyword
  rule tables (material/BC/load) + `setup_outcome_to_stage_state()` projector + `SETUP_STAGES`.
  Each decision carries `from_hint` and discloses defaults in its explanation. Agent layer (may
  import schemas freely); defines its display vocabulary locally (does NOT import backend).
- `backend/app/workbench/agent_facade.py` — `run_node` allow-set extended to the 3 setup stages
  (still raises `NotImplementedError` for every tool/artifact-bound stage). No `schemas.sim_state`
  import (ADR-015 rule 3).
- `backend/app/services/workflow/mock_pipeline.py` — `_AGENT_REQUEST_STAGES` (defined locally
  from schema enums — no `agents.*` import) + the delegation guard extended to the 3 stages, same
  verbatim chain as intake (`error is None ∧ specs is STAGE_SPECS ∧ genuine user_request`).
- `backend/tests/test_agent_facade_setup.py` — **new**, 13 tests (input-dependence, hard
  default-disclosure, per-stage provenance, barrier-intact, scripted-without-request, scripted-on-
  failure-injection, agent-driven-on-request).
- `backend/tests/test_agent_facade_intake.py` — `_AGENT_STAGES` expanded 2→5 (additive coverage,
  not a threshold loosening; the OTHER 8 stages still asserted scripted_demo).

## R0 — CHANGES_REQUIRED (1 actionable finding; design otherwise confirmed)

- **P3 section confirmed the design is sound** (verbatim): no ADR-015 violation (mock_pipeline
  defines the set locally, facade stays the `agents.*` choke point, state_projection imports no
  backend); guard chain correct (and a separate `solve_ctx` guard is NOT needed here since
  `specs is STAGE_SPECS` is the demo-path discriminator); barrier intact; test expansion additive.
- **P2 (the only actionable finding) — fixed verbatim.** `_decide_load` set `from_hint=True` when
  only a magnitude/unit was present but still used the `tip_load` default for kind/topology
  *without disclosing the topology defaulted* — e.g. `"施加 100N"` read "识别载荷 = 末端集中力 100N",
  a partial over-claim. **Fix:** track `kind_from_hint` and `mag_from_hint` separately, branch the
  explanation into 4 honest cases (both / kind-only / magnitude-only-with-disclosed-default-topology
  / neither), and add a machine-checkable `kindFromHint` metric. Pinned by
  `test_setup_load_magnitude_only_discloses_default_topology` (asserts `kindFromHint is False` +
  `"默认"` in the explanation).

## R1 — **APPROVE** (no remaining findings)

Verbatim: *"the P2 finding is resolved. Case (3) now separates `kindFromHint` from magnitude
detection and the explanation explicitly says the load magnitude was recognized while topology was
unspecified and defaulted. That removes the partial over-claim. … I don't see a new D2/honesty
issue introduced. VERDICT: APPROVE."*

(Tooling note: the R1 relay first hung on a background-mode stdin read; re-running with stdin
closed (`< /dev/null`) produced the verdict — a harness invocation quirk, not a code signal.)

## Honest coverage delta (D2)

A genuine-request run goes **2/13 → 5/13** agent-driven (intake + material + BC + load + routing).
Default no-request run stays **1/13** (routing only); label-only and failure-injection runs keep
the 3 setup stages `scripted_demo`. The 8 tool/artifact-bound stages remain `scripted_demo` (the
artifact wall is not crossed). Claim tier UNCHANGED: Tier-0 demo with honest per-stage provenance;
the planner claims ONLY the setup DECISION (which material / BC topology / load), with defaults
disclosed — no Tier-1/2 implied, no mesh/solver numbers claimed.

## Gates

- setup + intake + routing + pipeline + le10 → all pass; ADR-015 facade-discipline (root) passes.
- Full root suite `pytest tests/` = **2680 passed, 6 skipped**; full backend = **1243 passed, 24
  skipped, 1 xfailed** (minus pre-existing local openai/httpx `proxies` collection errors in
  untouched files). `ruff check agents` + format clean.

**Closure:** R0 CHANGES_REQUIRED → P2 fixed-verbatim + test-pinned → **R1 APPROVE**.
