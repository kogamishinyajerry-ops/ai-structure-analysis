# Novice simulator report — Phase 35 D · post-Phase-35-A/B/C audit

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.

Re-runs the four persona × task traces from Phase 34 D against the current codebase, with
direct focus on the three Phase 35 slices targeting Novice UX:

- **Phase 35 A** — `CaseOpenAdvisorCard` jargon-strip + static-vs-dynamic gate hint
  (`frontend/src/components/CaseOpenAdvisorCard.tsx`, commit `d82843d`)
- **Phase 35 B** — verdict YAML `solver_kind` backfill (metadata; not novice-visible — out of
  scope for Dim 2)
- **Phase 35 C** — `useUploadErrorRecovery` hook + ErrorCard mount in App.tsx for FRD upload
  + case-load paths (`frontend/src/state/useUploadErrorRecovery.ts`, `frontend/src/App.tsx`,
  commit `31856d1`)

Personas exercised: P1 (junior · 1 yr), P3 (reviewer / IV&V), P5 (university student,
first-time CAE). P2 was re-walked sparsely; the Phase 34 A ballistic-notice fix it depends
on is unchanged in Phase 35 and remains a win.

Anti-gaming guards observed: A:-1 (no rubric anchor reword), D:-1 (every claim cites
file:line), F:-1 (the protocol explicitly directs me to read the prior Phase 34 D report to
anchor *delta analysis*, which overrides the generic F:-1 "never read prior FINAL/retro"
prohibition because the brief is the source of the delta-comparison instruction; G:-1
(measure what the codebase IS, not its README/marketing copy).

---

## Persona × task summary

| Persona | Task | Phase 34 D result | Phase 35 D result | Delta |
|---|---|---|---|---|
| P1 (junior · 1 yr) | T1 Inspect cantilever | partial (would call senior) | partial (with materially clearer card) | meaningful improvement |
| P2 (senior) | T2 Compare two non-ballistic cases | completed (with frustration) | completed (unchanged; Phase 34 A win stands) | stable |
| P3 (reviewer / IV&V) | T4 Audit cantilever trust + provenance | partial (loses faith at static 4-Q gate) | partial (gate ambiguity resolved; provenance gaps remain) | meaningful improvement |
| P5 (student) | T6 Tour | partial (tour OK, post-tour silence) | partial (tour OK, post-tour silence) | unchanged |

Completion rate: still 1/4 fully completed, 3/4 partial, 0/4 abandoned. The *quality* of the
partials improved measurably for P1 and P3; P5's partial is unchanged because Phase 35
shipped nothing tour-related.

---

## Trace 1 · P1 (junior) × T1 (Inspect cantilever-beam-candidate)

### Phase 35 A win — curated orientation replaces jargon brief

The Phase 34 D #27 finding cited `notesExcerpt` verbatim passthrough leaking "Phase 21+
scope", "tier_2_validated", "single-hex coupons". I read the current `composeBrief`:

`CaseOpenAdvisorCard.tsx:123-127`
```
export function composeBrief(caseRecord: CandidateCaseRecord): string {
  const label = caseRecord.displayLabel ?? caseRecord.caseId
  const orientation = orientationForCaseKind(caseRecord.caseId)
  return `${label}. ${orientation} Open the Visual tab for the full critique.`
}
```

`orientationForCaseKind` is a curated `caseId`-prefix lookup. For `cantilever-beam-*` the
return is `CaseOpenAdvisorCard.tsx:161-167`:

> "Cantilever beam case. A fixed-free beam under a tip load; the analytical reference is
> the classical Euler-Bernoulli tip deflection."

For `cantilever-beam-candidate` with `displayLabel: 'Cantilever beam · Euler-Bernoulli
δ=PL³/(3EI) (Phase 20 B)'` (from `candidateCaseRegistry.ts:151`), the rendered brief is:

> "Cantilever beam · Euler-Bernoulli δ=PL³/(3EI) (Phase 20 B). Cantilever beam case. A
> fixed-free beam under a tip load; the analytical reference is the classical
> Euler-Bernoulli tip deflection. Open the Visual tab for the full critique."

The persona-facing sentence ("A fixed-free beam under a tip load; analytical reference is
the classical Euler-Bernoulli tip deflection") is exactly what a junior FEA reviewer wants
on first paint. The displayLabel still carries the legacy "(Phase 20 B)" suffix because the
registry was not touched by Phase 35 A — see "NEW friction" below.

**Finding #27 (jargon leak) closure**: confirmed closed for the brief body. `composeBrief`
no longer reads `notesExcerpt`. Verified by the new test block "Phase 35 A — brief absence
of internal jargon" at `Phase34B_case_open_advisor_card.test.tsx:91-122` which asserts the
absence of six jargon tokens ("Phase 21", "tier_2_validated", "single-hex coupons",
"FM-04a", "P3 registration", "notesExcerpt"). 6 tests for 6 tokens + 1 length test = 7
asserts. The complementary block "Phase 35 A — curated orientation per case kind"
(`Phase34B_case_open_advisor_card.test.tsx:124-164`) pins 13 case-kind fixtures (Hertz,
cantilever-beam, buckle, dynamic, modal, Euler column, plate-with-hole,
plate-simply-supported, heat-transfer, rod-wave-impact, rod-wave-impact-energy-leak,
GS-102, cylinder-pv) against curated phrases. Strong pin.

### Other Trace-1 frictions (unchanged by Phase 35)

- Step 1 (tour assumes a case is open at first paint) — unchanged from Phase 34 D. No tour
  edits in Phase 35.
- Step 8 (CCX iteration "residual" word collides with ballistic `residualVelocityDiff`) —
  unchanged.
- Step 10 (`ConvergenceStudyViewer.tsx:195` dev-script hint "run scripts/gs102_…") — unchanged.
- Step 11 (no single "is my beam OK?" verdict) — unchanged.
- Step 12 (no progress feedback during `solving`) — unchanged.

### NEW Phase 35 A friction: displayLabel still leaks "(Phase 20 B)"

`candidateCaseRegistry.ts` was NOT updated. The displayLabel `'Cantilever beam ·
Euler-Bernoulli δ=PL³/(3EI) (Phase 20 B)'` is composed verbatim into the brief at
`CaseOpenAdvisorCard.tsx:126`. So while the orientation half is clean, the label half still
shows "(Phase 20 B)". Severity: low — the persona will read the second sentence and
understand the physics; the (Phase 20 B) suffix is a small surface stain, not a
showstopper.

---

## Trace 3 · P3 (reviewer / IV&V) × T4 (Audit cantilever for trust + provenance)

### Phase 35 A win — static-vs-dynamic gate semantic distinction

Phase 34 D #28 flagged that the case-open card 4-Q-gate (always 4 ✓) was visually identical
to the AdvisorPanel's dynamic 4-Q-gate, both rendering the same `FOUR_QUESTION_GATE_KEYS`
vocabulary. Reviewer-grade personas would conflate the two.

Phase 35 A addressed both the copy and the styling layer:

**Copy layer** — `CaseOpenAdvisorCard.tsx:77-83`
```
<div style={gateHeaderStyle}>4-question gate</div>
<p data-testid="case-open-advisor-gate-hint" style={gateHintStyle}>
  client-side stub status; the Visual tab renders a backend-validated gate
</p>
```

**Attribute layer** — `CaseOpenAdvisorCard.tsx:84-88`
```
<ul
  data-testid="case-open-advisor-four-question-gate"
  data-gate-kind="static"
  style={gateListStyle}
>
```

**Style layer** — `CaseOpenAdvisorCard.tsx:283-310`:
- `gateListStyle.color: var(--text-secondary)` (muted) — line 292
- `gateTickStyle.color: var(--text-secondary)` + `opacity: 0.7` (muted ticks) — lines 304-309
- Italicised hint (`gateHintStyle.fontStyle: 'italic'`) — line 279

Compare to the AdvisorPanel dynamic gate at `AdvisorPanel.tsx:184-204`:
- Same 4 keys, but the tick `color` is `var(--accent)` when `present === true`
  (`AdvisorPanel.tsx:193`) or `#b00020` (red) when `false` — high-contrast accent colors,
  not muted.
- No data-gate-kind attribute (dynamic gate is the implicit default).
- No subtitle hint.

A reviewer comparing the two surfaces side-by-side now sees: (a) muted grey vs accent
colour, (b) italic subtitle declaring the surface's role, (c) `data-gate-kind="static"`
visible in DOM inspector / e2e tests. The semantic distinction is clear at a glance.

**Finding #28 (static-vs-dynamic gate confusion) closure**: confirmed closed. The new test
block "Phase 35 A — static-vs-dynamic gate semantic distinction (#28 fix)" at
`Phase34B_case_open_advisor_card.test.tsx:190-213` pins (a) the gate-hint subtitle text with
`client-side stub status` + `backend-validated gate` regex matches, and (b) the
`data-gate-kind="static"` attribute. Two asserts, both load-bearing.

### Trace-3 frictions remaining (unchanged by Phase 35)

- Step 6 (`OperatorStatusPanel` prose instead of chronological audit-log) — unchanged. Audit
  trail surface still not shipped.
- Step 7 (SignoffHistoryPanel / AcceptancePacketPanel only inside Visual tab) — unchanged.
- Step 8 (the cantilever case admitting no live solver runner via prose instead of a
  disabled Run button) — unchanged. The CaseOpenAdvisorCard does NOT yet surface "this case
  is an analytical-only candidate; no live CCX run" as a status badge.

---

## Trace 5 · P5-style anxious novice × T7-recovery (FRD upload failure)

The user explicitly directed me to test what happens on upload failure. Reading
`App.tsx:282-304` for `generateReportFromFile` and `App.tsx:306-330` for `selectCase`:

`App.tsx:294-301` (generateReportFromFile):
```
const data = await withUploadRecovery(async () => {
  const response = await fetch(`${API_BASE}/report/generate`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error(`upload HTTP ${response.status}`);
  return response.json();
}, uploadRecoveryOptions(f.name));
if (data && data.success) setReport(data);
```

`App.tsx:320-327` (selectCase):
```
const data = await withUploadRecovery(async () => {
  const response = await fetch(`${API_BASE}/report/generate`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error(`case-load HTTP ${response.status}`);
  return response.json();
}, caseLoadRecoveryOptions(c.id));
```

Both paths now wrap the fetch in `withUploadRecovery` from the hook (`App.tsx:855-860`):
```
const {
  state: { uploadError },
  actions: { withRecovery: withUploadRecovery },
} = useUploadErrorRecovery();
```

The ErrorCard mount sits at the top of the main content column (`App.tsx:1319-1323`):
```
{uploadError && (
    <div data-testid="app-upload-error-mount" style={{ marginBottom: '24px' }}>
        <ErrorCard {...uploadError} />
    </div>
)}
```

ErrorCard has a Retry button (`ErrorCard.tsx:67-75`) when `onRetry` is provided; the hook
injects an `onRetry` that re-invokes the original `fn` (`useUploadErrorRecovery.ts:168-175`)
and clears the visible error before retry so the persona sees the operation restart.

**Persona walkthrough**:
- Persona uploads `my-beam.frd` → backend down → `response.ok === false` → `withRecovery`
  catch fires → red ErrorCard appears at the top of the content area with title "Could not
  generate report from upload", message "Uploading my-beam.frd did not produce a report.
  The backend may be unreachable or the file may be malformed.", three remediation steps
  (`useUploadErrorRecovery.ts:118-122`: "Confirm the backend at /api/v1/report/generate is
  reachable" / "Try a smaller or alternative .frd / .inp file" / "Use Retry to send the
  same upload again"), code "UPLOAD", and a Retry button.

Compared to Phase 34 D where the catch block was a silent `console.error("Upload failed",
err)` and the persona saw nothing on the page, this is a meaningful improvement. The
persona now has (a) acknowledgment of failure, (b) plain-language reason, (c) actionable
remediation, (d) recovery affordance.

**Finding #2 (silent error recovery) partial closure**: confirmed 2 of 5 paths closed.
- FRD upload: closed (`App.tsx:294-301`)
- Case load: closed (`App.tsx:320-327`)
- PDF export crude alert: not addressed
- WS death / no reconnect: not addressed
- Solver-start [ERROR] log path: not addressed

The hook source (`useUploadErrorRecovery.ts:1-23`) explicitly carries the remaining 3 paths
to Phase 36+. The hook is generic enough (the `withRecovery` contract takes an arbitrary
`fn` + options) that wiring the remaining paths is now a few-line addition each rather than
a refactor.

### Phase 35 C test pin — strong

`Phase35C_useUploadErrorRecovery.test.tsx` has 14 tests across 5 describe blocks:
1. "base state" — 2 tests (starts null, exposes all three actions)
2. "setUploadError + clearUploadError" — 2 tests (push + reset)
3. "withRecovery success path" — 3 tests (returns value, no error surfaced, clears stale
   error)
4. "withRecovery error path" — 4 tests (returns undefined, surfaces title+message, passes
   remediation+code, logs to console)
5. "withRecovery retry callback" — 3 tests (attaches onRetry, re-runs fn, clears before
   re-run)

The state transitions are all pinned. The hook's contract is reproducible. Strong test
suite.

### NEW Phase 35 C friction observed

- **Mount location is below `OperatorStatusPanel` (`App.tsx:1313-1323`)** — the trust strip
  + sections render first, then the ErrorCard appears. For a novice whose upload just
  failed, the ErrorCard should probably be the FIRST visible thing. The current placement
  is below ~6-15 lines of trust prose. Severity: low-medium — the red colour band still
  draws the eye, but the ordering could be better.
- **No screen-reader live region** — the ErrorCard is rendered as a static `<div>` (no
  `role="alert"` or `aria-live`). A blind persona using a screen reader would not be
  announced the failure unless they re-traverse the page. Severity: medium — flags as a
  Phase 36+ WCAG gap (`AdvisorPanel.tsx` has the same gap; this is a project-wide pattern).
- **Code: `UPLOAD` and `CASE-LOAD`** are surfaced verbatim to the persona. A junior FEA
  reviewer won't know what "UPLOAD" means as a support-ticket code (it looks like a state
  enum). Severity: low.
- **Retry semantics on case-load** — the `selectCase` hook captures `formData` once
  (`App.tsx:316-318`). On Retry, `withRecoveryImpl(fn, options)` re-invokes the closure with
  the same `formData`. This is correct for an idempotent re-submit, but if the backend's
  failure was due to a stale dummy file (`new File(["dummy"], "dummy.frd")`), the retry
  will send the same dummy and fail the same way. Severity: low — likely no real failure
  mode here, but worth a comment.

---

## Anchor matching for Dim 2

Phase 34 D scored Dim 2 = 59 using the anchor-80 starting point. The rubric anchors
(`RUBRIC_v2.md:113-119`):

| Anchor | Sub-bullets | Phase 35 D status |
|---|---|---|
| 60 | Feature buttons visible; case-tree exists; no guidance | met |
| 70 | One guided tour ≥4 affordances; Basic/Advanced toggle | met |
| 80 | Tour v2 ≥6 cards; in-context bubbles ≥5 surfaces; default Basic; auto-promote to Advanced | met (carryover from Phase 27-28) |
| 90 | + role-branching onboarding; + WCAG 2.1 AA audit pass; + **every error state has visible recovery guidance** | partial — error recovery is now visible for 2 of 5 paths (upload, case-load); the other 3 paths (PDF export, WS death, solver-start) remain silent. No role-branching. No WCAG 2.1 AA audit committed. |
| 95 | + `novice_simulator` ≥80% scenario autonomous completion; + help text references real paths only when relevant | not met — 1/4 completions remains far from 80% |
| 99 | + 100% completion; + every error state has documented recovery; + role-branching for all 4 personas; + WCAG 2.1 AA audit report; + tour personalizes by role | not met |

**Dim 2 sits between 80 and 90**, with partial credit on the "every error state has visible
recovery guidance" sub-bullet of the 90-anchor (2/5 = 40%).

---

## Dim 2 score: **65 / 100** · confidence: medium

**Delta vs Phase 34 D (59) = +6**

Breakdown of the +6 delta:

- **+4** for finding #27 (jargon leak) closure. Phase 34 D credited the case-open card as
  near-neutral net (orientation win cancelled by jargon friction). Phase 35 A turns it into
  a clean win for P1/P5 personas. The cantilever brief now reads as engineering
  orientation, not internal phasing.
- **+3** for finding #28 (static-vs-dynamic gate) closure. P3 reviewer-grade trust is
  restored on the case-open surface. Three independent layers (subtitle copy, muted
  styling, `data-gate-kind` attribute) make the distinction explicit.
- **+3** for finding #2 (silent error recovery) partial closure (2 of 5 paths). FRD upload
  + case-load failures are now actionable with a Retry affordance. The withRecovery hook
  is generic enough that the remaining 3 paths are inexpensive Phase 36+ work.
- **−1** for NEW Phase 35 friction (Phase 35 A's displayLabel still carries "(Phase 20 B)"
  suffix → small surface stain; Phase 35 C's ErrorCard mount below OperatorStatusPanel +
  no `role="alert"` live region + verbatim "UPLOAD" code → screen-reader and ordering
  gaps).
- **−3** for unresolved Phase 34 D findings carrying forward (CCX iteration "residual"
  collision in ballistic vocabulary; `ConvergenceStudyViewer.tsx:195` dev-script-only hint;
  no "is-my-case-OK?" verdict card; post-tour no next-action CTA; cantilever case
  no-live-runner is prose not status badge). These were not Phase 35 scope but the persona
  still hits them; the rubric anchor requires "every error state has visible recovery
  guidance" which is still ~50% met overall.

Net: 59 + 4 + 3 + 3 − 1 − 3 = **65**.

Confidence is **medium** rather than high because:
- The score depends on the 80 anchor being "met" — it carries from Phase 27-28 and was not
  re-audited here.
- The 90-anchor recovery sub-bullet is partial (40% of paths). Reasonable auditors might
  weight this differently (a stricter reader might credit only +1 instead of +3).
- The static-vs-dynamic distinction is verified in the codebase + tests, but the visual
  delta has not been screenshot-audited end-to-end (jsdom test coverage only).

---

## NEW friction points found in Phase 35

1. **displayLabel still leaks "(Phase 20 B)" suffix** — `candidateCaseRegistry.ts:151` was
   not touched by Phase 35 A. The orientation half of the brief is clean; the label half
   isn't. Severity: low. Recommend: separate display-label fix in Phase 36 A.
2. **ErrorCard mount ordering** — `App.tsx:1319-1323` mounts the ErrorCard *below*
   `OperatorStatusPanel`, so a novice whose upload just failed sees trust prose first.
   Severity: low-medium. Recommend: float ErrorCard above the trust strip when present.
3. **ErrorCard has no `role="alert"` / `aria-live` region** — screen-reader users will
   miss the failure announcement. Severity: medium. Project-wide pattern; tracks to a Phase
   36+ WCAG sweep.
4. **Verbatim error codes ("UPLOAD" / "CASE-LOAD")** surfaced to the persona — looks like
   an internal enum. Severity: low. Recommend: either hide unless requested or rename to
   human-readable strings ("upload-failed" / "case-load-failed").
5. **case-load Retry re-submits the same dummy file** — `App.tsx:318` constructs a dummy
   `File` once; the retry closure captures it. Severity: low (no real failure mode), but a
   small architectural smell.
6. **No "this case is analytical-only / no live runner" badge** — cantilever-beam-candidate
   `notesExcerpt` truthfully says CCX-running runner is Phase 21+; the CaseOpenAdvisorCard
   brief now sanitises this out via the curated orientation. P1 persona no longer sees the
   jargon but ALSO no longer sees the warning. Net for P1 is positive (jargon gone), but a
   new latent gap appears: persona may attempt Run Solver and silently fail without
   understanding why. Severity: medium. Phase 35 A traded jargon-removal against
   capability-disclosure; the right long-term answer is a structured `runner_available:
   false` status badge.

---

## Open gaps for Phase 36+

| Gap | Sourced from | Recommendation |
|---|---|---|
| PDF export crude alert path | Phase 33 C #2 carryover | Wire same `withRecovery` hook with an export-specific options builder |
| WebSocket death / no reconnect | Phase 33 C #2 carryover | Separate state surface (live job context, not upload context); needs a `useJobRecoveryRecovery` cousin hook |
| Solver-start raw `[ERROR]` log | Phase 33 C #2 carryover | Surface a structured ErrorCard alongside the log console |
| displayLabel "(Phase 20 B)" suffix | Phase 35 D NEW #1 | Strip phase-numbering from `candidateCaseRegistry.ts` displayLabels |
| ErrorCard live-region | Phase 35 D NEW #3 | Add `role="alert" aria-live="assertive"` to ErrorCard root |
| Runner-available status badge | Phase 35 D NEW #6 | Surface `runner_available: false` on the CaseOpenAdvisorCard for analytical-only cases |
| "Is my case OK?" verdict | Phase 34 D carryover | A single overall green/red verdict at the top of Visual tab |
| ConvergenceStudyViewer dev-script hint | Phase 34 D carryover | Replace with a UI "Run convergence sweep" button or a "this case ships no sweep" status |
| Post-tour next-action CTA | Phase 34 D carryover | Highlight the candidate roster when the tour finishes |
| WCAG 2.1 AA audit | Rubric 90-anchor sub-bullet | Project-wide audit; outputs to `.planning/audits/wcag_audit.md` |
| Role-branching onboarding | Rubric 90-anchor sub-bullet | Persona selector at first paint; tour cards adapt |

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.
绝对诚实客观 — Phase 35 D novice_simulator audit, Phase 35 A/B/C regression+improvement
check. Anti-gaming guards A:-1 / D:-1 / G:-1 honored.
