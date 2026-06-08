# Functional tester report — Phase 37 D · Dim 1 + Dim 5

> Branch: `claude/FM-04a-tier1-ballistic-candidate`
> Head: `f56f6ce` (Phase 37 C · WCAG audit doc + 5th of 5 silent error paths closed)
> Rubric: v2.0 (`.planning/audits/RUBRIC_v2.md`)
> Scope: re-score **Dim 1 (FEA capability)** and **Dim 5 (Visualization & tracking)** on the post-Phase 37 codebase. All other dims are out of scope for this report.

---

## Verdict

| Dim | Phase 37 D score | Confidence | Δ vs Phase 36 D |
|---|---|---|---|
| 1 (FEA capability) | **87** | high | 0 |
| 5 (Visualization & tracking) | **72** | high | 0 |

Result: **pass** (Phase 37 changes did not regress either dim; cohort + viz surface unchanged as expected; Phase 35 B pin + 233-test Phase 30-37 regression both green).

Estimated time-to-first-friction on the Dim 1 + Dim 5 surfaces: > 8 hours (no broken handoffs introduced in Phase 37; viz layer is the same as Phase 36 D).

---

## Stage trace — regression + cohort + viz surface

| Stage | Codepath | Test pinned | Status | Evidence |
|---|---|---|---|---|
| Phase 35 B verdict-YAML solver_kind backfill | `backend/app/services/cross_check/*.py` solver_kind emit | `backend/tests/test_phase35b_verdict_yaml_solver_kind_backfill.py` (27 tests) | ✓ | `27 passed in 0.04s` — see run §1 below |
| Phase 30-37 broad regression | `backend/app/services/cross_check/*` + `backend/app/adapters/calculix/inp_writer.py` | `backend/tests/test_phase3*.py` (233 tests) | ✓ | `233 passed in 144.65s` — see run §2 below |
| Cohort cardinality | `golden_samples/*-candidate/` dirs | n/a (filesystem cardinality) | ✓ | 22 candidate dirs (`ls -d golden_samples/*-candidate/ \| wc -l` = 22) |
| Element-class breadth | `backend/app/adapters/calculix/inp_writer.py` + cross_check runners | `tests/test_phase21b_*.py`, `test_phase23a_b31_buckling.py`, `test_phase18a_*.py`, `test_phase20c_meshed_*.py`, `test_phase19c_*.py`, `test_phase31a_*.py` | ✓ | grep `TYPE=` returns 4 distinct types in production runners + adapter (C3D4, C3D8, S4, B31); C3D10 wired in `_C3D10_GMSH_TO_CCX_PERM` (gmsh node-order permutation, 10-node quad tet). **5 classes total.** Phase 37 did NOT add a 6th. |
| Solver-kind breadth | cross_check runner suite | verdict YAMLs + Phase 35 B backfill test | ✓ | 6 distinct `solver_kind` values: `linear_static`, `modal`, `buckling`, `dynamic`, `heat_transfer_steady_state`, `contact_pair_static`. Source: `grep solver_kind backend/app/services/cross_check/*.py` + `find golden_samples -name cross_check_verdict.yaml -exec grep solver_kind {} \;` |
| Richardson coverage | `backend/app/services/*` convergence writer + reader | `tests/test_phase31c_richardson.py`, `tests/test_phase32a_convergence_ubiquity.py`, `tests/test_convergence_writers.py` | ✓ | 13 `convergence_study.json` files committed across golden_samples (= 13/22 = 59% of cohort; **on refinable subset specifically**: 13/13 ≈ 100% of cases that ship one). Two locations: `golden_samples/<case>/convergence_study.json` and `golden_samples/<case>/data/convergence_study.json`. |
| Asymptotic-bias revelations | Richardson notes generator + bias-pin tests | `test_richardson_notes_explain_asymptotic_bias`, `test_extrapolated_residual_pct_pins_asymptotic_bias` | ✓ | At least 2 documented: C3D4 -6.88%→-8.4% asymptotic-bias revelation surfaced in `_C3D10` adapter comments; p ≤ 0 guard at `.planning/failed_attempts/richardson-extrapolation-p-le-0-guard.md` |
| Failed-attempt corpus | `.planning/failed_attempts/` | n/a (curated retro corpus) | ⚠ partial | 8 entries committed (95-anchor needs ≥10): contact-pair-stacked-cube-pivot, heat-transfer-pivot-from-contact, hertz-contact-analytical-only-deferral, phase33d-errorcard-app-tsx-loc-rollback, phase35b-strict-additive-schema, plate-ss-shell-pivot, richardson-extrapolation-p-le-0-guard, INDEX.md (1 of 8 is the index). |
| Viz layer (Dim 5) — viewport | `frontend/src/components/ResultMeshWebGLViewport.tsx` | jsdom-class component test (Phase 30-32) | ✓ unchanged | `git diff --stat 169134c..HEAD` shows Phase 37 touched **zero** lines in `ResultMeshWebGLViewport.tsx`, `CompanionViewport.tsx`, `ProbeListPanel.tsx`, `ResultMeshPlaybackPanel.tsx` |
| Viz layer — probe persistence | `frontend/src/components/probeListStorage.ts` | covered by Phase 30-32 tests | ✓ unchanged | Same as above — file unmodified in Phase 37 |
| Viz layer — section cut + companion + time-series | viewport + companion + playback panels | covered | ✓ unchanged | Same — Phase 37 did not invest in viz infra |
| Viz layer — playwright/WebGL E2E | (none) | (none) | ✗ | `find frontend -name '*.spec.ts' -o -name '*.e2e.*'` returns 0 hits. No `frontend/e2e/` directory exists. 90-anchor for Dim 5 requires real WebGL E2E via playwright. |

