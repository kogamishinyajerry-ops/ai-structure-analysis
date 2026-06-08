# FM-04a Phase 30 — UX Audit · rubric v1.0

> Honest scoring per 绝对诚实客观 contract carried from Phase 18-29.
> Rubric: `.planning/audits/RUBRIC.md` v1.0 (Phase 29 D pinning).
> Tier 1 / Tier 2 engineering candidate; not signed validation;
> not benchmark agreement.

## Provenance baseline

- Phase 29 UX composite = **89.2/100** under v1.0 anchors
  (`phase29_ux_audit.md:183-185`): 90 / 90 / 89 / 90 / 86 / 90.
- Phase 30 UX-relevant deliveries (2 of 4 commits touch UX surface):
  - `a054995` Phase 30 B: `CompanionViewport.tsx` (233 LOC) +
    `companionViewportStorage.ts` (114 LOC) +
    `ResultMeshPlaybackPanel.tsx` viewport-row restructure +
    `uiMode.ts` `'companion-viewport'` feature-id + 36 tests.
  - `e935c63` Phase 30 C: `CoordReadoutTooltip.tsx` (103 LOC) +
    `probeListStorage.ts:loadProbeListWithDiagnostic` (structured
    `LoadProbeListResult` w/ `corrupted` flag + reason) + corrupted
    toast in panel + `ResultMeshWebGLViewport.tsx` `onHoverCoords`
    prop with 30Hz throttled raycast + 23 tests.
  - `a2e3b7c`, `1b34f5e` — FEA-only, no UX surface change.
- `App.tsx` = **1457 LOC** (identical to Phase 29 E; `git diff
  a2e3b7c~1 1b34f5e -- frontend/src/App.tsx` empty). Phase 27
  punchlist #3 reducer-extraction debt **unmoved**.
- Test status: **59/59 Phase 30 B+C tests PASS** (vitest, 1.45s).
- D:-1 additive guard: Phase 29 retains 89.2 verbatim.

## Sub-axes

### 1. Onboarding flow quality: **90/100**

- **Anchor match:** 90 anchor = "App-root tour mount (no tab coupling);
  focus-trap; reduce-motion; corrupted-key warnings observable.
  Phase 29 C+D." Phase 30 made **zero** structural changes to
  onboarding (no diff to `App.tsx` / `OnboardingTour` /
  `AdvancedModePromo`).
- **Evidence (file:line):**
  - Tour + promo App-root mount unchanged (`App.tsx:1224-1240`
    preserved from Phase 29; verified via empty git diff).
  - Compare-cuts toggle NOT walked by the tour — neither lift nor
    regression on this axis. Corrupt toast (Phase 30 C) is bystander
    evidence that 90-anchor still holds (its +4 lands on Dim 5).
- **Interpolation rationale:** All four 90-anchor conditions hold; 99
  reserved for branching paths / in-context bubbles (not pursued).
  Held at **90** (additive D:-1).

### 2. State preservation + recovery: **92/100**

- **Anchor match:** Between Phase 29's 90 and 99. Phase 30 B adds a
  new persistence dimension (companion enabled + independent cut),
  and Phase 30 C upgrades the corrupted-key surface from
  observability-only to first-class recovery via
  `LoadProbeListResult.corrupted/reason`.
- **Evidence (file:line):**
  - Companion persistence: `companionViewportStorage.ts:22-25` keys
    `fm04a.companion-viewport.{enabled,cut-position}.v1`; `:29-50`
    enabled load/save with SecurityError swallow (E:-1); `:55-78` cut
    load with full shape validation (axis enum + finite positionM +
    boolean showLow), returns `null` on any fault. 12 storage tests
    (`Phase30B_companion_viewport.test.tsx:52-170`).
  - C:-1 cross-toggle preservation:
    `Phase30B_companion_viewport.test.tsx:573-601` pins "companion
    section-cut state preserved across Compare toggle off/on."
  - Diagnostic signal: `probeListStorage.ts:47-52` defines
    `LoadProbeListResult`; `:76-122` returns `{state, corrupted,
    reason}` on three failure modes (malformed JSON `:89-98`, wrong-
    shape `:99-109`, storage-access `:111-121`). Missing-key returns
    `corrupted:false` explicitly (`:84`) — "discarded ≠ never-stored"
    distinction honored.
  - Toast wired: `ResultMeshPlaybackPanel.tsx:246-262` case-mount
    effect; `:264-268` 8s auto-dismiss; `:434-459` renders with
    `role="alert"` + `aria-live="assertive"` + warning color override
    + manual dismiss button. 8 toast tests
    (`Phase30C_corrupt_toast_coord_readout.test.tsx:114-256`).
- **Interpolation rationale:** Phase 30 adds (a) NEW persistence axis
  (companion), (b) user-visible alert toast with a11y, (c) console.warn
  still fires at `:90-91, 101-102, 113-114` (no regression). Two 99-
  anchor conditions (JSON snapshot + IndexedDB / server resume) still
  future. **+2 over Phase 29's 90 → 92.**

