# FM-04a · Phase 30 retro · first *DYNAMIC + companion viewport + corrupted toast + coord readout + convergence study

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-29.

## Scope

| Slice | What landed | Commit | Tests |
|---|---|---|---|
| 30 blueprint | 5-slice plan, projection band 86.8-88.7 | `ba009f9` | — |
| 30 A | 10th tier_2_validated case `cantilever-dynamic-candidate` — **FIRST `*DYNAMIC` (transient implicit) validated case**; -1.1928% residual; 600 increments / 8 zero crossings; cross-validates Phase 26 A's eigenvalue result via independent time-domain path; sub-sampling bug + DIRECT-mode fix documented | `a2e3b7c` | 22 unit + 2 @requires_solver |
| 30 B | 2-quadrant viewport split + section-cut companion (`CompanionViewport.tsx` + `companionViewportStorage.ts`); advanced-mode gated; viewport-row restructured to flex column with probe-list lifted out of primary-slot; Phase 25 C registry pin extended additively | `a054995` | 36 frontend |
| 30 C | Toast-surface corrupted-key warn (Phase 29 D devtools-only → user-visible `role="alert"` toast) + Hyperworks-style 30Hz throttled coord-readout tooltip (`CoordReadoutTooltip.tsx` + viewport `onHoverCoords` prop) | `e935c63` | 23 frontend |
| 30 D | Convergence-study artifacts for 2 representative cases (plate-ss-shell n=10/20/40 + cantilever-modal cl=12/8/5 mm); runner-agnostic `convergence_study.py` helper; cylinder-pv honestly deferred with pin | `1b34f5e` | 32 backend |
| 30 E | 3 sub-agent audits (UX 90.3 / FEA 84.17 / UI 87.0); FINAL synthesis; retro; STATE | (this commit) | — |

**Total: 115 new tests** (54 backend + 59 frontend + 2
@requires_solver E2E). Frontend 687/687 PASS across 46 files;
backend Phase 30 A live ccx 2.23 ran PASS at -1.1928%; Phase 30 D
6 live convergence runs all PASS.

## Composite trajectory (honest)

| Phase | Honest composite | Per-phase Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 26 | 74.7 | +2.5 (honest re-baseline) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| 29 | 84.23 | +4.63 |
| **30** | **87.16** | **+2.93** |

**Phase 30 is the fifth inside-band landing in a row** and the
second-largest per-phase Δ since Phase 27. Lift driven primarily
by FEA (+6.67) — the first `*DYNAMIC` ship alone moved FEA Dim 6
from 50 → 75 (rubric anchor exact, +25 single-axis).

## What worked

### Single-axis structural lift trumps polish accumulation (third phase running)
- Phase 28 (polish-heavy, +1.1) confirmed via Phase 29 (shells +
  primitive, +4.63) confirmed again via Phase 30 (`*DYNAMIC` +
  multi-viewport, +2.93). The pattern is **"ship the single
  biggest single-axis lift available; multi-axis polish
  bundles deliver less than half the composite Δ."**
- Phase 30 A's FEA Dim 6 +25 = +4.17 FEA-composite alone =
  +1.39 composite alone. The other 4 slices combined moved the
  needle +1.54. Roughly 50/50 between one structural ship and
  four polish/refactor slices.

### Honest convergence-study revelation
- Phase 30 D's plate-ss-shell convergence revealed S4 + Mindlin
  thick-shell kinematics converges to a +1.2% bias as h→0, NOT
  to zero. **Phase 29 A's canonical +0.49% residual was the lucky
  mid-range crossing through zero, not the converged value.**
- The artifact records this HONESTLY: `trend_monotone=false`,
  pinned by a dedicated test that trips if a future runner
  tweak makes it monotone (would suggest fudging).
- This is the most valuable kind of self-correction the 绝对诚实
  客观 contract makes possible. Future S4 cases will benchmark
  against the +1.2% bias, not 0.

### Sub-sampling bug caught + fixed in-phase
- Phase 30 A's first run produced an observed period of 31 ms
  vs analytical 14.96 ms (2× = classic aliasing). Root cause:
  CCX adaptive time stepping took only ~16 increments over
  60 ms — ~4 samples per period.
- Fix: `*DYNAMIC, ALPHA=0, DIRECT` forces fixed dt → 600
  increments → 150 samples per period → clean zero-crossing
  detection → -1.19% residual.
