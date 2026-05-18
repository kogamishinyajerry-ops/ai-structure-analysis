# Novice simulator report — Phase 36 D · post-Phase-36-A/B/C audit

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.

Re-runs persona × task traces against the current codebase, with direct focus on the three
Phase 36 slices targeting Novice UX completion:

- **Phase 36 A** (commit `3c50572`) — PDF + stop-request silent paths closed via Phase 35 C
  hook reuse; `(Phase XX)` suffix stripped from `candidateCaseRegistry.ts` displayLabels.
- **Phase 36 B** (commit `8315aaa`) — ErrorCard WCAG audit: `aria-labelledby` to title id,
  `aria-live="assertive"`, `codeFriendly` priority pill, Retry rebuilds FormData inside
  closure. ErrorCard mount moved ABOVE `OperatorStatusPanel`.
- **Phase 36 C** (commit `4188dc5`) — `runnerAvailable?: boolean` on
  `CandidateCaseRecord`; amber "demo · no live runner" badge in `CaseOpenAdvisorCard`.

Personas exercised: **P1** (junior · 1 yr · GS-102 demo open), **P3** (reviewer / IV&V ·
PDF export failure), **P5** (anxious novice · upload failure). P2 sparsely re-walked; the
Phase 34 A ballistic-notice fix is unchanged and remains a win.

Anti-gaming guards observed: A:-1 (no rubric anchor reword), D:-1 (every claim has
file:line evidence in the current codebase), F:-1 (the protocol overrides F:-1 generic
prohibition for this delta-comparison brief — re-reading Phase 35 D explicitly authorised),
G:-1 (measure what the codebase IS, not what it CLAIMS to be).

---

## Persona × task summary

| Persona | Task | Phase 35 D result | Phase 36 D result | Delta |
|---|---|---|---|---|
| P1 (junior · 1 yr) | T1 Open GS-102 demo case | partial — would attempt Run Solver without knowing case has no runner | **partial → cleaner** — amber "demo · no live runner" badge now warns at case-open | meaningful improvement |
| P3 (reviewer / IV&V) | T7 PDF export failure on cantilever | **silent** — crude `alert("Failed to export PDF: ")` | **partial completed** — styled ErrorCard above trust strip, "PDF export" pill, 3 remediation steps, Retry | meaningful improvement |
| P5 (anxious novice) | T7 Upload failure recovery | partial — ErrorCard rendered but below OperatorStatusPanel + no screen-reader announce | **partial → meaningfully cleaner** — ErrorCard above trust strip, screen reader announces via `aria-labelledby`, friendly "Upload" pill | meaningful improvement |

Completion rate: 1/4 full, 3/4 partial unchanged in COUNT, but partial QUALITY uniformly
lifted. The persona experience is materially closer to "actionable + recoverable" across all
4 of the 5 silent error paths originally flagged in Phase 33 C #2.

---

## Trace 1 · P1 (junior) × T1 (Open GS-102 demo)

### Phase 36 C win — runner_available badge closes friction point (f)

`CandidateCaseRecord` gained an optional `runnerAvailable?: boolean` field
(`candidateCaseRegistry.ts:38`). The fallback list is backfilled:

- GS-102-candidate / GS-102-refined / GS-102-hifi → `runnerAvailable: false`
  (`candidateCaseRegistry.ts:57,72,89`)
- rod-wave-impact-energy-leak → `runnerAvailable: false`
  (`candidateCaseRegistry.ts:108`)
- cylinder-pv-candidate / plate-with-hole-candidate / cantilever-beam-candidate →
  `runnerAvailable: true` (`candidateCaseRegistry.ts:131,148,165`)

`CaseOpenAdvisorCard.tsx:72-79` renders an amber badge with copy "demo · no live runner"
when `caseRecord.runnerAvailable === false`. Visual distinction from the stub badge:

- **stub badge** (`stubBadgeStyle`, lines 262-271): muted neutral border / text-secondary
  colour ("stub · offline-first")