### 3. Cognitive-load mitigation: **88/100**

- **Anchor match:** Between Phase 29's 89 and 99. Phase 30 B
  introduces NEW UI surface (companion viewport + Compare-cuts toggle
  + companion section-cut control row) — opposite of load reduction.
  Honest question: do gating + default-off earn back the surface cost?
- **Evidence (file:line):**
  - Default OFF: `companionViewportStorage.ts:28-36`
    (`loadCompanionEnabled` returns `false` on missing key). Pinned
    at `Phase30B_companion_viewport.test.tsx:56-58`.
  - Advanced-gating: `uiMode.ts:22-27, 29-35` adds
    `'companion-viewport'` to `ADVANCED_FEATURE_IDS`;
    `ResultMeshPlaybackPanel.tsx:304, 309-310` AND-gates toggle ×
    advanced × WebGL mode. `:540` button hidden in basic. 3 gating
    tests at `Phase30B_companion_viewport.test.tsx:459-502`.
  - Coord-readout NOT advanced-gated
    (`ResultMeshPlaybackPanel.tsx:835-837`) — runs in both modes.
    Honest debit: basic-mode novices now see floating XYZ they
    didn't before (small but non-zero).
  - Probe-list-row **lifted out** of `primary-viewport-slot` to
    sibling of `viewport-flex-row`
    (`ResultMeshPlaybackPanel.tsx:861-899`; pinned at
    `Phase30B_companion_viewport.test.tsx:653-677`). Small layout
    cognitive-load WIN — symmetric when Compare is on.
- **Interpolation rationale:** Companion adds ~120px of new chrome
  when ON; gating earns most back but not all. **-1 vs Phase 29's 89**
  because the panel is approaching a complexity inflection
  (`ResultMeshPlaybackPanel.tsx` now 1515 LOC, up from ~1310 at
  Phase 29 close) and App.tsx reducer debt is unmoved. 99 anchor
  (adaptive density) future.

### 4. Motion / micro-interactions: **90/100**

- **Anchor match:** Phase 29's 90 = "chevron rotation + promo
  entrance matching tour vocabulary + all reviewer-touchable
  affordances covered." Phase 30 adds new affordances; question is
  whether each respects the 200ms ease-out vocabulary.
- **Evidence (file:line):**
  - Corrupted toast reuses `POLISH_CLASS_RESTORED_TOAST`
    (`ResultMeshPlaybackPanel.tsx:437`) → `fm04a-restored-toast-fade-in
    200ms ease-out` (`polishStyles.ts:70-77, 102`). Same vocabulary.
  - Reduce-motion inherited: `polishStyles.ts:161-167` already names
    `.${POLISH_CLASS_RESTORED_TOAST}` in the
    `prefers-reduced-motion: reduce` block — corrupted toast picks
    up suppression for free.
  - Compare-cuts toggle (`ResultMeshPlaybackPanel.tsx:540-582`): NO
    layout-swap animation. When Compare flips ON, primary resizes
    50% narrower and companion mounts cold — a 200ms width transition
    would match vocabulary, isn't there. Honest gap.
  - Coord-readout (`CoordReadoutTooltip.tsx:50-83`): no entrance fade
    — defensible (30Hz tooltip; fade would feel laggy).
  - Companion section-cut readout reuses
    `POLISH_CLASS_SECTION_CUT_READOUT` (`CompanionViewport.tsx:172`)
    — same vocabulary as primary.
- **Interpolation rationale:** Vocabulary preserved, no new motion
  innovation, one missed layout-swap opportunity. Held at **90** (no
  lift, no regression). 99 (spring physics / haptic) future.

### 5. Error recovery + honesty surfacing: **90/100**

- **Anchor match:** Phase 29 D landed at 86 because corrupted-key
  warn was console-only. Phase 29 audit recommendation #1 said
  "Toast-surface the corrupted-key warn would lift Dim 5 from 86 → 90
  cleanly." Phase 30 C ships exactly that.
- **Evidence (file:line):**
  - Structured signal: `probeListStorage.ts:47-52`
    (`LoadProbeListResult.corrupted` + `reason`). Three failure modes
    carry distinct reasons (`malformed JSON: <err>` :89, `wrong-shape
    payload` :100, `storage access failed: <err>` :112).
  - User-visible toast: `ResultMeshPlaybackPanel.tsx:434-459` —
    `role="alert"` + `aria-live="assertive"` (`:438-439`) → screen
    readers announce immediately (higher-stakes than restored toast's
    `aria-live="polite"`). Warning color `#fda4af` + danger border
    (`:442-443`). Pinned at
    `Phase30C_corrupt_toast_coord_readout.test.tsx:231-256`.
  - Auto-dismiss + manual: `:264-268` 8s timeout (2× restored toast
    lifespan, justified inline as "higher-stakes"); `:450-457`
    dismiss button.
  - Semantic distinction: missing-key ≠ corrupted pinned at
    `Phase30C_corrupt_toast_coord_readout.test.tsx:134-145`.
  - Phase 29 D console.warn preserved
    (`probeListStorage.ts:90-91, 101-102, 113-114`) — engineer path
    intact alongside user toast.
