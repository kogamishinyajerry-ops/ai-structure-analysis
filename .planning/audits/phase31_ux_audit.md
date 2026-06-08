# FM-04a Phase 31 — UX Audit · rubric v1.0

> Honest scoring per 绝对诚实客观 contract carried from Phase 18-30.
> Rubric: `.planning/audits/RUBRIC.md` v1.0 (Phase 29 D pinning).
> Tier 1 / Tier 2 engineering candidate; not signed validation;
> not benchmark agreement.

## Provenance baseline

- Phase 30 UX composite = **90.3/100** under v1.0 anchors
  (`phase30_ux_audit.md:198-200`): 90 / 92 / 88 / 90 / 90 / 92.
- Phase 31 UX-relevant deliveries (3 of 4 commits touch UX surface):
  - `52a9011` Phase 31 B: `useViewportLayout.ts` (268 LOC NEW) +
    `ResultMeshPlaybackPanel.tsx` -104 LOC + 441-LOC test file
    closing the 3-phase reducer-extraction debt (Phase 27 punchlist
    #3 + Phase 29 rec #2 + Phase 30 Dim 3 -1 debit).
  - `2c82860` Phase 31 D: UI polish bundle — companion
    `onNodePicked` + `companion:` prefix + layout-swap motion +
    WebGL context-lost handler + token warning-toast colors
    (8 files, +507 / -24 LOC, +14 tests).
  - `53e3430` Phase 31 A and `a8a1932` Phase 31 C — FEA-only
    (heat-transfer case + Richardson extrapolation), no UX surface.
- `App.tsx` = **1457 LOC** (unchanged from Phase 30 — verified via
  `git diff e935c63 a8a1932 -- frontend/src/App.tsx` empty).
  Reducer hook landed in panel, not App root — App-root reducer
  debt itself is **not** what was claimed closed (see gap #1 below).
- `ResultMeshPlaybackPanel.tsx` = **1411 LOC** (down from Phase 30
  close of 1515 → -104). Hook lift confirmed.
- Test status: **722/722 frontend tests PASS** (vitest, 8.34s,
  48 files). +14 over Phase 30 close at 708.
- D:-1 additive guard: Phase 30 retains 90.3 verbatim.

## Sub-axes

### 1. Onboarding flow quality: **90/100**

- **Anchor match:** 90 anchor = "App-root tour mount; focus-trap;
  reduce-motion; corrupted-key warnings observable" (Phase 29 C+D).
  Phase 31 made **zero** structural changes to onboarding — no diff
  to `App.tsx` / `OnboardingTour` / `AdvancedModePromo`.
- **Evidence (file:line):**
  - `App.tsx` byte-identical from Phase 30 (1457 LOC; `git diff
    e935c63 a8a1932 -- frontend/src/App.tsx` empty). Tour mount
    untouched.
  - Phase 31 D's new context-lost toast (`ResultMeshPlaybackPanel.
    tsx:407-428`) is bystander evidence the 90-anchor still holds —
    it's a recovery affordance, not an onboarding affordance. Its
    +N lands on Dim 5 and Dim 6, not here.
  - 99-anchor conditions (branching paths / in-context bubbles /
    telemetry) still future.
- **Interpolation rationale:** Held at **90** (no lift, no
  regression; additive D:-1).

### 2. State preservation + recovery: **92/100**

- **Anchor match:** Phase 30 landed at 92. Phase 31 B re-homes the
  same state surface into `useViewportLayout` without altering the
  persistence contract. Phase 31 D adds context-loss recovery
  state but the persistence axis is structurally unchanged.
- **Evidence (file:line):**
  - Persistence effects centralized: `useViewportLayout.ts:196-209`
    (probe-list `:196-199`, companion enabled `:202-204`, cut
    `:207-209`). Same keys, same shape — pinned by Phase 30 B/C
    invariant tests (`Phase31B_use_viewport_layout.test.tsx`
    `restores companion state from persisted localStorage`
    `:114-121`).
  - Corrupted-toast pathway still wired:
    `useViewportLayout.ts:161-180` case-mount diagnostic load
    `→ setCorruptedToast({caseId, reason})` on corruption;
    `:182-187` 8s auto-dismiss; `:243` `dismissCorruptedToast`
    action exported.
  - C:-1 cross-toggle preservation re-pinned via the hook:
    `Phase31B_use_viewport_layout.test.tsx` `toggleCompanion`
    section (`toggle ON when persisted cut exists does NOT re-seed`
    line ~ in 441-line file; preserved verbatim from Phase 30 B).
  - No new persistence dimension added; 99-anchor (cross-session
    JSON snapshot / IndexedDB / server resume) still future.
- **Interpolation rationale:** Held at **92** (structural lift —
  testable in isolation via `renderHook` — but no new behavioral
  guarantee for the reviewer; additive D:-1).

### 3. Cognitive-load mitigation: **91/100**

- **Anchor match:** Phase 30 took a -1 debit to 88 because the new
  companion-viewport UI surface was added without a structural
  refactor. The Phase 30 audit recommended a `useViewportLayout`
  hook would "lift Dim 3 from 88 to ~91." Phase 31 B ships exactly
  that.
- **Evidence (file:line):**
  - Hook extraction: `useViewportLayout.ts:113-268` collapses
    8 state fields + 5 effect cascades behind a single
    `{state, actions}` return surface (`:108-111`).
  - Panel LOC delta: `ResultMeshPlaybackPanel.tsx` **1515 → 1411
    (-104)** (verified `wc -l`). Inline `useState` + `useEffect`
    blocks replaced by destructured pull (`:159-181`).
  - Cohesion gain: 5 viewport-layout effects now in ONE file
    (`useViewportLayout.ts:158-209`) instead of 9 scattered blocks
    in the panel. Comments at `:151-158` document the migration.
  - Testability gain: 441 LOC of `renderHook` unit tests
    (`Phase31B_use_viewport_layout.test.tsx`) — no panel-mount
    required to pin the layout cascade.
  - **Honest debit:** the hook's typed surface (`ViewportLayoutState`
    `:73-82` + `ViewportLayoutActions` `:84-99`) adds boilerplate
    the inline `useState` calls didn't have, so the panel LOC drop
    is -104 not the blueprint-projected -180. App.tsx (1457 LOC)
    itself is **unchanged** — the Phase 27 punchlist #3 also named
    App.tsx as a target, but Phase 31 B addressed only the panel.
    The reducer-extraction debt is **partially closed** (panel
    side) not fully closed.
  - Coord-readout still NOT advanced-gated
    (`ResultMeshPlaybackPanel.tsx:786-788`). Phase 30 gap #4
    explicitly called this out as "~5 LOC + 1 feature-id entry to
    gate" — unaddressed in Phase 31.
- **Interpolation rationale:** Hook lift earns the +3 (88 → 91)
  the Phase 30 audit projected. The unaddressed coord-readout
  gating and unchanged App.tsx prevent reaching the Phase 30
  audit's upper bound. 99 (adaptive density) future. **+3 over
  Phase 30's 88 → 91.**

### 4. Motion / micro-interactions: **93/100**

- **Anchor match:** Between Phase 30's 90 and 99. Phase 30 audit
  explicitly named the layout-swap motion gap (Compare-cuts flips
  instantly without width transition) as "~10-15 LOC of CSS" to lift
  Dim 4 toward 99. Phase 31 D ships it.
- **Evidence (file:line):**
  - New motion class: `polishStyles.ts:69` (export
    `POLISH_CLASS_VIEWPORT_FLEX_ROW`).
  - CSS rules: `polishStyles.ts:144-149` —
    `.fm04a-viewport-flex-row { transition: gap 200ms ease-out; }`
    plus `> * { transition: flex-basis 200ms ease-out, width 200ms
    ease-out; }`. Matches the FM-04a 200ms ease-out vocabulary
    (Phase 27 C probe-row, Phase 28 C restored-toast, Phase 29 B
    chevron).
  - Reduce-motion respect:
    `polishStyles.ts:207-213` — `prefers-reduced-motion: reduce`
    block names both selectors with `transition: none`. Pinned at
    `Phase31D_ui_polish_bundle.test.tsx:183-196`.
  - Class wired on the row container:
    `ResultMeshPlaybackPanel.tsx:600-601` (`data-testid="viewport-
    flex-row"` + `className={POLISH_CLASS_VIEWPORT_FLEX_ROW}`).
    Pinned at `Phase31D_ui_polish_bundle.test.tsx:167-181`.
  - Companion `onNodePicked` (Phase 31 D feature 1) does NOT add
    new motion — defensible (the pick already animates via
    `POLISH_CLASS_PROBE_ROW_MOUNT`, which the new `companion:`
    prefix inherits for free).
  - Token warning-toast (`POLISH_CLASS_WARNING_TOAST`) reuses the
    restored-toast 200ms fade-in animation (composition pattern at
    `ResultMeshPlaybackPanel.tsx:410` + `polishStyles.ts:128-135`)
    — no motion regression on the corrupted-toast or the new
    context-lost toast.
- **Interpolation rationale:** Phase 30 audit recommended
  "200ms ease-out on `primary-viewport-slot` + entrance fade on
  companion." Layout-swap delivered; entrance fade on companion
  itself is NOT delivered (companion uses the row transition for
  flex-basis but has no opacity/translate entrance). Partial
  lift earns **+3 over Phase 30's 90 → 93**, short of the full
  delta the audit projected because the entrance-fade half is
  still future. 99 (spring physics / haptic) further future.

### 5. Error recovery + honesty surfacing: **93/100**

- **Anchor match:** Between Phase 30's 90 and 99. Phase 30 audit
  named "WebGL context-loss handler missing" as gap #3 — novice
  has no recovery path when GPU context drops. Phase 31 D ships
  the handler + SVG fallback + user-visible warning toast.
- **Evidence (file:line):**
  - Listener registered: `ResultMeshWebGLViewport.tsx:201-223` —
    `webglcontextlost` event handler on `renderer.domElement`,
    `event.preventDefault()` to suppress browser retry-loop,
    `reason` extracted from `statusMessage` when present.
  - E:-1 unmount safety: `ResultMeshWebGLViewport.tsx:244-249`
    (listener removed in the same `useEffect` cleanup that disposes
    the renderer).
  - Parent fallback wired:
    `ResultMeshPlaybackPanel.tsx:225-228` — `handleContextLost`
    sets `viewportMode='svg'` AND surfaces the toast.
  - Toast surfaced: `ResultMeshPlaybackPanel.tsx:407-428` —
    `role="alert"` + `aria-live="assertive"` (`:411-412`),
    composes `POLISH_CLASS_RESTORED_TOAST` +
    `POLISH_CLASS_WARNING_TOAST` (`:410`), 10s auto-dismiss
    (`:214-218`) — longer than Phase 28 C 4s and Phase 30 C 8s,
    justified inline as "rarer + reviewer needs time to register
    the mode change."
  - Token-tinted warning color migration:
    `polishStyles.ts:128-135` — `.fm04a-warning-toast` overrides
    ONLY color (`#fda4af`) and border-color
    (`rgba(239,68,68,0.55)`), no `background:` override (inherits
    slate-950 from parent). Phase 30 C's inline rgba override
    moved to this class. Phase 30 C corrupted-toast updated to
    compose the class at `ResultMeshPlaybackPanel.tsx:410`.
    Pinned at `Phase31D_ui_polish_bundle.test.tsx:226-247`.
  - Hue continuity guard: `Phase31D_ui_polish_bundle.test.tsx:242-
    247` asserts `#fda4af` survives the class migration.
- **Interpolation rationale:** The handler + fallback + toast
  triplet directly addresses the Phase 30 audit's recommendation
  #3. Token migration adds tonal-discipline gain (UI Dim 3
  spillover but UX-relevant: warning colors now consistent across
  corrupted + context-lost). **+3 over Phase 30's 90 → 93.**
  99 anchor (inline "explain this verdict" + dynamic
  claim_boundary) still future.

### 6. Novice-user gotchas: **94/100**

- **Anchor match:** Between Phase 30's 92 and 99. Phase 30 scored
  92 with 2 of 3 99-conditions hit (coord tooltips ✅,
  multi-viewport ✅, Real WebGL E2E ❌). Phase 31 D closes the
  WebGL context-loss novice-trap (Phase 30 audit Gap #3 named
  this as the sole 90→99 gap on Dim 6 below E2E).
- **Evidence (file:line):**
  - Context-loss novice-trap closed: when GPU context drops, panel
    auto-falls-back to SVG (`ResultMeshPlaybackPanel.tsx:226`) AND
    surfaces an `aria-live="assertive"` alert (`:411-418`). Without
    this handler, the canvas would have gone black silently — the
    exact novice-trap Phase 30 audit flagged. Reviewer keeps
    working in SVG mode without a hard reload.
  - Companion picks now surface in probe list:
    `ProbeListPanel.tsx:208-216` — `companion:` prefix renders when
    `entry.origin === 'companion'`. Closes a smaller novice-trap
    Phase 30 audit honest gap section #11 named ("Companion
    `onNodePicked` not wired — read-only companion leaves a parity
    gap"). Reviewer who picks in companion now SEES the source —
    previously the pick was silently dropped.
  - CSV schema stability preserved (`Phase31D_ui_polish_bundle.
    test.tsx:147-162`): `origin` field omitted from CSV output to
    preserve the Phase 25 D 5-column schema. Novice exporting a
    probe list doesn't see a schema break.
  - Real WebGL E2E coverage still future: `npx vitest run` output
    still shows `Not implemented: HTMLCanvasElement's getContext()`
    repeating across canvas-touching tests — vitest still mocks
    canvas. Playwright + headless-WebGL remains the third 99-
    condition. Phase 30 audit #5 unchanged.
- **Interpolation rationale:** Context-loss closure is the biggest
  novice-trap addressed since coord-readout / multi-viewport.
  Companion-pick prefix is a smaller-but-real recovery on a Phase
  30 audit honest-gap line item. **+2 over Phase 30's 92 → 94.**
  Real WebGL E2E remains the only blocker to 99.

## Composite UX score: **92.2/100**

  (90 + 92 + 91 + 93 + 93 + 94) / 6 = 553/6 = **92.166… → 92.2**

## Phase-31 lift over Phase 30 UX (90.3): **+1.9**

Lift breakdown (additive D:-1; Phase 30 numbers untouched):
- Onboarding 90 → 90 (+0); State 92 → 92 (+0); Cog-load 88 → 91
  (+3); Motion 90 → 93 (+3); Error/honesty 90 → 93 (+3); Novice
  92 → 94 (+2).

Aggregate **+1.9** lands inside the Phase 30 audit's projected
"+1 to +2.5" forward look. Gains concentrate on the 3 axes the
Phase 30 audit explicitly called out as Phase-31 candidates
(Dim 3 reducer extraction → +3; Dim 4 layout-swap motion → +3;
Dim 5+6 context-loss handler → +3/+2). Two axes held flat
(Onboarding, State) — no regressions.

## Phase 31 honest gaps (Phase 32 forward look)

1. **App.tsx reducer extraction not done.** `App.tsx` is still
   1457 LOC (byte-identical to Phase 30). Phase 31 B closed the
   panel-side reducer debt but the Phase 27 punchlist #3 also
   named App.tsx as a target. A `useTopbarState` or `useAppLayout`
   hook collapsing tour/promo/case-list/mode state would lift
   Dim 3 from 91 toward 94.
2. **Coord-readout still not advanced-gated.** Phase 30 audit
   gap #4 named this as "~5 LOC + 1 feature-id entry to gate."
   `ResultMeshPlaybackPanel.tsx:786-788` renders the tooltip in
   both basic + advanced. Basic-mode novices still see floating
   XYZ they didn't see pre-Phase-30. Trivial Phase 32 lift —
   would close a small Dim 3 / Dim 6 surface-area regression.
3. **Companion entrance fade NOT shipped.** Phase 30 audit
   gap #2 recommended "200ms ease-out on `primary-viewport-slot`
   + entrance fade on companion." Phase 31 D shipped the row
   transition (flex-basis/gap) but the companion mounts cold
   with no opacity/translate entrance. Adding ~5 LOC of
   `@keyframes fm04a-companion-mount` would close the half-gap
   and lift Dim 4 toward 95.
4. **Real WebGL E2E coverage still future.** `npx vitest run`
   stderr still emits `Not implemented: HTMLCanvasElement's
   getContext()` 12+ times — vitest mocks canvas. The new
   context-loss handler (Phase 31 D) is pinned only via CSS-
   class assertion (`Phase31D_ui_polish_bundle.test.tsx:210-220`)
   and a no-throw render check, NOT via a real `webglcontextlost`
   event dispatch on a live canvas. Playwright + headless-WebGL
   is the prerequisite to anchor the context-loss + multi-
   viewport features against real browser regression. Sole
   remaining Dim 6 90→99 blocker.
5. **`useViewportLayout` doesn't own all viewport-coupled state.**
   `viewportMode` lives in the hook (`:125-126`) but
   `contextLostToast` lives in the panel
   (`ResultMeshPlaybackPanel.tsx:147-149`) because the hook
   landed in Phase 31 B before context-loss landed in Phase 31 D.
   `activePick` (`:141`) likewise stayed in the panel. A small
   Phase 32 follow-up could migrate these two for cohesion
   (would not move the Dim 3 score further but reduces drift
   risk).

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
