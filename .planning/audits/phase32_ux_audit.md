# FM-04a Phase 32 — UX Audit · rubric v1.0

> Honest scoring per 绝对诚实客观 contract carried from Phase 18-31.
> Rubric: `.planning/audits/RUBRIC.md` v1.0 (Phase 29 D pinning).
> Tier 1 / Tier 2 engineering candidate; not signed validation;
> not benchmark agreement.

## Provenance baseline

- Phase 31 UX composite = **92.2/100** under v1.0 anchors
  (`phase31_ux_audit.md:239-241`): 90 / 92 / 91 / 93 / 93 / 94.
- Phase 32 UX-relevant deliveries (2 of 3 implementation commits
  touch UX surface; the third is FEA-only Richardson extension):
  - `682e8f6` Phase 32 B: `useAppUiMode.ts` (110 LOC NEW) + 167-LOC
    test file. **Honest:** `App.tsx` 1457 → 1457 (NET ZERO; 17+/17-
    swap). Smallest cohesive cluster extracted; ~36 state surfaces
    remain in App.tsx. Partial closure of Phase 31 UX honest gap #7.
  - `ee11aca` Phase 32 C: Tier-2 polish bundle — C1 coord-readout
    advanced-gating (Phase 31 gap #2 closed), C2 companion entrance
    fade (Phase 31 gap #3 closed), C3 Compare-cuts basic-mode
    unlock (Phase 30 FINAL gap #10 closed), C4 Richardson r=2
    spike (FEA-only).
- `App.tsx` = **1457 LOC** (verified `wc -l`; unchanged from
  Phase 30+31). Hook lifted state OUT but the LOC delta was a
  17/17 swap.
- `useAppUiMode.ts` = **110 LOC** (verified `wc -l`).
- D:-1 additive guard: Phase 31 retains 92.2 verbatim.

## Sub-axes

### 1. Onboarding flow quality: **90/100**

- **Anchor match:** 90 anchor = "App-root tour mount; focus-trap;
  reduce-motion; corrupted-key warnings observable" (Phase 29 C+D).
  Phase 32 made **zero** structural changes to onboarding. The
  `useAppUiMode` hook lifts the `appTourDismissedInSession` flag
  into the hook (`useAppUiMode.ts`) but the tour mount + focus-trap
  + reduce-motion contracts are byte-stable.
- **Evidence (file:line):**
  - Phase 32 B touches only `App.tsx` reducer plumbing; tour
    component code unchanged (no diff against `OnboardingTour` /
    `AdvancedModePromo`).
  - 99-anchor conditions (branching paths / in-context bubbles /
    telemetry) still future.
- **Interpolation rationale:** Held at **90** (no lift, no
  regression; additive D:-1).

### 2. State preservation + recovery: **92/100**

- **Anchor match:** Phase 31 landed at 92. Phase 32 B re-homes
  the `appUiMode` persistence (already at the 90-anchor in Phase
  29 C) into a hook — same `localStorage` key, same shape, same
  corrupted-key fallback. Phase 32 C unlocks Compare-cuts to basic
  mode but `useViewportLayout`'s persistence contract is byte-stable
  (Phase 31 D origin-stamping eliminated the write-conflict risk
  that originally motivated the gate).
- **Evidence (file:line):**
  - `useAppUiMode.ts:1-110` — same `UI_MODE_LS_KEY` rehydration as
    Phase 29 C; corrupted-key path preserved.
  - `uiMode.ts:50` — `'coord-readout'` added but persistence keys
    unchanged; `'companion-viewport'` removed but the companion
    enabled-state in `useViewportLayout.ts:202-204` is untouched.
  - 99-anchor (cross-session JSON snapshot / IndexedDB / server
    resume) still future.
- **Interpolation rationale:** Held at **92** (structural lift on
  hook side mirrors Phase 31 B; no new behavioral guarantee for
  reviewer; additive D:-1).

### 3. Cognitive-load mitigation: **92/100**

- **Anchor match:** Between Phase 31's 91 and 99. Phase 31 honest
  gap #7 (App.tsx reducer debt) projected "Cog-load Dim 3 91 → ~93"
  if App-root extraction landed. Phase 32 B did the smallest honest
  slice — net-zero LOC, but separation-of-concerns improved.
  Phase 32 C1 (coord-readout gating) reduces basic-mode novice
  cognitive load; Phase 32 C3 (Compare-cuts unlock) ADDS feature
  surface in basic mode but is opt-in (first-paint unchanged).
- **Evidence (file:line):**
  - Hook extraction: `useAppUiMode.ts:1-110` collapses the
    `appUiMode` + `appTourDismissedInSession` cluster behind a
    `{state, actions}` return surface. Mirrors Phase 31 B pattern.
  - **Honest debit:** `App.tsx` 1457 LOC unchanged (verified
    `wc -l`). The 17/17 swap means structural cohesion improved
    inside the file but the file itself did not shrink. The
    blueprint's "1457 → 1200-1250" projection was over-optimistic;
    the commit body documents this honestly.
  - ~36 state surfaces remain in App.tsx (commit body
    `682e8f6` enumerates them). Phase 31 gap #7 is **partially**
    closed (the appUiMode cluster is the smallest cohesive piece;
    the rest is "too coupled for single-slice extraction").
  - Coord-readout gating: `uiMode.ts:43, 50` (added to type union
    + ADVANCED_FEATURE_IDS); `ResultMeshPlaybackPanel.tsx:796`
    (`shouldShowFeature(uiMode, 'coord-readout')` wraps the
    CoordReadoutTooltip render). Closes Phase 30 FINAL gap #9 +
    Phase 31 UX honest gap #2. Basic-mode novices no longer see
    the always-on 30Hz floating XYZ — direct cog-load reduction.
  - Compare-cuts unlock: `uiMode.ts:24-32` comments document
    `'companion-viewport'` removal; companion toggle now renders
    unconditionally in `ResultMeshPlaybackPanel.tsx`. Counter-
    vector: ADDS one feature surface to basic mode. **Mitigation:**
    the toggle is OPT-IN; default state = companion off (Phase 30
    contract); first-paint is unchanged. Reviewer must actively
    click into it. Net effect on novice first-paint = neutral;
    net effect on novice WHO DECIDES TO ENGAGE = positive (no
    longer hits a "this requires advanced mode" wall).
  - 99-anchor (adaptive density / role-driven UI) still future.
- **Interpolation rationale:** Hook extraction is honestly small
  (net-zero LOC; the projected -200 was over-optimistic). Coord-
  readout gating is the bigger Dim 3 win (closing a Phase-30
  regression). Compare-cuts unlock is net-neutral on first-paint
  but positive on engaged-novice flow. Combined **+1 over Phase
  31's 91 → 92** (NOT +2 — the App.tsx LOC stayed flat and the
  hook lift is incomplete). 14 of 17 Phase 31 honest gaps remain.

### 4. Motion / micro-interactions: **94/100**

- **Anchor match:** Between Phase 31's 93 and 99. Phase 31 honest
  gap #3 explicitly named "companion entrance fade NOT shipped —
  only the flex transition... Adding ~5 LOC of `@keyframes
  fm04a-companion-mount` would close the half-gap." Phase 32 C2
  ships exactly that.
- **Evidence (file:line):**
  - New motion class: `polishStyles.ts:75`
    (`POLISH_CLASS_COMPANION_MOUNT = 'fm04a-companion-mount'`).
  - Keyframes: `polishStyles.ts:94` (`@keyframes
    fm04a-companion-mount-fade-in`).
  - CSS rule: `polishStyles.ts:166-167` —
    `.fm04a-companion-mount { animation: fm04a-companion-mount-
    fade-in 200ms ease-out; }`. Matches the FM-04a 200ms ease-out
    vocabulary (probe-row mount/unmount, restored toast, advanced
    promo, chevron, layout-swap).
  - Reduce-motion respect: `polishStyles.ts:218` —
    `prefers-reduced-motion: reduce` block disables the animation.
    (B:-1 anti-gaming guard preserved.)
  - Class wired: `CompanionViewport.tsx:113` —
    `className={POLISH_CLASS_COMPANION_MOUNT}` on outermost div.
  - **Seventh surface in the FM-04a 200ms motion vocabulary**:
    (1) probe-row mount, (2) probe-row unmount, (3) restored toast,
    (4) advanced-mode promo, (5) chevron rotation, (6) layout-swap
    flex-basis/gap (Phase 31 D), (7) companion entrance fade
    (Phase 32 C). Each one closes one Phase-30+ recommended item.
- **Interpolation rationale:** Closes Phase 31 honest gap #3
  verbatim — a `~5 LOC` recommendation became a clean ~5 LOC
  delivery (3 lines in polishStyles + 1 import + 1 className).
  **+1 over Phase 31's 93 → 94.** Why not +2: this is a single
  affordance closure; the next ~5 honest-gap motion items
  (entrance fade on advanced controls, exit fade on companion
  unmount) are still future. 99 (spring physics / haptic) further
  future.

### 5. Error recovery + honesty surfacing: **93/100**

- **Anchor match:** Phase 31 landed at 93. Phase 32 made **zero**
  structural changes to error-recovery or honesty surfacing.
  - WebGL context-lost handler (Phase 31 D) byte-stable.
  - Warning-toast tokens (Phase 31 D) byte-stable.
  - No new claim-tier or claim-boundary surfacing.
  - No new corrupted-key pathway.
- **Evidence (file:line):**
  - `ResultMeshPlaybackPanel.tsx` toast surfaces at `:407-428`
    (verified existing from Phase 31).
  - `polishStyles.ts:128-135` `.fm04a-warning-toast` class
    untouched.
  - Phase 32 C unlocks Compare-cuts to basic mode but the trust
    strip + Tier-2-blocker row + claim badges are render-stable.
- **Interpolation rationale:** Held at **93** (no lift, no
  regression; additive D:-1).

### 6. Novice-user gotchas: **95/100**

- **Anchor match:** Between Phase 31's 94 and 99. Phase 31 closed
  the WebGL context-loss novice-trap; Real WebGL E2E remained the
  sole 90→99 blocker. Phase 32 closes the **coord-readout novice-
  surprise** (Phase 30 FINAL gap #9 + Phase 31 honest gap #2).
  Compare-cuts unlock is a small additional novice-affordance —
  novices who want to compare cuts no longer hit the "advanced
  mode required" wall.
- **Evidence (file:line):**
  - Coord-readout gotcha closed: `uiMode.ts:50` adds
    `'coord-readout'` to ADVANCED_FEATURE_IDS; the type union at
    `:43` adds the same literal; `ResultMeshPlaybackPanel.tsx:796`
    wraps `<CoordReadoutTooltip ...>` in
    `shouldShowFeature(uiMode, 'coord-readout')`. Basic-mode
    novices no longer see the always-on 30Hz floating XYZ that
    Phase 30 C silently introduced. Phase 30 FINAL gap #9 + Phase
    31 UX honest gap #2 closed verbatim.
  - Compare-cuts gotcha closed: `uiMode.ts:24-32` documents the
    `'companion-viewport'` removal from the gate; the comment
    explicitly cites "Phase 31 D origin-stamping wrapper
    eliminates the write-conflict risk." Companion toggle now
    visible in basic mode — novices can opt-in without context-
    switching to advanced. Phase 30 FINAL gap #10 + Phase 31 UI
    honest gap #11 closed.
  - Real WebGL E2E still future: `npx vitest run` stderr still
    emits `Not implemented: HTMLCanvasElement's getContext()` —
    vitest still mocks canvas. Phase 31 honest gap #4 carries to
    Phase 33+.
- **Interpolation rationale:** Two novice-gotcha closures
  (coord-readout + Compare-cuts gate) earn **+1 over Phase 31's
  94 → 95**. Real WebGL E2E remains the only blocker to 99.

## Composite UX score: **92.7/100**

  (90 + 92 + 92 + 94 + 93 + 95) / 6 = 556/6 = **92.666… → 92.7**

## Phase-32 lift over Phase 31 UX (92.2): **+0.5**

Lift breakdown (additive D:-1; Phase 31 numbers untouched):
- Onboarding 90 → 90 (+0); State 92 → 92 (+0); Cog-load 91 → 92
  (+1); Motion 93 → 94 (+1); Error/honesty 93 → 93 (+0); Novice
  94 → 95 (+1).

Aggregate **+0.5** is a small, honest lift — Phase 32 was a
deliberate "lower-FEA-ambition swap" phase that traded big-axis
moves for Tier-2 polish + a half-closure of the reducer debt.
The 3 axes that lifted are the 3 axes Phase 31's honest gaps
named (#2 coord-readout / #3 companion fade / #7 reducer +
#10 Compare-cuts). No regressions. The flat axes (Onboarding,
State, Error/honesty) reflect Phase 32 making no structural
changes there — consistent with the blueprint scope.

## Phase 32 honest gaps (Phase 33 forward look)

1. **App.tsx reducer debt still mostly open.** `useAppUiMode`
   extracted only the smallest cohesive cluster (`appUiMode` +
   `appTourDismissedInSession`). `App.tsx` is still 1457 LOC
   (byte-identical to Phase 30/31). ~36 state surfaces remain —
   the commit body explicitly names this as "too coupled for
   single-slice extraction." Phase 33+ candidates: `useTourState`
   (tour open + step + dismissedInSession), `useCaseListState`
   (selectedCaseId + cases + loading), `useTopbarState` (mode +
   density + collapsed-rails). Each would lift Dim 3 incrementally
   toward 94-95.
2. **Companion ENTRANCE fade landed but EXIT fade NOT shipped.**
   `POLISH_CLASS_COMPANION_MOUNT` covers opacity 0 → 1 on mount.
   When the user toggles companion OFF, it disappears instantly.
   Adding `@keyframes fm04a-companion-mount-fade-out` (opacity 1
   → 0, ~5 LOC) would complete the symmetric motion treatment
   (Phase 28 C asymmetric-faster-exit pattern). Dim 4 94 → ~95.
3. **Real WebGL E2E coverage still future.** `npx vitest run`
   stderr still emits `Not implemented: HTMLCanvasElement's
   getContext()`. vitest mocks canvas; Phase 31 D context-loss
   handler is pinned only via CSS-class assertion. Playwright
   + headless-WebGL is the prerequisite to anchor real
   `webglcontextlost` event dispatch. Sole remaining Dim 6
   95→99 blocker. Carry-over from Phase 26-31.
4. **`useViewportLayout` still doesn't own `contextLostToast` or
   `activePick`.** Phase 31 honest gap #5 not addressed. Small
   drift-risk item; would not move Dim 3 score but improves
   cohesion. Phase 33+ candidate.
5. **No telemetry / role-aware UI.** All 6 axes' 99-anchors
   require some form of user-role or proficiency-driven UI —
   onboarding paths (Dim 1), adaptive density (Dim 3), real
   WebGL E2E (Dim 6), inline "explain this verdict" (Dim 5).
   Multi-phase architectural item; not a single-phase spike.
6. **14 of 17 Phase 31 honest gaps carry forward.** Phase 32
   closed Phase 31 #2 (coord-readout), #3 (companion entrance),
   #7 partial (App-root reducer cluster only), plus Phase 30
   FINAL #9 (coord-readout) + #10 (Compare-cuts). The remaining
   12 items (App.tsx full extraction, exit-fade symmetry, WebGL
   E2E, useViewportLayout completion, ...) are Phase 33+ work.
7. **Onboarding + State + Error-honesty axes flat for 2 phases.**
   Phase 31 → Phase 32 these three held at 90/92/93. The 99-
   anchor items (branching tour paths, IndexedDB resume, dynamic
   claim_boundary) are each multi-phase items. Phase 33 may want
   to pick one to push.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
