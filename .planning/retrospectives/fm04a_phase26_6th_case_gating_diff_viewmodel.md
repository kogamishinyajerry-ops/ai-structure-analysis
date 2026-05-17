# FM-04a · Phase 26 retro · 6th validated case + Basic-mode gating + probe diff + view-model extraction

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-25.

## Scope

| Slice | What landed | Commit | Tests |
|---|---|---|---|
| 26 A | 6th tier_2_validated case `cantilever-beam-modal-candidate`; first `*FREQUENCY` solver kind in validated cohort; live ccx residual **+0.13%** (tightest across all 6 cases) | `10f4168` | 15 unit + @requires_solver E2E pin |
| 26 B | Full Basic-mode gating: section cut + threshold filter + field-component switcher now actually hidden in basic mode | `ac87e41` | 7 new + 11 existing tests updated |
| 26 C | Probe-list A-vs-baseline Δ column (D:-2 PIN ORDER, E:-1 null propagation, E:-2 hide when count<2, Unicode minus) | `4a1d87b` | 18 new + 2 Phase 24 D loosened |
| 26 D | Trust Center view-model extracted to pure builders (trustStrip + 5/7 sections + statusTone); HONEST LOC MISS (App.tsx 1446 → 1464) | `05e0f21` | 24 new |

Total: 64 new tests; 452 frontend pass; 292 backend (Phase 18-26) pass.

## Composite trajectory

| Phase | Reported composite | Honest composite | Inflation | Per-phase honest lift |
|---|---|---|---|---|
| 22 | 77.1 | ~75 | ~+2 | baseline |
| 23 | 78.7 | ~76 | ~+3 | +1 |
| 24 | 80.9 | ~75 | ~+6 | -1 |
| 25 | 82.1 | ~72.2 | **~+10** | -3 |
| **26** | **74.7** | **74.7** | **0** | **+2.5** |

**Phase 26 is the honest re-baseline event.** Per 绝对诚实客观
contract this recalibration is named verbatim in FINAL.md and not
buried. The -7.4 swing from reported Phase 25 (82.1) to Phase 26
(74.7) is the inflation correction; the +2.5 over HONEST Phase 25
(~72.2) is the real signal.

## Honest scope misses (named verbatim)

1. **App.tsx LOC target <1300 MISSED by 164** — Phase 26 D's
   extraction GREW the file (1446 → 1464). The trade was real
   (24 tests of pure-builder isolation + statusTone dedup) but the
   primary KPI on this slice missed. The retro names the LOC miss
   verbatim and adds "actual delta on App.tsx LOC after extraction"
   to the Phase 27 punchlist.

2. **Phase 25 inflation correction paid in this phase** — UX 84.0 →
   76.8 (-7.2), UI 86.4 → 72.3 (-14.1) are recalibrations, not
   regressions. Phase 21-25 UI Dim 1 was awarding 75-80 points for
   "decomposition in progress" while absolute App.tsx LOC grew
   every phase. The rubric is now `(target_LOC / actual_LOC) × 100`
   anchored at the 1300 target. Future phases compare against this
   honest baseline.

3. **Tour copy not refreshed** — written for Phase 24 B; doesn't
   mention Phase 25 C Basic mode or Phase 26 C Δ column. Honest
   Phase 26 carry-over.

4. **Blueprint target + Ballistic candidate sections still inline
   in App.tsx** — they close over many derived locals; their
   context interfaces would balloon. Honest scope; explicitly
   documented in `trustCenterViewModel.ts` and in Phase 26 D's
   commit message.

5. **Apple-tier polish BREADTH stalled** — Phase 25 D shipped tour
   fade-slide + CSV; Phase 26 added baseline tag + Unicode minus
   but no new motion. Row-easing / slider tracks / hover preview
   still open.

6. **No Round 2 spawned** — Round 2 here would polish 1-2 sub-
   dimensions but cannot move the composite to 99 or even
   meaningfully toward the next 5-point step. Per v2.3 round-cap=3
   and prior phases' "Round 2 = score-padding" discipline.

