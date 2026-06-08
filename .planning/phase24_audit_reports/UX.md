# Phase 24 — UX audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 23 baseline UX = 80.8/100.
> Blueprint UX projection: 82-84 (mid 83.0).

## Dimensions

### Dim 1 — Reviewer flow ergonomics (0-100)

**Score: 89/100.** +3 from Phase 23 (86). Phase 24 D closes the
"#1 industrial-CAE feature gap" Phase 23 retro named at the end of
its Dim 1 section: multi-pick / probe list. A reviewer can now
click a node → see HUD → click "+ Pin" → click next node → repeat
up to 8 entries → see the comparison table side-by-side. Each
entry has a remove button; clear-all button when ≥1 entry.

Evidence:
- `frontend/src/components/probeList.ts` — pure-function reducer
  (addProbeEntry FIFO at 8, removeProbeEntry, clearAllProbes).
- `frontend/src/components/ProbeListPanel.tsx` — comparison table
  with scientific-notation x/y/z/value columns.
- `Phase24D_probe_list.test.tsx` — 18 tests including D:-2
  anti-gaming guard (pin order [7, 42, 99, 11, 3] renders in
  PIN order, NOT sorted by label, NOT by array index).
- Wired in ResultMeshPlaybackPanel; activePick state forwards
  from viewport `onNodePicked` callback.

Gap to 99: still no node-by-label search box, no probe-list
export (CSV / clipboard), no diff column (probe A vs probe B
delta). Future-phase scope.

### Dim 2 — Animation + dynamic engagement (0-100)

**Score: 84/100.** Held flat from Phase 23 (84). No animation
features added in Phase 24.

Gap to 99: see Phase 22 / 23 list (playback speed, scrub-to-time,
keyboard shortcuts, reverse).

### Dim 3 — Cognitive load on first open (0-100)

**Score: 78/100.** +3 from Phase 23 (75). Phase 24 B introduces a
4-step progressive-disclosure tour that explicitly walks new
reviewers through the Phase 22-23 control surfaces (component
switcher, threshold filter, node-pick, section cut). LocalStorage
persists dismissal so the tour fires exactly once. Skip-tour link
is non-modal.

Honest miss within this dim: Phase 24 D adds yet another panel
(probe list), which is the cognitive-load cost. The tour mitigates
new-user load but the probe list adds one more thing on screen for
returning users. Net +3 (recovers the Phase 23 -1 regression AND
adds 2 points from the tour) but not the full +5 it could be with
also a basic/advanced mode toggle.

Evidence:
- `frontend/src/onboardingTour.ts` — 4-step pure-function state
  machine with persistence.
- `frontend/src/components/OnboardingTour.tsx` — overlay with
  progress dots, "Got it" advance, "Skip tour" link.
- `Phase24B_onboarding_tour.test.tsx` — 20 tests including B:-1
  anti-gaming guard (no auto-advance on timer).

Gap to 99: basic-mode/advanced-mode toggle, inline tooltips on
controls, contextual help links.

### Dim 4 — Error-recovery clarity (0-100)

**Score: 80/100.** +1 from Phase 23 (79). Phase 24 D's ProbeListPanel
shows an explicit empty state ("No pinned probes. Click a node in
the viewport, then '+ Pin'.") and disables the "+ Pin" button with
visual / aria-disabled cues when active pick is missing, already
pinned, or list is at capacity. Failure modes surface in-place.

Evidence:
- ProbeListPanel empty-state testid `probe-list-empty`.
- "+ Pin" button has `aria-disabled` + `cursor: not-allowed` + 50%
  opacity when disabled.

Gap to 99: WebGL context-loss recovery still mock-only (Phase 21
carry-forward), no probe-list-overflow toast, no save/restore
probe set across sessions.

### Dim 5 — Novice usability (0-100)

**Score: 82/100.** +2 from Phase 23 (80). The onboarding tour
directly targets novices; the first-load overlay introduces every
new Phase 22-23 affordance with plain-language explanations
attached to a `shippedInPhase` provenance tag.

Evidence:
- 4 tour steps each have a body sentence explaining WHAT the
  surface does and WHEN to use it (e.g. "Click anywhere on a
  mesh node to open the field-probe HUD").

Gap to 99: still no "Replay tour" affordance in the settings (the
component supports `forceShow={true}` but no UI invokes it),
still no inline help dialog, still no contextual examples.

## Composite

| Dim | Phase 23 | Phase 24 | Delta |
|---|---|---|---|
| Reviewer flow | 86 | 89 | +3 |
| Animation engagement | 84 | 84 | 0 |
| Cognitive load | 75 | 78 | +3 |
| Error recovery | 79 | 80 | +1 |
| Novice usability | 80 | 82 | +2 |
| **UX composite** | **80.8** | **82.6** | **+1.8** |

**UX axis: 82.6/100.** Inside blueprint band (82-84) at the LOW
end (within band). The +1.8 lift is driven by the multi-probe
reviewer-flow win + onboarding-tour cognitive-load recovery;
animation engagement held flat (no Phase 24 work). Documented
verbatim per 绝对诚实客观.

Not signed validation; not benchmark agreement.
