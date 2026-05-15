# FM-04a Phase 2 — Industrial Workbench Closure Blueprint

> **Status:** authoring + execution plan; Tier 1 engineering candidate scope only.
> **Author:** local Claude Opus 4.7 acting as project lead under direct-execution authorization 2026-05-16.
> **Parent:** `.planning/STATE.md` (FM-04a P1-P9 complete on `claude/FM-04a-tier1-ballistic-candidate`).
> **Boundary anchor:** `.planning/FM-04B_READINESS.md` — this blueprint **does NOT cross any FM-04b prerequisite line**.

---

## Why this blueprint exists

FM-04a P1-P9 delivered a Tier 1 candidate spine + extractor + convergence sidecar
writers + synthetic e2e pipeline + Workbench surfacing. The follow-up local arc
(commits `61857f5 ... 88362ad`) added a dynamic result-mesh exporter, the
result-mesh playback panel, the bullet-plate blueprint surfaces, two new
candidate deck variants (refined + hifi), and 33 GS-102 run reports from the
2026-05-12 velocity bracket / mechanism diagnostic exploration.

The exploration **surfaced four industrial-readiness gaps** that block the
Workbench from being something the user can hand to a non-FM-04a-author:

| Gap | Evidence | Workbench impact |
|---|---|---|
| **G1 — Energy audit incomplete** | Every run report says `partial_energy_audit_status: partial_candidate` with `missing_terms: plastic_dissipation_j, contact_friction_j, hourglass_energy_j`. The extractor contract accepts these fields but nothing parses them from OpenRadioss output. | Trust Center can never show a closed energy ledger; no defensible "energy balance OK" claim. |
| **G2 — Convergence study is a stub** | `convergence_writers.py` writes sidecar shape but no orchestrator runs a real mesh × dt sweep across the new refined / refined-mid / hifi candidate decks. | Trust Center claim "convergence observed" is not earned by repeatable evidence. |
| **G3 — Workbench case picker is single-fixture** | Front-end UI only dispatches against one hardcoded case at a time; users cannot switch between `GS-102-candidate / GS-102-refined-candidate / GS-102-hifi-candidate` with a click. | Live demo of the hifi 7.62 AP-class deck is gated on backend manual config. |
| **G4 — Tier 1 report stays as ad-hoc per-run markdown** | 33 `reports/gs102_*` files are bespoke ad-hoc text. No single command emits a structured "Tier 1 Candidate Report" packet (assumptions + metrics + energy + convergence + blueprint reference + hashes + Tier 1 banner). | No reproducible artifact the user can hand to a reviewer. |

This blueprint closes the four gaps **without crossing any FM-04b line**:

- No `^GS-\d{3}$` registry mutation. Only `*-candidate` directories.
- No `ADR-024 (full)`. ADR-024 stays at lite.
- No `benchmark_comparison_candidate.json`. No comparison against Borvik 2002
  experimental data — only candidate-internal energy / convergence audit.
- No `sealed packet`. Hashes per artifact only.
- No `independent reviewer signoff`. Tier 1 wording stays.
- No Linear / Notion writes. Repo-only.
- No `golden_samples/<id>` (signed) edits. HF1 path-guard overrides cite
  ADR-011 §HF1.7 + FM-04a P3 precedent only when touching `*-candidate`.
- No real-solver requirement. The closure runs entirely on synthetic / replay
  inputs; when the user later runs real OpenRadioss on a hifi V0=600 m/s deck,
  the same pipeline ingests the real output without code changes.

---

## North star ("done when")

A non-FM-04a-author user can, in one Workbench session:

1. **Pick** any of `GS-102-candidate` / `GS-102-refined-candidate` /
   `GS-102-hifi-candidate` from a dropdown.
2. **See** the run dispatched (synthetic by default; real OpenRadioss when the
   environment has the container).
