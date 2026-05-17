# FM-04a Phase 29 — Shell S4 case + Section-Frame primitive + App-root tour lift + Tier-2 quality fixes · BLUEPRINT

> Authorized by user 2026-05-18. 6 commits planned (blueprint + 5 slices).
> 绝对诚实客观 contract carried verbatim from Phase 18-28.

## Phase 28 → Phase 29 lift target (honest projection)

| Dimension | Phase 28 actual (delta method) | Phase 29 R1 projection |
|---|---|---|
| UX | 83.6/100 | 85.0-87.0 (+1.5-3.5 from App-root lift + focus-trap + corrupted-key warn) |
| FEA | 77.5/100 | 81.0-84.0 (+3.5-6.5 from 9th case unlocking Dim 1 hard cap; first time since Phase 18) |
| UI | 77.6/100 | 81.0-84.0 (+3.5-6.5 from collapsible accordion + SectionFrame primitive + uniform section visual) |
| **Composite** | **79.6/100** | **82.5-85.0 (+3-5)** |

This is the biggest projected per-phase Δ since Phase 26's recalibration
(+2.5). Driver: TWO load-bearing structural lifts (shells + reviewer-
frame primitive), not pure-polish accumulation. The 99 target stays
multi-phase; Phase 29's projected 82.5-85.0 still leaves 14-17 points
needing 3-5 more phases.

## Reconnaissance done before this blueprint

- **CalculiX reader already recognizes S4** (`backend/app/adapters/calculix/reader.py:377`); the "shell-output plumbing" Phase 27 retro flagged was a stress-tensor decomposition concern, NOT a displacement-read gap. For a cross-check that compares u_z at plate-center to analytical, the existing displacement reader is element-type-agnostic.
- **`plate_simply_supported.py` analytical helper** (Phase 23 D / 26 A) is reusable verbatim — Timoshenko α·q·a⁴/D is the same regardless of FEM element discretization. Phase 29 A reuses the helper and ships a SECOND simply-supported-plate case with S4 instead of C3D10.
- **Existing plate-ss runner** (`plate_ss_runner.py`, 530 LOC) uses gmsh + C3D10. Phase 29 A composes a hand-rolled structured 2D quad mesh (cheaper than depending on gmsh for shells; structured grid is what S4 simply-supported plate convergence studies use anyway).
- **App.tsx OnboardingTour mount site**: currently inside `ResultMeshPlaybackPanel` (Visual tab only). Phase 29 C lifts to App-root so Narrative-tab landings get onboarding too.
- **No accordion / collapsible primitive exists** in the codebase. `OperatorStatusPanel` renders all 7 trust sections expanded with no collapse affordance.

## Slice plan (5 implementation slices + audit)

### Slice A — 9th validated case · simply-supported plate with S4 shell elements

**Why**: After 10 phases of validated-case growth, **0 cases use shell
elements**. FEA Dim 1 has been hard-capped at ≤75 since Phase 18.
Shell elements are core to thin-walled structures (plates, panels,
fuselage skins) — a ballistic-FEA workbench without ANY shell
case validated is a gap that 4 prior phase blueprints have promised
to close.

**Approach**: simply-supported plate, S4 element, hand-rolled structured
quad mesh, compare center-node u_z to existing Timoshenko α·q·a⁴/D
analytical (reuse `plate_simply_supported.py` verbatim).

- **Material**: steel (same as plate-ss-candidate)
- **Geometry**: 1.0m × 1.0m × 0.020m (same as plate-ss-candidate, so
  per-case A-B comparison across element types is clean)
- **Mesh**: 20×20 = 400 S4 quad elements (structured, hand-rolled in
  the runner); 441 nodes total; 4-edge simply-supported BC (u_z = 0
  on perimeter, rotations free).
- **Load**: uniform pressure converted to nodal `*CLOAD` (consistent
  load lumping for S4 quads is straightforward — pressure × dA / 4
  per node for interior + edge-share for boundary nodes).
- **Solver**: CalculiX `*STATIC`. New runner
  `backend/app/services/cross_check/plate_ss_shell_runner.py`
  (~250 LOC; mirrors plate_ss_runner.py structure but no gmsh).
- **Verdict**: residual `(observed_w - analytical_w) / analytical_w`;
  envelope ±15% (same as C3D10 case). Shell theory bias for thin
  plate Timoshenko is typically ±3-5% which should be tight.

