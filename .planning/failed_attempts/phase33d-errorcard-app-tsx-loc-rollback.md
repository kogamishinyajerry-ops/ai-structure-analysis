# phase33d-errorcard-app-tsx-loc-rollback — Phase 33 D → Phase 35 C

## Trigger
Phase 33 C novice_simulator finding #2 surfaced 5 silent
error-recovery paths in App.tsx: FRD upload, PDF export,
WebSocket death, stop request, solver-start [ERROR] log. Phase 33 D
attempted to wire ErrorCard into the upload + selectCase paths
INLINE (try/catch + setError state + ErrorCard mount, all in
App.tsx).

The wiring added ~71 LOC to App.tsx (1457 → 1528), tripping the
Phase 29 B regression pin that caps App.tsx at <1500 LOC.

## Decision
**Roll back** the Phase 33 D ErrorCard wiring. App.tsx returns to
1457 LOC. The 5 error-recovery paths get re-scheduled for Phase 35
with an explicit pre-requisite: extract state into a custom hook
FIRST (so App.tsx absorbs the wiring at ~+10 LOC, not +71).

## Evidence
- Phase 33 D rollback: see git log Phase 33 D (the ErrorCard wiring
  was added in an intermediate commit and reverted in the closing
  commit of Phase 33 D)
- Phase 35 C closure: commit `31856d1`
- Surviving hook (the Phase 33 D lesson's payoff):
  `frontend/src/state/useUploadErrorRecovery.ts` (~180 LOC NEW
  file at Phase 35 C)
- App.tsx LOC trace:
  - Phase 33 baseline: 1457
  - Phase 33 D pre-rollback (transient): 1528 (over the pin)
  - Phase 33 D post-rollback: 1457 (clean)
  - Phase 34 B: 1467 (CaseOpenAdvisorCard mount)
  - Phase 35 C: 1478 (ErrorCard + hook wiring, finally landed)
  - Phase 36 B: 1482 (mount repositioning)

## Closure status
CLOSED via Phase 35 C. The `useUploadErrorRecovery` hook absorbs
the state + try/catch + auto-retry machinery so App.tsx can mount
ErrorCard at +11 LOC instead of +71. The Phase 32 B `useAppUiMode`
extraction pattern is now applied for a second context.

Phase 36 A extended the same hook pattern to cover 2 more paths
(PDF export + stop-request) — total 4 of 5 silent paths closed.
The 5th (solver-start raw [ERROR] log) is structural — it's a
WebSocket log stream, not a fetch — and deferred to a future phase
that does dedicated WS-stream-error handling.

## Lessons
1. **Architecture > heroics.** Phase 33 D could have argued for a
   one-off LOC-pin exemption to land the wiring, but the discipline
   to roll back + re-plan with extraction-first was worth more than
   the 1 phase of delay.
2. **Custom hook patterns compound.** Phase 32 B's `useAppUiMode`
   showed the pattern; Phase 35 C's `useUploadErrorRecovery`
   reused it; Phase 36 A added new option templates with zero LOC
   growth to App.tsx. Each extraction lowers the marginal cost of
   the next one.
3. **Honest rollback is recorded in git history.** The Phase 33 D
   transient over-LOC commit + its rollback are both in the log;
   this entry preserves the WHY so future maintainers don't try
   the same inline approach assuming "nobody thought of it".