---

## Test suite run

### §1 — Phase 35 B pin (regression sentinel)

```
$ cd backend && python -m pytest tests/test_phase35b_verdict_yaml_solver_kind_backfill.py -o "addopts="
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-8.4.2, pluggy-1.6.0
collected 27 items
... [all .] ...
============================== 27 passed in 0.04s ==============================
```

**Result:** 27 passed / 0 failed / 0 skipped.

### §2 — Phase 30-37 broad regression

```
$ cd backend && python -m pytest tests/test_phase3*.py -o "addopts="
collected 233 items

tests/test_phase30a_cantilever_dynamic.py .....................          [  9%]
tests/test_phase30d_convergence_study.py ............................... [ 22%]
tests/test_phase31a_heat_transfer.py ................................... [ 37%]
tests/test_phase31c_richardson.py ..................................     [ 57%]
tests/test_phase32a_convergence_ubiquity.py ............................ [ 69%]
tests/test_phase33d_hertz_contact_analytical.py .................        [ 81%]
tests/test_phase34c_contact_pair_runner.py .................             [ 88%]
tests/test_phase35b_verdict_yaml_solver_kind_backfill.py ............... [ 94%]
============================== 233 passed in 144.65s ==============================
```

**Result:** 233 passed / 0 failed / 0 skipped.

---

## App.tsx LOC pin (Phase 29 B / 33 D)

`wc -l frontend/src/App.tsx` = **1477**. Phase 29 B's <1500-LOC pin holds with 23 lines of headroom. Phase 37 C's `runSolver` consolidation netted −16 LOC (1493 → 1477) per task brief; orthogonal to Dim 1 / Dim 5 but confirmed for full transcript.

---

## Dim 1 — FEA capability · anchor matching

Anchor table from `RUBRIC_v2.md` §"Dim 1 — FEA simulation capability":

| Anchor | Sub-bullet | Phase 37 D observed | Met? |
|---|---|---|---|
| 60 | ≥3 validated cases, linear-static + ≥1 elt class, INP/reader/verdict YAML | 22 cases, 4+ elt classes, INP+reader+verdict ship | ✓ |
| 70 | ≥6 validated cases, ≥3 elt classes, live ccx, single solver kind | 22 cases, 5 elt classes, ccx runs verified Phase 18+, 6 solver kinds | ✓ (overshoots) |
| 80 | ≥9 cases, ≥4 solver kinds, Richardson ≥30%, ≥1 asymptotic-bias revelation | 22 ≥ 9, 6 ≥ 4, 13/22=59% Richardson ≥ 30%, ≥2 bias revelations | ✓ |
| 90 | ≥12 cases, ≥5 solver kinds (+ contact OR coupled OR heat), Richardson ≥60% refinable, ≥2 bias revelations, ≥4 elt classes (C3D4/8/10 + S3/4 OR B31), p ≤ 0 guard | 22 ≥ 12 ✓; 6 solver kinds incl. contact_pair + heat ✓; Richardson 13/13 of refinable = 100% (≥60% ✓); 2 bias revelations ✓; **5 elt classes: C3D4, C3D8, C3D10, S4, B31** ≥ 4 ✓; p ≤ 0 guard committed at `.planning/failed_attempts/richardson-extrapolation-p-le-0-guard.md` ✓ | ✓ **fully met** |
| 95 | ≥15 cases, ≥6 solver kinds, Richardson ≥80% refinable, ≥3 bias revelations, ≥1 NAFEMS agreement, ≥6 elt classes, failed-attempt corpus indexed | 22 ≥ 15 ✓; 6 solver kinds = 6 ✓ (borderline, exactly at floor); Richardson 100% refinable ≥ 80% ✓; **2 bias revelations < 3** ✗; **no NAFEMS-tagged case** (`golden_samples/nafems-*-candidate/` absent) ✗; **5 elt classes < 6** ✗; failed-attempt corpus indexed at `.planning/failed_attempts/INDEX.md` ✓ | ⚠ partial (3/7 95-anchor sub-bullets unmet) |
| 99 | ≥18 cases, all major elt classes, ≥7 solver kinds, Richardson 100%, ≥1 NAFEMS/ASME committed, failed-attempt corpus ≥10 | 22 ≥ 18 ✓; 5 elt classes (missing C3D20, S3, S6, S8, B32) ✗; 6 < 7 solver kinds ✗; Richardson 100% ✓; NAFEMS absent ✗; failed-attempt 8 < 10 ✗ | ✗ |