**Files**:
- NEW `backend/app/services/cross_check/plate_ss_shell_runner.py`
- NEW `golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml`
- NEW `golden_samples/plate-ss-shell-candidate/NOTES.md`
- MODIFIED `backend/app/services/reporting/_claim_tier.py` (registry +1)
- MODIFIED `backend/tests/test_phase28a_cantilever_buckle.py` (loosen `len==8` → `>=8`)
- NEW `backend/tests/test_phase29a_plate_ss_shell.py` (~10 unit + E2E)

**Anti-gaming guards**:
- A:-1: hand-rolled mesh node-id-vs-position pin (no off-by-one
  in BC predicate)
- E:-1: convergence pin (`20×20` mesh shows ≤7% residual; envelope
  is ±15%)
- D:-3: ctx-not-mutated pin on runner result builder

**Risks**:
- S4 quad in CalculiX uses *reduced integration* under
  full-integration setting (need to verify the INP card)
- Drilling DOF: S4 has no drilling rotation; corner constraints
  must NOT over-constrain (only u_z = 0; θ_x and θ_y are free on
  the simply-supported edges in the standard convention)

**Honest scope reduction (predicted)**:
- ONLY u_z compared; shell-stress decomposition explicitly deferred
- ONLY structured square mesh; gmsh integration deferred
- ONLY isotropic material; composite layup deferred
- 4-edge simply-supported only; clamped / 1-edge-only / mixed-BC
  cases deferred

**Commit message stem**: `FM-04a Phase 29 A: 9th validated case (S4 shell simply-supported plate) → validated count 8 → 9`

### Slice B — SectionFrame primitive + collapsible accordion + useTrustSections hook

**Why**: Phase 28 audits flagged "no collapse/expand on 7 trust
sections; industrial reviewer tools default to collapsible
accordions; uniform SectionFrame primitive absent." UI Dim 5
industrial-parity is the second-biggest single-axis lift available
(+8 to +12 sub-agent estimate).

Also: Phase 28 D's granular useMemo wrapping grew App.tsx 1454 →
1596 LOC. A `useTrustSections(ctx)` custom hook can encapsulate
the 7 useMemos into a single import, reversing some of that growth.

**Approach**:
- NEW `frontend/src/components/SectionFrame.tsx` — primitive component
  taking `{ title, icon, items, defaultCollapsed?, storageKey?, tone? }`;
  renders header with collapse chevron + body with item table; persists
  collapse state to localStorage per `storageKey`.
- NEW `frontend/src/state/useTrustSections.ts` — custom hook moving
  the 7 useMemos out of App.tsx; takes the full trust context bundle,
  returns `{ trustStrip, sections }`.
- MODIFIED `frontend/src/components/OperatorStatusPanel.tsx` — render
  sections through `SectionFrame` instead of inline; collapse state
  threaded via storage key `fm04a.trust-section.<id>.collapsed.v1`.
- MODIFIED `frontend/src/App.tsx` — replace 220+ LOC of inline useMemos
  with one `const { trustStrip, sections } = useTrustSections(ctx)`
  call. Target: net App.tsx LOC delta -100 to -150 vs Phase 28 D's
  +141 growth.
- prefers-reduced-motion: chevron rotation respects @media reduce.

**Anti-gaming guards**:
- C:-1: collapse state persists per section ID (no cross-section bleed)
- D:-1: default-expanded preserved (additive — collapsing is opt-in)
- E:-1: localStorage corruption fallback (expand all on parse fail)

**Files**:
- NEW `frontend/src/components/SectionFrame.tsx` (~120 LOC)
- NEW `frontend/src/state/useTrustSections.ts` (~150 LOC)
- MODIFIED `frontend/src/components/OperatorStatusPanel.tsx`
- MODIFIED `frontend/src/App.tsx` (target: -100 to -150 LOC)
- NEW `frontend/test/Phase29B_section_frame_collapse.test.tsx` (~25 tests)

**Risks**:
- OperatorStatusPanel may have inline styling that's hard to factor
  cleanly into SectionFrame. Honest scope reduction acceptable if
  some sections retain bespoke rendering — pinned by test.

**Commit message stem**: `FM-04a Phase 29 B: SectionFrame primitive + collapsible accordion + useTrustSections hook`

### Slice C — Tour + AdvancedModePromo lifted to App-root + focus-trap on both modals + Promo entrance animation

**Why**: Phase 28 UX audit flagged "Tour + Promo mounted inside Visual
tab; novices landing on Narrative tab miss onboarding entirely." Also
"no focus-trap on dialogs — Tab escapes. WCAG 2.4.3 gap. Industrial
software (Abaqus) traps focus." Plus the cosmetic mismatch: tour has
fade-slide entrance, Promo has none.

