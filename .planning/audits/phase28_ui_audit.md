# FM-04a Phase 28 — UI Audit

> Honest scoring contract carried verbatim from Phase 18-27.
> Tier 1 / Tier 2 engineering candidate review tool; the comparison bar
> is "top-industrial reviewer dashboard" (Abaqus/CAE result-inspection
> mode, Hyperworks Tcl-era → modern web parity), NOT a full preprocessor.
> Phase 27 UI baseline ~78.5; honest expected lift +3 to +6.

## Dimensions

### 1. Micro-interaction polish + animation quality: **80/100**
- Evidence:
  - Probe-row mount fade 200ms + 6px lift; unmount fade 150ms ease-in -6px translateY (`polishStyles.ts:61-80`). Asymmetric exit-faster-than-enter is correct Apple HIG pattern.
  - Restored toast fade-in 200ms ease-out + 8px translateY (`polishStyles.ts:69-72, 97`). Same easing family as probe rows = cohesive motion language.
  - Onboarding tour fade+slide 200ms ease-out (`OnboardingTour.tsx:148-155`). Same 200ms anchor.
  - Auto-dismiss timer 4s (`ResultMeshPlaybackPanel.tsx:181`) matches Material Design "informational snackbar" duration (4-10s band).
  - prefers-reduced-motion covered for all three new classes (`polishStyles.ts:145-151`).
- Gap vs industrial bar:
  - Abaqus/CAE result-mode shows synchronized animation across panels (probe pin → table row → viewport callout); here the toast/row/promo are independent timelines, no choreographed entrance.
  - Advanced promo dialog has NO animation — appears instantly while everything else around it fades. Visual discontinuity vs Hyperworks "Property Editor" modal class which slides in.

### 2. Visual hierarchy + typography: **76/100**
- Evidence:
  - OperatorStatusPanel uses tiered type ramp: 0.68rem uppercase tracked label / 0.88rem 650-weight value / 0.72rem detail (`OperatorStatusPanel.tsx:60-63`). Clean 3-tier system.
  - Eyebrow labels with letterSpacing 0.5px uppercase consistently across promo (`AdvancedModePromo.tsx:179-184`) and tour (`OnboardingTour.tsx:191-197`).
  - System font stack on cards (`system-ui, -apple-system`) — correct for native feel.
- Gap vs industrial bar:
  - No clear "title vs section header vs item label" semantic separation in Visual tab — App.tsx Visual tab area composes header/sliders/legend ad-hoc, not via a shared SectionFrame.
  - Trust strip badges all use same chip shape regardless of severity — Abaqus uses distinct shapes (octagon for FAIL, rounded rect for PASS) to encode hierarchy non-color-redundantly.
  - Claim-impact badges and "not signed validation" red pill (`OperatorStatusPanel.tsx:53`) are visually identical-weight to neutral chips — danger doesn't dominate visually.

### 3. Color system + tonal discipline: **78/100**
- Evidence:
  - 4-tone vocabulary `accent/warning/danger/muted` consistently consumed across 7 view-model sections (`trustCenterViewModel.ts:32-38`, used in `buildTrustStrip:74-93`, `buildRuntimeSection:144`, `buildEvidenceSection:197`, `buildValidationSection:254`).
  - Toast blue `#93c5fd` on dark slate-blue accent (`polishStyles.ts:88-91`) ties into the candidate-spine blue used in viewport overlays.
  - Gradient slider track blue→green→orange (`polishStyles.ts:114, 119`) matches viewport legend gradient — single color story across reviewer surfaces.
  - Promo blue switchButton `#2563eb` matches dot-progress active state in tour (`OnboardingTour.tsx:114`).
