# FM-04a Phase 2 — Industrial Workbench Closure Retrospective

> **Status:** retrospective; Phase 2 A-F shipped under direct-execution
> authorization 2026-05-16.
> **Parent plan:** `.planning/FM-04A_PHASE2_BLUEPRINT.md`.
> **Boundary anchor:** `.planning/FM-04B_READINESS.md` — Tier 2
> prerequisites unchanged.
> **Author:** local Claude Opus 4.7 (session 2026-05-16).
> **Branch:** `claude/FM-04a-tier1-ballistic-candidate`; nothing pushed,
> nothing merged, no Linear / Notion writes.

---

## Scope refresher

Phase 2 closed the four industrial-readiness gaps surfaced by the
2026-05-12 GS-102 velocity-bracket / mechanism-diagnostic arc, without
crossing any FM-04b prerequisite.

| Gap | Phase that closed it | Evidence |
|---|---|---|
| G1 — Energy audit always `partial_candidate` | A | `energy_audit_extractor.py` parses `model_00_0001.out` and graduates the audit to `closed_aggregate` when KE + I + EXT_WORK are present. |
| G2 — Convergence study stubbed | B | `convergence_orchestrator.py` + `gs102_convergence_sweep.py` produce a 2-axis study with combined verdict. |
| G3 — Workbench single-fixture | C | `/api/v1/candidate-cases` + `CandidateCasePicker.tsx` let users switch between the three candidate decks from the UI. |
| G4 — Per-run reports bespoke | E | `tier1_candidate_report.py` + CLI + endpoint render a structured markdown + DOCX packet per case. |

Phases D and F are integration layers: D wires the three new evidence
surfaces into Trust Center / Copilot review cards with the right tones;
F proves Phase 2 A → B → C → E composes cleanly on synthetic inputs in
one CI-runnable test.

---

## Commit ledger (in execution order)

| Phase | SHA | Subject | Δ tests |
|---|---|---|---|
| Blueprint | `7d7e5c6` | docs(FM-04a): authoring + execution blueprint for Phase 2 industrial polish | n/a |
| A | `b3c97ef` | feat(FM-04a/Phase2-A): closed-aggregate energy audit from engine .out | 1244 → 1261 (+17) |
| B | `346c32a` | feat(FM-04a/Phase2-B): convergence study orchestrator + sweep CLI | 1261 → 1275 (+14) |
| C | `3476280` | feat(FM-04a/Phase2-C): Workbench multi-case picker (backend + frontend) | 1275 → 1282 (+7 backend, +7 frontend) |
| D | `4a52a1a` | feat(FM-04a/Phase2-D): Trust Center industrial review cards | 1282 unchanged backend, +15 frontend |
| E | `15b671f` | feat(FM-04a/Phase2-E): Tier 1 candidate report generator (markdown + DOCX) | 1282 → 1292 (+10) |
| F | `477c529` | test(FM-04a/Phase2-F): end-to-end synthetic integration for Phase 2 A→E | 1292 → 1293 (+1) |
| G | (this retrospective) | docs(FM-04a/Phase2-G): STATE refresh + retrospective | n/a |

Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`:

- backend pytest: **1293 passed / 8 skipped**.
- frontend node:test: **29 passed** (`bulletPlateBlueprint` ·
  `resultMeshPlayback` · `candidateCaseRegistry` ·
  `trustCenterSummary`).
- `tsc -b` + `vite build` clean.
- ruff + ruff-format + HF1 path-guard all green on every Phase 2
  commit.

---

## What worked

1. **Pure-function orchestrators.** The energy extractor, the
   convergence orchestrator, and the Tier 1 report builder are all
   pure functions that take pre-extracted inputs. CI exercises them
   with synthetic data, and the real-world CLI wrappers (`scripts/`)
   handle the on-disk reads + writes. That separation let Phase F
   prove the full A → E loop in a single 0.5-second test without
   OpenRadioss / Docker.
2. **Honest aggregation.** The Phase A energy audit doesn't fake a
   per-term breakdown — it surfaces `breakdown_status:
   aggregated_into_internal_energy` and points at `/TH/PART` /
   `/TH/MAT` as the future cards needed for separable plastic /
   contact / hourglass output. The 19% balance error observed against
   the real `GS-102-transient-text-to-cae-v830-adapter-20260512` run
   is exactly the kind of honest Tier 1 signal that downstream review
   should see.
3. **Forbidden-wording audit at every layer.** Every module asserts
   no `validated against` / `benchmark agreement` / `signed validation`
   / `perforation completed` / `bullet-through-steel complete` /
   `validated physics` positive claim leaks. The Phase F test
   re-runs that audit across the full combined haystack
   (markdown + study payload + picker payload + audit block) and the
   Tier 1 boundary survived end-to-end.
4. **Fallback-first frontend registry.** The candidate-case picker
   ships a static `FALLBACK_CANDIDATE_CASES` list matching the
   on-disk dirs, so the Workbench still renders the picker (and the
   blueprint anchored to a chosen case) even when the backend is
   unreachable.
5. **Trust Center tone helpers are pure.** Phase 2 D tone selection
   is a small TypeScript module with no React imports, exercised by
   15 node:test cases. That lets future surfaces (e.g. an FM-04b
   reviewer dashboard) reuse the same accent/warning/danger logic
   without forking it.

---

## What's deliberately deferred (still NOT done)

These are the FM-04b prerequisites preserved unchanged from
`.planning/FM-04B_READINESS.md`. Phase 2 did not touch any of them.

1. ADR-024 (full) — locked benchmark case + tolerance + uncertainty
   interval + citation compliance.
2. `benchmark_comparison_candidate.json` — comparison vs Borvik 2002
   experimental data.
3. Sealed packet (SHA freeze + manifest of manifests).
4. Independent reviewer signoff path.
5. User milestone-experience acceptance.
6. `^GS-\d{3}$` registry flip from `GS-102-candidate` to `GS-102`.
7. Linear / Notion mirror writes.
8. `agents/solver.py` / `agents/router.py` / `schemas/sim_state.py`
   HF1 zone edits.
9. Real OpenRadioss container runs against the hifi 7.62 AP-class
   deck. Phase 2 makes the Workbench *ready* to ingest that output;
   actually running the solver is environment work.
10. Per-term plastic / contact / hourglass energy breakdown via
    `/TH/PART` cards in the starter. The Phase 2 A audit honestly
    surfaces this as an aggregated number until the cards land.

---

## Process notes (lessons for the next phase plan)

1. **Slice 0 — clean up runtime junk first.** `GS-102-hifi-candidate/data`
   had 18 runtime `model_00A###` files committed locally in violation
   of its own NOTES policy. Catching it in a pre-commit slice
   (commit `2f55608`) was cheaper than re-doing the registry walk
   later.
