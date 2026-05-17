# FM-04a Phase 30 — UI Audit · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Scoring per `.planning/audits/RUBRIC.md`
> (v1.0). Phase 29 UI composite baseline = **86.0** (held flat per
> D:-1 retroactive guard; mean of 90/89/85/85/82/85).
>
> Phase 30 B (`a054995`) shipped `CompanionViewport.tsx` (233 LOC)
> + `companionViewportStorage.ts` (113 LOC) + a "Compare cuts"
> toggle in `ResultMeshPlaybackPanel.tsx` via flex column / flex
> row restructure (probe-list lifted out of `primary-viewport-slot`).
> Toggle gated by `shouldShowFeature(uiMode, 'companion-viewport')`
> via additive `ADVANCED_FEATURE_IDS` extension (`uiMode.ts:27,34`).
> Phase 30 C (`e935c63`) shipped `CoordReadoutTooltip.tsx` (102 LOC)
> + 30 Hz throttled hover-raycast in `ResultMeshWebGLViewport.tsx`
> + `role="alert"` / `aria-live="assertive"` corrupted-key
> probe-list toast on case mount (existing-key + parse-fail path;
> missing-key first-load intentionally silent).
>
> Both structurally load-bearing toward Dim 5 industrial parity
> (rubric v1.0 "88 anchor") and Dim 4 a11y semantic split. Bounded
> lift because (a) 2-quadrant layout is advanced-mode gated, (b)
> companion is read-only, (c) coord-readout WebGL→tooltip is
> unit-sliced in jsdom (no real-WebGL E2E).

## Sub-axes

### 1. Micro-interaction polish + animation quality: **90/100**

- Evidence:
  - Motion vocabulary preserved verbatim — `git diff a2e3b7c..1b34f5e
    -- polishStyles.ts SectionFrame.tsx` returns EMPTY.
  - Corrupted-key toast REUSES `POLISH_CLASS_RESTORED_TOAST`
    (`ResultMeshPlaybackPanel.tsx:437`) → inherits the 200 ms
    ease-out `fm04a-restored-toast-fade-in` keyframe
    (`polishStyles.ts:70-73,102`) + the reduce-motion `@media`
    block (`polishStyles.ts:161-167`).
  - CompanionViewport's section-cut readout reuses
    `POLISH_CLASS_SECTION_CUT_READOUT` (`CompanionViewport.tsx:42,172`).
  - CoordReadoutTooltip intentionally has NO animation
    (`CoordReadoutTooltip.tsx:50-82`); a 30 Hz cursor-follow with
    entry/exit transitions would fight the motion budget.
    `pointerEvents: none` (line 67) keeps it ephemeral.
- Anchor: rubric 90 anchor (Phase 29 B+C chevron+accordion+promo).
  Phase 30 added NEW surfaces strictly reusing existing
  primitives — none added, none regressed. **Held at 90.** 99
  anchor (spring physics / haptics) out of scope.

### 2. Visual hierarchy + typography: **89/100**

- Evidence:
  - CompanionViewport header: 3-slot grid, `fontWeight: 700` +
    `textTransform: uppercase` + `letterSpacing: 0.04em` on
    "Companion view" label (`CompanionViewport.tsx:106-110`) —
    matches existing trust-section header grammar.
  - Coord-readout: 2-column grid, muted axis labels (`#94a3b8`)
    vs primary values, monospace 0.66 rem, fixed 3-decimal
    precision (`CoordReadoutTooltip.tsx:70-80`) — engineer-grade.
  - Compare-cuts toggle adopts existing viewport-toggle style
    (`ResultMeshPlaybackPanel.tsx:566-578`) — same rounded-4 /
    accent-on / muted-off pattern as `viewport-toggle-webgl`.
  - HONEST GAP: SectionFrame primitive UNCHANGED — Visual-tab
    slider/legend still doesn't flow through it.
- Anchor: rubric 90 anchor (Phase 29 B SectionFrame). Phase 30
  added new surfaces matching the type-ramp vocabulary but did
  NOT push SectionFrame into untouched areas. **Held at 89.**

### 3. Color system + tonal discipline: **85/100**

- Evidence:
  - No new color tokens. CompanionViewport uses
    `var(--text-secondary)` / `var(--text-primary)` /
    `var(--border)` / `var(--accent)` exclusively
    (`CompanionViewport.tsx:101,108,135,193`).
  - CoordReadoutTooltip uses hard hex `#e2e8f0` / `#94a3b8` /
    `rgba(2,6,23,0.92)` (`CoordReadoutTooltip.tsx:60-64,75`) —
    same values already in `polishStyles.ts:148-150`. Reuse, not
    new palette.
  - HONEST GAP: corrupted-toast adds inline hard-string overrides
    `color: '#fda4af'` + `borderColor: 'rgba(239, 68, 68, 0.55)'`
    (`ResultMeshPlaybackPanel.tsx:441-443`) instead of threading
    `var(--danger)` / `statusTone('warning')`. One MORE hard-string
    application — neutral (no regression) but no advancement.
