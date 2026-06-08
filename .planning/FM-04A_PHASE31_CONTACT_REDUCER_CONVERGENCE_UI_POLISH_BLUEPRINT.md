# FM-04a Phase 31 — *CONTACT PAIR + reducer extraction + cylinder-pv convergence + UI polish

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-30. 15 consecutive Tier-2 phases.

## Headline (honest projection)

**Phase 31 honest composite projection: 89.0-90.5/100**
(target: +1.8 to +3.3 over Phase 30's 87.16; reach for the
~95 ethical ceiling but acknowledge ~89-90 is the realistic
single-phase lift from here).

Phase 30 confirmed Phase 29 FINAL's thesis: **99/100 has a
structural ceiling at ~95** under the Tier-1-candidate honest
contract; the final 95 → 99 gap requires signed external
verification which the project forbids. Phase 31 onward each
phase should net +1.5 to +2.5 composite while we approach 95.

## Strategy

Phase 30 dominant lift was a single structural ship (`*DYNAMIC`
ballistic floor + 25 single-axis = +1.39 composite alone). Phase 31
has NO equivalent single-axis +25 lift available — the floor at 75
on FEA Dim 6 only reopens with `*DYNAMIC, EXPLICIT` (Milestone 4,
not a one-phase ship). Instead Phase 31 targets **4 parallel
medium-magnitude lifts** spanning all 3 axes:

| Slice | Primary axis lift | Magnitude | Cross-axis |
|---|---|---|---|
| A *CONTACT PAIR | FEA Dim 1 80 → 85 | +5/6 = +0.83 FEA | Dim 4 84 → 86 (cohort 10→11) |
| B Reducer extraction | UX Dim 3 88 → 91 | +3/6 = +0.5 UX | UI Dim 6 86 → 88 (maintainability) |
| C Convergence + Richardson | FEA Dim 5 86 → 89 | +3/6 = +0.5 FEA | Dim 3 95 → 96 (honest-scope) |
| D UI polish bundle | UI Dim 5 86 → 88 | +2/6 = +0.33 UI | UX Dim 4 + UI Dim 3 + Dim 4 |

Expected composite Δ ≈ (0.5 + 0 + 0 from UX cross) + (0.83 + 0.5
+ small from FEA cross) + (0.33 + small from UI cross) ≈ +2.2 to
+2.7. Lands inside the projected 89.0-90.5 band.

**Anti-gaming guard meta:** if any one slice over-delivers by
>+2 axis points beyond the rubric anchor, audit it for rubric
drift (signal of inflation, not real progress).

## Slice A — 11th validated case: first `*CONTACT PAIR` (Hertz contact)

**Why**: FEA Dim 1 element-class breadth still at 5 classes (C3D4 /
C3D8 / C3D10 / B31 / S4). Phase 29 FEA audit flagged contact-pair
as cheapest Phase 31 candidate (+5 → Dim 1 85). Closes the
Phase 27-29 "no contact validated case" carry-over. Also moves
Dim 4 from 82 (Phase 30: 10 cases) toward 88 (12+ cases anchor).

**Approach**: 2D-axisymmetric (or 3D-quarter-symmetry) Hertz contact
between a rigid spherical punch and an elastic half-space. Analytical
reference is the closed-form Hertz contact-stress formula:

```
p_0 = (1/π) * (6 F E* / R²)^(1/3)        max contact pressure
a   = (3 F R / (4 E*))^(1/3)             contact patch radius
δ   = a² / R                             indentation depth
```

where `1/E* = (1-ν₁²)/E₁ + (1-ν₂²)/E₂` for two-body, or
`E* = E/(1-ν²)` for elastic-on-rigid.

- NEW `backend/app/services/cross_check/contact_hertz.py` (~150 LOC)
  with `compute_hertz_max_pressure_pa`, `compute_hertz_contact_radius_m`,
  `compute_hertz_indentation_m` analytical functions. Pinned by 5
  unit tests against textbook values (Johnson 1985 §3.4).
