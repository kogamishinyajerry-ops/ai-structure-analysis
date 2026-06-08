# FM-04a Phase 40 B — two-result comparison overlay → Dim 5 90-anchor · PLAN

> Closes the last unmet Dim 5 90-anchor sub-bullet: "comparison cuts (overlay TWO
> results)". The fresh registered functional-tester audit (`phase40_functional_tester_phase40A_dim5_viz.md`)
> put Dim 5 at 84 with the 90-anchor 2/4 (iso ✓ + CSV ✓; playwright-E2E ✗ +
> two-result-overlay ✗). This sub-bullet → ~88. Path A (frontend-only). 绝对诚实客观.
> Author: main session (Opus) + Plan-agent investigation, 2026-05-25. Code @ `2594a08`.

## NOT the companion viewport (do not conflate)
`CompanionViewport` = side-by-side 2-quadrant view of the SAME single result with
INDEPENDENT section cuts ("compare-cuts"). This feature surfaces TWO DISTINCT
results (two cases, or two steps/runs) overlaid / diffed. Different feature.

## Investigation findings (verified, file:line)
- **Load path is frontend-only + caseId-driven:** `ResultMeshPlaybackPanel.tsx:274`
  `fetch(\`${apiBase}/visualize/result-mesh/${caseId}\`)`. A 2nd result loads with an
  identical 2nd fetch for a different case_id — **no backend/solver-truth change**.
- **Stable join key = node `label`** (`resultMeshPlayback.ts:1-7`, used by
  `buildNodeCoords` `viewportGeometry.ts:198`). Element `label` is OPTIONAL
  (`resultMeshPlayback.ts:18-19`) → **join by node label only; no element-level join**.
- **No nodal field** (same as iso-surface): values are per-ELEMENT. A future
  difference FIELD must cell→point average each result first (reuse
  `averageElementValuesToNodes` from `isoSurface.ts`) then diff on shared labels.
- App already holds `comparisonCaseA/comparisonCaseB` state
  (`App.tsx:167-180`, localStorage-persisted) — a ready overlay source.

## Path A (frontend) vs Path B (backend) — **Path A**
- Path A: load 2nd result client-side + correspondence/diff in pure TS. No
  solver-truth/export/schema change; unit-testable; mirrors the iso-surface landing.
- Path B (backend emits paired/diff result) touches result-export/solver-truth =
  Codex risk-tier + golden_samples guards. **Reserve ONLY if** a future increment
  needs cross-mesh RESAMPLING (interpolating B onto mesh A). v1 does NOT resample.

## Increment split (mirrors the proven 40 A step-1/step-2 discipline)
- **40 B step 1 (THIS session) — pure correspondence kernel.** NEW
  `frontend/src/components/resultOverlay.ts` (no WebGL): `computeMeshCorrespondence(
  frameA, frameB)` → shared / only-A / only-B node-label sets + ratio + honesty
  metadata (whether the two meshes correspond enough to support a diff). Pure,
  fully unit-tested (`test/Phase40B_result_overlay.test.ts`, node --test). This is
  the low-risk testable core — land it isolated, like step-1 isoSurface.ts.
- **40 B step 2 (NEXT session) — viewport + panel wiring (regression-sensitive).**
  - `ResultMeshWebGLViewport.tsx`: opt-in props `overlayFrame?` + `overlayEnabled?`;
    when on, build a SECOND `buildBufferGeometry(overlayFrame,…)` (reuse verbatim) as
    a translucent CYAN mesh (distinct from blue→green→orange truth gradient AND the
    magenta iso-mesh) in its OWN useEffect that never touches the camera (mirror the
    iso-mesh effect). Default OFF → byte-stable. Render in the SAME scene (NO 2nd
    WebGL context — the ~16-context cap is noted at `CompanionViewport.tsx:11-14`).
  - `ResultMeshPlaybackPanel.tsx`: 2nd fetch effect for an `overlayCaseId` (clone of
    `:270-302`), summarize, pass `overlayFrame`/`overlayEnabled`; advanced-gated
    toggle in `ViewportDepthControls` (mirror the iso-surface row) + honesty caption.
  - `App.tsx`: ONE-LINE `overlayCaseId={comparisonCaseB}` on the existing mount
    (reuse existing state — guard the <1500 pin; currently 1486).
- **40 B step 3 (later) — difference FIELD** over shared labels only (cell→point
  average each result, per-node Δ, colored), gated on correspondence ratio.

## Honesty requirements (load-bearing)
- Overlay badge: "second result overlaid (case <id>) — NOT a validated diff."
- When correspondence ratio low/zero: "meshes do not share node labels — difference
  field unavailable; geometric overlay only." NEVER fabricate a Δ; NEVER resample in v1.
- Distinct hue (cyan) so the overlay is never read as a truth-gradient field.
- Step-3 diff badge: "difference on N shared nodes (of Ma/Mb); unmatched excluded."

## Acceptance (per increment)
- Step 1: pure module unit-tested (identical frames → ratio 1, only-A/B empty;
  disjoint → ratio 0 + honesty flag; partial → correct intersection). `tsc -b`
  0 net new (baseline 16); eslint 0 net new (baseline 72); node --test green.
- Step 2: jsdom test (overlay OFF default → no badge/2nd geometry, existing testids
  unchanged = byte-stable; ON+corresponding → overlay badge names case; ON+non-
  corresponding → "difference unavailable"). vitest green; App.tsx < 1500. Likely a
  Codex round (regression-sensitive viewport again — 40 A caught 2 P1s here).

## Risks
- **App.tsx LOC pin (1486/1500, 14 headroom):** keep the App change to a single prop;
  all logic in the panel. Highest watch.
- **Two WebGL contexts:** AVOID — overlay = 2nd mesh in the SAME scene.
- **Element-label instability:** join by NODE label only; element-level diff out of scope.
- **Path-B creep:** any cross-mesh resampling → solver-truth/export → risk-tier. v1
  stays strictly label-intersection (no resampling).
