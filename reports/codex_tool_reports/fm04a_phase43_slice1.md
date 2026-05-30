# FM-04a Phase 43 Slice 1 — Codex review arc (industrial CAE chrome)

> ADR-026 risk-tier: cross-≥3-file frontend change (9 source + 3 test files).
> Relay: 86gs gpt-5.4 xhigh primary; CRS effort=high fallback when the relay
> degraded. Round cap = 3 (R0 + 2 fix iterations). 绝对诚实客观.

## Scope (from the Phase 43 discovery audit)

Phase 43 theme: **industrial CAE chrome + cinematic result reveal** — close the
structural gaps that made the workbench read as a "web app dressed as CAE". Slice
1 = the 4 highest-leverage, zero-App.tsx-LOC items:

| Rank | Item | Files |
|---|---|---|
| 1 | ModeSelector de-Tailwind → tokenized dark-glass HUD | `ModeSelector.tsx`, `index.css` (pulse keyframe + reduced-motion) |
| 2 | ViewportNavGizmo (X/Y/Z triad + Iso/Top/Front/Right/Fit) | NEW `ViewportNavGizmo.tsx` + `viewportNavPresets.ts`; `ResultMeshWebGLViewport.tsx` setView seam |
| 3 | HeroPeakReadout headline peak banner | NEW `HeroPeakReadout.tsx` + `heroPeakFormat.ts`; `ResultMeshPlaybackPanel.tsx` mount |
| 6 | Visual-grid rebalance (WebGL hero, iframe secondary) | `App.tsx` gridTemplateRows 1:1 string edit |

The ModeSelector overlay floats over the intentionally-dark WebGL canvas, so it
(and the gizmo) are styled as **dark-glass HUDs**, not warm-light cards. Tests
are additive in `frontend/test/`. App.tsx held at **1498** (<1500 pin).

A pre-review fix: ViewportNavGizmo/HeroPeakReadout each exported a non-component
value (object const / function), tripping `react-refresh/only-export-components`
(+2 over the eslint baseline). Resolved per repo convention by extracting the
pure data/logic into sibling `.ts` modules (`viewportNavPresets.ts`,
`heroPeakFormat.ts`) — eslint back to the byte-identical 70 baseline.

## R0 — 86gs gpt-5.4 xhigh · CHANGES_REQUIRED · 2×P2 (non-security) · both FIXED

- **R0-P2#1 — hero readout reported the wrong quantity in tensor views**
  (`ResultMeshPlaybackPanel.tsx`). When a frame carries `stressTensor` and the
  legend dropdown switches off von Mises, the viewport colors by `fieldComponent`
  but the banner still showed `summary.valueMax` (the scalar path) → the headline
  could read von Mises while the plot showed σxx.
  **FIX:** `selectActiveFieldPeak` (in `heroPeakFormat.ts`) recomputes the peak of
  the **active** component via the same `componentValue` path the viewport uses;
  wired through a `heroField` memo in RMPP. Pinned by unit tests.

- **R0-P2#2 — Fit/Home framed the filtered subset, not the whole model**
  (`ResultMeshWebGLViewport.tsx`). `buildBufferGeometry(..., {valueFilter})`
  computes `bounds` from only the retained elements; caching those made Fit zoom
  to a threshold-filtered hotspot (and no-op if the filter emptied the mesh).
  **FIX:** when a filter is active, recompute bounds from the **unfiltered** model
  (filter omitted) and dispose the throwaway geometry; otherwise reuse `bounds`.

## R1 — CRS effort=high (relay degraded mid-run: reconnect loop) · CHANGES_REQUIRED · 2×P2 (non-security)

Reviewed commit `27a6682`. Both findings are second-order, on the R0 fixes.

- **R1-P2#1 — hero peak dropped scalar-only elements on MIXED frames**
  (`heroPeakFormat.ts`). The recompute loop did `if (!el.stressTensor) continue`,
  but the viewport colors tensor-less elements via `componentValue`'s `value`
  fallback (`viewportGeometry.colorForElement`), so on a frame mixing tensor +
  scalar-only elements the hero could **under-report** the displayed maximum.
  **REAL — FIXED:** removed the `continue`; the loop now calls
  `componentValue(el.stressTensor, fieldComponent, el.value ?? NaN)` for **every**
  element (tensor → component; scalar-only → its `value` via the fallback; neither
  → NaN, skipped by `Number.isFinite`), exactly matching the displayed coloring.
  Added a `hasAnyTensor` guard so an all-scalar frame still falls back to the
  scalar summary (correct label, R0 behavior preserved). Pinned by a new
  mixed-frame unit test (`Phase43_hero_peak_readout.test.tsx`).

- **R1-P2#2 — "preserve section-cut bounds in the Fit/Home cache"**
  (`ResultMeshWebGLViewport.tsx`). **DECLINED — not a regression introduced by
  this commit** (fact-based):
  - `buildBufferGeometry`'s options are `{nextFrame, tInterp, deformationScale,
    fieldComponent, valueFilter}` — it does **not** accept `sectionCut`
    (`sectionCut` appears 0× in `viewportGeometry.ts`); the section cut is applied
    as a **material clipping plane** in the viewport effect, never folded into
    `bounds`.
  - Therefore `bounds` has **never** been section-cut-aware — neither the original
    line-351 `bounds` (used in the no-filter Fit path) nor the new `full` rebuild.
    My filter-path `full.bounds` represents the **same** thing as the original
    no-filter `bounds`: the whole-model, clip-agnostic extent.
  - Codex's premise ("rebuilt *without* `sectionCut`") implies the baseline path
    had section-cut-aware bounds; it did not. The consistent, documented Fit
    semantic is **"frame the whole-model bounding box"** (the Home/reset action) —
    which is exactly what R0-P2#2 asked for. A section-cut-aware Fit (frame only
    the visible clipped region) is a **net-new enhancement** requiring clipped-bounds
    computation that `buildBufferGeometry` does not provide; logged as a Slice-2+
    candidate, not a Slice-1 regression.

## Round-cap status

R0 (2×P2, fixed) → R1 (P2#1 fixed, P2#2 declined-with-rationale). Both rounds were
**non-security** (per ~/CLAUDE.md, non-security findings are async-review-eligible).
Within the round cap (R0 + ≤2 fix iterations). No P1 at any round.

## Verification

- `tsc --noEmit` clean · `eslint .` **70 = byte-identical baseline (0 introduced)**
  · App.tsx **1498** (<1500) · `vitest run` **1004 passed (71 files)** (+27 Phase 43).
- LIVE (preview, post-fix): ViewportNavGizmo (triad + 5 view buttons) + HeroPeakReadout
  ("von Mises stress · 1 Pa" @ `--fs-xl`) + WebGL-hero grid all render over the
  GS-102 single-hex demo result.

## Commits

- `27a6682` — Slice 1 + R0 fixes.
- (this) — R1-P2#1 fix (mixed-frame hero peak) + R1-P2#2 decline rationale + report.
