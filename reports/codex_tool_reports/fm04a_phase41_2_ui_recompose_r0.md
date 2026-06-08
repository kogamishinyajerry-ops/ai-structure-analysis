OpenAI Codex v0.128.0 (research preview)
--------
workdir: /Users/Zhuanz/20260408 AI StructureAnalysis
model: gpt-5.4
provider: OpenAI
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019e71db-efa6-71c3-9de0-79f47e00f002
--------
user
current changes
exec
/bin/zsh -lc "pwd && ls -la && printf '\\n--- git status ---\\n' && git status --short && printf '\\n--- skill file ---\\n' && sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md && printf '\\n--- AGENTS ---\\n' && sed -n '1,260p' AGENTS.md && printf '\\n--- STATE ---\\n' && sed -n '1,220p' .planning/STATE.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 4827ms:
2026-05-29 11:51:50.617 xcodebuild[2204:81705791]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:51:51.079 xcodebuild[2204:81705787] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-HpXmpX77' (errno=Operation not permitted)
2026-05-29 11:51:52.106 xcodebuild[2331:81706006]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:51:52.421 xcodebuild[2331:81706005] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
 M frontend/src/App.tsx
 M frontend/src/components/AdvancedModePromo.tsx
 M frontend/src/components/CaseBrowser.tsx
 M frontend/src/components/OnboardingTour.tsx
 M frontend/src/components/ProjectManager.tsx
 M frontend/src/index.css
?? docs/_archived/
?? golden_samples/cylinder-pv-candidate/data/
?? reports/codex_tool_reports/fm04a_phase41_2_ui_recompose_r0.md
?? reports/signoffs/
?? reports/snapshots/
?? tmp/
?? uv.lock

--- skill file ---
---
name: gsd-code-review
description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
  - Task
---

<objective>
Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.

Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.

Arguments:
- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
  - quick: Pattern-matching only (~2 min)
  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)

Output: {padded_phase}-REVIEW.md in phase directory + inline summary of findings
</objective>

<execution_context>
@$HOME/.Codex/get-shit-done/workflows/code-review.md
</execution_context>

<context>
Phase: $ARGUMENTS (first positional argument is phase number)

Optional flags parsed from $ARGUMENTS:
- `--depth=VALUE` — Depth override (quick|standard|deep). If provided, overrides workflow.code_review_depth config.
- `--files=file1,file2,...` — Explicit file list override. Has highest precedence for file scoping per D-08. When provided, workflow skips SUMMARY.md extraction and git diff fallback entirely.

Context files (AGENTS.md, SUMMARY.md, phase state) are resolved inside the workflow via `gsd-tools init phase-op` and delegated to agent via `<files_to_read>` blocks.
</context>

<process>
This command is a thin dispatch layer. It parses arguments and delegates to the workflow.

Execute the code-review workflow from @$HOME/.Codex/get-shit-done/workflows/code-review.md end-to-end.

The workflow (not this command) enforces these gates:
- Phase validation (before config gate)
- Config gate check (workflow.code_review)
- File scoping (--files override > SUMMARY.md > git diff fallback)
- Empty scope check (skip if no files)
- Agent spawning (gsd-code-reviewer)
- Result presentation (inline summary + next steps)
</process>

--- AGENTS ---
# AGENTS.md

> **Realigned by ADR-026** (2026-05-24, Accepted): the development-team
> architecture is now **dual-engine** (Opus 4.7 主驱动 + Codex 代码审查),
> amending the AR-2026-05-06-001 Codex-primary role assignment. **`CLAUDE.md` is
> the team-architecture SSOT**; this file defines Codex-facing operating rules
> within that architecture. If the two drift, ADR-026 is the reconciliation anchor.

## Implementation Roles (dual-engine · ADR-026)

- **Opus 4.7 is the primary driver** for direct-execution work (FM-04a-class:
  blueprint → slice → composite synthesis → final audit; local-commit, no-push,
  under standing user authorization). This amends the AR-2026-05-06-001
  "Codex-primary / Opus-reviewer-not-executor" assignment.
- **Codex is the independent code reviewer + optional delegated codegen.** On
  risk-tier changes (schema / CalculiX adapter / solver-truth / `golden_samples`
  boundary / cross-≥3-file refactor / `confidence: low`), Codex reviews the diff
  before local commit (round cap = 3). Codex may also author delegated codegen
  when Opus defines the contract.
- **The Linear/Symphony Codex-primary path remains available** for bounded-issue
  PR work the user explicitly routes through Linear — no longer the default, but
  not removed.
- Linear is the work-control truth for Linear-routed work: explicit issues for
  scope, status proof, blockers, acceptance.
- GitHub/repo is the code truth. Linear-routed code lands by branch + PR only,
  never direct-push to `main`. FM-04a direct-execution = local-commit / no-push.
- Notion is an architecture/control mirror. Patch only after repo + Linear truth
  settle, and only with explicit confirmation for external writes.
- When Opus drives, Codex review is invoked by the main session via
  `codex-review-relay` (see `CLAUDE.md` Layer 1) — Claude Code's responsibility,
  not pushed to the user. When Codex drives a Linear issue, it may invoke local
  Opus as read-only reviewer without stopping to ask.
- For one bounded Linear issue, Codex may merge the PR and mark it Done when all
  required GitHub checks are green, merge state is clean, required proof/trailers
  exist, and the Opus owner gate returns `APPROVE` + `APPROVE_TO_MERGE`. Human
  acceptance is reserved for feature-milestone checkpoints.

## Operating Rules

- Start from repo truth: read this file, `.planning/STATE.md`, relevant ADRs, Linear issue contracts, and explicit user instructions before changing files.
- Default to Opus 主驱动 + Codex risk-tier review (dual-engine, ADR-026). Prefer single-agent execution over ad-hoc multi-agent orchestration; the evaluation fleet (3 `.claude/agents/` sub-agents) and Codex relay review are the sanctioned multi-agent surfaces.
- For Linear/Symphony work, one eligible Linear issue maps to one bounded run. Do not infer missing outcome, repository, acceptance, boundaries, or evidence requirements.
- External writes are gated. Show dry-run payloads before Notion updates, branch-protection changes, signed-validation claim promotion, or milestone completion announcements. Linear proof comments are allowed inside an explicit Linear issue run when they report verified repo evidence. GitHub merge actions and issue-level Done transitions are allowed only after the Claude owner gate approves the issue-level merge.
- Do not self-approve, auto-merge without the Claude owner gate, or claim completion beyond verified evidence.
- Current calibration gates still apply. If `scripts/compute_calibration_cap.py` reports a mandatory or blocking review gate, attach independent review evidence before merge.
- Lean validation workflow applies per ADR-023: sandbox/demo and engineering-candidate work may move quickly with explicit no-overclaim wording; strict validation packets are required only at signed physical-claim boundaries.

## Code Boundaries

- Prefer small, surgical, reversible diffs.
- Do not perform drive-by refactors, broad reformatting, framework swaps, or dependency additions.
- Do not change public interfaces, schemas, state machines, CLI contracts, persistent data formats, solver truth, golden samples, CI, or workflow policy unless the Linear/user scope explicitly calls for it.
- `golden_samples/` access (HF1.7a/b · ADR-011 AR-2026-05-16): signed-registry dirs (`^GS-\d{3}$`) are hard-stop read-only; `golden_samples/*-candidate/` is **writable** per the HF1.7b carve-out (pinned by `tests/test_hf1_path_guard_candidate_carveout.py`); any other `golden_samples/**` change needs an explicit signed validation/golden-sample issue.
- Keep solver/runtime claims honest: smoke tests, synthetic fixtures, and demo-unsigned paths are not signed validation.
- Name the claim tier when summarizing simulation work: Tier 0 sandbox/demo, Tier 1 engineering candidate, or Tier 2 signed validation. Never let Tier 0 or Tier 1 evidence imply Tier 2 validation.

## Review Roles (dual-engine · ADR-026)

- **Opus 主驱动** authors blueprints, slice implementations, tests, and composite
  synthesis for direct-execution work; **Codex** authors delegated codegen and
  reviews diffs. Either may author; the driver depends on the collaboration path.
- **Codex code review** returns `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER` with
  evidence-focused findings on the diff (round cap = 3).
- **Opus review** (when Codex drives a Linear issue) returns the same verdicts;
  for ordinary issue-level PRs Opus may act as delegated owner gate and authorize
  merge only with `APPROVE` + `APPROVE_TO_MERGE` after mechanical gates are green.
- Neither engine authorizes self-approval, Notion mutation, branch-protection
  changes, signed-validation (Tier 2) promotion, or milestone-level user
  acceptance by drift.
- A green CI run is not sufficient for governance or role-authority changes.
  **Repo-level policy changes (incl. this architecture realignment) need explicit
  review evidence** — ADR-026 itself is dogfood-reviewed via Codex relay before
  ratification — and must preserve the milestone-level human acceptance gate.

## Completion Format

For meaningful tasks, report:

- Changed files
- Implementation summary
- Verification command
- Test result
- Risks / unresolved issues
- Next recommended step

--- STATE ---
# AI-Structure-FEA · STATE