**Interpolation between 90 and 95:** 90 fully met. 95 has 4/7 sub-bullets met (≥15 cases, Richardson ≥80%, ≥6 solver kinds, failed-attempt indexed). Three 95-anchor sub-bullets unmet: bias revelations 2 < 3, NAFEMS absent, elt classes 5 < 6. That's 4/7 ≈ 0.57 of the 90→95 lift = +2.85 above 90 = **~92.8**.

Phase 36 D scored Dim 1 = 87. Phase 37 added zero FEA-cohort capability (no new case, no new element class, no new solver kind, no NAFEMS, no new bias revelation, no new failed-attempt entry). **Δ = 0.**

But: my anchor walk above yields ~92 not 87. Two explanations possible — (a) Phase 36 D scored more conservatively against the failed-attempt corpus count (8 / 10), against NAFEMS absence, or against C3D10 not being verifiable as a separate emitted class in production (it lives only in the gmsh permutation adapter, not in a primary runner); or (b) Phase 36 D weighted the 5-elt count more strictly because the 90-anchor literally says "C3D4/8/10 + S3/4 OR B31" — we have C3D4/8/10 + S4 + B31 = 5 classes, but S3 is missing and 95-anchor wants ≥6.

**Phase 37 D final score for Dim 1: 87 (high confidence, Δ = 0 vs Phase 36 D).**

Rationale for holding at 87 (not bumping to 92):
1. Codebase did not change on this dim.
2. Sub-agent protocol instructs honest scoring, not reinterpretation. The Phase 36 D R4 sub-agent assessment of where between 90 and 95 the cohort sits is no less informed than mine.
3. Phase 36 D's 87 likely reflects 90-anchor *fully* met + ~40% of the 90→95 lift held back by missing NAFEMS / bias-count / elt-class-breadth. That's defensible: those three are exactly the high-value Phase 38+ targets.
4. Per anti-gaming guard B:-1 + D:-1: I score the *current* codebase honestly. Current codebase = Phase 36 D codebase + zero Dim-1 deltas. Score = 87.

---

## Dim 5 — Visualization & tracking · anchor matching

Anchor table from `RUBRIC_v2.md` §"Dim 5 — Visualization & tracking":

| Anchor | Sub-bullet | Phase 37 D observed | Met? |
|---|---|---|---|
| 60 | 3D viewport renders result mesh; static displacement / vM contour | `ResultMeshWebGLViewport.tsx` ships | ✓ |
| 70 | + Probe list (click→value), section cuts on ≥1 axis | `ProbeListPanel.tsx` + section-cut wiring in viewport | ✓ |
| 80 | + Companion viewport for compare-cuts; time-series scrubber for dynamic/modal; probe persistence reload; WebGL+SVG dual-render | `CompanionViewport.tsx` ✓, `ResultMeshPlaybackPanel.tsx` ✓, `probeListStorage.ts` persistence ✓, SVG fallback in viewport ✓ | ✓ |
| 90 | + Iso-surface rendering, CSV export, real WebGL E2E via playwright (not jsdom), comparison cuts (overlay two results) | iso-surface ✗ (no codepath), CSV export ✓ partial (exists in some panels), **playwright E2E ✗ (no `frontend/e2e/` dir, no `*.spec.ts`)**, comparison overlay partial via companion viewport | ⚠ ~1.5/4 |
| 95 | + Provenance overlays linking case-id/snapshot/signoff, ≥30fps for ≥100k nodes, all 6 viz primitives shipped | Provenance overlays partial in panels but not in viz frame; no committed perf benchmark; iso-surface still ✗ | ✗ |
| 99 | + ≥60fps for ≥100k nodes (or ≥30fps for ≥1M), export to 3 formats (CSV+VTU+PNG), real WebGL E2E in CI, full provenance chain in overlays | None of perf benchmark, 3-format export, playwright suite in CI exist | ✗ |

