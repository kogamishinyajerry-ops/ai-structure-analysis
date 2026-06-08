# FM-04a Phase 28 — UX Audit

> Honest scoring per绝对诚实客观 contract carried from Phase 18-27.
> Tier 1 / Tier 2 engineering candidate; not signed validation;
> not benchmark agreement.

## Provenance baseline
- Phase 27 honest composite = 78.5/100 (per
  `fm04a_phase27_7th_case_loc_polish_persist.md` §Composite trajectory).
- Phase 27 UX dimension is not split out as a stand-alone number in
  that retro; brief states Phase 27 UX ≈ 80 (estimated from composite
  + UI 78 split). Per scoring rule, treat 80 as the Phase 27 UX anchor.
- Phase 28 punchlist closures: #2 (28 B), #4 + #5 (28 C), #6 + #9 (28 D).
  Punchlist gaps still open: #1 shell, #3 reducer extraction, #7 real
  WebGL E2E, #8 third modal case, #10 iso-surface.

## Dimensions

### 1. Onboarding flow quality: **84/100**

**Evidence (lift):**
- `frontend/src/onboardingTour.ts:215-275` adds
  `ADVANCED_PROMPT_LS_KEY` + `shouldShowAdvancedPrompt` predicate
  (pure, truth-table tested in `Phase28D_advanced_promo_trust_memo.test.tsx`).
- `frontend/src/components/OnboardingTour.tsx:60-82` fires
  `onDismissed?.()` exactly once on both Skip and final-Done paths —
  closes Phase 27 punchlist #6 (tour auto-promote sequencing).
- `frontend/src/components/AdvancedModePromo.tsx:58-150` surfaces
  one-shot promo when (tour-dismissed) ∧ (uiMode='basic') ∧
  (¬prompt-shown). D:-1 anti-gaming pinned by two re-mount tests.
- `ResultMeshPlaybackPanel.tsx:284-289` wires both into the Visual
  tab with `tourDismissedInSession` in-session signal for no-reload
  surfacing.

**Gap (caps lift):**
- Tour + Promo are mounted *inside* `ResultMeshPlaybackPanel`
  (Visual-tab tree, App.tsx:1518-1521). A novice who lands on
  Narrative tab first never sees the tour. Tab-default *is* Visual
  (App.tsx:173), so the common path works — but a user who navigates
  away and returns will still encounter the tour. Not regression;
  a structural Phase 29 candidate (Lift tour mount to App-root).
- Modal-on-modal sequencing risk: tour ends → Promo appears.
  `AdvancedModePromo.tsx` z-index 999 vs Tour 1000 → both can briefly
  co-exist during the dismiss-transition frame (mitigated by
  `setPersistedDismissed(true)` before `onDismissed?.()`, which makes
  the tour return null first, but is single-frame fragile).
- AdvancedModePromo has **zero entrance animation** (no `animation`
  key in `AdvancedModePromo.tsx:153-223 STYLES`) vs Tour fade-slide
  (200ms) + restored-toast fade-in (200ms). Polish inconsistency.

### 2. State preservation + recovery: **86/100**

**Evidence (lift):**
- Probe persistence by case_id from Phase 27 D
  (`probeListStorage.ts:38-39`,
  `loadProbeList()` corrupted-key fallback to
  `PROBE_LIST_INITIAL_STATE` lines 45-60).
- 28 C surfaces persistence via
  `ResultMeshPlaybackPanel.tsx:145-149,168-183,293-313`:
  initial-mount `restoredCount` populates from `loadProbeList`,
  4s auto-fade timer at line 181, dismiss button at line 304-311,
  `role="status" aria-live="polite"` at line 297-298 (accessible).
- The case-switch effect (lines 168-177) re-sets the toast when the
  user switches cases — a brand-new persistence-aware case-mount
  flow that surfaces what was silent in Phase 27 D.

