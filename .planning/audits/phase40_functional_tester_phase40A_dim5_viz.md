# Functional-tester report — scenario phase40A_dim5_viz

> Registered evaluation fleet (`subagent_type=functional-tester`), ADR-026.
> Fresh scoring run, F:-1 (no prior audits/retros/plans read; rubric only).
> Persisted by the orchestrator (main session does NOT score — B:-1).
> Date: 2026-05-25 · code @ `774ab69` · branch `claude/FM-04a-tier1-ballistic-candidate`.

## 1. Achieved anchor + final score

**Dim 5 (Visualization & tracking) = 84/100.** Highest fully-met anchor = **80**;
90-anchor is **2 of 4 sub-criteria met** (iso-surface ✓, CSV export ✓; playwright
E2E ✗, overlay-two-results ✗) → interpolate 80 → +4. All viz tests green.

Justification: full 80-anchor stack (companion compare-cuts + time-series scrubber +
probe persistence + WebGL/SVG dual-render) is shipped and tested; the new Phase 40 A
iso-surface and the earlier CSV export land half of the 90-anchor; no real-WebGL
Playwright suite and no two-results overlay.

## 2. Per-anchor (file:line evidence)

- **60 — MET.** 3D viewport + per-vertex contour: `ResultMeshWebGLViewport.tsx:341-388`
  (BufferGeometry + MeshPhongMaterial vertexColors), gradient `viewportGeometry.colorForValueFraction`,
  orbit/pan/zoom `:516-602`. (`Phase21C_webgl.test.tsx` green.)
- **70 — MET.** Probe pick `:549-593`→`onNodePicked`, HUD `:799-845`, `ProbeListPanel.tsx`;
  section cuts on ALL 3 axes `ResultMeshPlaybackPanel.tsx:1315-1331`, clip plane `:362-375`.
- **80 — MET (4/4).** Companion compare-cuts `CompanionViewport.tsx:1-36` (wired `:836-837`);
  time-series scrubber `ResultMeshPlaybackPanel.tsx:323-328,916-923,892-909`; probe persistence
  `probeListStorage.ts:4-8,63`; WebGL+SVG dual-render `ResultMeshWebGLViewport.tsx:173,239-245,285-297`
  + `ResultMeshPlaybackPanel.tsx:230-232`.
- **90 — PARTIAL (2/4).** See §3.
- **95 — UNMET.** No per-frame provenance overlay (grep snapshot/signoff/provenance in viewport = empty);
  no fps/perf path.
- **99 — UNMET.** No ≥60fps benchmark; only CSV export (no VTU/PNG); no Playwright suite; no full
  provenance chain.

## 3. 90-anchor sub-criteria

| Sub-criterion | Status | Evidence |
|---|---|---|
| Iso-surface rendering | **PRESENT** | `isoSurface.ts:181-280` marching-tets (cell→point, tet-only, honestly badged); mesh `ResultMeshWebGLViewport.tsx:419-462`; badge `:749-797`; toggle+threshold `ResultMeshPlaybackPanel.tsx:142-143,588-592`; tests `Phase40A_iso_surface*.test.*` |
| CSV export | **PRESENT** | `probeList.ts:99-120` + `ProbeListPanel.tsx:275-289` (Blob text/csv) |
| Real WebGL E2E via Playwright | **MISSING** | no `*.spec.ts` / `playwright.config` / dep; all tests jsdom (getContext-not-implemented → SVG fallback path) |
| Comparison cuts (overlay two results) | **MISSING** | companion shares ONE frame (`CompanionViewport.tsx:54-56`, E:-1); `CaseComparisonPanel.tsx` is a diff table, not a viewport overlay |

## 4. Top 3 gaps to raise next

1. **Two-results overlay** in the viewport (independent 2nd frame/case source, delta-colored) →
   closes the 4th 90-sub-bullet → ~88.
2. **Real-WebGL Playwright E2E** (`frontend/e2e/webgl_*.spec.ts`) in CI (90 + 99 evidence).
3. **Provenance overlay on viz frames** (case-id/snapshot-id/signoff-id; data already flows via
   `caseId`) + measured-fps artifact + VTU/PNG export (95→99).

**Verdict: partial / confidence high.** Viz wiring sound end-to-end; no broken handoffs;
iso-surface correctly reuses deformed coords and honors the value-filter
(`ResultMeshWebGLViewport.tsx:195-217`). **Net Dim 5 = 84.**
