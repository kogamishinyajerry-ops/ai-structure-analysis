# FM-04a Phase 29 — UI Audit · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Scoring per `.planning/audits/RUBRIC.md`
> (v1.0). Phase 28 UI composite baseline = **77.6** (delta-corrected
> from Phase 27 actual per Phase 28 8th-case ballistic-exit retro;
> absolute audit pinned **77.5** held flat).
>
> Phase 29 B (`5456e82`) shipped the SectionFrame primitive + 7
> collapsible trust sections + per-section localStorage. Phase 29 C
> (`8d3baed`) shipped useFocusTrap on both modal overlays + promo
> entrance animation matching tour vocabulary + App-root mount of
> both overlays. Both are **structurally load-bearing** (closing
> Phase 28 audit Dim 2 / Dim 4 / Dim 5 / Dim 6 named gaps), not pure
> polish — the composite should reflect that.

## Sub-axes

### 1. Micro-interaction polish + animation quality: **90/100**
- Evidence:
  - Phase 29 B chevron rotation `transition: transform 180ms ease-out`
    (`polishStyles.ts:140-142`); same easing family as tour 200ms
    ease-out anchor (`polishStyles.ts:74-77,104-106`).
  - Phase 29 C `fm04a-advanced-mode-promo-fade-slide-in` keyframe
    matches tour entrance vocabulary (200ms ease-out, 8px translateY)
    — `polishStyles.ts:74-77`. Promo no longer "snaps in" while
    surrounding affordances fade.
  - Reduce-motion @media expanded to cover BOTH new affordances:
    promo (`polishStyles.ts:165`) + chevron (`polishStyles.ts:171-173`,
    transition disabled but rotation visual state preserved per
    SectionFrame B:-1 guard).
- Anchor: **90 anchor exact match** — rubric line 185 reads
  "Chevron + accordion + promo entrance all in the same vocabulary."
  Phase 29 B + C deliver verbatim. Stays under 99 (no spring physics,
  no haptic hooks, no choreographed cross-panel synchronization).

### 2. Visual hierarchy + typography: **89/100**
- Evidence:
  - SectionFrame primitive (`SectionFrame.tsx:89-150`) supplies a
    uniform 3-tier type ramp: 0.86rem/800 header → 0.66rem
    uppercase/700 row label → 0.82rem/650 row value. All 7 trust
    sections render through it (`OperatorStatusPanel.tsx:91-99`).
  - Collapse summary chip in header (`SectionFrame.tsx:115-122`)
    is 0.7rem uppercase 600 muted — visually distinct from title
    weight (800), encoding hierarchy non-color-redundantly.
  - Chevron + icon + title + count form a stable 4-slot header
    grammar repeated across all 7 sections (`SectionFrame.tsx:102-122`).
- Anchor: rubric 90 anchor reads "+ Uniform SectionFrame primitive;
  + collapse summary in header." Exact match for both. Held back
  from 95+ because the wider Visual tab area (App.tsx slider/legend
  composition) still does not flow through SectionFrame, so the
  primitive is sectioned-but-not-system-wide. Interpolate **89**.

### 3. Color system + tonal discipline: **85/100**
- Evidence:
  - 4-tone vocabulary unchanged from Phase 28
    (`OperatorStatusPanel.tsx:48-67`); SectionFrame reuses identical
    accent/warning/danger/muted resolver (`SectionFrame.tsx:49-54`).
  - No new color tokens added; no regression — diff scoped to
    structural primitive + animation keyframe.
- Anchor: rubric 90 anchor reads "+ No regression in Phase 29 ship."
  Phase 28 anchored at 85 explicitly (rubric line 207). **Honest
  hold at 85**: the *anchor* allows 90 but the *underlying state*
  (no dark theme, no semantic-enum statusTone, statusTone(fail)
  hard-string fallback unchanged) hasn't actually improved. Per
  rubric "find the anchor closest to current state" + cite evidence,
  scoring 90 here would inflate against unchanged substrate.

