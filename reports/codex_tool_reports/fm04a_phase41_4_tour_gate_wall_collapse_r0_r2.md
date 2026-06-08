# FM-04a Phase 41.4 — Codex review R0→R2 (tour/promo boot-gate + evidence-wall collapse)

> ADR-026 risk-tier: cross-≥3-file frontend change (App.tsx + hook + 3 components
> + new test). Relay: CRS effort=high (86gs xhigh 502'd the whole milestone).
> Round cap = 3 reached (R0 + R1 + R2). 2 residual P2 → retro queue.

## Scope (the change under review)

| File | Change |
|---|---|
| `frontend/src/components/OnboardingTour.tsx` | new `autoShow?: boolean = true` prop; `visible = (autoShow \|\| forceShow) && shouldShowTour(...)` |
| `frontend/src/components/AdvancedModePromo.tsx` | new `autoShow?: boolean = true` prop; gates `shouldShowAdvancedPrompt(...)` |
| `frontend/src/state/useBootCaseSelect.ts` | returns `{ tourAutoShow, promoAutoShow }` (was void); `casesLoaded` param added; boot-landing policy co-located |
| `frontend/src/App.tsx` | `casesLoaded` request-lifecycle state; destructures the two gates; passes them to tour/promo (net 0 LOC — pin 1498<1500) |
| `frontend/src/components/VisualTabPanel.tsx` | 22 evidence/governance panels wrapped in a default-closed `<details>` "Evidence & Trust" disclosure |
| `frontend/test/Phase41_4_boot_autoshow.test.tsx` | NEW — 11 tests pinning the tour/promo auto-show policy |

## R0 — 2 findings (REAL, fixed)

- **[P2] upload session re-armed onboarding.** `handleFileUpload()` clears
  `activeCaseId`; the first gate `casesLoaded && !activeCaseId` therefore re-enabled
  the overlays mid-upload. **FIX:** the gate now also requires `!sessionActive`
  (`Boolean(file || report)`), matching `useBootCaseSelect`'s existing session guard.
- **[P2] one-paint flash over the boot hero.** `casesLoaded` flipped true in the same
  commit where `activeCaseId` was still null (the boot effect runs later), so the tour
  could mount for one paint over the loading hero. **FIX:** gate on `!preferredAvailable`
  (a boot auto-select is pending) so the overlay is suppressed from the first paint.

## R1 — 2 findings (REAL, fixed)

- **[P2] promo permanently unreachable.** Gating the promo identically to the tour
  (`!activeCaseId`) suppressed it on every auto-boot visit, and it has no other
  surfacing path (`forceShow` unwired) → returning Basic-mode users who'd never seen
  it never could. **FIX:** the hook now returns SEPARATE `tourAutoShow` / `promoAutoShow`.
  The promo is suppressed only during the boot first-paint flash (`bootPending`) and
  becomes reachable once the case settles / on the no-case landing.
- **[P2] `casesLoaded` not request-scoped.** Set only on success → project-switch left
  it stale (flash risk) and a first-load `/cases` error suppressed both overlays forever.
  **FIX:** App resets `casesLoaded=false` before each fetch and sets it true in BOTH the
  `.then` and `.catch` (completes on failure too).

## R2 — 2 findings (REAL) → **DEFERRED to retro (round cap reached)**

- **[P2] promo can cover the loading shimmer.** `promoAutoShow` flips true the moment
  `selectCase()` sets `activeCaseId`, before the report/viewport finishes loading, so a
  returning Basic user's promo can pop over the shimmer rather than the settled result.
  A refinement of the R1 timing (moving target across rounds — exactly what the cap
  guards). Proper fix: gate the promo on report-loaded, not just `activeCaseId`.
- **[P2] collapsed evidence panels still mount + fetch.** `<details>` hides children
  visually but they still mount, so the 22 panels' mount-time fetch effects fire on first
  paint. The *visual* first-paint goal is met (live-verified clean hero); this is a
  request-burst/perf concern on slower backends. Proper fix: lazily mount the children on
  the disclosure's `open` state (needs a test sweep — 39 child-testid refs across ~10
  files, mostly direct-component renders, but App-integration paths must be cleared first).

Both R2 P2 → `.planning/retrospectives/` per `~/CLAUDE.md` round-cap rule
(R3 still-P1 → user ratify; remaining P2/P3 → retro, no infinite iteration).

## Verification (current committed state)

- `npx tsc --noEmit` clean; `App.tsx` 1498 LOC (Phase29B pin < 1500 green).
- vitest **962 passed** (951 baseline + 11 new boot-autoshow); Phase21D + onboarding/
  promo suites green.
- eslint: 2 errors — both **pre-existing on HEAD** (`withUploadRecovery` hoisting +
  AdvancedModePromo's prior setState-in-effect); **0 introduced** (stash-baseline confirmed).
- LIVE (fresh first-visit, localStorage cleared, reload): tour/promo absent across the
  entire boot-loading window (flash-free), 3D hero canvas 860×560 renders GS-102-candidate,
  "Evidence & Trust" disclosure collapsed by default.