- **runner badge** (`runnerBadgeStyle`, lines 275-284): amber-toned background
  `rgba(255, 180, 80, 0.10)` + amber border `rgba(255, 180, 80, 0.45)` — warm visual
  separation from the neutral stub badge

Both badges sit in the card header alongside "Case-open advisor" title (lines 66-83), so a
P1 persona opening GS-102 sees: case orientation copy + "demo · no live runner" warning +
"stub · offline-first" status badge BEFORE they hit Run Solver. **Friction point (f) from
Phase 35 D NEW #6 closed.**

Test pin: `Phase34B_case_open_advisor_card.test.tsx:215-248` adds 3 tests covering
`runnerAvailable: false` (badge rendered), `true` (badge absent), `undefined` (badge
absent — treats unknown as no opinion, matching the live-route contract). Strong pin.

### Trace-1 frictions remaining

- Tour still assumes a case is open at first paint — unchanged.
- No "is my beam OK?" verdict card — unchanged.
- No progress feedback during `solving` — unchanged.

---

## Trace 3 · P3 (reviewer / IV&V) × T7 (PDF export failure)

### Phase 36 A win — PDF export silent → styled ErrorCard

`App.tsx:399-417` (`downloadPDFReport`):

```tsx
await withUploadRecovery(async () => {
  const response = await fetch(`${API_BASE}/report/export/pdf/${activeCaseId}`)
  if (!response.ok) throw new Error(`PDF export HTTP ${response.status}`)
  ...
}, pdfExportRecoveryOptions(activeCaseId))
```

`pdfExportRecoveryOptions` in `useUploadErrorRecovery.ts:127-137` returns:

- title: "Could not export PDF report"
- message: `The PDF export for ${caseId} did not complete. The backend may be unreachable
  or the report may not yet be ready.`
- remediation: 3-step list at `useUploadErrorRecovery.ts:166-170` (confirm backend
  reachable / re-load case if stale / Retry)
- `code: 'PDF-EXPORT'` (raw, for support correlation)
- `codeFriendly: 'PDF export'` (visible pill copy)

P3 walk-through: triggers PDF export on cantilever → backend 502 → red ErrorCard appears
at the top of the content column with "PDF export" pill, plain-language title and 3
remediation steps, and a Retry button. **Friction point (a) from Phase 35 R3 closed.**

### Phase 36 A win — stop-request silent → ErrorCard