3. **Observe** the bullet-plate blueprint anchored to that case's evidence.
4. **Play back** the dynamic result mesh frame-by-frame.
5. **Read** a closed energy ledger (5 terms: KE_initial / plastic / contact /
   hourglass / KE_residual + balance error %) in Trust Center.
6. **Read** the mesh × dt convergence table for the chosen case with a
   `candidate_observed_stable` / `candidate_observed_unstable` /
   `insufficient_data` verdict.
7. **Click** "Export Tier 1 candidate report" and receive a structured
   markdown + PDF/DOCX packet with all evidence, hashes, assumptions, and
   Tier 1 banner.
8. **Read** in `.planning/STATE.md` exactly what local commits delivered each
   of the above.

Every artifact the user touches carries the Tier 1 banner. Every "this is not
benchmark agreement" wording stays. No FM-04b prerequisites are touched.

---

## Phase plan

Seven phases. Each phase is one or more atomic commits with passing tests.
Verification gates are mechanical (pytest + frontend `node:test` + frontend
build) — no human review gate required inside Tier 1 candidate work.

### Phase A — Energy audit extractor closes the 3 missing terms

**Goal:** `partial_energy_audit` graduates to a closed energy ledger when the
upstream solver provides global energy time history.

**Deliverables:**

- `backend/app/services/ballistics/energy_audit_extractor.py`: pure function
  reading either an OpenRadioss T01 time-history JSON sidecar (preferred) or
  a parsed engine.log totals block, returning a `BallisticEnergyAudit` with
  the 5 terms populated. Synthesizes `total_internal_energy_j` and `balance_error_pct`
  helper fields.
- `scripts/parse_openradioss_energy_history.py`: thin CLI wrapper for the
  text-mode `engine.log` energy totals block — produces the JSON sidecar
  the extractor consumes. Output sandboxed to `project_state/runs/<case>/data/`.
- `backend/app/services/ballistics/metric_extraction.py`: integrates the
  extractor; falls back to `partial_candidate` only when neither sidecar
  nor engine.log totals are available.
- Tests: synthetic engine.log totals + JSON sidecar inputs covering closed /
  partial / empty cases. New file `tests/test_energy_audit_extractor.py`.

**No regressions:** all 33 existing GS-102 reports were generated under the
`partial_candidate` path; they remain valid evidence (the closure is forward).

### Phase B — Convergence study orchestrator + verdict rule

**Goal:** `convergence_writers.py` is paired with an orchestrator that actually
runs (or replays) a mesh × dt sweep against the candidate deck registry and
writes a structured `convergence_study.json` per case.

**Deliverables:**

- `backend/app/services/ballistics/convergence_orchestrator.py`: pure logic
  that, given a list of `(mesh_id, dt_ms, ballistic_metrics_path)` rows,
  builds a structured `convergence_study.json` with mesh refinement curve +
  dt stability curve + verdict (`candidate_observed_stable` /
  `candidate_observed_unstable` / `insufficient_data`). Uses the existing
  `convergence_writers.py` writer shape.
- `scripts/gs102_convergence_sweep.py`: CLI driver — given a list of
  case-id + mesh-id + dt rows + paths to existing `ballistic_metrics.json`
  outputs in `project_state/graph_executor/`, emits the merged study.
  Refuses output paths under `golden_samples/**`.
- Tests: synthetic 3×3 mesh × dt grid with monotonically improving residual
  velocity → stable verdict; non-monotonic → unstable verdict; <3 points →
  insufficient_data. New file `tests/test_convergence_orchestrator.py`.

### Phase C — Workbench multi-case picker

**Goal:** a Workbench user can switch between the three candidate decks
(`GS-102-candidate`, `GS-102-refined-candidate`, `GS-102-hifi-candidate`)
without code changes.

**Deliverables:**

- `backend/app/api/routes/candidate_cases.py` (NEW): `/candidate-cases`
  endpoint enumerating available `golden_samples/GS-102-*-candidate/`
  directories, returning case-id, mesh-id, deck file paths, generator script
  path, and NOTES.md excerpt. Read-only; never writes to `golden_samples/**`.
