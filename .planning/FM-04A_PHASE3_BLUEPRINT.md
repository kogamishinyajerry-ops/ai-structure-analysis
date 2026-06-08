# FM-04a Phase 3 — Reviewer Workbench Polish Blueprint

> **Status:** authoring + execution plan; Tier 1 engineering candidate scope only.
> **Author:** local Claude Opus 4.7 acting as project lead under direct-execution authorization 2026-05-16.
> **Parent:** `.planning/STATE.md` + `.planning/retrospectives/fm04a_phase2_industrial_polish.md` (Phase 2 closure ledger ends at `2ce9b4f`).
> **Boundary anchor:** `.planning/FM-04B_READINESS.md` — Tier 2 prerequisites unchanged.

---

## Why this blueprint exists

Phase 2 closed the four industrial-readiness gaps — the audit graduates
honestly, convergence has a real verdict, the picker switches between
candidate fixtures, and a structured Tier 1 report packet renders to
markdown + DOCX. What Phase 2 did NOT do is close the **reviewer
experience loop**: a non-author opening the Workbench today still has
to compare cases manually, can't see the convergence study without
opening JSON, can't hand a single canonical evidence manifest to a
reviewer, and the new endpoints have no HTTP-level test coverage.

This blueprint closes **five reviewer-experience gaps** without
crossing any FM-04b prerequisite:

| Gap | Phase that closes it | Phase 2 surface it builds on |
|---|---|---|
| **R1 — No canonical evidence manifest.** The Tier 1 report packet (Phase 2 E) is great for reading; a reviewer also needs a single machine-checkable JSON listing every artifact + SHA-256 hash + Tier 1 claim for sign-off / archival. | A | Phase 2 E `tier1_candidate_report.py` shows the right shape. |
| **R2 — Two cases can only be compared by eyeballing reports.** The 2026-05-12 velocity bracket has 27 per-run reports; no structured diff exists. | B | Phase 2 A `energy_audit_extractor`, Phase 2 B `convergence_orchestrator`, Phase 2 E packet builder all consumed. |
| **R3 — Workbench has no comparison/acceptance UI surface.** | C | Phase 2 C picker + Phase 2 D Trust Center cards extended. |
| **R4 — Convergence study only readable as raw JSON.** Phase 2 B writes a payload nobody renders. | D | Phase 2 B `convergence_orchestrator.py` JSON shape + Phase 2 D `trustCenterSummary.ts` tone helpers. |
| **R5 — New endpoints (Phase 2 C/E) have unit tests but no HTTP-layer tests.** | E | Phase 2 C `/candidate-cases`, Phase 2 E `/tier1-report`, Phase 3 A `/acceptance-packet`, Phase 3 B `/case-comparison`. |

This blueprint **does NOT** cross any FM-04b line. The acceptance
packet stays Tier 1 candidate evidence (not a sealed Tier 2 packet),
the comparison stays case-vs-case (not vs experimental benchmark
data), and the new endpoints all read-only over project_state /
golden_samples. ADR-024 stays at lite. No `^GS-\d{3}$` registry
mutation, no Linear / Notion writes, no signed validation, no
benchmark agreement.

---

## North star ("done when")

A non-author reviewer can, in one Workbench session:

1. Pick a Tier 1 candidate case from the existing picker.
2. **Click "Acceptance evidence packet"** → receive a canonical
   `<case-id>_acceptance_packet.json` listing every artifact path +
   SHA-256 + Tier 1 claim + assumptions + blockers; the same packet
   is also fetchable from `/api/v1/acceptance-packet/<case-id>`.
3. **Pick a second case from the comparison picker** and see a
   structured side-by-side: residual velocity Δ, perforation marker
   diff, energy balance error Δ, convergence verdict diff, energy
   audit status diff, blueprint anchor coverage diff. Same payload
   is fetchable from `/api/v1/case-comparison?a=<id>&b=<id>`.
4. **Open the convergence study view** and see the orchestrator
   payload rendered as two stacked tables (mesh sweep + dt sweep)
   with tone-driven cell coloring + a combined verdict badge.