Same pattern for the stop-request path. `App.tsx:419-444` wraps the stop fetch in
`withUploadRecovery(... , stopRequestRecoveryOptions(jobId))`. `stopRequestRecoveryOptions`
in `useUploadErrorRecovery.ts:142-152` returns the parallel options ("Could not stop the
running solver" / `STOP-REQUEST` / `Stop request`). Previously this catch was silent;
post-36 A a reviewer attempting to halt a hung job sees an actionable card.

### Trace-3 frictions remaining

- `OperatorStatusPanel` prose instead of chronological audit-log — unchanged.
- SignoffHistoryPanel / AcceptancePacketPanel only inside Visual tab — unchanged.

---

## Trace 5 · P5 (anxious novice) × T7 (upload failure recovery)

### Phase 36 B win — ErrorCard sits ABOVE OperatorStatusPanel

`App.tsx:1313-1327`: the conditional ErrorCard mount (`{uploadError && ...}`) is now placed
BEFORE the `OperatorStatusPanel` JSX, with a `marginBottom: '24px'` to separate the two
surfaces. The P5 persona whose upload just failed sees the red error band immediately, not
after scrolling past trust prose. **Friction point (b) from Phase 35 R3 closed.**

### Phase 36 B win — `aria-labelledby` + `aria-live="assertive"` screen-reader semantics

`ErrorCard.tsx:46-78`: the alert region carries `role="alert"`, `aria-live="assertive"`,
and `aria-labelledby={titleId}` where `titleId = useId()` (line 55). The title element
carries `id={titleId}` (line 68). A screen reader now announces the alert with the title
as its accessible name; without this, the entire card text would be read out as the alert
name.

Test pin: `Phase36B_error_card_wcag_and_friendly_code.test.tsx:28-39`:
```tsx
const alert = screen.getByRole('alert', {
  name: /Could not load case cantilever-beam-candidate/i,
})
```
Plus `aria-live="assertive"` assertion (line 41-45), aria-hidden icon (47-52), Retry by
role+name (54-59). **Friction point (c) from Phase 35 R3 closed.**

### Phase 36 B win — codeFriendly humanises the pill

`ErrorCard.tsx:46-78` reads `pillCopy = codeFriendly ?? code` (line 51). When present, the
visible pill text is the friendly label; the raw enum is preserved as
`data-error-code={code}` (line 72). The 4 option templates in `useUploadErrorRecovery.ts`
all now ship paired `code` + `codeFriendly`:

| Path | code | codeFriendly | line |
|---|---|---|---|
| upload | `UPLOAD` | `Upload` | 105-106 |
| case-load | `CASE-LOAD` | `Case load` | 119-120 |
| pdf-export | `PDF-EXPORT` | `PDF export` | 134-135 |
| stop-request | `STOP-REQUEST` | `Stop request` | 149-150 |

Test pin: `Phase36B_error_card_wcag_and_friendly_code.test.tsx:62-99`: 4 tests covering
`codeFriendly` priority, fallback to `code`, `data-error-code` preserved, and absence of
both → no pill. **Friction point (d) from Phase 35 R3 closed.**

### Phase 36 B win — Retry rebuilds FormData inside closure

`App.tsx:290-300` (`generateReportFromFile`) and `App.tsx:319-329` (`selectCase`): the
`new FormData()` construction now lives INSIDE the `withUploadRecovery(async () => { ... })`
closure, not outside it. Because the FormData multipart stream is consumed once per fetch,
the prior pattern (FormData built once, closure captures it) would have caused Retry to
send an empty / consumed body. Inline reconstruction fixes this. **Friction point (e) from
Phase 35 R3 closed.**

### Phase 36 A — displayLabel "(Phase XX)" suffix strip

`candidateCaseRegistry.ts:132,149,165`:
- "Cylinder pressure vessel · Tier 2 validated" (was "(Phase 19 B)")
- "Plate with hole · 100×50×5 mm, meshed pipeline" (was "(Phase 20 C)")
- "Cantilever beam · Euler-Bernoulli δ=PL³/(3EI)" (was "(Phase 20 B)")

The composeBrief output (which interpolates `displayLabel` per `CaseOpenAdvisorCard.tsx:138`)
no longer leaks the harness's internal phase numbering to novice readers. **Phase 35 D NEW
friction #1 closed.**

### Phase 35 C → 36 A test pin extension

`Phase35C_useUploadErrorRecovery.test.tsx` now has **19 tests** (was 14 in Phase 35 C),
adding 5 Phase 36 A coverage entries (lines 314+ for `pdfExportRecoveryOptions` /
`stopRequestRecoveryOptions` + the 4-code distinctness assertions at lines 334-335). All
state transitions remain pinned. Strong test suite.

---

## Missing recovery paths — status table

| Error state | Code path | Recovery present? | Notes |
|---|---|---|---|
| FRD upload failure | `App.tsx:290-300` | **yes** | Phase 35 C; friendly Upload pill |
| Case load failure | `App.tsx:319-329` | **yes** | Phase 35 C; friendly Case load pill |
| PDF export failure | `App.tsx:399-417` | **yes** (NEW) | Phase 36 A; friendly PDF export pill |
| Stop-request failure | `App.tsx:419-444` | **yes** (NEW) | Phase 36 A; friendly Stop request pill |
| WebSocket death / no reconnect | (carryover from Phase 33 C #2) | **no** | Phase 37+ scope; needs a separate `useJobRecovery` cousin hook (live job context, not upload context) |
| Solver-start `[ERROR]` log path | `App.tsx:344-396` | **partial** | Logs the error string but no structured ErrorCard alongside |

**4 of 5 silent error paths now closed** (was 2 of 5 at Phase 35 D). The 5th (WS death) is
architecturally separate.

---

## Anchor matching for Dim 2

The rubric anchors (`RUBRIC_v2.md:113-119`):

| Anchor | Sub-bullets | Phase 36 D status |
|---|---|---|
| 60 | Feature buttons visible; case-tree exists; no guidance | met |
| 70 | One guided tour ≥4 affordances; Basic/Advanced toggle | met |
| 80 | Tour v2 ≥6 cards; in-context bubbles ≥5 surfaces; default Basic; auto-promote | met (carryover) |
| 90 | + role-branching onboarding; + **WCAG 2.1 AA audit pass**; + **every error state has visible recovery guidance** | **strong partial** — 4/5 error paths now have visible recovery (was 2/5 at Phase 35 D). ErrorCard ships `role="alert"` + `aria-live="assertive"` + `aria-labelledby` + accessible Retry button by role+name; this is materially WCAG 2.1 AA aligned for the error surface (live region announce, accessible name, focus-reachable button), but no project-wide WCAG audit report committed. No role-branching onboarding. |
| 95 | + novice_simulator ≥80% scenario autonomous completion; + help text references real paths only when relevant | not met — completion rate still around 1-2/4 full |
| 99 | + 100% completion; + every error state documented + tested recovery; + role-branching 4 personas; + WCAG audit report committed; + tour personalizes by role | not met |

**Dim 2 sits between 80 and 90**, with the 90-anchor recovery sub-bullet now **80%-met**
(4/5 paths) and WCAG sub-bullet partially-met (ErrorCard semantics shipped + tested, but
no committed project-wide audit report).

---

## Dim 2 score: **72 / 100** · confidence: medium

**Delta vs Phase 35 D (65) = +7**

Breakdown of the +7 delta:

- **+3** for finding (a) / (e) — PDF export + stop-request silent paths closed. Phase 35 D
  flagged 2/5 paths; Phase 36 A brings the count to 4/5. This is a substantial fraction of
  the 90-anchor sub-bullet "every error state has visible recovery guidance" (40% → 80%).
- **+2** for finding (c) — WCAG 2.1 AA semantic alignment on ErrorCard. `aria-labelledby`
  + `aria-live="assertive"` + accessible name via title id are tested in jsdom (semantic
  queries via `getByRole('alert', { name })`), not vibe-checked. This isn't a full
  project-wide audit (no `wcag_audit.md` committed), so partial credit only. A stricter
  auditor might credit +1.
- **+1.5** for finding (b) / (d) — ErrorCard mount moved above OperatorStatusPanel +
  humanised `codeFriendly` pill. Both are first-paint hygiene improvements that materially
  affect P5's "what just happened?" recovery experience.
- **+1** for finding (f) — runner_available badge. P1 attempting Run Solver on a demo case
  is now warned at case-open via amber "demo · no live runner" badge. This addresses the
  latent capability-disclosure gap that Phase 35 A's jargon-strip created.
- **+0.5** for Phase 35 D NEW #1 closure — displayLabel `(Phase XX)` suffix strip on the
  3 cohort cases. Small surface-stain win.
- **−1** for NEW friction points found in Phase 36 (see below). None severe; they're
  Phase 37+ polish items.

Net: 65 + 3 + 2 + 1.5 + 1 + 0.5 − 1 = **72**.

Confidence is **medium** rather than high because:
- The 90-anchor WCAG sub-bullet is partial (ErrorCard semantics committed + tested, but
  no project-wide audit report at `.planning/audits/wcag_audit.md` per the 99-anchor
  evidence requirement). A stricter reader might cap at 70.
- The 80-anchor (tour v2 ≥6 cards) still carries from Phase 27-28 and was not re-audited
  in Phase 36; no regression but no fresh verification either.
- jsdom-only test coverage on ErrorCard semantics — not a real screen-reader playback
  audit. A future Phase could add NVDA / VoiceOver pinning, but the jsdom semantic
  queries via `getByRole('alert', { name })` already pin the load-bearing accessibility
  contract.

The +7 jump (65 → 72) is the largest single-phase Dim 2 lift since Phase 34 A. It reflects
Phase 36 being a deliberately Novice-UX-focused phase that closed almost all the
near-term friction points enumerated in Phase 35 D.

---

## NEW friction points found in Phase 36

1. **WS death / no reconnect remains silent** — `App.tsx:344+` solver-start log path
   doesn't surface a structured ErrorCard alongside the `[ERROR]` log. Severity: medium.
   Architecturally separate from upload-context (live job context); needs a sibling
   `useJobRecovery` hook. Track to Phase 37+.
2. **No committed WCAG audit report** — ErrorCard ships semantic a11y attributes + tests,
   but the 90-anchor sub-bullet "WCAG 2.1 AA audit pass for all major surfaces" requires a
   project-wide sweep. AdvisorPanel, OperatorStatusPanel, SignoffHistoryPanel etc. have
   not been audited. Severity: low-medium. Track to a dedicated WCAG-sweep phase.
3. **Solver-start log `[ERROR]` is text-only** — `App.tsx:366,388` push `[ERROR]` strings
   into the log array but don't trigger an ErrorCard. A P5 user staring at a raw log line
   won't have the same recovery scaffolding (title / remediation / Retry) as the upload
   path. Severity: medium.
4. **`role="alert"` only announces once per change** — if a novice retries and fails
   again with the SAME message, some screen readers don't re-announce because the DOM
   text is identical. Mitigation would be a transient counter / "Attempt N" prefix.
   Severity: low. Phase 37+ polish.
5. **Runner badge colour is text-secondary on amber background** — readable but not
   high-contrast. May fail WCAG 1.4.3 contrast ratio on certain themes. Severity: low.
   Tracks to the WCAG sweep.

---

## Open gaps for Phase 37+

| Gap | Sourced from | Recommendation |
|---|---|---|
| WS death / no reconnect | Phase 33 C #2 carryover · Phase 36 D NEW #1 | Build `useJobRecovery` cousin hook; surface live-job ErrorCard |
| Solver-start `[ERROR]` log surface | Phase 36 D NEW #3 | Wire the solver-start fetch into a `solverStartRecoveryOptions` template |
| Project-wide WCAG 2.1 AA audit report | Rubric 90-anchor · Phase 36 D NEW #2 | Sweep AdvisorPanel / OperatorStatusPanel / SignoffHistoryPanel; commit to `.planning/audits/wcag_audit.md` |
| Role-branching onboarding | Rubric 90-anchor | Persona selector at first paint; tour cards adapt |
| Tour v2 ≥6 cards regression check | 80-anchor carryover | Re-walk the tour code in a future phase; pin card count |
| "Is my case OK?" verdict | Phase 34 D carryover | Single overall green/red verdict at top of Visual tab |
| ConvergenceStudyViewer dev-script hint | Phase 34 D carryover | Replace `scripts/gs102_...` hint with a UI button or a "ships no sweep" status |
| Post-tour next-action CTA | Phase 34 D carryover | Highlight the candidate roster when the tour finishes |
| Repeat-error screen-reader re-announce | Phase 36 D NEW #4 | Add a transient counter / "Attempt N" prefix on retry surface |
| Runner badge contrast | Phase 36 D NEW #5 | Verify contrast ratio under WCAG sweep; tune amber hue if needed |
| Failed-attempt corpus visibility | `.planning/failed_attempts/` (Phase 36 C side-deliverable) | 7 corpus entries shipped (Dim 6 lift), but NOT user-facing UI — Dim 2 untouched. A future phase could surface curated lessons in-app |

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.
绝对诚实客观 — Phase 36 D novice_simulator audit, Phase 36 A/B/C regression+improvement
check. Anti-gaming guards A:-1 / D:-1 / F:-1 (protocol override authorised for delta
analysis) / G:-1 honored.