- Lesson preserved in NOTES.md + code comment + Phase 30 A
  commit message + this retro. Pattern: **for transient
  cross-checks, always force DIRECT mode + a dt that gives
  ≥ 20 samples per the analytical period.**

### Rubric v1.0 tightened to 0.01 points
- Phase 28 E pre-rubric: abs/delta gap 2.7
- Phase 29 E rubric v1.0 first use: 0.04 ✓
- Phase 30 E rubric v1.0 second use: **0.01** ✓
- The anchored scoring is working as designed; sub-agent drift
  remains closed. No v1.1 bump needed — every Phase 30 score
  landed at or between existing anchors.

### 3 parallel audit agents = 1.3× wall-clock cost, 3× depth
- Phase 30 E spawned UX/FEA/UI agents concurrently from a single
  Agent-tool message. Each ran ~8-10 min concurrently. The
  alternative (sequential agents) would have taken ~25-30 min;
  the parallel spawn took ~10 min wall-clock.
- Each agent independently read `RUBRIC.md` and verified file:line
  evidence in the tree. Synthesis was straightforward because
  each agent surfaced its top-5 evidence citations + carry-
  forward gaps in a structured tail section.

### Honest scope deferrals make Phase 30 D shippable
- Blueprint targeted 3 convergence artifacts (plate-ss-shell,
  cylinder-pv, cantilever-modal). Phase 30 D shipped 2 +
  documented cylinder-pv deferral with a dedicated test
  (`test_cylinder_pv_convergence_deferred`).
- The deferral test pins BOTH (a) the runner signature lacks a
  mesh-tunable param AND (b) no stub artifact exists. A future
  maintainer who closes the gap removes the test; the present-
  day Phase 30 D ships with the proof-of-pattern intact.
- This is the same "fail in-tree with documented rejection"
  pattern Phase 28 A established for C3D8 cantilever and
  Phase 29 A reused for S4 sign convention. **Third application
  of the pattern across 3 phases.**

## What didn't work / honest debt

### 1. ResultMeshPlaybackPanel grew to 1515 LOC
- Phase 30 B + 30 C added Compare-cuts + corrupted-toast +
  hover-coords + companion-state + tooltip render into a panel
  that was already 1279 LOC pre-30. Net +236.
