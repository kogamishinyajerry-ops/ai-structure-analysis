# AI-Structure-FEA · STATE

> **Stamp:** `post-RFC-001-W8d-merge-2026-04-29 · ENG-31-in-flight · 2026-05-03 refresh`
> **Last updated:** 2026-05-03 (after PR #114 W8d merge; main = `a254a23`; PR #121 ENG-31 in flight, Codex R1 APPROVE, awaiting CI re-run)
> **Maintained by:** T1 (Claude Code CLI · Opus 4.7 1M ctx) per ADR-011 §6 Sessions fully traced.

This file is the **repo-side execution status snapshot**. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is the human-facing process SSOT. When they conflict, **git is authoritative**; STATE.md is updated to match git, and Notion is patched from STATE.md.

---

## Phase ledger

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
| Phase 1.5 — Foundation-Freeze (post-pivot) | ✅ Governance baseline closed (FF-01/02/05/06 + ADR-011/012/013 merged). FF-07/08/09 still OPEN as separate PRs. |
| Phase 1.6 — RFC-001 Foundation rebuild (W1→W4) | ✅ Done 2026-04-26 → 2026-04-27 (#68-#82) | Buckets A/B/C/D + Layer-2/3 schema + CalculiX adapter + L1→L4 producers + report-cli driver. |
| Phase 1.7 — RFC-001 Workbench shell (W5) | ✅ Done 2026-04-27 (#83-#90) | Electron shell + GS-001 quick-start + violation panel + --doctor + viz tracking. |
| Phase 1.8 — RFC-001 Reporting libs + GS-101 ballistic (W6+W7) | ✅ Done 2026-04-28 (#91-#110) | Material/allowable_stress/verdict/BC/model-overview libs + DOCX wiring; OpenRadioss adapter + ballistic derivations + Dockerfile + Electron --kind=ballistic. |
| Phase 1.9 — RFC-001 3D viewport + live bake (W8) | ✅ Done 2026-04-29 (#111-#114) | OpenRadioss → VTU exporter + PyVista viewport + live streaming + Electron live-bake orchestration. |
| Phase 2 — Web Console hardening | 🟡 Active (ENG-31 / PR #121 in flight) | Frontend build-smoke restoration; Codex R1 APPROVE 2026-05-03; awaiting CI green to merge. |
| Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |

---

## Phase 1.5 — Foundation-Freeze final tally (closed except FF-07/08/09)

| Task | Status | PR | Commit | Notes |
|------|--------|----|--------|-------|
| FF-01 — ADR-011 Pivot baseline | ✅ Merged 2026-04-25 · R5 APPROVE | #17 | `34722ea` | 5-round Codex arc; reports at `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. |
| FF-01a — ADR-011 amendments AR-2026-04-25-001 | ✅ Merged 2026-04-25 · R1 CR → R2 APPROVE | #23 | `e53b0f7` | T2 rewording, §HF1/§HF2 narrowing, §Enforcement Maturity update. |
| FF-01b — Notion Decisions DS sync | ✅ Done | (Notion API) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. |
| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged 2026-04-25 | #18 | `77e6813` | 3 FPs (FP-001/002/003); R1 CR → R2 APPROVE. |
| FF-05 — STATE.md | ✅ Merged 2026-04-25 | #19 | `4a64cfd` | Adopts `.planning/` directory convention. |
| FF-06 — pre-commit path-guard for HF1 forbidden zone | ✅ Merged 2026-04-25 | #22 | `ac98fc3` | `scripts/hf1_path_guard.py` + 30 tests. R1 CR → R2 APPROVE. |
| ADR-012 — Calibration cap for T1 self-pass-rate | ✅ Merged 2026-04-26 01:01Z | #24 | `6f660ba` | Mechanical 5-PR rolling-window ceiling. CI workflow `.github/workflows/calibration-cap-check.yml` enforces on every PR. |
| ADR-013 — Branch protection enforcement | ✅ Merged 2026-04-26 01:02Z | #25 | `303233c` | 3-layer wrapper (PR template + CI `--check` workflow + `gh api` protection script). |
| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | 🟡 OPEN (PR #27, lint-and-test FAILURE) | #27 | — | Hard deadline 2026-05-23. Needs lint fix + Codex review. |
| FF-08 — `golden_samples/<id>` registry schema validation (HF3) | 🟡 OPEN (PR #28, MERGEABLE, ✓2/✗0) | #28 | — | Same hard deadline. Needs Self-pass-rate + body refresh + Codex review. |
| FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | 🟡 OPEN (PR #26, MERGEABLE, ✓1/✗0) | #26 | — | Bundled with FF-03/FF-04 governance docs sync. |

---

## Phase 1.6-1.9 highlights (RFC-001 W1-W8 build-out, 2026-04-26 → 2026-04-29)

> Full per-PR ledger in `git log a254a23 --grep "RFC-001 W"`. Below is the architectural beat sheet.

- **W1 (PR #68)** — Foundation rebuild buckets A/B/C/D; Layer-2/3 schema + handoff doc.
- **W2 (PR #69)** — CalculiX Layer-1 adapter on `ReaderHandle` Protocol (first concrete reader).
- **W3a/W3b/W3c (PRs #70/#71/#76)** — Layer-3 derivations: stress derivatives (vM/principals/max-shear) + Quantity unit conversion + ASME VIII Div 2 §5.5 SCL stress-linearization.
- **W4 (PRs #72-#78)** — Layer-4 services/report: `draft.py` (L1→L3→L4 spine) + `exporter.py` (DOCX export) + `templates.py` (template specs+validation) + 3 producers (`generate_*_summary`) + `report-cli` engineer driver.
- **W5 (PRs #83-#90)** — Electron workbench shell: minimal shell over report-cli, GS-001 quick-start button, structured violation panel, `--doctor` install probe, ADR-018 (defer electron-builder packaging), per-stage progress lines, viz tracking (mesh/displacement/von_mises figs).
- **W6 (PRs #91, #98-102, #109-110)** — Reporting libraries with DOCX wiring: material data (W6a, ADR-019), allowable_stress GB/ASME (W6b, ADR-020), verdict PASS/FAIL+safety_factor (W6c+W6c.2), boundary-condition summary (W6d+W6d.2), model-overview + SupportsElementInventory (W6e+W6e.2).
- **W7 (PRs #92-97, #105-108)** — OpenRadioss / ballistic track: Layer-1 adapter (W7b), animation manifest (W7c), Layer-3 ballistic derivations (W7d), summary template (W7f), Dockerfile (W7-tools), RFC-002 retrospective (W7g), `--kind=ballistic` Electron wiring (W7h), ADR-021 (gs100-radioss-smoke-fixture), ADR-022 (gs101-demo-unsigned).
- **W8 (PRs #111-114)** — 3D viewport + live bake: OpenRadioss → VTU + viewport manifest exporter (W8a), PyVista native viewport + Electron Open-3D-viewport button (W8b), live streaming exporter + viewport polling (W8c), Electron live-bake one-click ballistic demo (W8d).

---

## Repo state

`main == origin/main == a254a23` (post #114 W8d merge, 2026-04-29 02:38Z).

---

## Open PRs

### In flight (this session)

| PR | Branch | Status | Owner action |
|----|--------|--------|--------------|
| #121 | `codex/ENG-31-ui-launch-build-fixes` | DRAFT · MERGEABLE · 1 push since 2026-04-29 (Codex R1 APPROVE archived in commit `0ec6be5`, body refreshed with Self-pass-rate=30%) | Awaiting calibration-cap-check re-run on push `0ec6be5`; if green, mark Ready & merge. |

### Codex/ENG-* DRAFT backlog (all blocked on missing Self-pass-rate section)

| PR | Linear | Title |
|----|--------|-------|
| #115 | ENG-23 | GS-101 pre-gate ballistic candidate tooling |
| #116 | ENG-11 | GitHub sync live probe |
| #117 | ENG-16 | HF5 commit trailer enforcement (overlaps FF-07) |
| #118 | ENG-17 | HF3 golden-sample registry validation (overlaps FF-08) |
| #119 | ENG-20 | Plan viewport screenshot storyboard hook |
| #120 | ENG-18 | Plan README/ADR v6.3 routing sync (overlaps FF-09) |

All 6 fail `calibration-cap-check` for the same reason as #121's first failure (no `## Self-pass-rate` section). Triage decision pending: keep ENG-16/17/18 as supersedes for FF-07/08/09 and close FF-* duplicates, OR vice versa.

### Phase 1.5 governance backlog (still relevant, needs body+Codex refresh)

| PR | Branch | Status |
|----|--------|--------|
| #26 | `feature/AI-FEA-FF-09-readme-adr-011-sync` | OPEN · MERGEABLE · ✓1/✗0 |
| #27 | `feature/AI-FEA-FF-07-trailer-check` | OPEN · MERGEABLE · ✓1/✗1 (lint-and-test failing) |
| #28 | `feature/AI-FEA-FF-08-gs-registry` | OPEN · MERGEABLE · ✓2/✗0 |

### Surrogate hint scaffolding stack (post-pivot, P1-07 line)

| PR | Branch | Status |
|----|--------|--------|
| #30 | `feature/AI-FEA-P1-07-surrogate-hook` | OPEN · MERGEABLE · ✗1 (CI failing) |
| #36 | `feature/AI-FEA-P2-writeback-integration` | OPEN · MERGEABLE · stacked on `feature/AI-FEA-P2-github-writeback` (parent unclear; investigate) |
| #37 | `feature/AI-FEA-P1-07-simplan-adapter` | OPEN · MERGEABLE · stacked on #30 |

### Stale (W6e earlier draft, now subsumed)

| PR | Branch | Status |
|----|--------|--------|
| #103 | `feature/RFC-001-W6e-model-overview` | OPEN · UNKNOWN mergeable · subsumed by #109 (`407436e`) and #110 (`aa66ed1`) which both merged. **Recommended: close as stale.** |

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

---

## Carry-overs (still open)

1. **Calibration state file is stale**: `reports/calibration_state.json` last entry is PR #56 (2026-04-26). PRs #64-#114 (W1-W8 series) merged but not appended. The mechanical ceiling stays at 30% (5/5 last CR) because the file doesn't reflect any newer R1 outcomes — no recovery is possible until backfill. **Action**: backfill or document why backfill is intentional.
2. **FF-07 PR #27** has `lint-and-test` failure not yet diagnosed.
3. **FF-08 / FF-09** stalled in OPEN since 2026-04-25. Need PR-body refresh (Self-pass-rate) + Codex review to close out the Phase 1.5 governance maturity deadline of 2026-05-23.
4. **Codex/ENG-* DRAFT lane (#115-#120)** all 6 PRs blocked on missing Self-pass-rate. Triage pass needed: which to keep vs close as duplicates of FF-07/08/09.
5. **Pre-pivot P1-* (#11-#16)** disposition deferred since 2026-04-25. No action item committed yet.
6. **W6e #103 stale** — superseded by merged #109+#110. Recommend close.
7. **GS-001/002/003 status flip** to `insufficient_evidence` (proposed in FP-001/002/003) — Notion control-plane status field still not changed.
8. **Self-pass-rate honor-system replacement**: ADR-012 + ADR-013 are live and enforcing; calibration_state.json backfill (#1 above) is the residual gap.

---

## How to update this file

Update STATE.md whenever:

- A FF-task changes status (pending → in-flight → done).
- A branch is pushed or a PR opens / merges.
- An ADR is accepted, revised, or superseded.
- A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
- The `Last updated` stamp must change in the same commit.

**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.