**Approach**:
- Lift `<OnboardingTour />` + `<AdvancedModePromo>` mounts from
  `ResultMeshPlaybackPanel.tsx` to `App.tsx` root. Thread `uiMode` +
  `setUiMode` from the (lifted) hook output back down to the panel.
- Add focus-trap to both modal overlays. Hand-rolled (small;
  ~40 LOC each) — keyDown handler intercepts Tab/Shift-Tab and cycles
  within the dialog; first-focusable focused on mount; previous
  focus restored on dismiss.
- Add `fm04a-advanced-mode-promo-fade-slide-in` keyframe to
  polishStyles.ts (200ms ease-out, -8px Y) matching tour vocabulary.
- Reduce-motion media query covers the new class.

**Anti-gaming guards**:
- B:-1: reduce-motion @media disables Promo entrance animation
- D:-2: focus-trap initial focus = first-tabbable; restore on dismiss
- E:-1: Tab keydown handler only intercepts inside dialog (no global
  side effects)

**Files**:
- MODIFIED `frontend/src/App.tsx` (add tour mounts at root)
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx` (remove tour mounts; receive uiMode from props)
- NEW `frontend/src/components/useFocusTrap.ts` — small custom hook (~60 LOC)
- MODIFIED `frontend/src/components/OnboardingTour.tsx` (apply trap)
- MODIFIED `frontend/src/components/AdvancedModePromo.tsx` (apply trap + entrance class)
- MODIFIED `frontend/src/components/polishStyles.ts` (Promo keyframes)
- NEW `frontend/test/Phase29C_tour_app_root_focus_trap.test.tsx` (~20 tests)

**Risks**:
- Lifting uiMode upward changes the ResultMeshPlaybackPanel API surface;
  several existing tests pass `caseId` + `apiBase` but not `uiMode`.
  Migration: ResultMeshPlaybackPanel keeps an INTERNAL uiMode state
  with `uiMode` prop as optional OVERRIDE (lifted parent supplies it;
  legacy tests still work). Pinned by test.

**Commit message stem**: `FM-04a Phase 29 C: tour + promo lifted to App-root + focus-trap (WCAG 2.4.3) + Promo entrance animation`

### Slice D — Tier-2 quality fixes + audit RUBRIC pin

**Why**: Three Phase 28 carry-overs are small but real polish:
1. Corrupted-key fallback is silent (Phase 27 retro punchlist).
2. Registry pins verdict only, not tolerance (Phase 28 FEA audit).
3. Sub-agent rubric drift surfaced in Phase 28 E (FEA absolute -6 vs
   actual). Fix: pin per-dimension rubric definitions in a versioned
   `.planning/audits/RUBRIC.md` that Phase 29 E auditors read first.

**Approach**:
- `probeListStorage.ts` parse-fail site adds `console.warn` with the
  case_id + reason. Test: spy on console.warn, verify call on
  malformed JSON.
- Verdict YAML schema gains `tolerance_pct` field; runners write it;
  registry test pins (case → tolerance) lookup.
- NEW `.planning/audits/RUBRIC.md` — explicit per-dimension scoring
  rubric with anchors at 60 / 70 / 80 / 90 / 99. Each axis numbered;
  each anchor includes 2-3 concrete examples. Phase 29 E sub-agents
  cited as MUST-READ in their prompts.
- Optional: third modal case at intermediate L/h=25 (Phase 26 A is
  L/h=25 already; check — if L/h=25 already exists, skip; otherwise
  L/h=20 or L/h=30 fills the Phase 26 A↔ Phase 27 A gap).

**Files**:
- MODIFIED `frontend/src/components/probeListStorage.ts` (+1-line warn)
- MODIFIED `backend/app/services/cross_check/*_runner.py` (verdict YAML schema bump for all 8 existing cases + new shell case)
- MODIFIED `backend/tests/test_phase19b_cross_check.py` (tolerance round-trip pin)
- MODIFIED `backend/tests/test_phase28a_cantilever_buckle.py` (tolerance pin)
- NEW `backend/tests/test_phase29d_registry_tolerance_pin.py` (~6 tests)
- NEW `.planning/audits/RUBRIC.md` (~200 lines)
- NEW `frontend/test/Phase29D_corrupted_key_warn.test.tsx` (~3 tests)

**Anti-gaming guards**:
- C:-1: corrupted-key warn does NOT throw — it only logs and returns initial state
- D:-1: RUBRIC.md is ADDITIVE — Phase 29 E sub-agents use it but
  Phase 28 audit scores are NOT re-scored retroactively
- E:-1: tolerance bump is BACKWARD-COMPATIBLE — existing YAMLs without `tolerance_pct` field default to the prior hard-coded value

**Commit message stem**: `FM-04a Phase 29 D: corrupted-key warn + verdict tolerance pin + audit RUBRIC.md (prevent sub-agent drift)`

### Slice E — 3 testing sub-agents + FINAL + retro + STATE

**Why**: per Phase 26-28 convention. Spawn UX/FEA/UI sub-agents in
parallel, each given the RUBRIC.md as MUST-READ, each producing a
scored audit file. Synthesize FINAL composite. Write retrospective.
Refresh STATE.md.

**Approach** identical to Phase 28 E but with two refinements:
1. Each sub-agent prompt cites `RUBRIC.md` explicitly and is asked
   to BIND its scores to the rubric anchors (not free-floating).
2. The FINAL synthesis reports composite under BOTH absolute and
   delta methods — if they converge ≤±1 point, drift has been
   contained.

**Honest expectation**: composite 82.5-85.0/100 (+3-5 over Phase 28's
79.6). 14-17 points still to 99; that's 3-5 more phases of
structural work (contact, transient, multi-viewport, App.tsx
decomposition, real WebGL E2E, more solver kinds, more BC types).

**Commit message stem**: `FM-04a Phase 29 E: 3 testing agents + honest composite <X>/100 + retro + STATE`

## Phase 29 hard constraints (carry-over from Phase 18-28)

- HF1.7a signed-registry hard-stop respected (new case enters as `*-candidate`, promoted via overlay)
- HF1.7b `*-candidate` carve-out (golden_samples/plate-ss-shell-candidate/ allowed under HF1.7b)
- HF1.8 path-guard self-protection
- tmp_path-only test snapshot writes (except verdict YAMLs in golden_samples per HF1.7b)
- v2.3 round cap = 3 (Codex review NOT triggered unless auth/signing/安全 boundary touched)
- DEC frontmatter 6-field minimum per slice
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观: no rubric reshaping for score gain; honest scope misses recorded verbatim
- prefers-reduced-motion honored on all new motion
- Anti-gaming guards at predicate level
- Phase 1-N chain additive only (test loosening must preserve original intent)
- No push / no PR / no Linear writes unless explicitly authorized

## Projected per-phase Δ trajectory check

| Phase | Composite | Δ |
|---|---|---|
| 26 (re-baseline) | 74.7 | +2.5 |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| 29 (projected) | 82.5-85.0 | +3-5 |

Phase 29's projected Δ exceeds Phase 27's +3.8 because TWO load-bearing
structural lifts ship simultaneously (shells + section-frame). If the
shell case ships clean (no envelope blow-out), the FEA Dim 1 hard cap
finally lifts above 75 for the first time since Phase 18 — that alone
is +5 to +8 FEA, or +1.7 to +2.7 composite. Section-frame adds +3 to
+4 UI, or +1.0 to +1.3 composite. App-root tour lift + focus-trap is
+1 to +2 UX, or +0.3 to +0.7 composite. Sum: +3 to +4.7 composite,
consistent with the 82.5-85.0 band.

## Phase 30 punchlist (forward look · NOT this phase)

If Phase 29 lands at ~84/100:
- Real WebGL E2E via playwright (FEA Dim 7 evidence)
- `*DYNAMIC explicit` validated case (FIRST ballistic in cohort)
- `*HEAT TRANSFER` validated case (thermal coupling)
- Contact case (`*CONTACT PAIR`) — paired-surface validation
- Multi-viewport split + measurement/coord tools (UI Dim 5)
- Iso-surface rendering (Phase 26 retro carry-over)
- App.tsx reducer/candidate-spine extraction
- Composite-layup S4 case (anisotropic shell)
- 3rd modal case at intermediate L/h (if not in Phase 29 D)

That's ~9 more phases of work to reach 99, OR 3-4 phases of
"bundle 3-4 slices each" to reach 95+, with 95 → 99 likely needing
specialized work (signed validation? benchmark agreement? — both
disallowed by the 绝对诚实客观 contract, so 99 may have a structural
ceiling honest to acknowledge).

Honest note: **99/100 may not be achievable WITHOUT crossing the
"signed validation / benchmark agreement" line that the project
explicitly forbids**. Phase 28 retro acknowledged this. The honest
ceiling under Tier-1-candidate constraint may be ~92-95, with 95 →
99 requiring a category change (signed external review by a CAE
licensee, NIST benchmark agreement, etc.). Phase 29 will note this
in the FINAL if the math becomes clear.
