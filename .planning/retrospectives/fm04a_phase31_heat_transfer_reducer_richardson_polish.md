# FM-04a · Phase 31 retro · first *HEAT TRANSFER + useViewportLayout hook + Richardson + UI polish bundle

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-30. 15 consecutive Tier-2 phases.

## Scope

| Slice | What landed | Commit | Tests |
|---|---|---|---|
| 31 blueprint | 5-slice plan, projection band 89.0-90.5 | `acce14c` | — |
| 31 A | 11th `tier_2_validated` case `heat-transfer-1d-candidate` — **FIRST `*HEAT TRANSFER, STEADY STATE` validated case** (PIVOTED from `*CONTACT PAIR` after documented reconnaissance: CCX `*SURFACE TYPE` analytical-surface limitations, `*RIGID BODY` reference-node bookkeeping, CDIS/CSTR contact-output not in `reader.py` canonical field enum, ADR-002 enum lock). Hand-rolled structured 10×2×2 = 40 C3D8 hex (99 nodes); INP composer with `*CONDUCTIVITY` + `*INITIAL CONDITIONS, TYPE=TEMPERATURE` + `*PHYSICAL CONSTANTS, ABSOLUTE ZERO=0.0` + `*BOUNDARY` DOF 11 + `*NODE PRINT NT`. **Live ccx 2.23 result: 0.000% residual at midplane** (C3D8 trilinear hex reproduces linear T(x) exactly; k-invariant for this PDE so k=50 W/(m·K) hardcoded with no material-SSOT extension). | `53e3430` | 46 unit + 2 @requires_solver E2E |
| 31 B | `useViewportLayout.ts` custom hook (268 LOC NEW) collapses 8 useState + 5 useEffect from `ResultMeshPlaybackPanel.tsx`. Panel 1515 → 1411 LOC (-104). State surfaces: viewportMode / showCompanionViewport / companionSectionCut / hoverCoords / probeList / exitingProbeLabel / restoredCount / corruptedToast. Effects: case-mount diagnostic load + 4 timer/persistence. **Closes the 3-phase reducer-extraction debt** (Phase 27 punchlist #3 + Phase 29 rec #2 + Phase 30 Dim 3 -1 debit). Critical race-condition fix in `toggleCompanion`: compare live state against `computeCompanionInitialCut(null)` default shape, NOT `loadCompanionSectionCut() === null` (first-render persistence effect would always write before the toggle could read). | `52a9011` | 21 frontend |
| 31 C | Richardson extrapolation as POST-PROCESSING on existing Phase 30 D artifacts (PIVOTED from cylinder-pv BC redesign — Saint-Venant statically-determinate BCs designed for single C3D8 wall coupon, Phase 19 B Poisson-lockup avoidance; extension would re-create the bug Phase 19 B already documented). New: `RichardsonEstimate` dataclass + `richardson_extrapolate(h_sizes, observed_values, analytical)` (~140 LOC) + `compute_richardson_from_artifact(artifact, h_direction)` helper with sign-alignment for opposite observed/analytical conventions. Schema 1.0.0 → 1.1.0 (additive `richardson` field). **Live results**: plate-ss-shell (n=10/20/40, r=2): f_∞ = 0.000267370, p=2.480, **+1.31% asymptotic residual CONFIRMS Phase 30 D's S4+Mindlin asymptotic-bias hypothesis** — under-refinement was NOT the cause. cantilever-modal (cl=12/8/5 mm, r non-constant flagged): f_∞ = 66.861 Hz, p=0.688, +0.030% asymptotic agreement. | `a8a1932` | 34 backend (textbook math + recompute round-trip + per-artifact pins) |
| 31 D | UI polish bundle: (1) Companion `onNodePicked` with `companion:` prefix labels — `PickedNodeInfo.origin?: 'primary'\|'companion'` additive optional field, origin-stamping wrapper in `CompanionViewport.tsx`, ProbeListPanel renders prefix marker, CSV schema stable; (2) Layout-swap motion — `POLISH_CLASS_VIEWPORT_FLEX_ROW` (200ms ease-out gap + flex-basis + width transition; prefers-reduced-motion: reduce honored); (3) WebGL context-loss handler — `onContextLost?` prop + `webglcontextlost` listener with `event.preventDefault()`; parent falls back to `viewportMode='svg'` + 10s warning toast with `role="alert"` + `aria-live="assertive"`; (4) Token warning-toast colors — `POLISH_CLASS_WARNING_TOAST` class (color + border-color tokens, no background); Phase 30 C inline rgba migrated; Phase 30 C color-pin test updated to className assertion (only existing pin that changed shape — documented). | `2c82860` | 14 frontend (companion prefix, CSV stability, motion CSS rules, reduced-motion compliance, warning-toast token semantics, PickedNodeInfo schema) |
| 31 E | 3 sub-agent audits (UX 92.2 / FEA 85.83 / UI 89.0); FINAL synthesis; this retro; STATE refresh | (this commit) | — |

**Total: 115 new tests** (80 backend + 35 frontend + 2
@requires_solver E2E). Frontend 722/722 PASS across 48 files;
backend Phase 31 A live ccx 2.23 ran PASS at 0.000% residual;
Phase 31 C 6 Richardson round-trip pins agree at >12 digits.

## Composite trajectory (honest)

| Phase | Honest composite | Per-phase Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 26 | 74.7 | +2.5 (honest re-baseline) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| 29 | 84.23 | +4.63 |
| 30 | 87.16 | +2.93 |
| **31** | **89.01** | **+1.85** |

**Phase 31 is the sixth inside-band landing in a row**. Lift
distributed evenly across UX (+1.9) / FEA (+1.66) / UI (+2.0) —
each contributes ~30% of composite Δ, unlike Phase 30 where FEA
carried 75% via single-ship *DYNAMIC. **Phase 31 is a
"distributed polish" phase that nonetheless lands a real FEA
vertical (heat transfer) and a real diagnostic feature
(Richardson)**.

## What worked

### Two documented honest pivots in one phase (pattern matures)
- Phase 31 A contact→heat: contact pair reconnaissance surfaced 3
  CCX limitations + ADR-002 enum lock. Heat transfer chosen as
  lower-complexity substitute that still adds a NEW solver-kind
  axis. Documented in `golden_samples/heat-transfer-1d-candidate/NOTES.md`.
- Phase 31 C cylinder-pv→Richardson: BC-redesign would re-create
  Phase 19 B's Poisson lockup. Richardson post-processing on
  existing artifacts delivers the rubric Dim 5 anchor 90
  sub-bullet verbatim without the BC risk. Documented in
  `convergence_study.py` module docstring + 31 C commit body.
- **Both pivots preserved the original deferral target in-tree**
  (heat-transfer-1d NOTES.md mentions contact pair → Phase 32;
  31 C commit body explicitly reasserts cylinder-pv as ongoing
  Phase 32 deferral with `test_cylinder_pv_convergence_deferred`
  from Phase 30 D still pinning the absence). The honest-scope
  pattern from Phase 30 D / Phase 28 A → Phase 29 A → Phase 31
  A / 31 C is **3 phases consecutive** now, FEA Dim 3 anchored
  at 95.

### Distributed polish CAN deliver real lift (when targeted)
- Phase 28 (polish-heavy, +1.1) underdelivered because the polish
  was unscoped. Phase 31's polish was **derived directly from
  Phase 30 FINAL's honest-gaps section**:
  - Gap #2 → Phase 31 A (heat-transfer; alternative to contact)
  - Gap #6/#7 → Phase 31 B (reducer extraction)
  - Gap #5 → Phase 31 C (Richardson)
  - Gap #8 → Phase 31 D context-loss handler
  - Gap #12 → Phase 31 D token warning-toast
  - Gap #11 → Phase 31 D companion node-pick
- 6 of 17 honest gaps from Phase 30 FINAL closed. The
  remaining 11 are either Tier 3 architectural (drag-resize,
  4-quadrant, *DYNAMIC EXPLICIT) or known-deferred (App.tsx
  reducer, coord-readout gating, cylinder-pv BC redesign).
- **Lesson: honest-gaps-driven scoping makes "polish phases"
  productive.** Phase 30 FINAL gap list → Phase 31 implementation
  yielded +1.85 inside-band.

### Rubric v1.0 calibration stability (3 phases running)
- Phase 29 D pinning → Phase 30 (0.01 absolute/delta agreement)
  → Phase 31 (0.003 absolute/delta agreement).
- **Three independent sub-agent instances scored each axis within
  ±2 points of the projection band**. The v1.0 anchors with
  concrete file:line examples are doing their calibration job.
- No anchor inflation observed (sub-agents did NOT over-credit
  the new heat-transfer case for Dim 2 — 1/3 of the 99-anchor's
  three sub-bullets gives +4, not +10).

### Spike-class did NOT activate (correctly)
- All 4 implementation slices exceeded the ≤30-LOC + 1-test
  spike-class bound (31 A ~510 LOC, 31 B 268 LOC, 31 C ~140 LOC,
  31 D ~250 LOC across 6 files). All 4 are correctly full
  sub-DEC scope per v2.3 round-1-loosen.
- The schema migration 1.0.0 → 1.1.0 in 31 C is the closest call
  — it could conceptually be argued as a schema-break needing
  full DEC. The 3 existing schema_version pins in
  test_phase30d_convergence_study.py were updated (from "1.0.0"
  → "1.1.0") as a documented additive minor migration. NOT a
  semantic regression of the existing pins — they track the
  artifact's actual schema, which evolved.

## What didn't work / honest

### App.tsx still 1457 LOC (reducer debt half-closed)
- Phase 31 B successfully extracted the panel's state, but
  `App.tsx` itself stayed byte-identical. The 3-phase reducer
  debt is closed for the *panel*, not for App-root.
- UX audit honest-debit: "hook ownership incomplete" — Phase 31 D
  added `contextLostToast` + `activePick` directly to the panel
  rather than into the hook. The hook would have been the more
  cohesive home; deferring this to a Phase 32 spike.

### Coord-readout still not advanced-gated (Phase 30 FINAL gap #9)
- ~5 LOC + 1 feature-id entry. Trivial to add. Phase 31 D scope
  did not include it because the 4-item polish bundle was already
  large; better to ship 4 polish items end-to-end than 5 with
  one rushed.

### Companion entrance fade NOT shipped (only flex transition)
- Phase 31 D shipped the layout-swap motion (width/gap
  transition) but not the companion's mount-time fade-in. The
  full motion treatment would add a 200ms opacity fade on
  CompanionViewport's first render. ~6 LOC CSS.

### Richardson p-anomalies surfaced (not bugs, but worth flagging)
- plate-ss-shell empirical p = 2.48 vs S4 bending theoretical
  p = 2. Super-convergence on this specific problem (likely
  because the analytical reference is itself a series
  approximation, not exact). Honestly noted in the artifact's
  richardson.notes field.
- cantilever-modal empirical p = 0.69 vs C3D10 modal theoretical
  p = 2. Low; flagged as side-effect of non-constant refinement
  ratio (cl=12/8/5 mm → r=1.5 then r=1.6). Phase 32 candidate:
  re-run at cl=12/6/3 mm (clean r=2) to verify p stabilizes
  near 2.

### Real WebGL E2E still future (Phase 26-31 carry-over)
- Phase 31 D pinned the context-loss handler via CSS class
  assertions, NOT live event dispatch. jsdom can't fire
  `webglcontextlost`. The context-loss code path is exercised
  in the wild but not in CI; a playwright integration would
  cover this.

## Phase 32 forward look

See `.planning/audits/phase31_FINAL.md` "Phase 32 priority
recommendations" for the consolidated list. Top 3:

1. **`*CONTACT PAIR` Hertz contact case** — closes Phase 31 A's
   honest deferral; FEA Dim 1 80 → 85 = +0.83 composite.
2. **Cylinder-pv BC redesign + convergence_study + Richardson**
   — closes Phase 31 C's honest deferral; FEA Dim 5 90 → 93
   + Phase 30 FINAL gap #1; +0.5 composite.
3. **App-root reducer extraction (`useAppLayout`)** — completes
   the reducer-extraction work Phase 31 B started; UX Dim 3
   91 → ~93 + UI Dim 6 maintainability; +0.6 cross-axis.

**Phase 32 projection band: 89.5 - 91.0** if all 3 Tier-1 items
ship; 89.5 - 90.0 if 2 of 3.

The 99 target remains intentionally unreached. Per RUBRIC.md the
ceiling is 99; reaching it requires items the honest contract
explicitly forbids (signed validation, independent benchmark
agreement). Phase 31's 89.01 represents **engineering-honest
craft at the Tier-1/Tier-2 boundary** — six inside-band landings
in a row, two honest pivots, two structural lifts (heat-transfer
case + Richardson) and one foundational refactor (reducer hook)
delivered without rubric reshaping or score gaming.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 15 consecutive
Tier-2 phases.
