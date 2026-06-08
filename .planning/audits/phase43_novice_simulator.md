# FM-04a Phase 43 — novice-simulator (Dim 2 Novice UX)

> Registered evaluation fleet (`subagent_type=novice-simulator`). Tier 1 engineering
> candidate; not signed validation. 绝对诚实客观. Code @ `c3422b4`. Anti-gaming:
> scored by the sub-agent (B:-1), file:line evidence (D:-1), NOT given any prior
> audit/retro/blueprint (F:-1), scores what the UI ACTUALLY renders not what it CLAIMS
> (G:-1). Persona = brand-new engineer (FEA basics, zero product exposure) on the
> golden path (open → pick/create case → solve → understand 3D result).

## Dim 2 — Novice UX: **84 / 100**

**80-anchor fully met:** Tour v2 ships 6 cards (`onboardingTour.ts:43-86`),
in-context bubbles attach to ≥5 surfaces (`InContextHint` in `CaseBrowser.tsx:108`
+ probe/legend/threshold hints), Basic mode default with auto-promote to Advanced
(`onboardingTour.ts:266-275`, `AdvancedModePromo`).

**90-anchor partial (the cap):** "every error state has visible recovery guidance"
is genuinely met — 6 named recovery surfaces with remediation + Retry
(`useUploadErrorRecovery.ts:98-209`, `ErrorCard.tsx:80-101`, wired `App.tsx:1316-1320`)
— the strongest part of the product. The two gaps that cap below 90:
(1) **no role-branching onboarding** (single-track tour; `onboardingTour.ts` has no
engineer/reviewer/student/domain-expert selector); (2) **no WCAG 2.1 AA audit pass**
(focus-trap `OnboardingTour.tsx:101` + `role="alert"` exist, but contrast coverage is
per-surface ad hoc). 1 of 3 sub-bullets fully delivered → interpolate **84**.

## First-run walkthrough (friction, in order)

1. **Boot lands directly in a 3D result, tour suppressed** (`useBootCaseSelect.ts:48-61`
   auto-opens preferred candidate `GS-102-candidate`; `tourAutoShow` then false at `:80`,
   gated on `!activeCaseId`). **High.** A first-timer boots into a populated viewport
   with no onboarding — the 6-card tour fires only on the genuine no-case landing they
   never see.
2. **"Run Solver" enabled on a case the novice didn't choose** (`Topbar.tsx:202-228`,
   `showRunControls=Boolean(activeCaseId)` `App.tsx:1291`). **Medium.** No confirmation.
3. **Legend units default to raw "Pa", not engineering MPa**
   (`ResultMeshPlaybackPanel.tsx:131 fieldUnits='Pa'`, legend `:748-752`). **Medium.**
   Compounded: the primary contour viewport is a backend iframe (`App.tsx:1391-1397`
   `/visualize/plot`) whose legend the persona can't inspect → two legend surfaces.
4. **Solver progress honest but quiet** (`SolverProgressPanel.tsx:308-343`: indeterminate
   sweep + "Solving…" when no percent parses). **Low.** Honest; elapsed-seconds `:301`
   partly mitigates, but no ETA on long CCX runs.
5. **Trust/evidence prose dense for a beginner** (`OperatorStatusPanel` "Tier 1
   candidate; not signed validation…" `App.tsx:583-622`). **Low.**

## Missing error-recovery paths (dead-ends)

1. **`<NoResultState />` CTA is dead** — mounted at `App.tsx:1420` with **no
   `onBrowseCases` prop**; per `NoResultState.tsx:35-38` the "Browse cases" button only
   renders when the handler is supplied → empty state has no actionable button.
   **Medium.**
2. **Boot `/cases` fetch failure is silent** (`App.tsx:234-237`: failed fetch only
   `console.error`s, sets `casesLoaded=true`, no ErrorCard). **High.** Backend-down at
   boot → empty CaseBrowser, no "backend unreachable" guidance. `withUploadRecovery` is
   not wired to the initial cases/details fetch (`App.tsx:248-264`).
3. **No "what now?" after an in-stream CCX solve *failure*** (`App.tsx:445-449` sets
   status `failed`, red chip `SolverProgressPanel.tsx:119-125`, but no recovery card —
   distinct from solver-*start* failure which does have one at `App.tsx:358-382`).
   **Medium.**

**Wins (honest):** 6 recovery templates with ordered remediation + Retry
(`useUploadErrorRecovery.ts`), WS-disconnect reconnect (`App.tsx:472-481`), honest
no-fabricated-percent progress, CaseBrowser preview with per-case orientation blurbs
(`CaseBrowser.tsx:301-320`). Golden path completable (case pre-opened, Run Solver
visible, result renders) — partial-to-complete, med confidence. Caps: no role-branching,
no WCAG audit, two silent-boot/failed-solve recovery gaps.
