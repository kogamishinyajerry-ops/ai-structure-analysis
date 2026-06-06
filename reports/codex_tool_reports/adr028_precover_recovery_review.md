# Codex Review — ADR-028 P-recover: two-agent fault recovery on the failure path (R0 APPROVE)

**Scope (core honesty surface, NOT HF1):** on an INJECTED demo failure, surface a GENUINE
reviewer→router recovery decision WITHOUT relabeling the failing stage. The failure prose stays
scripted (`provenance` / `agent_explanation` / `next_action` UNTOUCHED → stage stays
`scripted_demo`, the `N/13` agent-driven count never moves); the recovery rides `metrics.recovery`
(StageMetrics `extra="allow"`, no schema change) with its own `agentDriven` / `faultInjected` flags.
The recovery is the real two-agent decision: `agents.reviewer._review_upstream_fault` DERIVES the
verdict from the actual fault (RERUN_FAULTS membership), then `agents.router.route_reviewer` picks
the recovery node (ADR-004 fault→node map + MAX_RETRIES=3 cap). Deterministic, no LLM. No HF1 file
edited.

## Provenance: pre-flight workflow caught + corrected a honesty trap

The slice design went through a 7-agent pre-flight Workflow (run `wf_ba31be43-071`). Its
adversarial reviewer **rejected the original blueprint Option (b)** — "overwrite `next_action` but
keep `scripted_demo`" — as a LIE against the StageProvenance contract (it labels the
`agent_explanation`/`next_action` TEXT; overwriting that text while keeping the `scripted_demo`
label misrepresents agent-derived prose as scripted). The accepted model leaves the failing stage's
text+provenance fully untouched and surfaces recovery OUT-OF-BAND in `metrics.recovery`. This mirrors
the earlier P-setup adversarial finding (a hard-injected failure has no reviewer, so any verdict
that *claims* the agent diagnosed the fault would be fabrication) — hence the explanation explicitly
discloses the fault was INJECTED (`demo 注入、非 agent 诊断`), and only the verdict-derivation +
routing are claimed as agent-computed.

## Files

- `agents/state_projection.py` — `decide_recovery(*, fault_class, retry_budgets)` + `RecoveryOutcome`
  frozen dataclass (deliberately **no `provenance` field** — the failure is scripted, so the stage
  label is owned by the failing stage, not this decision). Verdict DERIVED from the real reviewer
  (`_review_upstream_fault({"history": []}, fc)`), node from the real router. Agent layer (imports
  schemas freely); reuses `_ROUTE_LABEL_ZH` from P3.
- `backend/app/workbench/agent_facade.py` — `decide_recovery` wrapper (the ONLY `agents.*` importer;
  `fault_class` is a plain wire string → no `schemas.sim_state` import, ADR-015 rule 3). `__all__`
  updated.
- `backend/app/services/workflow/mock_pipeline.py` — recovery block in `_build_stage_state`, gated
  `error is not None and specs is STAGE_SPECS` (mock-demo path only; mutually exclusive with the P3
  routing block which requires `error is None`). Attaches `metrics.recovery`; does NOT touch
  provenance / agent_explanation / next_action. Real-LE10 failure (`LE10_STAGE_SPECS`) gets no overlay.
- `backend/tests/test_agent_facade_recovery.py` — **new**, 10 tests: 7 facade-unit (incl. the
  `reference_mismatch` → Needs Review → human_fallback anti-fabrication trip-wire, and the retry-cap
  escalation) + 3 live-seam (recovery surfaced while stage stays scripted; needs-review branch
  end-to-end; real-LE10 no-overlay exclusion).

## R0 — **APPROVE** (no findings)

Verbatim: *"APPROVE. No findings. The slice keeps the injected failure stage prose/provenance
untouched, surfaces the genuine reviewer→router decision out-of-band under `metrics.recovery`,
preserves the facade boundary for `agents.*`, and excludes the `LE10_STAGE_SPECS` real-failure path
as required."* (gpt-5.5 xhigh, contained relay, 11,023 tokens.)

## Honest coverage delta (D2)

**No change to the `N/13` agent-driven count** — by design. Recovery is a failure-path overlay; the
failing stage stays `scripted_demo`. A genuine-request *success* run remains 5/13 (intake + material
+ BC + load + routing). What this slice adds is a genuine agentic decision **on the failure path**
that was previously absent, surfaced honestly without inflating any claim. Claim tier UNCHANGED:
Tier-0 demo with honest per-stage provenance; the recovery claims ONLY the reviewer→router DECISION
(which node to recover to), with the fault explicitly disclosed as injected, not diagnosed.

## Gates

- `test_agent_facade_recovery.py` (10) + routing (14) + setup (13) + intake + pipeline (10) → 59 passed.
- ADR-015 facade-discipline (root) → 27 passed.
- Regression on workflow/workbench/pipeline/provenance/monitor surface → 94 passed.
- `scripts/hf1_path_guard.py` → EXIT=0 (no HF1 file touched).
- (Pre-existing local openai/httpx `proxies` collection errors in test_report/test_solver/test_api
  are untouched-file infra noise, ignored as established.)

**Closure:** R0 **APPROVE** — no fix iterations needed. Local commit, `confidence: med`, no push.
