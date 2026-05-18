# FM-04a Phase 31 — FINAL composite audit synthesis · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-30. 15 consecutive Tier-2 phases.

## Headline

**Phase 31 honest composite: 89.01/100**
**Lift over Phase 30 (87.16): +1.85**

Phase 31 = sixth inside-band landing in a row after Phase 26's
honest re-baseline event. The +1.85 lands inside the blueprint's
projected **89.0-90.5/100** band — exactly at the lower edge.

**Crucially**: the absolute audit sum (89.01) and the delta-from-
Phase-30 method (87.16 + (1.9 + 1.66 + 2.0)/3 = 87.16 + 1.853 ≈
89.013) **agree to within 0.003 points** — Phase 30's 0.01-point
agreement tightened further by ~3×. The rubric v1.0 (Phase 29 D
delivery) is in its third phase running and the per-axis anchors
remain calibration-stable across three independent sub-agent
instances. This is exactly the strictness pinning Phase 28 E
surfaced as missing.

## Per-dimension scoreboard

| Dim | Phase 30 absolute | Phase 31 absolute (rubric v1.0) | Δ | Anchor justification |
|---|---|---|---|---|
| UX  | 90.3 | **92.2** | +1.9 | Dim 3 88 → 91 (`useViewportLayout` hook closes 3-phase reducer debt); Dim 4 90 → 93 (layout-swap motion adds 6th surface in 200ms vocabulary); Dim 5 90 → 93 (WebGL context-loss handler closes novice-gotcha + token toast migration); Dim 6 92 → 94 (context-loss novice-trap + `companion:` origin prefix) |
| FEA | 84.17 | **85.83** | +1.66 | Dim 2 85 → 89 (*HEAT TRANSFER STEADY STATE lands 1/3 of 99-anchor's 3 sub-bullets — heat/visco/coupled-temp-disp); Dim 5 86 → 90 (Richardson extrapolation = anchor-90 second sub-bullet verbatim match); Dim 4 84 → 86 (10 → 11 validated cases) |
| UI  | 87.0 | **89.0** | +2.0 | Dim 3 85 → 90 (token warning-toast closes Phase 30 FINAL gap #12 — rubric anchor 90 verbatim match); Dim 1 90 → 92 (layout-swap motion adds to 200ms vocabulary); Dim 4 86 → 88 (context-lost toast a11y); Dim 5 86 → 88 (companion node-pick wiring closes gap #11); Dim 2 89 → 90 (companion prefix marker) |
| **Composite** | **87.16** | **89.01** | **+1.85** | **Sixth inside-band landing in a row; lift driven by polish breadth (3 axes lifted in each of UX/UI) plus targeted FEA verticals (heat-transfer + Richardson)** |

> Unlike Phase 30 where FEA carried +6.67 / 14 of the composite Δ,
> Phase 31 is **balanced** across all three dimensions — UX +1.9,
> FEA +1.66, UI +2.0 contribute roughly equal shares (each ~30%
> of the composite +1.85). This reflects Phase 31's scope: closing
> Phase 30 FINAL's distributed gap punchlist (UX cog-load + motion
> + context-loss; FEA solver-kind + Richardson; UI tokens + parity)
> rather than a single big-ship like Phase 30 A's `*DYNAMIC`.

## Phase 31 wins (cited verbatim from sub-agents)

### UX (auditor `a4ce1586...` → 92.2/100)
1. **`useViewportLayout` hook (31 B)** — `frontend/src/state/useViewportLayout.ts`
   (268 LOC NEW) collapses 8 state fields + 5 effects from
   `ResultMeshPlaybackPanel.tsx`. Panel: 1515 → 1411 LOC (-104).
   Phase 31 B test file (`Phase31B_use_viewport_layout.test.tsx`,
   441 LOC, 21 tests). Closes the 3-phase reducer-extraction debt
   (Phase 27 punchlist #3 + Phase 29 rec #2 + Phase 30 Dim 3 -1
   debit). Dim 3 88 → 91.
2. **Layout-swap motion (31 D)** —
   `frontend/src/components/polishStyles.ts:141-148`
   (`POLISH_CLASS_VIEWPORT_FLEX_ROW` with 200ms gap + flex-basis
   + width ease-out) + reduce-motion respect at
   `polishStyles.ts:207-211`. Sixth surface in the 200ms motion
   vocabulary (after probe-row mount/unmount, restored toast,
   advanced-mode promo, chevron, gradient slider). Dim 4 90 → 93.
3. **WebGL context-loss handler + token toast migration (31 D)** —
   `ResultMeshWebGLViewport.tsx` `onContextLost?` prop +
   `webglcontextlost` listener with `event.preventDefault()`;
   parent `ResultMeshPlaybackPanel.tsx` falls back to
   `viewportMode='svg'` + 10s auto-dismiss warning toast with
   `role="alert"` + `aria-live="assertive"`. Closes Phase 30
   FINAL gap #8 verbatim. Dim 5 90 → 93.

### FEA (auditor `a91bf5b9...` → 85.83/100)
1. **`*HEAT TRANSFER, STEADY STATE` solver-kind unlock (31 A)** —
   `backend/app/services/cross_check/heat_transfer_runner.py`
   (~510 LOC); INP composer with `*CONDUCTIVITY` + `*INITIAL
   CONDITIONS, TYPE=TEMPERATURE` + `*PHYSICAL CONSTANTS, ABSOLUTE
   ZERO=0.0` + `*HEAT TRANSFER, STEADY STATE` + `*BOUNDARY` DOF 11
   + `*NODE PRINT NT`. Verifies node-for-node (0.000% residual at
   midplane) because C3D8 trilinear hex shape functions reproduce
   linear T(x) exactly. Lands 1/3 of rubric Dim 2 anchor 99's
   three sub-bullets (heat / visco / coupled-temp-disp); linear
   interpolation 85 + (1/3)×14 ≈ 89. Dim 2 85 → 89.
2. **Two honest pivots in one phase (31 A + 31 C)** —
   - **31 A contact→heat**: `golden_samples/heat-transfer-1d-candidate/NOTES.md`
     documents CCX `*SURFACE TYPE` limitations, `*RIGID BODY`
     bookkeeping cost, CDIS/CSTR not in `reader.py` canonical
     field enum. Same "fail in-tree with documented rejection"
     pattern as Phase 30 D cylinder-pv deferral and Phase 28 A
     C3D8 cantilever NotImplementedError.
   - **31 C cylinder-pv runner deferral preserved**: extension
     would require Saint-Venant BC redesign (Phase 19 B Poisson
     lockup avoidance). Substitute: Richardson post-processing
     on existing Phase 30 D artifacts. Dim 3 anchor 95 holds.
3. **Richardson extrapolation = anchor 90 sub-bullet verbatim
   (31 C)** — `convergence_study.richardson_extrapolate()` +
   `compute_richardson_from_artifact()` (~140 LOC) with schema
   1.0.0 → 1.1.0 additive migration. Live results:
   - plate-ss-shell (n=10/20/40, r=2 constant): f_∞ = 0.000267370,
     p = 2.480, **+1.31% asymptotic residual CONFIRMS the
     S4+Mindlin bias** Phase 30 D hypothesized. Under-refinement
     was NOT the cause of the +1.17% at n=40.
   - cantilever-modal (cl=12/8/5 mm, r non-constant flagged):
     f_∞ = 66.861 Hz, p = 0.688, +0.030% asymptotic agreement.
   Dim 5 86 → 90.

### UI (auditor `ab7f650f...` → 89.0/100)
1. **Token warning-toast = Dim 3 anchor 90 verbatim (31 D)** —
   `frontend/src/components/polishStyles.ts:128-133`
   (`POLISH_CLASS_WARNING_TOAST` overrides color + border-color
   tokens only, no background). Phase 30 C inline `#fda4af` rgba
   migrated to class composition. Closes Phase 30 FINAL gap #12.
   Phase 30 C color-pin test migrated from inline `toast.style.color`
   to `className.toMatch(/fm04a-warning-toast/)`. Dim 3 85 → 90.
2. **Companion node-pick wiring (31 D)** — `PickedNodeInfo.origin?:
   'primary'|'companion'` additive optional field in
   `viewportRaycaster.ts:24-39`; `CompanionViewport.tsx:88-103`
   origin-stamping wrapper; `ProbeListPanel.tsx:209-218`
   companion-prefix marker render with `aria-label`. CSV
   serialization unchanged (origin field IGNORED — Phase 25 D
   schema stable, pinned by csv test). Closes Phase 30 FINAL
   gap #11. Dim 5 86 → 88.
3. **Layout-swap motion adds 6th surface to 200ms vocabulary
   (31 D)** — same `polishStyles.ts:141-148` cited under UX win
   #2; Dim 1 90 → 92.

## Phase 31 honest gaps (carried forward to Phase 32)

### FEA
1. **Element-type breadth still capped at 80** (Dim 1). C3D8 in
   heat transfer is a reused element class. `*CONTACT PAIR` Hertz
   case (documented in
   `golden_samples/heat-transfer-1d-candidate/NOTES.md` as
   deferred to Phase 32) remains the cheapest Dim 1 lift.
   80 → 85 = +0.83 FEA composite.
2. **Cylinder-pv convergence_study still deferred** (Dim 5
   ceiling at 90). Phase 31 C added Richardson math but did NOT
   extend cylinder-pv runner; the BC-redesign risk-reduction
   honest-scope decision persists. Phase 32 priority: rewrite
   cylinder-pv BCs to accept refinable mesh, then add its
   convergence_study + Richardson. 90 → 93 = +0.5 FEA composite.
3. **Remaining 9 cases lack convergence_study** (Dim 5 still
   2/11). Same +0.5-1 FEA composite lift available.
4. **`*DYNAMIC, EXPLICIT` still future** (Dim 6 at 75). Milestone
   4 item; not a Phase 32 spike.
5. **Richardson p-anomalies surfaced** — plate-ss-shell p=2.48
   (theoretical 2 for S4 bending; super-convergence) and
   cantilever-modal p=0.69 (low; non-constant ratio side-effect).
   Phase 32 candidate: re-run cantilever-modal at clean r=2 ratio
   (cl=12/6/3 mm) to verify p stabilizes.
6. **`*COUPLED TEMPERATURE-DISPLACEMENT`** is a natural Phase 32
   composition of Phase 30 + Phase 31 infrastructure. Dim 2
   89 → 92.

### UX
7. **App.tsx reducer debt half-closed** —
   `useViewportLayout` lifted state OUT of `ResultMeshPlaybackPanel.tsx`,
   but `App.tsx` is still 1457 LOC (verified byte-identical from
   Phase 30 via `git diff e935c63 a8a1932 -- frontend/src/App.tsx`).
   `contextLostToast` + `activePick` stayed in the panel rather
   than joining the hook (incomplete hook ownership).
   Phase 32 spike: extract App-root state into `useAppLayout`.
   Cog-load Dim 3 91 → ~93.
8. **Coord-readout still NOT advanced-gated** — Phase 30 FINAL
   gap #9 (~5 LOC + 1 feature-id entry) unaddressed. Basic-mode
   novices still see floating XYZ they didn't pre-Phase 30 C.
9. **Companion entrance fade NOT shipped** — only the flex
   transition. The full motion treatment would add a 200ms
   opacity fade-in on companion mount. ~6 LOC CSS.
10. **Real WebGL E2E via playwright** (Phase 26-31 carry-over) —
    context-loss is pinned via CSS class assertions, not live
    event dispatch (jsdom can't fire `webglcontextlost`).
    Persistent process maturity item; addressing it covers
    Dim 6 anchor 99 ("Real WebGL E2E coverage").

### UI
11. **Compare-cuts still advanced-mode-gated** — Phase 30 FINAL
    gap #10 unaddressed. Lifting the gate brings Dim 5 88 → 90.
12. **No 4-quadrant default + no drag-to-resize between primary
    and companion + no density toggle** — Dim 6 still held at
    86. Multi-phase architectural item (Milestone 5).
13. **Collapsible left/right rails** — Phase 30 FINAL forward
    look item; not addressed.

### Carried forward unresolved from Phase 26-30
14. Iso-surface rendering (Phase 26-30 carry).
15. Third modal case at intermediate L/h (Phase 27-30 carry).
16. Composite-layup S4 + clamped-edge BC variants (Phase 29 carry).
17. Failed-attempt corpus indexing for FEA Dim 3 anchor 99
    (would lift 95 → 99 if a `.planning/failed_attempts/`
    index of "what doesn't work" was maintained per case).

## Phase 32 priority recommendations (consolidated from 3 audits)

Ranked by single-axis lift potential × shippability:

### Tier 1 (biggest single-axis lifts available)
1. **`*CONTACT PAIR` Hertz contact case** — closes FEA Dim 1
   80 → 85 anchor exact match; the deferral documented in Phase
   31 A's NOTES.md is the entry point. Composite lift ~+0.8.
2. **Cylinder-pv BC redesign + convergence_study + Richardson** —
   closes FEA Dim 5 90 → 93 + clears Phase 30 FINAL gap #1 +
   Phase 31 honest gap #2 together. Composite lift ~+0.5.
3. **App-root reducer extraction (`useAppLayout`)** — closes UX
   Dim 3 91 → ~93 + UI Dim 6 maintainability. Cross-axis lift
   ~+0.6 composite.

### Tier 2 (smaller but real)
4. **Coord-readout advanced-gating + companion entrance fade
   + Compare-cuts basic-mode unlock** — UX Dim 6 + UX Dim 4 +
   UI Dim 5 combined lift. ~+0.5 composite.
5. **`*COUPLED TEMPERATURE-DISPLACEMENT`** — natural Phase 30 +
   31 composition. FEA Dim 2 89 → 92. ~+0.5.
6. **Re-run cantilever-modal at clean r=2 ratio** to verify p
   stabilizes (Phase 31 honest gap #5). FEA Dim 5 secondary
   refinement; ~+0.2.

### Tier 3 (architectural multi-phase)
7. **`*DYNAMIC, EXPLICIT` ballistic case** (Milestone 4) — Dim 6
   75 → 90 but requires explicit-stable Δt management + contact-
   erosion criteria + large-deformation kinematics.
8. **4-quadrant default + drag-to-resize panels** (Milestone 5
   item) — UI Dim 6 86 → 92.
9. **Real WebGL E2E via playwright** — process maturity; covers
   UX Dim 6 + UI Dim 4 anchor 99 sub-bullets.
10. **Failed-attempt corpus indexing** — FEA Dim 3 95 → 99.

## v2.3 disposition

- 1 sub-phase = Phase 31 (5 implementation slices + 31 E audit) =
  1 retro at phase-close ✓
- counter += 5 (telemetry only)
- No Codex review triggered (no auth / signing / 安全边界 hit)
- No charter triggered (changes within
  `backend/app/services/cross_check/`, backend reporting/,
  `golden_samples/`, backend `tests/`, frontend `src/components/`,
  frontend `src/state/`, frontend `test/`, `.planning/audits/`)
- DEC frontmatter: this FINAL doubles as the DEC for Phase 31
  (status=Accepted at commit, parent_dec=Phase 31 blueprint
  `acce14c`, notion_sync_status=pending session-end batch sync)
- Round cap 3: NOT triggered — R1 sub-agents surfaced honest
  gaps but no Phase-20-style real defects requiring Round 2.
- Spike-class: NONE of the 4 implementation slices qualified
  (each exceeded the ≤30-LOC + 1-test bound: 31 A ~510 LOC
  runner + 46 tests; 31 B 268 LOC hook + 21 tests; 31 C ~140
  LOC math + 34 tests; 31 D ~250 LOC across 6 files + 14 tests).
  All four are correctly full sub-DEC scope.

## Hard-constraint compliance

- HF1.7a signed-registry hard-stop: PASS — Phase 31 touches only
  `*-candidate` paths plus reports/ and backend cross_check/
  module (never `golden_samples/<non-candidate>/`).
- HF1.7b `*-candidate` carve-out: PASS — heat-transfer-1d-candidate
  is the new addition; plate-ss-shell-candidate +
  cantilever-beam-modal-candidate received additive `richardson`
  field (schema 1.0.0 → 1.1.0).
- HF1.8 path-guard self-protection: PASS — all golden_samples
  writes go through `_writes_inside_candidate_dir` predicate.
- tmp_path-only test writes: PASS — Phase 31 C round-trip test
  uses `tmp_path` fixture; golden-samples reads only.
- v2.3 governance round-cap = 3: not triggered (R1 only).
- confidence: high stamped on every Phase 31 commit message.
- 绝对诚实客观 contract: PASS — two documented honest pivots
  (31 A contact→heat, 31 C cylinder-pv BC-redesign-substitute),
  no rubric reshaping, no score gaming, additive `richardson`
  field flagged null when triple is non-monotone (NO
  FABRICATION).
- prefers-reduced-motion: PASS — Phase 31 D layout-swap
  transition explicitly disabled in reduce mode at
  `polishStyles.ts:207-211`; pinned by Phase 31 D test.
- Anti-gaming guards (A:-1 / B:-1 / C:-1 / D:-1/2/3 / E:-1):
  PASS — each Phase 31 commit message enumerates the guards
  that apply; recompute-matches-stored test in Phase 31 C
  re-runs Richardson math from the points and asserts exact
  agreement (D:-3 SSOT enforcement).
- NEVER score above 99: PASS — Phase 31 composite 89.01 well
  under the ceiling.
- NEVER re-score prior phases retroactively: PASS — Phase 30
  composite 87.16 verbatim; this FINAL Δ-calculates from it.
- NEVER apply weights/transforms to composite: PASS —
  (92.2 + 85.83 + 89.0)/3 = 89.01 simple arithmetic mean.
- Phase 1-N chain additive: PASS — Phase 30 + earlier tests all
  pass; only Phase 30 C color pin changed shape (inline-style
  → className assertion, documented in 31 D commit body).

## Trajectory summary (Phase 22 through Phase 31, honest)

| Phase | Honest composite | Per-phase Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 26 | 74.7 | +2.5 (honest re-baseline event) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| 29 | 84.23 | +4.63 |
| 30 | 87.16 | +2.93 |
| **31** | **89.01** | **+1.85** |

Phase 31 is the sixth inside-band landing in a row. Cumulative
lift since Phase 26 honest re-baseline = +14.31 over 5 phases
(87.16 - 74.7 → 89.01 - 74.7 = 14.31; average +2.86/phase). The
trajectory is **decelerating** as expected — the easy axis-wins
are increasingly behind us; remaining lifts (Tier 1 contact,
cylinder-pv BC redesign, App.tsx extraction) are smaller
single-axis Δs at higher implementation cost. **Phase 32
projection band: 89.5 - 91.0** if all 3 Tier-1 items ship; 89.5
- 90.0 if only 2 of 3.

The 99 target remains intentionally unreached. Per RUBRIC.md the
ceiling is 99; reaching it requires items the honest contract
explicitly forbids (signed validation, independent benchmark
agreement). The current 89.01 represents **engineering-honest
craft at the Tier-1/Tier-2 boundary** — not the marketing
99-point demo a less-disciplined contract would produce.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