### 4. Accessibility (a11y): **85/100**
- Evidence:
  - `useFocusTrap` hook (`useFocusTrap.ts:82-151`) cycles Tab /
    Shift-Tab among tabbables, captures+restores prior focus,
    focuses first tabbable on mount (D:-2 guard).
  - Applied to OnboardingTour AND AdvancedModePromo
    (`AdvancedModePromo.tsx:104`); both mount at App-root (`App.tsx:1234-1235`)
    so trap is unconditional, not tab-state-coupled.
  - SectionFrame toggle button has `aria-expanded={!collapsed}` +
    `aria-controls={...-body}` (`SectionFrame.tsx:98-99`); body has
    `role="region"` + `aria-label` (`SectionFrame.tsx:126-127`).
  - Phase 28 a11y substrate (role/dialog, aria-live, aria-label,
    reduce-motion) preserved — no regression.
- Anchor: rubric 85 anchor reads "+ Focus-trap on all modal overlays
  (WCAG 2.4.3)." Exact match. Held at 85 (not 88+) because rubric
  92 anchor requires "keyboard-only nav tested + documented + SR
  fixtures" — Phase 29 has 23 focus-trap tests but no SR fixtures,
  no documented keyboard nav path, and `aria-describedby` linking
  promo body (Phase 28 audit P29-1 sub-rec) is NOT shipped.

### 5. Industrial-software parity: **82/100**
- Evidence:
  - Collapsible accordion on all 7 trust sections via SectionFrame
    + per-section persistence (`sectionCollapseStorage.ts:32-62`) —
    matches Abaqus/CAE Model Tree default collapse-on-demand pattern.
  - Uniform SectionFrame primitive replaces inline section markup;
    `App.tsx` 1667 → 1457 LOC (`wc -l` actuals; brief cited 1421,
    drift small but verified shrink).
  - App-root mount of overlays (`App.tsx:1234-1235`) decouples
    tour/promo from Visual-tab — closer to Hyperworks "Getting
    Started" page pattern which is app-scoped, not view-scoped.
- Anchor: rubric 82 anchor reads "+ Collapsible accordion on trust
  sections; uniform SectionFrame primitive." Exact match. Held at
  82 (not 86+) because rubric 88 requires "multi-viewport split
  (4-quadrant default); measurement/coord tools; collapsible
  left/right rails" — NONE shipped. Abaqus/CAE / ANSYS Mechanical /
  Hyperworks all ship 4-quadrant default; the single-viewport
  playback panel remains the dominant parity gap.

### 6. Density + reviewer ergonomics: **85/100**
- Evidence:
  - SectionFrame per-section collapse with default expanded
    (D:-1 additive — `SectionFrame.tsx:59`) lets reviewer fold
    "Overview" / "Validation" / "Evidence" independently after
    reading; survives reload (`sectionCollapseStorage:25-27` key
    pattern `fm04a.trust-section.<slug>.collapsed.v1`).
  - Item-count chip in collapsed header (`SectionFrame.tsx:115-122`)
    keeps scan-density high — reviewer sees "5 items" without
    re-expanding to count.
  - Section grid `gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))'`
    (`OperatorStatusPanel.tsx:91`) reflows uncollapsed sections;
    collapsed sections still occupy a grid slot — Abaqus tree
    collapses fully out of flow which is denser, but the auto-fit
    reflow approximates.
- Anchor: rubric 85 anchor reads "+ Per-section collapse lets reviewer
  focus on one panel at a time." Exact match. Held at 85 (not 92)
  because rubric 92 requires "drag-to-resize panels; density toggle
  (compact / comfortable)" — neither shipped. Probe table still
  fixed-width (Phase 28 gap unaddressed).

---

## Composite UI score: **86.0/100**

(90 + 89 + 85 + 85 + 82 + 85) / 6 = **86.0**

## Phase-29 lift over Phase 28 UI (77.6): **+8.4**

