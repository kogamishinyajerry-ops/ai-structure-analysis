# FM-04a Phase 36 — Novice UX completion + failed-attempt corpus seed + WCAG audit

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-35. **20 consecutive Tier-2 phases**.

## Position in the 99+ journey

Phase 35 closed at composite **73.83/100 v2.0** (+1.33 over Phase
34's 72.50), landing -0.17 below the projected band's low end (74).
The Phase 35 sub-agent R3 audit flagged **6 NEW friction points**
that are concrete Phase 36 targets, plus the 3 remaining silent
error-recovery paths (PDF export / WebSocket death / stop request),
plus the long-standing Dim 6 anchor-95 gap (failed-attempt corpus
absent).

Phase 36 cleans the Phase 35 shortfall + the 6 friction points + 1
or 2 of the 3 remaining error paths + the failed-attempt corpus
seed.

Projected lift: **Phase 36 composite 75-78 / v2.0** (+1.2-4.2).

## Slice plan

| Slice | What lands | Projected dim impact |
|---|---|---|
| 36 blueprint | This document | — |
| **36 A** | Close 2 more silent error-recovery paths via reuse of `useUploadErrorRecovery.withRecovery` pattern: (a) PDF export crude-alert path → ErrorCard with PDF-EXPORT code; (b) stop-request silent path → ErrorCard with STOP-REQUEST code. Plus close Phase 35 friction point (a): strip "(Phase XX)" suffix from `candidateCaseRegistry.ts` displayLabel entries (replace with semantic-only labels). | Dim 2 +3-5 |
| **36 B** | WCAG audit pass on ErrorCard surface (friction points b/c/d/e from Phase 35 R3): (b) move ErrorCard mount ABOVE OperatorStatusPanel so failed users see error before trust prose; (c) verify ErrorCard's `role="alert"` + `aria-live="assertive"` actually announces to screen-readers (add a vitest a11y pin); (d) humanize the verbatim UPLOAD/CASE-LOAD codes — render a friendly title + the technical code as a smaller pill (no code change to ErrorCard.tsx; just adjust the hook's options); (e) `selectCase` Retry currently re-submits the captured dummy `File` — switch to closure that re-creates the FormData. | Dim 2 +2-3 / Dim 6 +0.5 |
| **36 C** | Failed-attempt corpus seed at `.planning/failed_attempts/INDEX.md` with ≥5 entries documenting the FM-04a honest pivots: (1) Phase 30 D plate-ss-shell pivot; (2) Phase 31 A heat transfer pivot from contact; (3) Phase 31 C Richardson sweep ≤0 guard; (4) Phase 33 D Hertz analytical-only deferral; (5) Phase 34 C stacked-cube vs Hertz curvature pivot; (6) Phase 35 B strict-additive schema interpretation. Each entry: link to the deferring/pivoting commit + analytical SSOT preserved + reason + Phase that closed the loop (or "still deferred"). Also `runner_available: false` badge for cases without live runners (friction point f from Phase 35 R3). | Dim 6 +1.5-2.5 |
| **36 D** | 3 sub-agents R4 + FINAL composite + retro + STATE refresh + commit. | — |

**Total projected composite lift: +1.2-2.5 (73.83 → ~75-78)**

## Phase 36 anti-gaming guards

All Phase 33-35 guards (A-M) carry verbatim. Phase 36-specific:

- **N:-1** (NEW): Phase 36 A must NOT break the Phase 35 C
  `useUploadErrorRecovery` test pins. The new PDF + stop-request
  paths must use the same `withRecovery(fn, options)` contract;
  no new error-surface widget; no parallel error-state hook.
- **O:-1** (NEW): Phase 36 C corpus entries must be EVIDENCE-LINKED —
  each entry cites a real commit SHA + a real preserved analytical
  SSOT (or marks "lost work" honestly if no SSOT survived). No
  reconstructed-from-memory entries; if a pivot's evidence is
  missing, document the absence rather than fabricate.
- **P:-1** (NEW): WCAG audit additions (Phase 36 B aria pin) must
  not be vibe-test "the role attribute exists". Use vitest +
  `@testing-library/jest-dom` matcher OR DOM queryByRole semantic
  check with explicit name. Phase 18 D ErrorCard test surface should
  be extended, NOT replaced (I:-1 ErrorCard carryover).

## Slice 36 A details