- `frontend/src/candidateCaseRegistry.ts` (NEW): typed contract + `useCandidateCases`
  hook calling the new endpoint with fallback to a static client-side list
  matching the on-disk dirs.
- `frontend/src/components/CandidateCasePicker.tsx` (NEW): dropdown component
  showing case + claim tier + generator script + NOTES excerpt.
- `frontend/src/App.tsx`: integrates the picker above the visual tab grid;
  the chosen case-id drives the result-mesh playback + blueprint evidence
  binding + Trust Center summary.
- Tests: `tests/test_candidate_cases_endpoint.py` (backend) +
  `frontend/test/candidateCaseRegistry.test.ts` (frontend) covering schema,
  read-only guarantee, and fallback list.

### Phase D — Trust Center industrial review cards

**Goal:** Trust Center exposes the new energy + convergence + multi-case
evidence as structured Copilot review cards consistent with existing
`blueprint_target` / `ballistic_candidate` cards.

**Deliverables:**

- `frontend/src/App.tsx`: 3 new `caeReviewCards` types:
  - `energy_balance_status` — KE_initial / plastic / contact / hourglass /
    KE_residual / balance_error_pct / `closed` vs `partial_candidate` /
    Tier 1 banner.
  - `convergence_study_status` — mesh refinement verdict + dt stability
    verdict + claim_impact wording.
  - `candidate_case_selection` — selected case id + claim tier + deck-source
    hash + generator script path.
- `frontend/src/components/ChatPanel.tsx`: filter the new card types under
  `review` and `evidence` tabs.
- `frontend/src/trustCenterSummary.ts` (NEW): pure functions returning the
  summary tone (accent / warning / danger) for the three new statuses.
- Tests: `frontend/test/trustCenterSummary.test.ts` covering tone selection
  for closed/partial/missing energy, stable/unstable/insufficient
  convergence, and selected/unselected case.

### Phase E — Tier 1 candidate report generator (markdown + DOCX)

**Goal:** one command turns a finished `project_state/graph_executor/<case-id>/`
directory into a structured Tier 1 Candidate Report packet.

**Deliverables:**

- `backend/app/services/reporting/tier1_candidate_report.py` (NEW): pure
  builder taking `(case_id, ballistic_metrics_path, energy_audit_path,
  convergence_study_path, blueprint_image_path, animation_manifest_path)`
  and returning a structured `Tier1CandidateReport` dataclass with
  assumptions / inputs / metrics / energy / convergence / blueprint /
  artifact_hashes / claim_boundary / Tier 1 banner sections.
- `scripts/export_tier1_candidate_report.py` (NEW): CLI driver writing both
  `<case-id>_Tier1_candidate_report.md` and `_Tier1_candidate_report.docx`
  under `reports/`. Refuses output paths under `golden_samples/**`. The
  DOCX output reuses `python-docx` (already a dep).
- `backend/app/api/routes/tier1_report.py` (NEW): `/tier1-report/<case-id>`
  endpoint streaming the generated DOCX. Read-only; writes only to
  `reports/` (already mutable).
- Tests: `tests/test_tier1_candidate_report.py` covering synthetic input →
  every banner present, every section populated, all 5 energy terms in
  output, claim_boundary wording present, forbidden-wording audit clean.

### Phase F — End-to-end synthetic integration test

**Goal:** prove the whole Phase A-E loop with one test from synthetic
OpenRadioss output to exported report.

**Deliverables:**

- `tests/test_fm04a_phase2_e2e.py` (NEW): synthesizes engine.log + A-frame +
  ballistic metrics + convergence rows for a fictional `GS-102-fixture-e2e`
  case → extracts energy audit → runs convergence orchestrator → calls
  Tier 1 report builder → asserts every artifact has hash + every Trust
  Center summary helper returns the right tone + forbidden-wording audit
  passes.

