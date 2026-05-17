# Phase 22 — UX audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 21 baseline UX = 76/100.
> Blueprint UX projection: 76-82 (mid 79). Each axis is 0-100;
> composite is the unweighted mean of dimensions.

## Dimensions

### Dim 1 — Reviewer flow ergonomics (0-100)

**Score: 81/100.** Carry-forward +1 from Phase 21 (80 baseline) plus
+1 for Topbar material dropdown (Slice D). The 1-click swap path from
the top rail closes the Phase 21 T4 finding that material picker was
"scroll-buried" in the Visual tab.

Evidence:
- `frontend/src/components/Topbar.tsx` — `data-testid="topbar-
  material-select"` adjacent to the analysis-type dropdown.
- `frontend/test/Phase22D_material_legend.test.tsx` — 4 tests pin the
  dropdown's value, change handler, suppression when no options /
  showRunControls=false.
- `cmd-material-picker-open` palette entry — keyboard-driven users
  can jump to the picker without mouse hunting.

Gap to 99: the picker still doesn't surface yield/ultimate-stress
quick previews on hover, doesn't allow direct edit of a Tier 1
material's properties, and doesn't show last-used material across
sessions. None of those landed in Phase 22; legitimate carry-forward
to Phase 23+.

### Dim 2 — Animation + dynamic engagement (0-100)

**Score: 84/100.** Phase 21 score was 72 — the WebGL viewport
rendered single-frame static scenes. Phase 22 B added (a) per-frame
RAF-driven interpolation 0→1 over 220ms matched to the parent's
240ms interval, (b) section-cut clipping plane, (c) deformation
magnification 1×-100×. Reviewers can now SEE small-strain
deformation evolution rather than watching hard-cut frame swaps.

Evidence:
- `frontend/src/components/ResultMeshWebGLViewport.tsx` — `animTInterp`
  state + requestAnimationFrame loop + clippingPlanes wired into
  MeshPhongMaterial + `buildNodeCoords` magnification math.
- `frontend/test/Phase22B_viewport_depth.test.tsx` — 14 tests
  including interpolation at t=0/0.5/1, magnification scaling, UI
  toggles.

Gap to 99: no playback speed control, no scrub-to-time, no
keyboard shortcuts for next-frame, no overlay of "current frame
N/total". The animation is one-way (no reverse).

### Dim 3 — Cognitive load on first open (0-100)

**Score: 76/100.** Held flat from Phase 21. The new section-cut +
deformation controls add a row of inputs to the playback panel; a
first-time reviewer has more knobs to understand. Mitigated by
collapsible cut state (default off) and tooltip/aria labels, but
not eliminated.

Evidence:
- `frontend/src/components/ResultMeshPlaybackPanel.tsx` —
  `ViewportDepthControls` row only renders in WebGL mode (SVG
  fallback stays simple), section-cut details only appear when the
  checkbox is checked.

Gap to 99: no onboarding tour, no first-run "what does this do?"
overlay on the depth controls, no progressive disclosure of advanced
features. Phase 23+ scope.

### Dim 4 — Error-recovery clarity (0-100)

**Score: 78/100.** Held flat from Phase 21. Phase 22 didn't add or
remove any failure modes user-visible to a reviewer. Phase 22 B's
animation loop fails gracefully (when `nextFrame=null` it falls back
to single-frame render, when `playing=false` it pauses cleanly).

Evidence:
- `frontend/src/components/ResultMeshWebGLViewport.tsx:357..387` —
  animation loop early-returns on missing nextFrame.

Gap to 99: no diagnostic for "WebGL context lost" mid-session;
no error toast for failed PDF export (currently `alert()`); no
retry button on result_mesh.json fetch failures.

### Dim 5 — Novice usability (0-100)

**Score: 79/100.** +3 from Phase 21 (76). Material picker promotion
to the Topbar means a brand-new user finds the material control
without scrolling. Tab extractions don't directly impact novice
usability but they DO mean App.tsx is more maintainable, which
indirectly buys faster iteration on novice-facing copy.

Evidence:
- Topbar material dropdown — same shape as the analysis-type
  dropdown (familiar pattern reduces learning cost).
- `cmd-material-picker-open` — discoverable via Cmd-K palette.

Gap to 99: still no novice-mode toggle, still no "what is a
material?"-style inline help, still no smoke-test fixture for
brand-new users.

## Composite

| Dim | Phase 21 | Phase 22 | Delta |
|---|---|---|---|
| Reviewer flow | 80 | 81 | +1 |
| Animation engagement | 72 | 84 | +12 |
| Cognitive load | 76 | 76 | 0 |
| Error recovery | 78 | 78 | 0 |
| Novice usability | 76 | 79 | +3 |
| **UX composite** | **76.4** | **79.6** | **+3.2** |

**UX axis: 79.6/100.** Inside blueprint band (76-82, mid 79). Not at
99 — the gap is named honestly per the absolute-honesty contract.
Phase 22 B's animation slider was the single biggest UX lift; tab
extractions delivered no direct UX signal.

Not signed validation; not benchmark agreement.