2. **Glob mistakes are silent.** The Phase 7-slice commit
   `f421221` initially only landed 6 reports because the glob
   `reports/gs102_*_20260512*.md` matched underscore-before-date
   filenames but not hyphen-before-date filenames. The follow-up
   commit `88362ad` caught it. A `git diff --cached --stat | wc -l`
   sanity check before committing would have caught the gap.
3. **ruff-format rewrites need re-staging.** Several Phase 2 commits
   required two attempts because the pre-commit `ruff format` hook
   reformatted staged files, and the commit needed to re-stage after
   the rewrite. Worth documenting in `AGENTS.md` for future
   automation.
4. **Test fixtures benefit from a top-level `# ruff: noqa: E501`.**
   The OpenRadioss `.out` rows are wide-column by spec; preserving
   their wire format is worth more than a 100-char line cap. Same
   trick used in `test_engine_energy_history.py`,
   `test_energy_audit_extractor.py`, and `test_fm04a_phase2_e2e.py`.
5. **Phase D's "live vs fallback" indicator is load-bearing.** The
   candidate-case picker degrades to a static list when the backend
   is unreachable; Trust Center's `candidate_case_selection` card
   reflects that explicitly so reviewers don't mistake fallback
   evidence for live evidence. Future phases should keep this kind
   of explicit downgrade signal.

---

## Next recommended slices (outside Phase 2 scope)

These are candidate next slices for a future Phase 3 or a separate
FM-04a polish branch. **None of them is authorized by this
retrospective** — they're a backlog for the user.

1. **Per-term TH cards.** Add `/TH/PART/...` to the candidate decks
   so the engine writes a `.thy` time-history binary; add a `.thy`
   parser; replace `aggregate_internal_energy_j` with separated
   `plastic_dissipation_j` / `contact_friction_j` /
   `hourglass_energy_j` in the audit. Pair with a `/TH/` validation
   commit so the next 33 runs upgrade naturally.
2. **Live convergence sweep dispatcher.** `gs102_convergence_sweep.py`
   today reads existing sidecars; the next step is a dispatcher
   that runs the OpenRadioss container N times across a (mesh, dt)
   grid + collects sidecars + calls the orchestrator. Tier 1
   candidate-only.
3. **Frontend convergence study viewer.** Show the orchestrator's
   `convergence_study.json` as a 2-axis plot in the Visual tab
   beside the playback panel. Use the existing tone helpers for
   tabular cell coloring.
4. **End-to-end hifi smoke.** Run the OpenRadioss container against
   `GS-102-hifi-candidate` at V0 = 600 m/s once on a machine that
   has the container, attach the resulting evidence to a new run
   report, and exercise the Tier 1 report generator on that real
   output.
5. **`/api/v1/tier1-report` integration test.** Wire FastAPI's
   TestClient (or `httpx.AsyncClient`) into a test that hits the
   live endpoint with a synthetic case-id and verifies both `fmt=md`
   and `fmt=docx` produce 200-OK responses with the right MIME
   types and Content-Disposition headers.

---

## Final claim boundary

Every artifact produced in Phase 2 carries the same boundary the
blueprint promised: **Tier 1 engineering candidate; not signed
validation; not benchmark agreement**. FM-04a remains
**not user-accepted at the milestone checkpoint**; FM-04b remains
**not authorized**. Nothing in this branch promotes any
`*-candidate` directory to a `^GS-\d{3}$` signed entry, attaches a
benchmark comparison, or seals a Tier 2 packet.

The branch is ready for whatever the user wants next: push +
trailer-rewrite for PR review, hand off to another agent, or sit on
it until FM-04b authorization.