### Phase G — STATE refresh + Phase 2 retrospective

**Goal:** `.planning/STATE.md` reflects the new local-only Phase 2 ledger
and a retrospective documents what changed vs the original FM-04a plan.

**Deliverables:**

- `.planning/STATE.md`: new Phase 2 section listing every commit SHA from
  Phase A-F with one-line summary; updated `Last updated:` stamp.
- `.planning/retrospectives/fm04a_phase2_industrial_polish.md` (NEW):
  what each phase delivered, what was deliberately deferred, the running
  diff between this plan and `.planning/FM-04B_READINESS.md` (still
  separating Tier 1 closure from Tier 2 prerequisites).

---

## Verification gates (mechanical only)

Each phase commit must satisfy:

1. **pytest:** all new tests pass; full repo-root `pytest -q` returns no
   regressions vs the post-Phase 7-slice baseline (1244 passed / 8 skipped).
2. **frontend node:test:** all new tests pass.
3. **frontend tsc -b + vite build:** clean.
4. **pre-commit:** ruff + ruff-format + HF1 path-guard all pass. When a phase
   touches `golden_samples/*-candidate/**` the commit uses
   `HF1_GUARD_OVERRIDE=<reason citing ADR-011 §HF1.7 + FM-04a P3 precedent>`.
5. **forbidden-wording audit:** every new doc/code path with public wording
   is grep-clean against the ADR-024 lite forbidden list (`validated against`,
   `benchmark agreement`, `signed validation`, `perforation completed`,
   `bullet-through-steel complete`, `validated physics`).

No real-solver execution is required. No external review gate is required
inside Tier 1 candidate work.

---

## What this blueprint deliberately does NOT do

| Out-of-scope item | Where it lives | Why deferred |
|---|---|---|
| ADR-024 (full) authoring | FM-04b P2-full | governance-grade ADR; needs owner approval |
| `benchmark_comparison_candidate.json` schema + producer | FM-04b P7 | benchmark linkage is Tier 2 |
| Sealed packet (SHA freeze, manifest of manifests) | FM-04b P8 | Tier 2 sealing |
| Independent reviewer signoff path | FM-04b P8 | Tier 2 reviewer gate |
| User milestone-experience acceptance | FM-04b P9 | reserved for the human user |
| `^GS-\d{3}$` flip from `GS-102-candidate` to `GS-102` | FM-04b P9 | Tier 2 promotion |
| Notion / Linear mirror writes | FM-04a / FM-04b alike | user-controlled |
| Real OpenRadioss container runs | environment, not code | code is solver-input-agnostic |
| `agents/solver.py` / `agents/router.py` HF1 zone edits | HF1 hard-stop | no need; new code lives outside HF1 surfaces |

---

## Execution policy

- Atomic commits per phase deliverable. Commit messages follow the existing
  Tier 1 candidate style (`feat(...)`, `chore(...)`, `docs(...)`, `test(...)`).
- HF5 trailer rewrite is deferred to push-time per existing FM-04a convention.
- Each phase closes with a plain-Chinese summary to the user covering: what
  changed, what tests prove it, where in `.planning/` the evidence sits, and
  what's next.
- Mid-phase blockers escalate to the user immediately; otherwise the run is
  autonomous until Phase G ships.

---

## Anti-drift checklist (re-read before every phase commit)

- [ ] Is the artifact under `*-candidate/` or outside `golden_samples/**`?
- [ ] Does every new public claim include `Tier 1 engineering candidate; not
  signed validation; not benchmark agreement`?
- [ ] Is there zero new `benchmark` / `validated against` / `signed`
  wording?
- [ ] Are tests covering the synthetic path so real-solver absence does
  not block CI?
- [ ] Does `.planning/FM-04B_READINESS.md` still describe the same Tier 2
  prerequisites unchanged?

If any answer is "no", the commit gets reworked, not merged.
