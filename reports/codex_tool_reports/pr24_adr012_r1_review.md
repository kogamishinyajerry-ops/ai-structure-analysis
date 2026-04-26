2026-04-25T17:32:43.125166Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-25T17:32:43.125193Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/20260408 AI StructureAnalysis
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc5b3-6af6-7453-a205-a359bc117a99
--------
user
# CODE REVIEW REQUEST — PR #24

Repo: github.com/kogamishinyajerry-ops/ai-structure-analysis
Project context: AI-Structure-FEA — agentic FEA pipeline with Claude Code Opus 4.7 as the single development entry point per ADR-011 §T2.

ADR-011 §T2 mandatory M-triggers:
  M1 = governance text touched (docs/adr, docs/governance, docs/failure_patterns)
  M2 = executable assertions added
  M3 = HF compliance hot-zone touched
  M4 = governance → enforcement coupling
  M5 = self-pass-rate claim ≤ 50%

ADR-012 (this PR) introduces a rolling 5-PR window for self-pass-rate calibration:
  0/5 CR=95%, 1-2/5=80%, 3-4/5=50%, 5/5=30% BLOCKING
  Recovery: 2 trailing APPROVE = step up, 3 = reset to 95%

## Review request

Please review the diff below and produce one of:
  APPROVE / APPROVE_WITH_NOTES / CHANGES_REQUIRED

For each finding give: severity (HIGH/MEDIUM/LOW), location (file:line), description, suggested fix.
Special focus areas:
  1. Bootstrap correctness (5/5 CR initial state → 30% BLOCKING ceiling)
  2. Append-only schema integrity (reports/calibration_state.json v1)
  3. Test coverage of recovery paths (2-trailing-APPROVE step-up, 3-trailing reset)
  4. M-trigger flag accuracy (claim is M1+M2+M4+M5)
  5. CLI exit-code correctness in --check mode

## PR metadata
# [ADR-012] Calibration cap for T1 self-pass-rate (mechanical ceiling, BLOCKING bootstrap)

## Body
## Summary

Replaces RETRO-V61-001's honor-system self-pass-rate with a mechanically-derived ceiling computed from a rolling 5-PR window of Codex Round 1 outcomes. T1 cannot type a number; T1 reads one.

Per **AR-2026-04-25-001 §1** / **DEC-T0-2026-04-25-001** / sibling ADR-013 (branch protection, lands separately).

### Formula (canonical)

```
Base ceiling (per next PR), CR-of-last-5:
  0 → 95% optional · 1-2 → 80% recommended · 3-4 → 50% mandatory · 5 → 30% mandatory BLOCKING

Recovery (overrides base):
  2 trailing R1=APPROVE → step up one rung    (30→50, 50→80, 80→95)
  3 trailing R1=APPROVE → reset to 95
```

Outcome canon: `APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER` (NITS = APPROVE; BLOCKER = CHANGES_REQUIRED).

### Why this exists

Session 2026-04-25 produced empirical evidence that the honor-system fails:

| PR | T1 self-estimate | Codex R1 actual |
|---|---|---|
| #20 | 95% | CHANGES_REQUIRED (1 BLOCKER) |
| #18 | 95% | CHANGES_REQUIRED (1 HIGH) |
| #19 | 95% | CHANGES_REQUIRED (1 HIGH) |
| #21 | 90% | CHANGES_REQUIRED (1 HIGH) |
| #22 | 80% | CHANGES_REQUIRED (1 BLOCKER) |
| #23 | (n/a) | CHANGES_REQUIRED (3 BLOCKER + 1 SHOULD_FIX) |

T1 self-estimates were systematically wrong by 80-95 pp each across the same session. The retro-debit lag (next-cycle correction) is too slow.

## Files