5. Trust Center has new review cards for `acceptance_packet_status`
   and `case_comparison_status` so reviewers see the new surfaces
   without hunting for tabs.
6. Every new endpoint has at least one HTTP-layer integration test
   driving it through FastAPI TestClient with assertions on
   status code, content-type, content-disposition (where relevant),
   and Tier 1 boundary in the body.

Every artifact carries the Tier 1 banner; no positive `validated
against` / `benchmark agreement` / `signed validation` / `perforation
completed` / `bullet-through-steel complete` / `validated physics`
wording.

---

## Phase plan

Six phases. Each phase is one or more atomic commits with passing
tests + ruff clean + HF1 path-guard green. No real solver, no
external mirror writes.

### Phase A — Acceptance evidence packet generator

**Goal:** one command produces a canonical
`<case-id>_acceptance_packet.json` for any completed Tier 1 candidate
run; the JSON is the machine-readable counterpart to the Phase 2 E
DOCX/MD report.

**Deliverables:**

- `backend/app/services/reporting/acceptance_packet.py` (NEW): pure
  builder that takes the same `Tier1CandidateReportInputs` (re-used)
  and emits a `AcceptancePacket` dataclass + JSON renderer. Schema:
  ```
  {
    "case_id", "generated_at_utc",
    "claim_tier", "claim_boundary",
    "deck_artifacts": [{"relpath", "sha256", "bytes"}, ...],
    "evidence_artifacts": [{"relpath", "sha256", "bytes",
                            "kind": "ballistic_metrics"|"convergence_study"|...},
                           ...],
    "visualization_artifacts": [{"relpath", "sha256", "bytes",
                                 "kind": "blueprint"|"animation"|"result_mesh"},
                                ...],
    "ballistic_metrics_summary": {...},
    "energy_audit_summary": {...},
    "convergence_study_summary": {...},
    "assumptions": [...],
    "limitations": [...],
    "tier2_blockers_remaining": [...],
    "claim_impact": "..."
  }
  ```
- `scripts/export_acceptance_packet.py` (NEW): CLI driver. Writes to
  `reports/` by default; refuses `golden_samples/**`.
- `backend/app/api/routes/acceptance_packet.py` (NEW): GET
  `/api/v1/acceptance-packet/<case-id>` endpoint streaming the JSON.
- Tests: `tests/test_acceptance_packet.py` covering schema completeness,
  every artifact type with SHA-256, missing-file fallback, golden_samples
  write refusal, build-time forbidden-wording audit.

### Phase B — Case comparison engine + endpoint

**Goal:** two candidate cases compared in one structured payload.

**Deliverables:**

- `backend/app/services/reporting/case_comparison.py` (NEW): pure
  builder taking two `AcceptancePacket` instances → `CaseComparison`
  dataclass with axis-by-axis diff:
  ```
  {
    "case_a", "case_b", "generated_at_utc",
    "residual_velocity_diff": {a, b, delta, delta_pct},
    "perforation_marker_diff": {a, b, same_marker: bool},
    "energy_balance_error_diff": {a, b, delta_abs_pct},
    "energy_audit_status_diff": {a, b, both_closed: bool},
    "convergence_verdict_diff": {a, b, same_verdict: bool},
    "deck_artifact_diff": {a_only: [...], b_only: [...], shared: [...], hash_changed: [...]},
    "claim_boundary", "claim_impact": "Tier 1 candidate comparison..."
  }
  ```
- `backend/app/api/routes/case_comparison.py` (NEW): GET
  `/api/v1/case-comparison?a=<id>&b=<id>` endpoint streaming the
  JSON payload.
- Tests: `tests/test_case_comparison.py` covering all diff axes,
  identity case (a==b: every diff = 0), missing-field tolerance,
  forbidden-wording audit.

### Phase C — Frontend reviewer panel (acceptance + comparison)

**Goal:** the Workbench surfaces both new endpoints in the Visual tab
through one consolidated Reviewer panel above the blueprint.

**Deliverables:**