- Anchor: rubric 90 anchor "+ No regression in Phase 29 ship."
  Phase 30 confirms no regression but adds a hard-string. **Held
  at 85** with the same Phase 29 honest-brake logic.

### 4. Accessibility (a11y): **86/100**

- Evidence:
  - Corrupted-key toast carries `role="alert"` +
    `aria-live="assertive"` (`ResultMeshPlaybackPanel.tsx:438-439`)
    — semantically distinct from routine "restored N probes" which
    retains `role="status"` + `aria-live="polite"` (lines 410-411).
    Correct per WAI-ARIA: corruption is higher-stakes interruptive;
    restoration is informational. Genuine advancement vs Phase 29's
    single-tier toast set.
  - Coord-readout intentionally uses `role="status"` +
    `aria-live="off"` (`CoordReadoutTooltip.tsx:52-53`) — honest:
    a 30 Hz coord stream announced by SR would be cacophonous.
    `aria-live="off"` IS the correct answer for high-rate cursor
    tracking.
  - CompanionViewport section-cut controls carry
    `aria-label="Companion section-cut axis"` (line 122) + position
    (line 147) + flip half (line 202) — distinguishable from primary.
  - Compare-cuts toggle has `aria-pressed={companionViewportActive}`
    (`ResultMeshPlaybackPanel.tsx:544`).
  - HONEST GAP: NO new focus-trap, NO SR fixtures, keyboard-only
    nav path for 2-quadrant layout NOT documented; Phase 29 audit
    P29-1 `aria-describedby` on promo body remains UNSHIPPED.
- Anchor: rubric 85 anchor (Phase 29 C focus-trap). Phase 30 adds
  semantically distinct `role="alert"` + correct `aria-live="off"`
  decision — genuine but bounded. Held below 92 (no SR fixtures,
  no documented keyboard nav). **Interpolated 86.**

### 5. Industrial-software parity: **86/100**

- Evidence (the big lift — rubric Dim 5 88-anchor axis):
  - 2-quadrant viewport split SHIPS
    (`ResultMeshPlaybackPanel.tsx:650-861` flex-row +
    `CompanionViewport.tsx` 233 LOC). Side-by-side primary +
    companion when Compare-cuts is on (D:-1 additive).
  - Hyperworks-style floating coord readout SHIPS
    (`CoordReadoutTooltip.tsx`) wired through
    `ResultMeshWebGLViewport.tsx:439-485` (throttled raycast +
    bounding-box-anchored screen-space coords).
  - Rubric 88 anchor (line 230) reads "+ Multi-viewport split
    (4-quadrant default); + measurement/coord tools; +
    collapsible left/right rails." Phase 30 delivers 2 of 3
    partially: 2-quadrant (not 4), coord tools yes, no rails.
  - HONEST SCOPE NARROWING:
    1. **Advanced-mode gated**
       (`ResultMeshPlaybackPanel.tsx:304`, `uiMode.ts:27,34`).
       Basic-mode reviewers — the default — NEVER see the
       2-quadrant lift unless they flip both Advanced AND
       Compare-cuts.
    2. **Companion is read-only** — `onNodePicked` intentionally
       omitted (`CompanionViewport.tsx:18-21` + lines 219-229
       pass no `onNodePicked`). Reviewer cannot pin a probe
       from the companion. Honest scope to avoid double-write,
       but Abaqus/CAE / Hyperworks let any viewport pin probes.
    3. **Coord-readout integration is tested in pieces, not
       end-to-end.** jsdom cannot exercise real `THREE.Raycaster`
       (`ResultMeshWebGLViewport.tsx:468-470`) → cursor-to-mesh
       hit path verified only by code review. Real-WebGL
       playwright E2E remains deferred.
    4. **No 4-quadrant default** — Abaqus/CAE / ANSYS Mechanical
       ship 4-quadrant default; Phase 30 ships 2-quadrant opt-in.
    5. **No collapsible left/right rails** — third sub-bullet
       unshipped.
- Anchor: rubric 82 anchor was Phase 29; 88 anchor requires
  4-quadrant default + measurement/coord + collapsible rails.
  Phase 30 ships 2-quadrant opt-in + coord-readout (the two
  biggest), no rails. Honestly interpolating between 82 and 88:
  **86**. The +4 lift reflects two genuine industrial-parity
  primitives while withholding 2 points for advanced-gating +
  read-only + no 4-quadrant + no rails.

### 6. Density + reviewer ergonomics: **86/100**