- `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` (132 lines)
- `scripts/compute_calibration_cap.py` (229 lines · pure function + CLI: `--human`, `--check <claimed>`, JSON default)
- `tests/test_compute_calibration_cap.py` (42 unit tests · all rungs, recovery, BLOCKER/NITS canon, JSON output, edge cases)
- `reports/calibration_state.json` (append-only schema v1 · 6 entries: PR #18-#23)

## Bootstrap state at this PR's open

Last 5 = #19, #20, #21, #22, #23 — all `CHANGES_REQUIRED`.

```
T1 calibration ceiling : 30%
Codex pre-merge gate   : BLOCKING
Basis                  : 5 of last 5 = CHANGES_REQUIRED → ceiling 30%
State entries          : 6 (last 5 used)
```

**This PR therefore opens UNDER the 30%/BLOCKING regime that ADR-012 itself defines.** Pre-merge Codex review is **mandatory** per the ADR's own gate rules — not optional.

## Self-pass-rate (mechanically derived)

**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in `reports/calibration_state.json` last-5 window.

ADR-011 §T2 mandatory triggers (audited per AR-2026-04-25-001 §4):

- [x] **M1** — governance text added (`docs/adr/ADR-012-*.md` + supersedes-clause for RETRO-V61-001)
- [x] **M2** — non-trivial numerical computation (the rung-ladder formula, recovery thresholds, and the `--check` boundary semantics are factual numerical assertions)
- [x] **M4** — governance→enforcement translation (`compute_calibration_cap.py` is the validator implementing the rule; `calibration_state.json` is the schema-typed source of truth)
- [x] **M5** — PR opened while ceiling ≤ 50% (ceiling is 30; this PR opens under its own BLOCKING regime)
- [ ] M3 — no HF zone compliance claim made by this PR

Codex pre-merge is therefore mandatory on **two independent grounds**: ceiling-derived BLOCKING gate AND M1+M2+M4+M5 triggers. Either alone would suffice.

## Recovery path

To return to honor-system 95%:

- 1 R1=APPROVE → 4-of-5-CR → ceiling 50, MANDATORY non-blocking
- 2 trailing APPROVE → step-up to 80, RECOMMENDED
- 3 trailing APPROVE → reset to 95, OPTIONAL

Three clean PRs in a row restore honor-system. Mechanical, fast, evidence-grounded.

## Test plan

- [ ] **Pre-merge Codex review** (`/codex-gpt54`) — required by the ADR's own gate; review must reach R1=APPROVE before merge per the BLOCKING ceiling
- [x] `tests/test_compute_calibration_cap.py` — 42/42 passing locally (Python 3.9 + 3.11)
- [x] `tests/test_hf1_path_guard.py` — 30/30 passing locally
- [x] `python3 scripts/compute_calibration_cap.py --human` produces ceiling=30 BLOCKING
- [x] `python3 scripts/compute_calibration_cap.py --check 80` exits non-zero (claim above ceiling)
- [x] `python3 scripts/compute_calibration_cap.py --check 30` exits zero
- [ ] CI green on 3.11

## Out of scope

- ADR-013 (branch protection — the *enforcement* surface for this gate; sibling PR, lands separately)
- ADR-011 amendment for Codex M1-M5 reword: already shipped via PR #23 (e53b0f7)
- PR template integration (waits for ADR-013)
- CI hook calling `--check` against PR body claims (waits for ADR-013)

## Related

- Parent: ADR-011 (claude-code-takeover, ratified PR #17, amended PR #23)
- Sibling: ADR-013 (branch protection)
- T0 Decision: AR-2026-04-25-001 / DEC-T0-2026-04-25-001
- Supersedes (for AI-Structure-FEA only): RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## Stats
+775 -0

## Files
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
reports/calibration_state.json
scripts/compute_calibration_cap.py
tests/test_compute_calibration_cap.py

## DIFF (truncated to 750 lines if needed)
diff --git a/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md b/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
new file mode 100644
index 0000000..e948d14
--- /dev/null
+++ b/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
@@ -0,0 +1,132 @@
+# ADR-012: Calibration Cap for T1 Self-Pass-Rate
+
+- **Status:** Accepted
+- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
+- **Date:** 2026-04-25
+- **Supersedes:** RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system discipline (replaced for AI-Structure-FEA; other projects still under V61 may retain the honor-system version)
+- **Related:** ADR-011 (parent), ADR-013 (branch protection — sibling, lands separately), DEC-T0-2026-04-25-001 (Notion record)
+- **Branch:** `feature/AI-FEA-ADR-012-calibration-cap`
+
+---
+
+## Context
+
+ADR-011 ratified RETRO-V61-001's honor-system: T1 writes a self-pass-rate per PR; ≤70% triggers pre-merge Codex; high estimates that fail are retro-debited next cycle. Session 2026-04-25 produced empirical evidence that this honor-system fails:
+
+| PR | T1 self-estimate | Codex R1 actual outcome |
+|---|---|---|
+| #20 revert | 95% | CHANGES_REQUIRED · 1 BLOCKER (direction inversion) |
+| #18 FF-02 | 95% | CHANGES_REQUIRED · 1 HIGH (over-claim + unflagged prescription) |
+| #19 FF-05 | 95% | CHANGES_REQUIRED · 1 HIGH (stale post-merge state) |
+| #21 chore | 90% | CHANGES_REQUIRED · 1 HIGH (open-PRs underreport) |
+| #22 FF-06 | 80% | CHANGES_REQUIRED · 1 BLOCKER (rename/delete bypass) |
+
+Empirical R1-pass-rate: **0/5 = 0%**. T1 self-estimates were systematically wrong by 80-95 percentage points each, *across the same session*. T0's diagnostic in AR-2026-04-25-001 §1: "this is not noise; it is the predictable failure mode of any honor-system metric where the rater and the rated party are the same agent in the same context window." The discipline cannot self-correct mid-session — T1 wrote "95%" five times in a row while Codex was actively contradicting it.
+
+The retro-debit lag (next-cycle correction) is also too slow: by the time the retro lands, multiple PRs have already shipped with mis-calibrated confidence, and T1's session-end summary inherits the over-confidence as part of its training signal.
+
+## Decision
+
+Self-pass-rate becomes a **mechanically-derived ceiling** based on a rolling window of the last 5 PRs' Codex Round 1 outcomes. T1 cannot type a number; T1 reads a number computed by `scripts/compute_calibration_cap.py` from the append-only state file `reports/calibration_state.json`.
+
+### Formula (canonical, ratified in AR-2026-04-25-001 §1)
+
+```
+Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR PRs excluded)
+Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
+                 (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
+
+Base ceiling (per next PR):
+  0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
+  1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
+  3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
+  5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
+
+Recovery (override on top of base):
+  2 consecutive R1=APPROVE  → ceiling steps up one rung from base
+  3 consecutive R1=APPROVE  → ceiling returns to 95%
+```
+
+Rung ladder is `30 → 50 → 80 → 95` (`step_up` saturates at 95).
+
+### Codex gate derivation from final ceiling
+
+| Ceiling | Mandatory Codex pre-merge | Blocking |
+|---|---|---|
+| 30 | yes | **yes** (no T1 self-merge; needs t0-approved or external review) |
+| 50 | yes | no |
+| 80 | no (recommended) | no |
+| 95 | no (optional) | no |
+
+Independently of the ceiling, ADR-011 §T2 amendments (M1-M5 triggers — governance text, sign/direction math, HF compliance claims, governance→enforcement translations, and any PR opened while ceiling ≤ 50%) may still mandate Codex review.
+
+## Implementation contract
+
+**Sources of truth:**
+
+- `reports/calibration_state.json` — append-only state file, schema v1. Each entry: `{pr, sha, title, merged_at, r1_outcome, r1_severity, r1_review_report, notes}`. Authoritative for the formula's input.
+- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes.
+- `tests/test_compute_calibration_cap.py` — 42 unit tests covering each rung, recovery transitions, BLOCKER/NITS canon, edge cases, JSON output.
+
+**T1 invocation surface:**
+
+- At session-start, T1 runs `python3 scripts/compute_calibration_cap.py --human` and renders the result in the `MODEL COMPLIANCE CHECK` block of every reply that initiates work.
+- The PR template (in `.github/PULL_REQUEST_TEMPLATE.md` once branch protection lands per ADR-013) prefills the `Self-pass-rate` field by calling the script. The field is **read-only** to T1.
+- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.
+
+**State maintenance:**
+
+After each PR merges, the maintainer (T1 or T0) appends a new entry to `reports/calibration_state.json` with the actual R1 outcome. Entry SHOULD be added in the same PR as housekeeping or in the next PR's first commit. State updates do NOT themselves count as PRs in the formula — the formula counts PRs that touched code/governance content.
+
+## Bootstrap state (initial 5 entries)
+
+Per AR-2026-04-25-001 §1, initialize from PRs #18-#22 (PR #17 excluded as the ADR-011 baseline establishment). All 5 are `CHANGES_REQUIRED` per session 2026-04-25 record:
+
+| PR | SHA | R1 outcome | R1 severity |
+|---|---|---|---|
+| #18 | `77e6813` | CHANGES_REQUIRED | 1 HIGH + 3 MEDIUM |
+| #19 | `4a64cfd` | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM |
+| #20 | `9362f6d` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
+| #21 | `2bbf0f1` | CHANGES_REQUIRED | 1 HIGH |
+| #22 | `ac98fc3` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
+
+Resulting ceiling at ADR-012 land: **30%, MANDATORY pre-merge Codex, BLOCKING**.
+
+This means ADR-012 itself (this PR), ADR-013, and ADR-011 amendments all open under the 30% blocking regime. That is exactly correct given the empirical record.
+
+## Recovery path
+
+To return to the 95% honor-system regime from the bootstrap 30%, T1 needs:
+
+- **One** R1=APPROVE PR after this one → state `4 of last 5 = CR` → ceiling 50, MANDATORY but not blocking
+- **Two consecutive** R1=APPROVE → recovery clause overrides base → ceiling steps from `4 of 5 → base 50` to step-up `80`, RECOMMENDED only
+- **Three consecutive** R1=APPROVE → recovery clause resets ceiling to 95, OPTIONAL
+
+In other words: three clean PRs in a row, no R1 BLOCKER/HIGH, restores honor-system. The formula is forgiving but evidence-grounded.
+
+## Consequences
+
+**Intended:**
+
+- T1's self-rated confidence becomes irrelevant to ceiling derivation. Calibration error cannot affect the gate.
+- Ceiling = leading indicator (predicts likely R1 outcome) rather than RETRO-V61-001's lagging indicator (corrects after the fact).
+- Recovery is mechanical and fast (3 clean PRs ≈ 1-2 sessions of clean work), so T1 isn't permanently penalized for one bad session.
+- Bootstrap 30%/BLOCKING for the immediate next 3 PRs (ADR-012, ADR-013, ADR-011 amendment) is exactly what the empirical record warrants.
+
+**Acknowledged:**
+
+- The recovery thresholds (2 → step up, 3 → reset) are reasonable but not empirically grounded yet (T0 self-rated 88% on this clause). Revisit after 10 more PRs of post-ADR-012 data; either ratify or tighten via ADR-012 amendment.
+- The formula assumes Codex R1 quality is stable. If Codex itself becomes lenient over time (NITS-with-ulterior-motive or APPROVE-without-checking), the formula's signal degrades. This is a Codex-quality concern, not an ADR-012 concern, but should be tracked.
+- "Last 5" is small enough that one anomalous session can flip the ceiling. A larger window (10 or 20) is statistically more robust but slower to respond. T0's choice of 5 prioritizes responsiveness; revisit if ceiling thrashes after the bootstrap recovery completes.
+- Cross-project portability: the formula assumes Codex is the de facto reviewer (per ADR-011 §T2). Projects without Codex must adapt the canon (e.g., human review verdict).
+
+**Out of scope:**
+
+- ADR-013 (branch protection) is the surface that *enforces* the gate (a 30%-blocking ceiling means nothing if T1 can self-merge anyway). ADR-012 is the calibration math; ADR-013 is the access-control wrapper. They are sibling ADRs landed in the same session under the same T0 verdict.
+- Codex role rewording (anti-shenanigans backstop, M1-M5 triggers) is part of the ADR-011 amendment PR, not ADR-012.
+
+## Open follow-ups
+
+- Add CI step calling `compute_calibration_cap.py --check` against PR body's claim, after `.github/PULL_REQUEST_TEMPLATE.md` lands (in ADR-013's batch).
+- After 10 post-ADR-012 PRs, write a calibration-stability retro: confirm or amend recovery thresholds based on empirical thrashing rate.
+- Notion control plane: DEC-T0-2026-04-25-001 captures this ADR; future ADR-012 amendments must update the same DEC entry.
diff --git a/reports/calibration_state.json b/reports/calibration_state.json
new file mode 100644
index 0000000..6580e7c
--- /dev/null
+++ b/reports/calibration_state.json
@@ -0,0 +1,80 @@
+{
+  "schema_version": 1,
+  "established_by": "ADR-012 / AR-2026-04-25-001 / DEC-T0-2026-04-25-001",
+  "doc": "Append-only state for T1 calibration cap. Entries ordered by PR number (monotonic with merge time on this repo). Last 5 entries determine the ceiling per AR-2026-04-25-001 §1 formula. Pre-ADR-011-baseline PRs excluded; PR #17 (the ADR-011 establishment) is also excluded as bootstrap baseline per T0 verdict.",
+  "outcome_canon": "APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)",
+  "entries": [
+    {
+      "pr": 18,
+      "sha": "77e6813",
+      "title": "[FF-02] FailurePattern attribution for GS-001/002/003",
+      "merged_at": "2026-04-25T08:53:09Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH + 3 MEDIUM",
+      "r1_review_report": "reports/codex_tool_reports/ff02_r1_review.md",
+      "notes": "Over-claim/prescription, gs_artifact_pin placeholder, HF3 cite inconsistency, README severity scope"
+    },
+    {
+      "pr": 19,
+      "sha": "4a64cfd",
+      "title": "[FF-05] Seed .planning/STATE.md as repo-side execution snapshot",
+      "merged_at": "2026-04-25T08:56:46Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH + 1 MEDIUM",
+      "r1_review_report": "reports/codex_tool_reports/ff05_r1_review.md",
+      "notes": "STATE.md still pre-push state (FF-01/FF-02 listed as pending); invented ADR-012/013 references"
+    },
+    {
+      "pr": 20,
+      "sha": "9362f6d",
+      "title": "Revert direct-push 815945c, preserve portable-path fixes",
+      "merged_at": "2026-04-25T08:33:51Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
+      "r1_review_report": "reports/codex_tool_reports/revert_815945c_r1_review.md",
+      "notes": "Revert direction inversion (re-introduced /Users/Zhuanz/ paths); commit message factual error; CI claim overstated"
+    },
+    {
+      "pr": 21,
+      "sha": "2bbf0f1",
+      "title": "chore: post-merge cleanup — STATE.md + Codex review archive",
+      "merged_at": "2026-04-25T10:30:14Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "STATE.md Active branches/Open PRs sections underreported (P1-* PRs #11-#16 missing); R1 review still in /tmp/, awaits next housekeeping cycle"
+    },
+    {
+      "pr": 22,
+      "sha": "ac98fc3",
+      "title": "[FF-06] pre-commit path-guard for HF1 forbidden zone",
+      "merged_at": "2026-04-25T10:43:55Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "pre-commit pass_filenames misses rename old-paths and deletes (silent HF1 bypass); HF1.6 over-blocks Makefile other targets; override audit trail unenforceable"
+    },
+    {
+      "pr": 23,
+      "sha": "e53b0f7",
+      "title": "[ADR-011] T0 amendments AR-2026-04-25-001 (T2 + HF1 + HF2 + numbering)",
+      "merged_at": "2026-04-25T12:06:52Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "3 BLOCKER + 1 SHOULD_FIX",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "ADR-011 amendments PR — Codex R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit e96904d, then merged after CI green. R1 review report still pending archive into reports/codex_tool_reports/."
+    }
+  ],
+  "computed_at_bootstrap": {
+    "last_5_cr_count": 5,
+    "trailing_approve_count": 0,
+    "base_ceiling": 30,
+    "final_ceiling": 30,
+    "mandatory_codex": true,
+    "blocking": true,
+    "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%"
+  }
+}
diff --git a/scripts/compute_calibration_cap.py b/scripts/compute_calibration_cap.py
new file mode 100644
index 0000000..bbf46d6
--- /dev/null
+++ b/scripts/compute_calibration_cap.py
@@ -0,0 +1,229 @@
+#!/usr/bin/env python3
+"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).
+
+Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
+derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
+T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
+self-pass field by calling this script; the field is read-only to T1.
+
+Formula (canonical, ratified in AR-2026-04-25-001 §1):
+
+    Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR excluded)
+    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
+                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
+
+    Base ceiling (per next PR):
+      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
+      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
+      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
+      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
+
+    Recovery (override):
+      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
+      3 consecutive R1=APPROVE  → ceiling returns to 95%
+
+Invocations:
+    python3 scripts/compute_calibration_cap.py
+        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
+    python3 scripts/compute_calibration_cap.py --human
+        emits human-readable summary to stdout
+    python3 scripts/compute_calibration_cap.py --check <CEILING>
+        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)
+
+State source: reports/calibration_state.json (append-only). State file is the
+single source of truth; this script is a pure function over its contents.
+
+Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
+(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
+revisit after 10 more PRs of post-ADR-012 data.
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+import sys
+from dataclasses import dataclass
+from pathlib import Path
+
+# Canonical: NITS counts as APPROVE; everything else counts as CHANGES_REQUIRED.
+APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})
+
+# Rung ladder, low → high. Recovery moves one index up.
+RUNGS: tuple[int, ...] = (30, 50, 80, 95)
+
+
+@dataclass(frozen=True)
+class CalibrationResult:
+    ceiling: int
+    mandatory_codex: bool
+    blocking: bool
+    basis: str
+    entry_count: int
+
+
+def step_up(ceiling: int) -> int:
+    """Move ceiling one rung up (saturate at 95)."""
+    if ceiling not in RUNGS:
+        raise ValueError(f"unknown ceiling rung: {ceiling}")
+    idx = RUNGS.index(ceiling)
+    return RUNGS[min(idx + 1, len(RUNGS) - 1)]
+
+
+def base_ceiling_from_cr_count(cr_count: int) -> int:
+    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.
+
+    Per AR-2026-04-25-001 §1.
+    """
+    if cr_count < 0:
+        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
+    if cr_count == 0:
+        return 95
+    if cr_count <= 2:
+        return 80
+    if cr_count <= 4:
+        return 50
+    return 30
+
+
+def trailing_approve_count(outcomes: list[str]) -> int:
+    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
+    n = 0
+    for o in reversed(outcomes):
+        if o in APPROVE_OUTCOMES:
+            n += 1
+        else:
+            break
+    return n
+
+
+def compute_calibration(outcomes: list[str]) -> CalibrationResult:
+    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
+    last5 = outcomes[-5:]
+    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
+    base = base_ceiling_from_cr_count(cr_count)
+    trailing = trailing_approve_count(outcomes)
+
+    if trailing >= 3:
+        ceiling = 95
+        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
+    elif trailing >= 2:
+        stepped = step_up(base)
+        ceiling = stepped
+        basis = (
+            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
+            f"2 trailing APPROVE → step up to {ceiling}%"
+        )
+    else:
+        ceiling = base
+        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"
+
+    # Codex gate derivation from final ceiling
+    if ceiling <= 30:
+        mandatory_codex = True
+        blocking = True
+    elif ceiling <= 50:
+        mandatory_codex = True
+        blocking = False
+    else:
+        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
+        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
+        # Codex independently of the ceiling.
+        mandatory_codex = False
+        blocking = False
+
+    return CalibrationResult(
+        ceiling=ceiling,
+        mandatory_codex=mandatory_codex,
+        blocking=blocking,
+        basis=basis,
+        entry_count=len(outcomes),
+    )
+
+
+def load_state(state_path: Path) -> list[str]:
+    """Read calibration_state.json and return chronologically-ordered R1 outcomes.
+
+    Empty file (or missing file) yields an empty list, which by formula maps
+    to ceiling 95% (the "0 of last 5" branch). Callers must distinguish
+    "no history" from "all-good history" by inspecting the returned length.
+    """
+    if not state_path.exists():
+        return []
+    with state_path.open() as f:
+        data = json.load(f)
+    entries = data.get("entries", [])
+    # Order by PR number (monotonic with merge time on this repo).
+    entries_sorted = sorted(entries, key=lambda e: e.get("pr", 0))
+    return [e.get("r1_outcome", "CHANGES_REQUIRED") for e in entries_sorted]
+
+
+def gate_label(result: CalibrationResult) -> str:
+    if result.blocking:
+        return "BLOCKING"
+    if result.mandatory_codex:
+        return "MANDATORY"
+    if result.ceiling <= 80:
+        return "RECOMMENDED"
+    return "OPTIONAL"
+
+
+def main(argv: list[str]) -> int:
+    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
+    parser = argparse.ArgumentParser(
+        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
+    )
+    parser.add_argument(
+        "--human",
+        action="store_true",
+        help="emit human-readable summary instead of JSON",
+    )
+    parser.add_argument(
+        "--check",
+        type=int,
+        metavar="CEILING",
+        help="exit 1 if claimed CEILING exceeds the computed ceiling",
+    )
+    parser.add_argument(
+        "--state",
+        type=Path,
+        default=default_state,
+        help=f"path to calibration_state.json (default: {default_state})",
+    )
+    args = parser.parse_args(argv[1:])
+
+    outcomes = load_state(args.state)
+    result = compute_calibration(outcomes)
+
+    if args.check is not None:
+        if args.check > result.ceiling:
+            sys.stderr.write(
+                f"calibration check FAILED: claimed {args.check}% exceeds "
+                f"computed ceiling {result.ceiling}%\n"
+                f"  basis: {result.basis}\n"
+                f"  Codex gate: {gate_label(result)}\n"
+            )
+            return 1
+        return 0
+
+    if args.human:
+        print(f"T1 calibration ceiling : {result.ceiling}%")
+        print(f"Codex pre-merge gate   : {gate_label(result)}")
+        print(f"Basis                  : {result.basis}")
+        print(f"State entries          : {result.entry_count} (last 5 used)")
+    else:
+        out = {
+            "ceiling": result.ceiling,
+            "mandatory_codex": result.mandatory_codex,
+            "blocking": result.blocking,
+            "basis": result.basis,
+            "entry_count": result.entry_count,
+            "gate_label": gate_label(result),
+        }
+        print(json.dumps(out, ensure_ascii=False))
+
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_compute_calibration_cap.py b/tests/test_compute_calibration_cap.py
new file mode 100644
index 0000000..86201bb
--- /dev/null
+++ b/tests/test_compute_calibration_cap.py
@@ -0,0 +1,334 @@
+"""Tests for scripts/compute_calibration_cap.py (ADR-012)."""
+
+from __future__ import annotations
+
+import json
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
+def _load_calc():
+    import compute_calibration_cap  # type: ignore[import-not-found]
+
+    return compute_calibration_cap
+
+
+@pytest.fixture(scope="module")
+def calc():
+    return _load_calc()
+
+
+# ---------------------------------------------------------------------------
+# step_up
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "input_ceiling,expected",
+    [(30, 50), (50, 80), (80, 95), (95, 95)],
+)
+def test_step_up_each_rung(calc, input_ceiling, expected):
+    assert calc.step_up(input_ceiling) == expected
+
+
+def test_step_up_rejects_unknown_ceiling(calc):
+    with pytest.raises(ValueError, match="unknown ceiling rung"):
+        calc.step_up(42)
+
+
+# ---------------------------------------------------------------------------
+# base_ceiling_from_cr_count
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "cr_count,expected",
+    [
+        (0, 95),
+        (1, 80),
+        (2, 80),
+        (3, 50),
+        (4, 50),
+        (5, 30),
+    ],
+)
+def test_base_ceiling_each_count(calc, cr_count, expected):
+    assert calc.base_ceiling_from_cr_count(cr_count) == expected
+
+
+def test_base_ceiling_rejects_negative(calc):
+    with pytest.raises(ValueError, match="cr_count must be >= 0"):
+        calc.base_ceiling_from_cr_count(-1)
+
+
+# ---------------------------------------------------------------------------
+# trailing_approve_count
+# ---------------------------------------------------------------------------
+
+
+def test_trailing_approve_empty(calc):
+    assert calc.trailing_approve_count([]) == 0
+
+
+def test_trailing_approve_no_trailing(calc):
+    assert calc.trailing_approve_count(["APPROVE", "CHANGES_REQUIRED"]) == 0
+
+
+def test_trailing_approve_single(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE"]) == 1
+
+
+def test_trailing_approve_two(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE"]) == 2
+
+
+def test_trailing_approve_three(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]) == 3
+
+
+def test_trailing_approve_all_approve(calc):
+    assert calc.trailing_approve_count(["APPROVE"] * 5) == 5
+
+
+def test_trailing_approve_nits_counts_as_approve(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE_WITH_NITS", "APPROVE"]) == 2
+
+
+def test_trailing_approve_blocker_breaks(calc):
+    assert calc.trailing_approve_count(["APPROVE", "BLOCKER", "APPROVE"]) == 1
+
+
+# ---------------------------------------------------------------------------
+# compute_calibration — bootstrap and steady-state scenarios
+# ---------------------------------------------------------------------------
+
+
+def test_compute_bootstrap_5_cr_yields_30_blocking(calc):
+    """Session 2026-04-25 bootstrap: 5/5 CHANGES_REQUIRED → ceiling 30, blocking."""
+    r = calc.compute_calibration(["CHANGES_REQUIRED"] * 5)
+    assert r.ceiling == 30
+    assert r.mandatory_codex is True
+    assert r.blocking is True
+    assert "5 of last 5" in r.basis
+
+
+def test_compute_ideal_5_approve_yields_95_optional(calc):
+    r = calc.compute_calibration(["APPROVE"] * 5)
+    assert r.ceiling == 95
+    assert r.mandatory_codex is False
+    assert r.blocking is False
+
+
+def test_compute_two_cr_three_approve_recovery_step_up(calc):
+    """3-trailing-APPROVE recovery overrides base ceiling to 95."""
+    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    # base would be 80 (2 of 5 = CR), but 3 trailing approve → recovery = 95
+    assert r.ceiling == 95
+    assert "recovery" in r.basis
+
+
+def test_compute_three_cr_two_approve_step_up_one_rung(calc):
+    """2-trailing-APPROVE recovery moves base 50 → 80."""
+    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    # base = 50 (3 of 5 = CR), 2 trailing → step up to 80
+    assert r.ceiling == 80
+    assert r.mandatory_codex is False
+
+
+def test_compute_four_cr_one_approve_no_recovery(calc):
+    """1-trailing-APPROVE is below 2 threshold; ceiling stays at base."""
+    outcomes = ["CHANGES_REQUIRED"] * 4 + ["APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    # base = 50 (4 of 5 = CR), 1 trailing → no recovery
+    assert r.ceiling == 50
+    assert r.mandatory_codex is True
+    assert r.blocking is False
+
+
+def test_compute_more_than_5_uses_only_last_5(calc):
+    """Window is last 5 entries; older entries do not affect base count."""
+    # 7 entries: first 2 are APPROVE, last 5 are all CR
+    outcomes = ["APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 30  # last 5 are all CR
+
+
+def test_compute_trailing_approve_uses_full_history(calc):
+    """Trailing-APPROVE count uses the entire history, not just last 5."""
+    # Last 5 = all CR, but trailing 0 APPROVE; ceiling 30
+    outcomes = ["APPROVE", "APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 30
+
+
+def test_compute_empty_history_yields_95(calc):
+    """No PRs yet → 0 of last 5 = CR → ceiling 95 (honor system)."""
+    r = calc.compute_calibration([])
+    assert r.ceiling == 95
+    assert r.mandatory_codex is False
+    assert r.blocking is False
+
+
+def test_compute_blocker_counts_as_changes_required(calc):
+    """BLOCKER outcome must count as CHANGES_REQUIRED for the formula."""
+    r = calc.compute_calibration(["BLOCKER"] * 5)
+    assert r.ceiling == 30
+    assert r.blocking is True
+
+
+def test_compute_nits_counts_as_approve(calc):
+    """APPROVE_WITH_NITS must count as APPROVE for the formula."""
+    r = calc.compute_calibration(["APPROVE_WITH_NITS"] * 5)
+    assert r.ceiling == 95
+
+
+# ---------------------------------------------------------------------------
+# load_state
+# ---------------------------------------------------------------------------
+
+
+def test_load_state_missing_file_returns_empty(calc, tmp_path):
+    assert calc.load_state(tmp_path / "nonexistent.json") == []
+
+
+def test_load_state_reads_chronologically(calc, tmp_path):
+    """Entries must be sorted by PR number regardless of file order."""
+    state = {
+        "schema_version": 1,
+        "entries": [
+            {"pr": 22, "r1_outcome": "BLOCKER"},
+            {"pr": 18, "r1_outcome": "APPROVE"},
+            {"pr": 20, "r1_outcome": "CHANGES_REQUIRED"},
+        ],
+    }
+    state_path = tmp_path / "calibration_state.json"
+    state_path.write_text(json.dumps(state))
+    outcomes = calc.load_state(state_path)
+    assert outcomes == ["APPROVE", "CHANGES_REQUIRED", "BLOCKER"]  # sorted by pr
+
+
+def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
+    """The real reports/calibration_state.json must yield 30/BLOCKING
+    as long as the last 5 R1 outcomes are CHANGES_REQUIRED.
+
+    Entry count grows monotonically as PRs land — locking it would mean
+    every PR breaks this test. The invariant is the ceiling, not the row count.
+    """
+    state_path = _REPO_ROOT / "reports" / "calibration_state.json"
+    outcomes = calc.load_state(state_path)
+    assert len(outcomes) >= 5, "state file must have at least 5 bootstrap entries"
+    last_5 = outcomes[-5:]
+    if all(o in ("CHANGES_REQUIRED", "BLOCKER") for o in last_5):
+        r = calc.compute_calibration(outcomes)
+        assert r.ceiling == 30
+        assert r.blocking is True
+
+
+# ---------------------------------------------------------------------------
+# gate_label
+# ---------------------------------------------------------------------------
+
+
+def test_gate_label_blocking(calc):
+    r = calc.CalibrationResult(
+        ceiling=30, mandatory_codex=True, blocking=True, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "BLOCKING"
+
+
+def test_gate_label_mandatory(calc):
+    r = calc.CalibrationResult(
+        ceiling=50, mandatory_codex=True, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "MANDATORY"
+
+
+def test_gate_label_recommended(calc):
+    r = calc.CalibrationResult(
+        ceiling=80, mandatory_codex=False, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "RECOMMENDED"
+
+
+def test_gate_label_optional(calc):
+    r = calc.CalibrationResult(
+        ceiling=95, mandatory_codex=False, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "OPTIONAL"
+
+
+# ---------------------------------------------------------------------------
+# main() — JSON / human / --check
+# ---------------------------------------------------------------------------
+
+
+def test_main_json_output(calc, tmp_path, capsys):
+    state = {
+        "schema_version": 1,
+        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
+    }
+    state_path = tmp_path / "s.json"
+    state_path.write_text(json.dumps(state))
+    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
+    assert rc == 0
+    out = json.loads(capsys.readouterr().out)
+    assert out["ceiling"] == 30
+    assert out["mandatory_codex"] is True

codex
Reviewing PR #24 against the actual repo files and the requested focus areas. I’ll inspect the touched files first, then verify the calculation and `--check` behavior with targeted test runs so the verdict is based on the implementation, not just the PR body.
exec
/bin/zsh -lc "pwd && git status --short && rg --files . | rg '"'^(docs/adr/ADR-012|reports/calibration_state'"\\.json|scripts/compute_calibration_cap\\.py|tests/test_compute_calibration_cap\\.py)"'$'"'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
/Users/Zhuanz/20260408 AI StructureAnalysis

exec
/bin/zsh -lc 'nl -ba scripts/compute_calibration_cap.py' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'nl -ba tests/test_compute_calibration_cap.py' in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
nl: scripts/compute_calibration_cap.py: No such file or directory

 exited 1 in 0ms:
nl: tests/test_compute_calibration_cap.py: No such file or directory

exec
/bin/zsh -lc 'nl -ba reports/calibration_state.json' in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
nl: reports/calibration_state.json: No such file or directory

exec
/bin/zsh -lc 'nl -ba docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md' in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
nl: docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md: No such file or directory

codex
The requested paths are not present in the current checkout, so I’m verifying whether this workspace has the PR branch or only a different snapshot. I’ll map the repo root and branch state next, then review against the diff you supplied if the branch contents are not available locally.
exec
/bin/zsh -lc 'git rev-parse --show-toplevel' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/Users/Zhuanz/20260408 AI StructureAnalysis

exec
/bin/zsh -lc "rg --files . | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
./run_well_harness.py
./reports/hf2_calibration.md
./reports/codex_tool_reports/adr_011_r4_review.md
./reports/codex_tool_reports/revert_815945c_r2_review.md
./reports/codex_tool_reports/adr_011_r2_review.md
./reports/codex_tool_reports/adr_011_r5_review.md
./reports/codex_tool_reports/ff05_r1_review.md
./reports/codex_tool_reports/adr_011_r3_review.md
./reports/codex_tool_reports/ff02_r1_review.md
./reports/codex_tool_reports/ff05_r2_review.md
./reports/codex_tool_reports/ff02_r2_review.md
./reports/codex_tool_reports/adr_011_r1_review.md
./reports/codex_tool_reports/revert_815945c_r1_review.md
./runs/.gitkeep
./reporters/markdown.py
./reporters/__init__.py
./reporters/vtp.py
./calculix_cases/cantilever_beam/cantilever_beam.12d
./calculix_cases/cantilever_beam/cantilever_beam.inp
./templates/linear_static.inp.j2
./templates/cantilever_static.inp.j2
./prompts/architect_golden_prompt.md
./scripts/install_dependencies.sh
./scripts/hf1_path_guard.py
./persistence/__init__.py
./persistence/checkpointer.py
./PHASE1_SPRINT1_COMPLETION.md
./run_tests.sh
./README.md
./schemas/sim_state.py
./schemas/__init__.py
./schemas/sim_plan.py
./golden_samples/GS002_Enhanced_Report.png
./golden_samples/GS001_Enhanced_Report.png
./golden_samples/GS002_Scientific_Report.png
./golden_samples/make_gs003_report.py
./golden_samples/gs002_detailed_report.py
./golden_samples/gs001_detailed_report.py
./golden_samples/gs003_structure_diagram.png
./golden_samples/GS-001/gs001.inp
./golden_samples/GS-001/README.md
./golden_samples/GS-001/expected_results.json
./golden_samples/GS-001/cantilever_theory.py
./golden_samples/make_gs002_report.py
./golden_samples/gs_analysis_dashboard.png
./golden_samples/gs003_stress_distribution.png
./golden_samples/GS001_Scientific_Report.png
./golden_samples/GS003_Scientific_Report.png
./golden_samples/make_reports.py
./golden_samples/gs003_detailed_report.py
./golden_samples/visualization_report.py
./golden_samples/gs002_structure_diagram.png
./golden_samples/GS-003/gs003.inp
./golden_samples/GS-003/README.md
./golden_samples/GS-003/expected_results.json
./golden_samples/GS-003/gs003.12d
./golden_samples/GS-003/plane_stress_theory.py
./golden_samples/gs002_comparison.png
./golden_samples/GS-002/gs002.inp
./golden_samples/GS-002/README.md
./golden_samples/GS-002/expected_results.json
./golden_samples/GS-002/truss_theory.py
./golden_samples/GS-002/gs002.12d
./docs/sprint2_demo.md
./docs/sprint1_report.md
./docs/sprint2_benchmark_report.md
./docs/benchmark_report.md
./docs/PHASE1_SPRINT2_COMPLETION.md
./Makefile
./docs/failure_patterns/FP-002-gs002-truss-element-substitution.md
./Dockerfile
./docs/sprint1_completion_summary.md
./docs/architecture.md
./pyproject.toml
./docs/sprint2_report.md
./docs/demo_summary.md
./docs/quickstart.md
./docs/failure_patterns/README.md
./docs/failure_patterns/FP-003-gs003-missing-hole-and-bc-direction.md
./docs/failure_patterns/FP-001-gs001-cantilever-spec-fork.md
./sync_well_harness_approvals.py
./config/well_harness_control_plane.yaml
./config/well_harness_control_plane.yaml.example
./agents/human_fallback.py
./docs/adr/ADR-011-pivot-claude-code-takeover.md
./docs/well_harness_architecture.md
./agents/viz.py
./agents/router.py
./agents/geometry.py
./agents/reviewer.py
./agents/architect.py
./agents/mesh.py
./agents/llm.py
./agents/__init__.py
./agents/graph.py
./agents/solver.py
./checkers/jacobian.py
./checkers/__init__.py
./checkers/geometry_checker.py
./docs/visualization/gs_summary.png
./docs/visualization/gs001_deformation.png
./docs/visualization/gs003_plane_stress_analysis.png
./docs/visualization/gs001_cloud_plots.png
./docs/visualization/gs001_distribution.png
./docs/visualization/gs002_truss_analysis.png
./tools/frd_parser.py
./tools/__init__.py
./tools/freecad_driver.py
./tools/calculix_driver.py
./tools/gmsh_driver.py
./tests/conftest.py
./tests/test_vtp_reporter.py
./tests/test_rag_coverage_audit.py
./tests/test_rag_preflight_publish.py
./tests/test_architect.py
./tests/test_github_writeback.py
./tests/test_rag_query_cli.py
./tests/test_viz_agent.py
./tests/test_human_fallback.py
./tests/test_rag_advise_cli.py
./tests/test_freecad_driver.py
./tests/test_rag_knowledge_base.py
./tests/test_rag_cli.py
./tests/test_schemas.py
./tests/test_solver_agent.py
./tests/test_reviewer_agent.py
./tests/test_geometry_agent.py
./tests/test_hf1_path_guard.py
./tests/test_toolchain_probes.py
./tests/test_calculix_driver.py
./tests/test_checkpointer.py
./tests/test_rag_source_project_governance.py
./tests/test_frd_parser.py
./tests/test_stub_imports.py
./tests/test_markdown_reporter.py
./tests/__init__.py
./tests/test_jacobian.py
./tests/test_rag_source_gs_theory.py
./tests/test_gmsh_driver.py
./tests/test_router.py
./tests/test_rag_preflight_summary.py
./tests/test_cold_smoke_e2e.py
./tests/test_geometry_checker.py
./tests/test_rag_reviewer_advisor.py
./tests/test_rag_preflight_publish_cli.py
./tests/test_mesh_agent.py
./frontend/src/assets/react.svg
./frontend/src/assets/vite.svg
./frontend/src/assets/hero.png
./backend/tests/test_golden_samples.py
./backend/tests/test_compliance.py
./backend/tests/test_api.py
./backend/tests/test_solver.py
./backend/tests/test_well_harness_notion_sync.py
./backend/tests/test_report.py
./backend/tests/__init__.py
./backend/tests/test_parsers.py
./backend/tests/conftest.py
./backend/tests/test_well_harness.py
./backend/requirements.txt
./backend/pytest.ini
./frontend/src/components/ComplianceBadge.tsx
./frontend/src/components/ModeSelector.tsx
./frontend/src/components/ChatPanel.tsx
./frontend/src/components/ProjectManager.tsx
./frontend/src/components/SensitivityForm.tsx
./frontend/src/index.css
./frontend/src/App.css
./frontend/src/main.tsx
./frontend/src/App.tsx
./frontend/vite.config.ts
./frontend/eslint.config.js
./frontend/tsconfig.json
./frontend/package.json
./frontend/package-lock.json
./frontend/public/favicon.svg
./frontend/public/icons.svg
./frontend/README.md
./frontend/tsconfig.app.json
./frontend/index.html
./frontend/tsconfig.node.json
./backend/app/services/analysis_service.py
./backend/app/services/report_generator.py
./backend/app/services/sensitivity.py
./backend/app/services/visualization.py
./backend/app/services/case_service.py
./backend/app/services/rule_engine.py
./backend/app/services/copilot.py
./backend/app/services/pdf_service.py
./backend/app/services/solver.py
./backend/app/services/knowledge_base.py
./backend/app/main.py
./backend/app/rag/preflight_summary.py
./backend/app/rag/coverage_audit.py
./backend/app/rag/advise_cli.py
./backend/app/rag/reviewer_advisor.py
./backend/app/rag/embedder.py
./backend/app/rag/sources/project_governance.py
./backend/app/rag/sources/README.md
./backend/app/rag/sources/__init__.py

exec
/bin/zsh -lc 'git branch --show-current' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
feature/AI-FEA-P1-04b-cli-json-symmetry

exec
/bin/zsh -lc 'git status --short' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
codex
This checkout is on a different local feature branch and does not contain the PR #24 files. I’m checking whether the remote PR branch is available so I can validate against the real branch contents instead of only the pasted diff.
exec
/bin/zsh -lc 'git remote -v' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (fetch)
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (push)

exec
/bin/zsh -lc "git branch -a | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
  chore/AI-FEA-fp-status-applied
+ dark-eclipse-streaks-01h22-20260423
  feature/AI-FEA-ADR-012-calibration-cap
  feature/AI-FEA-ADR-013-branch-protection
  feature/AI-FEA-FF-07-trailer-check
  feature/AI-FEA-FF-08-gs-registry
  feature/AI-FEA-FF-09-readme-adr-011-sync
  feature/AI-FEA-P0-02-langgraph
  feature/AI-FEA-P0-03-notion-sync
  feature/AI-FEA-P0-04-architect-agent
  feature/AI-FEA-P0-04-architect-agent-fix
  feature/AI-FEA-P0-05-geometry-agent
  feature/AI-FEA-P0-06-mesh-agent
  feature/AI-FEA-P0-07-solver-agent
  feature/AI-FEA-P0-08-reviewer-agent
  feature/AI-FEA-P0-08-reviewer-agent-stale
  feature/AI-FEA-P0-09-viz-analysis-fix
  feature/AI-FEA-P1-02-hot-smoke
  feature/AI-FEA-P1-03-golden-sample-validation
* feature/AI-FEA-P1-04b-cli-json-symmetry
  feature/AI-FEA-P1-04b-cli-runner
  feature/AI-FEA-P1-04b-coverage-audit
  feature/AI-FEA-P1-04b-query-cli
  feature/AI-FEA-P1-04b-rag-knowledge-base
  feature/AI-FEA-P1-04b-source4-adrs-fps
  feature/AI-FEA-P1-04b-source5-gs-theory
  feature/AI-FEA-P1-05-reviewer-fault-injection
  feature/AI-FEA-P1-05b-advise-cli
  feature/AI-FEA-P1-05b-reviewer-rag-advisor
  feature/AI-FEA-P1-06-gate-solve-lint
  feature/AI-FEA-P1-06b-wire-linter-solver
  feature/AI-FEA-P1-07-simplan-adapter
  feature/AI-FEA-P1-07-surrogate-hook
  feature/AI-FEA-P1-08-preflight-publish
  feature/AI-FEA-P1-08-preflight-publish-cli
  feature/AI-FEA-P1-08-preflight-summary
  feature/AI-FEA-P1-08-preflight-upsert
  feature/AI-FEA-P1-08-publish-cli-json
  feature/AI-FEA-P2-github-writeback
  feature/AI-FEA-P2-writeback-integration
  feature/AI-FEA-S2.1-02-notion-sync-contract-align
  fix/AI-FEA-gs-status-flip-fp001-002-003
  main
  remotes/origin/HEAD -> origin/main
  remotes/origin/chore/AI-FEA-fp-status-applied
  remotes/origin/feature/AI-FEA-ADR-012-calibration-cap
  remotes/origin/feature/AI-FEA-ADR-013-branch-protection
  remotes/origin/feature/AI-FEA-FF-07-trailer-check
  remotes/origin/feature/AI-FEA-FF-08-gs-registry
  remotes/origin/feature/AI-FEA-FF-09-readme-adr-011-sync
  remotes/origin/feature/AI-FEA-P0-01-repo-skeleton
  remotes/origin/feature/AI-FEA-P0-02-langgraph
  remotes/origin/feature/AI-FEA-P0-03-notion-sync
  remotes/origin/feature/AI-FEA-P0-04-architect-agent
  remotes/origin/feature/AI-FEA-P0-04-architect-agent-fix
  remotes/origin/feature/AI-FEA-P0-05-geometry-agent
  remotes/origin/feature/AI-FEA-P0-06-mesh-agent
  remotes/origin/feature/AI-FEA-P0-07-solver-agent
  remotes/origin/feature/AI-FEA-P0-08-reviewer-agent
  remotes/origin/feature/AI-FEA-P0-09-viz-analysis
  remotes/origin/feature/AI-FEA-P0-09-viz-analysis-fix
  remotes/origin/feature/AI-FEA-P1-02-hot-smoke
  remotes/origin/feature/AI-FEA-P1-03-golden-sample-validation
  remotes/origin/feature/AI-FEA-P1-04a-rag-audit
  remotes/origin/feature/AI-FEA-P1-04b-cli-json-symmetry
  remotes/origin/feature/AI-FEA-P1-04b-cli-runner
  remotes/origin/feature/AI-FEA-P1-04b-coverage-audit
  remotes/origin/feature/AI-FEA-P1-04b-query-cli
  remotes/origin/feature/AI-FEA-P1-04b-rag-knowledge-base
  remotes/origin/feature/AI-FEA-P1-04b-source4-adrs-fps
  remotes/origin/feature/AI-FEA-P1-04b-source5-gs-theory
  remotes/origin/feature/AI-FEA-P1-05-reviewer-fault-injection
  remotes/origin/feature/AI-FEA-P1-05b-advise-cli
  remotes/origin/feature/AI-FEA-P1-05b-reviewer-rag-advisor
  remotes/origin/feature/AI-FEA-P1-06-gate-solve-lint
  remotes/origin/feature/AI-FEA-P1-06b-wire-linter-solver
  remotes/origin/feature/AI-FEA-P1-07-simplan-adapter
  remotes/origin/feature/AI-FEA-P1-07-surrogate-hook
  remotes/origin/feature/AI-FEA-P1-08-preflight-publish
  remotes/origin/feature/AI-FEA-P1-08-preflight-publish-cli
  remotes/origin/feature/AI-FEA-P1-08-preflight-summary
  remotes/origin/feature/AI-FEA-P1-08-preflight-upsert
  remotes/origin/feature/AI-FEA-P1-08-publish-cli-json
  remotes/origin/feature/AI-FEA-P2-github-writeback
  remotes/origin/feature/AI-FEA-P2-writeback-integration
  remotes/origin/feature/AI-FEA-S2.1-02-notion-sync-contract-align
  remotes/origin/feature/AI-FEA-S2.1-03-gha-workflow
  remotes/origin/fix/AI-FEA-gs-status-flip-fp001-002-003
  remotes/origin/main

exec
/bin/zsh -lc "git ls-remote --heads origin 'feature/*ADR-012*' 'refs/pull/24/head'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 1728ms:
5c21247cb4ca93ba65dff75c3a1e26ecbdb8e661	refs/heads/feature/AI-FEA-ADR-012-calibration-cap

codex
The ADR-012 branch is available locally, so I can review the real branch contents now. I’m pulling the exact branch diff and file line numbers next, then I’ll run the focused test file and a few CLI probes against that branch in an isolated worktree.
exec
/bin/zsh -lc 'git diff --name-only main...feature/AI-FEA-ADR-012-calibration-cap' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'git diff --stat main...feature/AI-FEA-ADR-012-calibration-cap' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
 ...DR-012-calibration-cap-for-t1-self-pass-rate.md | 132 ++++++++
 reports/calibration_state.json                     |  80 +++++
 scripts/compute_calibration_cap.py                 | 229 ++++++++++++++
 tests/test_compute_calibration_cap.py              | 334 +++++++++++++++++++++
 4 files changed, 775 insertions(+)

 succeeded in 0ms:
docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
reports/calibration_state.json
scripts/compute_calibration_cap.py
tests/test_compute_calibration_cap.py

exec
/bin/zsh -lc 'git show feature/AI-FEA-ADR-012-calibration-cap:scripts/compute_calibration_cap.py | nl -ba' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	#!/usr/bin/env python3
     2	"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).
     3	
     4	Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
     5	derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
     6	T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
     7	self-pass field by calling this script; the field is read-only to T1.
     8	
     9	Formula (canonical, ratified in AR-2026-04-25-001 §1):
    10	
    11	    Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR excluded)
    12	    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
    13	                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
    14	
    15	    Base ceiling (per next PR):
    16	      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
    17	      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
    18	      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
    19	      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
    20	
    21	    Recovery (override):
    22	      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
    23	      3 consecutive R1=APPROVE  → ceiling returns to 95%
    24	
    25	Invocations:
    26	    python3 scripts/compute_calibration_cap.py
    27	        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
    28	    python3 scripts/compute_calibration_cap.py --human
    29	        emits human-readable summary to stdout
    30	    python3 scripts/compute_calibration_cap.py --check <CEILING>
    31	        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)
    32	
    33	State source: reports/calibration_state.json (append-only). State file is the
    34	single source of truth; this script is a pure function over its contents.
    35	
    36	Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
    37	(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
    38	revisit after 10 more PRs of post-ADR-012 data.
    39	"""
    40	
    41	from __future__ import annotations
    42	
    43	import argparse
    44	import json
    45	import sys
    46	from dataclasses import dataclass
    47	from pathlib import Path
    48	
    49	# Canonical: NITS counts as APPROVE; everything else counts as CHANGES_REQUIRED.
    50	APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})
    51	
    52	# Rung ladder, low → high. Recovery moves one index up.
    53	RUNGS: tuple[int, ...] = (30, 50, 80, 95)
    54	
    55	
    56	@dataclass(frozen=True)
    57	class CalibrationResult:
    58	    ceiling: int
    59	    mandatory_codex: bool
    60	    blocking: bool
    61	    basis: str
    62	    entry_count: int
    63	
    64	
    65	def step_up(ceiling: int) -> int:
    66	    """Move ceiling one rung up (saturate at 95)."""
    67	    if ceiling not in RUNGS:
    68	        raise ValueError(f"unknown ceiling rung: {ceiling}")
    69	    idx = RUNGS.index(ceiling)
    70	    return RUNGS[min(idx + 1, len(RUNGS) - 1)]
    71	
    72	
    73	def base_ceiling_from_cr_count(cr_count: int) -> int:
    74	    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.
    75	
    76	    Per AR-2026-04-25-001 §1.
    77	    """
    78	    if cr_count < 0:
    79	        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
    80	    if cr_count == 0:
    81	        return 95
    82	    if cr_count <= 2:
    83	        return 80
    84	    if cr_count <= 4:
    85	        return 50
    86	    return 30
    87	
    88	
    89	def trailing_approve_count(outcomes: list[str]) -> int:
    90	    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
    91	    n = 0
    92	    for o in reversed(outcomes):
    93	        if o in APPROVE_OUTCOMES:
    94	            n += 1
    95	        else:
    96	            break
    97	    return n
    98	
    99	
   100	def compute_calibration(outcomes: list[str]) -> CalibrationResult:
   101	    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
   102	    last5 = outcomes[-5:]
   103	    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
   104	    base = base_ceiling_from_cr_count(cr_count)
   105	    trailing = trailing_approve_count(outcomes)
   106	
   107	    if trailing >= 3:
   108	        ceiling = 95
   109	        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
   110	    elif trailing >= 2:
   111	        stepped = step_up(base)
   112	        ceiling = stepped
   113	        basis = (
   114	            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
   115	            f"2 trailing APPROVE → step up to {ceiling}%"
   116	        )
   117	    else:
   118	        ceiling = base
   119	        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"
   120	
   121	    # Codex gate derivation from final ceiling
   122	    if ceiling <= 30:
   123	        mandatory_codex = True
   124	        blocking = True
   125	    elif ceiling <= 50:
   126	        mandatory_codex = True
   127	        blocking = False
   128	    else:
   129	        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
   130	        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
   131	        # Codex independently of the ceiling.
   132	        mandatory_codex = False
   133	        blocking = False
   134	
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
   221	            "gate_label": gate_label(result),
   222	        }
   223	        print(json.dumps(out, ensure_ascii=False))
   224	
   225	    return 0
   226	
   227	
   228	if __name__ == "__main__":
   229	    sys.exit(main(sys.argv))

exec
/bin/zsh -lc 'git show feature/AI-FEA-ADR-012-calibration-cap:reports/calibration_state.json | nl -ba' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	{
     2	  "schema_version": 1,
     3	  "established_by": "ADR-012 / AR-2026-04-25-001 / DEC-T0-2026-04-25-001",
     4	  "doc": "Append-only state for T1 calibration cap. Entries ordered by PR number (monotonic with merge time on this repo). Last 5 entries determine the ceiling per AR-2026-04-25-001 §1 formula. Pre-ADR-011-baseline PRs excluded; PR #17 (the ADR-011 establishment) is also excluded as bootstrap baseline per T0 verdict.",
     5	  "outcome_canon": "APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)",
     6	  "entries": [
     7	    {
     8	      "pr": 18,
     9	      "sha": "77e6813",
    10	      "title": "[FF-02] FailurePattern attribution for GS-001/002/003",
    11	      "merged_at": "2026-04-25T08:53:09Z",
    12	      "r1_outcome": "CHANGES_REQUIRED",
    13	      "r1_severity": "1 HIGH + 3 MEDIUM",
    14	      "r1_review_report": "reports/codex_tool_reports/ff02_r1_review.md",
    15	      "notes": "Over-claim/prescription, gs_artifact_pin placeholder, HF3 cite inconsistency, README severity scope"
    16	    },
    17	    {
    18	      "pr": 19,
    19	      "sha": "4a64cfd",
    20	      "title": "[FF-05] Seed .planning/STATE.md as repo-side execution snapshot",
    21	      "merged_at": "2026-04-25T08:56:46Z",
    22	      "r1_outcome": "CHANGES_REQUIRED",
    23	      "r1_severity": "1 HIGH + 1 MEDIUM",
    24	      "r1_review_report": "reports/codex_tool_reports/ff05_r1_review.md",
    25	      "notes": "STATE.md still pre-push state (FF-01/FF-02 listed as pending); invented ADR-012/013 references"
    26	    },
    27	    {
    28	      "pr": 20,
    29	      "sha": "9362f6d",
    30	      "title": "Revert direct-push 815945c, preserve portable-path fixes",
    31	      "merged_at": "2026-04-25T08:33:51Z",
    32	      "r1_outcome": "CHANGES_REQUIRED",
    33	      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
    34	      "r1_review_report": "reports/codex_tool_reports/revert_815945c_r1_review.md",
    35	      "notes": "Revert direction inversion (re-introduced /Users/Zhuanz/ paths); commit message factual error; CI claim overstated"
    36	    },
    37	    {
    38	      "pr": 21,
    39	      "sha": "2bbf0f1",
    40	      "title": "chore: post-merge cleanup — STATE.md + Codex review archive",
    41	      "merged_at": "2026-04-25T10:30:14Z",
    42	      "r1_outcome": "CHANGES_REQUIRED",
    43	      "r1_severity": "1 HIGH",
    44	      "r1_review_report": null,
    45	      "r1_review_report_pending_archive": true,
    46	      "notes": "STATE.md Active branches/Open PRs sections underreported (P1-* PRs #11-#16 missing); R1 review still in /tmp/, awaits next housekeeping cycle"
    47	    },
    48	    {
    49	      "pr": 22,
    50	      "sha": "ac98fc3",
    51	      "title": "[FF-06] pre-commit path-guard for HF1 forbidden zone",
    52	      "merged_at": "2026-04-25T10:43:55Z",
    53	      "r1_outcome": "CHANGES_REQUIRED",
    54	      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
    55	      "r1_review_report": null,
    56	      "r1_review_report_pending_archive": true,
    57	      "notes": "pre-commit pass_filenames misses rename old-paths and deletes (silent HF1 bypass); HF1.6 over-blocks Makefile other targets; override audit trail unenforceable"
    58	    },
    59	    {
    60	      "pr": 23,
    61	      "sha": "e53b0f7",
    62	      "title": "[ADR-011] T0 amendments AR-2026-04-25-001 (T2 + HF1 + HF2 + numbering)",
    63	      "merged_at": "2026-04-25T12:06:52Z",
    64	      "r1_outcome": "CHANGES_REQUIRED",
    65	      "r1_severity": "3 BLOCKER + 1 SHOULD_FIX",
    66	      "r1_review_report": null,
    67	      "r1_review_report_pending_archive": true,
    68	      "notes": "ADR-011 amendments PR — Codex R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit e96904d, then merged after CI green. R1 review report still pending archive into reports/codex_tool_reports/."
    69	    }
    70	  ],
    71	  "computed_at_bootstrap": {
    72	    "last_5_cr_count": 5,
    73	    "trailing_approve_count": 0,
    74	    "base_ceiling": 30,
    75	    "final_ceiling": 30,
    76	    "mandatory_codex": true,
    77	    "blocking": true,
    78	    "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%"
    79	  }
    80	}

exec
/bin/zsh -lc 'git show feature/AI-FEA-ADR-012-calibration-cap:docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md | nl -ba' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'git show feature/AI-FEA-ADR-012-calibration-cap:tests/test_compute_calibration_cap.py | nl -ba' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	# ADR-012: Calibration Cap for T1 Self-Pass-Rate
     2	
     3	- **Status:** Accepted
     4	- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
     5	- **Date:** 2026-04-25
     6	- **Supersedes:** RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system discipline (replaced for AI-Structure-FEA; other projects still under V61 may retain the honor-system version)
     7	- **Related:** ADR-011 (parent), ADR-013 (branch protection — sibling, lands separately), DEC-T0-2026-04-25-001 (Notion record)
     8	- **Branch:** `feature/AI-FEA-ADR-012-calibration-cap`
     9	
    10	---
    11	
    12	## Context
    13	
    14	ADR-011 ratified RETRO-V61-001's honor-system: T1 writes a self-pass-rate per PR; ≤70% triggers pre-merge Codex; high estimates that fail are retro-debited next cycle. Session 2026-04-25 produced empirical evidence that this honor-system fails:
    15	
    16	| PR | T1 self-estimate | Codex R1 actual outcome |
    17	|---|---|---|
    18	| #20 revert | 95% | CHANGES_REQUIRED · 1 BLOCKER (direction inversion) |
    19	| #18 FF-02 | 95% | CHANGES_REQUIRED · 1 HIGH (over-claim + unflagged prescription) |
    20	| #19 FF-05 | 95% | CHANGES_REQUIRED · 1 HIGH (stale post-merge state) |
    21	| #21 chore | 90% | CHANGES_REQUIRED · 1 HIGH (open-PRs underreport) |
    22	| #22 FF-06 | 80% | CHANGES_REQUIRED · 1 BLOCKER (rename/delete bypass) |
    23	
    24	Empirical R1-pass-rate: **0/5 = 0%**. T1 self-estimates were systematically wrong by 80-95 percentage points each, *across the same session*. T0's diagnostic in AR-2026-04-25-001 §1: "this is not noise; it is the predictable failure mode of any honor-system metric where the rater and the rated party are the same agent in the same context window." The discipline cannot self-correct mid-session — T1 wrote "95%" five times in a row while Codex was actively contradicting it.
    25	
    26	The retro-debit lag (next-cycle correction) is also too slow: by the time the retro lands, multiple PRs have already shipped with mis-calibrated confidence, and T1's session-end summary inherits the over-confidence as part of its training signal.
    27	
    28	## Decision
    29	
    30	Self-pass-rate becomes a **mechanically-derived ceiling** based on a rolling window of the last 5 PRs' Codex Round 1 outcomes. T1 cannot type a number; T1 reads a number computed by `scripts/compute_calibration_cap.py` from the append-only state file `reports/calibration_state.json`.
    31	
    32	### Formula (canonical, ratified in AR-2026-04-25-001 §1)
    33	
    34	```
    35	Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR PRs excluded)
    36	Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
    37	                 (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
    38	
    39	Base ceiling (per next PR):
    40	  0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
    41	  1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
    42	  3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
    43	  5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
    44	
    45	Recovery (override on top of base):
    46	  2 consecutive R1=APPROVE  → ceiling steps up one rung from base
    47	  3 consecutive R1=APPROVE  → ceiling returns to 95%
    48	```
    49	
    50	Rung ladder is `30 → 50 → 80 → 95` (`step_up` saturates at 95).
    51	
    52	### Codex gate derivation from final ceiling
    53	
    54	| Ceiling | Mandatory Codex pre-merge | Blocking |
    55	|---|---|---|
    56	| 30 | yes | **yes** (no T1 self-merge; needs t0-approved or external review) |
    57	| 50 | yes | no |
    58	| 80 | no (recommended) | no |
    59	| 95 | no (optional) | no |
    60	
    61	Independently of the ceiling, ADR-011 §T2 amendments (M1-M5 triggers — governance text, sign/direction math, HF compliance claims, governance→enforcement translations, and any PR opened while ceiling ≤ 50%) may still mandate Codex review.
    62	
    63	## Implementation contract
    64	
    65	**Sources of truth:**
    66	
    67	- `reports/calibration_state.json` — append-only state file, schema v1. Each entry: `{pr, sha, title, merged_at, r1_outcome, r1_severity, r1_review_report, notes}`. Authoritative for the formula's input.
    68	- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes.
    69	- `tests/test_compute_calibration_cap.py` — 42 unit tests covering each rung, recovery transitions, BLOCKER/NITS canon, edge cases, JSON output.
    70	
    71	**T1 invocation surface:**
    72	
    73	- At session-start, T1 runs `python3 scripts/compute_calibration_cap.py --human` and renders the result in the `MODEL COMPLIANCE CHECK` block of every reply that initiates work.
    74	- The PR template (in `.github/PULL_REQUEST_TEMPLATE.md` once branch protection lands per ADR-013) prefills the `Self-pass-rate` field by calling the script. The field is **read-only** to T1.
    75	- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.
    76	
    77	**State maintenance:**
    78	
    79	After each PR merges, the maintainer (T1 or T0) appends a new entry to `reports/calibration_state.json` with the actual R1 outcome. Entry SHOULD be added in the same PR as housekeeping or in the next PR's first commit. State updates do NOT themselves count as PRs in the formula — the formula counts PRs that touched code/governance content.
    80	
    81	## Bootstrap state (initial 5 entries)
    82	
    83	Per AR-2026-04-25-001 §1, initialize from PRs #18-#22 (PR #17 excluded as the ADR-011 baseline establishment). All 5 are `CHANGES_REQUIRED` per session 2026-04-25 record:
    84	
    85	| PR | SHA | R1 outcome | R1 severity |
    86	|---|---|---|---|
    87	| #18 | `77e6813` | CHANGES_REQUIRED | 1 HIGH + 3 MEDIUM |
    88	| #19 | `4a64cfd` | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM |
    89	| #20 | `9362f6d` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
    90	| #21 | `2bbf0f1` | CHANGES_REQUIRED | 1 HIGH |
    91	| #22 | `ac98fc3` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
    92	
    93	Resulting ceiling at ADR-012 land: **30%, MANDATORY pre-merge Codex, BLOCKING**.
    94	
    95	This means ADR-012 itself (this PR), ADR-013, and ADR-011 amendments all open under the 30% blocking regime. That is exactly correct given the empirical record.
    96	
    97	## Recovery path
    98	
    99	To return to the 95% honor-system regime from the bootstrap 30%, T1 needs:
   100	
   101	- **One** R1=APPROVE PR after this one → state `4 of last 5 = CR` → ceiling 50, MANDATORY but not blocking
   102	- **Two consecutive** R1=APPROVE → recovery clause overrides base → ceiling steps from `4 of 5 → base 50` to step-up `80`, RECOMMENDED only
   103	- **Three consecutive** R1=APPROVE → recovery clause resets ceiling to 95, OPTIONAL
   104	
   105	In other words: three clean PRs in a row, no R1 BLOCKER/HIGH, restores honor-system. The formula is forgiving but evidence-grounded.
   106	
   107	## Consequences
   108	
   109	**Intended:**
   110	
   111	- T1's self-rated confidence becomes irrelevant to ceiling derivation. Calibration error cannot affect the gate.
   112	- Ceiling = leading indicator (predicts likely R1 outcome) rather than RETRO-V61-001's lagging indicator (corrects after the fact).
   113	- Recovery is mechanical and fast (3 clean PRs ≈ 1-2 sessions of clean work), so T1 isn't permanently penalized for one bad session.
   114	- Bootstrap 30%/BLOCKING for the immediate next 3 PRs (ADR-012, ADR-013, ADR-011 amendment) is exactly what the empirical record warrants.
   115	
   116	**Acknowledged:**
   117	
   118	- The recovery thresholds (2 → step up, 3 → reset) are reasonable but not empirically grounded yet (T0 self-rated 88% on this clause). Revisit after 10 more PRs of post-ADR-012 data; either ratify or tighten via ADR-012 amendment.
   119	- The formula assumes Codex R1 quality is stable. If Codex itself becomes lenient over time (NITS-with-ulterior-motive or APPROVE-without-checking), the formula's signal degrades. This is a Codex-quality concern, not an ADR-012 concern, but should be tracked.
   120	- "Last 5" is small enough that one anomalous session can flip the ceiling. A larger window (10 or 20) is statistically more robust but slower to respond. T0's choice of 5 prioritizes responsiveness; revisit if ceiling thrashes after the bootstrap recovery completes.
   121	- Cross-project portability: the formula assumes Codex is the de facto reviewer (per ADR-011 §T2). Projects without Codex must adapt the canon (e.g., human review verdict).
   122	
   123	**Out of scope:**
   124	
   125	- ADR-013 (branch protection) is the surface that *enforces* the gate (a 30%-blocking ceiling means nothing if T1 can self-merge anyway). ADR-012 is the calibration math; ADR-013 is the access-control wrapper. They are sibling ADRs landed in the same session under the same T0 verdict.
   126	- Codex role rewording (anti-shenanigans backstop, M1-M5 triggers) is part of the ADR-011 amendment PR, not ADR-012.
   127	
   128	## Open follow-ups
   129	
   130	- Add CI step calling `compute_calibration_cap.py --check` against PR body's claim, after `.github/PULL_REQUEST_TEMPLATE.md` lands (in ADR-013's batch).
   131	- After 10 post-ADR-012 PRs, write a calibration-stability retro: confirm or amend recovery thresholds based on empirical thrashing rate.
   132	- Notion control plane: DEC-T0-2026-04-25-001 captures this ADR; future ADR-012 amendments must update the same DEC entry.

 succeeded in 0ms:
     1	"""Tests for scripts/compute_calibration_cap.py (ADR-012)."""
     2	
     3	from __future__ import annotations
     4	
     5	import json
     6	import sys
     7	from pathlib import Path
     8	
     9	import pytest
    10	
    11	_REPO_ROOT = Path(__file__).resolve().parent.parent
    12	_SCRIPTS_DIR = _REPO_ROOT / "scripts"
    13	if str(_SCRIPTS_DIR) not in sys.path:
    14	    sys.path.insert(0, str(_SCRIPTS_DIR))
    15	
    16	
    17	def _load_calc():
    18	    import compute_calibration_cap  # type: ignore[import-not-found]
    19	
    20	    return compute_calibration_cap
    21	
    22	
    23	@pytest.fixture(scope="module")
    24	def calc():
    25	    return _load_calc()
    26	
    27	
    28	# ---------------------------------------------------------------------------
    29	# step_up
    30	# ---------------------------------------------------------------------------
    31	
    32	
    33	@pytest.mark.parametrize(
    34	    "input_ceiling,expected",
    35	    [(30, 50), (50, 80), (80, 95), (95, 95)],
    36	)
    37	def test_step_up_each_rung(calc, input_ceiling, expected):
    38	    assert calc.step_up(input_ceiling) == expected
    39	
    40	
    41	def test_step_up_rejects_unknown_ceiling(calc):
    42	    with pytest.raises(ValueError, match="unknown ceiling rung"):
    43	        calc.step_up(42)
    44	
    45	
    46	# ---------------------------------------------------------------------------
    47	# base_ceiling_from_cr_count
    48	# ---------------------------------------------------------------------------
    49	
    50	
    51	@pytest.mark.parametrize(
    52	    "cr_count,expected",
    53	    [
    54	        (0, 95),
    55	        (1, 80),
    56	        (2, 80),
    57	        (3, 50),
    58	        (4, 50),
    59	        (5, 30),
    60	    ],
    61	)
    62	def test_base_ceiling_each_count(calc, cr_count, expected):
    63	    assert calc.base_ceiling_from_cr_count(cr_count) == expected
    64	
    65	
    66	def test_base_ceiling_rejects_negative(calc):
    67	    with pytest.raises(ValueError, match="cr_count must be >= 0"):
    68	        calc.base_ceiling_from_cr_count(-1)
    69	
    70	
    71	# ---------------------------------------------------------------------------
    72	# trailing_approve_count
    73	# ---------------------------------------------------------------------------
    74	
    75	
    76	def test_trailing_approve_empty(calc):
    77	    assert calc.trailing_approve_count([]) == 0
    78	
    79	
    80	def test_trailing_approve_no_trailing(calc):
    81	    assert calc.trailing_approve_count(["APPROVE", "CHANGES_REQUIRED"]) == 0
    82	
    83	
    84	def test_trailing_approve_single(calc):
    85	    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE"]) == 1
    86	
    87	
    88	def test_trailing_approve_two(calc):
    89	    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE"]) == 2
    90	
    91	
    92	def test_trailing_approve_three(calc):
    93	    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]) == 3
    94	
    95	
    96	def test_trailing_approve_all_approve(calc):
    97	    assert calc.trailing_approve_count(["APPROVE"] * 5) == 5
    98	
    99	
   100	def test_trailing_approve_nits_counts_as_approve(calc):
   101	    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE_WITH_NITS", "APPROVE"]) == 2
   102	
   103	
   104	def test_trailing_approve_blocker_breaks(calc):
   105	    assert calc.trailing_approve_count(["APPROVE", "BLOCKER", "APPROVE"]) == 1
   106	
   107	
   108	# ---------------------------------------------------------------------------
   109	# compute_calibration — bootstrap and steady-state scenarios
   110	# ---------------------------------------------------------------------------
   111	
   112	
   113	def test_compute_bootstrap_5_cr_yields_30_blocking(calc):
   114	    """Session 2026-04-25 bootstrap: 5/5 CHANGES_REQUIRED → ceiling 30, blocking."""
   115	    r = calc.compute_calibration(["CHANGES_REQUIRED"] * 5)
   116	    assert r.ceiling == 30
   117	    assert r.mandatory_codex is True
   118	    assert r.blocking is True
   119	    assert "5 of last 5" in r.basis
   120	
   121	
   122	def test_compute_ideal_5_approve_yields_95_optional(calc):
   123	    r = calc.compute_calibration(["APPROVE"] * 5)
   124	    assert r.ceiling == 95
   125	    assert r.mandatory_codex is False
   126	    assert r.blocking is False
   127	
   128	
   129	def test_compute_two_cr_three_approve_recovery_step_up(calc):
   130	    """3-trailing-APPROVE recovery overrides base ceiling to 95."""
   131	    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]
   132	    r = calc.compute_calibration(outcomes)
   133	    # base would be 80 (2 of 5 = CR), but 3 trailing approve → recovery = 95
   134	    assert r.ceiling == 95
   135	    assert "recovery" in r.basis
   136	
   137	
   138	def test_compute_three_cr_two_approve_step_up_one_rung(calc):
   139	    """2-trailing-APPROVE recovery moves base 50 → 80."""
   140	    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE"]
   141	    r = calc.compute_calibration(outcomes)
   142	    # base = 50 (3 of 5 = CR), 2 trailing → step up to 80
   143	    assert r.ceiling == 80
   144	    assert r.mandatory_codex is False
   145	
   146	
   147	def test_compute_four_cr_one_approve_no_recovery(calc):
   148	    """1-trailing-APPROVE is below 2 threshold; ceiling stays at base."""
   149	    outcomes = ["CHANGES_REQUIRED"] * 4 + ["APPROVE"]
   150	    r = calc.compute_calibration(outcomes)
   151	    # base = 50 (4 of 5 = CR), 1 trailing → no recovery
   152	    assert r.ceiling == 50
   153	    assert r.mandatory_codex is True
   154	    assert r.blocking is False
   155	
   156	
   157	def test_compute_more_than_5_uses_only_last_5(calc):
   158	    """Window is last 5 entries; older entries do not affect base count."""
   159	    # 7 entries: first 2 are APPROVE, last 5 are all CR
   160	    outcomes = ["APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
   161	    r = calc.compute_calibration(outcomes)
   162	    assert r.ceiling == 30  # last 5 are all CR
   163	
   164	
   165	def test_compute_trailing_approve_uses_full_history(calc):
   166	    """Trailing-APPROVE count uses the entire history, not just last 5."""
   167	    # Last 5 = all CR, but trailing 0 APPROVE; ceiling 30
   168	    outcomes = ["APPROVE", "APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
   169	    r = calc.compute_calibration(outcomes)
   170	    assert r.ceiling == 30
   171	
   172	
   173	def test_compute_empty_history_yields_95(calc):
   174	    """No PRs yet → 0 of last 5 = CR → ceiling 95 (honor system)."""
   175	    r = calc.compute_calibration([])
   176	    assert r.ceiling == 95
   177	    assert r.mandatory_codex is False
   178	    assert r.blocking is False
   179	
   180	
   181	def test_compute_blocker_counts_as_changes_required(calc):
   182	    """BLOCKER outcome must count as CHANGES_REQUIRED for the formula."""
   183	    r = calc.compute_calibration(["BLOCKER"] * 5)
   184	    assert r.ceiling == 30
   185	    assert r.blocking is True
   186	
   187	
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

exec
/bin/zsh -lc 'tmpdir=$(mktemp -d /tmp/adr012-review.XXXXXX) && echo "$tmpdir" && git worktree add --detach "$tmpdir" feature/AI-FEA-ADR-012-calibration-cap' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 131ms:
HEAD is now at 5c21247 [ADR-012] housekeeping: append PR #23 entry, harden bootstrap test

codex
I have the PR branch mounted in an isolated worktree now. Next step is execution: the focused unit suite plus the exact CLI paths called out in the PR body, so any verdict on bootstrap, recovery, and `--check` behavior is grounded in observed results.
exec
/bin/zsh -lc 'python3 -m pytest tests/test_compute_calibration_cap.py -q' in /tmp/adr012-review.GW7sje
exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py --human' in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
T1 calibration ceiling : 30%
Codex pre-merge gate   : BLOCKING
Basis                  : 5 of last 5 = CHANGES_REQUIRED → ceiling 30%
State entries          : 6 (last 5 used)

exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py --check 80; echo EXIT:$?' in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
calibration check FAILED: claimed 80% exceeds computed ceiling 30%
  basis: 5 of last 5 = CHANGES_REQUIRED → ceiling 30%
  Codex gate: BLOCKING
EXIT:1

exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py --check 30; echo EXIT:$?' in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
EXIT:0

 succeeded in 447ms:
..........................................                               [100%]
42 passed in 0.06s

codex
I found one likely correctness risk in the implementation and I’m probing it directly now: the loader reorders entries by PR number, not merge order. I’m also checking the fail-open behavior when the state file is missing, because that affects `--check` enforcement in CI.
exec
/bin/zsh -lc "python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
import compute_calibration_cap as c
actual_merge_order = ['CHANGES_REQUIRED', 'APPROVE', 'APPROVE']
wrong_pr_sorted_order = ['APPROVE', 'CHANGES_REQUIRED', 'APPROVE']
for label, outcomes in [('actual', actual_merge_order), ('pr_sorted', wrong_pr_sorted_order)]:
    r = c.compute_calibration(outcomes)
    print(label, outcomes, '=>', {'ceiling': r.ceiling, 'basis': r.basis, 'blocking': r.blocking, 'mandatory': r.mandatory_codex})
PY" in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
actual ['CHANGES_REQUIRED', 'APPROVE', 'APPROVE'] => {'ceiling': 95, 'basis': '1 of last 5 = CHANGES_REQUIRED (base 80%) + 2 trailing APPROVE → step up to 95%', 'blocking': False, 'mandatory': False}
pr_sorted ['APPROVE', 'CHANGES_REQUIRED', 'APPROVE'] => {'ceiling': 80, 'basis': '1 of last 5 = CHANGES_REQUIRED → ceiling 80%', 'blocking': False, 'mandatory': False}

exec
/bin/zsh -lc 'python3 scripts/compute_calibration_cap.py --check 95 --state /tmp/does-not-exist-calibration-state.json; echo EXIT:$?' in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
EXIT:0

codex
I have two concrete risks at this point: one in ordering, one in enforcement. I’m running one more probe on schema handling to see whether malformed or duplicate state is rejected or silently used, because that determines whether the append-only v1 contract is actually protected by code.
exec
/bin/zsh -lc "python3 - <<'PY'
import json, tempfile, subprocess, os
state = {
  'schema_version': 999,
  'entries': [
    {'pr': 23, 'r1_outcome': 'CHANGES_REQUIRED'},
    {'pr': 23, 'r1_outcome': 'APPROVE'},
    {'pr': 24, 'r1_outcome': 'APPROVE'},
  ],
}
fd, path = tempfile.mkstemp(suffix='.json')
os.close(fd)
with open(path, 'w') as f:
    json.dump(state, f)
cp = subprocess.run(['python3', 'scripts/compute_calibration_cap.py', '--state', path], capture_output=True, text=True)
print('rc=', cp.returncode)
print(cp.stdout.strip())
print(cp.stderr.strip())
os.unlink(path)
PY" in /tmp/adr012-review.GW7sje
 succeeded in 0ms:
rc= 0
{"ceiling": 95, "mandatory_codex": false, "blocking": false, "basis": "1 of last 5 = CHANGES_REQUIRED (base 80%) + 2 trailing APPROVE → step up to 95%", "entry_count": 3, "gate_label": "OPTIONAL"}


codex
I have enough to call the review: the branch passes its own tests and CLI happy-path checks, but there are two correctness flaws that affect the gate calculation itself. I’m cleaning up the temporary worktree and then I’ll return the verdict with line-cited findings and the minimal reproduction evidence.
exec
/bin/zsh -lc 'git worktree remove /tmp/adr012-review.GW7sje' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
codex
`CHANGES_REQUIRED`

1. `HIGH` — `scripts/compute_calibration_cap.py:156`
Description: `load_state()` reorders entries by PR number, but ADR-012’s formula is about the last merged PRs, not the last created PRs. PR numbers are not merge-order, and this repo already has a counterexample in `reports/calibration_state.json` (`#20` merged before `#18` and `#19`). Once APPROVE outcomes appear, this can change both the rolling 5-PR base ceiling and the trailing-APPROVE recovery result. I verified the current logic gives different ceilings for the same outcomes depending on PR-sort vs merge-order.
Suggested fix: derive sequence from `merged_at` or preserve append order and validate it; do not sort by `pr`. Update the state-file/ADR wording accordingly, and replace the current ordering test with one that asserts merge-order behavior.

2. `HIGH` — `scripts/compute_calibration_cap.py:151`
Description: the enforcement path fails open when the authoritative state is missing or malformed. A missing `--state` path returns `[]`, which the script interprets as `95% / OPTIONAL`; I verified `python3 scripts/compute_calibration_cap.py --check 95 --state /tmp/does-not-exist-calibration-state.json` exits `0`. The loader also accepts bad `schema_version` values and duplicate PR rows, so the claimed append-only v1 contract is not actually enforced.
Suggested fix: make missing/default-state load failures, schema-version mismatches, duplicate `pr` values, unknown outcomes, and malformed records hard errors; `--check` should exit non-zero on any validation failure. Add tests for these failure modes.

Happy-path checks do work: `tests/test_compute_calibration_cap.py` passes `42/42`, `--human` reports `30% / BLOCKING`, `--check 80` fails, and `--check 30` passes. I did not find a separate defect in the PR’s M-trigger audit; the blockers are in ordering and state-validation/enforcement, not in the claimed `M1+M2+M4+M5` set.
tokens used
112,532
`CHANGES_REQUIRED`

1. `HIGH` — `scripts/compute_calibration_cap.py:156`
Description: `load_state()` reorders entries by PR number, but ADR-012’s formula is about the last merged PRs, not the last created PRs. PR numbers are not merge-order, and this repo already has a counterexample in `reports/calibration_state.json` (`#20` merged before `#18` and `#19`). Once APPROVE outcomes appear, this can change both the rolling 5-PR base ceiling and the trailing-APPROVE recovery result. I verified the current logic gives different ceilings for the same outcomes depending on PR-sort vs merge-order.
Suggested fix: derive sequence from `merged_at` or preserve append order and validate it; do not sort by `pr`. Update the state-file/ADR wording accordingly, and replace the current ordering test with one that asserts merge-order behavior.

2. `HIGH` — `scripts/compute_calibration_cap.py:151`
Description: the enforcement path fails open when the authoritative state is missing or malformed. A missing `--state` path returns `[]`, which the script interprets as `95% / OPTIONAL`; I verified `python3 scripts/compute_calibration_cap.py --check 95 --state /tmp/does-not-exist-calibration-state.json` exits `0`. The loader also accepts bad `schema_version` values and duplicate PR rows, so the claimed append-only v1 contract is not actually enforced.
Suggested fix: make missing/default-state load failures, schema-version mismatches, duplicate `pr` values, unknown outcomes, and malformed records hard errors; `--check` should exit non-zero on any validation failure. Add tests for these failure modes.

Happy-path checks do work: `tests/test_compute_calibration_cap.py` passes `42/42`, `--human` reports `30% / BLOCKING`, `--check 80` fails, and `--check 30` passes. I did not find a separate defect in the PR’s M-trigger audit; the blockers are in ordering and state-validation/enforcement, not in the claimed `M1+M2+M4+M5` set.