> **Stamp:** `fm04a-phase40B-step1-two-result-overlay-correspondence-KERNEL-LANDED(resultOverlay.ts:computeMeshCorrespondence-node-label-join+honesty-corresponds-gate+8-node-tests;Path-A-frontend-only;step2-viewport-wiring-DEFERRED;2-new-files-0-existing-touched-no-risk-tier;code@c1b65dd)·composite-UNCHANGED-81.00-until-wired+scored·PRIOR-phase40A-step2-iso-surface-viewport-WIRED+Codex-R0/R1/R2-arc-CLOSED-(opt-in-default-OFF;deformed-coords+value-filter+companion-fwd;honesty-badge-Tier0+per-element-is-truth-view;Codex-caught-2-REAL-P1[undeformed-coords/filtered-tet-march-via-shared-nodes]-FIXED+2-P2-DEFERRED-to-retro-queue[tensor-component-threshold-range/iso-in-hover-raycast];registered-functional-tester-Dim5=84[was82;90-anchor-2of4:iso✓CSV✓/playwright✗two-result-overlay✗];composite-81.00[was80.67;D1=86/D2=82/D3=76/D4=80/D5=84/D6=78;PROSPECTIVE-from-new-code-NOT-retro;Phase37-77.50/Phase38-78.33/Phase39-80.67-records-FROZEN];gates-tsc16/eslint72/vitest951-all-0-net-new;step1-core@0e28bb4)-prior:phase39-REGISTERED-rebaseline-80.67(D1=86/D2=82/D3=76/D4=80/D5=82/D6=78;real+0.83_vs_calibration+1.50;Phase38-78.33+Phase37-77.50-UNCHANGED)-2026-05-25 · code@774ab69 · branch=claude/FM-04a-tier1-ballistic-candidate`
>
> 最近 3 个 phase(37/36/35)完整 preamble 见下方。Phase 11-34 全文叙述 + 早期 Repo state(ENG-39→FM-04a Phase 10)+ Foundation-Freeze tally + W1-8 highlights 已归档 → `.planning/STATE_ARCHIVE.md`(git history 保留逐次全量;归档于 2026-05-23 Phase 38 前 housekeeping)。
>
> **Last updated:** 2026-05-25 (FM-04a **Phase 40 B step 1 = two-result-overlay mesh-correspondence KERNEL landed + turnkey plan** — opens the LAST Dim 5 90-anchor sub-bullet ("comparison cuts — overlay TWO results"; the audit put Dim 5=84 with this 1 of 4 missing). Path A frontend-only (load path is caseId-driven `ResultMeshPlaybackPanel.tsx:274` → 2nd fetch, NO solver-truth change; node `label` is the stable join key, element label optional → join by node only). NEW pure `frontend/src/components/resultOverlay.ts`: `computeMeshCorrespondence(frameA,frameB,diffThreshold=0.5)` → shared / only-A / only-B node-label sets + correspondenceRatio + a `corresponds` HONESTY gate (a per-node Δ field is meaningful ONLY when the meshes share enough node labels; otherwise the note says they do not correspond / share too little → caller renders a geometric overlay ONLY, NEVER a fabricated Δ, NEVER resampling [= Path B / solver-truth, out of v1 scope]). **8 node --test** (identical→ratio1 / disjoint→ratio0+"do not correspond" / partial±threshold / custom-threshold gate / null+empty no-crash / label-dedup / default-0.5 pin) all pass. Turnkey plan `.planning/FM-04A_PHASE40B_TWO_RESULT_OVERLAY_PLAN.md` (Path A>B rationale; **step 2 = viewport CYAN 2nd-mesh in the SAME scene [NO 2nd WebGL context] in its own camera-free useEffect [mirror the iso-mesh effect] + panel 2nd-fetch + advanced-gated toggle + honesty badge**; step 3 = difference field over shared labels via cell→point avg). Gates: `tsc -b` 16 / eslint 72 (both 0 net new) / node --test 8/8 / vitest unaffected (kernel not yet imported). **2 new files, 0 existing touched → no risk-tier Codex trigger**; App.tsx untouched; confidence: high; code@`c1b65dd`. **Composite UNCHANGED 81.00** (kernel not yet wired/scored). **STEP 2 (next session, regression-sensitive — deliberate split per the 40 A step-1/step-2 discipline; 40 A's viewport wiring drew 2 Codex P1s so treat with care):** wire `overlayFrame?`/`overlayEnabled?` into `ResultMeshWebGLViewport` (default-OFF cyan 2nd mesh, own useEffect, byte-stable when off) + panel 2nd-fetch (`overlayCaseId`, clone `:270-302`, reuse App `comparisonCaseB` `App.tsx:167-180`) + advanced-gated control + honesty badge → likely a Codex round → registered functional-tester re-score (does the overlay close the 4th 90-sub-bullet → ~88?). **27th consecutive Tier-2 increment; local-commit only.** — PRIOR **Phase 40 A step 2 = iso-surface WIRED into the 3D viewport + honesty-label UX** — Dim 5 82→**84**, composite 80.67→**81.00** (PROSPECTIVE from new code; Phase 37/38/39 records FROZEN). Opt-in default-OFF magenta overlay; per-element coloring stays the truth view; toggle+threshold in `ViewportDepthControls` (advanced-gated); forwarded to the companion. **Codex risk-tier arc R0→R2 (round-cap-3, CLOSED):** R0 caught a P1 (iso built in undeformed coords → peels off under deformation/playback) + R1 caught a P1 (my R0 filter fix only gated the cell→point averaging; filtered-out tets still marched via shared nodes) — **both REAL correctness bugs the vitest happy-path missed; fixed + regression-guarded**; R2 = **0 P1** + 2 P2 → retro queue (tensor-component threshold range [shares the value-filter slider's identical limitation, documented inline] / iso-in-hover-raycast [arguably correct-by-design — iso vertices have no node identity]). Registered **functional-tester Dim 5 = 84** (80-anchor fully met; 90-anchor 2/4 = iso✓ CSV✓ / playwright-WebGL-E2E✗ two-result-overlay✗; independently CONFIRMED the deformed-coord + value-filter fixes hold @`ResultMeshWebGLViewport.tsx:195-217`). Gates: `tsc -b` 16 / eslint 72 (both 0 net new) / vitest **951/65** (939+12; 0 regressions) / step-1 node --test 12/12 / App.tsx untouched (<1500). 4 commits `de493d3`→`c5c7b87`→`f2070a9`→`774ab69`. Audit `.planning/audits/phase40_functional_tester_phase40A_dim5_viz.md` + retro `.planning/retrospectives/phase40A_step2_codex_arc.md` + P2 backlog `.planning/retrospectives/codex_round3_overflow_phase40A.md`. **Next Dim 5→90:** two-result-overlay (closes the 4th 90-sub-bullet → ~88) / real-WebGL playwright E2E / provenance overlay + fps + VTU/PNG (95→99). **26th consecutive Tier-2 phase; local-commit only.** — PRIOR step 1 (core@`0e28bb4`): pure `isoSurface.ts` cell→point avg + marching-tets + 12 tests.) **Investigation:** `ResultMeshFrame` (`resultMeshPlayback.ts:18-43`) carries PER-ELEMENT scalars + per-node coords, NO nodal field → an iso-surface needs cell→point averaging (frontend-only, **NOT a solver-truth change**). New pure `frontend/src/components/isoSurface.ts` (no WebGL): `averageElementValuesToNodes` (cell→point smoothing onto tet corners) + `marchTetrahedron` (the 5 marching-tets topological cases) + `extractIsoSurface` (tet-scoped C3D4/C3D10; non-tet hex/wedge/shell/beam reported in `metadata.skippedElementTypes`, NOT silently dropped). **HONESTY T:-1 (new Phase 40 guard):** output is a SMOOTHED Tier-0 viz approximation (averaging smooths the genuinely discontinuous per-element field) — labeled in `metadata.note` + the module header; the per-element coloring stays the default truth view; **a single constant tet correctly yields NO iso-surface** (test-pinned honest consequence). **12 tests** (`Phase40A_iso_surface.test.ts`, node --test via tsx — kernel cases with hand-computed crossings + smoothing + metadata + graceful skips) all pass. Gates: `tsc -b` 16 / eslint 72 (**both 0 net new**) / vitest **939/64** (0 regressions) / App.tsx untouched (<1500); **3 new files, 0 existing touched → no risk-tier Codex trigger**; confidence: high. code@`0e28bb4`. **STEP 2 (next) = wire the iso-surface mesh into `ResultMeshWebGLViewport` behind a default-OFF toggle + the honesty-label UX** (regression/UX-sensitive → deliberate, not a tail-rush); THEN a registered `functional-tester` re-score of Dim 5 (does iso-surface move 82→ toward 90? — 90 needs iso-surface + CSV[✅done] + real-playwright-WebGL-E2E[**CI-green unverifiable on no-push branch**] + two-result-overlay[mesh-correspondence, moderate-large]). **25th consecutive Tier-2 phase; local-commit only.** — Prior **Phase 39 = REGISTERED-fleet prospective re-baseline COMPLETE → composite 80.67**). The registered eval fleet ran successfully post-restart — the `~/.claude/agents/` ABSOLUTE-path install + restart fixed the registry-not-discovered blocker; **this is the FIRST authoritative registered-fleet composite in FM-04a**. **Composite re-baselined to 80.67** = (86+82+76+80+82+78)/6. Per-dim vs Phase 38 *recorded*: Dim 1 91→**86** (−5, functional-tester REGISTERED — **CALIBRATION**: the Phase 38 proxy's 91 was generous; the 90-anchor is NOT met because Richardson coverage 38.5% < 60%; FEA byte-unchanged → NOT a regression) / Dim 2 77→**82** (+5, novice-simulator REGISTERED — **the ONLY REAL product delta**: 39 A BC-deadend + WS-death ErrorCard + 39 B 5 in-context-hints closed the last 80-anchor sub-bullet + 5/7 error-recovery; all 80-anchor met) / Dim 3 76→**76** (0, industrial-ui-comparator REGISTERED — confirmed; fleet==proxy agree exactly; mean parity 2.4/10; 70 met + 2/3 of 80) / Dim 4 76→**80** (+4, main synthesis — **CALIBRATION**: stale Phase-37 carry; advisor byte-unchanged; 80-anchor fully met = 3 stages `App.tsx:1341`/`:1342`/`VisualTabPanel.tsx:185` + 4-Q gate each; nothing of 90) / Dim 5 72→**82** (+10, functional-tester REGISTERED — **CALIBRATION**: stale Phase-37 HELD value; viz byte-unchanged; 80 fully + 1/4 of 90 = CSV only [iso-surface/playwright-E2E/two-result-overlay absent]; **CompanionViewport CONFIRMED side-by-side same-result NOT overlay** → 82, the correct value, not the proxy's over-credited 84) / Dim 6 78→**78** (0, main synthesis — **HELD**: Phase 38 fresh value, no Phase 39 trust/repro change; anti-inflation: NOT pushed up). **HONEST SPLIT of the +2.33 (78.33→80.67): only +0.83 is REAL Phase 39 A/B product work (Dim 2 +5/6); +1.50 is a one-time CALIBRATION basis-shift** (Dim 1 −5 generous-proxy correction + Dim 4 +4 & Dim 5 +10 stale-carry corrections — all byte-unchanged code). **Calibration cut BOTH ways** — the proxy was generous on Dim 1 (and Dim 5-as-84) while the stale carries under-credited Dim 4/5; the registered fleet is the authoritative arbiter. **From Phase 39 onward 80.67 is the new registered-fleet baseline; Phase 38's 78.33 (proxy/stale-carry-calibrated) + Phase 37's 77.50 are UNCHANGED — prospective re-baseline like v1.0→v2.0, never backfilled.** APPROVE gate (all 6 dims ≥99) FAILED (lowest Dim 3=76). **No code touched** (HEAD `67c2b8e`; frontend byte-unchanged since `b8bb8fc`) — the re-score is pure measurement. FINAL `.planning/audits/phase39_FINAL.md` + fleet reports `phase39_{novice_simulator,functional_tester,industrial_ui_comparator}.md` + `phase39_dim4_ai_workflow_PREP.md` + retro `.planning/retrospectives/fm04a_phase39_registered_fleet_rebaseline.md`. **Recommended next:** Dim 5→90 (iso-surface + playwright WebGL E2E — highest ROI, 3/4 of the 90-anchor viz-buildable) OR Dim 1→90 (Richardson 38.5%→≥60%, ≈3 more `convergence_study.json`) OR Dim 2→90 (role-branching 4 personas + WCAG AA + 2 missing recovery paths); separately a debt-cleanup phase (tsc-b 16 + eslint 69 + 4 backend httpx collection errors + GS-001 legacy marker + dev "Phase X" label leak — behavior-sensitive, NOT drive-by). **24th consecutive Tier-2 phase; local-commit only.** — Prior 2026-05-24 **Phase 39 registered-fleet re-score = BLOCKED on a hard infrastructure dependency (now RESOLVED by the restart + the ~/.claude/agents/ install)**. The Phase 38 D "Phase 39 re-baseline candidates" (Dim 4/5 HELD on byte-unchanged code) were to be resolved THIS session by the REGISTERED eval fleet via `subagent_type=`. **They are NOT available**: the Agent-tool registry is frozen at session init; the session root is `/Users/Zhuanz` (home, NOT the project dir — confirmed via the environment block + the available-agents error list); and Claude Code loads agents only from `~/.claude/agents/` (user-level) + plugins — it did NOT load the project's `<repo>/.claude/agents/`. **Last session's recorded fix ("launch from the project dir") was WRONG**: discovery is user-level, and even a project-dir launch wouldn't resolve the agents' relative protocol paths. **DURABLE FIX installed this session** (outside the repo, in `~/.claude/agents/`): `functional-tester.md` / `novice-simulator.md` / `industrial-ui-comparator.md` — thin frontmatter wrappers identical to the repo's, but pointing at **ABSOLUTE** protocol paths (`/Users/Zhuanz/20260408 AI StructureAnalysis/.planning/test_subagents/*.md`) so they resolve from ANY cwd. Verified all 3 protocol files + 5 reference surfaces + RUBRIC_v2.md exist at those absolute paths. **The registry does NOT hot-reload** (confirmed: re-issuing the Agent call after writing the files still errored "agent type not found") → **a session RESTART is required** to pick them up; after restart `subagent_type=functional-tester/novice-simulator/industrial-ui-comparator` works from any launch dir. **Did NOT fall back to general-purpose proxies** — that is the exact path that produced the Phase 38 D generous-drift (Dim 5 read 84, +12 on byte-identical viz, over-crediting CompanionViewport as an overlay); the instruction is explicit that the authoritative re-score must be the registered fleet, not a proxy. **No code touched** (HEAD `67c2b8e`, last code `b8bb8fc`); the frontend the fleet must measure is byte-unchanged at the Phase 39 A/B state, so the restart loses nothing. **Productive work done while blocked (read-only, contaminates no measurement):** the **Dim 4 main-session re-confirmation** (Dim 4 has no fleet agent — it is main-session synthesis). Re-confirmed **Dim 4 = 80** (HELD value 76) — a PROSPECTIVE re-baseline candidate parallel to Dim 5: the 80-anchor is fully met by file:line (3 advisor stages — case-open `App.tsx:1341` + BC-setup `App.tsx:1342` + review `VisualTabPanel.tsx:185` — each with the inline 4-Q gate at `CaseOpenAdvisorCard.tsx:96-109` / `BCSetupAdvisorCard.tsx:83-96` / `AdvisorPanel.tsx:187-210`), and **nothing** of the 90-anchor (only 3 advisor surfaces exist — no mesh-setup/solve-monitor stage; no "confidence: high/med/low" calibration prose). Details + anti-generous-drift counter-checks in `.planning/audits/phase39_dim4_ai_workflow_PREP.md`. **Phase 38 (78.33; Dim 4=76) + Phase 37 (77.50) records UNCHANGED** — the Dim 4=80 is prospective-only, banked at the next composite alongside the fleet's Dim 1/2/3/5, never backfilled. **NEXT-SESSION ONE-SHOT PLAN (post-restart, launch from anywhere):** (1) one message, 3 parallel `subagent_type=` calls — novice-simulator→Dim 2 (did Phase 39 A+B lift 77→80? the 80-anchor checklist now appears full: tour v2≥6 + Basic/Advanced + default-Basic + auto-promote + in-context bubbles ≥5 surfaces), functional-tester→Dim 1+Dim 5 (resolve HELD Dim 5=72; strictly judge the 90-anchor "comparison cuts overlay TWO results" vs CompanionViewport's side-by-side single-result compare-cuts), industrial-ui-comparator→Dim 3; (2) combine with the ready Dim 4=80 prep + a Dim 6 re-confirmation; (3) compute the PROSPECTIVE re-baseline composite, transparently splitting "real Phase 39 A/B Dim 2 lift" vs "byte-unchanged Dim 4/5 calibration correction"; (4) retro + STATE refresh; (5) proceed to the next candidate phase (Dim 2→90 role-branching, or Viz iso-surface + playwright WebGL E2E for Dim 5 90-anchor). Composite remains officially **78.33** until that pass lands. — Prior **Phase 39 B = Dim 2 in-context hints on 5 surfaces** — closes the rubric-v2.0 Dim 2 **80-anchor sub-bullet "in-context bubbles attached to ≥5 UI surfaces"**, the last 80-anchor gap the Phase 38 D R6 novice fleet flagged absent; code @`b8bb8fc`). New `InContextHint.tsx` (dismissible `role="note"` contextual hint; per-hintId dismissal persists to localStorage via `hintDismissedStorage.ts`, mirroring the Phase 29 B `sectionCollapseStorage` C:-1/D:-1/E:-1 pattern). Mounted on **5 DISTINCT workflow surfaces** with genuine surface-specific copy (G:-1, not 5 copies of one string): CaseBrowser (case selection) / BCSetupPillList (BC concept for a true novice) / AdvisorPanel (AI critique) / OperatorStatusPanel (workbench + trust state) / ProbeListPanel (results probes). **App.tsx UNTOUCHED** — hints live in the surface components → 0 App.tsx growth (<1500 pin unaffected). 13 new tests (storage + component dismiss-persistence + a non-brittle source-presence proof of all 5 attachments). **Codex governance review** (`codex-review-relay --commit 40533d9`, 86gs gpt-5.4 xhigh — risk-tier: the change spans 7 files): **R0 returned 2 findings (P2 + P3, no P1)**, both real + commit-introduced, both fixed verbatim-faithfully at `b8bb8fc`: **P3 (trust honesty)** — the AdvisorPanel hint claimed the advisor "runs offline", contradicting the live-LLM (`advisor_status:'online'`) path the panel supports + shows in its status badge; reframed to "advisory only … falls back to an offline stub if the live LLM is unavailable" (accurate provenance on a trust-sensitive surface). **P2 (test robustness)** — the 5-surface source-scan used `process.cwd()` (fragile to the vitest launch dir); switched to `resolve(__dirname, …)` mirroring the repo's Phase 28 D / 29 C structural tests. Verbatim-exception applied (faithful landing of Codex's own suggestions + fully verified) → no redundant R1. **Verification:** `tsc -b` 16 = baseline (0 net new); eslint 69 = baseline (0 net new); frontend suite **939 passed** (926 + 13 new), 0 regressions. **Composite UNCHANGED at 78.33** — with 39 A (2 HIGH frictions) + 39 B (the 80-anchor bubble sub-bullet) landed, Dim 2's full 80-anchor checklist now appears met (tour v2 + Basic/Advanced + default-Basic + auto-promote + in-context bubbles ≥5), BUT the authoritative Dim 2 re-score (77 → ?) **waits for the REGISTERED eval fleet next session (launch from the project dir)**, NOT a proxy (avoids the 38 D generous-drift). Phase 37/38 records unchanged. — Prior **Phase 39 A = Dim 2 novice-friction closure** — 2 HIGH frictions the Phase 38 D R6 fleet flagged, fixed at `a0533e8`). **(A) BC dead-end:** `BCSetupAdvisorCard` told the novice to "Set the BCs before running" + "after BCs are wired", but no BC editor exists and the BCs are fixed by the case definition (`BCSetupPillList` has said so since 38 F) — the contradiction sent novices hunting for a non-existent editor. Reframed `composeBCBrief` + footer to honest read-only copy ("These BCs are fixed by the case definition — no setup step here"); **NO BC editor added** (the BCs ARE case-fixed; an editor would be physically wrong). **(B) WS-death recovery:** `connectToLogs` `ws.onerror` appended one `[ERROR] WebSocket connection died` console line then went silent — the **6th/last** silent error-recovery path (Phase 33 C novice #2 / Phase 36 D friction (a)). Now surfaces an ErrorCard via `setUploadError` (live-job event-handler context → the direct setter, not the async `withRecovery` wrapper); Retry reconnects to the same job's stream via the existing `connectToLogs`. New `connectionLostRecoveryOptions` template, honest copy (a dropped log stream does NOT stop the backend solver). **Verification (real gates per the 38 I hollow-tsc lesson — `tsc -b`, NOT `tsc --noEmit`):** `tsc -b` = 16 = baseline (**0 net new**; the touched-file App.tsx TS2322 at 892-933 are the pre-existing trust-section ×7, not mine); **eslint = 69 = stash-on-HEAD baseline (0 net new) — NOTE the real eslint baseline is 69, NOT the 50 the 38 J STATE recorded; that 50 was a stale under-count, now flagged for the dedicated debt-cleanup phase**; frontend suite **926 passed** (922 baseline + 4 new `Phase39A`), 0 regressions; App.tsx 1476→1486 (<1500 pin holds, 14 LOC headroom). **Composite UNCHANGED at 78.33** — these are real Dim 2 friction closures, but the Dim 2 re-score (whether they lift Dim 2 toward the 80 anchor) **waits for the REGISTERED eval fleet next session (launch from the project dir)**, NOT a proxy (avoids the 38 D generous-drift). Frontend copy + ErrorCard wiring; no schema/adapter/solver/golden_samples change → no risk-tier Codex review; confidence: high. Phase 37/38 records unchanged. **Dim 2 80-anchor still blocked by the in-context-bubbles ≥5-surface gap** (the remaining novice 80-anchor sub-bullet; candidate Phase 39 B). — Prior **Phase 38 D = composite FINALIZED at 78.33/100** under rubric v2.0 — lift over Phase 37 (77.50): **+0.83**). The R6 eval fleet was re-run and the composite synthesized. **Per-dim:** Dim 1 FEA 87→**91** (+4; functional-tester fleet — REAL Phase 38 B work: C3D6 wedge 6th element class → 13 PASS cohort / 6 solver kinds / 6 element classes, 95-anchor "≥6 element classes" now met; 95 still blocked by cohort 13<15 + NAFEMS LE10 `REFERENCE_ONLY`) / Dim 2 Novice 77→**77** (0; novice-simulator fleet — net-neutral; in-context-bubbles ≥5-surface gap still blocks anchor 80) / Dim 3 Industrial UI 76→**76** (0; industrial-ui-comparator fleet — drag-resize/density/4-quadrant all absent block anchor 80; WCAG fixes don't move the parity feature-checklist) / Dim 4 AI workflow 76→**76** (0; **HELD** — advisor wiring `CaseOpenAdvisorCard`/`BCSetupAdvisorCard`/`AdvisorPanel` byte-unchanged in Phase 38; 38D added only the read-only `BCSetupPillList`) / Dim 5 Viz 72→**72** (0; **HELD** — viz layer byte-unchanged per `git diff f56f6ce..HEAD`) / Dim 6 Trust 77→**78** (+1; main synthesis — REAL 38 F tier-2 API-boundary visibility + 38 H drift-guard test + provenance script). Composite = (91+77+76+76+72+78)/6 = **78.33** simple arithmetic mean. **APPROVE gate (99+ = all 6 dims ≥99) FAILED by 20.67** — recorded honestly. **R6 ran via `general-purpose` proxies, NOT the registered `subagent_type` fleet**: the agents live in the project `.claude/agents/` but the session launched from `/Users/Zhuanz` (home) so they aren't discovered — AND their protocol paths are relative `.planning/...`, so a `~/.claude/agents/` copy wouldn't resolve either. **Durable fix = launch next session from the project dir** (`cd "…/20260408 AI StructureAnalysis" && claude`). The proxies were briefed with absolute paths to the protocol + RUBRIC_v2.md and scored against the rubric's anchor structure — this **fixed the prior harsh-drift** (the earlier R6 crashed Dim 2→58 / Dim 3→45 by scoring "from zero vs commercial CAE"; this run's Dim 1/2/3 are calibrated). **BUT the fresh-absolute proxy drifted GENEROUS on Dim 5** (read 84, +12 over Phase 37's 72 on byte-identical viz code, and over-credited the 90-anchor "comparison cuts overlay" — `CompanionViewport.tsx:1-6` is side-by-side compare-CUTS of ONE result, not an overlay of TWO). **Per the no-retroactive-rescore guard + the prior anti-drift caveat, Dim 4/5 (no Phase 38 code change) HOLD the Phase 37 calibrated values; the higher proxy reads are logged as Phase 39 re-baseline candidates for the REGISTERED agent — prospective, never retroactive.** Honest delta attribution: the +0.83 is **entirely Dim 1 (real C3D6) + Dim 6 (real trust work)** — Dim 2/3/4/5 flat; no dim inflated. The one main-session adjustment (Dim 5 proxy 84→corrected ~82) was a **downward** correction of a cited factual over-credit, and Dim 5 was HELD at 72 anyway. **Carry-forward findings** (valid regardless of calibration): GS-001 legacy unit-mismatch test runs+fails in default sweep (no `@pytest.mark.legacy`); 38 D BC dead-end (no BC editor — `BCSetupAdvisorCard` says "set BCs" with nowhere to go); WS-death mid-solve has no ErrorCard. All → Phase 39 / debt-cleanup. **23rd consecutive Tier-2 phase. Composite 78.33 LANDED, local-commit only, nothing pushed.** FINAL `.planning/audits/phase38_FINAL.md` + fleet reports `phase38d_{functional_tester,novice_simulator,industrial_ui_comparator,dim4_ai_workflow,dim6_trust_reproducibility}.md` + retro addendum. — Prior **Phase 38 G/H/I = act-on queue CLEARED + a milestone-integrity discovery**, autonomously per user directive). The Phase 38 E eval surfaced 6 calibration-independent findings; #1+#2 shipped in 38 F; **38 G/H/I + #4-disposition close the remaining four.** **38 G #5** `c428e43` — WCAG 1.4.3 closed to **10/10 PASS**: measured the 3 deferred surfaces (CaseBrowser chip, runner badge, TabButton) with the spec-verified `wcagContrast.ts` helper; **2 of 3 were "suspected fail actually passes"** (runner badge 5.77:1, not the eval's ~3.3:1 — the harsh proxy likely measured the amber border) → recorded as **measured PASS, not a fabricated color change** (honest non-fix, like the eval-#5 disposition). `wcag_audit.md` tally + addendum updated; per-surface rows superseded via the explicit line-175 note. **38 H #3** `a7ec424` — offline fallback cohort **7/24 → 24/24**: the 17 missing entries are **disk-sourced** (not hand-fabricated) via a committed provenance script `scripts/gen_fallback_candidate_registry.py` — claimTier/claimBoundary from the `_claim_tier` SSOT (a PASS verdict on a REGISTERED case promotes to Tier 2; **nafems-le10 stays Tier 1** as the analytical-only reference → no over-claim), solverKind/runnerAvailable from the verdict YAML, notesExcerpt = the backend's 12-line rule. New **drift-guard test** `Phase38H_fallback_cohort_coverage` fails loudly if any on-disk `-candidate` dir lacks a fallback entry / a phantom appears / a "Tier 2" entry has no verdict file — converting silent drift into a CI failure (the real fix for the class of bug). **38 I #6** `9703f4e`+`302339e`+`a747e10`+`98d5979` — silent sensitivity-study errors surfaced + infinite-poll stopped: extracted a new `useSensitivityStudy` hook (respecting the App.tsx <1500 LOC pin, per the Phase 35 C precedent); start failures route through the shared ErrorCard recovery + reset loading; `pollExperiment` gained try/catch + terminal-FAILED detection off per-run status (the backend never rolls a failed run up to FAILED, so it would otherwise poll forever). **Codex risk-tier arc R0→R2 (round cap 3, converging — NOT an N1.1 runaway)**: R0 3×P2 (retry affordances weren't actually recoverable) → R1 2×P2+1×P3 (loading lost on retry / re-poll-vs-relaunch / FAILED tone) → R2 1×P1+1×P2 (retried-failed-start stuck loading / 404-should-relaunch). **User explicitly ratified "fix both, skip further review" at the round cap**; all fixed (cleanup moved inside the withRecovery closure; 404→relaunch; runStateTone reads FAILED as warning). 11 hook tests pin every path. **#4 (render_all viz HTTP-unreachable) — assessed, bounded fix DEFERRED (honest)**: the backend `/visualize/plot` already returns friendly HTML for viz-unavailable + render-failed; the residual is a narrow raw-404 (report without on-disk FRD / uploaded-FRD-no-case) + the fundamental iframe-to-down-backend limitation (the whole app is unusable when the backend is down). A robust health-precheck/load-timeout overlay is ~20 LOC against the LOC pin + hacky + low-ROI for a MED finding from the harsh proxy → recorded as a bounded follow-up rather than a disproportionate fix. **⚠️ MILESTONE-INTEGRITY DISCOVERY: the project's type-check has been HOLLOW.** `npx tsc --noEmit` on the root config is a **no-op** (the project-reference setup needs `tsc -b`); it silently checks nothing. This session's earlier "tsc 0 errors in touched files" signals (and likely prior phases') were **vacuously true**. The real `tsc -b` shows **21 pre-existing errors** (App.tsx 9: 2 unused-import + 7 trust-section TS2322; + 12 across 7 other files) and **eslint = 55 pre-existing errors** (set-state-in-effect 26 / react-refresh 21 / no-unused-vars 8). **Phase 38 J** then removed the 5 clean unused-import/const declarations (the safe mechanical subset, dead-code — can't break tests) → **`tsc -b` 21→16, eslint 55→50**, App.tsx 1479→1476; the remaining red (7 trust-section `TS2322` type-shapes + misc, `set-state-in-effect` ×26, `react-refresh` file-splits ×21, 2 `_`-prefixed unused params) is **deliberate-phase work** (behavior-sensitive / shared-contract / multi-file — NOT a session-tail rush). **All 38 G/H/I changes were re-verified against the REAL `tsc -b` + eslint baselines: 0 net new tsc errors, 0 net new eslint errors** (stash-on-HEAD comparison). The pre-existing red is a standing condition recorded for a **dedicated cleanup phase**, NOT drive-by-fixed mid-feature. **Act-on queue now fully addressed** (#1,#2 = 38 F · #5 = 38 G · #3 = 38 H · #6 = 38 I · #4 = assessed/deferred). **Composite STILL PENDING the calibrated eval-fleet re-run** (the `.claude/agents/` fleet is not registered as `subagent_type` this session → needs a restart). **Recommended next: (1) session restart → invoke the calibrated eval fleet via `subagent_type=` → R6 re-score → finalize the Phase 38 composite; (2) a dedicated `tsc -b`+eslint debt-cleanup phase (21+55 pre-existing).** Tests: frontend **922 passed** (62 files); backend unchanged from 38 F (1150 passed; pre-existing failures confirmed on HEAD). All local-commit / no-push. Retro addendum `.planning/retrospectives/fm04a_phase38_cohort_nafems_c3d6_wcag_bc_setup.md`. — Prior **Phase 38 F preamble:** **38 F #2** `611cc0f` reframes the Phase 38 D BCSetupPillList copy from the novice dead-end "Expected BCs — not yet assigned" → honest "Case-defined BCs (read-only — fixed by the case definition)". **38 F #1** `9439841` surfaces tier-2 promotion at the API boundary: `candidate_cases.py`/`cohort_overview.py` now resolve per-case tier via `_claim_tier` (was hard-coded Tier 1, hiding every real-solver promotion); frontend wires the never-populated `cohortOverviewClient.claimTier` + a cohort Tier-2 badge + the picker's per-case `claimBoundary`; `COHORT_OVERVIEW_SCHEMA_VERSION` 1.0.0→1.1.0 (additive field). **Codex risk-tier review ran R0→R3 (ADR-026 cap)**: R0 fixed frontend-type-decl + schema-bump; R1 fixed root-scoping (accessors gain repo_root) + a **genuine hidden promotion** (`hertz-contact-candidate` was Phase-34-C-validated via real ccx but unregistered + its YAML/nested verdict skipped by the json-only overlay — now registered+parsed, tier_2 cohort 12→13); R2 fixed a registry-SSOT bypass (root-scoped path now gated on registry membership so a stray PASS verdict can't self-promote an unregistered case); R3 fixed the picker boundary suffix + a **stale hertz NOTES.md** (Phase 33 D "INFRASTRUCTURE_ONLY" status predated the Phase 34 C validation — updated, 33 D history preserved as superseded) and **dismissed a Codex false positive** (it cited `test_schema_versions_stamping.py` which does not exist; full suite confirms). Round cap reached at R3 with no finding remaining. Tests: backend **1150 passed** (+3 vs the 1147 baseline: test_phase38f 10 + test_phase29d hertz param; 2 failures + 8 errors all pre-existing, confirmed identical on clean HEAD via stash — GS-001 UY scale / draft layer-import / app.api OpenAI(proxies) env); frontend **901 passed** (+5); tsc 0 errors in touched files. Honesty: hertz tier_2 is genuine (real ccx PASS) with honest scope kept (validates *CONTACT PAIR machinery via stacked-cube proxy, NOT Hertz curvature). Commit messages carry the full R0-R3 disposition. **Act-on queue remaining** (#3-#6, deferred): 18/24 cohort absent from frontend fallback; render_all HTTP-unreachable; CaseBrowser amber badge ≈3.3:1; silent sensitivity-study error. Composite still PENDING calibrated eval-fleet re-run (needs subagent registration). — Prior 38 A-E preamble: Dev-team architecture realigned to dual-engine + eval fleet via **ADR-026** (Accepted; `CLAUDE.md`/`AGENTS.md`/`.claude/agents/`). 38 A `4c8d77a` NAFEMS LE10 published-reference (analytical-only; honest-corrected to `published_reference.yaml` REFERENCE_ONLY not tautological PASS, signed −5.38e6, NOT registered; Codex R0 2 findings fixed). 38 B `5f97f04` C3D6 wedge 6th element class — **real ccx** σ_zz=−210 MPa 0.00% residual → genuine tier_2_validated (registry + Phase 35B census 12→13 / linear_static 5→6 + Phase 29D tolerance registry, all sanctioned forward-gate updates); Codex R0 clean. 38 C `59bd253` WCAG 1.4.3 sweep — real `frontend/src/lib/wcagContrast.ts` helper (spec-verified vs 3 published canonicals), `--text-muted` #64748b 3.74:1→#828fa6 5.4:1; `wcag_audit.md` honest 7/10 PASS / 3 GAP. 38 D `dcc9ee1` BC-setup friction — advisor row flexDirection column→row + `shouldShowBCSetupAdvisor` gating + new `BCSetupPillList`; App.tsx 1479<1500. **38 E eval fleet R6 (ADR-026 evaluation layer): composite NOT finalized** — scores diverged sharply (Dim 2 58 vs 77, Dim 3 45 vs 76) BUT custom `.claude/agents/` not registered this session → ran via general-purpose proxies with harsh framing (methodology caveat; Dim 1/5 track baseline, Dim 2/3 crash = scale mismatch). Did NOT crash composite to ~68 (would retroactively re-score prior phases on uncalibrated scale) NOR fabricate 79-82 (eval evidence doesn't support). **Act-on queue**: tier-2 promotion invisible at API boundary (`candidate_cases.py:39`+`cohort_overview.py:36` hard-code Tier 1, never call `_claim_tier`); 38 D BCSetupPillList "not yet assigned" dead-end (novice friction my change introduced); 18/24 cohort absent from frontend fallback; render_all HTTP-unreachable; CaseBrowser amber badge ≈3.3:1 (the 38C GAP, confirmed); silent sensitivity-study error. **Recommendation: restart session → invoke real calibrated eval fleet via subagent_type= → R6 re-score → finalize composite; act on findings #1+#2 next.** Tests: backend full suite 1155 passed (10 pre-existing env failures confirmed on HEAD, unrelated); frontend 896 passed; 38A 8 + 38B 4 + 38C 17 + 38D 10 new. Codex relay activated after 38-phase dormancy (caught sign bug + cohort-pin break single-agent self-review missed). Audit `.planning/audits/phase38_eval_fleet_r6.md`; retro `.planning/retrospectives/fm04a_phase38_cohort_nafems_c3d6_wcag_bc_setup.md`. 22nd consecutive Tier-2 phase (A-D). Nothing pushed.
>
> **Phase 37 preamble retained below:**
>
> **Last updated:** 2026-05-19 (FM-04a Phase 37 A-D **Industrial-UI-canonical-surface + BC-setup-advisor + WCAG-audit-doc phase** under user's "99 分以上" mandate, targeting the explicit UI 设计是否能对标顶级工业软件 axis + Dim 4 80-anchor 3-stage sub-bullet closure + Dim 6 WCAG provenance baseline + Dim 2 5/5 silent error-path closure. 37 A `72635aa` CaseBrowser canonical-surface industrial-UI parity. New `frontend/src/components/CaseBrowser.tsx` (~480 LOC): Hyperworks Model Browser-style case picker with (a) tree grouping by `solverKind` (6 group headings: linear_static / contact_pair_static / heat_transfer_steady_state / dynamic / modal / buckling); (b) filter chip row driving cohort filter via `<button aria-pressed>` chips; (c) incremental search via `<input type="search">`; (d) preview pane `<aside>` showing solver kind + runner_available badge + blurb + one-click "Open case" CTA; (e) X-of-Y counter "Showing N of M cases"; (f) empty-state copy "No cases match the current filters"; (g) full ARIA: `role="region"` + `aria-label="Case browser — grouped by solver kind"` + chip aria-pressed + search aria-label. App.tsx mounts CaseBrowser when no active case selected (replaces inline button list). `CandidateCaseRecord` gained optional `solverKind?: <6-value enum>` field; 12 entries backfilled. Exports `groupAndFilterCases` + `prettyKind` + `previewBlurbFor` helpers. 16 new Phase 37 A tests (5-fixture full-render across 6 describe groups). App.tsx LOC 1482→1490 (+8). **Q:-1 NEW Phase 37 anti-gaming guard**: CaseBrowser data contract — `solverKind?` strictly additive; existing consumers unchanged; tests pin full render across 5 representative fixtures. 37 B `492ab13` BCSetupAdvisorCard — 3rd advisor surface at BC-setup stage. New `frontend/src/components/BCSetupAdvisorCard.tsx` (~310 LOC). Same envelope as Phase 34 B + 35 A: (a) offline-first stub status badge; (b) curated BC orientation copy per case kind via `bcOrientationForCaseKind(caseId)` — 13 case-kind branches (cantilever / cylinder-pv / hertz-contact / heat-transfer / modal-frequency / dynamic-explicit / contact-pair-stacked-cube / buckling / plate-with-hole / shell-roof / rod-wave / 1d-bar / fallback) mapping to expected BC conventions; (c) 4-Q gate INLINE with `data-gate-kind="static"` attribute + italic gate-hint subtitle matching CaseOpenAdvisorCard; (d) `role="region"` + `aria-label="BC-setup AI advisor"`; (e) own test-ids (`bc-setup-advisor-status` / `bc-setup-advisor-orientation` / etc.) — additive per K:-1, existing case-open test-ids UNCHANGED. App.tsx mounts BCSetupAdvisorCard paired with CaseOpenAdvisorCard in a `flexDirection: 'column'` block when case is open. 16 `it()` blocks across 6 describe groups (brief said 28; honest miscount caught by R5 sub-agent — friction point #7). App.tsx LOC 1490→1493 (+3). **R:-1 NEW Phase 37 anti-gaming guard**: BCSetupAdvisorCard envelope — same Phase 34 B + 35 A pattern; offline-first stub; curated copy; static gate-hint; no LLM call; no fetch. Closes Phase 36 R4 friction (advisor surface count was 2; now 3) + closes Dim 4 80-anchor 3-stage sub-bullet (case-open + BC-setup + review). 37 C `f56f6ce` WCAG audit doc + 5th of 5 silent error paths closed. New `.planning/wcag_audit.md` (~210 LOC): 10 surfaces × 6 WCAG 2.1 criteria (1.3.1 Info & Relationships / 1.4.3 Contrast / 2.1.1 Keyboard / 2.4.6 Headings & Labels / 3.3.1 Error Identification / 4.1.2 Name Role Value) with explicit PASS/GAP/TODO/N/A per cell. Headline: 10/10 surfaces fail 1.4.3 contrast (text-on-dark-glass palette never formally measured); committed honestly. **Solver-start `[ERROR]` path** wired through Phase 35 C `useUploadErrorRecovery.withRecovery`: App.tsx `runSolver` now wraps in `withUploadRecovery(fn, solverStartRecoveryOptions(caseId))`. New option template `solverStartRecoveryOptions()` in `useUploadErrorRecovery.ts` with codeFriendly `"Solver start"`. App.tsx `runSolver` consolidation SHRANK the file: 1493→1477 (-16 LOC; cleaned up duplicate error-path code that the hook makes redundant). 5 of 5 silent paths now closed (UPLOAD + CASE-LOAD + PDF-EXPORT + STOP-REQUEST + SOLVER-START — all 5 codes distinct). 1 new option-template test + 1 codeFriendly humanization test. **S:-1 NEW Phase 37 anti-gaming guard**: WCAG audit enumerated — 10 surfaces × 6 criteria with PASS/GAP/TODO/N/A per cell; reviewable surface-by-surface; headline GAP (10/10 fail 1.4.3) declared honestly. 37 D 3 sub-agent R5 audits (functional / novice / industrial-UI) + 2 main-session syntheses (Dim 4 + Dim 6) + FINAL composite + retro + STATE refresh. **Phase 37 composite: 77.50/100 under rubric v2.0** — lift over Phase 36 D (75.50): **+2.00**. **Lands INSIDE projected band 77-79 at midpoint**. Per-dim: Dim 1 FEA 87→**87** (Δ 0; functional_tester R5 — Phase 37 didn't invest in cohort capability; biggest single 90→95 anchor pickup remains NAFEMS-tagged case + 6th element class → Phase 38 priority) / Dim 2 Novice UX 72→**77** (**Δ +5**; novice_simulator R5 — CaseBrowser canonical-surface industrial picker + 5th of 5 silent paths closed + BCSetupAdvisorCard 3rd advisor stage + WCAG audit doc committed each contribute) / Dim 3 Industrial UI 73→**76** (**Δ +3**; industrial_ui_comparator R5 — **first canonical-surface lift since rubric v2.0 baseline (Phase 33 A)**: case_tree_panel 4.3→6.0/10 via Hyperworks Model Browser parity on 4 of 8 critical-success signals; bc_setup_panel +0.5 (1.5→2.0); 5-canonical mean 3.76→4.20/10) / Dim 4 AI workflow 73→**76** (**Δ +3**; main syn — closes 80-anchor 3-stage sub-bullet: case-open + BC-setup + review; surface count 2→3) / Dim 5 Viz 72→**72** (untouched; iso-surface + WebGL Playwright E2E + VTU/PNG export all Phase 39 target) / Dim 6 Trust 76→**77** (**Δ +1**; main syn — WCAG audit doc commits project-wide provenance baseline closing Phase 36 D friction b + 5/5 error-path closure strengthens 90-anchor "trust score explains every UI step" sub-bullet; honest counter-weight: 10/10 contrast GAP declared, not glossed). Composite = (87+77+76+76+72+77)/6 = 77.50 simple arithmetic mean. **NOT spawning R6** per v2.3 cap discipline. **APPROVE gate FAILED by 21.50 points** — recorded honestly; 99-target reachable at Phase ~45-46 per refined multi-phase roadmap. **NEW Phase 37 anti-gaming guards Q/R/S on top of A-P all honored**: Q:-1 CaseBrowser data contract (solverKind? additive; existing consumers unchanged); R:-1 BCSetupAdvisorCard envelope (same Phase 34 B + 35 A pattern; offline-first stub; no LLM; no fetch); S:-1 WCAG enumerated (10×6 grid with PASS/GAP/TODO/N/A per cell). **7 NEW Phase 37 R5 friction points** surfaced by sub-agents (the exact unanticipated cost the v2.0 apparatus catches): (1) brief-vs-code drift Phase 37 B mount: brief said "side-by-side" but App.tsx `flexDirection: 'column'`; (2) BCSetupAdvisorCard always mounts when case open — no bc_status proxy detection; (3) BCSetupAdvisorCard has no CTA / no real BC-setup UI; (4) runner_available amber badge only in CaseBrowser preview, not on case row buttons; (5) no tour-card refresh describing canonical CaseBrowser surface; (6) WCAG audit headline 10/10 surfaces fail 1.4.3 contrast (audit shipped honestly but contrast measurements not fixed); (7) Phase 37 B test count mismatch (brief 28 vs file 16 `it()` blocks). All 7 flagged for Phase 38+. **First 4-dim simultaneous lift in FM-04a journey** (Dim 2 + Dim 3 + Dim 4 + Dim 6 moved together in single phase — prior phases lifted 1-2 dims at a time). **First canonical-surface industrial-UI lift since rubric v2.0 baseline** (Phase 33 A introduced 5-canonical measurement; for 4 phases all Dim 3 lifts were non-canonical; Phase 37 A directly redesigns case_tree_panel). **Multi-phase roadmap toward 99+ (refined from Phase 36 FINAL with +2.00 LANDED)**: P38 FEA cohort 13-15 + NAFEMS + 6th element class + contrast sweep → ~79-82 / P39 Viz iso-surface + playwright WebGL E2E → ~82-86 / P40 Trust audit-log + reproduce CLI → ~85-89 / P41-43 NAFEMS + cases 16-18 + LLM provider → ~89-93 / P44-45 final polish + first 99+ audit cycle → ~93-99. **Projected reach of 99+: Phase ~45-46** (~8-9 more phases). Phase 37 +2.00 is on the +2.5/phase average needed; the foundation laid (canonical-surface redesign pattern + advisor-stage closure + 5/5 error path hook arc + project-wide WCAG provenance) accelerates Phase 38-40 work. **Phase 37 total: 33 new tests** (16 Phase 37 A CaseBrowser + 16 Phase 37 B BCSetupAdvisorCard + 1 Phase 37 C SOLVER-START template); 856/856 frontend tests pass (was 823 at Phase 36 D close; +33 net); 233/233 Phase 30-37 backend cross_check tests pass UNCHANGED; 232/232 Phase 18-31 schema-version pinning tests pass UNCHANGED; 0 regressions vs Phase 36 baseline. Hard constraints PASS: HF1.7a/b/8 intact + *-candidate carve-out for hertz-contact-candidate + tmp_path-only test writes outside golden_samples/*-candidate + no push/PR/Linear/Notion in Phase 37 (local-commit only) + Phase 1-36 chain additive only (App.tsx LOC 1482→1477 — Phase 37 C consolidation actually shrank; < 1500 with 23 LOC headroom; no test threshold edits; Phase 11 AdvisorPanel byte-identical via I:-1; CSV export schema byte-identical via J:-1; ErrorCard.tsx UNCHANGED in Phase 37; Phase 34 B CaseOpenAdvisorCard byte-identical; schema_version labels byte-identical via L:-1 strict additive; Phase 36 C failed-attempt corpus byte-identical via O:-1). **Phase 37 thesis MET on truth axis**: CaseBrowser canonical-surface industrial-UI parity lift on the long-stuck case_tree_panel canonical (first since v2.0 baseline); BCSetupAdvisorCard closes Dim 4 80-anchor 3-stage sub-bullet; WCAG audit doc commits project-wide provenance baseline with honest 10/10 contrast GAP declaration; 5/5 silent error paths now closed via reusable hook — but bc_setup_panel canonical surface remains at 2.0/10 (no real BC-setup UI yet), 4 of 5 canonical surfaces still below 90-anchor ≥7/10 gate, advisor surface count still 3 (need 5 for Dim 4 90-anchor; need 6 for 99-anchor), ≥1 concrete LLM provider still Phase 41+, iso-surface + playwright WebGL E2E still Phase 39, audit-trail log + reproduce CLI still Phase 40, NAFEMS + 6 more cases still Phase 41-43, contrast sweep + palette adjustment still Phase 38, all 6 dims to 99 still Phase 44-45 — all recorded verbatim — zero score reshapes — Anthropic "real-usage eval > benchmark" preserved across 21 consecutive Tier-2 phases. Retro `.planning/retrospectives/fm04a_phase37_industrial_ui_parity_bc_setup_advisor.md`. FINAL audit `.planning/audits/phase37_FINAL.md` + sub-agent R5 reports at `.planning/audits/phase37d_{functional_tester,novice_simulator,industrial_ui_comparator}.md` + main syntheses at `.planning/audits/phase37d_{dim4_ai_workflow,dim6_trust_reproducibility}.md`. Phase 36 stamp `@169134c` preserved in git history. Nothing pushed in Phase 37.
>
> **Phase 36 preamble retained below for context:**
>
> **Last updated:** 2026-05-19 (FM-04a Phase 36 A-D **Novice-UX-completion phase** targeting the explicit user mandate axis 新手人类用户的使用难度、交互模式 + Dim 6 failed-attempt corpus 95-anchor closure. 36 A `3c50572` PDF export + stop-request silent paths closed via Phase 35 C `useUploadErrorRecovery.withRecovery` hook reuse. App.tsx `downloadPDFReport` wraps in `withUploadRecovery(fn, pdfExportRecoveryOptions(activeCaseId))`; `stopSolver` wraps in `withUploadRecovery(fn, stopRequestRecoveryOptions(jobId))`. New option templates `pdfExportRecoveryOptions()` + `stopRequestRecoveryOptions()` in `useUploadErrorRecovery.ts`. PDF_EXPORT + STOP_REQUEST remediation lists (3 steps each). displayLabel "(Phase 19 B)" / "(Phase 20 B)" / "(Phase 20 C)" suffixes stripped from 3 entries in `candidateCaseRegistry.ts` (lines 119, 135, 151) closing Phase 35 R3 friction point (a). App.tsx LOC unchanged at 1478 (PDF + stop wrappers absorbed what try/catch/finally took). 5 new frontend option-template tests pin all 4 distinct codes (UPLOAD / CASE-LOAD / PDF-EXPORT / STOP-REQUEST). 36 B `8315aaa` ErrorCard WCAG audit + codeFriendly + Retry FormData fix. **ErrorCard.tsx receives 2 ADDITIVE changes** (Phase 18 D tests pass UNCHANGED): (a) `aria-labelledby` → title id via `useId()` so screen readers announce the title not the full content; (b) optional `codeFriendly?: string` field — renders in the pill when present + raw `code` preserved via `data-error-code` attribute for support-ticket scraping. WithRecoveryOptions gains matching `codeFriendly?: string`; 4 option templates updated with codeFriendly: 'Upload' / 'Case load' / 'PDF export' / 'Stop request'. App.tsx: ErrorCard mount repositioned ABOVE OperatorStatusPanel (Phase 35 R3 friction point b — failed users see red error band before trust prose). selectCase + generateReportFromFile FormData construction moved INSIDE the withUploadRecovery closure so Retry sends a fresh request body (Phase 35 R3 friction point e). App.tsx LOC 1478 → 1482 (+4). 8 new frontend tests pin (4 WCAG semantic: getByRole(alert, name) + aria-live="assertive" + aria-hidden icon + Retry by-role-name; 4 codeFriendly priority: priority when present, code fallback, data-error-code preservation, pill omitted when both absent). **P:-1 NEW Phase 36 guard**: WCAG semantic queryByRole not vibe role-presence. 36 C `4188dc5` failed-attempt corpus seed + runner_available badge. `.planning/failed_attempts/INDEX.md` 74 LOC corpus charter + entry table + template, plus 7 evidence-linked entries: plate-ss-shell-pivot (Phase 30 D) / heat-transfer-pivot-from-contact (Phase 31 A) / richardson-extrapolation-p-le-0-guard (Phase 31 C) / hertz-contact-analytical-only-deferral (Phase 33 D → 34 C) / contact-pair-stacked-cube-pivot (Phase 34 C) / phase35b-strict-additive-schema (Phase 35 B) / phase33d-errorcard-app-tsx-loc-rollback (Phase 33 D → 35 C). Each cites a real commit SHA + preserved-evidence path per **O:-1 NEW Phase 36 guard**. Closes the long-standing Dim 6 anchor-95 sub-bullet "failed-attempt corpus with ≥5 entries" (40% over target). `CandidateCaseRecord` gains optional `runnerAvailable?: boolean` field. `FALLBACK_CANDIDATE_CASES` backfilled (GS-102* + rod-wave-* = false; cylinder-pv / plate-with-hole / cantilever-beam = true; undefined = unknown for live-route back-compat). CaseOpenAdvisorCard renders amber "demo · no live runner" badge when `runnerAvailable === false` (test-id `case-open-advisor-runner-badge`; closes Phase 35 R3 friction point f). 3 new badge tests (renders when false, hides when true, hides when absent). 36 D 3 sub-agent R4 audits (functional / novice / industrial-UI) + 2 main-session syntheses (Dim 4 + Dim 6) + FINAL composite + retro + STATE refresh. **Phase 36 composite: 75.50/100 under rubric v2.0** — lift over Phase 35 D (73.83): **+1.67**. **Lands INSIDE projected band 75-78 at the low end** (recovers Phase 35 D's -0.17 shortfall + delivers real Dim 2 + Dim 6 progress). Per-dim: Dim 1 FEA 87→**87** (Δ 0; functional_tester R4 — Phase 36 didn't invest in cohort capability; **biggest finding**: cohort actually has 5 element classes not 4, C3D4+C3D10 gmsh-driven via `element_order` in 5 runners; 95-anchor gap to 6 is 1 not 2 — per B:-1 score holds, finding recorded as Phase 37+ priority) / Dim 2 Novice UX 65→**72** (**Δ +7**; novice_simulator R4 — **largest single-phase Dim 2 lift since Phase 34 A**; 4 of 5 silent error paths now closed via reusable hook + WCAG aria-labelledby + codeFriendly humanized pill + Retry FormData fix + runner_available badge) / Dim 3 Industrial UI 73→**73** (Δ 0; industrial_ui_comparator R4 — Phase 36 B + 36 C wins land on NON-canonical surfaces; 5-canonical mean parity unchanged at 3.76/10) / Dim 4 AI workflow 73→**73** (Δ 0; main syn — surface count + workflow stages unchanged) / Dim 5 Viz 72→**72** (untouched; Phase 39 target) / Dim 6 Trust 73→**76** (**Δ +3**; main syn — **failed-attempt corpus 7 entries closes 95-anchor sub-bullet** + ErrorCard `data-error-code` preserves raw enum for support correlation + aria-labelledby adds WCAG-grade UI provenance + runner_available transparency at case-open). Composite = (87+72+73+73+72+76)/6 = 75.50 simple arithmetic mean. **NOT spawning R5** per v2.3 cap discipline. **APPROVE gate FAILED by 23.50 points** — recorded honestly; 99-target reachable at Phase ~45 per refined multi-phase roadmap. **NEW Phase 36 anti-gaming guards N/O/P on top of A-M all honored**: N:-1 hook reuse (Phase 36 A wraps PDF + stop through existing useUploadErrorRecovery; no parallel error-state widget); O:-1 corpus entries evidence-linked (all 7 cite commit SHA + preserved-evidence path); P:-1 WCAG semantic pin (getByRole + aria-live attribute checks). **5 NEW Phase 36 R4 friction points** surfaced by novice_simulator (the exact unanticipated cost the v2.0 apparatus catches): (a) WebSocket death / no reconnect still silent (separate live-job context; needs cousin hook); (b) no committed project-wide `wcag_audit.md` (ErrorCard semantics pinned; other surfaces unaudited); (c) solver-start `[ERROR]` log is text-only (no structured ErrorCard alongside); (d) `role="alert"` may not re-announce identical retry-fail messages (screen-reader edge case); (e) runner badge `text-secondary` on amber may fail WCAG 1.4.3 contrast (theme-dependent). All 5 flagged for Phase 37+. **Multi-phase roadmap toward 99+ (refined from Phase 35 FINAL with shortfall recovered)**: P37 Industrial UI canonical-surface parity + BC-setup advisor + WCAG audit doc → ~78-81 / P38 FEA cohort 13-15 + 6th element class → ~81-84 / P39 Viz iso-surface + playwright WebGL → ~84-87 / P40 Trust audit-log + reproduce CLI → ~87-90 / P41-43 NAFEMS + cases 16-18 + LLM provider → ~90-94 / P44-45 final polish + first 99+ audit cycle → ~94-99. **Projected reach of 99+: Phase ~45** (~9 more phases). Phase 36 +1.67 is below projected ~+2.5/phase average needed but the Phase 35-36 foundation (reusable useUploadErrorRecovery hook arc with 4 option templates + 7-entry failed-attempt corpus + WCAG-grade ErrorCard provenance + runner_available transparency) accelerates Phase 37-40 work. **Phase 36 total: 19 new tests** (all frontend across 36 A 5 option-template + 36 B 8 WCAG/codeFriendly + 36 C 3 runner badge + 36 C 3 additional); 823/823 frontend tests pass (was 820 at Phase 35 D close; +3 from Phase 36 C runner_available alone, total Phase 35 → Phase 36 delta +16); 233/233 Phase 30-36 backend cross_check tests pass UNCHANGED; 232/232 Phase 18-31 schema-version pinning tests pass UNCHANGED; 0 regressions vs Phase 35 baseline. Hard constraints PASS: HF1.7a/b/8 intact + *-candidate carve-out for hertz-contact-candidate + tmp_path-only test writes outside golden_samples/*-candidate + no push/PR/Linear/Notion in Phase 36 (local-commit only) + Phase 1-35 chain additive only (App.tsx LOC stays at 1482 < 1500; no test threshold edits; Phase 11 AdvisorPanel byte-identical via I:-1; CSV export schema byte-identical via J:-1; ErrorCard.tsx receives 2 strictly additive changes — Phase 18 D tests pass UNCHANGED; schema_version labels byte-identical via L:-1 strict additive). **Phase 36 thesis MET on truth axis**: 4 of 5 silent error-recovery paths now closed cleanly via the reusable Phase 35 C hook pattern; WCAG aria-labelledby + codeFriendly humanized pill + data-error-code support attribute ship with semantic test pin; failed-attempt corpus 7 evidence-linked entries close the long-standing 95-anchor sub-bullet; runner_available transparency badge restores the latent "no live ccx runner" capability disclosure stripped in Phase 35 A — but 1 of 5 error paths still Phase 37+ (WS death / no reconnect; separate live-job hook), 5 new Phase 36 R4 friction points all carry, role-branching onboarding still future, BC-setup advisor surface still Phase 37+, dynamic 4-Q gate at case-open still Phase 37+, ≥1 concrete LLM provider still Phase 41+, iso-surface + playwright WebGL E2E still Phase 39, audit-trail log + reproduce CLI still Phase 40, NAFEMS + 6 more cases still Phase 41-43, all 6 dims to 99 still Phase 44-45 — all recorded verbatim — zero score reshapes — Anthropic "real-usage eval > benchmark" preserved across 20 consecutive Tier-2 phases. Retro `.planning/retrospectives/fm04a_phase36_novice_ux_completion.md`. FINAL audit `.planning/audits/phase36_FINAL.md` + sub-agent R4 reports at `.planning/audits/phase36d_{functional_tester,novice_simulator,industrial_ui_comparator}.md` + main syntheses at `.planning/audits/phase36d_{dim4_ai_workflow,dim6_trust_reproducibility}.md`. Phase 35 stamp `@5d8f368` preserved in git history. Nothing pushed in Phase 36.
>
> **Phase 35 preamble retained below for context:**
>
> **Last updated:** 2026-05-18 (FM-04a Phase 35 A-D **Novice-UX-overhaul phase** under user's "99 分以上" mandate, targeting the explicit 新手人类用户的使用难度、交互模式 axis: 35 A `d82843d` CaseOpenAdvisorCard jargon + static-gate fix — composeBrief() no longer reads notesExcerpt; infers case kind from caseId prefix (13 case-kind mappings: hertz-contact / cantilever-buckle / cantilever-dynamic / cantilever-beam-modal+modal-cantilever / cantilever-beam+cantilever- / cylinder-pv / euler-column / plate-with-hole / plate-simply-supported+plate-ss-shell / heat-transfer / rod-wave-impact-energy-leak / rod-wave-impact / GS-) and emits curated 1-paragraph engineering orientation (Euler-Bernoulli / Kirsch / Lamé / etc.). 4-Q gate gains muted color band + italic "client-side stub status; the Visual tab renders a backend-validated gate" subtitle + `data-gate-kind="static"` attribute. 20 new frontend tests pin jargon-absence × 6 tokens + curated-orientation × 13 case-kind fixtures + static-gate-hint + data-gate-kind attribute. Closes Phase 34 D #27 + #28. 35 B `e0786ff` verdict YAML solver_kind cohort backfill — **HONEST REVISION at implementation time**: blueprint called for schema_version 1.0→1.4 bump; Phase 21/29/30 backend tests pin exact schema_version labels per case (cantilever_kirsch 1.0.0 / plate_ss_shell 1.1.0 / cantilever_dynamic 1.2.0 / heat_transfer 1.3.0), so bumping forces test-pin edits (Phase 1-N additive-only guard treats that as a code smell). Strict-additive path taken: only solver_kind field added; schema_versions preserved verbatim. 11 cohort verdicts gained solver_kind. Cohort distribution: linear_static×5 (cantilever-beam / cylinder-pv / plate-simply-supported / plate-ss-shell / plate-with-hole) / modal×2 (cantilever-beam-modal + l50) / buckling×2 (cantilever-buckle / euler-column) / dynamic×1 / heat_transfer_steady_state×1 / contact_pair_static×1 (Phase 34 C hertz-contact). New backend test pin `test_phase35b_verdict_yaml_solver_kind_backfill.py` 27/27 (4 invariants + parametrized × 12 + schema-heterogeneity preservation guard); 232/232 Phase 18-31 schema-version pinning tests pass UNCHANGED. **L:-1 NEW Phase 35 anti-gaming guard**: strict additive; schema heterogeneity declared. 35 C `31856d1` useUploadErrorRecovery hook + ErrorCard wiring — `frontend/src/state/useUploadErrorRecovery.ts` NEW (~180 LOC); owns `uploadError: ErrorCardProps | null` state + `setUploadError` / `clearUploadError` / `withRecovery(fn, options)` actions; withRecovery wraps try/catch, surfaces ErrorCard with title + message + remediation + code, auto-binds onRetry callback that re-runs fn. ErrorCard mounted conditionally in App.tsx between case-open advisor and tab buttons (data-testid="app-upload-error-mount"). 2 of 5 silent error-recovery paths closed: generateReportFromFile (FRD upload) + selectCase (case-load); remaining 3 (PDF export crude alert / WebSocket death no reconnect / stop request silent / solver-start raw [ERROR] log) carry to Phase 36+ — each needs a separate hook (live-job context). App.tsx LOC 1467→1478 (+11; **M:-1 NEW Phase 35 anti-gaming guard**: <1500 pin holds with 22 LOC headroom). 14 new frontend hook tests pin every state transition + withRecovery success + error with title/message/remediation/code + retry binding + retry-clears-stale-error semantics. 35 D 3 sub-agent R3 audits (functional / novice / industrial-UI) + 2 main-session syntheses (Dim 4 + Dim 6) + FINAL composite + retro + STATE refresh. **Phase 35 composite: 73.83/100 under rubric v2.0** — lift over Phase 34 D (72.50): **+1.33**. **Lands -0.17 below projected band 74-77 low end** (honest accounting: blueprint projected Dim 2 +7 to +11 to 66-70; realistic sub-agent score is +6 to 65 because 2 of 5 error-recovery paths closed is partial + 6 new friction points found). Per-dim: Dim 1 FEA 87→**87** (Δ 0; functional_tester R3 — Phase 35 didn't invest in cohort capability; cohort floor 12 cases / 6 solver kinds intact and now enforced by Phase 35 B test pin) / Dim 2 Novice UX 59→**65** (**Δ +6, biggest single-dim lift since v2.0 baseline**; novice_simulator R3 — user's mandate axis advanced cleanly: P1 jargon-free orientation / P3 gate clarity declared / P5 visible failure mode with retry) / Dim 3 Industrial UI 73→**73** (Δ 0; industrial_ui_comparator R3 — within ±2 noise; mean parity 3.76/10 unchanged) / Dim 4 AI workflow 72→**73** (Δ +1; main syn — static-gate semantic clarity resolves Phase 34 D -1 tension + curated orientation copy lifts 70-anchor sub-bullet quality; surface count UNCHANGED at 2; setup + solve-monitor stages still missing) / Dim 5 Viz 72→**72** (untouched; 4 missing items iso-surface / playwright WebGL / VTU-PNG frontend export / overlay all carry to Phase 39) / Dim 6 Trust 72→**73** (Δ +1; main syn — cohort-wide solver_kind invariant pin closes grep gap 4/12→12/12 + error-code surface UPLOAD/CASE-LOAD adds support-ticket provenance; failed-attempt corpus + audit-log + reproduce CLI still absent). Composite = (87+65+73+73+72+73)/6 = 73.83 simple arithmetic mean. **NOT spawning R4** per v2.3 cap discipline. **APPROVE gate FAILED by 25.17 points** — recorded honestly; 99-target reachable at Phase ~45-46 per refined multi-phase roadmap (~10-11 more phases). **NEW Phase 35 anti-gaming guards K/L/M on top of A-J all honored**: K:-1 CaseOpenAdvisorCard 5 test-ids preserved (case-open-advisor-card / -status-badge / -brief / -four-question-gate / -footer) + 1 additive new test-id (case-open-advisor-gate-hint); L:-1 schema additive only — schema_versions preserved verbatim; 232/232 Phase 18-31 pinning tests pass UNCHANGED; M:-1 App.tsx LOC 1478<1500 (22 LOC headroom). **6 NEW Phase 35 friction points** surfaced by sub-agent R3 (the exact unanticipated cost the v2.0 apparatus was designed to catch): (a) `candidateCaseRegistry.ts:151` displayLabel still carries "(Phase 20 B)" / "(Phase 21+)" suffix in some entries — Phase 35 A only sanitized the orientation half; (b) ErrorCard mount sits BELOW OperatorStatusPanel — mount position not ideal for failed-upload scenario; (c) ErrorCard role="alert" + aria-live screen-reader semantics need WCAG-grade verification; (d) Verbatim UPLOAD/CASE-LOAD codes surfaced to novices look like internal enums — humanize copy; (e) selectCase Retry re-submits same captured dummy File — minor smell; (f) Phase 35 A jargon-strip side-effect removed the latent "no live CCX runner" warning for cantilever — needs structured runner_available: boolean badge. All 6 flagged for Phase 36+. **Honest pivot #5 in FM-04a journey** (after Phase 30 D plate-ss-shell / Phase 31 A heat transfer / Phase 31 C Richardson / Phase 33 D Hertz analytical / Phase 34 C stacked-cube): Phase 35 B strict-additive interpretation of L:-1 instead of blueprint's schema bump. Documented inline in blueprint + retro + commit body. **Multi-phase roadmap toward 99+ (refined from Phase 34 FINAL with -0.17 shortfall absorbed)**: P36 Novice UX completion (3 more error paths + WCAG + onboarding role-branching) + failed-attempt corpus seed → ~76-79 / P37 Industrial UI parity round → ~79-82 / P38 FEA cohort 13-15 + new solver kind → ~82-85 / P39 Viz iso-surface + playwright WebGL → ~85-88 / P40 Trust audit-log + reproduce CLI → ~88-91 / P41-43 NAFEMS + cases 16-18 + LLM provider → ~91-95 / P44-45 final polish + first 99+ audit cycle → ~95-99. **Projected reach of 99+: Phase ~45-46.** Phase 35 +1.33 is slightly below projected ~+2.5/phase average needed but the Novice UX foundation (reusable useUploadErrorRecovery hook + case-kind orientation pattern + static-gate semantic distinction) accelerates Phase 36-37 Dim 2 work. **Phase 35 total: 61 new tests** (27 backend Phase 35 B + 34 frontend across 35 A 20 + 35 C 14); 233/233 Phase 30-35 backend cross_check tests pass; 232/232 Phase 18-31 schema-version pinning tests pass UNCHANGED; 807/807 frontend tests pass (was 773 in Phase 34; +34 net); 0 regressions vs Phase 34 baseline. Hard constraints PASS: HF1.7a/b/8 intact + *-candidate carve-out for hertz-contact-candidate + tmp_path-only test writes outside golden_samples/*-candidate + no push/PR/Linear/Notion in Phase 35 (local-commit only) + Phase 1-34 chain additive only (App.tsx LOC stays at 1478 < 1500; no test threshold edits; Phase 11 AdvisorPanel byte-identical via I:-1; CSV export schema byte-identical via J:-1; ErrorCard.tsx byte-identical via Phase 18 D composition; schema_version labels byte-identical via L:-1 strict additive). **Phase 35 thesis MET on truth axis**: jargon-leak + static-gate ambiguity closed cleanly with strong test pins; cohort-wide solver_kind grep gap closed without touching a single existing test pin (5th honest pivot documented); 2 of 5 silent error-recovery paths closed via reusable hook pattern that Phase 32 B useAppUiMode preceded — but 3 error-recovery paths still Phase 36+, role-branching onboarding still future, WCAG audit still Phase 36, BC-setup advisor surface still Phase 36-37, dynamic 4-Q gate at case-open still Phase 36+, ≥1 concrete LLM provider still Phase 41+, iso-surface + playwright WebGL E2E still Phase 39, failed-attempt corpus + audit-log + reproduce CLI still Phase 40, NAFEMS + 6 more cases still Phase 41-43, all 6 dims to 99 still Phase 44-45 — all recorded verbatim — zero score reshapes — Anthropic "real-usage eval > benchmark" preserved across 19 consecutive Tier-2 phases. Retro `.planning/retrospectives/fm04a_phase35_novice_ux_overhaul.md`. FINAL audit `.planning/audits/phase35_FINAL.md` + sub-agent R3 reports at `.planning/audits/phase35d_{functional_tester,novice_simulator,industrial_ui_comparator}.md` + main syntheses at `.planning/audits/phase35d_{dim4_ai_workflow,dim6_trust_reproducibility}.md`. Phase 34 stamp `@a1ef486` preserved in git history. Nothing pushed in Phase 35.

> **Maintained by:** Codex primary executor (default); under user direct-execution authorization 2026-05-07/16 the FM-03 closeout, FM-04a P1-P9, the local-arc closure commits (`61857f5..88362ad`), the FM-04a Phase 2 industrial polish (`b3c97ef..477c529`), the FM-04a Phase 3 reviewer-workbench polish (`7f726bb..de3e90d`), the FM-04a Phase 4 cohort-operations console (`2399c11..3e2de76`), the FM-04a Phase 5 reproducibility / schema versioning / cohort snapshots stack (`fd23f7f..4df64e2`), and the FM-04a Phase 6 reviewer drift narrative + evidence trust score stack (`cc057c5..1bf3df4` plus this STATE refresh) are authored by local Claude Opus 4.7 with the same ADR-011/012/013/023 boundaries. Codex review remains required for any path that flips this back to Codex-primary or that promotes Tier 1 → Tier 2.

This file is the **repo-side execution status snapshot**. Linear is the work-control truth for scoped issues, acceptance, blockers, and proof. GitHub/repo is the code truth. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is an architecture/control mirror patched after repo and Linear truth settle. When they conflict, **git is authoritative**; STATE.md is updated to match git, and external mirrors are patched from STATE.md.

---

## Phase ledger

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
| Phase 1.5 — Foundation-Freeze (post-pivot) | ✅ Governance/workflow gates closed: WF-00 / ENG-32 established Codex-primary + Linear work-control + Claude Opus audit; ENG-33 AERON L0 protocol salvage done via #128; FF-07 done via #129; FF-08 done via #131; FF-09 done via #132. Branch protection requires `trailer-check` and `golden-samples-validation`. |
| Phase 1.6 — RFC-001 Foundation rebuild (W1→W4) | ✅ Done 2026-04-26 → 2026-04-27 (#68-#82) | Buckets A/B/C/D + Layer-2/3 schema + CalculiX adapter + L1→L4 producers + report-cli driver. |
| Phase 1.7 — RFC-001 Workbench shell (W5) | ✅ Done 2026-04-27 (#83-#90) | Electron shell + GS-001 quick-start + violation panel + --doctor + viz tracking. |
| Phase 1.8 — RFC-001 Reporting libs + GS-101 ballistic (W6+W7) | ✅ Done 2026-04-28 (#91-#110) | Material/allowable_stress/verdict/BC/model-overview libs + DOCX wiring; OpenRadioss adapter + ballistic derivations + Dockerfile + Electron --kind=ballistic. |
| Phase 1.9 — RFC-001 3D viewport + live bake (W8) | ✅ Done 2026-04-29 (#111-#114) | OpenRadioss → VTU exporter + PyVista viewport + live streaming + Electron live-bake orchestration. |
| Phase 2 — Web Console hardening | 🟡 Active candidate lane (lean validation workflow being adopted) | Frontend build-smoke restoration landed in PR #121. Governance/workflow gates are closed. AERON-01 landed the first concrete AERON L0 backend adapter in PR #135; AERON-02 wired that backend into exactly one solver caller path in PR #137; AERON-03 surfaced backend provenance through graph cold-smoke in PR #139. ENG-39 introduces ADR-023 so Tier 0/Tier 1 development can move faster while signed physical claims remain strictly gated. |
| Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |

---


> **早期历史已归档**(Foundation-Freeze tally / W1-8 highlights / Repo state ENG-39→Phase 10 / FM-04a Phase 10 全文)→ `.planning/STATE_ARCHIVE.md`。

## Open PRs

### Recently resolved / superseded

| PR | Branch | Status | Notes |
|----|--------|--------|-------|
| #126 | `claude/L0-protocol` | CLOSED 2026-05-06 · **BLOCKED/SUPERSEDED** | Closed after #127 governance and #128 protocol salvage. Do not merge as-is. |
| #128 | `codex/aeron-l0-protocol-salvage` | MERGED 2026-05-06 · ENG-33 | Salvaged only the AERON L0 protocol package and packaging/tests from blocked #126. Does not inherit #126 root `AGENTS.md`. |
| #129 | `codex/ff-07-hf5-trailer-enforcement` | MERGED 2026-05-06 · FF-07 / ENG-16 | Landed HF5 trailer validator/workflow/docs; branch protection now requires `trailer-check`. |
| #130 | `codex/ff-07-state-closeout` | MERGED 2026-05-06 · FF-07 closeout | Verified `trailer-check` as a required branch-protection context on a follow-up PR and refreshed repo state. |
| #131 | `codex/ff-08-gs-registry-validation` | MERGED 2026-05-06 · FF-08 / ENG-17 | Landed HF3 golden-sample registry validator and `golden-samples-validation`; branch protection now requires the check. Old #28 closed as superseded. |
| #132 | `codex/ff-09-readme-adr-routing-sync` | MERGED 2026-05-06 · FF-09 / ENG-18 | Synced README, ADR-011, and `docs/governance/` with current Codex-primary workflow truth. Old #26 closed as superseded. |
| #133 | `codex/ff-09-state-closeout` | MERGED 2026-05-06 · FF-09 closeout | Refreshed STATE after #132 and confirmed no active Codex Foundation-Freeze PRs. |
| #134 | `codex/control-plane-triage-state` | MERGED 2026-05-06 · WF-01 / ENG-34 | Refreshed control-plane stale PR triage after #133; ENG-34 Done. |
| #135 | `codex/ENG-35-aeron-calculix-backend` | MERGED 2026-05-06 · AERON-01 / ENG-35 | Adds `aeron.drivers.CalculiXFEABackend`, the first concrete AERON L0 backend adapter. No protocol/schema/driver/golden-sample changes. |
| #136 | `codex/ENG-35-state-closeout` | MERGED 2026-05-06 · ENG-35 closeout | Refreshed STATE after #135 and confirmed AERON-01 Done. |
| #137 | `codex/ENG-36-aeron-solver-backend-wiring` | MERGED 2026-05-06 · AERON-02 / ENG-36 | Wires `CalculiXFEABackend` into `agents.solver.run()` with HF1 override, Opus approval, GitHub review fix, and CI green. |
| #138 | `codex/ENG-36-state-closeout` | MERGED 2026-05-06 · ENG-36 closeout | Refreshed STATE after #137 and confirmed AERON-02 Done. |
| #139 | `codex/ENG-37-aeron-graph-provenance` | MERGED 2026-05-06 · AERON-03 / ENG-37 | Surfaces additive `solve_metadata.backend` provenance through the graph cold-smoke path with HF1 override, Opus approval, and CI green. |
| #143 | `codex/ENG-39-lean-validation-workflow` | MERGED 2026-05-07 · ENG-39 | Adds ADR-023 lean validation workflow plus feature milestone `/goal` run structure. CI green, Linear ENG-39 Done, Notion mirror updated. |
| #117 | `codex/ENG-16-hf5-commit-trailers` | CLOSED · superseded by #129 | Old draft duplicate; do not reopen. |
| #118 | `codex/ENG-17-hf3-gs-registry` | CLOSED · superseded by #131 | Old draft duplicate; do not reopen. |
| #120 | `codex/ENG-18-routing-sync-plan` | CLOSED · superseded by #132 | Old draft duplicate; do not reopen. |
| #116 | `codex/ENG-11-github-sync-probe` | CLOSED 2026-05-06 · superseded by WF-00 / #127-#133 | Empty workflow probe; actual Codex-primary workflow proof now lives in the merged governance path. |

### Active Codex Foundation-Freeze PRs

| PR | Branch | Status | Notes |
|----|--------|--------|-------|
| — | — | None | ENG-45/FM-01 polish branch is active but no PR is open yet. |

### Remaining Codex/ENG-* draft backlog (blocked, no current merge path)

| PR | Linear | Status | Triage |
|----|--------|--------|--------|
| #115 | ENG-23 | OPEN DRAFT · behind main · failing `calibration-cap-check` | Real GS-101-adjacent code; possible salvage only after ENG-22/GS101 contract is made agent-eligible and PR body/checks are refreshed. Do not merge as-is. |
| #119 | ENG-20 | OPEN DRAFT · docs-only plan · behind main · failing `calibration-cap-check` | Useful planning material may be copied into a future issue, but the PR is not a merge target as-is. Recommended close or refresh under a new issue contract. |

All remaining drafts fail `calibration-cap-check` because their PR bodies predate the enforced `## Self-pass-rate` section. Treat these as backlog evidence, not active implementation branches.

### Phase 1.5 governance backlog (still relevant, needs body+Codex refresh)

| PR | Branch | Status |
|----|--------|--------|
| #26 | `feature/AI-FEA-FF-09-readme-adr-011-sync` | CLOSED · superseded by Codex replacement #132 |
| #27 | `feature/AI-FEA-FF-07-trailer-check` | CLOSED · **SUPERSEDED by #129** |
| #28 | `feature/AI-FEA-FF-08-gs-registry` | CLOSED · superseded by Codex replacement #131 |

### Surrogate hint scaffolding stack (post-pivot, P1-07 line)

| PR | Branch | Status |
|----|--------|--------|
| #30 | `feature/AI-FEA-P1-07-surrogate-hook` | OPEN · MERGEABLE · ✗1 (CI failing) |
| #36 | `feature/AI-FEA-P2-writeback-integration` | OPEN · MERGEABLE · stacked on `feature/AI-FEA-P2-github-writeback` (parent unclear; investigate) |
| #37 | `feature/AI-FEA-P1-07-simplan-adapter` | OPEN · MERGEABLE · stacked on #30 |

### Stale (W6e earlier draft, now subsumed)

| PR | Branch | Status |
|----|--------|--------|
| #103 | `feature/RFC-001-W6e-model-overview` | CLOSED · subsumed by #109 (`407436e`) and #110 (`aa66ed1`) which both merged; stale state verified on 2026-05-06, no action needed. |

### Pre-pivot P1-* (4-18, predates ADR-011 routing contract)

| PR | Branch | Status |
|----|--------|--------|
| #11 | `feature/AI-FEA-P1-02-hot-smoke` | OPEN · UNKNOWN mergeable · ✓1/✗0 |
| #12 | `feature/AI-FEA-P1-03-golden-sample-validation` | OPEN · UNKNOWN mergeable · ✗1 |
| #14 | `feature/AI-FEA-P1-06-gate-solve-lint` | OPEN · UNKNOWN mergeable · ✗1 |
| #15 | `feature/AI-FEA-P1-06b-wire-linter-solver` | OPEN · MERGEABLE · stacked on #14 |
| #16 | `feature/AI-FEA-P1-05-reviewer-fault-injection` | OPEN · UNKNOWN mergeable · ✗1 |

These predate ADR-011/012/013 governance. Disposition (rebase / close / merge under ADR-006) is **out of scope for current Phase 2 hardening** and needs a separate triage pass.

---

## Active ADRs

| ADR | Status | File |
|-----|--------|------|
| ADR-002 | Live | (referenced in code; file not in repo — in Notion) |
| ADR-004 | Live | (referenced in `agents/router.py`, `schemas/sim_state.py`) |
| ADR-005 | Live | (well_harness Notion writeback) |
| ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
| ADR-010 | Live | (notion_sync contract) |
| ADR-011 | Accepted (R5 APPROVE + R2 APPROVE on amendments) | `docs/adr/ADR-011-pivot-claude-code-takeover.md` |
| ADR-012 | Accepted · enforced via `.github/workflows/calibration-cap-check.yml` | `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` |
| ADR-013 | Accepted · CI `--check` workflow live; branch protection script `scripts/apply_branch_protection.sh` | `docs/adr/ADR-013-branch-protection-enforcement.md` |
| ADR-014 | Accepted | `docs/adr/ADR-014-ws-event-bus-for-workbench.md` |
| ADR-015 | Accepted | `docs/adr/ADR-015-workbench-agent-rpc-boundary.md` |
| ADR-016 | Accepted | `docs/adr/ADR-016-frd-vtu-result-viz.md` |
| ADR-017 | Accepted (R7 alias-annotation + subclass bypass close, PR #104) | `docs/adr/ADR-017-rag-facade-cli-lib-parity.md` |
| ADR-018 | Accepted (defer electron-builder packaging) | `docs/adr/ADR-018-electron-packaging-strategy.md` |
| ADR-019 | Accepted | `docs/adr/ADR-019-material-properties-data-model.md` |
| ADR-020 | Accepted | `docs/adr/ADR-020-allowable-stress-lookup.md` |
| ADR-021 | Accepted | `docs/adr/ADR-021-gs100-radioss-smoke-fixture.md` |
| ADR-022 | Accepted | `docs/adr/ADR-022-gs101-demo-unsigned-fixture.md` |
| ADR-023 | Accepted by user directive, implementation PR pending | `docs/adr/ADR-023-lean-validation-workflow.md` |
| ADR-024 (lite) | Accepted under user direct-execution authorization 2026-05-07; lite scope = parameters-only Børvik 2002 citation for FM-04a Tier 1; full version reserved for FM-04b | `docs/adr/ADR-024-ballistic-benchmark-source-selection.md` |

---

## Carry-overs (still open)

1. **Foundation-Freeze governance gate path**: FF-07/08/09 are merged, old #26/#27/#28 and draft duplicates #117/#118/#120 are closed, ENG-17/18 are Done, and required checks now include `trailer-check` + `golden-samples-validation`. Workflow gates are reliable enough to select a next issue, but the current Linear backlog has no agent-eligible contract.
2. **Codex/ENG-* DRAFT lane**: remaining open drafts are ENG-20 (#119 planning doc) and ENG-23 (#115 real GS-101-adjacent code). Recommended: close or refresh #119 under a new issue; keep #115 only if ENG-22/GS101 acceptance is explicitly contracted.
3. **Pre-pivot P1-* (#11-#16) and surrogate stack (#30/#36/#37)** disposition deferred since 2026-04-25. These PRs predate ADR-011/012/013 and should not be merged without a separate Codex-owned triage/rebuild issue.
4. **GS-001/002/003 status flip** to `insufficient_evidence` (proposed in FP-001/002/003) — Notion control-plane status field still not changed.
5. **AERON L0 adoption**: ENG-33 / PR #128 salvaged the protocol package; ENG-35 / PR #135 landed the first concrete `CalculiXFEABackend`; ENG-36 / PR #137 wired that backend into `agents.solver.run()` while preserving the existing solver-node `SimState -> dict` contract; ENG-37 / PR #139 surfaced backend provenance through the graph cold-smoke path without starting GS101 or signed-validation work. Next AERON work should be an explicit Linear contract for one user-facing adoption point, not GS101 or signed validation by implication.

---

## How to update this file

Update STATE.md whenever:

- A FF-task changes status (pending → in-flight → done).
- A branch is pushed or a PR opens / merges.
- An ADR is accepted, revised, or superseded.
- A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
- The `Last updated` stamp must change in the same commit.

**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.

exec
/bin/zsh -lc "git diff --stat && printf '\\n--- cached stat ---\\n' && git diff --cached --stat && printf '\\n--- name-only ---\\n' && git diff --name-only && printf '\\n--- cached name-only ---\\n' && git diff --cached --name-only" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'git diff -- frontend/src/App.tsx frontend/src/components/AdvancedModePromo.tsx frontend/src/components/CaseBrowser.tsx frontend/src/components/OnboardingTour.tsx frontend/src/components/ProjectManager.tsx frontend/src/index.css' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 3465ms:
2026-05-29 11:52:10.332 xcodebuild[3163:81707630]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:10.706 xcodebuild[3163:81707628] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-9QEAiCoR' (errno=Operation not permitted)
2026-05-29 11:52:11.592 xcodebuild[3179:81707683]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:11.827 xcodebuild[3179:81707678] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
diff --git a/frontend/src/App.tsx b/frontend/src/App.tsx
index 7d48871..aec8f23 100644
--- a/frontend/src/App.tsx
+++ b/frontend/src/App.tsx
@@ -1222,7 +1222,7 @@ function App() {
   ])
 
   return (
-    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '240px 300px 1fr', height: '100vh' }}>
+    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '210px 300px 1fr', height: '100vh' }}>
       {/* FM-04a Phase 29 C — onboarding tour + advanced-mode auto-
           promote mounted at App-root so reviewers landing on the
           Narrative tab (or any future tab) still see onboarding.
@@ -1303,22 +1303,31 @@ function App() {
               }}
             />
 
-            <div style={{ padding: '40px', flex: 1 }}>
+            {/* FM-04a Phase 41.2 — flex column so the trust/governance panel is
+                demoted via CSS `order` BELOW the case + 3D viewport (demo-first:
+                lead with the result, not the compliance dashboard). DOM order
+                unchanged; ErrorCard keeps order 0 (red band still first). */}
+            <div style={{ padding: '40px', flex: 1, display: 'flex', flexDirection: 'column' }}>
             {/* FM-04a Phase 36 B — ErrorCard mounts ABOVE
                 OperatorStatusPanel so a failed user sees the red
                 error band before the trust prose (Phase 35 R3
                 friction point b). */}
             {uploadError && (
-                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px' }}>
+                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px', order: 0 }}>
                     <ErrorCard {...uploadError} />
                 </div>
             )}
 
+            {/* order: 5 → demoted below the golden-path content (tabs + viewport,
+                order 0). The "Evidence & trust center" is reachable by scroll,
+                not the landing hero. */}
+            <div style={{ order: 5, marginTop: '32px' }}>
             <OperatorStatusPanel
               strip={trustStrip}
               sections={trustSections}
               goldenSamples={goldenSampleQueue}
             />
+            </div>
 
             {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
             {!activeCaseId && (
@@ -1327,7 +1336,7 @@ function App() {
                 </div>
             )}
 
-            <div className="glass-panel" style={{ padding: '8px', display: 'flex', gap: '8px', width: 'fit-content', marginBottom: '32px' }}>
+            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
                 <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                 <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                 {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
@@ -1391,7 +1400,7 @@ function App() {
                         <div className="shimmer-active" style={{ height: '400px', width: '100%', borderRadius: '12px', background: 'var(--bg-surface)' }}></div>
                     ) : report ? (
                         <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
-                            <div className="glass-panel" style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
+                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
                                 {activeTab === 'visual' ? (
                                     <div
                                       style={{
diff --git a/frontend/src/components/AdvancedModePromo.tsx b/frontend/src/components/AdvancedModePromo.tsx
index 126b036..12cd3f1 100644
--- a/frontend/src/components/AdvancedModePromo.tsx
+++ b/frontend/src/components/AdvancedModePromo.tsx
@@ -129,7 +129,10 @@ export function AdvancedModePromo({
     >
       <div className={POLISH_CLASS_ADVANCED_MODE_PROMO} style={STYLES.card}>
         <div style={STYLES.header}>
-          <span style={STYLES.eyebrow}>Phase 25 C · Phase 28 D</span>
+          {/* FM-04a Phase 41.2 — was "Phase 25 C · Phase 28 D" (internal
+              build cadence leaked to the user). Replaced with a
+              user-meaningful eyebrow. */}
+          <span style={STYLES.eyebrow}>Workbench tip</span>
         </div>
         <h2 style={STYLES.title}>Want to see the advanced controls?</h2>
         <p style={STYLES.body}>
diff --git a/frontend/src/components/CaseBrowser.tsx b/frontend/src/components/CaseBrowser.tsx
index 37f0d47..3f1dfda 100644
--- a/frontend/src/components/CaseBrowser.tsx
+++ b/frontend/src/components/CaseBrowser.tsx
@@ -126,6 +126,7 @@ export function CaseBrowser({
           value={searchQuery}
           onChange={(e) => setSearchQuery(e.target.value)}
           data-testid="case-browser-search-input"
+          className="cb-search"
           style={searchInputStyle}
         />
         <button
@@ -133,6 +134,7 @@ export function CaseBrowser({
           data-testid="case-browser-tier2-chip"
           aria-pressed={tier2Only}
           onClick={() => setTier2Only((v) => !v)}
+          className="cb-chip"
           style={tier2Only ? chipActiveStyle : chipIdleStyle}
         >
           Tier 2 validated
@@ -171,6 +173,7 @@ export function CaseBrowser({
                       onClick={() => onSelectCase(c.caseId)}
                       data-testid={`case-browser-row-${c.caseId}`}
                       data-active={focusedCaseId === c.caseId ? 'true' : undefined}
+                      className="cb-case-card"
                       style={
                         focusedCaseId === c.caseId
                           ? caseRowActiveStyle
@@ -317,14 +320,15 @@ export function previewBlurbFor(caseId: string): string {
 }
 
 const rootStyle: CSSProperties = {
-  borderRadius: 10,
+  borderRadius: 'var(--r-lg)',
   border: '1px solid var(--border)',
   background: 'var(--bg-surface)',
-  padding: 14,
+  padding: 'var(--sp-6)',
   display: 'flex',
   flexDirection: 'column',
-  gap: 10,
+  gap: 'var(--sp-4)',
   color: 'var(--text-primary)',
+  boxShadow: 'var(--elev-2)',
 }
 const headerStyle: CSSProperties = {
   display: 'flex',
@@ -333,9 +337,9 @@ const headerStyle: CSSProperties = {
   justifyContent: 'space-between',
 }
 const titleStyle: CSSProperties = {
-  fontSize: 14,
-  fontWeight: 600,
-  letterSpacing: '0.02em',
+  fontSize: 'var(--fs-lg)',
+  fontWeight: 700,
+  letterSpacing: 'var(--tracking-tight)',
 }
 const countStyle: CSSProperties = {
   fontSize: 11,
@@ -355,9 +359,9 @@ const searchInputStyle: CSSProperties = {
   background: 'var(--bg-muted, rgba(255,255,255,0.04))',
   border: '1px solid var(--border)',
   color: 'var(--text-primary)',
-  padding: '6px 10px',
-  borderRadius: 6,
-  fontSize: 12,
+  padding: '8px 12px',
+  borderRadius: 'var(--r-sm)',
+  fontSize: 'var(--fs-sm)',
 }
 const chipBase: CSSProperties = {
   fontSize: 11,
@@ -417,15 +421,18 @@ const caseListStyle: CSSProperties = {
   listStyle: 'none',
   display: 'flex',
   flexDirection: 'column',
-  gap: 2,
+  gap: 'var(--sp-1)',
 }
 const caseRowBase: CSSProperties = {
-  display: 'block',
+  display: 'flex',
+  alignItems: 'center',
+  justifyContent: 'space-between',
+  gap: 'var(--sp-3)',
   width: '100%',
   textAlign: 'left',
-  fontSize: 13,
-  padding: '6px 10px',
-  borderRadius: 6,
+  fontSize: 'var(--fs-sm)',
+  padding: 'var(--sp-3) var(--sp-4)',
+  borderRadius: 'var(--r-md)',
   border: '1px solid transparent',
   cursor: 'pointer',
   fontFamily: 'inherit',
@@ -437,18 +444,21 @@ const caseRowIdleStyle: CSSProperties = {
 }
 const caseRowActiveStyle: CSSProperties = {
   ...caseRowBase,
-  background: 'var(--bg-muted, rgba(255,255,255,0.06))',
-  border: '1px solid var(--border)',
+  background: 'var(--accent-glow)',
+  border: '1px solid var(--border-focus)',
 }
 const previewPaneStyle: CSSProperties = {
-  borderRadius: 8,
+  borderRadius: 'var(--r-lg)',
   border: '1px solid var(--border)',
   background: 'var(--bg-muted, rgba(255,255,255,0.03))',
-  padding: 12,
+  padding: 'var(--sp-5)',
   display: 'flex',
   flexDirection: 'column',
-  gap: 6,
+  gap: 'var(--sp-2)',
   minHeight: 100,
+  boxShadow: 'var(--elev-1)',
+  position: 'sticky',
+  top: 'var(--sp-4)',
 }
 const previewHeaderStyle: CSSProperties = {
   display: 'flex',
diff --git a/frontend/src/components/OnboardingTour.tsx b/frontend/src/components/OnboardingTour.tsx
index ed85dec..e6f9df7 100644
--- a/frontend/src/components/OnboardingTour.tsx
+++ b/frontend/src/components/OnboardingTour.tsx
@@ -103,7 +103,11 @@ export function OnboardingTour({
       <style>{ONBOARDING_TOUR_KEYFRAMES}</style>
       <div style={STYLES.card} className="onboarding-tour-card">
         <div style={STYLES.header}>
-          <span style={STYLES.shipped}>{step.shippedInPhase}</span>
+          {/* FM-04a Phase 41.2 — dev-phase provenance badge
+              (step.shippedInPhase, e.g. "Phase 23 B") removed from the
+              user-facing tour: it leaked the internal build cadence into
+              the demo. The 1/N progress label carries the only
+              user-meaningful position info. Closes Phase 39 audit #2. */}
           <span data-testid="onboarding-progress" style={STYLES.progress}>
             {progressLabel(state)}
           </span>
diff --git a/frontend/src/components/ProjectManager.tsx b/frontend/src/components/ProjectManager.tsx
index ba843d4..71e1dbe 100644
--- a/frontend/src/components/ProjectManager.tsx
+++ b/frontend/src/components/ProjectManager.tsx
@@ -1,5 +1,13 @@
-import { useState, useEffect } from 'react';
-import { Folder, FolderPlus, Clock, Layout } from 'lucide-react';
+// FM-04a Phase 41.2 — ProjectManager restyle. The pre-41 markup used
+// Tailwind utility classes (bg-slate-*/text-indigo-*/w-64/space-y-*), but
+// this project has NO Tailwind pipeline, so every one of those classes was
+// DEAD — the left rail rendered as unstyled browser defaults (the "empty
+// broken rail" the demo audit flagged). This rewrite swaps the dead Tailwind
+// for the real 41.1 token system + the existing .glass-sidebar / .case-item /
+// .glass-panel shared classes. Behavior (fetch, create, select, modal) is
+// unchanged.
+import { useState, useEffect, type CSSProperties } from 'react';
+import { Folder, FolderPlus, Clock } from 'lucide-react';
 
 interface Project {
   id: number;
@@ -27,7 +35,7 @@ export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectMa
 
   const handleCreateProject = async () => {
     if (!newProject.name) return;
-    
+
     try {
       const resp = await fetch('http://localhost:8000/api/v1/projects', {
         method: 'POST',
@@ -46,79 +54,75 @@ export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectMa
   };
 
   return (
-    <div className="flex flex-col h-full bg-slate-900/50 border-r border-slate-800 w-64">
-      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
-        <div className="flex items-center space-x-2">
-          <Layout className="w-5 h-5 text-indigo-400" />
-          <h2 className="font-semibold text-slate-200">Projects</h2>
-        </div>
-        <button 
+    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
+      <div style={headerStyle}>
+        <span className="eyebrow">Projects</span>
+        <button
+          type="button"
           onClick={() => setIsModalOpen(true)}
-          className="p-1 hover:bg-slate-800 rounded-md transition-colors text-slate-400 hover:text-indigo-400"
+          aria-label="Create new project"
+          style={addButtonStyle}
         >
-          <FolderPlus className="w-5 h-5" />
+          <FolderPlus size={16} />
         </button>
       </div>
 
-      <div className="flex-1 overflow-y-auto p-2 space-y-1">
-        {projects.map(project => (
-          <button
-            key={project.id}
-            onClick={() => onSelectProject(project.id)}
-            className={`w-full text-left p-3 rounded-lg flex items-center group transition-all ${
-              selectedProjectId === project.id 
-                ? 'bg-indigo-600/20 border border-indigo-500/50' 
-                : 'hover:bg-slate-800 border border-transparent'
-            }`}
-          >
-            <Folder className={`w-4 h-4 mr-3 ${selectedProjectId === project.id ? 'text-indigo-400' : 'text-slate-500'}`} />
-            <div className="flex-1 overflow-hidden">
-              <div className={`text-sm font-medium truncate ${selectedProjectId === project.id ? 'text-white' : 'text-slate-300'}`}>
-                {project.name}
-              </div>
-              <div className="text-[10px] text-slate-500 truncate flex items-center mt-0.5">
-                <Clock className="w-3 h-3 mr-1" />
-                {new Date(project.created_at).toLocaleDateString()}
-              </div>
-            </div>
-          </button>
-        ))}
+      <div style={listStyle}>
+        {projects.map(project => {
+          const active = selectedProjectId === project.id;
+          return (
+            <button
+              key={project.id}
+              onClick={() => onSelectProject(project.id)}
+              className={`case-item${active ? ' active' : ''}`}
+              style={{ ...projectButtonStyle, ...(active ? projectButtonActiveStyle : null) }}
+            >
+              <Folder size={15} style={{ color: active ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0 }} />
+              <span style={{ flex: 1, overflow: 'hidden' }}>
+                <span style={{ ...projectNameStyle, color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
+                  {project.name}
+                </span>
+                <span style={projectDateStyle}>
+                  <Clock size={11} />
+                  {new Date(project.created_at).toLocaleDateString()}
+                </span>
+              </span>
+            </button>
+          );
+        })}
+        {projects.length === 0 && (
+          <p style={emptyHintStyle}>No projects yet. Create one to organize your analyses.</p>
+        )}
       </div>
 
       {isModalOpen && (
-        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
-          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
-            <h3 className="text-xl font-bold text-white mb-4">Create New Project</h3>
-            <div className="space-y-4">
+        <div style={modalOverlayStyle}>
+          <div className="glass-panel" style={modalCardStyle}>
+            <h3 style={modalTitleStyle}>Create new project</h3>
+            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
               <div>
-                <label className="block text-sm font-medium text-slate-400 mb-1">Project Name</label>
-                <input 
+                <label style={fieldLabelStyle}>Project name</label>
+                <input
                   value={newProject.name}
-                  onChange={e => setNewProject({...newProject, name: e.target.value})}
-                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
-                  placeholder="e.g. Truss Bridge Design"
+                  onChange={e => setNewProject({ ...newProject, name: e.target.value })}
+                  style={fieldInputStyle}
+                  placeholder="e.g. Truss bridge design"
                 />
               </div>
               <div>
-                <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
-                <textarea 
+                <label style={fieldLabelStyle}>Description</label>
+                <textarea
                   value={newProject.description}
-                  onChange={e => setNewProject({...newProject, description: e.target.value})}
-                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white h-24 focus:outline-none focus:ring-2 focus:ring-indigo-500"
-                  placeholder="Analyze the structural stability of..."
+                  onChange={e => setNewProject({ ...newProject, description: e.target.value })}
+                  style={{ ...fieldInputStyle, height: 96, resize: 'vertical' }}
+                  placeholder="Analyze the structural stability of…"
                 />
               </div>
-              <div className="flex space-x-3 pt-2">
-                <button 
-                  onClick={() => setIsModalOpen(false)}
-                  className="flex-1 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
-                >
+              <div style={{ display: 'flex', gap: 'var(--sp-3)', paddingTop: 'var(--sp-1)' }}>
+                <button type="button" onClick={() => setIsModalOpen(false)} style={cancelButtonStyle}>
                   Cancel
                 </button>
-                <button 
-                  onClick={handleCreateProject}
-                  className="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors font-semibold"
-                >
+                <button type="button" onClick={handleCreateProject} style={createButtonStyle}>
                   Create
                 </button>
               </div>
@@ -129,3 +133,140 @@ export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectMa
     </div>
   );
 }
+
+const rootStyle: CSSProperties = {
+  display: 'flex',
+  flexDirection: 'column',
+  height: '100%',
+  overflow: 'hidden',
+};
+const headerStyle: CSSProperties = {
+  padding: 'var(--sp-4)',
+  borderBottom: '1px solid var(--border)',
+  display: 'flex',
+  alignItems: 'center',
+  justifyContent: 'space-between',
+};
+const addButtonStyle: CSSProperties = {
+  display: 'inline-flex',
+  alignItems: 'center',
+  justifyContent: 'center',
+  padding: 'var(--sp-1)',
+  borderRadius: 'var(--r-sm)',
+  border: '1px solid var(--border)',
+  background: 'transparent',
+  color: 'var(--text-secondary)',
+  cursor: 'pointer',
+};
+const listStyle: CSSProperties = {
+  flex: 1,
+  overflowY: 'auto',
+  padding: 'var(--sp-2)',
+  display: 'flex',
+  flexDirection: 'column',
+  gap: 'var(--sp-1)',
+};
+const projectButtonStyle: CSSProperties = {
+  width: '100%',
+  textAlign: 'left',
+  display: 'flex',
+  alignItems: 'center',
+  gap: 'var(--sp-3)',
+  padding: 'var(--sp-3)',
+  borderRadius: 'var(--r-md)',
+  border: '1px solid transparent',
+  background: 'transparent',
+  cursor: 'pointer',
+  fontFamily: 'inherit',
+};
+const projectButtonActiveStyle: CSSProperties = {
+  background: 'var(--accent-glow)',
+  border: '1px solid var(--border-focus)',
+};
+const projectNameStyle: CSSProperties = {
+  display: 'block',
+  fontSize: 'var(--fs-sm)',
+  fontWeight: 600,
+  whiteSpace: 'nowrap',
+  overflow: 'hidden',
+  textOverflow: 'ellipsis',
+};
+const projectDateStyle: CSSProperties = {
+  display: 'flex',
+  alignItems: 'center',
+  gap: 4,
+  marginTop: 2,
+  fontSize: 'var(--fs-xs)',
+  color: 'var(--text-muted)',
+};
+const emptyHintStyle: CSSProperties = {
+  margin: 0,
+  padding: 'var(--sp-3)',
+  fontSize: 'var(--fs-xs)',
+  color: 'var(--text-muted)',
+  lineHeight: 1.5,
+};
+const modalOverlayStyle: CSSProperties = {
+  position: 'fixed',
+  inset: 0,
+  background: 'rgba(0, 0, 0, 0.6)',
+  backdropFilter: 'blur(4px)',
+  display: 'flex',
+  alignItems: 'center',
+  justifyContent: 'center',
+  zIndex: 50,
+  padding: 'var(--sp-4)',
+};
+const modalCardStyle: CSSProperties = {
+  width: '100%',
+  maxWidth: 420,
+  padding: 'var(--sp-6)',
+  boxShadow: 'var(--elev-3)',
+};
+const modalTitleStyle: CSSProperties = {
+  margin: '0 0 var(--sp-4)',
+  fontSize: 'var(--fs-lg)',
+  fontWeight: 700,
+  letterSpacing: 'var(--tracking-tight)',
+  color: 'var(--text-primary)',
+};
+const fieldLabelStyle: CSSProperties = {
+  display: 'block',
+  marginBottom: 'var(--sp-1)',
+  fontSize: 'var(--fs-sm)',
+  fontWeight: 500,
+  color: 'var(--text-secondary)',
+};
+const fieldInputStyle: CSSProperties = {
+  width: '100%',
+  boxSizing: 'border-box',
+  background: 'var(--c-900)',
+  border: '1px solid var(--border)',
+  borderRadius: 'var(--r-sm)',
+  padding: 'var(--sp-2) var(--sp-3)',
+  color: 'var(--text-primary)',
+  fontFamily: 'inherit',
+  fontSize: 'var(--fs-sm)',
+};
+const cancelButtonStyle: CSSProperties = {
+  flex: 1,
+  padding: 'var(--sp-2)',
+  background: 'transparent',
+  border: '1px solid var(--border)',
+  color: 'var(--text-secondary)',
+  borderRadius: 'var(--r-sm)',
+  cursor: 'pointer',
+  fontFamily: 'inherit',
+  fontWeight: 600,
+};
+const createButtonStyle: CSSProperties = {
+  flex: 1,
+  padding: 'var(--sp-2)',
+  background: 'var(--accent)',
+  border: '1px solid var(--accent)',
+  color: '#04130d',
+  borderRadius: 'var(--r-sm)',
+  cursor: 'pointer',
+  fontFamily: 'inherit',
+  fontWeight: 700,
+};
diff --git a/frontend/src/index.css b/frontend/src/index.css
index 3c8ec30..d0b412c 100644
--- a/frontend/src/index.css
+++ b/frontend/src/index.css
@@ -1,25 +1,98 @@
-@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
+@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
+
+/*
+ * FM-04a Phase 41.1 — modern-premium design-token foundation.
+ *
+ * Aesthetic target: Linear / Vercel / Arc — near-black tinted surfaces,
+ * restrained accent, layered elevation, refined typography + motion.
+ *
+ * Back-compat contract: every token name + shared class name from the
+ * pre-41 foundation is preserved (a few are refined in value, none
+ * removed). Existing `var(--token)` consumers and `.glass-*`/`.case-item`
+ * consumers keep working unchanged. New scales are additive.
+ *
+ * Anti-gaming guard B:-1 — `prefers-reduced-motion: reduce` honored at
+ * the foundation level (see bottom). WCAG 1.4.3 — text tokens kept ≥4.5:1
+ * on their intended surface (see per-token notes).
+ */
 
 :root {
-  --bg-base: #020617;
-  --bg-sidebar: rgba(15, 23, 42, 0.8);
-  --bg-surface: rgba(30, 41, 59, 0.5);
-  
-  --accent: #10b981;
-  --accent-glow: rgba(16, 185, 129, 0.2);
-  
-  --text-primary: #f8fafc;
-  --text-secondary: #94a3b8;
-  --text-muted: #828fa6; /* Phase 38 C: raised from #64748b (3.74:1 on glass, FAIL) to 4.5:1+ per WCAG 1.4.3 */
-  
-  --border: rgba(255, 255, 255, 0.08);
-  --border-focus: rgba(16, 185, 129, 0.4);
-  
-  --glass-blur: blur(16px);
-  --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
-  
+  /* ---- Neutral ramp (slate, blue-tinted near-black → white) ---------- */
+  --c-950: #060a14;   /* deepest base */
+  --c-900: #0b1120;
+  --c-850: #0f1729;
+  --c-800: #151f33;
+  --c-700: #1d2940;
+  --c-600: #2a3852;
+  --c-500: #3d4d6a;
+  --c-400: #5b6c8a;
+  --c-300: #8c9bb5;   /* ≥4.5:1 on --c-900 */
+  --c-200: #b8c3d6;
+  --c-100: #dde3ee;
+  --c-50:  #f4f7fc;
+
+  /* ---- Accent ramp (emerald, kept as the brand hue) ------------------ */
+  --accent-700: #047857;
+  --accent-600: #059669;
+  --accent-500: #10b981;   /* primary brand accent (unchanged value) */
+  --accent-400: #34d399;
+  --accent-300: #6ee7b7;
+
+  /* ---- Status hues ---------------------------------------------------- */
+  --info-400: #60a5fa;
+  --warn-400: #fbbf24;
+  --danger-400: #f87171;
+  --danger-300: #fca5a5;
+
+  /* ---- Legacy semantic tokens (PRESERVED names; values refined) ------ */
+  --bg-base: var(--c-950);
+  --bg-sidebar: rgba(11, 17, 32, 0.72);
+  --bg-surface: rgba(21, 31, 51, 0.55);
+
+  --accent: var(--accent-500);
+  /* 41.2 RESTRAINED-ACCENT: accent = the single primary action (Run Solver /
+     active tab+case / focus ring) only — never neutral-card borders, never a
+     glow wash; tint fills cap at ~10% alpha. */
+  --accent-glow: rgba(16, 185, 129, 0.10);   /* 41.2: 0.18→0.10, calm tint not neon */
+
+  --text-primary: #f6f9ff;
+  --text-secondary: #aab6cc;            /* ≥4.5:1 on base + glass */
+  --text-muted: #8b97ad;                /* WCAG 1.4.3 ≥4.5:1 (was #828fa6) */
+
+  --border: rgba(255, 255, 255, 0.07);
+  --border-strong: rgba(255, 255, 255, 0.12);
+  --border-focus: rgba(16, 185, 129, 0.45);
+
+  --glass-blur: blur(18px) saturate(140%);
+
+  /* ---- Elevation (layered soft shadows, Linear-style) ---------------- */
+  --elev-1: 0 1px 2px rgba(0, 0, 0, 0.32), 0 1px 1px rgba(0, 0, 0, 0.24);
+  --elev-2: 0 4px 12px -2px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
+  --elev-3: 0 12px 32px -8px rgba(0, 0, 0, 0.5), 0 6px 12px -6px rgba(0, 0, 0, 0.4);
+  --shadow-lg: var(--elev-3);            /* PRESERVED name */
+  --glow-accent: 0 0 0 1px rgba(16, 185, 129, 0.30), var(--elev-2);   /* 41.2: emerald-halo → accent ring + neutral elevation */
+
+  /* ---- Spacing rhythm (4px base) ------------------------------------- */
+  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
+  --sp-5: 20px; --sp-6: 24px; --sp-8: 32px; --sp-10: 40px; --sp-12: 48px;
+
+  /* ---- Radius scale --------------------------------------------------- */
+  --r-xs: 4px; --r-sm: 6px; --r-md: 10px; --r-lg: 14px; --r-xl: 20px; --r-full: 999px;
+
+  /* ---- Type scale ----------------------------------------------------- */
+  --fs-xs: 0.72rem; --fs-sm: 0.82rem; --fs-base: 0.94rem;
+  --fs-md: 1.05rem; --fs-lg: 1.25rem; --fs-xl: 1.6rem; --fs-2xl: 2.1rem;
+  --tracking-tight: -0.014em;
+  --tracking-wide: 0.06em;
+  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
+
+  /* ---- Motion --------------------------------------------------------- */
+  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
+  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
+  --dur-fast: 130ms; --dur-base: 200ms; --dur-slow: 320ms;
+
   font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
-  line-height: 1.5;
+  line-height: 1.55;
   font-weight: 400;
 
   color: var(--text-primary);
@@ -37,136 +110,288 @@ body {
   min-width: 320px;
   min-height: 100vh;
   overflow: hidden;
+  /* Premium ambient depth: two faint accent/cool light wells over the
+     near-black base. Fixed, non-interactive, cheap (paint-once). */
+  background-color: var(--bg-base);
+  background-image:
+    radial-gradient(900px 600px at 78% -8%, rgba(16, 185, 129, 0.07), transparent 60%),
+    radial-gradient(1000px 700px at -6% 110%, rgba(56, 96, 165, 0.08), transparent 60%);
+  background-attachment: fixed;
 }
 
 #root {
   width: 100%;
 }
 
-/* Scrollbar Styles */
-::-webkit-scrollbar {
-  width: 6px;
-  height: 6px;
+/* Headings — tight tracking is the single biggest "premium" tell. */
+h1, h2, h3, h4 {
+  letter-spacing: var(--tracking-tight);
+  font-weight: 700;
+  line-height: 1.2;
 }
 
-::-webkit-scrollbar-track {
-  background: transparent;
+/* Eyebrow / section-label all-caps text reads as refined when tracked out. */
+.eyebrow,
+[data-eyebrow] {
+  text-transform: uppercase;
+  letter-spacing: var(--tracking-wide);
+  font-size: var(--fs-xs);
+  font-weight: 600;
+  color: var(--text-muted);
 }
 
-::-webkit-scrollbar-thumb {
-  background: var(--border);
-  border-radius: 10px;
+::selection {
+  background: rgba(16, 185, 129, 0.28);
+  color: var(--text-primary);
 }
 
-::-webkit-scrollbar-thumb:hover {
-  background: var(--text-muted);
+:focus-visible {
+  outline: 2px solid var(--accent-400);
+  outline-offset: 2px;
+  border-radius: var(--r-xs);
 }
 
-/* Glassmorphism Classes */
+/* ---- Scrollbar ------------------------------------------------------- */
+::-webkit-scrollbar { width: 8px; height: 8px; }
+::-webkit-scrollbar-track { background: transparent; }
+::-webkit-scrollbar-thumb {
+  background: var(--c-600);
+  border-radius: var(--r-full);
+  border: 2px solid transparent;
+  background-clip: padding-box;
+}
+::-webkit-scrollbar-thumb:hover { background: var(--c-500); background-clip: padding-box; }
+
+/* ---- Glass surfaces (PRESERVED class names, refined) ----------------- */
 .glass-panel {
-  background: var(--bg-surface);
+  background:
+    linear-gradient(180deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0) 40%),
+    var(--bg-surface);
   backdrop-filter: var(--glass-blur);
+  -webkit-backdrop-filter: var(--glass-blur);
   border: 1px solid var(--border);
-  border-radius: 12px;
+  border-radius: var(--r-lg);
+  box-shadow: var(--elev-2);
 }
 
 .glass-sidebar {
   background: var(--bg-sidebar);
   backdrop-filter: var(--glass-blur);
+  -webkit-backdrop-filter: var(--glass-blur);
   border-right: 1px solid var(--border);
 }
 
-/* Sidebar Case Item */
+/* ---- Sidebar case item (PRESERVED) ----------------------------------- */
 .case-item {
-  transition: all 0.2s ease;
+  transition: background var(--dur-fast) var(--ease-out),
+              color var(--dur-fast) var(--ease-out),
+              transform var(--dur-fast) var(--ease-out);
+  border-radius: var(--r-sm);
 }
-
 .case-item:hover {
-  background: rgba(255, 255, 255, 0.03) !important;
+  background: rgba(255, 255, 255, 0.045) !important;
   color: var(--text-primary) !important;
 }
-
 .case-item.active {
   background: var(--accent-glow) !important;
   border-left: 3px solid var(--accent);
-  border-radius: 0 8px 8px 0;
+  border-radius: 0 var(--r-sm) var(--r-sm) 0;
 }
 
-/* Tab Button Glow */
+/* ---- Tab active glow (PRESERVED) ------------------------------------- */
 .tab-button-active {
-  box-shadow: 0 0 15px var(--accent-glow);
+  box-shadow: var(--glow-accent);   /* 41.2: de-glow, reuse calm ring */
 }
 
-/* Responsive Media Queries */
-@media (max-width: 1024px) {
-  .app-container {
-    grid-template-columns: 240px 1fr !important;
-  }
+/* ====================================================================
+   FM-04a Phase 41.2 — calm-premium primitives (Claude/Codex aesthetic).
+   Opt-in classes; no existing markup is forced to change. All values use
+   41.1 tokens. New motion is honored in the reduced-motion block below.
+   ==================================================================== */
+
+/* Canonical calm content card — solid (no blur), quiet border, soft lift. */
+.surface-card {
+  background:
+    linear-gradient(180deg, rgba(255, 255, 255, 0.018), transparent 38%),
+    var(--c-900);
+  border: 1px solid var(--border);
+  border-radius: var(--r-lg);
+  box-shadow: var(--elev-1);
+  transition: border-color var(--dur-base) var(--ease-out),
+              box-shadow var(--dur-base) var(--ease-out);
+}
+.surface-card.is-interactive:hover,
+a.surface-card:hover,
+button.surface-card:hover {
+  border-color: var(--border-strong);
+  box-shadow: var(--elev-2);
+}
+
+/* Type-rhythm helpers. */
+.heading-tight {
+  font-size: var(--fs-md);
+  font-weight: 600;
+  letter-spacing: var(--tracking-tight);
+  line-height: 1.25;
+  color: var(--text-primary);
+}
+.body-muted {
+  font-size: var(--fs-sm);
+  color: var(--text-secondary);
+  line-height: 1.6;
+}
+
+/* Canonical entrance motion. */
+@keyframes fm04a-rise-in {
+  from { opacity: 0; transform: translateY(8px); }
+  to   { opacity: 1; transform: translateY(0); }
 }
+.rise-in { animation: fm04a-rise-in var(--dur-base) var(--ease-out) both; }
 
+/* Case-browser hero classes (landing). */
+.cb-case-card {
+  transition: transform var(--dur-fast) var(--ease-out),
+              border-color var(--dur-fast) var(--ease-out),
+              background var(--dur-fast) var(--ease-out),
+              box-shadow var(--dur-base) var(--ease-out);
+}
+.cb-case-card:hover {
+  transform: translateY(-1px);
+  border-color: var(--border-strong);
+  background: rgba(255, 255, 255, 0.045);
+  box-shadow: var(--elev-2);
+}
+.cb-chip {
+  transition: background var(--dur-fast) var(--ease-out),
+              border-color var(--dur-fast) var(--ease-out),
+              color var(--dur-fast) var(--ease-out);
+}
+.cb-chip:hover { border-color: var(--border-strong); color: var(--text-primary); }
+.cb-search { transition: border-color var(--dur-fast) var(--ease-out); }
+.cb-search:focus-visible { border-color: var(--border-focus); outline: none; }
+.cb-tier-badge {
+  display: inline-flex;
+  align-items: center;
+  font-size: var(--fs-xs);
+  font-weight: 600;
+  letter-spacing: var(--tracking-wide);
+  padding: 1px var(--sp-2);
+  border-radius: var(--r-full);
+  background: rgba(255, 255, 255, 0.04);
+  border: 1px solid var(--border);
+  color: var(--text-muted);
+}
+.cb-tier-badge[data-tier2] {
+  background: var(--accent-glow);
+  border-color: var(--border-focus);
+  color: var(--accent-300);
+}
+
+/* Viewport-hero + tab-pill + in-viewport toggle (active-case golden path). */
+.viewport-hero {
+  border: 1px solid var(--border-strong);
+  border-radius: var(--r-xl);
+  background:
+    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0) 38%),
+    var(--bg-surface);
+  box-shadow: var(--elev-3);
+  overflow: hidden;
+}
+.tab-pill-bar {
+  display: flex;
+  gap: var(--sp-1);
+  padding: var(--sp-1);
+  width: fit-content;
+  border: 1px solid var(--border);
+  border-radius: var(--r-md);
+  background: var(--bg-surface);
+}
+.tab-pill {
+  padding: var(--sp-2) var(--sp-4);
+  border: none;
+  border-radius: var(--r-sm);
+  background: transparent;
+  color: var(--text-secondary);
+  font-weight: 600;
+  font-size: var(--fs-sm);
+  cursor: pointer;
+  display: flex;
+  align-items: center;
+  gap: var(--sp-2);
+  transition: background var(--dur-fast) var(--ease-out),
+              color var(--dur-fast) var(--ease-out);
+}
+.tab-pill:hover { color: var(--text-primary); background: rgba(255, 255, 255, 0.045); }
+.tab-pill.active { background: var(--accent); color: #04130d; }
+.vp-toggle {
+  padding: var(--sp-1) var(--sp-3);
+  border-radius: var(--r-xs);
+  border: 1px solid var(--border);
+  background: transparent;
+  color: var(--text-secondary);
+  font-weight: 700;
+  font-size: var(--fs-xs);
+  cursor: pointer;
+}
+.vp-toggle[aria-pressed="true"], .vp-toggle.active {
+  background: var(--accent-glow);
+  color: var(--accent-300);
+  border-color: var(--border-focus);
+}
+
+/* ---- Responsive (PRESERVED breakpoints) ------------------------------ */
+@media (max-width: 1024px) {
+  .app-container { grid-template-columns: 210px 1fr !important; }
+}
 @media (max-width: 768px) {
-  body {
-    overflow: auto;
-  }
-  .app-container {
-    grid-template-columns: 1fr !important;
-    height: auto !important;
-  }
+  body { overflow: auto; }
+  .app-container { grid-template-columns: 1fr !important; height: auto !important; }
   .glass-sidebar {
     border-right: none;
     border-bottom: 1px solid var(--border);
     height: auto !important;
-    backdrop-filter: none; /* Perf on mobile */
-  }
-  main {
-    overflow: visible !important;
-  }
-  .metrics-grid {
-    grid-template-columns: repeat(2, 1fr) !important;
+    backdrop-filter: none;
   }
+  main { overflow: visible !important; }
+  .metrics-grid { grid-template-columns: repeat(2, 1fr) !important; }
 }
-
 @media (max-width: 480px) {
-  .metrics-grid {
-    grid-template-columns: 1fr !important;
-  }
+  .metrics-grid { grid-template-columns: 1fr !important; }
 }
 
-/* High-end Animations */
+/* ---- Animations (PRESERVED) ------------------------------------------ */
 @keyframes shimmer {
   0% { transform: translateX(-100%); }
   100% { transform: translateX(100%); }
 }
-
-.shimmer-active {
-  position: relative;
-  overflow: hidden;
-}
-
+.shimmer-active { position: relative; overflow: hidden; }
 .shimmer-active::after {
   content: "";
   position: absolute;
-  top: 0;
-  left: 0;
-  width: 100%;
-  height: 100%;
-  background: linear-gradient(
-    90deg,
-    transparent,
-    rgba(255, 255, 255, 0.05),
-    transparent
-  );
+  top: 0; left: 0;
+  width: 100%; height: 100%;
+  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.06), transparent);
   animation: shimmer 2s infinite;
 }
 
-/* Markdown Styling */
+/* ---- Markdown (PRESERVED) -------------------------------------------- */
 .report-markdown h1, .report-markdown h2, .report-markdown h3 {
   color: var(--text-primary);
   border-bottom: 1px solid var(--border);
-  padding-bottom: 8px;
-  margin-top: 24px;
+  padding-bottom: var(--sp-2);
+  margin-top: var(--sp-6);
+  letter-spacing: var(--tracking-tight);
 }
+.report-markdown strong { color: var(--accent); }
 
-.report-markdown strong {
-  color: var(--accent);
+/* ---- Foundation-level reduced-motion (anti-gaming guard B:-1) -------- */
+@media (prefers-reduced-motion: reduce) {
+  .shimmer-active::after { animation: none; }
+  .case-item { transition: none; }
+  /* 41.2 — every new motion utility honored (anti-gaming guard B:-1). */
+  .rise-in { animation: none; }
+  .surface-card { transition: none; }
+  .cb-case-card, .cb-chip, .cb-search { transition: none; }
+  .cb-case-card:hover { transform: none; }
+  .tab-pill, .vp-toggle { transition: none; }
 }

 succeeded in 13997ms:
2026-05-29 11:52:10.332 xcodebuild[3162:81707629]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:10.705 xcodebuild[3162:81707627] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-CwXV43wV' (errno=Operation not permitted)
2026-05-29 11:52:11.592 xcodebuild[3178:81707684]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:11.826 xcodebuild[3178:81707679] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
 frontend/src/App.tsx                          |  19 +-
 frontend/src/components/AdvancedModePromo.tsx |   5 +-
 frontend/src/components/CaseBrowser.tsx       |  48 ++--
 frontend/src/components/OnboardingTour.tsx    |   6 +-
 frontend/src/components/ProjectManager.tsx    | 257 +++++++++++++----
 frontend/src/index.css                        | 397 ++++++++++++++++++++------
 6 files changed, 562 insertions(+), 170 deletions(-)

--- cached stat ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Q0vt9ehJ' (errno=Operation not permitted)
2026-05-29 11:52:13.790 xcodebuild[3187:81707808]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:14.109 xcodebuild[3187:81707744] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-pMjt3yZf' (errno=Operation not permitted)
2026-05-29 11:52:14.944 xcodebuild[3309:81707914]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:15.200 xcodebuild[3309:81707913] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.

--- name-only ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-eOA391Ou' (errno=Operation not permitted)
2026-05-29 11:52:17.055 xcodebuild[3317:81708002]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:17.330 xcodebuild[3317:81708001] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Pu9xEKvp' (errno=Operation not permitted)
2026-05-29 11:52:18.296 xcodebuild[3438:81708187]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:18.644 xcodebuild[3438:81708180] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
frontend/src/App.tsx
frontend/src/components/AdvancedModePromo.tsx
frontend/src/components/CaseBrowser.tsx
frontend/src/components/OnboardingTour.tsx
frontend/src/components/ProjectManager.tsx
frontend/src/index.css

--- cached name-only ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-CoYy7nP1' (errno=Operation not permitted)
2026-05-29 11:52:20.860 xcodebuild[3790:81708697]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:21.117 xcodebuild[3790:81708696] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-78C7Ba6B' (errno=Operation not permitted)
2026-05-29 11:52:21.921 xcodebuild[3792:81708712]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:52:22.181 xcodebuild[3792:81708711] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.

exec
/bin/zsh -lc "sed -n '1,260p' frontend/src/components/ProjectManager.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 41.2 — ProjectManager restyle. The pre-41 markup used
// Tailwind utility classes (bg-slate-*/text-indigo-*/w-64/space-y-*), but
// this project has NO Tailwind pipeline, so every one of those classes was
// DEAD — the left rail rendered as unstyled browser defaults (the "empty
// broken rail" the demo audit flagged). This rewrite swaps the dead Tailwind
// for the real 41.1 token system + the existing .glass-sidebar / .case-item /
// .glass-panel shared classes. Behavior (fetch, create, select, modal) is
// unchanged.
import { useState, useEffect, type CSSProperties } from 'react';
import { Folder, FolderPlus, Clock } from 'lucide-react';

interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

interface ProjectManagerProps {
  onSelectProject: (projectId: number) => void;
  selectedProjectId: number | null;
}

export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectManagerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/projects')
      .then(res => res.json())
      .then(data => setProjects(data))
      .catch(err => console.error("Failed to fetch projects", err));
  }, []);

  const handleCreateProject = async () => {
    if (!newProject.name) return;

    try {
      const resp = await fetch('http://localhost:8000/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject)
      });
      if (resp.ok) {
        const created = await resp.json();
        setProjects([...projects, created]);
        setIsModalOpen(false);
        setNewProject({ name: '', description: '' });
      }
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  return (
    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
      <div style={headerStyle}>
        <span className="eyebrow">Projects</span>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          aria-label="Create new project"
          style={addButtonStyle}
        >
          <FolderPlus size={16} />
        </button>
      </div>

      <div style={listStyle}>
        {projects.map(project => {
          const active = selectedProjectId === project.id;
          return (
            <button
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className={`case-item${active ? ' active' : ''}`}
              style={{ ...projectButtonStyle, ...(active ? projectButtonActiveStyle : null) }}
            >
              <Folder size={15} style={{ color: active ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0 }} />
              <span style={{ flex: 1, overflow: 'hidden' }}>
                <span style={{ ...projectNameStyle, color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {project.name}
                </span>
                <span style={projectDateStyle}>
                  <Clock size={11} />
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </span>
            </button>
          );
        })}
        {projects.length === 0 && (
          <p style={emptyHintStyle}>No projects yet. Create one to organize your analyses.</p>
        )}
      </div>

      {isModalOpen && (
        <div style={modalOverlayStyle}>
          <div className="glass-panel" style={modalCardStyle}>
            <h3 style={modalTitleStyle}>Create new project</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
              <div>
                <label style={fieldLabelStyle}>Project name</label>
                <input
                  value={newProject.name}
                  onChange={e => setNewProject({ ...newProject, name: e.target.value })}
                  style={fieldInputStyle}
                  placeholder="e.g. Truss bridge design"
                />
              </div>
              <div>
                <label style={fieldLabelStyle}>Description</label>
                <textarea
                  value={newProject.description}
                  onChange={e => setNewProject({ ...newProject, description: e.target.value })}
                  style={{ ...fieldInputStyle, height: 96, resize: 'vertical' }}
                  placeholder="Analyze the structural stability of…"
                />
              </div>
              <div style={{ display: 'flex', gap: 'var(--sp-3)', paddingTop: 'var(--sp-1)' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={cancelButtonStyle}>
                  Cancel
                </button>
                <button type="button" onClick={handleCreateProject} style={createButtonStyle}>
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const rootStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflow: 'hidden',
};
const headerStyle: CSSProperties = {
  padding: 'var(--sp-4)',
  borderBottom: '1px solid var(--border)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};
const addButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 'var(--sp-1)',
  borderRadius: 'var(--r-sm)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
};
const listStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 'var(--sp-2)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-1)',
};
const projectButtonStyle: CSSProperties = {
  width: '100%',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'center',
  gap: 'var(--sp-3)',
  padding: 'var(--sp-3)',
  borderRadius: 'var(--r-md)',
  border: '1px solid transparent',
  background: 'transparent',
  cursor: 'pointer',
  fontFamily: 'inherit',
};
const projectButtonActiveStyle: CSSProperties = {
  background: 'var(--accent-glow)',
  border: '1px solid var(--border-focus)',
};
const projectNameStyle: CSSProperties = {
  display: 'block',
  fontSize: 'var(--fs-sm)',
  fontWeight: 600,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
};
const projectDateStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  marginTop: 2,
  fontSize: 'var(--fs-xs)',
  color: 'var(--text-muted)',
};
const emptyHintStyle: CSSProperties = {
  margin: 0,
  padding: 'var(--sp-3)',
  fontSize: 'var(--fs-xs)',
  color: 'var(--text-muted)',
  lineHeight: 1.5,
};
const modalOverlayStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0, 0, 0, 0.6)',
  backdropFilter: 'blur(4px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 50,
  padding: 'var(--sp-4)',
};
const modalCardStyle: CSSProperties = {
  width: '100%',
  maxWidth: 420,
  padding: 'var(--sp-6)',
  boxShadow: 'var(--elev-3)',
};
const modalTitleStyle: CSSProperties = {
  margin: '0 0 var(--sp-4)',
  fontSize: 'var(--fs-lg)',
  fontWeight: 700,
  letterSpacing: 'var(--tracking-tight)',
  color: 'var(--text-primary)',
};
const fieldLabelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 'var(--sp-1)',
  fontSize: 'var(--fs-sm)',
  fontWeight: 500,
  color: 'var(--text-secondary)',
};
const fieldInputStyle: CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'var(--c-900)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--r-sm)',
  padding: 'var(--sp-2) var(--sp-3)',
  color: 'var(--text-primary)',
  fontFamily: 'inherit',
  fontSize: 'var(--fs-sm)',
};
const cancelButtonStyle: CSSProperties = {
  flex: 1,
  padding: 'var(--sp-2)',
  background: 'transparent',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
  borderRadius: 'var(--r-sm)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontWeight: 600,

exec
/bin/zsh -lc "sed -n '1,260p' frontend/src/components/CaseBrowser.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 37 A — CaseBrowser canonical case-picker surface.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// First canonical-surface industrial-UI parity lift since the
// rubric v2.0 baseline (Phase 33 A). The 5 canonical surfaces
// described at `.planning/test_subagents/references/` set
// Hyperworks / Abaqus / ANSYS conventions; before Phase 37 A the
// case-picker pillar was rated 3.2/10 (flat list, no grouping,
// no filter, no preview). CaseBrowser delivers Hyperworks-style
// case browser conventions:
//
//   * Tree-style grouping by `solverKind` (matches the verdict YAML
//     enum: linear_static / modal / buckling / dynamic /
//     heat_transfer_steady_state / contact_pair_static). When a
//     case lacks a solverKind in the registry, it groups under
//     "uncategorized".
//   * Filter chip row — toggle individual solver-kind chips +
//     "Tier 2 validated only" filter chip + text search input
//     (matches against displayLabel + caseId, case-insensitive).
//   * Preview pane on the right showing the focused case's
//     displayLabel + claimTier + runnerAvailable badge + a short
//     orientation derived from the same caseId-pattern lookup
//     CaseOpenAdvisorCard uses (so the browse + open surfaces
//     give the reviewer consistent copy).
//
// Anti-gaming guards:
//   Q:-1 (NEW Phase 37) — preserves the CandidateCaseRecord data
//     contract; consumes the existing FALLBACK_CANDIDATE_CASES OR
//     the live-route payload unchanged. New test pin asserts the
//     12-cohort case list is fully rendered when grouping is
//     enabled.
//   I:-1 (Phase 34 carry) — does NOT modify Phase 19 D Sidebar.
//     The Sidebar still mounts as before; CaseBrowser is a NEW
//     surface that coexists.

import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import { InContextHint } from './InContextHint'

export interface CaseBrowserProps {
  /** The cohort of candidate cases to browse. Pass the same array
   * the existing case-picker consumes. */
  readonly cases: readonly CandidateCaseRecord[]
  /** Optional currently-focused case id. When provided, the preview
   * pane renders that case's details. */
  readonly focusedCaseId?: string | null
  /** Selection callback. Fires when the user clicks a case row in
   * a group. The host wires this to the same handler the existing
   * Sidebar / palette already calls. */
  readonly onSelectCase: (caseId: string) => void
}

/** Phase 37 A — Hyperworks-style canonical case-browser surface.
 *
 * Renders a 2-pane layout: left = grouped + filterable case list,
 * right = focused-case preview. */
export function CaseBrowser({
  cases,
  focusedCaseId,
  onSelectCase,
}: CaseBrowserProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeKindFilters, setActiveKindFilters] = useState<ReadonlySet<string>>(
    new Set(),
  )
  const [tier2Only, setTier2Only] = useState(false)
  const [hoveredCaseId, setHoveredCaseId] = useState<string | null>(null)

  const previewCaseId = hoveredCaseId ?? focusedCaseId ?? null
  const previewCase = useMemo(
    () => cases.find((c) => c.caseId === previewCaseId) ?? null,
    [cases, previewCaseId],
  )

  const grouped = useMemo(
    () => groupAndFilterCases(cases, { searchQuery, activeKindFilters, tier2Only }),
    [cases, searchQuery, activeKindFilters, tier2Only],
  )

  // Stable solver-kind enum for the chip row.
  const allKinds = useMemo(() => {
    const set = new Set<string>()
    for (const c of cases) if (c.solverKind !== undefined) set.add(c.solverKind)
    return Array.from(set).sort()
  }, [cases])

  const toggleKindFilter = (kind: string) => {
    setActiveKindFilters((prev) => {
      const next = new Set(prev)
      if (next.has(kind)) next.delete(kind)
      else next.add(kind)
      return next
    })
  }

  const totalShown = grouped.reduce((acc, g) => acc + g.cases.length, 0)

  return (
    <section
      data-testid="case-browser"
      role="region"
      aria-label="Case browser — grouped by solver kind"
      style={rootStyle}
    >
      <InContextHint
        hintId="case-browser"
        label="Case browser"
        text="Pick a case to open. Filter by solver kind or search by name; the preview pane summarises what each case validates before you commit."
      />
      <header style={headerStyle}>
        <strong style={titleStyle}>Case browser</strong>
        <span
          data-testid="case-browser-count"
          style={countStyle}
        >{`${totalShown} of ${cases.length}`}</span>
      </header>

      <div style={filterRowStyle} data-testid="case-browser-filter-row">
        <input
          type="search"
          placeholder="Filter by name or id"
          aria-label="Filter cases by name or id"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="case-browser-search-input"
          className="cb-search"
          style={searchInputStyle}
        />
        <button
          type="button"
          data-testid="case-browser-tier2-chip"
          aria-pressed={tier2Only}
          onClick={() => setTier2Only((v) => !v)}
          className="cb-chip"
          style={tier2Only ? chipActiveStyle : chipIdleStyle}
        >
          Tier 2 validated
        </button>
        {allKinds.map((kind) => (
          <button
            type="button"
            key={kind}
            data-testid={`case-browser-kind-chip-${kind}`}
            aria-pressed={activeKindFilters.has(kind)}
            onClick={() => toggleKindFilter(kind)}
            style={
              activeKindFilters.has(kind) ? chipActiveStyle : chipIdleStyle
            }
          >
            {prettyKind(kind)}
          </button>
        ))}
      </div>

      <div style={paneRowStyle}>
        <ol style={groupListStyle} data-testid="case-browser-group-list">
          {grouped.map((group) => (
            <li key={group.kind} style={groupItemStyle}>
              <div style={groupHeaderStyle} data-testid={`case-browser-group-${group.kind}`}>
                <span style={groupHeaderLabelStyle}>{prettyKind(group.kind)}</span>
                <span style={groupHeaderCountStyle}>{group.cases.length}</span>
              </div>
              <ul style={caseListStyle}>
                {group.cases.map((c) => (
                  <li key={c.caseId}>
                    <button
                      type="button"
                      onMouseEnter={() => setHoveredCaseId(c.caseId)}
                      onMouseLeave={() => setHoveredCaseId(null)}
                      onClick={() => onSelectCase(c.caseId)}
                      data-testid={`case-browser-row-${c.caseId}`}
                      data-active={focusedCaseId === c.caseId ? 'true' : undefined}
                      className="cb-case-card"
                      style={
                        focusedCaseId === c.caseId
                          ? caseRowActiveStyle
                          : caseRowIdleStyle
                      }
                    >
                      {c.displayLabel ?? c.caseId}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {grouped.length === 0 && (
            <li data-testid="case-browser-empty" style={emptyStateStyle}>
              No cases match the current filters.
            </li>
          )}
        </ol>

        <aside style={previewPaneStyle} data-testid="case-browser-preview-pane">
          {previewCase ? (
            <>
              <div style={previewHeaderStyle}>
                <strong style={previewTitleStyle}>
                  {previewCase.displayLabel ?? previewCase.caseId}
                </strong>
                {previewCase.runnerAvailable === false && (
                  <span
                    data-testid="case-browser-runner-badge"
                    style={runnerBadgeStyle}
                  >
                    demo · no live runner
                  </span>
                )}
              </div>
              <p style={previewMetaStyle}>
                <span style={previewMetaLabelStyle}>Tier:</span> {previewCase.claimTier}
              </p>
              {previewCase.solverKind !== undefined && (
                <p style={previewMetaStyle}>
                  <span style={previewMetaLabelStyle}>Solver kind:</span>{' '}
                  {prettyKind(previewCase.solverKind)}
                </p>
              )}
              <p style={previewBlurbStyle}>
                {previewBlurbFor(previewCase.caseId)}
              </p>
            </>
          ) : (
            <p style={previewEmptyStyle}>Hover or focus a case to preview it here.</p>
          )}
        </aside>
      </div>
    </section>
  )
}

/** Phase 37 A — pure helper: filter + group cases per current
 * UI controls. Exposed for testing. */
export function groupAndFilterCases(
  cases: readonly CandidateCaseRecord[],
  opts: {
    readonly searchQuery: string
    readonly activeKindFilters: ReadonlySet<string>
    readonly tier2Only: boolean
  },
): ReadonlyArray<{ readonly kind: string; readonly cases: readonly CandidateCaseRecord[] }> {
  const q = opts.searchQuery.trim().toLowerCase()
  const filtered = cases.filter((c) => {
    if (opts.tier2Only && !c.claimTier.toLowerCase().includes('tier 2')) {
      return false
    }
    if (opts.activeKindFilters.size > 0) {
      const kind = c.solverKind ?? 'uncategorized'
      if (!opts.activeKindFilters.has(kind)) return false
    }
    if (q.length > 0) {
      const hay = `${c.displayLabel ?? ''} ${c.caseId}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })


exec
/bin/zsh -lc "sed -n '1180,1460p' frontend/src/App.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
      // No-op when no case is selected; the palette closes regardless.
      console.warn('Run Solver command invoked with no active case selected.')
      return
    }
    // Re-uses the existing solver flow; safer than duplicating fetch logic.
    void fetch(`${API_BASE}/solver/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: activeCaseId,
        analysis_type: analysisType,
        // Phase 18 E (round 3) — palette-fired re-runs carry the
        // material pick too; symmetric with the main solver flow.
        // Same Phase 19 priority-0.5 caveat: field declared on the
        // backend RunRequest model but not yet plumbed into the
        // solver pipeline. Wire-level contract only.
        material_id: selectedMaterial.id,
      }),
    })
  }
  const commands: Command[] = buildPaletteCommands({
    setActiveTab,
    runSolverFromPalette: _runSolverFromPalette,
    pickMaterialByIndex: (i) => setSelectedMaterial(FALLBACK_MATERIALS[i]),
    openMaterialPickerPanel: () => {
      if (typeof document === 'undefined') return;
      const target = document.getElementById('material-picker-panel');
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },
    closePalette: () => setPaletteOpen(false),
    activeCaseId,
    materials: FALLBACK_MATERIALS,
  });
  useKeyboardShortcuts([
    {
      hotkey: 'mod+k',
      handler: (e) => {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      },
      fireInTextInput: true,
    },
  ])

  return (
    <div className="app-container" style={{ display: 'grid', gridTemplateColumns: '210px 300px 1fr', height: '100vh' }}>
      {/* FM-04a Phase 29 C — onboarding tour + advanced-mode auto-
          promote mounted at App-root so reviewers landing on the
          Narrative tab (or any future tab) still see onboarding.
          Phase 28 D's prior mount was inside ResultMeshPlaybackPanel
          and the Visual-tab-only coupling was flagged by the UX
          audit. The promo's visibility is fully self-gated by its
          storage predicate; uiMode lives in App-root via
          appUiModeStorage / appUiMode below. */}
      <OnboardingTour onDismissed={markTourDismissedInSession} />
      <AdvancedModePromo
        uiMode={appUiMode}
        tourDismissedInSession={appTourDismissedInSession}
        onSwitchToAdvanced={() => handleAppUiModeChange('advanced')}
      />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={commands}
      />

      {/* Project Sidebar */}
      <ProjectManager
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => setSelectedProjectId(id)}
      />

      {/* Case Sidebar — extracted to Sidebar.tsx in Phase 19 D */}
      <Sidebar
        availableCases={availableCases}
        candidateCases={FALLBACK_CANDIDATE_CASES.map<SidebarCandidateCase>((c) => ({
          caseId: c.caseId,
          displayLabel: c.displayLabel ?? c.caseId,
        }))}
        selectedCandidateCaseId={selectedCandidateCaseId}
        onSelectCandidateCase={(id) => {
          setSelectedCandidateCaseId(id)
          // Phase 20 E (round 1 → round 2 fix) — close the state-
          // divergence defect the UX agent flagged: selecting a
          // candidate previously left `activeCaseId` null so the
          // Topbar's Run Solver button stayed hidden. Unify the
          // selection now so the Phase 20 A material_id route flow
          // (which keys on `activeCaseId`) is reachable end-to-end
          // from the Sidebar candidate roster click.
          setActiveCaseId(id)
          try {
            window.localStorage.setItem('fm04a.candidateCaseId', id)
          } catch {
            /* no-op when storage is unavailable */
          }
        }}
        activeCaseId={activeCaseId}
        onSelectCase={(c) => selectCase(c)}
        activeExperiment={activeExperiment}
        onFileUpload={handleFileUpload}
        onOpenPalette={() => setPaletteOpen(true)}
      />

      {/* Main Content Area */}
      <div style={{ display: 'grid', gridTemplateColumns: showChat ? '1fr 340px' : '1fr', height: '100vh', overflow: 'hidden' }}>
        <main style={{ overflowY: 'auto', background: 'var(--bg-base)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <Topbar
              breadcrumbLabel={activeCaseId || (file ? file.name : "Session")}
              badge={report && <ComplianceBadge status={report.metrics.status} standard="GB50017" />}
              showRunControls={Boolean(activeCaseId)}
              analysisType={analysisType}
              onChangeAnalysisType={setAnalysisType}
              solving={solving}
              onRunSolver={runSolver}
              onStopSolver={stopSolver}
              showChat={showChat}
              onToggleChat={() => setShowChat(!showChat)}
              materialReference={lastSolverMaterialReference}
              materialOptions={buildTopbarMaterialOptions(FALLBACK_MATERIALS)}
              selectedMaterialId={selectedMaterial.id}
              onChangeMaterialId={(id) => {
                const found = FALLBACK_MATERIALS.find((m) => m.id === id);
                if (found) setSelectedMaterial(found);
              }}
            />

            {/* FM-04a Phase 41.2 — flex column so the trust/governance panel is
                demoted via CSS `order` BELOW the case + 3D viewport (demo-first:
                lead with the result, not the compliance dashboard). DOM order
                unchanged; ErrorCard keeps order 0 (red band still first). */}
            <div style={{ padding: '40px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* FM-04a Phase 36 B — ErrorCard mounts ABOVE
                OperatorStatusPanel so a failed user sees the red
                error band before the trust prose (Phase 35 R3
                friction point b). */}
            {uploadError && (
                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px', order: 0 }}>
                    <ErrorCard {...uploadError} />
                </div>
            )}

            {/* order: 5 → demoted below the golden-path content (tabs + viewport,
                order 0). The "Evidence & trust center" is reachable by scroll,
                not the landing hero. */}
            <div style={{ order: 5, marginTop: '32px' }}>
            <OperatorStatusPanel
              strip={trustStrip}
              sections={trustSections}
              goldenSamples={goldenSampleQueue}
            />
            </div>

            {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
            {!activeCaseId && (
                <div style={{ marginBottom: '24px' }}>
                    <CaseBrowser cases={FALLBACK_CANDIDATE_CASES} focusedCaseId={selectedCandidateCaseId} onSelectCase={(caseId) => setSelectedCandidateCaseId(caseId)} />
                </div>
            )}

            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
            </div>

            {activeCaseId && (() => {
                // FM-04a Phase 37 B — pair BCSetupAdvisorCard with CaseOpenAdvisorCard (3rd advisor surface; closes Dim 4 80-anchor 3-stage sub-bullet).
                const caseOpenRecord = findCandidateCase(FALLBACK_CANDIDATE_CASES, activeCaseId);
                return caseOpenRecord ? (
                    <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '12px' }}>
                        <CaseOpenAdvisorCard caseRecord={caseOpenRecord} />
                        {shouldShowBCSetupAdvisor(caseOpenRecord) && <BCSetupAdvisorCard caseRecord={caseOpenRecord} />}
                        <BCSetupPillList caseRecord={caseOpenRecord} />
                    </div>
                ) : null;
            })()}

            {activeTab === 'visual' && (
                <VisualTabPanel
                    apiBase={API_BASE}
                    selectedCandidateCaseId={selectedCandidateCaseId}
                    onSelectCandidateCaseId={setSelectedCandidateCaseId}
                    comparisonCaseA={comparisonCaseA}
                    comparisonCaseB={comparisonCaseB}
                    onSelectComparisonA={setComparisonCaseA}
                    onSelectComparisonB={setComparisonCaseB}
                    snapshotLabelA={snapshotLabelA}
                    snapshotLabelB={snapshotLabelB}
                    onSelectSnapshotLabelA={setSnapshotLabelA}
                    onSelectSnapshotLabelB={setSnapshotLabelB}
                    selectedMaterial={selectedMaterial}
                    onMaterialChange={setSelectedMaterial}
                    latestSignoff={latestSignoff}
                    onLatestSignoff={setLatestSignoff}
                />
            )}

            <div style={{ padding: '0', flex: 1 }}>
                {activeTab === 'explore' ? (
                    <ExplorationTabPanel
                        activeCaseId={activeCaseId!}
                        loading={loading}
                        activeExperiment={activeExperiment}
                        comparedIndices={comparedIndices}
                        onCompareIndex={(i) => {
                            if (comparedIndices) {
                                if (comparedIndices[0] === i) {
                                    setComparedIndices(null);
                                } else {
                                    setComparedIndices([comparedIndices[0], i]);
                                }
                            } else {
                                setComparedIndices([i, -1]);
                            }
                        }}
                        onRunStudy={handleRunStudy}
                    />
                ) : (
                    <>
                    {loading ? (
                        <div className="shimmer-active" style={{ height: '400px', width: '100%', borderRadius: '12px', background: 'var(--bg-surface)' }}></div>
                    ) : report ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
                                {activeTab === 'visual' ? (
                                    <div
                                      style={{
                                        display: 'grid',
                                        gridTemplateRows: activeCaseId ? '400px minmax(300px, 1fr)' : '1fr',
                                        gap: activeCaseId ? '12px' : 0,
                                        padding: activeCaseId ? '12px' : 0,
                                        minHeight: activeCaseId ? '820px' : '600px',
                                      }}
                                    >
                                        {activeCaseId && (
                                          <ResultMeshPlaybackPanel
                                            caseId={activeCaseId}
                                            apiBase={API_BASE}
                                            enabled={activeTab === 'visual'}
                                            uiMode={appUiMode}
                                            onUiModeChange={handleAppUiModeChange}
                                          />
                                        )}
                                        <div
                                          style={{
                                            position: 'relative',
                                            width: '100%',
                                            minHeight: '300px',
                                            overflow: 'hidden',
                                            border: activeCaseId ? '1px solid var(--border)' : 'none',
                                            borderRadius: activeCaseId ? '8px' : 0,
                                          }}
                                        >
                                        <iframe 
                                            src={comparedIndices && comparedIndices[1] !== -1 
                                                ? `${API_BASE}/visualize/delta?file1=${activeExperiment?.runs[comparedIndices[0]].inp_path.replace('.inp','.frd')}&file2=${activeExperiment?.runs[comparedIndices[1]].inp_path.replace('.inp','.frd')}` 
                                                : `${API_BASE}/visualize/plot?case_id=${activeCaseId || 'last'}&output_format=html&increment_index=${selectedModeIndex}`} 
                                            style={{ width: '100%', height: '100%', border: 'none' }} 
                                            title="FEA Visualization" 
                                        />
                                        
                                        {report?.increments && report.increments.length > 0 && (
                                            <div style={{ position: 'absolute', top: '24px', right: '24px', width: '320px', zIndex: 10 }}>
                                                <ModeSelector 
                                                    increments={report.increments}
                                                    selectedModeIndex={selectedModeIndex}
                                                    activeAnalysisType={analysisType}
                                                    onSelectMode={(idx) => setSelectedModeIndex(idx)}
                                                />
                                            </div>
                                        )}
                                        </div>
                                    </div>
                                ) : (
                                    <NarrativeTabPanel
                                        report={report}
                                        onDownloadPDF={downloadPDFReport}
                                    />
                                )}
                            </div>
                        </div>

exec
/bin/zsh -lc "sed -n '1460,1545p' frontend/src/App.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
                        </div>
                    ) : (
                        <div style={{ height: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '16px' }}>
                            <LayoutDashboard size={48} strokeWidth={1} />
                            <div>Select a structural case from the gallery to begin analysis</div>
                        </div>
                    )}
                    </>
                )}
            </div>
            </div>

            {showConsole && (
            <div className="glass-panel" style={{ margin: '0 40px 40px 40px', height: '160px', display: 'flex', flexDirection: 'column', background: '#000' }}>
                <div style={{ flex: 1, padding: '12px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#ccc' }}>
                {logs.map((log, i) => <div key={i}>{log}</div>)}
                <div ref={terminalEndRef} />
                </div>
            </div>
            )}
        </main>

        <RightRail
            showChat={showChat}
            caseId={activeCaseId}
            onExecuteAction={handleExecuteCopilotAction}
            reviewCards={caeReviewCards}
            claimTier={claimTier}
            allowedClaim={allowedClaim}
        />
      </div>
    </div>
  );
}

export default App;

exec
/bin/zsh -lc 'rg -n "function TabButton|const TabButton|tab-button-active|tab-pill" frontend/src -S' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "rg -n \"ProjectManager\\(|project-rail|api/v1/projects|selectedProjectId\" -S frontend/src backend | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 251ms:
frontend/src/index.css:202:.tab-button-active {
frontend/src/index.css:290:/* Viewport-hero + tab-pill + in-viewport toggle (active-case golden path). */
frontend/src/index.css:300:.tab-pill-bar {
frontend/src/index.css:309:.tab-pill {
frontend/src/index.css:324:.tab-pill:hover { color: var(--text-primary); background: rgba(255, 255, 255, 0.045); }
frontend/src/index.css:325:.tab-pill.active { background: var(--accent); color: #04130d; }
frontend/src/index.css:396:  .tab-pill, .vp-toggle { transition: none; }
frontend/src/App.tsx:1339:            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
frontend/src/components/TabButton.tsx:9:export function TabButton({

 succeeded in 112ms:
frontend/src/App.tsx:198:  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
frontend/src/App.tsx:222:    const url = selectedProjectId 
frontend/src/App.tsx:223:      ? `${API_BASE}/cases?project_id=${selectedProjectId}` 
frontend/src/App.tsx:230:  }, [selectedProjectId]);
frontend/src/App.tsx:1248:        selectedProjectId={selectedProjectId}
frontend/src/components/ProjectManager.tsx:21:  selectedProjectId: number | null;
frontend/src/components/ProjectManager.tsx:24:export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectManagerProps) {
frontend/src/components/ProjectManager.tsx:30:    fetch('http://localhost:8000/api/v1/projects')
frontend/src/components/ProjectManager.tsx:40:      const resp = await fetch('http://localhost:8000/api/v1/projects', {
frontend/src/components/ProjectManager.tsx:57:    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
frontend/src/components/ProjectManager.tsx:72:          const active = selectedProjectId === project.id;
backend/app/api/__init__.py:4:Replacement endpoint POST /api/v1/projects/{id}/results lands in W4+ per RFC §6.3.

exec
/bin/zsh -lc "sed -n '1,220p' frontend/src/components/TabButton.tsx && printf '\\n--- related App selectedProject effect ---\\n' && sed -n '180,245p' frontend/src/App.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 22 C — TabButton extracted out of App.tsx as part of
// the LOC-discipline trajectory.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { ReactNode } from 'react';

export function TabButton({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 16px',
        border: 'none',
        borderRadius: '8px',
        background: active ? 'var(--accent)' : 'transparent',
        color: active ? '#000' : '#fff',
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}
    >
      {icon} {label}
    </button>
  );
}

--- related App selectedProject effect ---
      return FALLBACK_CANDIDATE_CASES[1]?.caseId ?? null;
    }
  });
  // FM-04a Phase 6 E — lifted snapshot label selection so DriftNarrativePanel
  // can read the same labels the CohortSnapshotPanel picks.
  const [snapshotLabelA, setSnapshotLabelA] = useState<string | null>(null);
  const [snapshotLabelB, setSnapshotLabelB] = useState<string | null>(null);
  const [latestSignoff, setLatestSignoff] = useState<SignoffRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReportData | null>(null);
  const [activeTab, setActiveTab] = useState<'visual' | 'report' | 'explore'>('visual');
  // FM-04a Phase 18 D/E — Cmd-K palette + selected material (round 2).
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialRecord>(
    FALLBACK_MATERIALS[0],
  );
  const [availableCases, setAvailableCases] = useState<CaseMetadata[]>([]);
  const [caseDetailsById, setCaseDetailsById] = useState<Record<string, CaseReferenceDetails>>({});
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [analysisType, setAnalysisType] = useState<'static' | 'modal' | 'buckling'>('static');
  const [selectedModeIndex, setSelectedModeIndex] = useState(0);
  
  // Solver & Explorer State
  const [solving, setSolving] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showConsole, setShowConsole] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentJobStatus, setCurrentJobStatus] = useState<JobStatus>('idle');
  const [currentJobAnalysis, setCurrentJobAnalysis] = useState<'static' | 'modal' | 'buckling'>('static');
  // FM-04a Phase 21 D — surface the material reference returned by
  // /solver/run (Phase 20 A wired the route end-to-end but no UI
  // consumer existed; reviewers couldn't see which material was
  // actually used after pressing Run Solver). Cleared on each run start.
  const [lastSolverMaterialReference, setLastSolverMaterialReference] =
    useState<string | null>(null);
  const [activeExperiment, setActiveExperiment] = useState<ExperimentStatus | null>(null);
  const [comparedIndices, setComparedIndices] = useState<[number, number] | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Fetch available cases when project changes
  useEffect(() => {
    const url = selectedProjectId 
      ? `${API_BASE}/cases?project_id=${selectedProjectId}` 
      : `${API_BASE}/cases`;
      
    fetch(url)
      .then(res => res.json())
      .then(data => setAvailableCases(data))
      .catch(err => console.error("Failed to fetch cases", err));
  }, [selectedProjectId]);

  useEffect(() => {
    let cancelled = false;

    if (availableCases.length === 0) {
      setCaseDetailsById({});
      return;
    }

    Promise.all(
      availableCases.map(async (c) => {
        try {
          const res = await fetch(`${API_BASE}/cases/${encodeURIComponent(c.id)}`);
          if (!res.ok) return [c.id, {}] as const;
          const details = await res.json() as CaseReferenceDetails;

exec
/bin/zsh -lc "git show HEAD:frontend/src/components/ProjectManager.tsx | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show HEAD:frontend/src/components/CaseBrowser.tsx | sed -n '1,240p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show HEAD:frontend/src/App.tsx | sed -n '1290,1455p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 4540ms:
2026-05-29 11:53:31.382 xcodebuild[6530:81713819]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:32.002 xcodebuild[6530:81713811] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-eLk1hP0J' (errno=Operation not permitted)
2026-05-29 11:53:33.216 xcodebuild[6666:81714030]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:33.482 xcodebuild[6666:81714025] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
import { useState, useEffect } from 'react';
import { Folder, FolderPlus, Clock, Layout } from 'lucide-react';

interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

interface ProjectManagerProps {
  onSelectProject: (projectId: number) => void;
  selectedProjectId: number | null;
}

export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectManagerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/projects')
      .then(res => res.json())
      .then(data => setProjects(data))
      .catch(err => console.error("Failed to fetch projects", err));
  }, []);

  const handleCreateProject = async () => {
    if (!newProject.name) return;
    
    try {
      const resp = await fetch('http://localhost:8000/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject)
      });
      if (resp.ok) {
        const created = await resp.json();
        setProjects([...projects, created]);
        setIsModalOpen(false);
        setNewProject({ name: '', description: '' });
      }
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border-r border-slate-800 w-64">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Layout className="w-5 h-5 text-indigo-400" />
          <h2 className="font-semibold text-slate-200">Projects</h2>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="p-1 hover:bg-slate-800 rounded-md transition-colors text-slate-400 hover:text-indigo-400"
        >
          <FolderPlus className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.map(project => (
          <button
            key={project.id}
            onClick={() => onSelectProject(project.id)}
            className={`w-full text-left p-3 rounded-lg flex items-center group transition-all ${
              selectedProjectId === project.id 
                ? 'bg-indigo-600/20 border border-indigo-500/50' 
                : 'hover:bg-slate-800 border border-transparent'
            }`}
          >
            <Folder className={`w-4 h-4 mr-3 ${selectedProjectId === project.id ? 'text-indigo-400' : 'text-slate-500'}`} />
            <div className="flex-1 overflow-hidden">
              <div className={`text-sm font-medium truncate ${selectedProjectId === project.id ? 'text-white' : 'text-slate-300'}`}>
                {project.name}
              </div>
              <div className="text-[10px] text-slate-500 truncate flex items-center mt-0.5">
                <Clock className="w-3 h-3 mr-1" />
                {new Date(project.created_at).toLocaleDateString()}
              </div>
            </div>
          </button>
        ))}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Create New Project</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Project Name</label>
                <input 
                  value={newProject.name}
                  onChange={e => setNewProject({...newProject, name: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g. Truss Bridge Design"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
                <textarea 
                  value={newProject.description}
                  onChange={e => setNewProject({...newProject, description: e.target.value})}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2 px-3 text-white h-24 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Analyze the structural stability of..."
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleCreateProject}
                  className="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors font-semibold"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

 succeeded in 4482ms:
2026-05-29 11:53:31.382 xcodebuild[6528:81713817]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:32.002 xcodebuild[6528:81713809] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Gp7kb2yz' (errno=Operation not permitted)
2026-05-29 11:53:33.205 xcodebuild[6664:81714026]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:33.481 xcodebuild[6664:81714020] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
              analysisType={analysisType}
              onChangeAnalysisType={setAnalysisType}
              solving={solving}
              onRunSolver={runSolver}
              onStopSolver={stopSolver}
              showChat={showChat}
              onToggleChat={() => setShowChat(!showChat)}
              materialReference={lastSolverMaterialReference}
              materialOptions={buildTopbarMaterialOptions(FALLBACK_MATERIALS)}
              selectedMaterialId={selectedMaterial.id}
              onChangeMaterialId={(id) => {
                const found = FALLBACK_MATERIALS.find((m) => m.id === id);
                if (found) setSelectedMaterial(found);
              }}
            />

            <div style={{ padding: '40px', flex: 1 }}>
            {/* FM-04a Phase 36 B — ErrorCard mounts ABOVE
                OperatorStatusPanel so a failed user sees the red
                error band before the trust prose (Phase 35 R3
                friction point b). */}
            {uploadError && (
                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px' }}>
                    <ErrorCard {...uploadError} />
                </div>
            )}

            <OperatorStatusPanel
              strip={trustStrip}
              sections={trustSections}
              goldenSamples={goldenSampleQueue}
            />

            {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
            {!activeCaseId && (
                <div style={{ marginBottom: '24px' }}>
                    <CaseBrowser cases={FALLBACK_CANDIDATE_CASES} focusedCaseId={selectedCandidateCaseId} onSelectCase={(caseId) => setSelectedCandidateCaseId(caseId)} />
                </div>
            )}

            <div className="glass-panel" style={{ padding: '8px', display: 'flex', gap: '8px', width: 'fit-content', marginBottom: '32px' }}>
                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
            </div>

            {activeCaseId && (() => {
                // FM-04a Phase 37 B — pair BCSetupAdvisorCard with CaseOpenAdvisorCard (3rd advisor surface; closes Dim 4 80-anchor 3-stage sub-bullet).
                const caseOpenRecord = findCandidateCase(FALLBACK_CANDIDATE_CASES, activeCaseId);
                return caseOpenRecord ? (
                    <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '12px' }}>
                        <CaseOpenAdvisorCard caseRecord={caseOpenRecord} />
                        {shouldShowBCSetupAdvisor(caseOpenRecord) && <BCSetupAdvisorCard caseRecord={caseOpenRecord} />}
                        <BCSetupPillList caseRecord={caseOpenRecord} />
                    </div>
                ) : null;
            })()}

            {activeTab === 'visual' && (
                <VisualTabPanel
                    apiBase={API_BASE}
                    selectedCandidateCaseId={selectedCandidateCaseId}
                    onSelectCandidateCaseId={setSelectedCandidateCaseId}
                    comparisonCaseA={comparisonCaseA}
                    comparisonCaseB={comparisonCaseB}
                    onSelectComparisonA={setComparisonCaseA}
                    onSelectComparisonB={setComparisonCaseB}
                    snapshotLabelA={snapshotLabelA}
                    snapshotLabelB={snapshotLabelB}
                    onSelectSnapshotLabelA={setSnapshotLabelA}
                    onSelectSnapshotLabelB={setSnapshotLabelB}
                    selectedMaterial={selectedMaterial}
                    onMaterialChange={setSelectedMaterial}
                    latestSignoff={latestSignoff}
                    onLatestSignoff={setLatestSignoff}
                />
            )}

            <div style={{ padding: '0', flex: 1 }}>
                {activeTab === 'explore' ? (
                    <ExplorationTabPanel
                        activeCaseId={activeCaseId!}
                        loading={loading}
                        activeExperiment={activeExperiment}
                        comparedIndices={comparedIndices}
                        onCompareIndex={(i) => {
                            if (comparedIndices) {
                                if (comparedIndices[0] === i) {
                                    setComparedIndices(null);
                                } else {
                                    setComparedIndices([comparedIndices[0], i]);
                                }
                            } else {
                                setComparedIndices([i, -1]);
                            }
                        }}
                        onRunStudy={handleRunStudy}
                    />
                ) : (
                    <>
                    {loading ? (
                        <div className="shimmer-active" style={{ height: '400px', width: '100%', borderRadius: '12px', background: 'var(--bg-surface)' }}></div>
                    ) : report ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div className="glass-panel" style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
                                {activeTab === 'visual' ? (
                                    <div
                                      style={{
                                        display: 'grid',
                                        gridTemplateRows: activeCaseId ? '400px minmax(300px, 1fr)' : '1fr',
                                        gap: activeCaseId ? '12px' : 0,
                                        padding: activeCaseId ? '12px' : 0,
                                        minHeight: activeCaseId ? '820px' : '600px',
                                      }}
                                    >
                                        {activeCaseId && (
                                          <ResultMeshPlaybackPanel
                                            caseId={activeCaseId}
                                            apiBase={API_BASE}
                                            enabled={activeTab === 'visual'}
                                            uiMode={appUiMode}
                                            onUiModeChange={handleAppUiModeChange}
                                          />
                                        )}
                                        <div
                                          style={{
                                            position: 'relative',
                                            width: '100%',
                                            minHeight: '300px',
                                            overflow: 'hidden',
                                            border: activeCaseId ? '1px solid var(--border)' : 'none',
                                            borderRadius: activeCaseId ? '8px' : 0,
                                          }}
                                        >
                                        <iframe 
                                            src={comparedIndices && comparedIndices[1] !== -1 
                                                ? `${API_BASE}/visualize/delta?file1=${activeExperiment?.runs[comparedIndices[0]].inp_path.replace('.inp','.frd')}&file2=${activeExperiment?.runs[comparedIndices[1]].inp_path.replace('.inp','.frd')}` 
                                                : `${API_BASE}/visualize/plot?case_id=${activeCaseId || 'last'}&output_format=html&increment_index=${selectedModeIndex}`} 
                                            style={{ width: '100%', height: '100%', border: 'none' }} 
                                            title="FEA Visualization" 
                                        />
                                        
                                        {report?.increments && report.increments.length > 0 && (
                                            <div style={{ position: 'absolute', top: '24px', right: '24px', width: '320px', zIndex: 10 }}>
                                                <ModeSelector 
                                                    increments={report.increments}
                                                    selectedModeIndex={selectedModeIndex}
                                                    activeAnalysisType={analysisType}
                                                    onSelectMode={(idx) => setSelectedModeIndex(idx)}
                                                />
                                            </div>
                                        )}
                                        </div>
                                    </div>
                                ) : (
                                    <NarrativeTabPanel
                                        report={report}
                                        onDownloadPDF={downloadPDFReport}
                                    />
                                )}
                            </div>
                        </div>
                    ) : (
                        <div style={{ height: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '16px' }}>
                            <LayoutDashboard size={48} strokeWidth={1} />
                            <div>Select a structural case from the gallery to begin analysis</div>

 succeeded in 4487ms:
2026-05-29 11:53:31.391 xcodebuild[6529:81713814]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:32.001 xcodebuild[6529:81713810] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-okgs1eb9' (errno=Operation not permitted)
2026-05-29 11:53:33.204 xcodebuild[6665:81714027]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:53:33.481 xcodebuild[6665:81714022] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
// FM-04a Phase 37 A — CaseBrowser canonical case-picker surface.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.
//
// First canonical-surface industrial-UI parity lift since the
// rubric v2.0 baseline (Phase 33 A). The 5 canonical surfaces
// described at `.planning/test_subagents/references/` set
// Hyperworks / Abaqus / ANSYS conventions; before Phase 37 A the
// case-picker pillar was rated 3.2/10 (flat list, no grouping,
// no filter, no preview). CaseBrowser delivers Hyperworks-style
// case browser conventions:
//
//   * Tree-style grouping by `solverKind` (matches the verdict YAML
//     enum: linear_static / modal / buckling / dynamic /
//     heat_transfer_steady_state / contact_pair_static). When a
//     case lacks a solverKind in the registry, it groups under
//     "uncategorized".
//   * Filter chip row — toggle individual solver-kind chips +
//     "Tier 2 validated only" filter chip + text search input
//     (matches against displayLabel + caseId, case-insensitive).
//   * Preview pane on the right showing the focused case's
//     displayLabel + claimTier + runnerAvailable badge + a short
//     orientation derived from the same caseId-pattern lookup
//     CaseOpenAdvisorCard uses (so the browse + open surfaces
//     give the reviewer consistent copy).
//
// Anti-gaming guards:
//   Q:-1 (NEW Phase 37) — preserves the CandidateCaseRecord data
//     contract; consumes the existing FALLBACK_CANDIDATE_CASES OR
//     the live-route payload unchanged. New test pin asserts the
//     12-cohort case list is fully rendered when grouping is
//     enabled.
//   I:-1 (Phase 34 carry) — does NOT modify Phase 19 D Sidebar.
//     The Sidebar still mounts as before; CaseBrowser is a NEW
//     surface that coexists.

import type { CSSProperties } from 'react'
import { useMemo, useState } from 'react'
import type { CandidateCaseRecord } from '../candidateCaseRegistry'
import { InContextHint } from './InContextHint'

export interface CaseBrowserProps {
  /** The cohort of candidate cases to browse. Pass the same array
   * the existing case-picker consumes. */
  readonly cases: readonly CandidateCaseRecord[]
  /** Optional currently-focused case id. When provided, the preview
   * pane renders that case's details. */
  readonly focusedCaseId?: string | null
  /** Selection callback. Fires when the user clicks a case row in
   * a group. The host wires this to the same handler the existing
   * Sidebar / palette already calls. */
  readonly onSelectCase: (caseId: string) => void
}

/** Phase 37 A — Hyperworks-style canonical case-browser surface.
 *
 * Renders a 2-pane layout: left = grouped + filterable case list,
 * right = focused-case preview. */
export function CaseBrowser({
  cases,
  focusedCaseId,
  onSelectCase,
}: CaseBrowserProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeKindFilters, setActiveKindFilters] = useState<ReadonlySet<string>>(
    new Set(),
  )
  const [tier2Only, setTier2Only] = useState(false)
  const [hoveredCaseId, setHoveredCaseId] = useState<string | null>(null)

  const previewCaseId = hoveredCaseId ?? focusedCaseId ?? null
  const previewCase = useMemo(
    () => cases.find((c) => c.caseId === previewCaseId) ?? null,
    [cases, previewCaseId],
  )

  const grouped = useMemo(
    () => groupAndFilterCases(cases, { searchQuery, activeKindFilters, tier2Only }),
    [cases, searchQuery, activeKindFilters, tier2Only],
  )

  // Stable solver-kind enum for the chip row.
  const allKinds = useMemo(() => {
    const set = new Set<string>()
    for (const c of cases) if (c.solverKind !== undefined) set.add(c.solverKind)
    return Array.from(set).sort()
  }, [cases])

  const toggleKindFilter = (kind: string) => {
    setActiveKindFilters((prev) => {
      const next = new Set(prev)
      if (next.has(kind)) next.delete(kind)
      else next.add(kind)
      return next
    })
  }

  const totalShown = grouped.reduce((acc, g) => acc + g.cases.length, 0)

  return (
    <section
      data-testid="case-browser"
      role="region"
      aria-label="Case browser — grouped by solver kind"
      style={rootStyle}
    >
      <InContextHint
        hintId="case-browser"
        label="Case browser"
        text="Pick a case to open. Filter by solver kind or search by name; the preview pane summarises what each case validates before you commit."
      />
      <header style={headerStyle}>
        <strong style={titleStyle}>Case browser</strong>
        <span
          data-testid="case-browser-count"
          style={countStyle}
        >{`${totalShown} of ${cases.length}`}</span>
      </header>

      <div style={filterRowStyle} data-testid="case-browser-filter-row">
        <input
          type="search"
          placeholder="Filter by name or id"
          aria-label="Filter cases by name or id"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="case-browser-search-input"
          style={searchInputStyle}
        />
        <button
          type="button"
          data-testid="case-browser-tier2-chip"
          aria-pressed={tier2Only}
          onClick={() => setTier2Only((v) => !v)}
          style={tier2Only ? chipActiveStyle : chipIdleStyle}
        >
          Tier 2 validated
        </button>
        {allKinds.map((kind) => (
          <button
            type="button"
            key={kind}
            data-testid={`case-browser-kind-chip-${kind}`}
            aria-pressed={activeKindFilters.has(kind)}
            onClick={() => toggleKindFilter(kind)}
            style={
              activeKindFilters.has(kind) ? chipActiveStyle : chipIdleStyle
            }
          >
            {prettyKind(kind)}
          </button>
        ))}
      </div>

      <div style={paneRowStyle}>
        <ol style={groupListStyle} data-testid="case-browser-group-list">
          {grouped.map((group) => (
            <li key={group.kind} style={groupItemStyle}>
              <div style={groupHeaderStyle} data-testid={`case-browser-group-${group.kind}`}>
                <span style={groupHeaderLabelStyle}>{prettyKind(group.kind)}</span>
                <span style={groupHeaderCountStyle}>{group.cases.length}</span>
              </div>
              <ul style={caseListStyle}>
                {group.cases.map((c) => (
                  <li key={c.caseId}>
                    <button
                      type="button"
                      onMouseEnter={() => setHoveredCaseId(c.caseId)}
                      onMouseLeave={() => setHoveredCaseId(null)}
                      onClick={() => onSelectCase(c.caseId)}
                      data-testid={`case-browser-row-${c.caseId}`}
                      data-active={focusedCaseId === c.caseId ? 'true' : undefined}
                      style={
                        focusedCaseId === c.caseId
                          ? caseRowActiveStyle
                          : caseRowIdleStyle
                      }
                    >
                      {c.displayLabel ?? c.caseId}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
          {grouped.length === 0 && (
            <li data-testid="case-browser-empty" style={emptyStateStyle}>
              No cases match the current filters.
            </li>
          )}
        </ol>

        <aside style={previewPaneStyle} data-testid="case-browser-preview-pane">
          {previewCase ? (
            <>
              <div style={previewHeaderStyle}>
                <strong style={previewTitleStyle}>
                  {previewCase.displayLabel ?? previewCase.caseId}
                </strong>
                {previewCase.runnerAvailable === false && (
                  <span
                    data-testid="case-browser-runner-badge"
                    style={runnerBadgeStyle}
                  >
                    demo · no live runner
                  </span>
                )}
              </div>
              <p style={previewMetaStyle}>
                <span style={previewMetaLabelStyle}>Tier:</span> {previewCase.claimTier}
              </p>
              {previewCase.solverKind !== undefined && (
                <p style={previewMetaStyle}>
                  <span style={previewMetaLabelStyle}>Solver kind:</span>{' '}
                  {prettyKind(previewCase.solverKind)}
                </p>
              )}
              <p style={previewBlurbStyle}>
                {previewBlurbFor(previewCase.caseId)}
              </p>
            </>
          ) : (
            <p style={previewEmptyStyle}>Hover or focus a case to preview it here.</p>
          )}
        </aside>
      </div>
    </section>
  )
}

/** Phase 37 A — pure helper: filter + group cases per current
 * UI controls. Exposed for testing. */
export function groupAndFilterCases(
  cases: readonly CandidateCaseRecord[],
  opts: {
    readonly searchQuery: string
    readonly activeKindFilters: ReadonlySet<string>
    readonly tier2Only: boolean
  },

exec
/bin/zsh -lc "rg -n \"ProjectManager\" -S frontend/src/**/*.test* tests frontend/src | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
zsh:1: no matches found: frontend/src/**/*.test*

exec
/bin/zsh -lc "rg -n \"function OperatorStatusPanel|export function OperatorStatusPanel|const OperatorStatusPanel\" frontend/src -S && sed -n '1,260p' frontend/src/components/OperatorStatusPanel.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/src/components/OperatorStatusPanel.tsx:35:export function OperatorStatusPanel({
// FM-04a Phase 22 C — extracted out of App.tsx as part of the
// LOC-discipline trajectory. Renders the Validation & Trust Center
// header strip + sections + Golden-sample queue. Pure-presentational
// component; all state is owned by the App composition root.
//
// FM-04a Phase 29 B — per-section rendering delegated to the
// SectionFrame primitive (collapsible accordion + uniform visual
// vocabulary). The strip + golden-sample queue still inlined here.
// Per-section collapse state lives in localStorage; storage keys
// are derived from the section title (lowercased / kebabed).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { ShieldAlert } from 'lucide-react';
import type {
  GoldenSampleQueueItem,
  OperatorStatusItem,
  OperatorStatusSection,
} from '../types/AppTypes';
import { installPolishStyles } from './polishStyles';
import { SectionFrame } from './SectionFrame';
import { InContextHint } from './InContextHint';
import { useEffect } from 'react';

/** Derive a stable per-section storage key from the section title.
 * `Validation & Reference` → `validation-reference`. */
export function sectionStorageKey(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function OperatorStatusPanel({
  strip,
  sections,
  goldenSamples,
}: {
  strip: OperatorStatusItem[];
  sections: OperatorStatusSection[];
  goldenSamples: GoldenSampleQueueItem[];
}) {
  // Phase 29 B — ensure the polish stylesheet (which now carries
  // the chevron-rotation transition rule) is installed.
  useEffect(() => {
    installPolishStyles();
  }, []);
  const toneColor = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--accent)';
    if (tone === 'warning') return '#f59e0b';
    if (tone === 'danger') return '#ef4444';
    return 'var(--text-primary)';
  };

  const toneBackground = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.08)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.08)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.08)';
    return 'rgba(15, 23, 42, 0.55)';
  };

  const toneBorder = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.35)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.35)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.35)';
    return 'var(--border)';
  };

  return (
    <section className="glass-panel" style={{ padding: '18px 20px', marginBottom: '24px' }} aria-label="Validation and trust center">
      <InContextHint
        hintId="operator-status"
        label="Workbench state"
        text="This panel tracks the live solve and trust state. If the log connection drops mid-run, you'll get a recovery card with a Retry."
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>Validation & Trust Center</div>
          <h2 style={{ fontSize: '1.1rem', margin: '4px 0 0 0' }}>Evidence-first workbench state</h2>
        </div>
        <div style={{ color: '#ef4444', fontSize: '0.78rem', fontWeight: 800, border: '1px solid rgba(239, 68, 68, 0.35)', borderRadius: '999px', padding: '5px 10px', background: 'rgba(239, 68, 68, 0.08)' }}>
          not signed validation
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '18px' }}>
        {strip.map((item) => (
          <div key={item.label} style={{ background: toneBackground(item.tone), border: `1px solid ${toneBorder(item.tone)}`, borderRadius: '8px', padding: '12px', minHeight: '78px' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>{item.label}</div>
            <div style={{ color: toneColor(item.tone), fontSize: '0.88rem', fontWeight: 650, lineHeight: 1.35, overflowWrap: 'anywhere' }}>{item.value}</div>
            {item.detail && <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{item.detail}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
        {sections.map((section) => (
          <SectionFrame
            key={section.title}
            section={section}
            storageKey={sectionStorageKey(section.title)}
          />
        ))}
      </div>

      <div style={{ marginTop: '14px', background: 'rgba(15, 23, 42, 0.48)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px' }}>
        <div style={{ fontSize: '0.86rem', fontWeight: 800, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="var(--accent)" />
          Golden Sample Review Queue
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {goldenSamples.map((sample) => (
            <div key={sample.caseId} style={{ border: `1px solid ${toneBorder(sample.tone)}`, background: toneBackground(sample.tone), borderRadius: '8px', padding: '12px', minHeight: '106px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800, fontSize: '0.82rem' }}>{sample.caseId}</div>
                <div style={{ color: toneColor(sample.tone), fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>{sample.status}</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.74rem', lineHeight: 1.35, marginBottom: '6px' }}>{sample.name}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, overflowWrap: 'anywhere' }}>{sample.reason}</div>
              <div style={{ color: toneColor(sample.tone), fontSize: '0.7rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{sample.failurePatternRef}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

exec
/bin/zsh -lc 'rg -n "tab-pill-bar|viewport-hero|cb-case-card|cb-search|cb-chip|eyebrow|surface-card|vp-toggle" frontend/src -S' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/src/index.css:133:/* Eyebrow / section-label all-caps text reads as refined when tracked out. */
frontend/src/index.css:134:.eyebrow,
frontend/src/index.css:135:[data-eyebrow] {
frontend/src/index.css:213:.surface-card {
frontend/src/index.css:223:.surface-card.is-interactive:hover,
frontend/src/index.css:224:a.surface-card:hover,
frontend/src/index.css:225:button.surface-card:hover {
frontend/src/index.css:252:.cb-case-card {
frontend/src/index.css:258:.cb-case-card:hover {
frontend/src/index.css:264:.cb-chip {
frontend/src/index.css:269:.cb-chip:hover { border-color: var(--border-strong); color: var(--text-primary); }
frontend/src/index.css:270:.cb-search { transition: border-color var(--dur-fast) var(--ease-out); }
frontend/src/index.css:271:.cb-search:focus-visible { border-color: var(--border-focus); outline: none; }
frontend/src/index.css:290:/* Viewport-hero + tab-pill + in-viewport toggle (active-case golden path). */
frontend/src/index.css:291:.viewport-hero {
frontend/src/index.css:300:.tab-pill-bar {
frontend/src/index.css:326:.vp-toggle {
frontend/src/index.css:336:.vp-toggle[aria-pressed="true"], .vp-toggle.active {
frontend/src/index.css:393:  .surface-card { transition: none; }
frontend/src/index.css:394:  .cb-case-card, .cb-chip, .cb-search { transition: none; }
frontend/src/index.css:395:  .cb-case-card:hover { transform: none; }
frontend/src/index.css:396:  .tab-pill, .vp-toggle { transition: none; }
frontend/src/App.tsx:1339:            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
frontend/src/App.tsx:1403:                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
frontend/src/components/ProjectManager.tsx:59:        <span className="eyebrow">Projects</span>
frontend/src/components/CaseBrowser.tsx:129:          className="cb-search"
frontend/src/components/CaseBrowser.tsx:137:          className="cb-chip"
frontend/src/components/CaseBrowser.tsx:176:                      className="cb-case-card"
frontend/src/components/AdvancedModePromo.tsx:134:              user-meaningful eyebrow. */}
frontend/src/components/AdvancedModePromo.tsx:135:          <span style={STYLES.eyebrow}>Workbench tip</span>
frontend/src/components/AdvancedModePromo.tsx:193:  eyebrow: {

exec
/bin/zsh -lc 'rg -n "shippedInPhase|onboarding-progress|Workbench tip|Phase 25 C|ProjectManager|project-rail|case-browser-search-input|tab-pill-bar|viewport-hero" frontend tests -S' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/src/onboardingTour.ts:3:// Basic-mode toggle from Phase 25 C and Δ column from Phase 26 C).
frontend/src/onboardingTour.ts:31:  | 'basic-advanced-mode'  // Phase 27 D · introduces Phase 25 C
frontend/src/onboardingTour.ts:40:  shippedInPhase: string;
frontend/src/onboardingTour.ts:48:    shippedInPhase: 'Phase 23 B',
frontend/src/onboardingTour.ts:54:    shippedInPhase: 'Phase 23 D',
frontend/src/onboardingTour.ts:60:    shippedInPhase: 'Phase 23 C',
frontend/src/onboardingTour.ts:66:    shippedInPhase: 'Phase 22 B',
frontend/src/onboardingTour.ts:68:  // FM-04a Phase 27 D — Basic / Advanced mode toggle (Phase 25 C).
frontend/src/onboardingTour.ts:75:    shippedInPhase: 'Phase 25 C',
frontend/src/onboardingTour.ts:84:    shippedInPhase: 'Phase 26 C',
frontend/src/App.tsx:19:import { ProjectManager } from './components/ProjectManager';
frontend/src/App.tsx:1247:      <ProjectManager
frontend/src/App.tsx:1339:            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
frontend/src/App.tsx:1403:                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
frontend/src/uiMode.ts:1:// FM-04a Phase 25 C — Basic / Advanced UI mode state machine.
frontend/src/uiMode.ts:4:// Phase 25 C addresses the cognitive-load axis for RETURNING reviewers
frontend/src/uiMode.ts:35: * Net membership count is UNCHANGED (5 features). The Phase 25 C
frontend/src/components/ResultMeshPlaybackPanel.tsx:61:// FM-04a Phase 25 C — Basic/Advanced UI mode. Hides advanced
frontend/src/components/ResultMeshPlaybackPanel.tsx:187:  // FM-04a Phase 25 C — Basic/Advanced UI mode. State preservation
frontend/src/components/ResultMeshPlaybackPanel.tsx:190:  // hidden. Pinned by Phase 25 C tests.
frontend/src/components/ResultMeshPlaybackPanel.tsx:194:  // + storage adapter (preserves Phase 25 C contract for direct-
frontend/src/components/ResultMeshPlaybackPanel.tsx:843:                FM-04a Phase 25 C gated by uiMode advanced.
frontend/src/components/ProjectManager.tsx:1:// FM-04a Phase 41.2 — ProjectManager restyle. The pre-41 markup used
frontend/src/components/ProjectManager.tsx:19:interface ProjectManagerProps {
frontend/src/components/ProjectManager.tsx:24:export function ProjectManager({ onSelectProject, selectedProjectId }: ProjectManagerProps) {
frontend/src/components/ProjectManager.tsx:57:    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
frontend/src/components/CaseBrowser.tsx:128:          data-testid="case-browser-search-input"
frontend/src/components/UiModeToggle.tsx:1:// FM-04a Phase 25 C — Basic / Advanced UI mode toggle (segmented control).
frontend/src/components/OnboardingTour.tsx:107:              (step.shippedInPhase, e.g. "Phase 23 B") removed from the
frontend/src/components/OnboardingTour.tsx:111:          <span data-testid="onboarding-progress" style={STYLES.progress}>
frontend/src/components/AdvancedModePromo.tsx:132:          {/* FM-04a Phase 41.2 — was "Phase 25 C · Phase 28 D" (internal
frontend/src/components/AdvancedModePromo.tsx:135:          <span style={STYLES.eyebrow}>Workbench tip</span>
frontend/src/index.css:291:.viewport-hero {
frontend/src/index.css:300:.tab-pill-bar {
frontend/test/Phase32C_polish_bundle.test.tsx:25://   C:-1: all existing Phase 25 C / 30 B pins still pass (33
frontend/test/Phase32C_polish_bundle.test.tsx:26://         tests in Phase 30 B + 15 in Phase 25 C). 2 pins UPDATED
frontend/test/Phase32C_polish_bundle.test.tsx:62:  it('Phase 25 C registry count unchanged (5 features; swap-not-extend)', () => {
frontend/test/Phase32C_polish_bundle.test.tsx:64:    // readout swap); the registry-size invariant from Phase 25 C
frontend/test/Phase24B_onboarding_tour.test.tsx:115:  it('each step has a non-empty title, body, and shippedInPhase tag', () => {
frontend/test/Phase24B_onboarding_tour.test.tsx:116:    // FM-04a Phase 27 D loosened the shippedInPhase regex from
frontend/test/Phase24B_onboarding_tour.test.tsx:118:    // Phase 25 C / Phase 26 C steps can pass. Intent preserved.
frontend/test/Phase24B_onboarding_tour.test.tsx:122:      expect(step.shippedInPhase).toMatch(/Phase 2\d [A-Z]/)
frontend/test/Phase24B_onboarding_tour.test.tsx:144:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:160:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:193:      expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:216:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase25C_ui_mode_toggle.test.tsx:1:// FM-04a Phase 25 C — Basic / Advanced UI mode toggle tests.
frontend/test/Phase25C_ui_mode_toggle.test.tsx:29:describe('Phase 25 C — uiMode state machine', () => {
frontend/test/Phase25C_ui_mode_toggle.test.tsx:117:describe('Phase 25 C — UiModeToggle component', () => {
frontend/test/Phase25C_ui_mode_toggle.test.tsx:143:describe('Phase 25 C — C:-1 anti-gaming guard (state preservation)', () => {
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:11://    6 cards. New cards: 'basic-advanced-mode' (Phase 25 C) and
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:192:  it('new basic-advanced-mode step cites Phase 25 C provenance', () => {
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:194:    expect(step.shippedInPhase).toBe('Phase 25 C')
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:201:    expect(step.shippedInPhase).toBe('Phase 26 C')
frontend/test/Phase26B_basic_mode_gating.test.tsx:3:// Closes the Phase 25 C honest-scope gap: in Phase 25 C only the
frontend/test/Phase30B_companion_viewport.test.tsx:699:  // id returns false (Phase 25 C strict-typing contract). But
frontend/test/Phase32B_use_app_ui_mode.test.tsx:66:      // per Phase 25 C / 29 C precedent.
frontend/test/Phase37A_case_browser.test.tsx:157:    const input = screen.getByTestId('case-browser-search-input') as HTMLInputElement
frontend/test/Phase37A_case_browser.test.tsx:165:    const input = screen.getByTestId('case-browser-search-input') as HTMLInputElement

exec
/bin/zsh -lc 'rg -n "Project Name|Create New Project|Create new project|Validation & Trust Center|Evidence-first workbench state" frontend/src frontend/tests tests -S' in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 2 in 0ms:
rg: frontend/tests: No such file or directory (os error 2)
frontend/src/components/ProjectManager.tsx:63:          aria-label="Create new project"
frontend/src/components/ProjectManager.tsx:101:            <h3 style={modalTitleStyle}>Create new project</h3>
frontend/src/components/OperatorStatusPanel.tsx:2:// LOC-discipline trajectory. Renders the Validation & Trust Center
frontend/src/components/OperatorStatusPanel.tsx:79:          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>Validation & Trust Center</div>
frontend/src/components/OperatorStatusPanel.tsx:80:          <h2 style={{ fontSize: '1.1rem', margin: '4px 0 0 0' }}>Evidence-first workbench state</h2>

exec
/bin/zsh -lc "sed -n '240,420p' frontend/src/components/CaseBrowser.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
    readonly searchQuery: string
    readonly activeKindFilters: ReadonlySet<string>
    readonly tier2Only: boolean
  },
): ReadonlyArray<{ readonly kind: string; readonly cases: readonly CandidateCaseRecord[] }> {
  const q = opts.searchQuery.trim().toLowerCase()
  const filtered = cases.filter((c) => {
    if (opts.tier2Only && !c.claimTier.toLowerCase().includes('tier 2')) {
      return false
    }
    if (opts.activeKindFilters.size > 0) {
      const kind = c.solverKind ?? 'uncategorized'
      if (!opts.activeKindFilters.has(kind)) return false
    }
    if (q.length > 0) {
      const hay = `${c.displayLabel ?? ''} ${c.caseId}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })

  // Group by solverKind (or "uncategorized" when absent)
  const groups = new Map<string, CandidateCaseRecord[]>()
  for (const c of filtered) {
    const kind = c.solverKind ?? 'uncategorized'
    const bucket = groups.get(kind) ?? []
    bucket.push(c)
    groups.set(kind, bucket)
  }
  const out: { kind: string; cases: readonly CandidateCaseRecord[] }[] = []
  for (const kind of Array.from(groups.keys()).sort()) {
    out.push({ kind, cases: groups.get(kind) ?? [] })
  }
  return out
}

/** Phase 37 A — friendly label for a solver-kind enum value. */
export function prettyKind(kind: string): string {
  switch (kind) {
    case 'linear_static':
      return 'Linear static'
    case 'modal':
      return 'Modal'
    case 'buckling':
      return 'Buckling'
    case 'dynamic':
      return 'Dynamic'
    case 'heat_transfer_steady_state':
      return 'Heat transfer (steady state)'
    case 'contact_pair_static':
      return 'Contact pair (static)'
    case 'uncategorized':
      return 'Uncategorized'
    default:
      return kind
  }
}

/** Phase 37 A — preview blurb derived from caseId pattern. Matches
 * the Phase 35 A `orientationForCaseKind` lookup so the browse
 * surface and the case-open surface share their copy. */
export function previewBlurbFor(caseId: string): string {
  const id = caseId.toLowerCase()
  if (id.startsWith('hertz-contact-')) return 'Contact-mechanics candidate.'
  if (id.startsWith('cantilever-buckle')) return 'Linear buckling case.'
  if (id.startsWith('cantilever-dynamic')) return 'Dynamic cantilever case.'
  if (id.startsWith('cantilever-beam-modal') || id.startsWith('modal-cantilever'))
    return 'Modal analysis case.'
  if (id.startsWith('cantilever-')) return 'Cantilever beam case.'
  if (id.startsWith('cylinder-pv-')) return 'Pressure-vessel case.'
  if (id.startsWith('euler-column')) return 'Euler column buckling case.'
  if (id.startsWith('plate-with-hole')) return 'Stress-concentration case.'
  if (id.startsWith('plate-simply-supported') || id.startsWith('plate-ss-shell'))
    return 'Simply-supported plate case.'
  if (id.startsWith('heat-transfer-')) return 'Heat-transfer case.'
  if (id.startsWith('rod-wave-impact-energy-leak'))
    return 'Wave-propagation case in its known-bad configuration.'
  if (id.startsWith('rod-wave-impact-')) return 'Axial wave-propagation case.'
  if (id.startsWith('gs-1')) return 'Ballistic-impact demo case.'
  return 'Engineering candidate case.'
}

const rootStyle: CSSProperties = {
  borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)',
  background: 'var(--bg-surface)',
  padding: 'var(--sp-6)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-4)',
  color: 'var(--text-primary)',
  boxShadow: 'var(--elev-2)',
}
const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  justifyContent: 'space-between',
}
const titleStyle: CSSProperties = {
  fontSize: 'var(--fs-lg)',
  fontWeight: 700,
  letterSpacing: 'var(--tracking-tight)',
}
const countStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--text-secondary)',
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const filterRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  alignItems: 'center',
}
const searchInputStyle: CSSProperties = {
  flex: '1 1 200px',
  minWidth: 0,
  background: 'var(--bg-muted, rgba(255,255,255,0.04))',
  border: '1px solid var(--border)',
  color: 'var(--text-primary)',
  padding: '8px 12px',
  borderRadius: 'var(--r-sm)',
  fontSize: 'var(--fs-sm)',
}
const chipBase: CSSProperties = {
  fontSize: 11,
  padding: '4px 10px',
  borderRadius: 999,
  cursor: 'pointer',
  fontFamily: 'inherit',
}
const chipIdleStyle: CSSProperties = {
  ...chipBase,
  background: 'transparent',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
}
const chipActiveStyle: CSSProperties = {
  ...chipBase,
  background: 'var(--accent, #0a8a4a)',
  border: '1px solid var(--accent, #0a8a4a)',
  color: '#000',
}
const paneRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) minmax(220px, 280px)',
  gap: 12,
  alignItems: 'start',
}
const groupListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const groupItemStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}
const groupHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}
const groupHeaderLabelStyle: CSSProperties = {}
const groupHeaderCountStyle: CSSProperties = {
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const caseListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,

exec
/bin/zsh -lc "sed -n '420,560p' frontend/src/components/CaseBrowser.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-1)',
}
const caseRowBase: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 'var(--sp-3)',
  width: '100%',
  textAlign: 'left',
  fontSize: 'var(--fs-sm)',
  padding: 'var(--sp-3) var(--sp-4)',
  borderRadius: 'var(--r-md)',
  border: '1px solid transparent',
  cursor: 'pointer',
  fontFamily: 'inherit',
  color: 'var(--text-primary)',
}
const caseRowIdleStyle: CSSProperties = {
  ...caseRowBase,
  background: 'transparent',
}
const caseRowActiveStyle: CSSProperties = {
  ...caseRowBase,
  background: 'var(--accent-glow)',
  border: '1px solid var(--border-focus)',
}
const previewPaneStyle: CSSProperties = {
  borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)',
  background: 'var(--bg-muted, rgba(255,255,255,0.03))',
  padding: 'var(--sp-5)',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--sp-2)',
  minHeight: 100,
  boxShadow: 'var(--elev-1)',
  position: 'sticky',
  top: 'var(--sp-4)',
}
const previewHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
}
const previewTitleStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  flex: '1 1 auto',
  minWidth: 0,
}
const previewMetaStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-primary)',
  lineHeight: 1.45,
}
const previewMetaLabelStyle: CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginInlineEnd: 4,
}
const previewBlurbStyle: CSSProperties = {
  margin: '6px 0 0',
  fontSize: 12,
  fontStyle: 'italic',
  color: 'var(--text-secondary)',
  lineHeight: 1.45,
}
const previewEmptyStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
}
const emptyStateStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
  padding: '8px 10px',
}
const runnerBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  padding: '1px 6px',
  borderRadius: 6,
  background: 'rgba(255, 180, 80, 0.10)',
  border: '1px solid rgba(255, 180, 80, 0.45)',
  color: 'var(--text-secondary)',
}

exec
/bin/zsh -lc "sed -n '1,240p' frontend/src/components/SectionFrame.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 29 B — uniform SectionFrame primitive with
// collapsible header.
//
// Closes the Phase 28 UI-audit gap "no collapse/expand on 7 trust
// sections; industrial reviewer tools default to collapsible
// accordions." Renders one trust section with a clickable header
// containing the chevron + icon + title + (optional) item-count
// summary, and a collapsible body of label/value/detail rows.
//
// Anti-gaming guards:
//   B:-1: prefers-reduced-motion: reduce disables the chevron
//         rotation transition (the chevron still rotates structurally
//         so the user can see WHICH state it's in; only the
//         animation is suppressed).
//   C:-1: storage key includes the storageKey verbatim — no
//         cross-section bleed.
//   D:-1: default is EXPANDED. Toggle persists to localStorage so
//         reviewer's choice survives reloads.
//   E:-1: corrupted/malformed localStorage value → default expanded
//         (per loadSectionCollapsed contract).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { ChevronDown } from 'lucide-react';

import type { OperatorStatusItem, OperatorStatusSection } from '../types/AppTypes';
import {
  loadSectionCollapsed,
  saveSectionCollapsed,
} from './sectionCollapseStorage';

export interface SectionFrameProps {
  section: OperatorStatusSection;
  /** Stable identifier for localStorage key. Should be URL-safe
   * (no spaces; lowercase kebab-case recommended). */
  storageKey: string;
  /** Initial collapsed state if no persisted value exists.
   * Defaults to `false` (expanded). D:-1 additive guard. */
  defaultCollapsed?: boolean;
  /** Optional forced-collapsed override (for tests / settings UI). */
  forceCollapsed?: boolean;
  /** Optional callback for telemetry / parent state mirror. */
  onCollapsedChange?: (collapsed: boolean) => void;
}

/** Resolve tone → text color (matches OperatorStatusPanel's palette). */
function toneColor(tone?: OperatorStatusItem['tone']): string {
  if (tone === 'accent') return 'var(--accent)';
  if (tone === 'warning') return '#f59e0b';
  if (tone === 'danger') return '#ef4444';
  return 'var(--text-primary)';
}

export function SectionFrame({
  section,
  storageKey,
  defaultCollapsed = false,
  forceCollapsed,
  onCollapsedChange,
}: SectionFrameProps) {
  // Initialize from localStorage; fall back to defaultCollapsed if no
  // persisted value. Synchronous initializer so the first render is
  // already in the correct state (no flash).
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (forceCollapsed !== undefined) return forceCollapsed;
    const persisted = loadSectionCollapsed(storageKey);
    return persisted !== null ? persisted : defaultCollapsed;
  });

  // When the forceCollapsed prop changes, mirror it.
  useEffect(() => {
    if (forceCollapsed !== undefined) setCollapsed(forceCollapsed);
  }, [forceCollapsed]);

  const handleToggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      saveSectionCollapsed(storageKey, next);
      onCollapsedChange?.(next);
      return next;
    });
  }, [storageKey, onCollapsedChange]);

  // Item count summary shown in the collapsed-header state.
  const itemCount = section.items.length;

  return (
    <div
      data-testid={`section-frame-${storageKey}`}
      data-collapsed={collapsed ? 'true' : 'false'}
      style={STYLES.card}
    >
      <button
        type="button"
        data-testid={`section-frame-${storageKey}-toggle`}
        aria-expanded={!collapsed}
        aria-controls={`section-frame-${storageKey}-body`}
        onClick={handleToggle}
        style={STYLES.header}
      >
        <ChevronDown
          size={14}
          aria-hidden="true"
          data-testid={`section-frame-${storageKey}-chevron`}
          style={{
            ...STYLES.chevron,
            transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          }}
          className="fm04a-section-frame-chevron"
        />
        <span style={STYLES.icon}>{section.icon}</span>
        <span style={STYLES.title}>{section.title}</span>
        {collapsed && (
          <span
            data-testid={`section-frame-${storageKey}-count`}
            style={STYLES.count}
          >
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </span>
        )}
      </button>
      <div
        id={`section-frame-${storageKey}-body`}
        role="region"
        aria-label={`${section.title} details`}
        data-testid={`section-frame-${storageKey}-body`}
        hidden={collapsed}
        style={collapsed ? { display: 'none' } : STYLES.body}
      >
        {section.items.map((item: OperatorStatusItem) => (
          <div
            key={`${section.title}-${item.label}`}
            data-testid={`section-frame-${storageKey}-row-${item.label}`}
            style={STYLES.row}
          >
            <div style={STYLES.rowLabel}>{item.label}</div>
            <div style={{ ...STYLES.rowValue, color: toneColor(item.tone) }}>
              {item.value}
            </div>
            {item.detail && (
              <div style={STYLES.rowDetail}>{item.detail}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const STYLES: Record<string, CSSProperties> = {
  card: {
    background: 'rgba(15, 23, 42, 0.48)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 14,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    width: '100%',
    background: 'transparent',
    border: 'none',
    padding: 0,
    margin: 0,
    color: 'var(--text-primary)',
    fontSize: '0.86rem',
    fontWeight: 800,
    cursor: 'pointer',
    textAlign: 'left',
  },
  chevron: {
    color: 'var(--text-secondary)',
    flex: '0 0 auto',
  },
  icon: {
    color: 'var(--accent)',
    display: 'flex',
    flex: '0 0 auto',
  },
  title: {
    flex: '1 1 auto',
  },
  count: {
    color: 'var(--text-muted)',
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    flex: '0 0 auto',
  },
  body: {
    display: 'grid',
    gap: 9,
    marginTop: 10,
  },
  row: {
    borderTop: '1px solid var(--border)',
    paddingTop: 9,
  },
  rowLabel: {
    fontSize: '0.66rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    fontWeight: 700,
    marginBottom: 4,
  },
  rowValue: {
    fontSize: '0.82rem',
    fontWeight: 650,
    lineHeight: 1.35,
    overflowWrap: 'anywhere',
  },
  rowDetail: {
    color: 'var(--text-secondary)',
    fontSize: '0.72rem',
    lineHeight: 1.35,
    marginTop: 4,
    overflowWrap: 'anywhere',
  },
};

exec
/bin/zsh -lc "git show HEAD:frontend/src/components/CaseBrowser.tsx | sed -n '300,520p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 6607ms:
2026-05-29 11:56:59.423 xcodebuild[10683:81725698]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:57:00.010 xcodebuild[10683:81725696] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-29Ahfzab' (errno=Operation not permitted)
2026-05-29 11:57:02.441 xcodebuild[11083:81726376]  DVTFilePathFSEvents: Failed to start fs event stream.
2026-05-29 11:57:02.777 xcodebuild[11083:81726369] [MT] DVTDeveloperPaths: Failed to get length of DARWIN_USER_CACHE_DIR from confstr(3), error = Error Domain=NSPOSIXErrorDomain Code=5 "Input/output error". Using NSCachesDirectory instead.
  if (id.startsWith('hertz-contact-')) return 'Contact-mechanics candidate.'
  if (id.startsWith('cantilever-buckle')) return 'Linear buckling case.'
  if (id.startsWith('cantilever-dynamic')) return 'Dynamic cantilever case.'
  if (id.startsWith('cantilever-beam-modal') || id.startsWith('modal-cantilever'))
    return 'Modal analysis case.'
  if (id.startsWith('cantilever-')) return 'Cantilever beam case.'
  if (id.startsWith('cylinder-pv-')) return 'Pressure-vessel case.'
  if (id.startsWith('euler-column')) return 'Euler column buckling case.'
  if (id.startsWith('plate-with-hole')) return 'Stress-concentration case.'
  if (id.startsWith('plate-simply-supported') || id.startsWith('plate-ss-shell'))
    return 'Simply-supported plate case.'
  if (id.startsWith('heat-transfer-')) return 'Heat-transfer case.'
  if (id.startsWith('rod-wave-impact-energy-leak'))
    return 'Wave-propagation case in its known-bad configuration.'
  if (id.startsWith('rod-wave-impact-')) return 'Axial wave-propagation case.'
  if (id.startsWith('gs-1')) return 'Ballistic-impact demo case.'
  return 'Engineering candidate case.'
}

const rootStyle: CSSProperties = {
  borderRadius: 10,
  border: '1px solid var(--border)',
  background: 'var(--bg-surface)',
  padding: 14,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  color: 'var(--text-primary)',
}
const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  justifyContent: 'space-between',
}
const titleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: '0.02em',
}
const countStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--text-secondary)',
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const filterRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  alignItems: 'center',
}
const searchInputStyle: CSSProperties = {
  flex: '1 1 200px',
  minWidth: 0,
  background: 'var(--bg-muted, rgba(255,255,255,0.04))',
  border: '1px solid var(--border)',
  color: 'var(--text-primary)',
  padding: '6px 10px',
  borderRadius: 6,
  fontSize: 12,
}
const chipBase: CSSProperties = {
  fontSize: 11,
  padding: '4px 10px',
  borderRadius: 999,
  cursor: 'pointer',
  fontFamily: 'inherit',
}
const chipIdleStyle: CSSProperties = {
  ...chipBase,
  background: 'transparent',
  border: '1px solid var(--border)',
  color: 'var(--text-secondary)',
}
const chipActiveStyle: CSSProperties = {
  ...chipBase,
  background: 'var(--accent, #0a8a4a)',
  border: '1px solid var(--accent, #0a8a4a)',
  color: '#000',
}
const paneRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) minmax(220px, 280px)',
  gap: 12,
  alignItems: 'start',
}
const groupListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}
const groupItemStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
}
const groupHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  color: 'var(--text-secondary)',
}
const groupHeaderLabelStyle: CSSProperties = {}
const groupHeaderCountStyle: CSSProperties = {
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
}
const caseListStyle: CSSProperties = {
  margin: 0,
  paddingInlineStart: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
}
const caseRowBase: CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  fontSize: 13,
  padding: '6px 10px',
  borderRadius: 6,
  border: '1px solid transparent',
  cursor: 'pointer',
  fontFamily: 'inherit',
  color: 'var(--text-primary)',
}
const caseRowIdleStyle: CSSProperties = {
  ...caseRowBase,
  background: 'transparent',
}
const caseRowActiveStyle: CSSProperties = {
  ...caseRowBase,
  background: 'var(--bg-muted, rgba(255,255,255,0.06))',
  border: '1px solid var(--border)',
}
const previewPaneStyle: CSSProperties = {
  borderRadius: 8,
  border: '1px solid var(--border)',
  background: 'var(--bg-muted, rgba(255,255,255,0.03))',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  minHeight: 100,
}
const previewHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  flexWrap: 'wrap',
}
const previewTitleStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  flex: '1 1 auto',
  minWidth: 0,
}
const previewMetaStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-primary)',
  lineHeight: 1.45,
}
const previewMetaLabelStyle: CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginInlineEnd: 4,
}
const previewBlurbStyle: CSSProperties = {
  margin: '6px 0 0',
  fontSize: 12,
  fontStyle: 'italic',
  color: 'var(--text-secondary)',
  lineHeight: 1.45,
}
const previewEmptyStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
}
const emptyStateStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: 'var(--text-secondary)',
  fontStyle: 'italic',
  padding: '8px 10px',
}
const runnerBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  padding: '1px 6px',
  borderRadius: 6,
  background: 'rgba(255, 180, 80, 0.10)',
  border: '1px solid rgba(255, 180, 80, 0.45)',
  color: 'var(--text-secondary)',
}

exec
/bin/zsh -lc 'rg -n "Phase 25 C · Phase 28 D|Workbench tip|Projects|Create new project|Validation & Trust Center|Evidence-first workbench state|project-rail|tab-pill-bar|viewport-hero|onboarding-progress|shippedInPhase" frontend/test tests -S' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/test/Phase24B_onboarding_tour.test.tsx:115:  it('each step has a non-empty title, body, and shippedInPhase tag', () => {
frontend/test/Phase24B_onboarding_tour.test.tsx:116:    // FM-04a Phase 27 D loosened the shippedInPhase regex from
frontend/test/Phase24B_onboarding_tour.test.tsx:122:      expect(step.shippedInPhase).toMatch(/Phase 2\d [A-Z]/)
frontend/test/Phase24B_onboarding_tour.test.tsx:144:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:160:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:193:      expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase24B_onboarding_tour.test.tsx:216:    expect(screen.getByTestId('onboarding-progress').textContent).toBe(
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:194:    expect(step.shippedInPhase).toBe('Phase 25 C')
frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx:201:    expect(step.shippedInPhase).toBe('Phase 26 C')

exec
/bin/zsh -lc "rg -n \"case-item active|case-item|glass-sidebar|glass-panel|tab-button-active|TabButton\\(\" frontend/test tests frontend/src -S" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/src/App.tsx:1403:                            <div className={activeTab === 'visual' && activeCaseId ? 'viewport-hero' : 'glass-panel'} style={{ minHeight: activeTab === 'visual' && activeCaseId ? '820px' : '600px', padding: '0', overflow: 'hidden' }}>
frontend/src/App.tsx:1473:            <div className="glass-panel" style={{ margin: '0 40px 40px 40px', height: '160px', display: 'flex', flexDirection: 'column', background: '#000' }}>
frontend/test/Phase19D.test.tsx:8://      (cmd-k-hint, case-gallery, case-item-*, frd-upload-input,
frontend/test/Phase19D.test.tsx:103:  it('renders each case as a stable case-item-* test id', () => {
frontend/test/Phase19D.test.tsx:123:    expect(screen.getByTestId('case-item-cylinder-pv-candidate')).toBeInTheDocument()
frontend/test/Phase19D.test.tsx:124:    expect(screen.getByTestId('case-item-rod-wave-impact-candidate')).toBeInTheDocument()
frontend/test/Phase19D.test.tsx:129:  it('clicking a case-item fires onSelectCase with that case', () => {
frontend/test/Phase19D.test.tsx:148:    fireEvent.click(screen.getByTestId('case-item-cylinder-pv-candidate'))
frontend/test/Phase19D.test.tsx:171:    const item = screen.getByTestId('case-item-cylinder-pv-candidate')
frontend/test/Phase38C_wcag_contrast.test.tsx:41:// Effective opaque background behind glass-panel text.
frontend/src/index.css:11: * removed). Existing `var(--token)` consumers and `.glass-*`/`.case-item`
frontend/src/index.css:166:.glass-panel {
frontend/src/index.css:177:.glass-sidebar {
frontend/src/index.css:185:.case-item {
frontend/src/index.css:191:.case-item:hover {
frontend/src/index.css:195:.case-item.active {
frontend/src/index.css:202:.tab-button-active {
frontend/src/index.css:349:  .glass-sidebar {
frontend/src/index.css:390:  .case-item { transition: none; }
frontend/src/components/SensitivityForm.tsx:27:    <div className="glass-panel" style={{ padding: '24px' }}>
frontend/src/components/ExplorationTabPanel.tsx:43:          className="glass-panel"
frontend/src/components/ExplorationTabPanel.tsx:61:                className="glass-panel"
frontend/src/components/BCSetupPillList.tsx:76:      className="glass-panel"
frontend/src/components/ProjectManager.tsx:6:// for the real 41.1 token system + the existing .glass-sidebar / .case-item /
frontend/src/components/ProjectManager.tsx:7:// .glass-panel shared classes. Behavior (fetch, create, select, modal) is
frontend/src/components/ProjectManager.tsx:57:    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
frontend/src/components/ProjectManager.tsx:77:              className={`case-item${active ? ' active' : ''}`}
frontend/src/components/ProjectManager.tsx:100:          <div className="glass-panel" style={modalCardStyle}>
frontend/src/components/ChatPanel.tsx:167:    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
frontend/src/components/BulletPlateBlueprintPanel.tsx:32:      className="glass-panel"
frontend/src/components/OperatorStatusPanel.tsx:71:    <section className="glass-panel" style={{ padding: '18px 20px', marginBottom: '24px' }} aria-label="Validation and trust center">
frontend/src/components/TabButton.tsx:9:export function TabButton({
frontend/src/components/Sidebar.tsx:78:      className="glass-sidebar"
frontend/src/components/Sidebar.tsx:191:                data-testid={`case-item-${c.id}`}
frontend/src/components/Sidebar.tsx:192:                className={`case-item ${activeCaseId === c.id ? 'active' : ''}`}
frontend/src/components/Sidebar.tsx:245:                  className={`case-item ${isActive ? 'active' : ''}`}
frontend/src/components/Sidebar.tsx:274:          className="glass-panel"
frontend/src/components/Sidebar.tsx:314:          className="glass-panel"

ERROR: Reconnecting... 1/5
exec
/bin/zsh -lc "sed -n '1,220p' frontend/src/components/OnboardingTour.tsx && printf '\\n--- promo ---\\n' && sed -n '1,220p' frontend/src/components/AdvancedModePromo.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 24 B — onboarding tour overlay component.
//
// Reads the pure-function state machine in onboardingTour.ts; persists
// dismissal to localStorage on first user interaction so the tour
// surfaces exactly once.

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';

import { useFocusTrap } from './useFocusTrap';

import {
  ONBOARDING_INITIAL_STATE,
  ONBOARDING_TOTAL_STEPS,
  createLocalStorageBackedStore,
  currentStep,
  dismissTour,
  nextStep,
  progressLabel,
  shouldShowTour,
  type OnboardingState,
  type OnboardingStorage,
} from '../onboardingTour';

export interface OnboardingTourProps {
  /** Optional injected storage; defaults to the localStorage adapter.
   * Test code passes a stub. */
  storage?: OnboardingStorage;
  /** Forces the overlay open regardless of localStorage; useful for
   * a future "Replay tour" affordance in settings. */
  forceShow?: boolean;
  /** Called every time the user advances or dismisses; useful for
   * higher-level telemetry. */
  onStateChange?: (next: OnboardingState) => void;
  /** FM-04a Phase 28 D — fired exactly once when the tour
   * transitions to dismissed (either Skip click or Done on the last
   * step). The parent uses this to surface the Advanced-mode
   * auto-promote prompt in the same session without a page reload. */
  onDismissed?: () => void;
}

export function OnboardingTour({
  storage,
  forceShow = false,
  onStateChange,
  onDismissed,
}: OnboardingTourProps) {
  const resolvedStorage = useMemo<OnboardingStorage>(
    () => storage ?? createLocalStorageBackedStore(),
    [storage],
  );
  const [persistedDismissed, setPersistedDismissed] = useState<boolean>(() =>
    forceShow ? false : resolvedStorage.load(),
  );
  const [state, setState] = useState<OnboardingState>(ONBOARDING_INITIAL_STATE);

  useEffect(() => {
    onStateChange?.(state);
  }, [state, onStateChange]);

  const handleAdvance = useCallback(() => {
    setState((prev) => {
      const next = nextStep(prev);
      if (next.dismissed && !prev.dismissed) {
        resolvedStorage.save(true);
        setPersistedDismissed(true);
        // FM-04a Phase 28 D — fire the one-shot dismissed signal so
        // the Advanced-mode promo can surface this session.
        onDismissed?.();
      }
      return next;
    });
  }, [resolvedStorage, onDismissed]);

  const handleSkip = useCallback(() => {
    setState((prev) => {
      if (prev.dismissed) return prev;
      const next = dismissTour(prev);
      resolvedStorage.save(true);
      setPersistedDismissed(true);
      // FM-04a Phase 28 D — same one-shot signal on the Skip path.
      onDismissed?.();
      return next;
    });
  }, [resolvedStorage, onDismissed]);

  const containerRef = useRef<HTMLDivElement>(null);
  const visible = shouldShowTour(state, persistedDismissed);
  // FM-04a Phase 29 C — focus-trap (WCAG 2.4.3). Active only while
  // the overlay is visible.
  useFocusTrap({ containerRef, active: visible });

  if (!visible) {
    return null;
  }
  const step = currentStep(state);
  if (step === null) return null;

  // FM-04a Phase 25 D — fade + slide-in animation on first render.
  // Respects prefers-reduced-motion via CSS media query in the
  // injected <style> tag.
  return (
    <div ref={containerRef} data-testid="onboarding-tour" role="dialog" aria-label="onboarding tour" style={STYLES.backdrop}>
      <style>{ONBOARDING_TOUR_KEYFRAMES}</style>
      <div style={STYLES.card} className="onboarding-tour-card">
        <div style={STYLES.header}>
          {/* FM-04a Phase 41.2 — dev-phase provenance badge
              (step.shippedInPhase, e.g. "Phase 23 B") removed from the
              user-facing tour: it leaked the internal build cadence into
              the demo. The 1/N progress label carries the only
              user-meaningful position info. Closes Phase 39 audit #2. */}
          <span data-testid="onboarding-progress" style={STYLES.progress}>
            {progressLabel(state)}
          </span>
        </div>
        <h2 style={STYLES.title}>{step.title}</h2>
        <p style={STYLES.body}>{step.body}</p>
        <div style={STYLES.dotRow}>
          {Array.from({ length: ONBOARDING_TOTAL_STEPS }, (_, i) => (
            <span
              key={i}
              data-testid={`onboarding-dot-${i}`}
              style={{
                ...STYLES.dot,
                background:
                  i === state.currentStepIndex
                    ? '#2563eb'
                    : i < state.currentStepIndex
                      ? '#94a3b8'
                      : '#e2e8f0',
              }}
            />
          ))}
        </div>
        <div style={STYLES.actions}>
          <button
            type="button"
            data-testid="onboarding-skip"
            onClick={handleSkip}
            style={STYLES.skipButton}
          >
            Skip tour
          </button>
          <button
            type="button"
            data-testid="onboarding-advance"
            onClick={handleAdvance}
            style={STYLES.advanceButton}
          >
            {state.currentStepIndex + 1 >= ONBOARDING_TOTAL_STEPS ? 'Done' : 'Got it'}
          </button>
        </div>
      </div>
    </div>
  );
}

/** FM-04a Phase 25 D — fade + slide-in keyframes. Respects
 * prefers-reduced-motion so motion-sensitive users see an instant
 * appearance instead. */
const ONBOARDING_TOUR_KEYFRAMES = `
@keyframes fm04a-onboarding-fade-slide-in {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.onboarding-tour-card {
  animation: fm04a-onboarding-fade-slide-in 200ms ease-out;
}
@media (prefers-reduced-motion: reduce) {
  .onboarding-tour-card {
    animation: none;
  }
}
`;

const STYLES: Record<string, CSSProperties> = {
  backdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(15, 23, 42, 0.55)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  card: {
    background: 'white',
    borderRadius: 12,
    padding: '24px 28px',
    maxWidth: 480,
    width: '90%',
    boxShadow: '0 24px 48px rgba(15, 23, 42, 0.18)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  shipped: {
    color: '#475569',
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  progress: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: 500,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 8px',
  },

--- promo ---
// FM-04a Phase 28 D — Advanced-mode auto-promote prompt.
//
// Surfaces ONCE after the onboarding tour ends, when the user is
// still in Basic mode. Offers a single click to switch to Advanced
// (which exposes the threshold filter / section cut / field
// switcher / probe list panel the tour just covered).
//
// Visibility predicate (delegated to onboardingTour.shouldShowAdvancedPrompt):
//   * Tour persisted as dismissed in localStorage (ONBOARDING_LS_KEY = 'true'), AND
//   * Current uiMode === 'basic', AND
//   * ADVANCED_PROMPT_LS_KEY not yet 'true'.
//
// Either button (Switch / Stay) writes the prompt-shown flag and
// hides the promo. The promo is one-shot per browser; bumping the
// localStorage key bumps the version.
//
// Anti-gaming guard D:-1 — once the prompt-shown flag is written,
// the promo never re-surfaces for the same browser, even on full
// page reload + re-mount. Pinned by the storage round-trip test.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';

import {
  createAdvancedPromptStorage,
  createLocalStorageBackedStore,
  shouldShowAdvancedPrompt,
  type AdvancedPromptStorage,
  type OnboardingStorage,
} from '../onboardingTour';
import type { UiMode } from '../uiMode';
import {
  installPolishStyles,
  POLISH_CLASS_ADVANCED_MODE_PROMO,
} from './polishStyles';
import { useFocusTrap } from './useFocusTrap';

export interface AdvancedModePromoProps {
  /** Current UI mode. The promo only shows when this is 'basic'. */
  uiMode: UiMode;
  /** Called when the user clicks "Switch to Advanced". The parent is
   * responsible for actually flipping the mode (so this component
   * stays pure UI). */
  onSwitchToAdvanced: () => void;
  /** Optional injected storage for the prompt-shown flag. Defaults to
   * the localStorage adapter; tests pass a stub. */
  promptStorage?: AdvancedPromptStorage;
  /** Optional injected storage for the onboarding-dismissed flag.
   * Defaults to the localStorage adapter; tests pass a stub. */
  tourStorage?: OnboardingStorage;
  /** When true, surface the promo regardless of the persisted flag.
   * Useful for replaying via a settings affordance (not wired yet). */
  forceShow?: boolean;
  /** When provided, in-session signal that the tour just dismissed.
   * Triggers a re-read of the tour-dismissed flag so the promo
   * surfaces without a page reload. */
  tourDismissedInSession?: boolean;
}

export function AdvancedModePromo({
  uiMode,
  onSwitchToAdvanced,
  promptStorage,
  tourStorage,
  forceShow = false,
  tourDismissedInSession = false,
}: AdvancedModePromoProps) {
  const resolvedPromptStorage = useMemo<AdvancedPromptStorage>(
    () => promptStorage ?? createAdvancedPromptStorage(),
    [promptStorage],
  );
  const resolvedTourStorage = useMemo<OnboardingStorage>(
    () => tourStorage ?? createLocalStorageBackedStore(),
    [tourStorage],
  );

  // Persisted state, re-read on tour-dismiss signal.
  const [tourDismissed, setTourDismissed] = useState<boolean>(() =>
    forceShow ? true : resolvedTourStorage.load(),
  );
  const [promptShown, setPromptShown] = useState<boolean>(() =>
    forceShow ? false : resolvedPromptStorage.load(),
  );

  // FM-04a Phase 28 D — when the tour fires its in-session dismissed
  // signal, refresh both flags so the promo can surface in the same
  // session (no page reload required).
  useEffect(() => {
    if (!tourDismissedInSession) return;
    setTourDismissed(resolvedTourStorage.load());
    setPromptShown(resolvedPromptStorage.load());
  }, [tourDismissedInSession, resolvedTourStorage, resolvedPromptStorage]);

  const visible = shouldShowAdvancedPrompt(uiMode, tourDismissed, promptShown);
  const containerRef = useRef<HTMLDivElement>(null);
  // FM-04a Phase 29 C — install polish styles for the entrance
  // animation class + focus-trap (WCAG 2.4.3).
  useEffect(() => {
    installPolishStyles();
  }, []);
  useFocusTrap({ containerRef, active: visible });

  const markShownAndHide = useCallback(() => {
    resolvedPromptStorage.save(true);
    setPromptShown(true);
  }, [resolvedPromptStorage]);

  const handleSwitch = useCallback(() => {
    markShownAndHide();
    onSwitchToAdvanced();
  }, [markShownAndHide, onSwitchToAdvanced]);

  const handleStay = useCallback(() => {
    markShownAndHide();
  }, [markShownAndHide]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      data-testid="advanced-mode-promo"
      role="dialog"
      aria-label="advanced mode promo"
      aria-live="polite"
      style={STYLES.backdrop}
    >
      <div className={POLISH_CLASS_ADVANCED_MODE_PROMO} style={STYLES.card}>
        <div style={STYLES.header}>
          {/* FM-04a Phase 41.2 — was "Phase 25 C · Phase 28 D" (internal
              build cadence leaked to the user). Replaced with a
              user-meaningful eyebrow. */}
          <span style={STYLES.eyebrow}>Workbench tip</span>
        </div>
        <h2 style={STYLES.title}>Want to see the advanced controls?</h2>
        <p style={STYLES.body}>
          You're currently in <strong>Basic</strong> mode. The tour
          covered the threshold filter, section cut, field-component
          switcher, and probe list — those live in{' '}
          <strong>Advanced</strong>. You can toggle back any time from
          the viewport header.
        </p>
        <div style={STYLES.actions}>
          <button
            type="button"
            data-testid="advanced-mode-promo-stay"
            onClick={handleStay}
            style={STYLES.stayButton}
          >
            Stay in Basic
          </button>
          <button
            type="button"
            data-testid="advanced-mode-promo-switch"
            onClick={handleSwitch}
            style={STYLES.switchButton}
          >
            Switch to Advanced
          </button>
        </div>
      </div>
    </div>
  );
}

const STYLES: Record<string, CSSProperties> = {
  backdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(15, 23, 42, 0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999, // one below the tour
  },
  card: {
    background: 'white',
    borderRadius: 12,
    padding: '22px 26px',
    maxWidth: 440,
    width: '90%',
    boxShadow: '0 18px 36px rgba(15, 23, 42, 0.16)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    marginBottom: 6,
  },
  eyebrow: {
    color: '#475569',
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  title: {
    fontSize: 17,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 10px',
  },
  body: {
    fontSize: 13.5,
    lineHeight: 1.5,
    color: '#334155',
    margin: '0 0 16px',
  },
  actions: {
    display: 'flex',
    gap: 10,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  stayButton: {
    background: 'transparent',
    border: '1px solid #cbd5e1',

exec
/bin/zsh -lc "sed -n '1,220p' frontend/src/components/Sidebar.tsx" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
// FM-04a Phase 19 D — Case sidebar extraction.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Pulled out of App.tsx so the workbench shell stays under ~1900 LOC and
// the case-rail concerns (Cmd-K hint, nav, case gallery, active
// experiment surface, FRD upload) live in one component the test suite
// can drive in isolation. Every data-testid, class name, and inline
// style is preserved verbatim from the App.tsx original so the existing
// visual snapshot and round-3 UX adoption tests do not regress.
//
// EmptyStateCard is mounted when the case-gallery list is empty (Phase
// 18 D primitive adoption, UI agent round-2 finding follow-through).

import type { ChangeEvent } from 'react'
import { Box, FileUp, LayoutDashboard, Zap } from 'lucide-react'
import { EmptyStateCard } from './EmptyStateCard'

export interface SidebarCaseMetadata {
  id: string
  name: string
  description: string
  type: string
  structure: string
  frd_path: string
}

export interface SidebarExperimentRun {
  iteration: number
  value: number
  status: string
}

export interface SidebarExperimentStatus {
  parameter: string
  runs: SidebarExperimentRun[]
}

export interface SidebarCandidateCase {
  caseId: string
  displayLabel: string
}

export interface SidebarProps {
  availableCases: SidebarCaseMetadata[]
  /**
   * FM-04a Phase 20 D — candidate-case roster surfaced inline in the
   * left rail (closes the Phase 19 E UX finding that cylinder-pv was
   * invisible from the Sidebar because it only existed in the
   * candidate registry, not the DB-backed availableCases list).
   * Selecting one fires `onSelectCandidateCase` (a distinct callback
   * so the App can route candidate selection through the
   * `selectedCandidateCaseId` state separately from DB cases).
   */
  candidateCases?: SidebarCandidateCase[]
  selectedCandidateCaseId?: string | null
  onSelectCandidateCase?: (caseId: string) => void
  activeCaseId: string | null
  onSelectCase: (c: SidebarCaseMetadata) => void
  activeExperiment: SidebarExperimentStatus | null
  onFileUpload: (e: ChangeEvent<HTMLInputElement>) => void
  onOpenPalette: () => void
}

export function Sidebar({
  availableCases,
  candidateCases,
  selectedCandidateCaseId,
  onSelectCandidateCase,
  activeCaseId,
  onSelectCase,
  activeExperiment,
  onFileUpload,
  onOpenPalette,
}: SidebarProps) {
  return (
    <aside
      className="glass-sidebar"
      data-testid="case-sidebar"
      style={{
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        borderLeft: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            background: 'var(--accent)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Zap size={24} color="#000" />
        </div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
          Structure<span style={{ color: 'var(--accent)' }}>AI</span>
        </h2>
      </div>

      {/* Phase 18 E (round 3) — discoverable Cmd-K hint (UX agent
          round-2 finding). Click also opens the palette. */}
      <button
        type="button"
        onClick={onOpenPalette}
        data-testid="cmd-k-hint"
        aria-label="Open command palette (Cmd-K)"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          padding: '6px 10px',
          borderRadius: '6px',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          fontSize: '0.75rem',
          textAlign: 'left',
        }}
      >
        <span>Command palette</span>
        <kbd
          style={{
            fontSize: '0.7rem',
            padding: '1px 6px',
            borderRadius: 4,
            background: 'rgba(255,255,255,0.08)',
            fontFamily: 'ui-monospace, Menlo, monospace',
          }}
        >
          ⌘K
        </kbd>
      </button>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button
          className="nav-item active"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px',
            borderRadius: '8px',
            background: 'var(--accent-glow)',
            color: 'var(--accent)',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
            fontWeight: 600,
          }}
        >
          <LayoutDashboard size={18} /> Workbench
        </button>
      </nav>

      <div data-testid="case-gallery">
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            marginBottom: '12px',
            paddingLeft: '12px',
          }}
        >
          Case Gallery
        </div>
        {availableCases.length === 0 ? (
          <div data-testid="case-gallery-empty">
            <EmptyStateCard
              headline="No cases yet"
              body="Drop an FRD file below or load a candidate case from the workbench to populate this gallery."
              glyph="∅"
            />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {availableCases.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelectCase(c)}
                data-testid={`case-item-${c.id}`}
                className={`case-item ${activeCaseId === c.id ? 'active' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  background:
                    activeCaseId === c.id ? 'rgba(255,255,255,0.05)' : 'transparent',
                  color:
                    activeCaseId === c.id ? 'var(--accent)' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.875rem',
                }}
              >
                <Box size={16} /> {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Phase 20 D — candidate-case roster. Surfaces *-candidate
          entries (cylinder-pv, plate-with-hole, cantilever, etc.)
          in the left rail so the Phase 19 E UX finding "cylinder-pv
          is invisible because it lives only in the candidate
          registry" is closed. Only renders when the parent supplies

exec
/bin/zsh -lc "rg -n \"const API_BASE|API_BASE =|import.meta.env|localhost:8000\" frontend/src/App.tsx frontend/src -S | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
frontend/src/App.tsx:117:const API_BASE = "http://localhost:8000/api/v1";
frontend/src/App.tsx:118:const WS_BASE = "ws://localhost:8000/api/v1";
frontend/src/App.tsx:117:const API_BASE = "http://localhost:8000/api/v1";
frontend/src/App.tsx:118:const WS_BASE = "ws://localhost:8000/api/v1";
frontend/src/state/useSensitivityStudy.ts:27:  /** API base URL (e.g. http://localhost:8000/api/v1). */
frontend/src/components/ProjectManager.tsx:30:    fetch('http://localhost:8000/api/v1/projects')
frontend/src/components/ProjectManager.tsx:40:      const resp = await fetch('http://localhost:8000/api/v1/projects', {
frontend/src/components/ChatPanel.tsx:57:      fetch(`http://localhost:8000/api/v1/history/${caseId}`)
frontend/src/components/ChatPanel.tsx:81:      const res = await fetch('http://localhost:8000/api/v1/parse-nl', {
frontend/src/components/MaterialPickerPanel.tsx:72:            'Verify /api/v1/materials/ responds 200 (curl http://localhost:8000/api/v1/materials/).',

exec
/bin/zsh -lc "nl -ba frontend/src/App.tsx | sed -n '1300,1335p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "nl -ba frontend/src/components/ProjectManager.tsx | sed -n '50,120p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
  1300	              onChangeMaterialId={(id) => {
  1301	                const found = FALLBACK_MATERIALS.find((m) => m.id === id);
  1302	                if (found) setSelectedMaterial(found);
  1303	              }}
  1304	            />
  1305	
  1306	            {/* FM-04a Phase 41.2 — flex column so the trust/governance panel is
  1307	                demoted via CSS `order` BELOW the case + 3D viewport (demo-first:
  1308	                lead with the result, not the compliance dashboard). DOM order
  1309	                unchanged; ErrorCard keeps order 0 (red band still first). */}
  1310	            <div style={{ padding: '40px', flex: 1, display: 'flex', flexDirection: 'column' }}>
  1311	            {/* FM-04a Phase 36 B — ErrorCard mounts ABOVE
  1312	                OperatorStatusPanel so a failed user sees the red
  1313	                error band before the trust prose (Phase 35 R3
  1314	                friction point b). */}
  1315	            {uploadError && (
  1316	                <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px', order: 0 }}>
  1317	                    <ErrorCard {...uploadError} />
  1318	                </div>
  1319	            )}
  1320	
  1321	            {/* order: 5 → demoted below the golden-path content (tabs + viewport,
  1322	                order 0). The "Evidence & trust center" is reachable by scroll,
  1323	                not the landing hero. */}
  1324	            <div style={{ order: 5, marginTop: '32px' }}>
  1325	            <OperatorStatusPanel
  1326	              strip={trustStrip}
  1327	              sections={trustSections}
  1328	              goldenSamples={goldenSampleQueue}
  1329	            />
  1330	            </div>
  1331	
  1332	            {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
  1333	            {!activeCaseId && (
  1334	                <div style={{ marginBottom: '24px' }}>
  1335	                    <CaseBrowser cases={FALLBACK_CANDIDATE_CASES} focusedCaseId={selectedCandidateCaseId} onSelectCase={(caseId) => setSelectedCandidateCaseId(caseId)} />

 succeeded in 0ms:
    50	      }
    51	    } catch (err) {
    52	      console.error("Failed to create project", err);
    53	    }
    54	  };
    55	
    56	  return (
    57	    <div className="glass-sidebar" style={rootStyle} data-testid="project-rail">
    58	      <div style={headerStyle}>
    59	        <span className="eyebrow">Projects</span>
    60	        <button
    61	          type="button"
    62	          onClick={() => setIsModalOpen(true)}
    63	          aria-label="Create new project"
    64	          style={addButtonStyle}
    65	        >
    66	          <FolderPlus size={16} />
    67	        </button>
    68	      </div>
    69	
    70	      <div style={listStyle}>
    71	        {projects.map(project => {
    72	          const active = selectedProjectId === project.id;
    73	          return (
    74	            <button
    75	              key={project.id}
    76	              onClick={() => onSelectProject(project.id)}
    77	              className={`case-item${active ? ' active' : ''}`}
    78	              style={{ ...projectButtonStyle, ...(active ? projectButtonActiveStyle : null) }}
    79	            >
    80	              <Folder size={15} style={{ color: active ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0 }} />
    81	              <span style={{ flex: 1, overflow: 'hidden' }}>
    82	                <span style={{ ...projectNameStyle, color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
    83	                  {project.name}
    84	                </span>
    85	                <span style={projectDateStyle}>
    86	                  <Clock size={11} />
    87	                  {new Date(project.created_at).toLocaleDateString()}
    88	                </span>
    89	              </span>
    90	            </button>
    91	          );
    92	        })}
    93	        {projects.length === 0 && (
    94	          <p style={emptyHintStyle}>No projects yet. Create one to organize your analyses.</p>
    95	        )}
    96	      </div>
    97	
    98	      {isModalOpen && (
    99	        <div style={modalOverlayStyle}>
   100	          <div className="glass-panel" style={modalCardStyle}>
   101	            <h3 style={modalTitleStyle}>Create new project</h3>
   102	            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
   103	              <div>
   104	                <label style={fieldLabelStyle}>Project name</label>
   105	                <input
   106	                  value={newProject.name}
   107	                  onChange={e => setNewProject({ ...newProject, name: e.target.value })}
   108	                  style={fieldInputStyle}
   109	                  placeholder="e.g. Truss bridge design"
   110	                />
   111	              </div>
   112	              <div>
   113	                <label style={fieldLabelStyle}>Description</label>
   114	                <textarea
   115	                  value={newProject.description}
   116	                  onChange={e => setNewProject({ ...newProject, description: e.target.value })}
   117	                  style={{ ...fieldInputStyle, height: 96, resize: 'vertical' }}
   118	                  placeholder="Analyze the structural stability of…"
   119	                />
   120	              </div>

exec
/bin/zsh -lc "nl -ba frontend/src/index.css | sed -n '168,182p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   168	    linear-gradient(180deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0) 40%),
   169	    var(--bg-surface);
   170	  backdrop-filter: var(--glass-blur);
   171	  -webkit-backdrop-filter: var(--glass-blur);
   172	  border: 1px solid var(--border);
   173	  border-radius: var(--r-lg);
   174	  box-shadow: var(--elev-2);
   175	}
   176	
   177	.glass-sidebar {
   178	  background: var(--bg-sidebar);
   179	  backdrop-filter: var(--glass-blur);
   180	  -webkit-backdrop-filter: var(--glass-blur);
   181	  border-right: 1px solid var(--border);
   182	}

exec
/bin/zsh -lc "nl -ba frontend/src/App.tsx | sed -n '1320,1350p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
  1320	
  1321	            {/* order: 5 → demoted below the golden-path content (tabs + viewport,
  1322	                order 0). The "Evidence & trust center" is reachable by scroll,
  1323	                not the landing hero. */}
  1324	            <div style={{ order: 5, marginTop: '32px' }}>
  1325	            <OperatorStatusPanel
  1326	              strip={trustStrip}
  1327	              sections={trustSections}
  1328	              goldenSamples={goldenSampleQueue}
  1329	            />
  1330	            </div>
  1331	
  1332	            {/* FM-04a Phase 37 A — CaseBrowser canonical surface, browse mode. */}
  1333	            {!activeCaseId && (
  1334	                <div style={{ marginBottom: '24px' }}>
  1335	                    <CaseBrowser cases={FALLBACK_CANDIDATE_CASES} focusedCaseId={selectedCandidateCaseId} onSelectCase={(caseId) => setSelectedCandidateCaseId(caseId)} />
  1336	                </div>
  1337	            )}
  1338	
  1339	            <div className="tab-pill-bar" style={{ marginBottom: '32px' }}>
  1340	                <TabButton active={activeTab === 'visual'} onClick={() => setActiveTab('visual')} label="3D Scene" icon={<Box size={16} />} />
  1341	                <TabButton active={activeTab === 'report'} onClick={() => setActiveTab('report')} label="Narrative" icon={<Activity size={16} />} />
  1342	                {activeCaseId && <TabButton active={activeTab === 'explore'} onClick={() => setActiveTab('explore')} label="Exploration" icon={<Compass size={16} />} />}
  1343	            </div>
  1344	
  1345	            {activeCaseId && (() => {
  1346	                // FM-04a Phase 37 B — pair BCSetupAdvisorCard with CaseOpenAdvisorCard (3rd advisor surface; closes Dim 4 80-anchor 3-stage sub-bullet).
  1347	                const caseOpenRecord = findCandidateCase(FALLBACK_CANDIDATE_CASES, activeCaseId);
  1348	                return caseOpenRecord ? (
  1349	                    <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'row', flexWrap: 'wrap', gap: '12px' }}>
  1350	                        <CaseOpenAdvisorCard caseRecord={caseOpenRecord} />

exec
/bin/zsh -lc "nl -ba frontend/src/components/ProjectManager.tsx | sed -n '96,106p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
    96	      </div>
    97	
    98	      {isModalOpen && (
    99	        <div style={modalOverlayStyle}>
   100	          <div className="glass-panel" style={modalCardStyle}>
   101	            <h3 style={modalTitleStyle}>Create new project</h3>
   102	            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
   103	              <div>
   104	                <label style={fieldLabelStyle}>Project name</label>
   105	                <input
   106	                  value={newProject.name}

ERROR: Reconnecting... 1/5
codex
The restyling is mostly self-contained, but it introduces a misleading empty-state path in the project rail and a focus-order mismatch caused by CSS-only reordering. Those are user-visible regressions, so the patch should not be considered fully correct as-is.

Full review comments:

- [P2] Gate the empty-project hint on load completion — /Users/Zhuanz/20260408 AI StructureAnalysis/frontend/src/components/ProjectManager.tsx:93-95
  When `GET /api/v1/projects` is still in flight, or if it fails, `projects` remains `[]` and this branch immediately renders “No projects yet…”. On a slow or unavailable backend that turns latency/outages into a false empty state for users who actually have projects, and can prompt duplicate project creation. Please show this copy only after an explicit "loaded with zero results" state, not from `projects.length === 0` alone.

- [P2] Reorder the trust panel in the DOM, not only with CSS — /Users/Zhuanz/20260408 AI StructureAnalysis/frontend/src/App.tsx:1324-1329
  For keyboard-only and screen-reader users, `order: 5` changes only the visual placement here; focus order and reading order still follow the DOM. After this patch the trust-center controls appear below the case browser/viewport, but users navigating by keyboard will still hit that panel first, so the interaction order no longer matches what is on screen.
The restyling is mostly self-contained, but it introduces a misleading empty-state path in the project rail and a focus-order mismatch caused by CSS-only reordering. Those are user-visible regressions, so the patch should not be considered fully correct as-is.

Full review comments:

- [P2] Gate the empty-project hint on load completion — /Users/Zhuanz/20260408 AI StructureAnalysis/frontend/src/components/ProjectManager.tsx:93-95
  When `GET /api/v1/projects` is still in flight, or if it fails, `projects` remains `[]` and this branch immediately renders “No projects yet…”. On a slow or unavailable backend that turns latency/outages into a false empty state for users who actually have projects, and can prompt duplicate project creation. Please show this copy only after an explicit "loaded with zero results" state, not from `projects.length === 0` alone.

- [P2] Reorder the trust panel in the DOM, not only with CSS — /Users/Zhuanz/20260408 AI StructureAnalysis/frontend/src/App.tsx:1324-1329
  For keyboard-only and screen-reader users, `order: 5` changes only the visual placement here; focus order and reading order still follow the DOM. After this patch the trust-center controls appear below the case browser/viewport, but users navigating by keyboard will still hit that panel first, so the interaction order no longer matches what is on screen.