- `frontend/src/acceptancePacketClient.ts` (NEW): typed fetch helper
  for `/acceptance-packet` + `parseAcceptancePacket` snake→camel.
- `frontend/src/caseComparisonClient.ts` (NEW): typed fetch helper for
  `/case-comparison` + snake→camel.
- `frontend/src/components/AcceptancePacketPanel.tsx` (NEW): renders
  selected-case acceptance summary; "Download JSON" button hits the
  endpoint.
- `frontend/src/components/CaseComparisonPanel.tsx` (NEW): two case
  dropdowns (driven by `candidateCaseRegistry`); render structured
  diff table with tone-coded cells (delta_pct ≤ 5% accent, ≤ 15%
  warning, > 15% danger).
- `frontend/src/App.tsx`: integrates both panels above the existing
  Visual tab grid; new state `selectedComparisonCaseIds` (a/b pair).
- Trust Center: two new review cards (`acceptance_packet_status`,
  `case_comparison_status`) wired through ChatPanel filter.
- Tests: `frontend/test/acceptancePacketClient.test.ts` +
  `caseComparisonClient.test.ts` covering snake/camel parse, fallback
  on network error / non-2xx, Tier 1 banner preservation.

### Phase D — Frontend convergence study viewer

**Goal:** the orchestrator's `convergence_study.json` becomes a
visual artifact in the Workbench, not a raw JSON.

**Deliverables:**

- `frontend/src/convergenceStudyClient.ts` (NEW): typed fetch helper
  for any `convergence_study.json` URL (e.g. via the existing
  `/visualization/result-mesh/<case>/convergence_study.json` path or
  a new whitelist entry).
- `frontend/src/components/ConvergenceStudyViewer.tsx` (NEW): mesh
  sweep table + dt sweep table + combined-verdict badge. Cell coloring
  uses `trustCenterSummary.convergenceTone`.
- Backend: extend `_resolve_result_mesh_artifact_path` whitelist (or
  add a sibling endpoint) so the convergence JSON is reachable. No
  schema change; additive new file pattern only.
- `frontend/src/App.tsx`: integrates the viewer alongside the
  comparison panel in the Visual tab.
- Tests: `frontend/test/convergenceStudyClient.test.ts` covering
  fetch/parse + tone-coded label generation.

### Phase E — TestClient endpoint integration tests

**Goal:** every Phase 2 / Phase 3 endpoint has a real HTTP-layer test
that drives it through FastAPI TestClient with proper assertions on
status code, content-type, content-disposition, and Tier 1 boundary
in the body.

**Deliverables:**

- `tests/test_api_endpoints_integration.py` (NEW): TestClient suite
  with one section per endpoint. Covers:
  - `GET /api/v1/candidate-cases` — 200 OK, JSON with claim_tier +
    cases array.
  - `GET /api/v1/tier1-report/<case-id>?fmt=md` — 200 OK, text/markdown,
    Content-Disposition attachment, body contains Tier 1 banner.
  - `GET /api/v1/tier1-report/<case-id>?fmt=docx` — 200 OK, DOCX MIME
    type, body starts with PK\x03\x04 zip signature.
  - `GET /api/v1/tier1-report/<case-id>?fmt=bogus` — 400.
  - `GET /api/v1/tier1-report/<bad-id>` — 400.
  - `GET /api/v1/tier1-report/<missing-id>` — 404.
  - `GET /api/v1/acceptance-packet/<case-id>` — 200 OK, application/json,
    Tier 1 claim_tier in payload.
  - `GET /api/v1/case-comparison?a=<id>&b=<id>` — 200 OK, deltas all
    zero on identity comparison.

### Phase F — STATE refresh + Phase 3 retrospective

**Goal:** `.planning/STATE.md` reflects the new Phase 3 ledger; a
retrospective documents what shipped vs deferred.

**Deliverables:**

- `.planning/STATE.md`: new Phase 3 section listing every commit SHA
  with one-line summary; updated `Last updated:` stamp.