- **Interpolation rationale:** Cleanest single-axis lift in Phase 30;
  lands the Phase 29 audit recommendation verbatim. **+4 over Phase
  29's 86 → 90.** 99 anchor (inline "explain this verdict" + dynamic
  claim-boundary) future.

### 6. Novice-user gotchas: **92/100**

- **Anchor match:** Between Phase 29's 90 and 99. The 99 anchor names
  "+ Real WebGL E2E coverage; **+ measurement/coord tooltips**;
  + multi-viewport split for context." Phase 30 ships 2 of 3.
- **Evidence (file:line):**
  - Multi-viewport split: `CompanionViewport.tsx:80-232`. Honest
    scope inline `:1-30` (no camera-sync, no pick-pinning across
    views — avoids double-add confusion). 9 render tests
    (`Phase30B_companion_viewport.test.tsx:173-326`).
  - Coord-readout: `CoordReadoutTooltip.tsx:40-83` — null/NaN/Infinity
    guards `:41-48`, `pointerEvents:'none'` `:67` (never blocks
    canvas hits), `aria-live="off"` `:54` (30Hz screen-reader spam
    deliberately suppressed; pinned at
    `Phase30C_corrupt_toast_coord_readout.test.tsx:340-350`).
  - 30Hz throttle at source: `ResultMeshWebGLViewport.tsx:444-505` —
    `HOVER_THROTTLE_MS=33` `:445`, gated on `!dragging` `:448`
    (D:-1 "don't fight orbit"). Mouse-leave clears
    (`:483-485` + tooltip self-clears on `info=null`
    `CoordReadoutTooltip.tsx:41`).
  - Corrupted warning now visible to non-engineers (Dim 5 evidence
    reinforces this axis).
- **Interpolation rationale:** **+2 over Phase 29's 90.** 99 conditions
  scoreboard: coord tooltips ✅, multi-viewport ✅, Real WebGL E2E ❌
  (vitest still mocks canvas — 14× "Not implemented: getContext()"
  warnings in test stderr). Gap #3 below flags missing
  `webglcontextlost` handler as a novice trap under 2× context load.

## Composite UX score: **90.3/100**

  (90 + 92 + 88 + 90 + 90 + 92) / 6 = 542/6 = **90.33 → 90.3**

## Phase-30 lift over Phase 29 UX (89.2): **+1.1**

Lift breakdown (additive D:-1; Phase 29 numbers untouched):
- Onboarding 90 → 90 (+0); State 90 → 92 (+2); Cog-load 89 → 88 (-1);
  Motion 90 → 90 (+0); Error/honesty 86 → 90 (+4); Novice 90 → 92 (+2).

Aggregate **+1.1** lands at the lower end of the blueprint's projected
"+1 to +2.5" band — honest under-delivery because the cognitive-load
axis took a small debit (+companion UI surface) the blueprint did not
model. **Phase 30's UX lift concentrates in Dim 5 (+4)** — the single
quality-debt closure Phase 29 audit recommended #1.

## Honest gaps carried forward to Phase 31 (top 5)

1. **Cognitive-load debit needs reducer extraction.**
   `ResultMeshPlaybackPanel.tsx` now 1515 LOC; App.tsx still 1457.
   A `useViewportLayout` hook collapsing (showCompanionViewport,
   companionSectionCut, hoverCoords, viewportMode) would lift Dim 3
   from 88 to ~91. SAME debt as Phase 27 punchlist #3 + Phase 29
   recommendation #2, unpaid across three phases now.
2. **Layout-swap motion gap.** Compare-cuts flips instantly with no
   width transition. 200ms ease-out on `primary-viewport-slot` +
   entrance fade on companion would lift Dim 4 toward 99. ~10-15 LOC
   of CSS.
3. **WebGL context-loss handler missing.** No `webglcontextlost`
   listener in either viewport — when a 2× context-cap eviction
   silently blanks the canvas, a novice has no recovery path. Toast
   surfacing "WebGL context lost — refresh to recover" closes the
   sole 90→99 gap on Dim 6 below E2E. ~30 LOC.
4. **Coord tooltip not advanced-gated.** Basic-mode novices now see
   floating XYZ they didn't before. Gate on
   `shouldShowFeature(uiMode, 'coord-readout')` to remove the
   basic-mode surface-area increase. ~5 LOC + 1 feature-id entry.
5. **Real WebGL E2E coverage still future.** 14× "Not implemented:
   getContext()" warnings in test stderr confirm vitest still mocks
   canvas. Playwright + headless-WebGL is prerequisite to anchoring
   the multi-viewport + coord-readout features with real browser
   regression — the third 99-condition on Dim 6.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
