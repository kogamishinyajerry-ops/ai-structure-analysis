# AI-Structure-FEA · STATE

> **Stamp:** `eng44-fm01-candidate-acceptance-packet-2026-05-07 · main=f133f5a`
> **Last updated:** 2026-05-07 (after ENG-43 PR #147 merge; ENG-44/FM-01 candidate packet branch opened)
> **Maintained by:** Codex primary executor; local Claude Opus 4.7 reviewer/auditor per ADR-011 AR-2026-05-06-001.

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

## Phase 1.5 — Foundation-Freeze final tally

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
| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green | #129 | `e62a4e7` | Supersedes blocked PR #27 and closed duplicate #117. Adds trusted-main trailer validator, `pull_request_target` workflow, branch-protection `trailer-check` context, PR template merge trailers, and docs/ADR sync. Branch protection applied 2026-05-06; `trailer-check` is now required on `main`. |
| FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green · Linear ENG-17 Done | #131 | `0913792` | Adds trusted signed-registry validator, always-on `golden-samples-validation` workflow, ADR-011/013 sync, symlink-bypass fix, and branch-protection context update. Old #28 closed as superseded. |
| FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green · Linear ENG-18 Done | #132 | `a5c3dc4` | Syncs README quick rules, ADR-011 maturity/cross-reference text, and `docs/governance/` routing/onboarding with Codex-primary workflow truth. Old #26 closed as superseded. |

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

`origin/main == f133f5a` (post ENG-43 PR #147 merge, 2026-05-07).

ENG-39 created 2026-05-06 to adopt a lean validation workflow:

- Tier 0 sandbox/demo work moves quickly with explicit software-path-only labels.
- Tier 1 engineering-candidate work uses compact reproducibility manifests and automatic read-only Claude Opus review when triggered.
- Tier 2 signed validation remains strict at the physical-claim boundary: benchmark, metrics, tolerance comparison, convergence, hashes, and reviewer/signoff.
- This change is governance/documentation only and does not mutate `golden_samples/**`, solver decks, schemas, protocols, CI, dependencies, or signed-validation evidence.
- PR #143 merged 2026-05-07 for ENG-39. The same branch introduced
  `.planning/ROADMAP.md` and `docs/governance/goal_driven_development.md` so
  future feature work is organized as Linear-backed milestone `/goal` runs with
  Claude Opus read-only review gates.
- ENG-40 / FM-01 merged in PR #144 at `776fdae`. It added the first Tier 0 Web
  Console operator shell/status surface and closed with local Claude Opus 4.7
  owner-gate `APPROVE_TO_MERGE`. Linear ENG-40 is Done as an issue-level slice;
  human acceptance remains deferred to the feature-milestone experience
  checkpoint.
- ENG-41 merged in PR #145 at `4a6caf1`. It documents the delegated Claude
  Opus 4.7 issue-level owner gate and keeps human acceptance at feature
  milestone checkpoints. Linear ENG-41 is Done.
- ENG-42 / FM-01 merged in PR #146 at `222e9f4`. It made the operator shell
  derive case/run/evidence/next-action values from existing frontend session
  state. Linear ENG-42 is Done as an issue-level slice.
- ENG-43 / FM-01 merged in PR #147 at `f133f5a`. It added current solver job
  id/status, active analysis mode, and software-path backend provenance to the
  operator shell from existing frontend session state. Linear ENG-43 is Done.
- ENG-44 / FM-01 is the active candidate-acceptance packet issue. Branch
  `codex/ENG-44-fm01-acceptance-packet` starts from `f133f5a` and is limited
  to preparing repo-local milestone evidence for human experience review.
  FM-01 is not user-accepted until the human milestone checkpoint records it.

2026-05-06 pre-WF-01 Linear discover readback:

- `eligible_count = 0`.
- Remaining queued GS101 issues ENG-24..ENG-30 are not agent-eligible because they lack repository, acceptance, boundaries, and evidence_required fields.
- ENG-11 / ENG-20 / ENG-21 / ENG-13..15 are in Pending Review but still lack executable issue contracts.
- Next business-code work should first create or refresh one bounded Linear contract; do not infer acceptance criteria from stale PR bodies.

WF-01 / ENG-34 was then created as the bounded control-plane triage issue for this STATE refresh and the approved stale closure/verification path (#116 and #103). Post-creation discover readback returns `eligible_count = 1` with ENG-34 as the only eligible issue.

AERON-01 / ENG-35 then created and landed the first concrete AERON L0 backend adapter:

- PR #135 added `aeron.drivers.CalculiXFEABackend`.
- `solve(..., dry_run=True)` does not invoke `ccx`.
- Non-dry-run `solve()` delegates to the existing `tools.calculix_driver.run_solve()`.
- `parse_results()` exposes raw output paths and metadata without derived engineering quantities.
- ENG-35 is Done with `verify:passed`.

AERON-02 / ENG-36 then wired that backend into the existing solver caller path:

- PR #137 routes `agents.solver.run()` through `CalculiXFEABackend.prepare_case()`, `solve()`, and `parse_results()`.
- The solver-node `SimState -> dict` return contract remains compatible: `fault_class`, `frd_path`, `artifacts`, `solve_path`, and `solve_metadata`.
- Unsupported non-CalculiX solver backends now fail as non-retriable preflight/history instead of solver syntax retry.
- `agents/solver.py` was touched under ADR-011 HF1.1 with explicit HF1 override accepted by Claude Opus.
- ENG-36 is Done with `verify:passed`.

AERON-03 / ENG-37 then landed a narrow orchestration-provenance slice:

- PR #139 added additive `solve_metadata.backend` provenance.
- `tests/test_cold_smoke_e2e.py` proves `compile_graph().invoke(...)` exposes the AERON backend provenance without real `ccx`.
- This slice intentionally avoided `aeron/protocols/*`, `schemas/*`, `agents/graph.py`, Web/API services, report-cli, UI/workbench, golden samples, GS101, signed-validation artifacts, Notion sync, and CI/governance workflows.

---

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
| — | — | None | ENG-40/FM-01 implementation branch is active but no PR is open yet. |

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