- `.planning/retrospectives/fm04a_phase3_reviewer_workbench.md` (NEW):
  R1..R5 closure ledger + commit table + what worked + deliberately
  deferred (FM-04b prerequisites unchanged) + process notes + 5
  candidate next slices.

---

## Verification gates (mechanical only)

Each phase commit must satisfy:

1. **pytest:** all new tests pass; full repo-root pytest returns no
   regressions vs the Phase 2 baseline (1293 passed / 8 skipped).
2. **frontend node:test:** all new tests pass; total grows from 29.
3. **frontend tsc -b + vite build:** clean.
4. **pre-commit:** ruff + ruff-format + HF1 path-guard all pass. No
   new HF1 zones touched in Phase 3 — every new file is outside
   `agents/`, `tools/calculix_driver.py`, `schemas/sim_state.py`,
   `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`,
   `scripts/hf1_path_guard.py`, `.github/workflows/`, and the signed
   `^GS-\d{3}$` registry inside `golden_samples/`.
5. **forbidden-wording audit:** every new doc/code path with public
   wording is grep-clean against the ADR-024 lite forbidden list
   (`validated against`, `benchmark agreement`, `signed validation`,
   `perforation completed`, `bullet-through-steel complete`,
   `validated physics`). Disclaimer forms (`not <claim>`) remain
   allowed.

No real-solver execution. No external review gate inside Tier 1
candidate work.

---

## What this blueprint deliberately does NOT do

| Out-of-scope item | Where it lives | Why deferred |
|---|---|---|
| ADR-024 (full) authoring | FM-04b P2-full | governance-grade ADR |
| `benchmark_comparison_candidate.json` schema + producer | FM-04b P7 | benchmark linkage is Tier 2 |
| Sealed packet (SHA freeze, manifest of manifests, immutable bundle) | FM-04b P8 | Tier 2 sealing — the Phase 3 A acceptance packet is **a Tier 1 candidate manifest**, not a sealed bundle |
| Independent reviewer signoff path / reviewer assignment | FM-04b P8 | Tier 2 reviewer gate |
| User milestone-experience acceptance | FM-04b P9 | reserved for the human user |
| `^GS-\d{3}$` flip from `GS-102-candidate` to `GS-102` | FM-04b P9 | Tier 2 promotion |
| Notion / Linear mirror writes | FM-04a / FM-04b alike | user-controlled |
| Real OpenRadioss container runs | environment, not code | code is solver-input-agnostic |
| Per-term plastic / contact / hourglass via `/TH/PART` | Phase 4 candidate | requires deck change + new parser + re-runs |
| MP4 animation export | Phase 4 candidate | dependency on ffmpeg/imageio MP4 plugin uncertain |
| `agents/solver.py` / `agents/router.py` HF1 zone edits | HF1 hard-stop | no need; Phase 3 code lives outside HF1 |

---

## Execution policy

- Atomic commits per phase deliverable. Commit messages follow the
  Phase 2 style (`feat(FM-04a/Phase3-X)`, `docs(...)`, `test(...)`).
- HF5 trailer rewrite deferred to push-time per existing FM-04a
  convention.
- Each phase closes with a plain-Chinese summary to the user.
- Mid-phase blockers escalate to the user immediately; otherwise the
  run is autonomous until Phase F ships.

---

## Anti-drift checklist (re-read before every Phase 3 commit)

- [ ] Is every new artifact outside `golden_samples/<signed>/` and
  outside the HF1 zone?
- [ ] Does every new public claim include `Tier 1 engineering
  candidate; not signed validation; not benchmark agreement`?
- [ ] Is there zero new positive `validated against` / `benchmark
  agreement` / `signed validation` / `perforation completed` /
  `bullet-through-steel complete` / `validated physics` wording?
- [ ] Are tests covering the synthetic path so real-solver absence
  does not block CI?
- [ ] Does `.planning/FM-04B_READINESS.md` still describe the same
  Tier 2 prerequisites unchanged?
- [ ] Is the acceptance packet still **machine-readable Tier 1 candidate
  manifest**, not a sealed Tier 2 packet?

If any answer is "no", the commit gets reworked, not merged.