- NEW `backend/app/services/cross_check/contact_hertz_runner.py`
  (~400 LOC) — hand-rolled 3D quarter-symmetry mesh of an elastic
  cube (10 mm × 10 mm × 10 mm) under a rigid spherical punch
  (R = 5 mm) applying total force F = 100 N (small-strain regime).
  `*CONTACT PAIR, INTERACTION=hertz`, `*SURFACE INTERACTION`,
  `*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD`.
- NEW `golden_samples/contact-hertz-candidate/{data/,
  cross_check_verdict.yaml, NOTES.md}`. Schema 1.3.0 adds
  `contact_pair` provenance fields.
- `_claim_tier.py` adds `contact-hertz-candidate`.
- `test_phase29d_registry_tolerance_pin.py` extended additively
  with `"contact-hertz-candidate": 15.0` (contact problems
  typically have wider residuals than displacement cross-checks
  due to mesh-resolution sensitivity at the contact zone).
- `test_phase31a_contact_hertz.py` (~25 unit + 2 @requires_solver
  E2E).

**Anti-gaming guards**:
- **A:-1**: contact patch radius measured from contact-active node
  set (`*CONTACT OUTPUT`), NOT from displacement isosurface
  (which could pad the verdict).
- **B:-1**: analytical helper SSOT-pinned via reuse test (D:-3
  pattern from Phase 26 A).
- **E:-1**: small-strain regime preserved by indentation/punch-
  radius ratio guard (δ/R ≤ 0.05).

**Risks**:
- CCX `*CONTACT PAIR` reader compatibility — Phase 29 A reconnaissance
  pattern: check `reader.py` for contact-output field codes BEFORE
  writing the runner.
- Mesh resolution at the contact patch is critical; under-resolved
  mesh produces order-of-magnitude residual errors. Honest plan:
  start with refined patch (cl ≈ a/10) and document the resolution
  sensitivity in NOTES.md.

**Commit message stem**: `FM-04a Phase 31 A: 11th validated case — first *CONTACT PAIR (Hertz axisymmetric)`

## Slice B — `useViewportLayout` reducer extraction (3-phase debt closure)