- Gap vs industrial bar:
  - 4 tones is parsimonious but flat — Abaqus/CAE uses 6+ semantic categories (info/pass/warn/critical/blocked/info-secondary) on its Job Monitor; reviewer dashboards expecting accreditation context (DO-160, ISO) typically need a "blocked-by-input" tone distinct from "warning."
  - statusTone(fail) → danger via hard string match; any new ccx status text (e.g. "abort") silently falls to warning (`trustCenterViewModel.ts:35-37`). Robust industrial dashboards use semantic enums + explicit fallback.
  - No dark/light theme — the entire UI assumes dark slate background. Hyperworks/Mechanical both ship light themes as default; reviewer printouts assume light.

### 4. Accessibility: **84/100**
- Evidence:
  - Restored toast `role="status"` + `aria-live="polite"` + dismiss button `aria-label="Dismiss restored probes notification"` (`ResultMeshPlaybackPanel.tsx:295-308`). Correct pattern for non-modal informational toast.
  - Advanced promo `role="dialog"` + `aria-label="advanced mode promo"` + `aria-live="polite"` (`AdvancedModePromo.tsx:113-116`).
  - OnboardingTour `role="dialog"` + `aria-label="onboarding tour"` (`OnboardingTour.tsx:94`).
  - prefers-reduced-motion covers all 3 new animations + tour (`polishStyles.ts:145-151`, `OnboardingTour.tsx:156-160`).
  - Probe remove button `aria-label` per node (`ProbeListPanel.tsx:239`).
- Gap vs industrial bar:
  - Promo dialog has NO `aria-describedby` linking to the body paragraph; screen readers will announce only the aria-label "advanced mode promo," missing the "you're in Basic mode" context.
  - Promo is **not focus-trapped** — Tab can leave the modal even though backdrop is visible. Industrial dashboards exposing modal dialogs (Abaqus job-edit) trap focus.
  - No skip-link / keyboard shortcut surfacing in tour — Hyperworks tour panels typically expose `?` shortcut.
  - Toast auto-dismiss in 4s; SR users may not finish reading. WCAG 2.2 "Enough Time" suggests pause/extend control (have dismiss only, not pause).

### 5. Industrial-software parity: **70/100**
- Evidence:
  - Trust strip + 7-section status panel matches Abaqus/CAE "Job Monitor + Visualization Module" mental model.
  - View-model purity (`trustCenterViewModel.ts:74-93`) approximates Hyperworks "templated session report" — same input → byte-equal output.
  - Probe table with Δ-vs-baseline column (Phase 26 C, retro 26) + Unicode minus is reviewer-grade.
  - Gradient slider matching legend = ANSYS Mechanical-style precision-friendly affordance.
- Gap vs industrial bar:
  - **No multi-viewport layout** — Abaqus/CAE ships 4-quadrant view (iso/top/front/side) by default; this is a single-viewport playback panel.
  - **No keyboard-driven probe pinning** — Hyperworks lets reviewer P-click + arrow-step through nodes; here probes only added via canvas click.
  - **No save-state filename in titlebar** — Abaqus shows `model.cae [modified]`; no equivalent here for the case being reviewed.
  - **No measurement tools** (distance/angle/coord-readout floating panel) — standard in every commercial CAE preprocessor.
  - **No undo stack visible** — reviewer can't undo a probe pin or section-cut adjustment; commercial CAE has 50-deep undo histories.
  - **Promo + tour both modal** — gating onboarding UX; commercial software either splits into non-modal docked panel or shows once and hides forever. Two sequential modals (tour → promo) is more friction than Hyperworks "Getting Started Page" pattern.

### 6. Density + reviewer ergonomics: **77/100**
- Evidence:
  - Trust strip horizontal scroller compresses 7 items into a strip without truncation; toneBackground at 8% alpha (`OperatorStatusPanel.tsx:33-35`) keeps strip from competing with viewport.
  - 12px-padded section cards on dark backdrop (`OperatorStatusPanel.tsx:70`) → comfortable density.
  - Probe table monospace columns + Δ column = grid-aligned scan.
  - Gradient slider gives proportional value sense (Phase 27 C) — better than plain track.