**Gap:**
- Corrupted-key fallback (Phase 27 retro §What didn't work item 3)
  is **still silent**. `probeListStorage.ts:57-58` returns initial
  state with no `console.warn`. Brief Phase 28 deliveries do not
  address this. Caps Dim 2.
- `restoredCount` is computed twice on initial mount
  (`useState` initializer at line 145-149 + `useEffect` at line
  168-177); minor over-evaluation, no correctness issue.

### 3. Cognitive-load mitigation: **82/100**

**Evidence (lift):**
- Basic-mode default (Phase 25 C) + auto-promote sequencing (28 D)
  closes the "tour explains Advanced features but user stays in
  Basic and never sees them" gap named in Phase 27 retro §miss #5.
- One-shot promo: `ADVANCED_PROMPT_LS_KEY` ensures the prompt
  never re-surfaces; either button writes the flag (`AdvancedModePromo.tsx:94-106`).

**Gap (real):**
- The chain is **modal → modal**: tour (max 6 cards) → Promo (1
  card). For a brand-new reviewer in Basic mode, this is up to 7
  consecutive overlay dismissals before the viewport is usable.
  Phase 27 retro's "no new layer of modal interruption" warning
  is *partially* violated; mitigated by both being one-shot
  per-browser and short.
- Trust-strip memoization (28 D) is pure perf, no UX-visible
  change — does not lift cognitive load.
- App.tsx is **1596 LOC** (verified `wc -l`), UP from Phase 27's
  1454. The 28 D useMemo wrapping added +142 LOC of inline
  `useMemo(() => buildX(...), [...deps])` blocks. Phase 27
  punchlist #3 (reducer extraction) is *worse* than at Phase 27
  close. Doesn't touch UX directly, but the cognitive-load story
  is partially "make Basic hide things" — file complexity for
  maintainers, not reviewers — so this caps the dimension only
  modestly.

### 4. Motion / micro-interactions: **86/100**

**Evidence (lift):**
- 28 C row EXIT animation: `polishStyles.ts:65-68,78-80` defines
  `fm04a-probe-row-fade-out` 150ms; consumed in
  `ProbeListPanel.tsx:193,200` via `isExiting` flag;
  `ResultMeshPlaybackPanel.tsx:635-641` sequences `setExitingProbeLabel`
  → 150ms timeout → `removeProbeEntry`. Closes Phase 27 punchlist
  #4 cleanly.
- 28 C restored-toast fade-in: `polishStyles.ts:69-72,82-98`
  defines `fm04a-restored-toast-fade-in` 200ms; consumed at
  `ResultMeshPlaybackPanel.tsx:296`.
- Reduced-motion: `polishStyles.ts:145-151` covers row-mount, row-
  unmount, AND restored-toast — all three new affordances honor
  `prefers-reduced-motion: reduce`.
- Tour fade-slide still covered (`OnboardingTour.tsx:148-161`).

**Gap:**
- `AdvancedModePromo.tsx` ships with **no entrance animation**
  whatsoever. Not a reduced-motion violation (no motion to
  reduce), but it is an *inconsistency* with the rest of the
  Phase 24+25+27+28 polish vocabulary. Caps Dim 4 +4 vs an
  otherwise-clean +6 lift.

### 5. Error recovery / honesty surfacing: **80/100**

**Evidence (no change from Phase 27):**
- `App.tsx:581-617` carries the full "Tier 0 sandbox / Tier 1
  candidate / not signed validation / not benchmark agreement"
  copy verbatim per the 绝对诚实客观 contract. ComplianceBadge mount
  at line 1429 surfaces the report metrics status. Claim-tier copy
  unchanged across Phase 28.
- Probe-list `loadProbeList` returns initial state on any failure
  (`probeListStorage.ts:45-60`) — safe recovery; corrupted state
  cannot leak into the UI.

**Gap (unchanged from Phase 27):**
- Persistence corrupted-key fallback is silent (item already named
  in Phase 27 retro §What didn't work #3). No `console.warn`, no
  toast surfacing "we discarded malformed pinned-probe state."
- Phase 28 ships *no new* honesty-surfacing affordance. Dimension
  scored equal to Phase 27 per the scoring contract.

### 6. Novice-user gotchas: **78/100**

**Evidence:**
- Default Visual tab + activeCaseId-gated tour means novice who
  picks a case sees the tour (good).
- Tour first step is `field-component-switcher`
  (`onboardingTour.ts:43-48`) — this is correct ordering: the
  Mises/σxx switcher is the most-used and most-explanatory entry.
- Restored-toast appears on case-mount only when count ≥ 1
  (`ResultMeshPlaybackPanel.tsx:172,293`), so novices with no
  prior session see no spurious toast.
- Auto-promote prompt's copy at `AdvancedModePromo.tsx:123-129`
  explicitly names the four affordances the user will get
  ("threshold filter, section cut, field-component switcher, and
  probe list") — concrete benefit-framed CTA.

**Gap (real):**
- Modal-on-modal stacking risk (Dim 1 gap repeated here from the
  novice angle): if a brand-new reviewer in Basic mode dismisses
  the tour quickly, the immediate Promo is borderline
  modal-fatigue. The "Stay in Basic" button is necessary but
  encourages a fast-click-dismiss-everything pattern that defeats
  the educational purpose.
- App.tsx LOC growth (1596) is a *reviewer maintenance* gotcha,
  not a novice gotcha — does not bound this dimension directly,
  but reviewer onboarding pain is tangential.
- 28 A's 8th validated case is FEA-only; no UX surfacing for the
  new buckling case in the Visual tab or tour (the tour copy is
  feature-driven, not case-driven; fine).
- Probe-list silent fallback (per Dim 5) is also a novice gotcha:
  a user whose state was discarded after a schema bump sees no
  feedback.

## Composite UX score: **82.7/100**

  (84 + 86 + 82 + 86 + 80 + 78) / 6 = 496/6 = **82.67**

## Phase-28 lift over Phase 27 UX baseline (~80): **+2.7**

- Lift drivers:
  - Onboarding flow +4 (28 D auto-promote closes punchlist #6).
  - State preservation +6 (28 C restored toast closes punchlist
    #5; the persistence was already shipped in 27 D but Phase 27
    explicitly noted it was silent).
  - Motion +6 (28 C row exit closes punchlist #4 + restored-toast
    fade adds depth).
- Drag drivers:
  - Cognitive-load +2 only (28 D promo helps but adds a modal
    layer; trust-strip memo is invisible perf).
  - Error/honesty +0 (no new affordance).
  - Novice gotchas -2 (modal-on-modal pattern is a real concern
    even though both modals are one-shot).
- Lift is in the brief's "+2 to +6" expected band. Score caps
  applied per contract — no dimension above 88, none below 75.
- Composite **82.7 < 88 cap**, defensible with file:line evidence;
  no inflation.

## Phase 29 recommendations (top 3)

1. **Lift tour + AdvancedModePromo out of `ResultMeshPlaybackPanel`
   to App-root.** Both mounts at `ResultMeshPlaybackPanel.tsx:284-289`
   are coupled to Visual tab + active case_id. A novice who lands
   on Narrative tab first misses onboarding entirely. Move the
   mounts to `App.tsx` between TopBar and tab-switch render
   (around line ~1455). Fix the modal-on-modal stacking by
   adding a 250ms gate between tour-dismissed-in-session and
   Promo visibility (so the tour exit animation completes first).

2. **Surface silent fallbacks via toast.** `probeListStorage.ts:57-58`
   should emit a `console.warn` + (optionally) a `restoredCount=0`
   toast variant like "Stored pinned-probe state was malformed and
   was reset" when the try/catch fires. Closes Phase 27 retro §What
   didn't work #3 AND lifts Dim 5 by 3-5 points. Cheap. Same
   pattern can apply to `createLocalStorageBackedStore` for
   onboarding / Advanced-prompt storage.

3. **Polish parity for AdvancedModePromo.** Add a 200ms fade-slide-
   in animation (mirror `ONBOARDING_TOUR_KEYFRAMES` at
   `OnboardingTour.tsx:148-161`) with the same
   `prefers-reduced-motion: reduce` opt-out. Tiny (~20 lines), but
   closes the only inconsistency in the Phase 27 C / 28 C motion
   vocabulary and lifts Dim 4 toward the +6 ceiling.

Not signed validation; not benchmark agreement.
