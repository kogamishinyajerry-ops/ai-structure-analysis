# Codex Review — ADR-028 P-fidelity: machine-checkable Tier-0/Tier-1 fidelity discriminator (R0 → R1 APPROVE)

**Scope (honesty-infrastructure, NOT HF1, NOT a schema field):** add the machine-checkable
fidelity discriminator that distinguishes — for a TOOL-bound stage — whether the real tool ran on
REAL data (`tier_1_real`) or DUMMY/sandbox data (`tier_0_dummy`). It is the anti-over-claim
primitive that UNBLOCKS honestly crossing the tool wall (the deferred real-`geometry.run`
dummy-mode): without it, a vacuous dummy result (a `check_geometry` that passes on fabricated
sidecar data) could read as a real validation. **This slice ships the vocabulary + helper + its
contract test; there is NO production producer yet** — the live producer is the explicitly-deferred
next slice. Discriminator-FIRST, then the dummy crossing (the memory-gate sequencing).

## Provenance: 10-agent pre-flight, three reasoned deviations from its blueprint

Slice chosen by pre-flight Workflow `wf_f887e585-47c` (3 grounded readers — coverage-model /
SimState-assembly / real-graph-reality — → 3 proposers → 3 adversarial verifiers → synthesizer). It
GO'd Proposal 1 (standalone discriminator + contract test as in-slice consumer), DEFERRED Proposal 2
(geometry.run dummy crossing — RISKY: launders a vacuous pass; mandatory-Codex next slice), and
NOGO'd real-graph orchestration (incompatible 7-node-SimState vs 13-stage-StageState shapes).

Three deviations I made + reasoning (documented for the next slice):
1. **SSOT/helper in the agent layer (`agents/state_projection.py`), not `mock_pipeline.py`** — the
   blueprint suggested mock_pipeline, but agent-driven tool stages EARLY-RETURN the facade StageState
   before mock_pipeline's emission seam, so the real producer (next slice's geometry.run) lives in
   state_projection; placing the vocab+helper there is where it'll actually be used (no dead helper),
   and avoids any `schemas/` change (no schema-trigger).
2. **Skipped the Accepted-ADR-028 edit** — caveats (NACA-vs-bracket, vacuous-pass, deferred crossing)
   are captured in code docstrings + this report + STATE.md instead of mutating an Accepted ADR.
3. **Did run Codex** even though the blueprint judged it non-mandatory (no risk-tier trigger fires) —
   this defines an honesty boundary future slices depend on, so an independent eye was warranted.

## Design (the discriminator's exact machine-checkable shape)

- `StageFidelityTier(StrEnum)` closed vocabulary `{not_applicable | tier_0_dummy | tier_1_real}` in
  the agent layer. Deliberately **NOT a 4th StageProvenance value** (the FE's defensive
  `asProvenance()` downgrades unknowns to `scripted_demo`, which would mis-label a wired stage) and
  **NOT a StageState schema field** (rides `metrics`, `extra="allow"`, so it never expands the
  D2-sanctioned schema surface).
- `fidelity_metrics(*, tool_ran, data_real, disclosure) -> dict`: `{}` for a no-tool stage (implicit
  `not_applicable`, byte-unchanged back-compat); else two co-located keys —
  - flat `metrics.fidelityTier` (survives the FE `parseStageState` number|string filter →
    auto-renders as the user-visible disclosure row in `MetricRows`);
  - nested `metrics.fidelity` `{tier, toolRan, dataReal, disclosure}` (DROPPED by the FE parser since
    it's an object → **structurally cannot reach `provenanceCoverage`/N13** — the machine-checkable
    evidence channel asserted by the backend test). Mirrors `metrics.recovery` exactly.
- Tier DERIVED from `data_real` (`tier_0_dummy` ⇔ not real) → closed vocabulary cannot drift.
- Emits **NO measurement-shaped keys** (watertight/manifold/volume/shortEdges/…) — anti-vacuous-pass.

## R0 — CHANGES_REQUIRED (1 valid P2) → fixed (enforce, not soften)

**R0 P2 (valid):** the test claimed "a dummy run MUST carry a non-empty caveat", but the helper
ACCEPTED `disclosure=""` for `tier_0_dummy` — so the assertion only proved the fixture string was
truthy, not that the contract was enforced. Codex offered two options (enforce / soften); I took the
**stronger, more honest** one — **enforce**: `fidelity_metrics` now `raise ValueError` when
`tier_0_dummy` has a blank/whitespace disclosure (a dummy/sandbox result can never ship without an
honesty hedge); `tier_1_real` may still omit it. Added `test_dummy_disclosure_is_enforced_not_merely_conventional`
asserting the raise for `""` and `"   "`. (Confirms N/13 inflation impossible — Codex R0 found no
issue there: fidelity rides metrics, the FE drops the nested object, count keys on provenance only.)

## R1 — **APPROVE**

Verbatim (gpt-5.5 xhigh, strict diff-only re-review): *"APPROVE. P2 resolved: tier_0_dummy now
rejects blank/whitespace disclosure before metrics emission. No new issue apparent from the provided
diff; tier_1_real may still omit it and no-tool remains {}."*

(Tooling note: the first R1 relay couldn't emit a verdict — its sandbox lacked a writable temp dir +
pydantic, so its attempts to RUN pytest/python failed; a strict diff-only / no-exec re-run produced
the clean verdict. A harness quirk, not a code signal.)

## Honest framing / claim ceiling (Tier-0 infrastructure)

"Added a machine-checkable Tier-0/Tier-1 fidelity discriminator to the coverage model, with a backend
contract test (+ FE invariant test) as its genuine consumer. N/13 agent-driven is UNCHANGED
(genuine-request success run stays 6/13). NO tool wall crossed, NO CAD kernel run, NO new agent
coverage — this is the prerequisite that UNBLOCKS the geometry.run dummy crossing, not the crossing
itself." MUST NOT be summarized as "wired the geometry agent" / "crossed the tool wall" / "stepped
toward graph orchestration" beyond "removed the blocker that deferred it."

## Gates

- Backend fidelity contract test (11) + recovery + geometry + intake + pipeline regression → all pass;
  full backend suite **1274 pass / 24 skip / 1 xfail** (minus pre-existing local openai/httpx `proxies`
  collection errors in test_report/test_solver/test_api).
- Root regression floor: `tests/test_geometry_agent.py` + ADR-015 facade-discipline → 29 pass.
- N/13 invariant: genuine-request run still exactly 6/13 agent-driven (provenanceCoverage unchanged).
- Frontend: `vitest test/workflowClient.test.ts` 8 pass (2 new fidelity invariant tests); `tsc` 0;
  `eslint` 70 (at the established ceiling — no new violations). `ruff check/format agents` clean.
- HF1 path-guard EXIT=0 (no HF1 file edited); ADR-015 intact (zero new `agents.*` import; facade untouched).

**Closure:** R0 CHANGES_REQUIRED (1 P2) → enforce-fix + test-pinned → **R1 APPROVE**. Local commit,
`confidence: med`, no push. **Deferred next slice (mandatory-Codex):** the real-`geometry.run`
dummy crossing that lands on this discriminator (NACA-gated, `tier_0_dummy`, measurement keys
suppressed, `dataReal:false`).