- App.tsx still at 1457 (UNCHANGED in Phase 30).
- The reducer-extraction debt (Phase 27 punchlist #3 →
  Phase 29 recommendation #2) is now 3 phases unpaid. UX Dim 3
  took a -1 debit this phase explicitly for this surface-area
  growth.
- **Phase 31 must close this**. A `useViewportLayout` custom
  hook collapsing (showCompanionViewport, companionSectionCut,
  hoverCoords, viewportMode, corruptedToast) is the cheapest
  next step.

### 2. Phase 30 D 3-of-3 → 2-of-3 honest scope cut
- Blueprint scoped 3 convergence artifacts; cylinder-pv runner
  has no tunable mesh param. The right call was to defer and
  pin; the wrong call would have been to extend the runner
  scope creep into Phase 30 D.
- But the FEA Dim 5 score (86) reflects this — anchor 90
  requires ALL cases having convergence, not 2 of 10.

### 3. Layout-swap motion gap on Compare-cuts toggle
- Compare-cuts flips instantly with no width transition.
  Motion-vocabulary inconsistency vs the established 200 ms
  ease-out anchor. UX Dim 4 90 → 99 anchor calls this out.
- Cheap fix (10-15 LOC CSS) deferred to Phase 31.

### 4. CoordReadoutTooltip integration tested in pieces
- jsdom cannot exercise real `THREE.Raycaster`. The
  ResultMeshWebGLViewport raycast → setHoverCoords → tooltip
  render path is verified only by code review.
- Real WebGL E2E via playwright is the cross-cutting blocker
  (carry-over from Phase 26-29). UI auditor flagged this as
  a 99-ceiling condition on Dim 5.

### 5. Phase 30 A residual sign is NEGATIVE
- Phase 26 A modal eigenvalue: +0.13% (period 0.13% too long;
  stiffer than analytical).
- Phase 30 A `*DYNAMIC` time-domain: -1.19% (period 1.19% too
  SHORT; same stiffness direction but larger magnitude).
- NOTES.md hypothesizes mode-3 contamination from half-sine
  impulse shape (3rd mode is 6.27× higher per Euler-Bernoulli
  (β₃/β₁)²; small admixture shortens apparent zero-crossing).
- Hypothesis is unfalsified, not proved. Phase 31 spike: square-
  wave impulse OR longer pluck duration to suppress mode-3
  excitation. If period returns to ~+0.13%, hypothesis confirmed
  and Dim 3 honest-scope discipline lifts 95 → ~97.

## Lessons for Phase 31+

1. **The +25-on-one-axis pattern is repeatable when there's a
   structural blocker to remove.** Phase 30 A removed the Dim 6
   floor. Phase 31's equivalent would be `*CONTACT PAIR` to
   remove Dim 1's contact-class hard cap (+5 single-axis).
2. **2 of 3 + honest deferral test** beats **fabricated 3 of 3**.
   The deferral test surfaces the gap rather than averaging it
   away.
3. **Convergence studies reveal honest bias** even when residuals
   pass — Phase 28 A's +0.49% was lucky; Phase 30 D revealed the
   converged S4 bias is +1.2%. Future S4 cases must benchmark
   against +1.2%, not 0.
4. **Reducer extraction debt compounds.** 3 phases unpaid.
   Phase 31 must close it.
5. **Composite ceiling is ~95 under the honest contract; not
   99.** Phase 30 at 87.16 is ~8 points below the ethical
   ceiling, ~12 below 99. The final 4 points to 99 require
   signed external verification which the project forbids.
   Plan accordingly.

## Pre-blueprint Phase 31 priorities (synthesized from 3 audits)

### Tier 1 (biggest single-axis lifts available)
- `*CONTACT PAIR` Hertz contact case — FEA Dim 1 80 → 85.
- Convergence pattern extension to 7 remaining cases (start
  with cylinder-pv runner mesh param) — FEA Dim 5 86 → 89.
- Reducer extraction (`useViewportLayout` + `useTrustSections`-
  style) — UX Dim 3 88 → 91 + UI Dim 6 maintainability.

### Tier 2 (smaller but real)
- Compare-cuts visible in basic-mode + companion node-pick
  wiring — UI Dim 5 86 → 88.
- Layout-swap motion + WebGL context-loss handler — UX Dim 4
  + Dim 6 cross-cutting lift.
- Token the warning-tinted toast colors — UI Dim 3 85 → 88.

### Tier 3 (architectural multi-phase)
- `*DYNAMIC, EXPLICIT` ballistic case (Milestone 4).
- Real WebGL E2E via playwright (Phase 26-29-30 carry-over).
- Composite-layup S4, `*HEAT TRANSFER`, branching onboarding.

## Hard-constraint compliance (carry-over from Phase 18-29)

- HF1.7a signed-registry hard-stop: PASS
- HF1.7b `*-candidate` carve-out: PASS (cantilever-dynamic-candidate)
- HF1.8 path-guard self-protection: PASS
- tmp_path-only test snapshot writes: PASS (excl.
  golden_samples per HF1.7b)
- v2.3 round cap = 3: NOT triggered
- DEC frontmatter 6-field minimum: phase30_FINAL.md doubles
- confidence: high tag on every Phase 30 commit (a2e3b7c,
  a054995, e935c63, 1b34f5e)
- 绝对诚实客观: composite ceiling honestly acknowledged at ~95;
  blueprint band achieved without rubric drift
- prefers-reduced-motion honored on all new motion (corrupted
  toast reuses POLISH_CLASS_RESTORED_TOAST which is already
  covered by the existing reduce-motion rule)
- Anti-gaming guards at predicate level (C:-1 companion state
  preservation, D:-1 default-off + advanced-gated, E:-1
  corrupted-payload null returns + 30Hz throttle, B:-1 reduce-
  motion suppression)
- Phase 1-29 chain additive only: PASS (Phase 25 C registry
  pin + Phase 29 D tolerance dict both extended additively)
- No push / no PR / no Linear writes — local-commit only

## Notion sync disposition

- This retro: NOT synced to Notion (per v2.3 rule §"Notion 仅
  sync Status=Accepted 的 DEC"; retros are process artifacts).
- phase30_FINAL.md (DEC equivalent): pending session-end batch
  sync per `notion_sync_status` frontmatter convention.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