## What worked

- **Self-contained runner pattern** carried forward from Phase 25 A:
  Phase 26 A's `cantilever_modal_runner.py` follows the same hand-
  rolled INP composition (no tier2_pipeline) used for the plate-SS
  multi-edge BC. The pattern is now load-bearing for ANY validated
  case whose constraint topology exceeds the single-BoundaryConditionSpec
  shape; future shell + contact cases will reuse it.

- **Additive promotion pattern for registry pin loosening** — Phase
  26 A's loosen of Phase 25's strict `len(validated) == 5` pin to
  subset-of (preserving Phase 25's intent of "5 cases REQUIRED
  present") is now the third instance of this pattern (Phase 22,
  Phase 23, Phase 26). Stable convention.

- **Two-tier anti-gaming guards** — Phase 26 A introduced A:-1
  (rigid-body-mode filter) pinned at BOTH the runner level
  (`_filter_rigid_body_modes`) AND the test level (stub-list pin
  asserting filter behavior on `[1e-6, 5e-7, 66.93, 416.45, 1153.11]`).
  Two-tier pinning is now the convention for ALL anti-gaming
  guards in Phase 27+.

- **Pure-builder extraction with context interfaces** — Phase 26 D
  proves the pattern (24 tests; D:-3 no-mutation guard; statusTone
  dedup) even though it didn't shrink App.tsx. Phase 27's first
  punchlist item (`b/c` Blueprint or Ballistic extraction) follows
  the same shape.

## What didn't work

- **Phase 26 D's LOC-target framing** — the blueprint said "target
  <1300"; the extraction shape (per-section context objects, multi-
  line) actually grew App.tsx by 18 lines. The real value
  (test-isolation, dedup) was orthogonal to LOC. Phase 27's
  punchlist explicitly says "actual delta on App.tsx LOC after
  extraction" — measure-twice-extract-once.

- **No Sub-Dimension review for honesty BEFORE the audit reports** —
  the inflation accumulated across Phase 21-25 because no
  intermediate audit caught it. Phase 27 should run a
  "self-recalibration" mini-audit at mid-phase, before Phase 27 E
  audits.

- **Punchlist carried forward** — items 1 (CalculiX static viewer
  σ-tensor path), 2 (Real WebGL E2E), 4 (App.tsx full
  decomposition) are still listed verbatim from Phase 24 or Phase
  25 retros. Carrying these is honest but Phase 27 should pick at
  least one and close it.

## v2.3 disposition

- 1 sub-phase = Phase 26 (4 slices) = 1 retro at phase-close ✓
- counter += 4 (telemetry only; not a stop signal)
- No Codex review triggered (no auth / signing / 安全边界 risk-tier
  hit)
- No charter triggered (no 3-module shared-code-path scope; all
  changes within frontend/src/components/, frontend/src/state/,
  backend/app/services/cross_check/, backend/app/services/reporting/_claim_tier.py)
- DEC frontmatter 6-field minimum: this retro IS the DEC for Phase
  26 (status=Accepted at commit, parent_dec=Phase 26 blueprint,
  notion_sync_status=pending session-end batch sync)

## Phase 27 opening punchlist (carried from Phase 26 R1 FINAL)

1. App.tsx LOC reduction PROPER (Blueprint OR Ballistic section
   extraction; measure-twice).
2. 7th validated case — shell element (S4) candidate.
3. Apple-tier polish breadth pass.
4. Tour copy refresh.
5. Real WebGL E2E.
6. Trust-strip / sections memoization.
7. Iso-surface rendering.
8. Probe-list save/restore across sessions.
9. Second modal case (different aspect ratio).
10. CalculiX static viewer σ-tensor path (Phase 24 carry-forward).

## Decision

Phase 26 closes at honest composite **74.7/100**,
CHANGES_REQUIRED. +2.5 over honest Phase 25. The honest re-baseline
event paid in this phase keeps the 99/100 target meaningful as a
multi-phase commitment, not a moving target.

Not signed validation; not benchmark agreement.