Honest reading: Phase 28 audit explicitly flagged "Phase 29
recommendations" that map 1:1 to Phase 29 B + C:

| Phase 28 recommendation | Phase 29 delivery |
|---|---|
| **Focus-trap on AdvancedModePromo + OnboardingTour** | `useFocusTrap` hook applied to both (Phase 29 C `8d3baed`) |
| **Reviewer-Frame primitive + collapsible 7-section accordion** | `SectionFrame` + `sectionCollapseStorage` + OperatorStatusPanel refactor (Phase 29 B `5456e82`) |
| ~~Measurement tools + multi-viewport split~~ | NOT shipped — Phase 30 candidate |

Phase 29 closed 2 of 3 named recs from Phase 28; the third
(multi-viewport / measurement) was the rubric Dim 5 "88 anchor"
gate and remains the dominant parity gap. The +8.4 lift is
consistent with closing 2 structurally-load-bearing recs in a
single phase; honest band per brief was 82-86 (lower bound assumed
Dim 5 stayed flat at 70; upper bound assumed Dim 5 absorbed the
SectionFrame win at the 82 anchor — the latter applies, putting
us at the upper end of the expected band).

Anti-gaming guard: composite did NOT cross 86 even though every
sub-axis is at or above its Phase 29 rubric anchor. Dim 3 held at
85 (no regression but no actual color-system advancement); Dim 5
held at 82 (no multi-viewport / measurement). Dim 4 held at 85
(no SR fixtures / aria-describedby). These are the honest brakes
keeping the composite from drifting above the anchor evidence.

## Phase 30 recommendations (top 3, industrial-parity-focused)

1. **Multi-viewport split (2-quadrant minimum: iso + section-cut
   companion)** — single biggest parity gap with Abaqus/CAE / ANSYS
   Mechanical / Hyperworks, all of which ship 4-quadrant default.
   Even a 2-viewport split closes the Dim 5 rubric jump from 82 →
   88 anchor. Implementation: split current viewport flex container
   into a horizontal pair; pipe same WebGL scene into a second
   `<canvas>` with locked-orthogonal projection. Pair with a coord-
   readout floating panel on cursor hover (the `section-cut-readout`
   class already half-exists in `polishStyles.ts:146-159`).
   Expected Dim 5 lift: +6 to +8. Composite lift: +1.0 to +1.5.

2. **Measurement / probe-coord tools (distance / angle / coord
   readout)** — standard in every commercial CAE preprocessor;
   Hyperworks ships a docked measurement palette; Abaqus has the
   Query toolset. Implementation: extend probe-pin mechanic to
   capture two-node distance + angle; floating tooltip with
   monospace coord readout. Closes Phase 28 audit "no measurement
   tools" gap AND lifts Dim 6 from 85 → 88 by surfacing precision-
   reviewer affordances. Expected Dim 5 lift: +3, Dim 6 lift: +3.

3. **`aria-describedby` linking + screen-reader fixture coverage**
   — Phase 28 audit P29-1 sub-rec (aria-describedby) is still NOT
   shipped on AdvancedModePromo body paragraph; SR users hear only
   the dialog aria-label "advanced mode promo," missing the "you're
   in Basic mode" context. Pair with a documented keyboard-only
   navigation path + 1-2 SR fixture tests (NVDA / VoiceOver script
   transcripts) to cross the rubric Dim 4 92 anchor "keyboard-only
   navigation tested + documented; screen-reader fixtures." Expected
   Dim 4 lift: +5 to +7. Composite lift: +0.8 to +1.2.

> NOT recommended for Phase 30: more SectionFrame applications
> (Visual-tab slider/legend) without a sibling primitive use case
> — would be a single-application generalization, low ROI vs the
> Dim 5 / Dim 4 structural lifts above. Also NOT recommended:
> additional animation classes; motion vocabulary is saturated per
> Phase 28 audit and Phase 29 B + C close the named gaps without
> adding new keyframes.