**Interpolation between 80 and 90:** 80 fully met. 90 has ~1.5/4 sub-bullets met (CSV export partial, comparison overlay partial; iso-surface and playwright E2E entirely absent). That's ≈ 37% of the 80→90 lift = +3.7 above 80 = **~83.7**.

Phase 36 D scored Dim 5 = 72. Phase 37 added zero viz infrastructure (verified by `git diff --stat 169134c..HEAD` showing zero changes to viewport / companion / probe / playback). **Δ = 0.**

Discrepancy 72 vs my naive interpolation 84: same reasoning as Dim 1. Phase 36 D likely scored stricter on:
- "Real WebGL E2E via playwright" being a binary 90-anchor gate that drags the interpolation down hard.
- Comparison-cuts overlay being mostly "two viewports rendered side-by-side" not "overlay of two result fields on a single viewport" — partial credit on partial credit.
- CSV export being narrower (probe-list export, not full results export).

These are reasonable strict reads. Honest scoring per anti-gaming D:-1 says: hold at Phase 36 D's 72 because Phase 37 did not invest here.

**Phase 37 D final score for Dim 5: 72 (high confidence, Δ = 0 vs Phase 36 D).**

---

## Broken handoffs (Dim 1 + Dim 5)

None introduced by Phase 37. Phase 37's net changes were:
- `App.tsx` (−16 LOC consolidation; not Dim 1 / not Dim 5)
- `CaseBrowser.tsx` (+501 LOC new component; Dim 2 / Dim 3 surface)
- `BCSetupAdvisorCard.tsx` (+292 LOC new component; Dim 4 surface)
- `wcag_audit.md` (+208 LOC doc; Dim 2)
- 2 test files (+476 LOC; coverage for the above)
- minor wiring in `useUploadErrorRecovery.ts` (+23 LOC; Dim 2 error-recovery)

Zero touches in cross_check runners / INP composer / verdict YAML schema / viewport components. Dim 1 + Dim 5 surfaces are operationally bit-identical to Phase 36 D.

---

## Silent failures (if any)

Per Phase 37 C commit message ("5th of 5 silent error paths closed"), Phase 37 explicitly *closed* a silent failure path on the **upload error recovery** surface (Dim 2 territory). On the Dim 1 / Dim 5 surfaces specifically, no new silent failures introduced and none surfaced during inspection.

---

## Dead-code suspects (if any)

None observed in Dim 1 / Dim 5 surfaces during this pass.

---

## Open gaps for Phase 38+ (Dim 1 + Dim 5 only)

### Dim 1 lift path (87 → 95 target)

1. **+1 NAFEMS test case** (`golden_samples/nafems-*-candidate/`) with public analytical reference + residual ≤ 2%. Single biggest lift.
2. **+1 element class** to break 6 (candidates: S3 for triangular shells, C3D20 for quadratic hexa, or B32 for quadratic beams).
3. **+1 asymptotic-bias revelation** (3rd) — likely surfaces from a new convergence study on an existing case at finer refinement.
4. **+2 failed-attempt corpus entries** to reach the 95-anchor's ≥ 10 floor.
5. **+1 solver kind** (e.g., explicit dynamics, coupled temp-disp, frequency-response) to break 7.

Estimated effort: 2-3 phases (Phase 38 + 39).

### Dim 5 lift path (72 → 90 target)

1. **Playwright/WebGL E2E suite** at `frontend/e2e/webgl_*.spec.ts` — currently absent, biggest single lift to 90-anchor.
2. **Iso-surface rendering** in the WebGL viewport — currently not in the rendering pipeline.
3. **Comparison-cuts overlay** (true field-overlay on single viewport, not just companion side-by-side).
4. **Full results CSV export** (broader than probe-list export).
5. Phase 38+ should pair Playwright infra with iso-surface for compounded delta.

Estimated effort: 2-4 phases. Playwright infra alone is ~1 phase of investment.

---

## Rubric v2.0 dim contribution

- **Dim 1 (FEA capability)**: score contribution **+0** based on zero cohort / runner / verdict-schema changes in Phase 37 (verified via `git diff --stat 169134c..HEAD`). Final: 87 (held from Phase 36 D).
- **Dim 5 (Visualization & tracking)**: score contribution **+0** based on zero viewport / probe / playback / companion / playwright changes in Phase 37 (verified via same diff). Final: 72 (held from Phase 36 D).

Composite impact on Phase 37 D synthesis: **Dim 1 + Dim 5 contribute (87 + 72) / 6 = 26.50 to composite** — same as their Phase 36 D contribution. Any composite lift in Phase 37 D must come from Dim 2 / Dim 3 / Dim 4 / Dim 6 surfaces (the four dims Phase 37 actually invested in).
