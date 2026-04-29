# README / ADR v6.3 Routing Sync Plan

ENG-18 is a planning and gate-prep slice. It does not rewrite README, ADR, or
governance text. The next implementation PR must use this map, then stop at the
required review gate before changing ADR/governance surfaces.

## Current Drift Evidence

| File | Current wording | Drift |
|---|---|---|
| `README.md` | Process SSOT is "Notion PRD v0.2". | Current process SSOT is Linear `AI-Structure-FEA`; Notion is archive/comment mirror only. |
| `README.md` | `docs/` points to Notion PRD; `backend/app/well_harness/` is described as Notion sync/control plane. | Control-plane language should distinguish Linear state from legacy Notion sync modules. |
| `README.md` | Development rules require Notion task review, Notion writeback, and Notion Decisions ADR records. | Current workflow requires Linear issues, GitHub PRs, fresh-subtask self-verification, and Notion archive comments only. |
| `.planning/STATE.md` | Maintained by T1 Claude Code CLI; Notion control tower is human-facing process SSOT. | Current driver is Codex solo; Linear is process SSOT. |
| `docs/adr/ADR-011-pivot-claude-code-takeover.md` | T1 is Claude Code CLI; T2 is Codex verify-only; Codex cannot directly commit; Notion is process/handoff surface. | Superseded by v6.3: Codex solo executes; T2 is Codex fresh-subtask double-blind self-verification; Linear owns process workflow. |
| `docs/adr/ADR-011-pivot-claude-code-takeover.md` | Banned routes do not ban Claude Code CLI; commit trailers use `Execution-by: claude-code-opus47` and `Codex-verified`. | Current banned routes include Claude Code any role; commit trailers use `Execution-by: codex-gpt-5.4-xhigh`, `Self-verified`, `Linear-issue`. |
| `docs/failure_patterns/FP-00*.md` | Follow-up actions say to mark GS status in Notion control plane. | Future closeout should use Linear Knowledge documents and issue comments; Notion can mirror archive text only. |

## Proposed Wording Map

| Concept | Old wording family | v6.3 wording family |
|---|---|---|
| Process state | Notion control tower / Notion PRD / Handoff pages | Linear workspace `AI-Structure-FEA` with initiatives, projects, issues, workflow states, cycles, and project documents |
| Notion role | Process SSOT and writeback target | Plain-text archive/comment mirror only; never a gate or current-status source |
| T1 driver | Claude Code CLI / Opus 4.7 daily execution | Codex GPT-5.4-xhigh solo execution |
| T2 verifier | Codex verify-only, external tool-report | Codex fresh-subtask double-blind self-verification |
| Handoff gate | Notion Handoff page | Linear `Pending Review -> Approved -> Done` workflow |
| Critical claim proof | `Codex-verified: <claim>@<sha>` | `Self-verified: <claim>@<sha> (fresh-subtask <id>)` |
| Process link trailer | Notion ADR / Handoff refs | `Linear-issue: ENG-<n>` and optional `Linear-decision: ADR/DEC-*` |
| Solver truth | CalculiX only | CalculiX default; OpenRadioss remains candidate/tooling unless ENG-22 carve-out is approved |
| GS-001/002/003 closeout | Notion status flip | Linear Knowledge FailurePattern/CorrectionPattern document plus linked issue proof |

## Candidate File List

Phase A can be done without changing ADR text:

| File | Action | Gate |
|---|---|---|
| `docs/readme_adr_v63_sync_plan.md` | This planning artifact. | None beyond fresh-subtask verification. |
| `README.md` | Update SSOT block, project structure notes, Well Harness legacy caveat, development rules, and branch naming. | Normal PR + fresh-subtask; not an ADR edit. |
| `.planning/STATE.md` | Stamp `linear-takeover-codex-solo-2026-04-29`; list ENG-11/16/17/20/18 PRs as in-flight only after their PRs exist. | Normal PR + fresh-subtask; do not claim merged state before merge. |

Phase B touches PR-protected governance/ADR surfaces:

| File | Action | Gate |
|---|---|---|
| `docs/adr/ADR-011-pivot-claude-code-takeover.md` | Mark superseded by v6.3 or add an amendment section that points to a new ADR/DEC. | STOP for user/T0 approval before edit. |
| `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` | Decide whether the T1 calibration model still applies after Codex solo takeover or is superseded by fresh-subtask verification. | STOP for user/T0 approval before edit. |
| `docs/adr/ADR-013-branch-protection-enforcement.md` | Update discipline wording from T1/Claude Code to Codex solo + Linear Pending Review. | STOP for user/T0 approval before edit. |
| `docs/failure_patterns/FP-001*.md`, `FP-002*.md`, `FP-003*.md` | Replace Notion closeout instructions with Linear Knowledge doc workflow. | STOP for user/T0 approval if treated as governance-protected FailurePattern text. |

## Gate Decision

- This ENG-18 plan itself does not touch HF1 hard-stop paths, ADR files,
  governance files, failure-pattern files, `golden_samples/**`, solver code, or
  GitHub workflow files.
- The next README/STATE-only sync PR can proceed without T0 if it avoids
  `docs/adr/**`, `docs/governance/**`, and `docs/failure_patterns/**`.
- Any ADR amendment, FailurePattern rewrite, or governance document rewrite must
  stop for explicit user/T0 gate approval before file edits.
- Notion may receive a plain-text archive comment after Linear proof is written,
  but it must not become the process state source.

## Acceptance Checks For The Follow-Up Rewrite

1. README top block says Code SSOT = GitHub, Runtime SSOT = artifacts/CI, Process
   SSOT = Linear `AI-Structure-FEA`; Notion is archive mirror.
2. README development rules require Linear issue, GitHub PR, fresh-subtask proof,
   commit trailers, and `Pending Review` handoff gate.
3. STATE stamp names `linear-takeover-codex-solo-2026-04-29` and does not claim
   any draft PR is merged.
4. All old "Claude Code T1", "Codex T2 verify-only", and "Notion Process SSOT"
   phrases either disappear from active instructions or are explicitly labeled
   historical in ADR text.
5. Fresh-subtask verifies the wording map against repo diff before commit.
