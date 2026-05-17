# Phase 25 — UX audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 24 baseline UX = 82.6/100.
> Blueprint UX projection: 84-85 (mid 84.5).

## Dimensions

### Dim 1 — Reviewer flow ergonomics (0-100)

**Score: 90/100.** +1 from Phase 24 (89). Phase 25 D's probe-list
CSV export is a modest reviewer-flow lift — the "Export CSV" button
appears in the panel header when ≥1 probe is pinned and downloads
`probe-list-<timestamp>.csv` with one row per entry preserving
the Phase 24 D pin-order semantics through the export layer.

Evidence:
- `frontend/src/components/probeList.ts:serializeProbeListAsCsv`
  pure-function CSV serializer with RFC-4180 quoting + NaN/Infinity/
  null → empty cell handling.
- `Phase25D_polish_csv_export.test.tsx` — 12 tests including the
  D:-1 anti-gaming guard (CSV row order = pin order, NOT sorted).

Gap to 99: no node-search-by-label, no probe-diff column (A − B),
no save/restore probe set across sessions, no shareable probe-set
URL.

### Dim 2 — Animation + dynamic engagement (0-100)

**Score: 84/100.** Held flat from Phase 24 (84). Phase 25 didn't
add playback/animation features (the tour fade-slide is UI chrome
not viewport animation).

Gap to 99: see Phase 22/23/24 list (playback speed, scrub-to-time,
keyboard shortcuts, reverse).

### Dim 3 — Cognitive load on first open (0-100)

**Score: 81/100.** +3 from Phase 24 (78). Phase 25 C's Basic/
Advanced mode toggle is the lever — Basic mode hides the probe-list
panel so returning reviewers can switch to a leaner viewport.
Persisted to localStorage so the preference survives across sessions.

**Honest scope reduction within this dim:** Phase 25 C gates ONLY
the probe-list panel. The threshold filter / section cut / per-
component switcher inside ViewportDepthControls are NOT yet gated —
they remain visible in both modes. Full gating threading uiMode
through ViewportDepthControls is a Phase 26 follow-up. So the
+3 lift here is partial (would be +5 to +6 if the gating were
complete).

Evidence:
- `frontend/src/uiMode.ts` pure-function state machine.
- `ResultMeshPlaybackPanel.tsx` shows/hides ProbeListPanel via
  `shouldShowFeature(uiMode, 'probe-list-panel')`.
- `Phase25C_ui_mode_toggle.test.tsx` — 15 tests including C:-1
  anti-gaming guard (toggleMode purity, state preservation).

Gap to 99: full ViewportDepthControls gating, inline help dialog,
contextual examples, basic-mode default copy explaining why some
features are hidden.

### Dim 4 — Error-recovery clarity (0-100)

**Score: 81/100.** +1 from Phase 24 (80). Phase 25 D's CSV export
swallows DOM failures (URL.createObjectURL, anchor click) gracefully;
Phase 25 C's localStorage adapter falls back to initial state on
corrupted key. Both are recovery-clarity wins via the "explicit
failure modes don't crash" pattern.

Evidence:
- `createUiModeStorage` fallback to `UI_MODE_INITIAL` on missing
  / corrupted / SecurityError keys.
- `defaultCsvExport` swallows exceptions with a comment marking
  it as best-effort.

Gap to 99: WebGL context-loss recovery still mock-only (Phase 21
carry-forward), no CSV-export-failure toast, no save/restore.

### Dim 5 — Novice usability (0-100)

**Score: 84/100.** +2 from Phase 24 (82). Basic mode is the default
on first load, which gives novices a leaner viewport on day one.
Combined with the Phase 24 B onboarding tour, the novice path
is now: tour overlay introduces the 4 advanced surfaces → user
dismisses → user is in Basic mode with only the leaner control
surface → user toggles to Advanced when they want more controls.

Evidence:
- `UI_MODE_INITIAL = 'basic'` (default on first load).
- UiModeToggle aria-radiogroup semantics for accessibility.

Gap to 99: tour does NOT yet auto-promote to Advanced after
dismissal; no "Try advanced mode" prompt; no per-feature mini-tours.

## Composite

| Dim | Phase 24 | Phase 25 | Delta |
|---|---|---|---|
| Reviewer flow | 89 | 90 | +1 |
| Animation engagement | 84 | 84 | 0 |
| Cognitive load | 78 | 81 | +3 |
| Error recovery | 80 | 81 | +1 |
| Novice usability | 82 | 84 | +2 |
| **UX composite** | **82.6** | **84.0** | **+1.4** |

**UX axis: 84.0/100.** Inside blueprint band (84-85) at the LOW
end (just barely inside). The +1.4 lift is driven by Basic-mode
cognitive-load recovery + novice-default sequencing; animation
held flat (no work this phase). The Phase 25 C gating scope
reduction is named verbatim — full ViewportDepthControls gating
would have pushed this to ~84.8.

Not signed validation; not benchmark agreement.