- Evidence:
  - Probe-list LIFTED OUT of `primary-viewport-slot` into its own
    row under `viewport-row` flex column
    (`ResultMeshPlaybackPanel.tsx:862-868` comment + line 868
    `data-testid="probe-list-row"`). Pre-Phase 30 the table was
    nested inside `primary-viewport-slot`, which would have
    collapsed under one column when Compare-cuts opens; now it
    sits below both viewports as its own width-full row.
  - Compare-cuts toggle is a single button (lines 540-582), not
    a modal — highest-density way to expose a layout-mode switch.
  - Coord-readout monospace + 3-decimal precision
    (`CoordReadoutTooltip.tsx:76,78,80`) matches Hyperworks
    reference precision — density-correct for engineering data.
  - Companion header is COMPACT — single 24-px row, axis selector
    + 120-px slider + flip button (`CompanionViewport.tsx:91-207`).
  - HONEST GAP: probe table still fixed-width; drag-to-resize and
    density toggle (compact / comfortable) remain unshipped — both
    rubric Dim 6 92-anchor items. The 2-quadrant flex-row uses
    `flex: 1` on both panes (`CompanionViewport.tsx:84`,
    `ResultMeshPlaybackPanel.tsx:659-670`) → fixed 50/50.
- Anchor: rubric 85 anchor (Phase 29 B per-section collapse).
  Phase 30 adds a layout-mode toggle that LIFTS probe-list out of
  the viewport-slot — concrete ergonomics Phase 29 didn't touch.
  Held below 92 (drag-to-resize + density toggle unshipped).
  **Interpolated 86.**

---

## Composite UI score: **87.0/100**

(90 + 89 + 85 + 86 + 86 + 86) / 6 = 522 / 6 = **87.0**

## Phase-30 lift over Phase 29 UI (86.0): **+1.0**

Phase 29 audit predicted multi-viewport split lift "+1.0 to +1.5
composite." Phase 30 lands at the LOWER bound:

| Phase 29 audit rec | Phase 30 delivery |
|---|---|
| Multi-viewport split (2-quadrant min) | Phase 30 B — advanced-gated, read-only companion (honest scope) |
| Coord-readout floating panel | Phase 30 C — 30 Hz throttled raycast → CoordReadoutTooltip |
| ~~`aria-describedby` + SR fixtures~~ | NOT shipped — deferred to Phase 31 |

Phase 30 closed 2 of 3 named Phase 29 recs. The +1.0 sits at the
LOWER bound: Dim 5 +4 (not +6-8) for 2-quadrant-not-4 + advanced
gated + read-only + no rails; Dim 4 +1 for semantic ARIA correct
but no SR fixtures / keyboard-nav doc; Dim 6 +1 for probe-list
lift but no drag-to-resize / density toggle.

Anti-gaming guard: composite did NOT cross 88 (rubric Dim 5
multi-viewport anchor). Three independent honest brakes hold it
at 87.0: Dim 1/2/3 ALL held flat (no motion vocab extension;
SectionFrame substrate unchanged; color tokens unchanged — and
corrupted toast added a hard-string color); Dim 5 honest-gated
by advanced-mode + read-only + 2-not-4 + no rails; Dim 6 honest-
gated by no resize + no density toggle.

## Top 5 honest gaps carried forward to Phase 31

1. **Make Compare-cuts visible in basic-mode (or document the
   gating rationale).** Default-mode reviewers never see the
   2-quadrant lift. Lifting the gate brings Dim 5 closer to 88.
   Expected Dim 5 lift: +1 to +2.

2. **Wire companion `onNodePicked` to a shared probe list (or
   document why not).** Read-only companion leaves the parity
   gap with Abaqus/CAE / Hyperworks. Expected Dim 5 lift: +1.

3. **Real-WebGL playwright E2E for the coord-readout path.**
   The raycaster→tooltip integration is tested in pieces; the
   cursor-to-mesh hit path is verified only by code review.
   Process-maturity lift; unlocks real Dim 5 confidence.

4. **Token the warning-tinted corrupted-toast colors + close the
   Phase 29 named `statusTone(fail)` hard-string.** Would
   finally cross Dim 3 85 → 88 anchor. Expected Dim 3 lift: +3.

5. **Drag-to-resize between primary and companion + density
   toggle (compact / comfortable) on probe-list row.** Would
   cross Dim 6 85 → 92 anchor. Expected Dim 6 lift: +4 to +5.

> Phase 31 composite math: Dim 3 85→88 + Dim 5 86→89 + Dim 6
> 86→90 = +7 across 3 axes → +1.17 composite, putting Phase 31
> at ~88.2/100. The 88-90 UI band is where the honest contract
> starts approaching the ~95 ethical ceiling; Phase 31-33 should
> aim for 88-90 max and reserve remaining points for external-
> validation surfaces (NOT under this contract).