- Gap vs industrial bar:
  - **App.tsx is still 1596 LOC** (`wc -l`), and the Visual tab composes inline — no shared SectionFrame contract. Abaqus tabs are uniform-density-bound.
  - **No collapse/expand** on the 7 trust sections — reviewer scanning a long page can't fold "Overview" once they're past it. Industrial reviewer tools default to collapsible accordions.
  - **No column-resize on probe table** — fixed-width monospace cells assume label≤4 digits and scientific notation fits; long node labels (>6 digits) will overflow.
  - **Restored toast at top-right absolute** (`polishStyles.ts:83-85`) is inside a `position: relative` parent (viewport section), but the parent isn't explicitly marked `position:relative` in the surrounding section style — risk of toast escaping the viewport bounds on some layouts.

## Composite UI score: **77.5/100**

(80 + 76 + 78 + 84 + 70 + 77) / 6 = 77.5

## Phase-28 lift over Phase 27 UI baseline (~78): **-0.5**

Honest reading: Phase 28 shipped the three named polish affordances
(row exit / restored toast / advanced promo) but ALSO surfaced parity
gaps that Phase 27's score did not weigh — specifically the missing
multi-viewport, undo stack, focus trapping, and aria-describedby. The
new affordances ARE additive on Dim 1 (motion cohesion +2-3 net) and
Dim 4 (toast a11y attributes well-formed +2), but Dim 5 (industrial
parity) gets HONEST attention here that Phase 27 implicitly punted on,
revealing -2 to -3 of latent debt.

Net Phase 28 honest delta: **-0.5 to +0.5 band**. Picked **77.5**
(effectively flat vs Phase 27 ~78). This is consistent with the retro
guidance "do NOT score above 90 without parity evidence vs Abaqus/CAE"
— Phase 28 added incremental polish but the 99/100 target needs Dim 5
structural lifts (multi-viewport, undo, measurement, focus trap), not
more individual affordances.

> Anti-gaming guard: the +3 to +6 expectation in the audit brief is
> reasonable IF the auditor only weighs the new affordances. Honest
> auditing requires weighing what's STILL ABSENT against industrial
> bar. Phase 28 didn't move the structural gaps.

## Phase 29 recommendations (top 3, industrial-parity-focused)

1. **Focus trap + aria-describedby on AdvancedModePromo + OnboardingTour modals** — both currently violate WCAG 2.4.3 focus order
   inside `role="dialog"`. Wire a focus-trap hook (or `inert` on
   background) + add `aria-describedby` linking to body text. This is
   a Dim 4 lift +5-8 and removes the "modal escapes" issue.
   Concrete: `AdvancedModePromo.tsx:111-150` needs ref + Tab handler;
   add `<p id="promo-body">` and `aria-describedby="promo-body"`.

2. **Reviewer-Frame primitive + collapsible 7-section accordion** —
   extract a `<SectionFrame title icon collapsible defaultOpen>` from
   the inline Trust Center markup (`App.tsx:851-967` style) so all 7
   sections share density / header / collapse behavior. Closes the
   "App.tsx 1596 LOC" debt AND matches Abaqus collapsible-tree pattern.
   Dim 2 +3-5 and Dim 6 +3-5 simultaneously. Honest LOC reduction win.

3. **Measurement tools + multi-viewport split (iso/top/front)** —
   the single biggest "looks like CAE" lift. Even a 2-viewport split
   (iso + section-cut companion view) closes the most-cited gap with
   Abaqus/CAE visualization mode. Pair with a coord-readout floating
   panel on cursor hover (`section-cut-readout` already half-exists —
   `polishStyles.ts:130-143`). Dim 5 +8-12 in one phase, gets composite
   into the low-80s honestly.

> NOT recommended for Phase 29: more entrance/exit animations or
> additional polishStyles classes. The motion language is already
> cohesive; further additions hit diminishing returns vs structural
> parity work.
