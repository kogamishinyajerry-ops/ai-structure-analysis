2026-04-25T17:37:29.792324Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-25T17:37:29.792344Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/20260408 AI StructureAnalysis
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc5b7-cac1-7732-b53b-46de2c189f7c
--------
user
# CODE REVIEW REQUEST — PR #25 (stacked on PR #24)

Repo: github.com/kogamishinyajerry-ops/ai-structure-analysis
Project context: AI-Structure-FEA — agentic FEA pipeline; ADR-011 §T2 governance regime.

PR #24 (the base) just got CHANGES_REQUIRED from R1 with two HIGH findings on calibration
ceiling math + state-file enforcement. PR #25 layers branch-protection ENFORCEMENT on top of #24's
calibration math via three layers:
  Layer 1: PR template (.github/PULL_REQUEST_TEMPLATE.md) — reserves Self-pass-rate section
  Layer 2: CI workflow (calibration-cap-check.yml) — extracts claim from PR body, runs --check
  Layer 3: branch protection script (apply_branch_protection.sh) — gh api PUT

ADR-011 §T2 mandatory M-triggers (same as PR #24).

## Review request

Please review the diff below and produce one of:
  APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED

Special focus areas:
  1. Regex correctness in extract_pr_self_pass_rate.py — the body extraction is the trust boundary
  2. CI workflow security: PR body comes from untrusted user; ensure no shell injection
  3. Branch protection script idempotency (gh api PUT)
  4. Coupling correctness: Layer 2 → calls compute_calibration_cap.py from PR #24
  5. M-trigger flag accuracy (claim is M1+M4+M5)
  6. Inheritance of PR #24's CHANGES_REQUIRED issues — does #25's layer 2 amplify the fail-open
     bug (missing state file → ceiling 95% / OPTIONAL → CI passes when it shouldn't)?

## PR metadata
# [ADR-013] Branch protection enforcement (stacked on PR #24)

## Body
## Summary

Three-layer enforcement wrapper around ADR-012 (PR #24, parent in stack). ADR-012 defines a calibration ceiling but has no surface that prevents T1 self-merge under BLOCKING — this PR adds it.

**Stacked on PR #24.** Base = `feature/AI-FEA-ADR-012-calibration-cap`. Diff narrows to ADR-013-only after PR #24 merges and GitHub auto-rebases the base to `main`.

## Three layers

**L1 — PR template** (`.github/PULL_REQUEST_TEMPLATE.md`)
Reserves a `## Self-pass-rate (mechanically derived)` section and forces a Codex gate level pick + ADR-011 §T2 M1-M5 ticks. Surfaces the gate before review.

**L2 — CI workflow** (`.github/workflows/calibration-cap-check.yml`)
On every `pull_request` event, parses the PR body, runs `compute_calibration_cap.py --check <claim>`. CI red on overclaim. 16 unit tests for the extractor.

**L3 — Branch protection** (`scripts/apply_branch_protection.sh`)
Idempotent `gh api PUT` enabling required status checks (`lint-and-test (3.11)` + `calibration-cap-check`), linear history, no force-push, no deletions, conversation resolution. `enforce_admins: false` so T0 retains emergency override; `required_pull_request_reviews: null` because solo-dev (Codex is de facto reviewer).

## Discipline binding

Layer 3's `enforce_admins: false` is a deliberate residual loophole. Closed by explicit T1 contract in ADR-013:

> T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:
> (a) Codex R1=APPROVE on latest commit, OR
> (b) T0 explicit in-conversation authorization.

Violation = P0 procedural failure → retro entry.

## Repo-tier prerequisite

Both classic branch protection and rulesets are paywalled on free private repos. Repo flipped **private → public** on 2026-04-25 to satisfy this. ADR-013 §"Repo-tier prerequisite" documents the alternatives if the project ever needs to go private again.

## Files

**Commit 1 — ADR-013 enforcement (`b6b722d`):**

- `docs/adr/ADR-013-branch-protection-enforcement.md` (~110 lines)
- `.github/PULL_REQUEST_TEMPLATE.md` (~50 lines)
- `.github/workflows/calibration-cap-check.yml` (~55 lines)
- `scripts/extract_pr_self_pass_rate.py` (~50 lines, pure stdlib)
- `tests/test_extract_pr_self_pass_rate.py` (16 unit tests)
- `scripts/apply_branch_protection.sh` (~35 lines, idempotent)

**Commit 2 — STATE.md sync (`7542b05`):**

Per FF-05 R1 lesson ("update STATE.md in the same PR as the change it reflects"), this PR also resyncs `.planning/STATE.md` to current main + ADR-012/013 in-flight. Before this commit, STATE.md was 4 PRs stale (#20/#21/#22/#23 missing) — Codex would have flagged this on R1 as the same stale-state pattern that produced FF-05's R1 CHANGES_REQUIRED.

- `.planning/STATE.md` (44 insertions, 23 deletions)
- New row FF-01a for ADR-011 amendments (PR #23)
- FF-06 row flipped Pending → Merged (PR #22)
- New "Governance ADRs in flight" sub-table for PR #24/25
- 2026-04-25 merge timeline (UTC) added
- Carry-over item #1 + #2 updated to reflect FF-06 merge + ADR-013 in flight
- Carry-over item #6 added: T1 still operates under falsified honor-system until #24 merges (epistemically honest disclosure)

## Self-pass-rate (mechanically derived)

**30%** · BLOCKING · pre-merge Codex MANDATORY · derived from `reports/calibration_state.json` last-5 R1 outcomes (PRs #19-#23, all CR).

ADR-011 §T2 mandatory triggers:
- [x] M1: governance text added (ADR-013)
- [x] M4: governance→enforcement translation (the entire purpose of this PR)
- [x] M5: PR opened while ceiling ≤ 50%

This PR is doubly Codex-mandatory: ceiling regime + M1+M4+M5 triggers.

## Activation sequence (post-merge of this PR)

1. Layers 1 + 2 take effect automatically on subsequent PRs.
2. T0 runs `bash scripts/apply_branch_protection.sh` once → Layer 3 active.
3. From that point: no main-bound PR can merge without both required checks green.

## Why stacked, not standalone

`scripts/compute_calibration_cap.py` lives on PR #24's branch and isn't on `main` yet. The CI workflow (`calibration-cap-check.yml`) shipped in this PR invokes that script. Stacking on PR #24 means the head ref has both files together, so CI on this PR can run end-to-end. After PR #24 merges, this PR's base auto-rebases to `main` and the diff cleanly narrows.

## Test plan

- [ ] **Pre-merge Codex review** (`/codex-gpt54`) — mandatory under both ceiling + M1+M4+M5
- [x] `tests/test_extract_pr_self_pass_rate.py` — 16/16 passing
- [x] Combined targeted suite (extractor + calibration_cap + hf1_path_guard) — 94/94 passing
- [x] Manual: empty body → extractor exits 2; `--check 80` against ceiling 30 → exits 1; `--check 30` → exits 0
- [ ] CI green on this PR (workflow file is new on this PR; runs against PR head — should validate cleanly since the body has the 30% claim)

## Out of scope

- Multi-reviewer / CODEOWNERS (single-author repo, no value yet)
- Signed-commit requirements (would require GPG keypair setup for T1)
- Direct-push restrictions on feature branches (force-push protection on main is enough)
- Auto-revert workflow for merge-bypasses (could land in a follow-up retro after observing actual bypass attempts)

## Related

- Parent: ADR-012 (PR #24, calibration math) — stacked beneath this PR
- Grandparent: ADR-011 (claude-code-takeover, ratified PR #17, amended PR #23)
- T0 Decision: AR-2026-04-25-001 / DEC-T0-2026-04-25-001

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## Stats
+527 -23

## Files
.github/PULL_REQUEST_TEMPLATE.md
.github/workflows/calibration-cap-check.yml
.planning/STATE.md
docs/adr/ADR-013-branch-protection-enforcement.md
scripts/apply_branch_protection.sh
scripts/extract_pr_self_pass_rate.py
tests/test_extract_pr_self_pass_rate.py

## DIFF
diff --git a/.github/PULL_REQUEST_TEMPLATE.md b/.github/PULL_REQUEST_TEMPLATE.md
new file mode 100644
index 0000000..667bf1c
--- /dev/null
+++ b/.github/PULL_REQUEST_TEMPLATE.md
@@ -0,0 +1,61 @@
+<!--
+ADR-013 PR template. Sections marked REQUIRED are validated by CI.
+The "Self-pass-rate" section is mechanically checked against the formula
+in scripts/compute_calibration_cap.py — claims above the current ceiling
+fail CI. Fill it by running:
+
+    python3 scripts/compute_calibration_cap.py --human
+
+and copying the ceiling integer (no `%`) into the section below.
+-->
+
+## Summary
+
+<!-- 1-3 bullets: what changes, why now. -->
+
+-
+-
+
+## Self-pass-rate (mechanically derived) <!-- REQUIRED — ADR-013 -->
+
+<!--
+Replace `<N>` with the integer printed by:
+    python3 scripts/compute_calibration_cap.py
+The CI calibration-cap-check job will fail if your claim exceeds the
+current ceiling. Do not type a number from intuition; ADR-012 forbids it.
+-->
+
+**<N>%** · derived from `reports/calibration_state.json` last-5 R1 outcomes.
+
+Codex pre-merge gate (per ADR-012):
+
+- [ ] BLOCKING (ceiling 30) — must reach Codex R1=APPROVE before merge
+- [ ] MANDATORY non-blocking (ceiling 50) — Codex R1 required, can iterate
+- [ ] RECOMMENDED (ceiling 80) — Codex review strongly suggested
+- [ ] OPTIONAL (ceiling 95) — honor system, Codex at author discretion
+
+ADR-011 §T2 mandatory triggers (M1-M5) override the ceiling-derived gate
+when applicable. Tick any that fire:
+
+- [ ] M1: governance text added/changed (ADRs, FailurePatterns, RETROs)
+- [ ] M2: sign-or-direction math (revert direction, BC orientation, etc.)
+- [ ] M3: HF compliance claim (HF1-HF6 path/zone/process assertions)
+- [ ] M4: governance→enforcement translation (script/CI/hook implementing a rule)
+- [ ] M5: PR opened while ceiling ≤ 50%
+
+## Test plan <!-- REQUIRED -->
+
+- [ ] `pytest tests/`
+- [ ] `ruff check .` and `ruff format --check .`
+- [ ] *(if applicable)* hot-smoke / hand-tested in a real workflow
+- [ ] Codex pre-merge review *(if BLOCKING/MANDATORY or any M1-M5 triggered)*
+
+## Out of scope
+
+<!-- What this PR explicitly does NOT do, to prevent scope creep reviews. -->
+
+-
+
+## Related
+
+- ADR-XXX, FP-XXX, DEC-XXX, AR-XXX as relevant
diff --git a/.github/workflows/calibration-cap-check.yml b/.github/workflows/calibration-cap-check.yml
new file mode 100644
index 0000000..53c5338
--- /dev/null
+++ b/.github/workflows/calibration-cap-check.yml
@@ -0,0 +1,61 @@
+name: Calibration Cap Check
+
+# ADR-013 enforcement workflow. Validates that every PR's
+# "Self-pass-rate" claim does not exceed the mechanical ceiling
+# computed by scripts/compute_calibration_cap.py from
+# reports/calibration_state.json.
+#
+# Runs only on pull_request events (no value on push to main).
+
+on:
+  pull_request:
+    branches: [main]
+    types: [opened, edited, synchronize, reopened]
+
+permissions:
+  contents: read
+  pull-requests: read
+
+jobs:
+  calibration-cap-check:
+    runs-on: ubuntu-latest
+    steps:
+      - uses: actions/checkout@v4
+
+      - name: Set up Python 3.11
+        uses: actions/setup-python@v5
+        with:
+          python-version: "3.11"
+
+      - name: Compute current ceiling
+        id: ceiling
+        run: |
+          set -euo pipefail
+          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
+          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
+          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
+          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
+          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
+          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
+          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
+          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING}"
+
+      - name: Extract Self-pass-rate claim from PR body
+        id: claim
+        env:
+          PR_BODY: ${{ github.event.pull_request.body }}
+        run: |
+          set -euo pipefail
+          if [[ -z "${PR_BODY:-}" ]]; then
+            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
+            exit 1
+          fi
+          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
+          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
+          echo "Claim parsed from PR body: ${CLAIM}%"
+
+      - name: Validate claim does not exceed ceiling
+        run: |
+          set -euo pipefail
+          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
+          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"
diff --git a/.planning/STATE.md b/.planning/STATE.md
index 151a120..712384a 100644
--- a/.planning/STATE.md
+++ b/.planning/STATE.md
@@ -1,7 +1,7 @@
 # AI-Structure-FEA · STATE
 
-> **Stamp:** `post-pivot-foundation-freeze-2026-04-25 · post-#17/#18/#19-merge · pre-FF-06`
-> **Last updated:** 2026-04-25 (after PR #17 → #18 → #19 merge chain; main = `4a64cfd`; Codex review reports archived at `reports/codex_tool_reports/`)
+> **Stamp:** `post-pivot-foundation-freeze-2026-04-25 · post-#17/18/19/20/21/22/23-merge · ADR-012/013-in-flight`
+> **Last updated:** 2026-04-25 (after PR #23 ADR-011 amendments merge; main = `e53b0f7`; PR #24 ADR-012 + PR #25 ADR-013 in flight, both pending Codex R1)
 > **Maintained by:** T1 (Claude Code CLI · Opus 4.7) per ADR-011 §6 Sessions fully traced.
 
 This file is the **repo-side execution status snapshot**. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is the human-facing process SSOT. When they conflict, **git is authoritative**; STATE.md is updated to match git, and Notion is patched from STATE.md.
@@ -13,8 +13,8 @@ This file is the **repo-side execution status snapshot**. Notion 项目控制塔
 | Phase | Status | Notes |
 |-------|--------|-------|
 | Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
-| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (governance baseline merged 2026-04-25; FF-06/07/08 enforcement open through 2026-05-23) | FF-01 (ADR-011), FF-02 (FailurePatterns), and FF-05 (STATE.md) all merged. FF-06/07/08 (path-guard, trailer-check, GS registry) are the remaining gate before Phase 2. |
-| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by FF-06/07/08 (HF1 path-guard, HF5 trailer check, HF3 GS registry) per ADR-011 §Enforcement Maturity. |
+| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (governance baseline merged 2026-04-25; FF-07/08/09 + ADR-012/013 still open) | FF-01 (ADR-011 + amendments), FF-02 (FailurePatterns), FF-05 (STATE.md), FF-06 (HF1 path-guard) all merged. ADR-012 (PR #24) + ADR-013 (PR #25) in Codex-review queue. FF-07/08/09 remain pending. |
+| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by FF-07/08/09 (HF5 trailer check, HF3 GS registry, README↔ADR-011 sync) per ADR-011 §Enforcement Maturity. |
 | Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |
 
 ---
@@ -24,36 +24,52 @@ This file is the **repo-side execution status snapshot**. Notion 项目控制塔
 | Task | Status | Branch | Commit | Notes |
 |------|--------|--------|--------|-------|
 | FF-01 — ADR-011 Pivot baseline | ✅ Merged (PR #17 · 2026-04-25) · **R5 APPROVE** | (deleted post-merge) | `34722ea` (squash) | 5-round Codex arc; reports landed at `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. |
+| FF-01a — ADR-011 amendments AR-2026-04-25-001 | ✅ Merged (PR #23 · 2026-04-25 12:06Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `e53b0f7` (squash) | T2 rewording (Codex anti-shenanigans backstop + M1-M5 trigger taxonomy), §HF2 subagent split, §HF1 zone narrowing, §Enforcement Maturity post-FF-06 update, §Known Gaps ADR-012/013 number reassignment. R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit `e96904d`. |
 | FF-01b — Notion Decisions DS sync | ✅ Done | (no branch — Notion API write) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. Discovered DS schema gap (missing `Branch`/`Session Batch`/`ADR Link`); see ADR-011 Risk #3. |
-| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged (PR #18 · 2026-04-25) | (deleted post-merge) | `77e6813` (squash) | 3 FPs (FP-001/002/003); recommends GS-001/002/003 → `insufficient_evidence`. Codex R1 (CHANGES_REQUIRED, 1 HIGH + 3 MEDIUM) → R2 APPROVE. |
+| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged (PR #18 · 2026-04-25) | (deleted post-merge) | `77e6813` (squash) | 3 FPs (FP-001/002/003); recommends GS-001/002/003 → `insufficient_evidence`. R1 (CR, 1 HIGH + 3 MEDIUM) → R2 APPROVE. |
 | FF-03 — Routing v6.2 doc (supersede Antigravity) | ⚪ Pending | — | — | Lower priority: ADR-011 already encodes the routing; this would be a thin pointer doc. |
 | FF-04 — Onboarding manual (Claude Code edition) | ⚪ Pending | — | — | New-contributor entry doc. |
-| FF-05 — STATE.md | ✅ Merged (PR #19 · 2026-04-25) | (deleted post-merge) | `4a64cfd` (squash) | Adopts `.planning/` directory convention from cfd-harness-unified. Codex R1 (CHANGES_REQUIRED, 1 HIGH stale-state + 1 MEDIUM ADR-012/013 inventions) → R2 APPROVE. |
-| FF-06 — pre-commit path-guard for HF1 forbidden zone | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
-| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Same hard deadline. |
+| FF-05 — STATE.md | ✅ Merged (PR #19 · 2026-04-25) | (deleted post-merge) | `4a64cfd` (squash) | Adopts `.planning/` directory convention from cfd-harness-unified. R1 (CR, 1 HIGH stale-state + 1 MEDIUM ADR-012/013 inventions) → R2 APPROVE. |
+| FF-06 — pre-commit path-guard for HF1 forbidden zone | ✅ Merged (PR #22 · 2026-04-25 10:43Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `ac98fc3` (squash) | `scripts/hf1_path_guard.py` + `tests/test_hf1_path_guard.py` (30 tests). R1 returned 1 BLOCKER (rename/delete bypass via `pass_filenames` default) + 2 SHOULD_FIX (HF1.6 over-block, override audit). Fixed via `--all-files` flag and HF1.6 scoping. |
+| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
 | FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ⚪ Pending | — | — | Same hard deadline. |
 | FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ⚪ Pending | — | — | Reconcile partial overlap noted in ADR-011 §Cross-References. |
 
+### Governance ADRs in flight
+
+| ADR | Status | PR | Branch | Notes |
+|-----|--------|----|--------|-------|
+| **ADR-012 — Calibration cap for T1 self-pass-rate** | 🟡 OPEN, CI green, awaiting Codex R1 | **#24** | `feature/AI-FEA-ADR-012-calibration-cap` | Replaces RETRO-V61-001's honor-system with a mechanical 5-PR rolling-window ceiling. Bootstrap: 5/5 CR → ceiling 30%, BLOCKING. 42 unit tests passing. Self-applies its own gate — must reach R1=APPROVE before merge. |
+| **ADR-013 — Branch protection enforcement** | 🟡 OPEN, stacked on PR #24, awaiting Codex R1 | **#25** | `feature/AI-FEA-ADR-013-branch-protection` | 3-layer wrapper around ADR-012: PR template + CI `--check` workflow + `gh api` protection script. M1+M4+M5 triggers fire. Repo flipped private→public on 2026-04-25 to access protection API. CI doesn't run on this PR until #24 merges and base auto-rebases. |
+
 ---
 
-## Governance-chain branches (post-#17/#18/#19 merge · 2026-04-25)
+## Repo state
+
+`main == origin/main == e53b0f7` (post #17 + #18 + #19 + #20 + #21 + #22 + #23).
+
+Merge timeline 2026-04-25 (UTC):
 
 ```
-chore/post-merge-cleanup-state-and-codex-archive   (this PR — STATE.md self-update lag fix + Codex log archive)
-feature/AI-FEA-S2.1-02-notion-sync-contract-align  (origin tracked; WIP stashed in stash@{0} as of 2026-04-25 pivot session, not touched by FF-* work)
+07:56  #17  ADR-011 baseline                               (FF-01)
+07:56  #18  FailurePattern attribution                     (FF-02)
+07:56  #19  STATE.md seed                                  (FF-05)
+08:33  #20  Revert direct-push 815945c                     (governance hygiene)
+10:26  #21  Post-merge cleanup — STATE.md + Codex archive  (chore)
+10:43  #22  HF1 path-guard pre-commit                      (FF-06)
+12:06  #23  ADR-011 amendments AR-2026-04-25-001           (FF-01a)
 ```
 
-`main == origin/main == 4a64cfd` (after PR #20 revert + PR #17 ADR-011 + PR #18 FF-02 + PR #19 FF-05 merges).
-
 ## Open PRs (governance-chain · this session)
 
 | PR | Branch | Status |
 |----|--------|--------|
-| (this) | `chore/post-merge-cleanup-state-and-codex-archive` | OPEN · post-merge housekeeping; PR self-references STATE.md update — see commit message for the self-update-lag pattern |
+| #24 | `feature/AI-FEA-ADR-012-calibration-cap` | OPEN · CI green · CLEAN/MERGEABLE · awaiting Codex R1 (BLOCKING gate self-applied) |
+| #25 | `feature/AI-FEA-ADR-013-branch-protection` | OPEN · stacked on #24 (base will auto-rebase to main on #24 merge) · awaiting Codex R1 |
 
 ## Open PRs (Phase 1 sprint work · pre-pivot, not in governance chain)
 
-The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. They are orthogonal to the Phase 1.5 governance pivot (PRs #17-#21) and are owned by their original sprint authors. STATE.md tracks them here for repo-wide situational awareness; **disposition (rebase / close / merge under ADR-006) is not in scope for the FF-* work** and will be handled separately.
+The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. They are orthogonal to the Phase 1.5 governance pivot and are owned by their original sprint authors. STATE.md tracks them here for repo-wide situational awareness; **disposition (rebase / close / merge under ADR-006) is not in scope for the FF-* work** and will be handled separately.
 
 | PR | Branch | Title |
 |----|--------|-------|
@@ -64,7 +80,7 @@ The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. Th
 | #15 | `feature/AI-FEA-P1-06b-wire-linter-solver` | AI-FEA-P1-06b: wire Gate-Solve linter into Solver node (stacked on #14) |
 | #16 | `feature/AI-FEA-P1-05-reviewer-fault-injection` | AI-FEA-P1-05: Reviewer fault-injection baseline + ADR-004 mirror |
 
-**Carry-over flag:** these PRs predate ADR-011 and therefore predate the T0/T1/T2 routing contract. Any rebase onto current main must (a) inherit ADR-011 § HF1-HF5 zoning, (b) decide whether their original review trail is sufficient or whether re-review under v6.2 is required. This is a separate decision from FF-06/07/08.
+**Carry-over flag:** these PRs predate ADR-011 and therefore predate the T0/T1/T2 routing contract. Any rebase onto current main must (a) inherit ADR-011 §HF1-HF5 zoning, (b) decide whether their original review trail is sufficient or whether re-review under v6.2 is required. This is a separate decision from FF-07/08/09 + ADR-012/013.
 
 ---
 
@@ -77,9 +93,12 @@ The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. Th
 | ADR-005 | Live | (well_harness Notion writeback) |
 | ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
 | ADR-010 | Live | (notion_sync contract — being aligned in S2.1-02) |
-| **ADR-011** | **Accepted (R5 APPROVE) · merged in main** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` |
+| **ADR-011** | **Accepted (R5 APPROVE) · merged + amended (R1 CR → R2 APPROVE) on main** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` (with AR-2026-04-25-001 amendments) |
+| **ADR-012** | **Drafted; awaiting Codex R1 on PR #24** | `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` (in `feature/AI-FEA-ADR-012-calibration-cap`) |
+| **ADR-013** | **Drafted; awaiting Codex R1 on PR #25** | `docs/adr/ADR-013-branch-protection-enforcement.md` (in `feature/AI-FEA-ADR-013-branch-protection`) |
+
+Two **further follow-up ADRs (numbers ADR-014 and beyond, not yet drafted)** are proposed in FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps:
 
-Two **follow-up ADRs (numbers TBD; not yet drafted)** are proposed in FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps:
 - "Golden-sample triplet contract" (README + `expected_results.json` + theory script as one calculator)
 - "Comparison-validity precondition for `REFERENCE_MISMATCH` retry routing"
 
@@ -89,10 +108,12 @@ These will be assigned numbers when drafted; do not pre-reserve ADR IDs.
 
 ## Carry-overs that ADR-011 R5 APPROVE does **not** make go away
 
-1. HF1 / HF5 enforcement is honor-system today (only `ruff` pre-commit + lint+pytest CI exist). Auto-detection is FF-06/07/08, deadline **2026-05-23**.
-2. `main` branch protection rules, PR review state machine, subagent failure SOP — all deferred to follow-up ADR candidates (numbers TBD; per ADR-011 §Known Gaps).
-3. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
-4. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.
+1. HF1 hard-stop is now enforced via FF-06 pre-commit (PR #22 ✅); the **PR-protected zone** (`docs/adr/`, `docs/governance/`, `.github/workflows/**`) relies on Codex M1 + branch protection (ADR-013 in flight, PR #25). HF5 (commit-trailer) auto-detection remains FF-07. Hard deadline **2026-05-23**.
+2. Branch protection rules + PR review state machine — proposed in ADR-013 (PR #25). Layer 3 activation (`bash scripts/apply_branch_protection.sh`) is a one-shot T0 action post-#25-merge.
+3. Subagent failure SOP — still deferred to a future ADR (number TBD).
+4. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
+5. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.
+6. Self-pass-rate honor-system (RETRO-V61-001) is empirically falsified by session 2026-04-25 (T1 estimated 80-95% on 5 PRs that all returned R1=CR). ADR-012 (PR #24) replaces it with a mechanical ceiling. Until #24 merges, T1 still operates under the falsified honor-system — i.e., this PR (#25) and the next few must explicitly cite the empirical 0/5 R1-pass-rate when self-rating.
 
 ---
 
@@ -106,4 +127,4 @@ Update STATE.md whenever:
 - A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
 - The `Last updated` stamp must change in the same commit.
 
-Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here.
+**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.
diff --git a/docs/adr/ADR-013-branch-protection-enforcement.md b/docs/adr/ADR-013-branch-protection-enforcement.md
new file mode 100644
index 0000000..ed6c9a6
--- /dev/null
+++ b/docs/adr/ADR-013-branch-protection-enforcement.md
@@ -0,0 +1,109 @@
+# ADR-013: Branch protection enforcement for the calibration cap
+
+- **Status:** Accepted
+- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
+- **Date:** 2026-04-25
+- **Related:** ADR-011 (parent), ADR-012 (calibration math — sibling), DEC-T0-2026-04-25-001 (Notion record)
+- **Branch:** `feature/AI-FEA-ADR-013-branch-protection`
+- **Repo-tier prerequisite:** repo must be **public** OR on **GitHub Pro** (required for branch protection + rulesets API). Repo was flipped from private→public on 2026-04-25 to satisfy this.
+
+---
+
+## Context
+
+ADR-012 defines a *calibration ceiling* (mechanical, derived from rolling 5-PR Codex R1 outcomes). That math is meaningless if T1 can self-merge under any ceiling — including 30%/BLOCKING. Session 2026-04-25 demonstrated empirically that T1 wrote `95%` self-estimates five times in a row while Codex was actively returning CHANGES_REQUIRED on each PR. The honor-system has zero enforcement surface; the calibration cap needs a wrapper that physically prevents T1 from merging when the gate is BLOCKING and that surfaces the gate's claim-vs-ceiling check on every PR.
+
+ADR-013 is that wrapper.
+
+## Decision
+
+Enforce ADR-012's gate via three concentric layers:
+
+### Layer 1 — PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
+
+Every PR is opened from a template that:
+
+- Reserves a section labeled `## Self-pass-rate (mechanically derived)`.
+- Instructs the author to fill it from `python3 scripts/compute_calibration_cap.py`'s output, **never from intuition**.
+- Forces the author to tick exactly one Codex pre-merge gate level (BLOCKING / MANDATORY / RECOMMENDED / OPTIONAL).
+- Forces the author to tick any ADR-011 §T2 M1-M5 mandatory triggers that fire (independent override).
+- Includes a `## Test plan` section validated by reviewers.
+
+The template is only a *prompt*; the actual enforcement is in Layer 2.
+
+### Layer 2 — CI workflow (`.github/workflows/calibration-cap-check.yml`)
+
+Triggered on every `pull_request` event (`opened` / `edited` / `synchronize` / `reopened`):
+
+1. Computes the current ceiling via `compute_calibration_cap.py`.
+2. Extracts the claimed ceiling from the PR body via `scripts/extract_pr_self_pass_rate.py`.
+3. Runs `compute_calibration_cap.py --check <claim>` — exits non-zero if the claim exceeds the ceiling.
+
+Result: a PR whose body claims 80% while the formula says 30% fails CI. The author cannot fix this by editing the body to a higher number — only by either correcting downward to ≤ ceiling or by adding R1=APPROVE entries to `calibration_state.json` (which requires merging clean PRs first, which require Codex review, which is the whole point).
+
+### Layer 3 — GitHub branch protection (`scripts/apply_branch_protection.sh`)
+
+A protection ruleset on `main` requires:
+
+- **`required_status_checks`** = `["lint-and-test (3.11)", "calibration-cap-check"]` with `strict: true` (PR must be up-to-date with main before merge).
+- **`required_linear_history`** = `true` — squash-only style, no merge commits.
+- **`allow_force_pushes`** = `false`, **`allow_deletions`** = `false` — protect against accidental destruction of main.
+- **`required_conversation_resolution`** = `true` — Codex review threads must be resolved.
+- **`enforce_admins`** = `false` — T0 (the human admin) retains emergency override. Justification: solo-developer setup; without admin override, any CI infrastructure breakage would brick the repo. ADR-013's discipline is procedural, not coercive at the admin level.
+- **`required_pull_request_reviews`** = `null` — solo-dev; Codex (via the M1-M5 + ceiling gate) is the de facto reviewer rather than a human approver. Adding a human-required-review on a single-author repo would just stamp the author's own approvals.
+
+### Discipline binding (T1 contract)
+
+The gate cannot mechanically prevent admin-bypass merges by T1 acting through the user's authenticated `gh` CLI. This residual loophole is closed by **discipline**:
+
+> **T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:**
+> **(a) Codex Round 1 returned `APPROVE` (or `APPROVE_WITH_NITS` with all nits resolved) on the latest commit, OR**
+> **(b) T0 (the human) explicitly authorizes the merge in writing in the conversation, citing the BLOCKING state.**
+
+Any T1 merge that violates this contract is a P0 procedural failure and triggers a retro entry per RETRO cadence rules. Layer 1 + 2 surface the BLOCKING state in CI and PR template so T1 cannot plausibly miss it; Layer 3 makes the merge *physically possible* only via deliberate admin-bypass *that T1 has no business invoking*.
+
+## Implementation contract
+
+| File | Purpose |
+|---|---|
+| `.github/PULL_REQUEST_TEMPLATE.md` | Layer 1 — PR template |
+| `.github/workflows/calibration-cap-check.yml` | Layer 2 — CI claim-vs-ceiling check |
+| `scripts/extract_pr_self_pass_rate.py` | Layer 2 — PR body parser (16 unit tests) |
+| `scripts/apply_branch_protection.sh` | Layer 3 — idempotent protection setup |
+| `docs/adr/ADR-013-branch-protection-enforcement.md` | This doc |
+
+## Activation sequence
+
+1. **Land this PR via Codex R1=APPROVE.** Layers 1 and 2 take effect on merge (template applies to subsequent PRs; CI workflow runs on subsequent PRs).
+2. **T0 runs** `bash scripts/apply_branch_protection.sh` once after merge. Layer 3 takes effect immediately; from this moment forward, no merge to main can land without `lint-and-test (3.11)` + `calibration-cap-check` both green.
+3. **Subsequent PRs** open from the new template; the calibration-cap-check workflow validates each automatically.
+
+The bootstrap PR for ADR-013 itself (this PR) is NOT subject to Layer 2 yet because the workflow file lands as part of this PR — GitHub doesn't run workflow files that don't exist on the base branch yet. ADR-012's PR (#24) is also NOT subject to Layer 2 for the same reason. **Both PRs land under Layer 0 (no enforcement) but are required by ADR-012/AR-2026-04-25-001 §1 to reach Codex R1=APPROVE before merge** — the discipline binding above applies retroactively to the same session that authored these ADRs.
+
+## Consequences
+
+**Intended:**
+
+- T1's mechanical ceiling becomes physically enforced at PR-merge time once Layer 3 is on. CI red blocks merge.
+- Layer 1 + 2 produce a clear paper trail: every PR body declares a ceiling; CI validates it; the validation result is part of the PR's check history.
+- Layer 3 prevents accidental force-push or deletion of main (defense against the same class of error that produced PR #20's revert).
+- The discipline binding turns the residual admin-bypass into a documented retro-eligible event rather than a silent loophole.
+
+**Acknowledged:**
+
+- `enforce_admins: false` means a determined or careless admin can bypass everything. This is a deliberate trade-off for solo-dev recoverability; revisit if/when the project grows to multi-author.
+- Layer 3 doesn't run until after this PR merges (chicken-and-egg). The first two ADR PRs (#24 and this one) ride on Layer 0 = nothing. ADR-012/013 is therefore a *prospective* gate, not retroactive.
+- The CI check uses GitHub's `pull_request.body` field, which can be edited freely. An author could in principle merge a PR, then edit the body to game future tooling. The state file (Layer 0 of ADR-012) is the actual source of truth, not the body claim. The body claim is just a checksum.
+- Repo had to be made public to access protection APIs on the free tier. Future-proof: if the project ever needs to go private again, options are (a) GitHub Pro, (b) move to GitLab (free private branch protection), (c) drop Layer 3 and rely on Layer 1 + 2 + discipline alone.
+
+**Out of scope:**
+
+- Multi-reviewer / CODEOWNERS enforcement (single-author repo, no value yet).
+- Signed-commit requirements (would block T1's automated commits without GPG keypair setup).
+- Blocking direct push to feature branches (low value; force-push protection on main is enough).
+
+## Open follow-ups
+
+- After 10 post-ADR-013 PRs, audit: did the `calibration-cap-check` job ever fail? Did it ever falsely pass? Sample 3 PR bodies to confirm the template was followed.
+- Consider extending the workflow to also scrape ADR-011 §T2 M1-M5 checkboxes; if any is ticked, require a `Codex-Approved-By:` trailer in the merge commit.
+- If a future PR rewords the `Self-pass-rate` heading, add a heading-rename safety check to `extract_pr_self_pass_rate.py` (currently tolerates `Self-pass-rate` and `Self pass rate` only).
diff --git a/scripts/apply_branch_protection.sh b/scripts/apply_branch_protection.sh
new file mode 100755
index 0000000..fddb340
--- /dev/null
+++ b/scripts/apply_branch_protection.sh
@@ -0,0 +1,46 @@
+#!/usr/bin/env bash
+# ADR-013: applies the protection ruleset to main.
+#
+# Idempotent — re-running with the same settings is a no-op.
+# Requires: `gh` authenticated as a user with admin permission on the repo.
+#
+# Settings rationale (see ADR-013 §"Protection ruleset"):
+# - required_status_checks: lint-and-test (3.11) + calibration-cap-check
+# - enforce_admins: false        (T0 retains emergency override)
+# - required_pull_request_reviews: null  (solo-dev — Codex is the de facto reviewer)
+# - allow_force_pushes: false
+# - allow_deletions: false
+# - required_linear_history: true        (squash-only style)
+# - lock_branch: false
+# - required_conversation_resolution: true
+
+set -euo pipefail
+
+REPO="${1:-kogamishinyajerry-ops/ai-structure-analysis}"
+BRANCH="${2:-main}"
+
+echo "Applying branch protection to $REPO:$BRANCH ..."
+
+gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
+  --input - <<'JSON'
+{
+  "required_status_checks": {
+    "strict": true,
+    "contexts": ["lint-and-test (3.11)", "calibration-cap-check"]
+  },
+  "enforce_admins": false,
+  "required_pull_request_reviews": null,
+  "restrictions": null,
+  "required_linear_history": true,
+  "allow_force_pushes": false,
+  "allow_deletions": false,
+  "required_conversation_resolution": true,
+  "lock_branch": false,
+  "allow_fork_syncing": true
+}
+JSON
+
+echo
+echo "Protection applied. Verifying..."
+gh api "repos/$REPO/branches/$BRANCH/protection" \
+  --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
diff --git a/scripts/extract_pr_self_pass_rate.py b/scripts/extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..31c463c
--- /dev/null
+++ b/scripts/extract_pr_self_pass_rate.py
@@ -0,0 +1,61 @@
+"""Extract the claimed Self-pass-rate from a PR body.
+
+The PR template (per ADR-013) reserves a section labeled
+"Self-pass-rate (mechanically derived)" whose first line contains the
+claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
+integer so CI can pass it to compute_calibration_cap.py --check.
+
+Usage:
+    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
+    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
+    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py
+
+Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
+no claim found in the body.
+"""
+
+from __future__ import annotations
+
+import re
+import sys
+
+# Match the Self-pass-rate section heading then the first \d+% within
+# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
+# `### Self-pass-rate`, with-or-without trailing parenthetical.
+_HEADING_RE = re.compile(
+    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
+)
+_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")
+
+
+def extract_claim(body: str) -> int | None:
+    """Return the integer claim (0-100) or None if not found."""
+    heading = _HEADING_RE.search(body)
+    if not heading:
+        return None
+    tail = body[heading.end() : heading.end() + 600]
+    m = _PERCENT_RE.search(tail)
+    if not m:
+        return None
+    val = int(m.group(1))
+    if not 0 <= val <= 100:
+        return None
+    return val
+
+
+def main(argv: list[str]) -> int:
+    body = sys.stdin.read()
+    claim = extract_claim(body)
+    if claim is None:
+        print(
+            "ERROR: PR body does not contain a 'Self-pass-rate' section "
+            "with a `N%` claim. ADR-013 requires this section in every PR.",
+            file=sys.stderr,
+        )
+        return 2
+    print(claim)
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_extract_pr_self_pass_rate.py b/tests/test_extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..3aa0d70
--- /dev/null
+++ b/tests/test_extract_pr_self_pass_rate.py
@@ -0,0 +1,145 @@
+"""Tests for scripts/extract_pr_self_pass_rate.py (ADR-013)."""
+
+from __future__ import annotations
+
+import sys
+from pathlib import Path
+
+import pytest
+
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+_SCRIPTS_DIR = _REPO_ROOT / "scripts"
+if str(_SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(_SCRIPTS_DIR))
+
+
+def _load():
+    import extract_pr_self_pass_rate  # type: ignore[import-not-found]
+
+    return extract_pr_self_pass_rate
+
+
+@pytest.fixture(scope="module")
+def mod():
+    return _load()
+
+
+# ---------------------------------------------------------------------------
+# Happy paths
+# ---------------------------------------------------------------------------
+
+
+def test_h2_with_parenthetical_bold_percent(mod):
+    body = """## Summary
+Stuff.
+
+## Self-pass-rate (mechanically derived)
+
+**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in state file.
+
+## Test plan
+- [x] tests
+"""
+    assert mod.extract_claim(body) == 30
+
+
+def test_h2_plain_percent(mod):
+    body = "## Self-pass-rate\n\n80%\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_h3_heading(mod):
+    body = "### Self-pass-rate\n95%\n"
+    assert mod.extract_claim(body) == 95
+
+
+def test_heading_with_space(mod):
+    """Tolerate 'Self pass rate' with spaces."""
+    body = "## Self pass rate\n\n50%\n"
+    assert mod.extract_claim(body) == 50
+
+
+def test_picks_first_percent_after_heading(mod):
+    body = "## Self-pass-rate\n\n**80%** baseline (raised from 50% earlier).\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_zero_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n0%\n"
+    assert mod.extract_claim(body) == 0
+
+
+def test_one_hundred_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n100%\n"
+    assert mod.extract_claim(body) == 100
+
+
+# ---------------------------------------------------------------------------
+# Unhappy paths
+# ---------------------------------------------------------------------------
+
+
+def test_no_heading_returns_none(mod):
+    body = "## Summary\n\nWe have 95% confidence here.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_heading_without_percent_returns_none(mod):
+    body = "## Self-pass-rate\n\nTBD — script will fill in.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_above_100_rejected(mod):
+    body = "## Self-pass-rate\n\n150%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_h1_heading_rejected(mod):
+    """Single-# heading must NOT match (PR body sections are h2+)."""
+    body = "# Self-pass-rate\n\n95%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_inline_mention_rejected(mod):
+    """Mentioning self-pass-rate in prose must not match."""
+    body = "## Summary\n\nThe self-pass-rate is 95% trust me bro.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_empty_body_returns_none(mod):
+    assert mod.extract_claim("") is None
+
+
+def test_percent_too_far_after_heading_ignored(mod):
+    """Search window is bounded so a wandering paragraph doesn't pollute."""
+    body = "## Self-pass-rate\n\n" + ("filler. " * 200) + "95%\n"
+    assert mod.extract_claim(body) is None
+
+
+# ---------------------------------------------------------------------------
+# CLI
+# ---------------------------------------------------------------------------
+
+
+def test_cli_prints_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Self-pass-rate\n\n30%\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 0
+    assert captured.out.strip() == "30"
+
+
+def test_cli_exits_2_when_no_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Summary\n\nNo claim here.\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 2
+    assert "Self-pass-rate" in captured.err
+
+
+class _StdinShim:
+    def __init__(self, text: str):
+        self._text = text
+
+    def read(self) -> str:
+        return self._text

codex
Reviewing PR #25 as a stacked review on top of PR #24. I’m checking the repo state, the base calibration-cap code from #24, and the new extractor/workflow/protection layers with emphasis on trust-boundary parsing and fail-open inheritance.
exec
/bin/zsh -lc 'rg -n "ai-structure-analysis|AI StructureAnalysis|ADR-012|ADR-013|compute_calibration_cap|calibration_state|extract_pr_self_pass_rate" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
396:scope: Operate the `ai-structure-analysis` PR stack under ADR-006, sync Notion after each merge, and stop correctly at a visual/demo milestone even when CI is green.
397:applies_to: cwd=/Users/Zhuanz/20260408 AI StructureAnalysis; reuse_rule=safe for this repo’s ADR-006 + Notion/GitHub control-plane workflow, but PR numbers and gate artifacts are rollout-specific.
403:- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, merged PRs #1-#8 under ADR-006)
413:- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, CI passed but rollout intentionally stopped for human visual verification)
423:- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, review note appended without changing verdict)

exec
/bin/zsh -lc "rg --files /Users/Zhuanz/20260408\\ AI\\ StructureAnalysis | rg \"compute_calibration_cap|calibration_state|extract_pr_self_pass_rate|calibration-cap-check|apply_branch_protection|PULL_REQUEST_TEMPLATE|ADR-012|ADR-013|STATE.md|test_extract_pr_self_pass_rate|test_compute_calibration_cap|hf1_path_guard\"" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/Users/Zhuanz/20260408 AI StructureAnalysis/scripts/hf1_path_guard.py
/Users/Zhuanz/20260408 AI StructureAnalysis/tests/test_hf1_path_guard.py

exec
/bin/zsh -lc 'pwd && git status --short && git branch --show-current && git log --oneline --decorate -5' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/Users/Zhuanz/20260408 AI StructureAnalysis
feature/AI-FEA-P1-04b-cli-json-symmetry
e185ba0 (HEAD -> feature/AI-FEA-P1-04b-cli-json-symmetry, origin/feature/AI-FEA-P1-04b-cli-json-symmetry) [P1-04b] query_cli + advise_cli: add --json output mode (symmetry with publish_cli)
85e26f3 (origin/feature/AI-FEA-P1-08-publish-cli-json, feature/AI-FEA-P1-08-publish-cli-json) [P1-08] preflight_publish_cli: add --json output mode
cde1036 (origin/feature/AI-FEA-P1-04b-coverage-audit, feature/AI-FEA-P1-04b-coverage-audit) [P1-04b] RAG corpus coverage audit — disk vs registry parity check
c6b7e91 (origin/feature/AI-FEA-P1-08-preflight-publish-cli, feature/AI-FEA-P1-08-preflight-publish-cli) [P1-08] Preflight publish CLI — operator-facing post/upsert tool
dc376f0 (origin/feature/AI-FEA-P1-08-preflight-upsert, feature/AI-FEA-P1-08-preflight-upsert) [P1-08] Preflight publisher upsert mode — find prior comment + PATCH

codex
The current checkout is an unrelated feature branch, so I’m pulling the stacked review branches and the base calibration script directly from git before judging coupling or inherited fail-open behavior.
exec
/bin/zsh -lc "sed -n '390,430p' /Users/Zhuanz/.codex/memories/MEMORY.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
- Symptom: `codex-builder` keeps failing during live validation -> cause: Codex usage-limit/reset and provider instability in this environment -> fix: stop chasing builder-primary routes, keep Codex as fallback until account state is healthy, and pin the live path to the most immediately usable local route [Task 2]
- Symptom: Codex stderr is noisy during smoke tests -> cause: malformed skill files under `~/.agents/skills/...` missing YAML frontmatter -> fix: treat that as local skills-tree cleanup debt, not the main OpenClaw blocker [Task 1]
- Symptom: configuration looks valid but the stack still is not safe to use -> cause: only schema validation was checked -> fix: require sentinel smoke tests and preserve the resulting `HANDOFF.md`, `STATUS.json`, and `SMOKE_TESTS.md` artifacts [Task 1]

# Task Group: AI-FEA autonomous merges and Demo Gate handling

scope: Operate the `ai-structure-analysis` PR stack under ADR-006, sync Notion after each merge, and stop correctly at a visual/demo milestone even when CI is green.
applies_to: cwd=/Users/Zhuanz/20260408 AI StructureAnalysis; reuse_rule=safe for this repo’s ADR-006 + Notion/GitHub control-plane workflow, but PR numbers and gate artifacts are rollout-specific.

## Task 1: Merge ADR-006-approved PR stack and sync Notion task/session records

### rollout_summary_files

- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, merged PRs #1-#8 under ADR-006)

### keywords

- ADR-006, Reviewer Agent Verdict=Accept 且 CI 全绿 → 你直接 merge, update-branch, sync_well_harness_approvals.py, Notion sync, PR stack, retarget to main, Clean Pass

## Task 2: Build `tests/test_smoke_e2e.py` and hold PR #9 at Demo Gate

### rollout_summary_files

- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, CI passed but rollout intentionally stopped for human visual verification)

### keywords

- tests/test_smoke_e2e.py, Demo Gate, results.vtp 在 ParaView 里打得开、且云图合理, manifest.yaml, git_sha, tool_versions, seeds, CalculiX 是主求解器, ccx missing, monkeypatch agents.solver.run_solve, PR #9

## Task 3: Keep gate-note append separate from verdict/merge

### rollout_summary_files

- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, review note appended without changing verdict)

### keywords

- Review Summary, verdict unchanged, gate review note, AI-FEA-P0-10, results.vtp not visually validated, manifest contract incomplete

## User preferences


exec
/bin/zsh -lc 'git remote -v && git branch -a | rg "ADR-012|ADR-013|main|feature/AI-FEA-ADR"' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (fetch)
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (push)
  feature/AI-FEA-ADR-012-calibration-cap
  feature/AI-FEA-ADR-013-branch-protection
  main
  remotes/origin/HEAD -> origin/main
  remotes/origin/feature/AI-FEA-ADR-012-calibration-cap
  remotes/origin/feature/AI-FEA-ADR-013-branch-protection
  remotes/origin/main

codex
Using `superpowers:using-superpowers` for skill-selection discipline and `gsd-code-review` because this is a correctness/security review rather than an implementation task. After that I’m reading the stacked branches directly and running the relevant tests/scripts locally.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.

exec
/bin/zsh -lc "sed -n '1,260p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
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

codex
I’ve confirmed the ADR-012 and ADR-013 branches exist on origin. Next I’m diffing #25 against #24, opening the calibration-cap implementation from the base branch, and then I’ll run the extractor tests plus a few adversarial body cases against the real code.
exec
/bin/zsh -lc "git show origin/feature/AI-FEA-ADR-012-calibration-cap:reports/calibration_state.json | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
{
  "schema_version": 1,
  "established_by": "ADR-012 / AR-2026-04-25-001 / DEC-T0-2026-04-25-001",
  "doc": "Append-only state for T1 calibration cap. Entries ordered by PR number (monotonic with merge time on this repo). Last 5 entries determine the ceiling per AR-2026-04-25-001 §1 formula. Pre-ADR-011-baseline PRs excluded; PR #17 (the ADR-011 establishment) is also excluded as bootstrap baseline per T0 verdict.",
  "outcome_canon": "APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)",
  "entries": [
    {
      "pr": 18,
      "sha": "77e6813",
      "title": "[FF-02] FailurePattern attribution for GS-001/002/003",
      "merged_at": "2026-04-25T08:53:09Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "1 HIGH + 3 MEDIUM",
      "r1_review_report": "reports/codex_tool_reports/ff02_r1_review.md",
      "notes": "Over-claim/prescription, gs_artifact_pin placeholder, HF3 cite inconsistency, README severity scope"
    },
    {
      "pr": 19,
      "sha": "4a64cfd",
      "title": "[FF-05] Seed .planning/STATE.md as repo-side execution snapshot",
      "merged_at": "2026-04-25T08:56:46Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "1 HIGH + 1 MEDIUM",
      "r1_review_report": "reports/codex_tool_reports/ff05_r1_review.md",
      "notes": "STATE.md still pre-push state (FF-01/FF-02 listed as pending); invented ADR-012/013 references"
    },
    {
      "pr": 20,
      "sha": "9362f6d",
      "title": "Revert direct-push 815945c, preserve portable-path fixes",
      "merged_at": "2026-04-25T08:33:51Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
      "r1_review_report": "reports/codex_tool_reports/revert_815945c_r1_review.md",
      "notes": "Revert direction inversion (re-introduced /Users/Zhuanz/ paths); commit message factual error; CI claim overstated"
    },
    {
      "pr": 21,
      "sha": "2bbf0f1",
      "title": "chore: post-merge cleanup — STATE.md + Codex review archive",
      "merged_at": "2026-04-25T10:30:14Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "1 HIGH",
      "r1_review_report": null,
      "r1_review_report_pending_archive": true,
      "notes": "STATE.md Active branches/Open PRs sections underreported (P1-* PRs #11-#16 missing); R1 review still in /tmp/, awaits next housekeeping cycle"
    },
    {
      "pr": 22,
      "sha": "ac98fc3",
      "title": "[FF-06] pre-commit path-guard for HF1 forbidden zone",
      "merged_at": "2026-04-25T10:43:55Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
      "r1_review_report": null,
      "r1_review_report_pending_archive": true,
      "notes": "pre-commit pass_filenames misses rename old-paths and deletes (silent HF1 bypass); HF1.6 over-blocks Makefile other targets; override audit trail unenforceable"
    },
    {
      "pr": 23,
      "sha": "e53b0f7",
      "title": "[ADR-011] T0 amendments AR-2026-04-25-001 (T2 + HF1 + HF2 + numbering)",
      "merged_at": "2026-04-25T12:06:52Z",
      "r1_outcome": "CHANGES_REQUIRED",
      "r1_severity": "3 BLOCKER + 1 SHOULD_FIX",
      "r1_review_report": null,
      "r1_review_report_pending_archive": true,
      "notes": "ADR-011 amendments PR — Codex R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit e96904d, then merged after CI green. R1 review report still pending archive into reports/codex_tool_reports/."
    }
  ],
  "computed_at_bootstrap": {
    "last_5_cr_count": 5,
    "trailing_approve_count": 0,
    "base_ceiling": 30,
    "final_ceiling": 30,
    "mandatory_codex": true,
    "blocking": true,
    "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%"
  }
}

exec
/bin/zsh -lc "git show origin/feature/AI-FEA-ADR-012-calibration-cap:scripts/compute_calibration_cap.py | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
#!/usr/bin/env python3
"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).

Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
self-pass field by calling this script; the field is read-only to T1.

Formula (canonical, ratified in AR-2026-04-25-001 §1):

    Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR excluded)
    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)

    Base ceiling (per next PR):
      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING

    Recovery (override):
      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
      3 consecutive R1=APPROVE  → ceiling returns to 95%

Invocations:
    python3 scripts/compute_calibration_cap.py
        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
    python3 scripts/compute_calibration_cap.py --human
        emits human-readable summary to stdout
    python3 scripts/compute_calibration_cap.py --check <CEILING>
        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)

State source: reports/calibration_state.json (append-only). State file is the
single source of truth; this script is a pure function over its contents.

Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
revisit after 10 more PRs of post-ADR-012 data.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Canonical: NITS counts as APPROVE; everything else counts as CHANGES_REQUIRED.
APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})

# Rung ladder, low → high. Recovery moves one index up.
RUNGS: tuple[int, ...] = (30, 50, 80, 95)


@dataclass(frozen=True)
class CalibrationResult:
    ceiling: int
    mandatory_codex: bool
    blocking: bool
    basis: str
    entry_count: int


def step_up(ceiling: int) -> int:
    """Move ceiling one rung up (saturate at 95)."""
    if ceiling not in RUNGS:
        raise ValueError(f"unknown ceiling rung: {ceiling}")
    idx = RUNGS.index(ceiling)
    return RUNGS[min(idx + 1, len(RUNGS) - 1)]


def base_ceiling_from_cr_count(cr_count: int) -> int:
    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.

    Per AR-2026-04-25-001 §1.
    """
    if cr_count < 0:
        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
    if cr_count == 0:
        return 95
    if cr_count <= 2:
        return 80
    if cr_count <= 4:
        return 50
    return 30


def trailing_approve_count(outcomes: list[str]) -> int:
    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
    n = 0
    for o in reversed(outcomes):
        if o in APPROVE_OUTCOMES:
            n += 1
        else:
            break
    return n


def compute_calibration(outcomes: list[str]) -> CalibrationResult:
    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
    last5 = outcomes[-5:]
    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
    base = base_ceiling_from_cr_count(cr_count)
    trailing = trailing_approve_count(outcomes)

    if trailing >= 3:
        ceiling = 95
        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
    elif trailing >= 2:
        stepped = step_up(base)
        ceiling = stepped
        basis = (
            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
            f"2 trailing APPROVE → step up to {ceiling}%"
        )
    else:
        ceiling = base
        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"

    # Codex gate derivation from final ceiling
    if ceiling <= 30:
        mandatory_codex = True
        blocking = True
    elif ceiling <= 50:
        mandatory_codex = True
        blocking = False
    else:
        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
        # Codex independently of the ceiling.
        mandatory_codex = False
        blocking = False

    return CalibrationResult(
        ceiling=ceiling,
        mandatory_codex=mandatory_codex,
        blocking=blocking,
        basis=basis,
        entry_count=len(outcomes),
    )


def load_state(state_path: Path) -> list[str]:
    """Read calibration_state.json and return chronologically-ordered R1 outcomes.

    Empty file (or missing file) yields an empty list, which by formula maps
    to ceiling 95% (the "0 of last 5" branch). Callers must distinguish
    "no history" from "all-good history" by inspecting the returned length.
    """
    if not state_path.exists():
        return []
    with state_path.open() as f:
        data = json.load(f)
    entries = data.get("entries", [])
    # Order by PR number (monotonic with merge time on this repo).
    entries_sorted = sorted(entries, key=lambda e: e.get("pr", 0))
    return [e.get("r1_outcome", "CHANGES_REQUIRED") for e in entries_sorted]


def gate_label(result: CalibrationResult) -> str:
    if result.blocking:
        return "BLOCKING"
    if result.mandatory_codex:
        return "MANDATORY"
    if result.ceiling <= 80:
        return "RECOMMENDED"
    return "OPTIONAL"


def main(argv: list[str]) -> int:
    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
    parser = argparse.ArgumentParser(
        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="emit human-readable summary instead of JSON",
    )
    parser.add_argument(
        "--check",
        type=int,
        metavar="CEILING",
        help="exit 1 if claimed CEILING exceeds the computed ceiling",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=default_state,
        help=f"path to calibration_state.json (default: {default_state})",
    )
    args = parser.parse_args(argv[1:])

    outcomes = load_state(args.state)
    result = compute_calibration(outcomes)

    if args.check is not None:
        if args.check > result.ceiling:
            sys.stderr.write(
                f"calibration check FAILED: claimed {args.check}% exceeds "
                f"computed ceiling {result.ceiling}%\n"
                f"  basis: {result.basis}\n"
                f"  Codex gate: {gate_label(result)}\n"
            )
            return 1
        return 0

    if args.human:
        print(f"T1 calibration ceiling : {result.ceiling}%")
        print(f"Codex pre-merge gate   : {gate_label(result)}")
        print(f"Basis                  : {result.basis}")
        print(f"State entries          : {result.entry_count} (last 5 used)")
    else:
        out = {
            "ceiling": result.ceiling,
            "mandatory_codex": result.mandatory_codex,
            "blocking": result.blocking,
            "basis": result.basis,
            "entry_count": result.entry_count,
            "gate_label": gate_label(result),
        }
        print(json.dumps(out, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

exec
/bin/zsh -lc 'git diff --stat origin/feature/AI-FEA-ADR-012-calibration-cap..origin/feature/AI-FEA-ADR-013-branch-protection' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'git diff --unified=80 origin/feature/AI-FEA-ADR-012-calibration-cap..origin/feature/AI-FEA-ADR-013-branch-protection -- .github/workflows/calibration-cap-check.yml scripts/extract_pr_self_pass_rate.py scripts/apply_branch_protection.sh tests/test_extract_pr_self_pass_rate.py docs/adr/ADR-013-branch-protection-enforcement.md .github/PULL_REQUEST_TEMPLATE.md' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
 .github/PULL_REQUEST_TEMPLATE.md                  |  61 +++++++++
 .github/workflows/calibration-cap-check.yml       |  61 +++++++++
 .planning/STATE.md                                |  67 ++++++----
 docs/adr/ADR-013-branch-protection-enforcement.md | 109 ++++++++++++++++
 scripts/apply_branch_protection.sh                |  46 +++++++
 scripts/extract_pr_self_pass_rate.py              |  61 +++++++++
 tests/test_extract_pr_self_pass_rate.py           | 145 ++++++++++++++++++++++
 7 files changed, 527 insertions(+), 23 deletions(-)

 succeeded in 0ms:
diff --git a/.github/PULL_REQUEST_TEMPLATE.md b/.github/PULL_REQUEST_TEMPLATE.md
new file mode 100644
index 0000000..667bf1c
--- /dev/null
+++ b/.github/PULL_REQUEST_TEMPLATE.md
@@ -0,0 +1,61 @@
+<!--
+ADR-013 PR template. Sections marked REQUIRED are validated by CI.
+The "Self-pass-rate" section is mechanically checked against the formula
+in scripts/compute_calibration_cap.py — claims above the current ceiling
+fail CI. Fill it by running:
+
+    python3 scripts/compute_calibration_cap.py --human
+
+and copying the ceiling integer (no `%`) into the section below.
+-->
+
+## Summary
+
+<!-- 1-3 bullets: what changes, why now. -->
+
+-
+-
+
+## Self-pass-rate (mechanically derived) <!-- REQUIRED — ADR-013 -->
+
+<!--
+Replace `<N>` with the integer printed by:
+    python3 scripts/compute_calibration_cap.py
+The CI calibration-cap-check job will fail if your claim exceeds the
+current ceiling. Do not type a number from intuition; ADR-012 forbids it.
+-->
+
+**<N>%** · derived from `reports/calibration_state.json` last-5 R1 outcomes.
+
+Codex pre-merge gate (per ADR-012):
+
+- [ ] BLOCKING (ceiling 30) — must reach Codex R1=APPROVE before merge
+- [ ] MANDATORY non-blocking (ceiling 50) — Codex R1 required, can iterate
+- [ ] RECOMMENDED (ceiling 80) — Codex review strongly suggested
+- [ ] OPTIONAL (ceiling 95) — honor system, Codex at author discretion
+
+ADR-011 §T2 mandatory triggers (M1-M5) override the ceiling-derived gate
+when applicable. Tick any that fire:
+
+- [ ] M1: governance text added/changed (ADRs, FailurePatterns, RETROs)
+- [ ] M2: sign-or-direction math (revert direction, BC orientation, etc.)
+- [ ] M3: HF compliance claim (HF1-HF6 path/zone/process assertions)
+- [ ] M4: governance→enforcement translation (script/CI/hook implementing a rule)
+- [ ] M5: PR opened while ceiling ≤ 50%
+
+## Test plan <!-- REQUIRED -->
+
+- [ ] `pytest tests/`
+- [ ] `ruff check .` and `ruff format --check .`
+- [ ] *(if applicable)* hot-smoke / hand-tested in a real workflow
+- [ ] Codex pre-merge review *(if BLOCKING/MANDATORY or any M1-M5 triggered)*
+
+## Out of scope
+
+<!-- What this PR explicitly does NOT do, to prevent scope creep reviews. -->
+
+-
+
+## Related
+
+- ADR-XXX, FP-XXX, DEC-XXX, AR-XXX as relevant
diff --git a/.github/workflows/calibration-cap-check.yml b/.github/workflows/calibration-cap-check.yml
new file mode 100644
index 0000000..53c5338
--- /dev/null
+++ b/.github/workflows/calibration-cap-check.yml
@@ -0,0 +1,61 @@
+name: Calibration Cap Check
+
+# ADR-013 enforcement workflow. Validates that every PR's
+# "Self-pass-rate" claim does not exceed the mechanical ceiling
+# computed by scripts/compute_calibration_cap.py from
+# reports/calibration_state.json.
+#
+# Runs only on pull_request events (no value on push to main).
+
+on:
+  pull_request:
+    branches: [main]
+    types: [opened, edited, synchronize, reopened]
+
+permissions:
+  contents: read
+  pull-requests: read
+
+jobs:
+  calibration-cap-check:
+    runs-on: ubuntu-latest
+    steps:
+      - uses: actions/checkout@v4
+
+      - name: Set up Python 3.11
+        uses: actions/setup-python@v5
+        with:
+          python-version: "3.11"
+
+      - name: Compute current ceiling
+        id: ceiling
+        run: |
+          set -euo pipefail
+          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
+          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
+          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
+          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
+          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
+          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
+          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
+          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING}"
+
+      - name: Extract Self-pass-rate claim from PR body
+        id: claim
+        env:
+          PR_BODY: ${{ github.event.pull_request.body }}
+        run: |
+          set -euo pipefail
+          if [[ -z "${PR_BODY:-}" ]]; then
+            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
+            exit 1
+          fi
+          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
+          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
+          echo "Claim parsed from PR body: ${CLAIM}%"
+
+      - name: Validate claim does not exceed ceiling
+        run: |
+          set -euo pipefail
+          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
+          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"
diff --git a/docs/adr/ADR-013-branch-protection-enforcement.md b/docs/adr/ADR-013-branch-protection-enforcement.md
new file mode 100644
index 0000000..ed6c9a6
--- /dev/null
+++ b/docs/adr/ADR-013-branch-protection-enforcement.md
@@ -0,0 +1,109 @@
+# ADR-013: Branch protection enforcement for the calibration cap
+
+- **Status:** Accepted
+- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
+- **Date:** 2026-04-25
+- **Related:** ADR-011 (parent), ADR-012 (calibration math — sibling), DEC-T0-2026-04-25-001 (Notion record)
+- **Branch:** `feature/AI-FEA-ADR-013-branch-protection`
+- **Repo-tier prerequisite:** repo must be **public** OR on **GitHub Pro** (required for branch protection + rulesets API). Repo was flipped from private→public on 2026-04-25 to satisfy this.
+
+---
+
+## Context
+
+ADR-012 defines a *calibration ceiling* (mechanical, derived from rolling 5-PR Codex R1 outcomes). That math is meaningless if T1 can self-merge under any ceiling — including 30%/BLOCKING. Session 2026-04-25 demonstrated empirically that T1 wrote `95%` self-estimates five times in a row while Codex was actively returning CHANGES_REQUIRED on each PR. The honor-system has zero enforcement surface; the calibration cap needs a wrapper that physically prevents T1 from merging when the gate is BLOCKING and that surfaces the gate's claim-vs-ceiling check on every PR.
+
+ADR-013 is that wrapper.
+
+## Decision
+
+Enforce ADR-012's gate via three concentric layers:
+
+### Layer 1 — PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
+
+Every PR is opened from a template that:
+
+- Reserves a section labeled `## Self-pass-rate (mechanically derived)`.
+- Instructs the author to fill it from `python3 scripts/compute_calibration_cap.py`'s output, **never from intuition**.
+- Forces the author to tick exactly one Codex pre-merge gate level (BLOCKING / MANDATORY / RECOMMENDED / OPTIONAL).
+- Forces the author to tick any ADR-011 §T2 M1-M5 mandatory triggers that fire (independent override).
+- Includes a `## Test plan` section validated by reviewers.
+
+The template is only a *prompt*; the actual enforcement is in Layer 2.
+
+### Layer 2 — CI workflow (`.github/workflows/calibration-cap-check.yml`)
+
+Triggered on every `pull_request` event (`opened` / `edited` / `synchronize` / `reopened`):
+
+1. Computes the current ceiling via `compute_calibration_cap.py`.
+2. Extracts the claimed ceiling from the PR body via `scripts/extract_pr_self_pass_rate.py`.
+3. Runs `compute_calibration_cap.py --check <claim>` — exits non-zero if the claim exceeds the ceiling.
+
+Result: a PR whose body claims 80% while the formula says 30% fails CI. The author cannot fix this by editing the body to a higher number — only by either correcting downward to ≤ ceiling or by adding R1=APPROVE entries to `calibration_state.json` (which requires merging clean PRs first, which require Codex review, which is the whole point).
+
+### Layer 3 — GitHub branch protection (`scripts/apply_branch_protection.sh`)
+
+A protection ruleset on `main` requires:
+
+- **`required_status_checks`** = `["lint-and-test (3.11)", "calibration-cap-check"]` with `strict: true` (PR must be up-to-date with main before merge).
+- **`required_linear_history`** = `true` — squash-only style, no merge commits.
+- **`allow_force_pushes`** = `false`, **`allow_deletions`** = `false` — protect against accidental destruction of main.
+- **`required_conversation_resolution`** = `true` — Codex review threads must be resolved.
+- **`enforce_admins`** = `false` — T0 (the human admin) retains emergency override. Justification: solo-developer setup; without admin override, any CI infrastructure breakage would brick the repo. ADR-013's discipline is procedural, not coercive at the admin level.
+- **`required_pull_request_reviews`** = `null` — solo-dev; Codex (via the M1-M5 + ceiling gate) is the de facto reviewer rather than a human approver. Adding a human-required-review on a single-author repo would just stamp the author's own approvals.
+
+### Discipline binding (T1 contract)
+
+The gate cannot mechanically prevent admin-bypass merges by T1 acting through the user's authenticated `gh` CLI. This residual loophole is closed by **discipline**:
+
+> **T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:**
+> **(a) Codex Round 1 returned `APPROVE` (or `APPROVE_WITH_NITS` with all nits resolved) on the latest commit, OR**
+> **(b) T0 (the human) explicitly authorizes the merge in writing in the conversation, citing the BLOCKING state.**
+
+Any T1 merge that violates this contract is a P0 procedural failure and triggers a retro entry per RETRO cadence rules. Layer 1 + 2 surface the BLOCKING state in CI and PR template so T1 cannot plausibly miss it; Layer 3 makes the merge *physically possible* only via deliberate admin-bypass *that T1 has no business invoking*.
+
+## Implementation contract
+
+| File | Purpose |
+|---|---|
+| `.github/PULL_REQUEST_TEMPLATE.md` | Layer 1 — PR template |
+| `.github/workflows/calibration-cap-check.yml` | Layer 2 — CI claim-vs-ceiling check |
+| `scripts/extract_pr_self_pass_rate.py` | Layer 2 — PR body parser (16 unit tests) |
+| `scripts/apply_branch_protection.sh` | Layer 3 — idempotent protection setup |
+| `docs/adr/ADR-013-branch-protection-enforcement.md` | This doc |
+
+## Activation sequence
+
+1. **Land this PR via Codex R1=APPROVE.** Layers 1 and 2 take effect on merge (template applies to subsequent PRs; CI workflow runs on subsequent PRs).
+2. **T0 runs** `bash scripts/apply_branch_protection.sh` once after merge. Layer 3 takes effect immediately; from this moment forward, no merge to main can land without `lint-and-test (3.11)` + `calibration-cap-check` both green.
+3. **Subsequent PRs** open from the new template; the calibration-cap-check workflow validates each automatically.
+
+The bootstrap PR for ADR-013 itself (this PR) is NOT subject to Layer 2 yet because the workflow file lands as part of this PR — GitHub doesn't run workflow files that don't exist on the base branch yet. ADR-012's PR (#24) is also NOT subject to Layer 2 for the same reason. **Both PRs land under Layer 0 (no enforcement) but are required by ADR-012/AR-2026-04-25-001 §1 to reach Codex R1=APPROVE before merge** — the discipline binding above applies retroactively to the same session that authored these ADRs.
+
+## Consequences
+
+**Intended:**
+
+- T1's mechanical ceiling becomes physically enforced at PR-merge time once Layer 3 is on. CI red blocks merge.
+- Layer 1 + 2 produce a clear paper trail: every PR body declares a ceiling; CI validates it; the validation result is part of the PR's check history.
+- Layer 3 prevents accidental force-push or deletion of main (defense against the same class of error that produced PR #20's revert).
+- The discipline binding turns the residual admin-bypass into a documented retro-eligible event rather than a silent loophole.
+
+**Acknowledged:**
+
+- `enforce_admins: false` means a determined or careless admin can bypass everything. This is a deliberate trade-off for solo-dev recoverability; revisit if/when the project grows to multi-author.
+- Layer 3 doesn't run until after this PR merges (chicken-and-egg). The first two ADR PRs (#24 and this one) ride on Layer 0 = nothing. ADR-012/013 is therefore a *prospective* gate, not retroactive.
+- The CI check uses GitHub's `pull_request.body` field, which can be edited freely. An author could in principle merge a PR, then edit the body to game future tooling. The state file (Layer 0 of ADR-012) is the actual source of truth, not the body claim. The body claim is just a checksum.
+- Repo had to be made public to access protection APIs on the free tier. Future-proof: if the project ever needs to go private again, options are (a) GitHub Pro, (b) move to GitLab (free private branch protection), (c) drop Layer 3 and rely on Layer 1 + 2 + discipline alone.
+
+**Out of scope:**
+
+- Multi-reviewer / CODEOWNERS enforcement (single-author repo, no value yet).
+- Signed-commit requirements (would block T1's automated commits without GPG keypair setup).
+- Blocking direct push to feature branches (low value; force-push protection on main is enough).
+
+## Open follow-ups
+
+- After 10 post-ADR-013 PRs, audit: did the `calibration-cap-check` job ever fail? Did it ever falsely pass? Sample 3 PR bodies to confirm the template was followed.
+- Consider extending the workflow to also scrape ADR-011 §T2 M1-M5 checkboxes; if any is ticked, require a `Codex-Approved-By:` trailer in the merge commit.
+- If a future PR rewords the `Self-pass-rate` heading, add a heading-rename safety check to `extract_pr_self_pass_rate.py` (currently tolerates `Self-pass-rate` and `Self pass rate` only).
diff --git a/scripts/apply_branch_protection.sh b/scripts/apply_branch_protection.sh
new file mode 100755
index 0000000..fddb340
--- /dev/null
+++ b/scripts/apply_branch_protection.sh
@@ -0,0 +1,46 @@
+#!/usr/bin/env bash
+# ADR-013: applies the protection ruleset to main.
+#
+# Idempotent — re-running with the same settings is a no-op.
+# Requires: `gh` authenticated as a user with admin permission on the repo.
+#
+# Settings rationale (see ADR-013 §"Protection ruleset"):
+# - required_status_checks: lint-and-test (3.11) + calibration-cap-check
+# - enforce_admins: false        (T0 retains emergency override)
+# - required_pull_request_reviews: null  (solo-dev — Codex is the de facto reviewer)
+# - allow_force_pushes: false
+# - allow_deletions: false
+# - required_linear_history: true        (squash-only style)
+# - lock_branch: false
+# - required_conversation_resolution: true
+
+set -euo pipefail
+
+REPO="${1:-kogamishinyajerry-ops/ai-structure-analysis}"
+BRANCH="${2:-main}"
+
+echo "Applying branch protection to $REPO:$BRANCH ..."
+
+gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
+  --input - <<'JSON'
+{
+  "required_status_checks": {
+    "strict": true,
+    "contexts": ["lint-and-test (3.11)", "calibration-cap-check"]
+  },
+  "enforce_admins": false,
+  "required_pull_request_reviews": null,
+  "restrictions": null,
+  "required_linear_history": true,
+  "allow_force_pushes": false,
+  "allow_deletions": false,
+  "required_conversation_resolution": true,
+  "lock_branch": false,
+  "allow_fork_syncing": true
+}
+JSON
+
+echo
+echo "Protection applied. Verifying..."
+gh api "repos/$REPO/branches/$BRANCH/protection" \
+  --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
diff --git a/scripts/extract_pr_self_pass_rate.py b/scripts/extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..31c463c
--- /dev/null
+++ b/scripts/extract_pr_self_pass_rate.py
@@ -0,0 +1,61 @@
+"""Extract the claimed Self-pass-rate from a PR body.
+
+The PR template (per ADR-013) reserves a section labeled
+"Self-pass-rate (mechanically derived)" whose first line contains the
+claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
+integer so CI can pass it to compute_calibration_cap.py --check.
+
+Usage:
+    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
+    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
+    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py
+
+Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
+no claim found in the body.
+"""
+
+from __future__ import annotations
+
+import re
+import sys
+
+# Match the Self-pass-rate section heading then the first \d+% within
+# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
+# `### Self-pass-rate`, with-or-without trailing parenthetical.
+_HEADING_RE = re.compile(
+    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
+)
+_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")
+
+
+def extract_claim(body: str) -> int | None:
+    """Return the integer claim (0-100) or None if not found."""
+    heading = _HEADING_RE.search(body)
+    if not heading:
+        return None
+    tail = body[heading.end() : heading.end() + 600]
+    m = _PERCENT_RE.search(tail)
+    if not m:
+        return None
+    val = int(m.group(1))
+    if not 0 <= val <= 100:
+        return None
+    return val
+
+
+def main(argv: list[str]) -> int:
+    body = sys.stdin.read()
+    claim = extract_claim(body)
+    if claim is None:
+        print(
+            "ERROR: PR body does not contain a 'Self-pass-rate' section "
+            "with a `N%` claim. ADR-013 requires this section in every PR.",
+            file=sys.stderr,
+        )
+        return 2
+    print(claim)
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_extract_pr_self_pass_rate.py b/tests/test_extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..3aa0d70
--- /dev/null
+++ b/tests/test_extract_pr_self_pass_rate.py
@@ -0,0 +1,145 @@
+"""Tests for scripts/extract_pr_self_pass_rate.py (ADR-013)."""
+
+from __future__ import annotations
+
+import sys
+from pathlib import Path
+
+import pytest
+
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+_SCRIPTS_DIR = _REPO_ROOT / "scripts"
+if str(_SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(_SCRIPTS_DIR))
+
+
+def _load():
+    import extract_pr_self_pass_rate  # type: ignore[import-not-found]
+
+    return extract_pr_self_pass_rate
+
+
+@pytest.fixture(scope="module")
+def mod():
+    return _load()
+
+
+# ---------------------------------------------------------------------------
+# Happy paths
+# ---------------------------------------------------------------------------
+
+
+def test_h2_with_parenthetical_bold_percent(mod):
+    body = """## Summary
+Stuff.
+
+## Self-pass-rate (mechanically derived)
+
+**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in state file.
+
+## Test plan
+- [x] tests
+"""
+    assert mod.extract_claim(body) == 30
+
+
+def test_h2_plain_percent(mod):
+    body = "## Self-pass-rate\n\n80%\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_h3_heading(mod):
+    body = "### Self-pass-rate\n95%\n"
+    assert mod.extract_claim(body) == 95
+
+
+def test_heading_with_space(mod):
+    """Tolerate 'Self pass rate' with spaces."""
+    body = "## Self pass rate\n\n50%\n"
+    assert mod.extract_claim(body) == 50
+
+
+def test_picks_first_percent_after_heading(mod):
+    body = "## Self-pass-rate\n\n**80%** baseline (raised from 50% earlier).\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_zero_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n0%\n"
+    assert mod.extract_claim(body) == 0
+
+
+def test_one_hundred_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n100%\n"
+    assert mod.extract_claim(body) == 100
+
+
+# ---------------------------------------------------------------------------
+# Unhappy paths
+# ---------------------------------------------------------------------------
+
+
+def test_no_heading_returns_none(mod):
+    body = "## Summary\n\nWe have 95% confidence here.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_heading_without_percent_returns_none(mod):
+    body = "## Self-pass-rate\n\nTBD — script will fill in.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_above_100_rejected(mod):
+    body = "## Self-pass-rate\n\n150%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_h1_heading_rejected(mod):
+    """Single-# heading must NOT match (PR body sections are h2+)."""
+    body = "# Self-pass-rate\n\n95%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_inline_mention_rejected(mod):
+    """Mentioning self-pass-rate in prose must not match."""
+    body = "## Summary\n\nThe self-pass-rate is 95% trust me bro.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_empty_body_returns_none(mod):
+    assert mod.extract_claim("") is None
+
+
+def test_percent_too_far_after_heading_ignored(mod):
+    """Search window is bounded so a wandering paragraph doesn't pollute."""
+    body = "## Self-pass-rate\n\n" + ("filler. " * 200) + "95%\n"
+    assert mod.extract_claim(body) is None
+
+
+# ---------------------------------------------------------------------------
+# CLI
+# ---------------------------------------------------------------------------
+
+
+def test_cli_prints_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Self-pass-rate\n\n30%\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 0
+    assert captured.out.strip() == "30"
+
+
+def test_cli_exits_2_when_no_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Summary\n\nNo claim here.\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 2
+    assert "Self-pass-rate" in captured.err
+
+
+class _StdinShim:
+    def __init__(self, text: str):
+        self._text = text
+
+    def read(self) -> str:
+        return self._text

web search: 
web search: site:docs.github.com REST API update branch protection required_conversation_resolution allow_fork_syncing
codex
I’ve got the diff and the base calibration script. I’m now executing the stacked branch in an isolated worktree so I can run the extractor tests and reproduce the trust-boundary behavior instead of reviewing the regex on paper only.
exec
/bin/zsh -lc 'tmpdir=$(mktemp -d /tmp/ai-structure-pr25-review.XXXXXX) && echo "$tmpdir" && git worktree add --detach "$tmpdir" origin/feature/AI-FEA-ADR-013-branch-protection' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/tmp/ai-structure-pr25-review.t8CRCl
Preparing worktree (detached HEAD 7542b05)
HEAD is now at 7542b05 [FF-05-discipline] STATE.md sync to current main + ADR-012/013 in-flight

exec
/bin/zsh -lc 'git status --short && rg --files . | rg "compute_calibration_cap|extract_pr_self_pass_rate|test_extract_pr_self_pass_rate|test_compute_calibration_cap|calibration_state|calibration-cap-check|apply_branch_protection|PULL_REQUEST_TEMPLATE"' in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
./reports/calibration_state.json
./scripts/apply_branch_protection.sh
./scripts/compute_calibration_cap.py
./scripts/extract_pr_self_pass_rate.py
./tests/test_extract_pr_self_pass_rate.py
./tests/test_compute_calibration_cap.py

exec
/bin/zsh -lc 'pytest -q tests/test_extract_pr_self_pass_rate.py' in /tmp/ai-structure-pr25-review.t8CRCl
exec
/bin/zsh -lc 'pytest -q tests/test_compute_calibration_cap.py tests/test_extract_pr_self_pass_rate.py tests/test_hf1_path_guard.py' in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 181ms:
................                                                         [100%]
16 passed in 0.02s

 succeeded in 268ms:
........................................................................ [ 76%]
......................                                                   [100%]
94 passed in 0.10s

exec
/bin/zsh -lc 'rg -n "missing file|missing state|state file|95%|OPTIONAL|empty file|load_state|--check" tests/test_compute_calibration_cap.py scripts/compute_calibration_cap.py docs/adr/ADR-012* .github/workflows/calibration-cap-check.yml .planning/STATE.md' in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
.planning/STATE.md:43:| **ADR-013 — Branch protection enforcement** | 🟡 OPEN, stacked on PR #24, awaiting Codex R1 | **#25** | `feature/AI-FEA-ADR-013-branch-protection` | 3-layer wrapper around ADR-012: PR template + CI `--check` workflow + `gh api` protection script. M1+M4+M5 triggers fire. Repo flipped private→public on 2026-04-25 to access protection API. CI doesn't run on this PR until #24 merges and base auto-rebases. |
.planning/STATE.md:116:6. Self-pass-rate honor-system (RETRO-V61-001) is empirically falsified by session 2026-04-25 (T1 estimated 80-95% on 5 PRs that all returned R1=CR). ADR-012 (PR #24) replaces it with a mechanical ceiling. Until #24 merges, T1 still operates under the falsified honor-system — i.e., this PR (#25) and the next few must explicitly cite the empirical 0/5 R1-pass-rate when self-rating.
.github/workflows/calibration-cap-check.yml:60:          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
tests/test_compute_calibration_cap.py:195:# load_state
tests/test_compute_calibration_cap.py:199:def test_load_state_missing_file_returns_empty(calc, tmp_path):
tests/test_compute_calibration_cap.py:200:    assert calc.load_state(tmp_path / "nonexistent.json") == []
tests/test_compute_calibration_cap.py:203:def test_load_state_reads_chronologically(calc, tmp_path):
tests/test_compute_calibration_cap.py:215:    outcomes = calc.load_state(state_path)
tests/test_compute_calibration_cap.py:219:def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
tests/test_compute_calibration_cap.py:227:    outcomes = calc.load_state(state_path)
tests/test_compute_calibration_cap.py:228:    assert len(outcomes) >= 5, "state file must have at least 5 bootstrap entries"
tests/test_compute_calibration_cap.py:266:    assert calc.gate_label(r) == "OPTIONAL"
tests/test_compute_calibration_cap.py:270:# main() — JSON / human / --check
tests/test_compute_calibration_cap.py:298:    assert "T1 calibration ceiling : 95%" in captured
tests/test_compute_calibration_cap.py:299:    assert "OPTIONAL" in captured
tests/test_compute_calibration_cap.py:306:    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
tests/test_compute_calibration_cap.py:317:    rc = calc.main(["compute_calibration_cap.py", "--check", "95", "--state", str(state_path)])
tests/test_compute_calibration_cap.py:321:    assert "claimed 95%" in err
tests/test_compute_calibration_cap.py:333:    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:18:| #20 revert | 95% | CHANGES_REQUIRED · 1 BLOCKER (direction inversion) |
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:19:| #18 FF-02 | 95% | CHANGES_REQUIRED · 1 HIGH (over-claim + unflagged prescription) |
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:20:| #19 FF-05 | 95% | CHANGES_REQUIRED · 1 HIGH (stale post-merge state) |
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:24:Empirical R1-pass-rate: **0/5 = 0%**. T1 self-estimates were systematically wrong by 80-95 percentage points each, *across the same session*. T0's diagnostic in AR-2026-04-25-001 §1: "this is not noise; it is the predictable failure mode of any honor-system metric where the rater and the rated party are the same agent in the same context window." The discipline cannot self-correct mid-session — T1 wrote "95%" five times in a row while Codex was actively contradicting it.
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:30:Self-pass-rate becomes a **mechanically-derived ceiling** based on a rolling window of the last 5 PRs' Codex Round 1 outcomes. T1 cannot type a number; T1 reads a number computed by `scripts/compute_calibration_cap.py` from the append-only state file `reports/calibration_state.json`.
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:40:  0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:47:  3 consecutive R1=APPROVE  → ceiling returns to 95%
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:67:- `reports/calibration_state.json` — append-only state file, schema v1. Each entry: `{pr, sha, title, merged_at, r1_outcome, r1_severity, r1_review_report, notes}`. Authoritative for the formula's input.
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:68:- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes.
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:75:- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:99:To return to the 95% honor-system regime from the bootstrap 30%, T1 needs:
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:103:- **Three consecutive** R1=APPROVE → recovery clause resets ceiling to 95, OPTIONAL
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md:130:- Add CI step calling `compute_calibration_cap.py --check` against PR body's claim, after `.github/PULL_REQUEST_TEMPLATE.md` lands (in ADR-013's batch).
scripts/compute_calibration_cap.py:16:      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
scripts/compute_calibration_cap.py:23:      3 consecutive R1=APPROVE  → ceiling returns to 95%
scripts/compute_calibration_cap.py:30:    python3 scripts/compute_calibration_cap.py --check <CEILING>
scripts/compute_calibration_cap.py:109:        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
scripts/compute_calibration_cap.py:144:def load_state(state_path: Path) -> list[str]:
scripts/compute_calibration_cap.py:147:    Empty file (or missing file) yields an empty list, which by formula maps
scripts/compute_calibration_cap.py:148:    to ceiling 95% (the "0 of last 5" branch). Callers must distinguish
scripts/compute_calibration_cap.py:168:    return "OPTIONAL"
scripts/compute_calibration_cap.py:182:        "--check",
scripts/compute_calibration_cap.py:195:    outcomes = load_state(args.state)

exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py && python3 scripts/compute_calibration_cap.py --check 30; echo exit:$?' in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
{"ceiling": 30, "mandatory_codex": true, "blocking": true, "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%", "entry_count": 6, "gate_label": "BLOCKING"}
exit:0

exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py --state /tmp/does-not-exist.json && python3 scripts/compute_calibration_cap.py --state /tmp/does-not-exist.json --check 95; echo exit:$?' in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
{"ceiling": 95, "mandatory_codex": false, "blocking": false, "basis": "0 of last 5 = CHANGES_REQUIRED → ceiling 95%", "entry_count": 0, "gate_label": "OPTIONAL"}
exit:0

codex
The current regex has a real trust-boundary weakness. I’m checking whether a hidden HTML comment or fenced code block containing a fake `## Self-pass-rate` heading can make CI parse a lower claim than the visible one.
exec
/bin/zsh -lc "python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import extract_pr_self_pass_rate as m
body='''<"'!--'"\\n## Self-pass-rate\\n30%\\n-->\\n\\n## Self-pass-rate\\n95%\\n'''
print(m.extract_claim(body))
PY" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
30

exec
/bin/zsh -lc "python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import extract_pr_self_pass_rate as m
body='''"'```md'"\\n## Self-pass-rate\\n30%\\n"'```'"\\n\\n## Self-pass-rate\\n95%\\n'''
print(m.extract_claim(body))
PY" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
30

exec
/bin/zsh -lc "python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import extract_pr_self_pass_rate as m
body='''> ## Self-pass-rate\\n> 30%\\n\\n## Self-pass-rate\\n95%\\n'''
print(m.extract_claim(body))
PY" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
95

codex
I have two concrete issues now: one is a parser bypass in the extractor itself, the other is the inherited fail-open from ADR-012 that this PR’s CI layer turns into a green required check. I’m pulling exact line references before I write the verdict.
exec
/bin/zsh -lc "nl -ba scripts/extract_pr_self_pass_rate.py | sed -n '1,120p'" in /tmp/ai-structure-pr25-review.t8CRCl
exec
/bin/zsh -lc "nl -ba .github/workflows/calibration-cap-check.yml | sed -n '1,120p'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
     1	"""Extract the claimed Self-pass-rate from a PR body.
     2	
     3	The PR template (per ADR-013) reserves a section labeled
     4	"Self-pass-rate (mechanically derived)" whose first line contains the
     5	claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
     6	integer so CI can pass it to compute_calibration_cap.py --check.
     7	
     8	Usage:
     9	    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
    10	    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
    11	    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py
    12	
    13	Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
    14	no claim found in the body.
    15	"""
    16	
    17	from __future__ import annotations
    18	
    19	import re
    20	import sys
    21	
    22	# Match the Self-pass-rate section heading then the first \d+% within
    23	# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
    24	# `### Self-pass-rate`, with-or-without trailing parenthetical.
    25	_HEADING_RE = re.compile(
    26	    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
    27	)
    28	_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")
    29	
    30	
    31	def extract_claim(body: str) -> int | None:
    32	    """Return the integer claim (0-100) or None if not found."""
    33	    heading = _HEADING_RE.search(body)
    34	    if not heading:
    35	        return None
    36	    tail = body[heading.end() : heading.end() + 600]
    37	    m = _PERCENT_RE.search(tail)
    38	    if not m:
    39	        return None
    40	    val = int(m.group(1))
    41	    if not 0 <= val <= 100:
    42	        return None
    43	    return val
    44	
    45	
    46	def main(argv: list[str]) -> int:
    47	    body = sys.stdin.read()
    48	    claim = extract_claim(body)
    49	    if claim is None:
    50	        print(
    51	            "ERROR: PR body does not contain a 'Self-pass-rate' section "
    52	            "with a `N%` claim. ADR-013 requires this section in every PR.",
    53	            file=sys.stderr,
    54	        )
    55	        return 2
    56	    print(claim)
    57	    return 0
    58	
    59	
    60	if __name__ == "__main__":
    61	    sys.exit(main(sys.argv))

 succeeded in 0ms:
     1	name: Calibration Cap Check
     2	
     3	# ADR-013 enforcement workflow. Validates that every PR's
     4	# "Self-pass-rate" claim does not exceed the mechanical ceiling
     5	# computed by scripts/compute_calibration_cap.py from
     6	# reports/calibration_state.json.
     7	#
     8	# Runs only on pull_request events (no value on push to main).
     9	
    10	on:
    11	  pull_request:
    12	    branches: [main]
    13	    types: [opened, edited, synchronize, reopened]
    14	
    15	permissions:
    16	  contents: read
    17	  pull-requests: read
    18	
    19	jobs:
    20	  calibration-cap-check:
    21	    runs-on: ubuntu-latest
    22	    steps:
    23	      - uses: actions/checkout@v4
    24	
    25	      - name: Set up Python 3.11
    26	        uses: actions/setup-python@v5
    27	        with:
    28	          python-version: "3.11"
    29	
    30	      - name: Compute current ceiling
    31	        id: ceiling
    32	        run: |
    33	          set -euo pipefail
    34	          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
    35	          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
    36	          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
    37	          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
    38	          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
    39	          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
    40	          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
    41	          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING}"
    42	
    43	      - name: Extract Self-pass-rate claim from PR body
    44	        id: claim
    45	        env:
    46	          PR_BODY: ${{ github.event.pull_request.body }}
    47	        run: |
    48	          set -euo pipefail
    49	          if [[ -z "${PR_BODY:-}" ]]; then
    50	            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
    51	            exit 1
    52	          fi
    53	          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
    54	          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
    55	          echo "Claim parsed from PR body: ${CLAIM}%"
    56	
    57	      - name: Validate claim does not exceed ceiling
    58	        run: |
    59	          set -euo pipefail
    60	          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
    61	          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"

exec
/bin/zsh -lc "nl -ba tests/test_extract_pr_self_pass_rate.py | sed -n '1,220p'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
     1	"""Tests for scripts/extract_pr_self_pass_rate.py (ADR-013)."""
     2	
     3	from __future__ import annotations
     4	
     5	import sys
     6	from pathlib import Path
     7	
     8	import pytest
     9	
    10	_REPO_ROOT = Path(__file__).resolve().parent.parent
    11	_SCRIPTS_DIR = _REPO_ROOT / "scripts"
    12	if str(_SCRIPTS_DIR) not in sys.path:
    13	    sys.path.insert(0, str(_SCRIPTS_DIR))
    14	
    15	
    16	def _load():
    17	    import extract_pr_self_pass_rate  # type: ignore[import-not-found]
    18	
    19	    return extract_pr_self_pass_rate
    20	
    21	
    22	@pytest.fixture(scope="module")
    23	def mod():
    24	    return _load()
    25	
    26	
    27	# ---------------------------------------------------------------------------
    28	# Happy paths
    29	# ---------------------------------------------------------------------------
    30	
    31	
    32	def test_h2_with_parenthetical_bold_percent(mod):
    33	    body = """## Summary
    34	Stuff.
    35	
    36	## Self-pass-rate (mechanically derived)
    37	
    38	**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in state file.
    39	
    40	## Test plan
    41	- [x] tests
    42	"""
    43	    assert mod.extract_claim(body) == 30
    44	
    45	
    46	def test_h2_plain_percent(mod):
    47	    body = "## Self-pass-rate\n\n80%\n"
    48	    assert mod.extract_claim(body) == 80
    49	
    50	
    51	def test_h3_heading(mod):
    52	    body = "### Self-pass-rate\n95%\n"
    53	    assert mod.extract_claim(body) == 95
    54	
    55	
    56	def test_heading_with_space(mod):
    57	    """Tolerate 'Self pass rate' with spaces."""
    58	    body = "## Self pass rate\n\n50%\n"
    59	    assert mod.extract_claim(body) == 50
    60	
    61	
    62	def test_picks_first_percent_after_heading(mod):
    63	    body = "## Self-pass-rate\n\n**80%** baseline (raised from 50% earlier).\n"
    64	    assert mod.extract_claim(body) == 80
    65	
    66	
    67	def test_zero_percent_is_valid(mod):
    68	    body = "## Self-pass-rate\n\n0%\n"
    69	    assert mod.extract_claim(body) == 0
    70	
    71	
    72	def test_one_hundred_percent_is_valid(mod):
    73	    body = "## Self-pass-rate\n\n100%\n"
    74	    assert mod.extract_claim(body) == 100
    75	
    76	
    77	# ---------------------------------------------------------------------------
    78	# Unhappy paths
    79	# ---------------------------------------------------------------------------
    80	
    81	
    82	def test_no_heading_returns_none(mod):
    83	    body = "## Summary\n\nWe have 95% confidence here.\n"
    84	    assert mod.extract_claim(body) is None
    85	
    86	
    87	def test_heading_without_percent_returns_none(mod):
    88	    body = "## Self-pass-rate\n\nTBD — script will fill in.\n"
    89	    assert mod.extract_claim(body) is None
    90	
    91	
    92	def test_above_100_rejected(mod):
    93	    body = "## Self-pass-rate\n\n150%\n"
    94	    assert mod.extract_claim(body) is None
    95	
    96	
    97	def test_h1_heading_rejected(mod):
    98	    """Single-# heading must NOT match (PR body sections are h2+)."""
    99	    body = "# Self-pass-rate\n\n95%\n"
   100	    assert mod.extract_claim(body) is None
   101	
   102	
   103	def test_inline_mention_rejected(mod):
   104	    """Mentioning self-pass-rate in prose must not match."""
   105	    body = "## Summary\n\nThe self-pass-rate is 95% trust me bro.\n"
   106	    assert mod.extract_claim(body) is None
   107	
   108	
   109	def test_empty_body_returns_none(mod):
   110	    assert mod.extract_claim("") is None
   111	
   112	
   113	def test_percent_too_far_after_heading_ignored(mod):
   114	    """Search window is bounded so a wandering paragraph doesn't pollute."""
   115	    body = "## Self-pass-rate\n\n" + ("filler. " * 200) + "95%\n"
   116	    assert mod.extract_claim(body) is None
   117	
   118	
   119	# ---------------------------------------------------------------------------
   120	# CLI
   121	# ---------------------------------------------------------------------------
   122	
   123	
   124	def test_cli_prints_claim(mod, capsys, monkeypatch):
   125	    monkeypatch.setattr("sys.stdin", _StdinShim("## Self-pass-rate\n\n30%\n"))
   126	    rc = mod.main([])
   127	    captured = capsys.readouterr()
   128	    assert rc == 0
   129	    assert captured.out.strip() == "30"
   130	
   131	
   132	def test_cli_exits_2_when_no_claim(mod, capsys, monkeypatch):
   133	    monkeypatch.setattr("sys.stdin", _StdinShim("## Summary\n\nNo claim here.\n"))
   134	    rc = mod.main([])
   135	    captured = capsys.readouterr()
   136	    assert rc == 2
   137	    assert "Self-pass-rate" in captured.err
   138	
   139	
   140	class _StdinShim:
   141	    def __init__(self, text: str):
   142	        self._text = text
   143	
   144	    def read(self) -> str:
   145	        return self._text

exec
/bin/zsh -lc "git show origin/feature/AI-FEA-ADR-012-calibration-cap:scripts/compute_calibration_cap.py | nl -ba | sed -n '135,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   135	    return CalibrationResult(
   136	        ceiling=ceiling,
   137	        mandatory_codex=mandatory_codex,
   138	        blocking=blocking,
   139	        basis=basis,
   140	        entry_count=len(outcomes),
   141	    )
   142	
   143	
   144	def load_state(state_path: Path) -> list[str]:
   145	    """Read calibration_state.json and return chronologically-ordered R1 outcomes.
   146	
   147	    Empty file (or missing file) yields an empty list, which by formula maps
   148	    to ceiling 95% (the "0 of last 5" branch). Callers must distinguish
   149	    "no history" from "all-good history" by inspecting the returned length.
   150	    """
   151	    if not state_path.exists():
   152	        return []
   153	    with state_path.open() as f:
   154	        data = json.load(f)
   155	    entries = data.get("entries", [])
   156	    # Order by PR number (monotonic with merge time on this repo).
   157	    entries_sorted = sorted(entries, key=lambda e: e.get("pr", 0))
   158	    return [e.get("r1_outcome", "CHANGES_REQUIRED") for e in entries_sorted]
   159	
   160	
   161	def gate_label(result: CalibrationResult) -> str:
   162	    if result.blocking:
   163	        return "BLOCKING"
   164	    if result.mandatory_codex:
   165	        return "MANDATORY"
   166	    if result.ceiling <= 80:
   167	        return "RECOMMENDED"
   168	    return "OPTIONAL"
   169	
   170	
   171	def main(argv: list[str]) -> int:
   172	    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
   173	    parser = argparse.ArgumentParser(
   174	        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
   175	    )
   176	    parser.add_argument(
   177	        "--human",
   178	        action="store_true",
   179	        help="emit human-readable summary instead of JSON",
   180	    )
   181	    parser.add_argument(
   182	        "--check",
   183	        type=int,
   184	        metavar="CEILING",
   185	        help="exit 1 if claimed CEILING exceeds the computed ceiling",
   186	    )
   187	    parser.add_argument(
   188	        "--state",
   189	        type=Path,
   190	        default=default_state,
   191	        help=f"path to calibration_state.json (default: {default_state})",
   192	    )
   193	    args = parser.parse_args(argv[1:])
   194	
   195	    outcomes = load_state(args.state)
   196	    result = compute_calibration(outcomes)
   197	
   198	    if args.check is not None:
   199	        if args.check > result.ceiling:
   200	            sys.stderr.write(
   201	                f"calibration check FAILED: claimed {args.check}% exceeds "
   202	                f"computed ceiling {result.ceiling}%\n"
   203	                f"  basis: {result.basis}\n"
   204	                f"  Codex gate: {gate_label(result)}\n"
   205	            )
   206	            return 1
   207	        return 0
   208	
   209	    if args.human:
   210	        print(f"T1 calibration ceiling : {result.ceiling}%")
   211	        print(f"Codex pre-merge gate   : {gate_label(result)}")
   212	        print(f"Basis                  : {result.basis}")
   213	        print(f"State entries          : {result.entry_count} (last 5 used)")
   214	    else:
   215	        out = {
   216	            "ceiling": result.ceiling,
   217	            "mandatory_codex": result.mandatory_codex,
   218	            "blocking": result.blocking,
   219	            "basis": result.basis,
   220	            "entry_count": result.entry_count,

exec
/bin/zsh -lc "rg -n \"lint-and-test|name:\" .github/workflows -g '*.yml' -g '*.yaml'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
.github/workflows/ci.yml:1:name: CI
.github/workflows/ci.yml:13:  lint-and-test:
.github/workflows/ci.yml:22:      - name: Set up Python ${{ matrix.python-version }}
.github/workflows/ci.yml:27:      - name: Install dependencies
.github/workflows/ci.yml:32:      - name: Lint — ruff check
.github/workflows/ci.yml:35:      - name: Lint — ruff format check
.github/workflows/ci.yml:38:      - name: Test — pytest
.github/workflows/calibration-cap-check.yml:1:name: Calibration Cap Check
.github/workflows/calibration-cap-check.yml:25:      - name: Set up Python 3.11
.github/workflows/calibration-cap-check.yml:30:      - name: Compute current ceiling
.github/workflows/calibration-cap-check.yml:43:      - name: Extract Self-pass-rate claim from PR body
.github/workflows/calibration-cap-check.yml:57:      - name: Validate claim does not exceed ceiling
.github/workflows/docker-base.yml:1:name: Docker base image
.github/workflows/docker-base.yml:32:      - name: Set up Docker Buildx
.github/workflows/docker-base.yml:35:      - name: Log in to GHCR
.github/workflows/docker-base.yml:40:          username: ${{ github.actor }}
.github/workflows/docker-base.yml:43:      - name: Build (and push on main)
.github/workflows/docker-base.yml:54:      - name: Probe toolchain inside freshly built image

exec
/bin/zsh -lc "nl -ba scripts/apply_branch_protection.sh | sed -n '1,120p'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	# ADR-013: applies the protection ruleset to main.
     3	#
     4	# Idempotent — re-running with the same settings is a no-op.
     5	# Requires: `gh` authenticated as a user with admin permission on the repo.
     6	#
     7	# Settings rationale (see ADR-013 §"Protection ruleset"):
     8	# - required_status_checks: lint-and-test (3.11) + calibration-cap-check
     9	# - enforce_admins: false        (T0 retains emergency override)
    10	# - required_pull_request_reviews: null  (solo-dev — Codex is the de facto reviewer)
    11	# - allow_force_pushes: false
    12	# - allow_deletions: false
    13	# - required_linear_history: true        (squash-only style)
    14	# - lock_branch: false
    15	# - required_conversation_resolution: true
    16	
    17	set -euo pipefail
    18	
    19	REPO="${1:-kogamishinyajerry-ops/ai-structure-analysis}"
    20	BRANCH="${2:-main}"
    21	
    22	echo "Applying branch protection to $REPO:$BRANCH ..."
    23	
    24	gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
    25	  --input - <<'JSON'
    26	{
    27	  "required_status_checks": {
    28	    "strict": true,
    29	    "contexts": ["lint-and-test (3.11)", "calibration-cap-check"]
    30	  },
    31	  "enforce_admins": false,
    32	  "required_pull_request_reviews": null,
    33	  "restrictions": null,
    34	  "required_linear_history": true,
    35	  "allow_force_pushes": false,
    36	  "allow_deletions": false,
    37	  "required_conversation_resolution": true,
    38	  "lock_branch": false,
    39	  "allow_fork_syncing": true
    40	}
    41	JSON
    42	
    43	echo
    44	echo "Protection applied. Verifying..."
    45	gh api "repos/$REPO/branches/$BRANCH/protection" \
    46	  --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'

exec
/bin/zsh -lc "nl -ba .github/workflows/ci.yml | sed -n '1,80p'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
     1	name: CI
     2	
     3	on:
     4	  pull_request:
     5	    branches: [main]
     6	  push:
     7	    branches: [main]
     8	
     9	permissions:
    10	  contents: read
    11	
    12	jobs:
    13	  lint-and-test:
    14	    runs-on: ubuntu-latest
    15	    strategy:
    16	      matrix:
    17	        python-version: ["3.11"]
    18	
    19	    steps:
    20	      - uses: actions/checkout@v4
    21	
    22	      - name: Set up Python ${{ matrix.python-version }}
    23	        uses: actions/setup-python@v5
    24	        with:
    25	          python-version: ${{ matrix.python-version }}
    26	
    27	      - name: Install dependencies
    28	        run: |
    29	          python -m pip install --upgrade pip
    30	          pip install -e ".[dev,agents]"
    31	
    32	      - name: Lint — ruff check
    33	        run: ruff check .
    34	
    35	      - name: Lint — ruff format check
    36	        run: ruff format --check .
    37	
    38	      - name: Test — pytest
    39	        run: pytest tests/ -v --tb=short

exec
/bin/zsh -lc "python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import extract_pr_self_pass_rate as m
body='''## Self-pass-rate\\n\\n<"'!-- 30% -->'"\\n\\n95%\\n'''
print(m.extract_claim(body))
PY" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
30

exec
/bin/zsh -lc "nl -ba tests/test_compute_calibration_cap.py | sed -n '188,340p'" in /tmp/ai-structure-pr25-review.t8CRCl
 succeeded in 0ms:
   188	def test_compute_nits_counts_as_approve(calc):
   189	    """APPROVE_WITH_NITS must count as APPROVE for the formula."""
   190	    r = calc.compute_calibration(["APPROVE_WITH_NITS"] * 5)
   191	    assert r.ceiling == 95
   192	
   193	
   194	# ---------------------------------------------------------------------------
   195	# load_state
   196	# ---------------------------------------------------------------------------
   197	
   198	
   199	def test_load_state_missing_file_returns_empty(calc, tmp_path):
   200	    assert calc.load_state(tmp_path / "nonexistent.json") == []
   201	
   202	
   203	def test_load_state_reads_chronologically(calc, tmp_path):
   204	    """Entries must be sorted by PR number regardless of file order."""
   205	    state = {
   206	        "schema_version": 1,
   207	        "entries": [
   208	            {"pr": 22, "r1_outcome": "BLOCKER"},
   209	            {"pr": 18, "r1_outcome": "APPROVE"},
   210	            {"pr": 20, "r1_outcome": "CHANGES_REQUIRED"},
   211	        ],
   212	    }
   213	    state_path = tmp_path / "calibration_state.json"
   214	    state_path.write_text(json.dumps(state))
   215	    outcomes = calc.load_state(state_path)
   216	    assert outcomes == ["APPROVE", "CHANGES_REQUIRED", "BLOCKER"]  # sorted by pr
   217	
   218	
   219	def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
   220	    """The real reports/calibration_state.json must yield 30/BLOCKING
   221	    as long as the last 5 R1 outcomes are CHANGES_REQUIRED.
   222	
   223	    Entry count grows monotonically as PRs land — locking it would mean
   224	    every PR breaks this test. The invariant is the ceiling, not the row count.
   225	    """
   226	    state_path = _REPO_ROOT / "reports" / "calibration_state.json"
   227	    outcomes = calc.load_state(state_path)
   228	    assert len(outcomes) >= 5, "state file must have at least 5 bootstrap entries"
   229	    last_5 = outcomes[-5:]
   230	    if all(o in ("CHANGES_REQUIRED", "BLOCKER") for o in last_5):
   231	        r = calc.compute_calibration(outcomes)
   232	        assert r.ceiling == 30
   233	        assert r.blocking is True
   234	
   235	
   236	# ---------------------------------------------------------------------------
   237	# gate_label
   238	# ---------------------------------------------------------------------------
   239	
   240	
   241	def test_gate_label_blocking(calc):
   242	    r = calc.CalibrationResult(
   243	        ceiling=30, mandatory_codex=True, blocking=True, basis="b", entry_count=5
   244	    )
   245	    assert calc.gate_label(r) == "BLOCKING"
   246	
   247	
   248	def test_gate_label_mandatory(calc):
   249	    r = calc.CalibrationResult(
   250	        ceiling=50, mandatory_codex=True, blocking=False, basis="b", entry_count=5
   251	    )
   252	    assert calc.gate_label(r) == "MANDATORY"
   253	
   254	
   255	def test_gate_label_recommended(calc):
   256	    r = calc.CalibrationResult(
   257	        ceiling=80, mandatory_codex=False, blocking=False, basis="b", entry_count=5
   258	    )
   259	    assert calc.gate_label(r) == "RECOMMENDED"
   260	
   261	
   262	def test_gate_label_optional(calc):
   263	    r = calc.CalibrationResult(
   264	        ceiling=95, mandatory_codex=False, blocking=False, basis="b", entry_count=5
   265	    )
   266	    assert calc.gate_label(r) == "OPTIONAL"
   267	
   268	
   269	# ---------------------------------------------------------------------------
   270	# main() — JSON / human / --check
   271	# ---------------------------------------------------------------------------
   272	
   273	
   274	def test_main_json_output(calc, tmp_path, capsys):
   275	    state = {
   276	        "schema_version": 1,
   277	        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
   278	    }
   279	    state_path = tmp_path / "s.json"
   280	    state_path.write_text(json.dumps(state))
   281	    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
   282	    assert rc == 0
   283	    out = json.loads(capsys.readouterr().out)
   284	    assert out["ceiling"] == 30
   285	    assert out["mandatory_codex"] is True
   286	    assert out["blocking"] is True
   287	    assert out["entry_count"] == 5
   288	    assert out["gate_label"] == "BLOCKING"
   289	
   290	
   291	def test_main_human_output(calc, tmp_path, capsys):
   292	    state = {"schema_version": 1, "entries": []}
   293	    state_path = tmp_path / "s.json"
   294	    state_path.write_text(json.dumps(state))
   295	    rc = calc.main(["compute_calibration_cap.py", "--human", "--state", str(state_path)])
   296	    assert rc == 0
   297	    captured = capsys.readouterr().out
   298	    assert "T1 calibration ceiling : 95%" in captured
   299	    assert "OPTIONAL" in captured
   300	
   301	
   302	def test_main_check_passes_when_claim_below_ceiling(calc, tmp_path):
   303	    state = {"schema_version": 1, "entries": []}  # ceiling 95
   304	    state_path = tmp_path / "s.json"
   305	    state_path.write_text(json.dumps(state))
   306	    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
   307	    assert rc == 0
   308	
   309	
   310	def test_main_check_fails_when_claim_above_ceiling(calc, tmp_path, capsys):
   311	    state = {
   312	        "schema_version": 1,
   313	        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
   314	    }  # ceiling 30
   315	    state_path = tmp_path / "s.json"
   316	    state_path.write_text(json.dumps(state))
   317	    rc = calc.main(["compute_calibration_cap.py", "--check", "95", "--state", str(state_path)])
   318	    assert rc == 1
   319	    err = capsys.readouterr().err
   320	    assert "calibration check FAILED" in err
   321	    assert "claimed 95%" in err
   322	    assert "computed ceiling 30%" in err
   323	
   324	
   325	def test_main_check_at_exact_ceiling_passes(calc, tmp_path):
   326	    """Claim == ceiling must pass (not strictly greater)."""
   327	    state = {
   328	        "schema_version": 1,
   329	        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
   330	    }
   331	    state_path = tmp_path / "s.json"
   332	    state_path.write_text(json.dumps(state))
   333	    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
   334	    assert rc == 0

web search: 
web search: site:docs.github.com actions/checkout pull_request default ref github.ref merge commit
codex
I’ve finished the review. I’m checking one memory line-range now for proper citation formatting, then I’ll return the verdict with the concrete findings and the manual reproductions.
exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '396,405p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   396	scope: Operate the `ai-structure-analysis` PR stack under ADR-006, sync Notion after each merge, and stop correctly at a visual/demo milestone even when CI is green.
   397	applies_to: cwd=/Users/Zhuanz/20260408 AI StructureAnalysis; reuse_rule=safe for this repo’s ADR-006 + Notion/GitHub control-plane workflow, but PR numbers and gate artifacts are rollout-specific.
   398	
   399	## Task 1: Merge ADR-006-approved PR stack and sync Notion task/session records
   400	
   401	### rollout_summary_files
   402	
   403	- rollout_summaries/2026-04-17T09-59-05-XzK5-ai_fea_adr006_autonomous_merges_smoke_e2e_demo_gate.md (cwd=/Users/Zhuanz/20260408 AI StructureAnalysis, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T17-59-05-019d9ae1-3a62-7232-9e44-28537fac30dd.jsonl, updated_at=2026-04-18T07:10:00+00:00, thread_id=019d9ae1-3a62-7232-9e44-28537fac30dd, merged PRs #1-#8 under ADR-006)
   404	
   405	### keywords

codex
CHANGES_REQUIRED

1. HIGH — Layer 2 is evaluating PR-controlled code and PR-controlled state, so the required check is self-bypassable. `.github/workflows/calibration-cap-check.yml:23-35,53-60` checks out the PR merge ref and then runs `scripts/compute_calibration_cap.py` and `scripts/extract_pr_self_pass_rate.py` from that checkout. A PR can therefore modify either script, or `reports/calibration_state.json`, and still make `calibration-cap-check` go green. That defeats the enforcement goal of ADR-013. Fix by evaluating trusted base-branch artifacts instead of the PR workspace, or by inlining the validation logic in the workflow. GitHub documents that `pull_request` workflows check out the PR merge branch by default: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows

2. HIGH — The extractor trust boundary is bypassable with hidden Markdown/HTML, so CI can parse a lower invisible claim while the visible PR body overclaims. `scripts/extract_pr_self_pass_rate.py:25-37` just finds the first matching heading and first `%` in the next 600 chars, without stripping HTML comments or fenced code blocks. I reproduced `## Self-pass-rate\n\n<!-- 30% -->\n\n95%` returning `30`, and a fenced-code fake section also returns the hidden value. The current tests in `tests/test_extract_pr_self_pass_rate.py:82-116` do not cover these adversarial cases. This needs a stricter parser plus tests for comments/code fences/multiple sections.

3. HIGH — PR #24’s fail-open on missing state is still present, and #25 amplifies it into a green required check. `.github/workflows/calibration-cap-check.yml:30-35,57-60` depends on `compute_calibration_cap.py`, whose `load_state()` returns `[]` when the state file is missing (`scripts/compute_calibration_cap.py:144-152` on PR #24; also codified in `tests/test_compute_calibration_cap.py:199-200`). I reproduced `python3 scripts/compute_calibration_cap.py --state /tmp/does-not-exist.json --check 95` exiting `0`. Once Layer 3 is on, a missing/renamed/wrongly checked-out state file silently degrades to `95% / OPTIONAL` and the required check passes when it should fail closed.

Notes:
- I do not see a shell-injection issue in `.github/workflows/calibration-cap-check.yml:43-60`; the PR body is passed through env + `printf` into Python, and only a numeric claim is written to `GITHUB_OUTPUT`.
- `M1 + M4 + M5` looks accurate for this PR.
- `scripts/apply_branch_protection.sh:24-46` is idempotent for the same payload; the blocking problem is that the status check it enforces is currently bypassable.

Verification:
- Ran `pytest -q tests/test_compute_calibration_cap.py tests/test_extract_pr_self_pass_rate.py tests/test_hf1_path_guard.py` on the stacked branch: `94 passed`.
- Manually reproduced the hidden-comment extractor bypass and the missing-state `95% / OPTIONAL` pass.


tokens used
146,681
CHANGES_REQUIRED

1. HIGH — Layer 2 is evaluating PR-controlled code and PR-controlled state, so the required check is self-bypassable. `.github/workflows/calibration-cap-check.yml:23-35,53-60` checks out the PR merge ref and then runs `scripts/compute_calibration_cap.py` and `scripts/extract_pr_self_pass_rate.py` from that checkout. A PR can therefore modify either script, or `reports/calibration_state.json`, and still make `calibration-cap-check` go green. That defeats the enforcement goal of ADR-013. Fix by evaluating trusted base-branch artifacts instead of the PR workspace, or by inlining the validation logic in the workflow. GitHub documents that `pull_request` workflows check out the PR merge branch by default: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows

2. HIGH — The extractor trust boundary is bypassable with hidden Markdown/HTML, so CI can parse a lower invisible claim while the visible PR body overclaims. `scripts/extract_pr_self_pass_rate.py:25-37` just finds the first matching heading and first `%` in the next 600 chars, without stripping HTML comments or fenced code blocks. I reproduced `## Self-pass-rate\n\n<!-- 30% -->\n\n95%` returning `30`, and a fenced-code fake section also returns the hidden value. The current tests in `tests/test_extract_pr_self_pass_rate.py:82-116` do not cover these adversarial cases. This needs a stricter parser plus tests for comments/code fences/multiple sections.

3. HIGH — PR #24’s fail-open on missing state is still present, and #25 amplifies it into a green required check. `.github/workflows/calibration-cap-check.yml:30-35,57-60` depends on `compute_calibration_cap.py`, whose `load_state()` returns `[]` when the state file is missing (`scripts/compute_calibration_cap.py:144-152` on PR #24; also codified in `tests/test_compute_calibration_cap.py:199-200`). I reproduced `python3 scripts/compute_calibration_cap.py --state /tmp/does-not-exist.json --check 95` exiting `0`. Once Layer 3 is on, a missing/renamed/wrongly checked-out state file silently degrades to `95% / OPTIONAL` and the required check passes when it should fail closed.

Notes:
- I do not see a shell-injection issue in `.github/workflows/calibration-cap-check.yml:43-60`; the PR body is passed through env + `printf` into Python, and only a numeric claim is written to `GITHUB_OUTPUT`.
- `M1 + M4 + M5` looks accurate for this PR.
- `scripts/apply_branch_protection.sh:24-46` is idempotent for the same payload; the blocking problem is that the status check it enforces is currently bypassable.

Verification:
- Ran `pytest -q tests/test_compute_calibration_cap.py tests/test_extract_pr_self_pass_rate.py tests/test_hf1_path_guard.py` on the stacked branch: `94 passed`.
- Manually reproduced the hidden-comment extractor bypass and the missing-state `95% / OPTIONAL` pass.


