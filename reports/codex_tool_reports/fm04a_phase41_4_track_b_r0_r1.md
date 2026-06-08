# FM-04a Phase 41.4 Track B — Codex review R0→R1 (3D-first recompose + boot)

> ADR-026 risk-tier: cross-≥3-file frontend change (App.tsx + ResultMeshPlaybackPanel.tsx
> + new useBootCaseSelect.ts). Relay: CRS effort=high (86gs xhigh 502'd this milestone).

## Scope

| File | Change |
|---|---|
| `frontend/src/state/useBootCaseSelect.ts` (new) | boot-select hook — auto-open a renderable candidate on a fresh, idle boot so the 3D leads first paint |
| `frontend/src/App.tsx` | call the hook; hoist the viewport-hero block ABOVE the VisualTabPanel governance wall + the advisor row (both demoted below the 3D) — JSX reorder, net flat (1497<1500) |
| `frontend/src/components/ResultMeshPlaybackPanel.tsx` | signed-registry (`^GS-\d{3}$`) 422 ErrorCard → honest "switch to a candidate" remediation (was the misleading "Run the solver") |

## R0 — 2 findings (both REAL, both fixed)

- **[P1]** boot-select raced upload-driven sessions (`useBootCaseSelect.ts`): `handleFileUpload()`
  keeps `activeCaseId` null, so a slow `/cases` load would let the effect fire and STEAL the
  upload session (replace the fresh upload report with the fallback case).
  **FIX:** added a `sessionActive` guard (`Boolean(file || report)`); the hook stands down (and
  latches `done`) whenever a case is open OR an upload/report session is underway.
- **[P2]** boot always opened `FALLBACK_CANDIDATE_CASES[0]`, ignoring a `localStorage`-restored
  `selectedCandidateCaseId` → a returning user saw the viewport on one case while the evidence
  panels keyed off another (mixed content on first paint).
  **FIX:** preferred id is now `selectedCandidateCaseId ?? FALLBACK_CANDIDATE_CASES[0]?.caseId`,
  so the auto-opened case matches the evidence surfaces; honest no-op if it isn't in `availableCases`.

## R1 — CLEAN / APPROVE (0 findings)

> "The diff is internally consistent and I did not find a discrete, user-impacting regression in
> the new boot-select hook, the viewport reordering, or the signed-registry remediation copy."

## Verification (live + gates)

- Fresh boot → auto-opens `GS-102-candidate`; WebGL 3D renders (`result-mesh-webgl-viewport`,
  canvas present) at scroll-y ≈ 418 (first screen), ABOVE the governance wall (≈ 1910). 3D-first ✓.
- P1 path: an upload/report session suppresses boot-select (no session theft).
- P2 path: persisted-but-unavailable candidate (`plate-with-hole-candidate`) → honest no-op →
  CaseBrowser landing (no mixed content). Cleared localStorage → fresh boot to `GS-102-candidate`.
- Signed `GS-003` → ErrorCard shows "sealed signed-registry case — switch to a candidate".
- Gates: vitest **951 passed** · `tsc -b` 16 (0 net new) · eslint 51 (0 net new) · App.tsx **1497** <1500
  (Phase29B pin) · Phase21D VisualTabPanel pins (testid + Provenance/Advisor null-gating) held.
- No golden_samples / solver-truth / schema change.