**Why**: Phase 30 audits unanimously flagged:
- UX auditor (Dim 3 -1 debit): "ResultMeshPlaybackPanel.tsx now
  1515 LOC; reducer-extraction debt unpaid across 3 phases now
  (Phase 27 punchlist #3 + Phase 29 recommendation #2)."
- UI auditor (Dim 6 cap 86): "drag-to-resize + density toggle
  would cross Dim 6 85 → 92, but state-management cleanup is
  prerequisite."

**Approach**: Custom hook collapsing the 6 viewport-related state
pieces into one reducer-style state surface, mirroring the
successful Phase 29 B `useTrustSections` extraction pattern
(App.tsx -246 LOC).

- NEW `frontend/src/state/useViewportLayout.ts` (~320 LOC):
  ```typescript
  export interface ViewportLayoutState {
    viewportMode: 'webgl' | 'svg';
    showCompanionViewport: boolean;
    companionSectionCut: SectionCutState;
    hoverCoords: HoverCoordsInfo | null;
    corruptedToast: { caseId: string; reason: string } | null;
    restoredCount: number;
  }
  export interface ViewportLayoutActions {
    setViewportMode: (mode: 'webgl' | 'svg') => void;
    toggleCompanion: (primarySectionCut: SectionCutState | null) => void;
    setCompanionSectionCut: (next: SectionCutState) => void;
    setHoverCoords: (info: HoverCoordsInfo | null) => void;
    setCorruptedToast: (next: ...) => void;
    setRestoredCount: (n: number) => void;
  }
  export function useViewportLayout(caseId: string | null):
    [ViewportLayoutState, ViewportLayoutActions];
  ```
- MODIFIED `ResultMeshPlaybackPanel.tsx`: replaces 6 separate
  `useState` calls + 4 `useEffect` (persistence + auto-dismiss
  toast) + ~80 LOC of effect logic with single `useViewportLayout`
  call. Target: -180 to -240 LOC (mirror Phase 29 B's -246 win).
- Persistence preserved verbatim (same localStorage keys);
  corruption-detection path preserved verbatim; auto-dismiss
  timing preserved verbatim.

**Anti-gaming guards**:
- **C:-1**: ALL existing behavioral pins (Phase 30 B + 30 C
  tests, 59 tests total) MUST still pass without modification.
  If a test needs to change to accommodate the hook, that's a
  silent semantic regression and must be reverted.
- **D:-1**: hook is opt-in (panel imports it explicitly). No
  cross-component leakage; the hook returns its state surface
  verbatim, not via context.
- **E:-1**: no new public API on the panel; the hook is internal.

**Files**:
- NEW `frontend/src/state/useViewportLayout.ts`
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`
- NEW `frontend/test/Phase31B_use_viewport_layout.test.tsx` (~25
  tests: hook in isolation via renderHook + integration regression
  pin via existing Phase 30 B+C tests still passing).

**Risks**:
- Persistence-effect ordering subtleties (Phase 27 D's silent
  cascade lesson). Mitigation: hook MUST replay the exact
  Phase 27 D `useEffect` chain — case-mount → loadProbeListWithDiagnostic
  → setProbeList + setRestoredCount + setCorruptedToast.
- Test pin breakage signals semantic drift, not refactor success.
  If Phase 30 B/C tests need ANY change, abort and re-plan.

**Commit message stem**: `FM-04a Phase 31 B: useViewportLayout reducer hook (-200+ LOC; 3-phase debt closure)`

## Slice C — cylinder-pv convergence + Richardson extrapolation

**Why**: Phase 30 D shipped convergence for 2 of 10 cases; Phase 30
FEA audit Dim 5 at 86 because pattern proven but not ubiquitous.
"+3 → Dim 5 89" was the cheapest path. Plus Richardson extrapolation
was honestly deferred in Phase 30 D — Phase 31 C closes it.

**Approach**:
1. Extend `cylinder_pv_runner.py` with `n_through_thickness: int =
   <default>` parameter that controls the wall-coupon mesh density.
   The current runner uses a fixed mesh; this exposes a tunable
   axis for convergence sweeps.
2. Ship `golden_samples/cylinder-pv-candidate/convergence_study.json`
   at n=4/8/16 (3 live ccx runs).
3. Add Richardson extrapolation to `convergence_study.py`:
   ```python
   def richardson_extrapolate(
       f_h: float, f_2h: float, f_4h: float, r: float = 2.0
   ) -> RichardsonResult:
       # f_∞ ≈ f_h - (f_h - f_2h) / (r^p - 1)
       # observed order p from triple: p = log_r((f_4h - f_2h)/(f_2h - f_h))
       ...
   ```
4. Update `convergence_study.json` schema to 1.1.0 with optional
   `richardson` block (only present for r=2 qualifying cases —
   plate-ss-shell n=10/20/40 ✓; cylinder-pv n=4/8/16 ✓; cantilever-
   modal cl=12/8/5 does NOT qualify cleanly at r≈1.5-1.6).
5. Re-run plate-ss-shell + cylinder-pv with Richardson added (no
   data fabrication — re-run from same inputs).
6. Phase 30 D `test_cylinder_pv_convergence_deferred` test
   **inverts** — must now FIND the artifact + the runner mesh-param
   AND the test must be **renamed** to
   `test_cylinder_pv_convergence_landed` to honor the additive-
   chain rule (deletion would erase the deferral history; rename
   preserves it).

**Anti-gaming guards**:
- **E:-1**: Richardson extrapolation only emitted when the
  observed convergence order `p` is in the textbook envelope
  [0.5, 4.0]. Outside that range, log a warning and emit
  `richardson: null` rather than a nonsense f_∞.
- **D:-3**: every convergence point produced by a live ccx run
  in this commit. Phase 30 D's plate-ss-shell + cantilever-modal
  artifacts re-generated to add the richardson field; no data
  fabrication.
- **B:-1**: contact-radius-from-pressure-distribution analytical
  vs `*CONTACT OUTPUT` — wait, this is contact slice. For
  cylinder-pv: analytical Lamé hoop-stress vs CCX σ_xx pinned
  via the existing Phase 22 A test infrastructure.

**Files**:
- MODIFIED `backend/app/services/cross_check/cylinder_pv_runner.py`
  (add `n_through_thickness` param; existing default behavior
  preserved via the default value)
- MODIFIED `backend/app/services/cross_check/convergence_study.py`
  (add `richardson_extrapolate` + `RichardsonResult` dataclass +
  schema 1.1.0)
- NEW `golden_samples/cylinder-pv-candidate/convergence_study.json`
- MODIFIED `golden_samples/plate-ss-shell-candidate/convergence_study.json`
  (regenerated with richardson field)
- MODIFIED `golden_samples/cantilever-beam-modal-candidate/convergence_study.json`
  (regenerated with richardson=null; r≠2 documented in notes)
- MODIFIED `backend/tests/test_phase30d_convergence_study.py`
  (deferral test inverted/renamed; add Richardson pin tests)
- NEW `backend/tests/test_phase31c_richardson_cylinder_pv.py`
  (~12 tests covering analytical extrapolation formula + cylinder
  artifact pin)

**Commit message stem**: `FM-04a Phase 31 C: cylinder-pv convergence study + Richardson extrapolation (3-of-10 cases)`

## Slice D — UI polish bundle

**Why**: 4 audit-flagged tier-2 polish items that didn't make
Phase 30. Each is small but cumulatively closes 3 axis caps:

1. **Companion onNodePicked wiring** — Phase 30 B audit Dim 5
   honest brake: "companion is read-only; node picks aren't
   shared." Phase 31 D wires companion picks into the SAME
   probe list with a `companion:` prefix label so the reviewer
   can disambiguate which viewport a probe came from. UI Dim 5
   86 → 88.
2. **Layout-swap motion (Compare-cuts toggle)** — Phase 30 UX
   audit Dim 4 gap. Add 200ms ease-out width transition on
   primary-viewport-slot + entrance fade-slide on companion.
   ~10-15 LOC CSS. UX Dim 4 90 → 92.
3. **WebGL context-loss handler** — Phase 30 UX audit Dim 6 gap.
   `webglcontextlost` listener on the WebGL viewport's canvas
   surfaces a toast ("WebGL context lost — refresh to recover")
   with `role="alert"`. ~30 LOC. UX Dim 6 92 → 93.
4. **Token the warning-tinted toast colors** — Phase 30 UI audit
   Dim 3 hard-brake at 85: corrupted-toast uses hard-string
   `'#fda4af'`/`'rgba(239,68,68,0.55)'` instead of the established
   `statusTone` vocabulary. Refactor to use existing `var(--danger)`
   tokens. UI Dim 3 85 → 88.

**Approach**: 4 sub-slices, each ≤60 LOC; commit as one bundle.

**Files**:
- MODIFIED `frontend/src/components/CompanionViewport.tsx`
  (add optional onNodePicked prop; forward to inner viewport)
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`
  (handle companion picks with `companion:` prefix in probe label)
- MODIFIED `frontend/src/components/polishStyles.ts` (add
  layout-swap keyframe + `webglcontextlost-toast` class +
  reduce-motion rules)
- MODIFIED `frontend/src/components/ResultMeshWebGLViewport.tsx`
  (add `webglcontextlost` listener + `onContextLost?: () => void`
  prop)
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`
  (use existing `statusTone('warning')` instead of hard-string
  rose colors for corrupted toast; render context-lost toast)
- NEW `frontend/test/Phase31D_companion_pick_motion_context_loss.test.tsx`
  (~30 tests)

**Anti-gaming guards**:
- **D:-1**: companion onNodePicked is OPTIONAL on the wrapper;
  defaults to no-op. Phase 30 B "companion is read-only" honest
  scope can still be elected by passing `null`. We change the
  default behavior; the optional surface remains.
- **B:-1**: layout-swap motion respects prefers-reduced-motion
  (inherits from established polishStyles pattern).
- **E:-1**: webglcontextlost listener doesn't fire in test env;
  trigger pin uses synthetic `dispatchEvent(new Event('webglcontextlost'))`.

**Commit message stem**: `FM-04a Phase 31 D: UI polish bundle — companion pick + layout motion + WebGL context-loss + token colors`

## Slice E — 3 testing sub-agents + FINAL + retro + STATE

**Why**: per Phase 26-30 convention.

**Approach** identical to Phase 30 E. Each sub-agent reads
`RUBRIC.md v1.0` (no bump expected — Phase 30 confirmed anchors
hold). FINAL synthesis reports composite + per-axis breakdown.

**Honest expectation**: composite 89.0-90.5. Within ~5-7 points
of the honest ~95 ceiling. APPROVE gate still expected to FAIL
by 8.5-10 points but the gap narrows further.

**Commit message stem**: `FM-04a Phase 31 E: 3 testing agents + honest composite <X>/100 + retro + STATE`

## Phase 31 hard constraints (carry-over from Phase 18-30)

- HF1.7a signed-registry hard-stop respected
- HF1.7b `*-candidate` carve-out
- HF1.8 path-guard self-protection
- tmp_path-only test snapshot writes (except case verdict YAMLs
  + convergence_study.json in golden_samples per HF1.7b)
- v2.3 round cap = 3
- DEC frontmatter 6-field minimum per slice
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观: no rubric reshaping (RUBRIC.md v1.0 untouched
  unless a Phase 31 score genuinely cannot interpolate against
  the anchors — in which case flag for v1.1 bump in retro, do
  NOT silently invent anchors)
- prefers-reduced-motion honored on all new motion (layout-swap +
  context-loss toast)
- Anti-gaming guards at predicate level
- Phase 1-30 chain additive only (Phase 30 D's
  `test_cylinder_pv_convergence_deferred` → renamed
  `test_cylinder_pv_convergence_landed` is the LIVE example of
  additive-rename pattern; do NOT delete the prior test's intent
  history)
- No push / no PR / no Linear writes unless explicitly authorized

## Phase 32 forward look (NOT this phase)

If Phase 31 lands at ~90/100:
- Composite-layup S4 case (FEA Dim 1 85 → 87 by adding anisotropic
  shell)
- `*HEAT TRANSFER` validated case (FEA Dim 2 85 → 92)
- Real WebGL E2E via playwright (UX Dim 6 + UI Dim 5 cross-axis;
  closes Phase 26-30 carry-over)
- Drag-to-resize between primary and companion + density toggle
  (UI Dim 6 85 → 92)
- Compare-cuts un-gating + basic-mode availability (UI Dim 5 88 → 89)
- Phase 30 A residual-sign hypothesis falsification spike
  (square-wave impulse to test mode-3 contamination theory)

If Phase 31 over-delivers (≥91):
- Pull `*DYNAMIC, EXPLICIT` ballistic case forward (this is the
  one remaining single-axis +15 lift available, but it's a
  Milestone 4 multi-phase build)

If Phase 31 under-delivers (≤88):
- Investigate which slice fell short; likely candidate is C
  (Richardson extrapolation may surface numerical
  pathologies — Phase 30 D revealed plate-ss-shell's non-monotone
  convergence, so the converged value may not satisfy the
  textbook envelope predicate).