**Problem** (Phase 35 R3 friction points + Phase 33 C #2 carryover):

1. PDF export path (App.tsx). When PDF export fails, current code
   shows a crude `alert("PDF export failed")` — modal, not styled,
   no remediation, no retry, blocking. Phase 35 C didn't touch this
   path (out of Phase 35 scope).
2. Stop-request path (App.tsx). When the user clicks "Stop solver"
   and the request fails, the code silently swallows. No surface.
3. displayLabel Phase-suffix leak. `candidateCaseRegistry.ts`
   entries have labels like "Cantilever beam · Euler-Bernoulli
   δ=PL³/(3EI) (Phase 20 B)" — the "(Phase 20 B)" suffix is
   internal vocabulary leaking to novices.

**Fix scope**:

- For (1) and (2): wrap the existing fetch calls in
  `withUploadRecovery(...)` from the Phase 35 C hook. New option
  templates: `pdfExportRecoveryOptions()` + `stopRequestRecoveryOptions()`
  in `useUploadErrorRecovery.ts`. App.tsx growth ≤5 LOC for both
  paths combined.
- For (3): scan `candidateCaseRegistry.ts` for `(Phase ` substrings
  in displayLabel; replace with semantic-only suffix or drop the
  suffix entirely. Update any tests that assert the suffix.

## Slice 36 B details

**Problem** (Phase 35 R3 friction points b/c/d/e):

- ErrorCard sits BELOW OperatorStatusPanel → failed users see trust
  prose first.
- ErrorCard role="alert" + aria-live semantics need to actually
  announce.
- Verbatim UPLOAD / CASE-LOAD codes look like internal enums.
- `selectCase` Retry uses captured dummy File (not regenerated).

**Fix scope**:

- Move the ErrorCard mount in App.tsx to immediately AFTER the
  page header (above OperatorStatusPanel), not between case-open
  advisor and tabs. This requires repositioning ~3 LOC.
- Add a vitest a11y pin: render ErrorCard with `getByRole("alert")
  + name=title` and assert that the role + aria-live attributes
  match Phase 18 D contract. Extend Phase 18 D ErrorCard test
  surface, don't replace.
- Humanize the code rendering: instead of UPLOAD / CASE-LOAD
  appearing as the headline pill, expose a `codeFriendly` field
  in `WithRecoveryOptions` — codeFriendly takes priority for
  display; the raw `code` becomes the support-ticket pill (smaller,
  monospace).
- Fix the selectCase Retry: change the FormData construction to
  happen inside the `withUploadRecovery` closure so retry rebuilds
  fresh FormData each time.

## Slice 36 C details

**Problem** (Phase 35 D Dim 6 audit + Phase 35 R3 friction point f):

- `.planning/failed_attempts/INDEX.md` absent → Dim 6 anchor-95
  sub-bullet "failed-attempt corpus with ≥5 entries" stuck at 0/10.
- Cases without live runners (e.g. cantilever-beam, GS-102 series)
  have no UI badge indicating that — novices may try "Run Solver"
  and fail silently.

**Fix scope**:

- Create `.planning/failed_attempts/INDEX.md` with 5+ evidence-linked
  entries (per O:-1 guard).
- Create `.planning/failed_attempts/<slug>.md` per entry — each
  details: trigger, decision, evidence (commit SHA + preserved
  analytical SSOT path), closure-or-still-deferred status.
- Add `runner_available: boolean` field to
  `frontend/src/candidateCaseRegistry.ts` `CandidateCaseRecord`.
  Backfill the 12 cohort cases (live-runner cases: hertz-contact,
  cantilever-beam, cantilever-beam-modal*, cantilever-buckle,
  cantilever-dynamic, cylinder-pv, euler-column, heat-transfer-1d,
  plate-simply-supported, plate-ss-shell, plate-with-hole — all
  12 have live runners since Phase 34 C; GS-102 series + rod-wave
  are demo decks without runners → runner_available: false).
- Surface `runner_available: false` as a small "demo case · no
  live runner" badge in the case picker + CaseOpenAdvisorCard.

## Phase 36 projection

| Dim | Phase 35 | Phase 36 projected | Δ | Lift source |
|---|---|---|---|---|
| 1 FEA | 87 | 87 | 0 | Untouched (Phase 38+ cohort expansion) |
| 2 Novice UX | 65 | 70-72 | +5-7 | 2 more error paths + WCAG audit + displayLabel suffix strip + runner_available badge |
| 3 Industrial UI | 73 | 73 | 0 | Untouched (Phase 37 industrial parity) |
| 4 AI workflow | 73 | 73 | 0 | Untouched (Phase 37+ BC-setup surface) |
| 5 Visualization | 72 | 72 | 0 | Untouched (Phase 39) |
| 6 Trust | 73 | 75-76 | +2-3 | Failed-attempt corpus ≥5 entries + ErrorCard a11y pin + runner_available provenance |
| **Composite** | **73.83** | **~75-77** | **+1.2-3.2** | Recovery from Phase 35 -0.17 shortfall + real Dim 2 + Dim 6 lift |

## Hard constraints

All Phase 18-35 hard constraints carry verbatim:
- HF1.7a/b/8 signed-registry hard-stop + *-candidate carve-out
- tmp_path-only test writes
- v2.3 round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract
- prefers-reduced-motion honored
- Anti-gaming guards A-M + new N/O/P for this phase
- Phase 1-N additive only (no test threshold edits; App.tsx <1500)
- Rubric v2.0 99-anchor reachable via verifiable evidence
- NEVER re-score prior phases retroactively
- NEVER apply weights/transforms to composite
- No push / no PR / no Linear / no Notion writes

## Closing

Phase 36 closes the Phase 35 -0.17 shortfall + the 6 friction
points the sub-agent R3 surfaced + 2 of 3 remaining silent error
paths + the failed-attempt corpus seed (Dim 6 95-anchor sub-bullet)
+ the runner_available badge (resolves a real Phase 35 jargon-strip
side effect). The composite lift is moderate (+1.2-3.2) but
distributes across Dim 2 + Dim 6 — both axes the user's mandate
explicitly calls out.

This is the 20th consecutive Tier-2 phase. Trajectory remains on
track for 99+ by Phase ~45-46.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 20 consecutive
Tier-2 phases.
