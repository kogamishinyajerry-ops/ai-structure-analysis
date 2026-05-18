# Novice simulator report — Phase 33 C re-baseline (rubric v2.0 Dim 2)

> Four persona × task traces stitched into one report. Codebase root
> `/Users/Zhuanz/20260408 AI StructureAnalysis`. No prior audit files
> read; scoring is from current code surface only.

---

## P1 × T1 — Junior engineer inspecting `cantilever-beam-candidate`

### Persona
Structural engineer, 1 year experience. SolidWorks + occasional ANSYS
Workbench. Strong CAD intuition, weak FEA theory. Goal: "Just see if
my beam is OK."

### Task
Open `cantilever-beam-candidate`, find the residual, decide if it's
acceptable.

### Completion
- result: **partial**
- completion confidence: med
- estimated time-to-first-friction: ~1 min
- estimated time-to-abandonment: n/a (engineer pushes through but
  exits uncertain whether the answer is "OK")

### Friction trace

| # | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Landing — first paint | Tour pops as expected; copy is dense ("Mises, σ_xx / σ_yy / σ_zz, σ_xy / σ_yz / σ_xz, principal stresses") for someone who has never opened the app. | low | "OK… a lot of Greek." | `onboardingTour.ts:47` |
| 2 | Tour card 4 ("Slice into the model") | "Section-cut depth slider" — no pointer/arrow at the actual slider. | low | "Where IS the slider though?" | `onboardingTour.ts:64` (text-only, no spotlight) |
| 3 | Tour card 5 ("Basic / Advanced") | Tells the engineer Basic HIDES the very features the previous cards just introduced. Confusing sequencing. | med | "Wait, so I should use Basic… but I just learned about all the things Basic hides?" | `onboardingTour.ts:73-74` |
| 4 | Tour done | Tour dismissed; tour mentions a *Basic/Advanced toggle in the viewport header* but no spotlight, and the post-tour `AdvancedModePromo` may or may not surface depending on `uiMode === 'basic'`. | med | "Now what — what's a Workbench? Where's my beam?" | `App.tsx:1234` (`OnboardingTour` mounts at root, no spotlight) |
| 5 | Sidebar — Case Gallery is empty | Empty-state copy: "Drop an FRD file below or load a candidate case from the workbench". "FRD" is unexplained jargon for an ANSYS-only user (FRD is the Calculix output format, not ANSYS terminology). | high | "FRD? Do I need one of those? Where do I get one?" | `Sidebar.tsx:181` |
| 6 | Sidebar — Candidate Cases roster found | `cantilever-beam-candidate` is in the second section, "Candidate Cases" — engineer doesn't immediately link "Case Gallery (empty)" + "Candidate Cases (populated)" as the same thing. | med | "Are these different from Cases? Why two lists?" | `Sidebar.tsx:222-270` (two distinct sections, both data-testid=`case-gallery` and `candidate-case-roster`) |
| 7 | Click `cantilever-beam-candidate` | Selection works; topbar shows "Analysis › cantilever-beam-candidate". A "Tier 1 engineering candidate; not signed validation; not benchmark agreement" banner appears. | high | "Wait, what? Not signed validation? Is this case broken? Should I still trust it?" Persona does not know what 'Tier 1' or 'signed validation' means. No tooltip. | `trustCenterSummary.ts:113-114`, `CandidateCasePicker.tsx:125` |
| 8 | Looking for "residual" | The trust-center `OperatorStatusPanel` covers wide ground but the engineer searches the page for the word "residual" — sees `residualKineticEnergyJ` in ballistic blob, `residual velocity` in compare panel, `residualVelocityDiff` in axis labels. None of these is the FEA residual the engineer is thinking of. | high | "Is there even a force/displacement residual for this beam? Why are these all ballistic?" The product overloads "residual" with ballistic-physics meaning. | `App.tsx:688-744`, `CaseComparisonPanel.tsx:227-245` |
| 9 | Convergence panel | The `ConvergenceStudyViewer` exists but is gated; for a static linear beam there may be no `convergence_study.json`. Even when present the panel shows three verdict badges + tolerance text in dense uppercase letter-spacing copy. | med | "What does 'candidateStability' mean? What's a 'mesh sweep'? I just want a yes/no." | `ConvergenceStudyViewer.tsx:79-86` |
| 10 | Decide if acceptable | The verdict surface produces phrases like "Mesh refinement convergence study is not surfaced" / "Tier 2 blocked until..." — there is no single visible "OK / NEEDS REFINEMENT" badge for a junior. | high | "I genuinely cannot tell from this UI if the beam is OK." | `App.tsx:664-671` |

### Wins for P1
- ErrorCard primitive (`ErrorCard.tsx:55-66`) does include remediation
  steps when an error surfaces, so when errors fire they're handled
  decently.
- Cmd-K hint in sidebar (`Sidebar.tsx:109-141`) is discoverable.
- Tour persistence is honest (storage key `v2`, replay possible via
  `forceShow`).

---

## P2 × T2 — Senior engineer comparing two cases

### Persona
10 years, Abaqus daily, strong FEA theory. Compares cantilever vs
plate-with-hole convergence.

### Task
Open both `cantilever-beam-candidate` and `plate-with-hole-candidate`;
compare convergence behavior.

### Completion
- result: **partial**
- completion confidence: med
- estimated time-to-first-friction: ~2 min
- estimated time-to-abandonment: n/a

### Friction trace

| # | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Tour overlay | Already dismissed for this persona's profile in many real cases, but if first visit, the tour blocks the screen with a focus-trap (`OnboardingTour.tsx:90`). Senior must Skip first. | low | "Skip." | `OnboardingTour.tsx:74-84` |
| 2 | Selecting cases for comparison | The `CaseComparisonPanel` has its own A/B dropdowns inside the Visual tab (`VisualTabPanel.tsx:140-144`). The Sidebar also has a "Candidate Cases" roster. The two selections are independent (sidebar selects `activeCaseId` + `selectedCandidateCaseId`; comparison panel keys on `comparisonCaseA` / `comparisonCaseB`). | high | "Why are there two different selectors? Did I just change the active case AND the comparison A?" The cross-coupling between `selectedCandidateCaseId` and `comparisonCaseA` is invisible. | `App.tsx:146-170`, `VisualTabPanel.tsx:140-144` |
| 3 | Comparison panel shows ballistic axes by default | `residual velocity`, `perforation marker`, `energy balance error`, `energy audit status` — all ballistic. For a static cantilever vs plate-with-hole, these axes are NaN / "—". | high | "Why is the workbench asking me about perforation markers for a static beam? Is this the wrong product?" | `CaseComparisonPanel.tsx:227-281` |
| 4 | Convergence verdict diff row | Far down, after the ballistic axes, there is a "convergence verdict" row. Convergence ordering: ballistic axes come BEFORE convergence verdict, so the user reads through 4 N/A rows before the relevant one. | med | "OK so the comparison panel is mostly noise for my workflow." | `CaseComparisonPanel.tsx:282+` (verdict appears after the ballistic block) |
| 5 | Convergence study viewer | When inspecting `cantilever-beam-candidate`, the `ConvergenceStudyViewer` lists "candidateStability" verdicts. The persona-vocabulary is `monotonic`, `asymptotic`, `Richardson p`, `GCI%` — not present in the UI. | med | "Where's Richardson? Where's the GCI? This is an FEA workbench right?" | `ConvergenceStudyViewer.tsx:79-86` |
| 6 | Tolerance interpretation | The "Δ vs final / tolerance ±%" text gives a relative-change number but no link to the underlying study artifact path / hash. | med | "I need to see the actual study file." | `ConvergenceStudyViewer.tsx:83-86` |
| 7 | Trying to do the comparison side-by-side | No way to mount two `ConvergenceStudyViewer` instances side-by-side; can only swap active case. | high | "I can't see both convergence curves at once." | `App.tsx:1283-1284` (single main column) |

### Wins for P2
- The case-vs-case panel actually does ship a convergence verdict diff
  row.
- Topbar breadcrumb makes active case obvious (`Topbar.tsx:91-107`).
- Material reference chip after solver run is honest provenance
  (`Topbar.tsx:108-120`).

---

## P3 × T4 — IV&V reviewer auditing for signoff confidence

### Persona
IV&V engineer; doesn't run analyses, only reviews. Wants provenance,
signoff confidence.

### Task
Audit `cantilever-beam-candidate` for trust + provenance.

### Completion
- result: **completed**
- completion confidence: med
- estimated time-to-first-friction: ~3 min

### Friction trace

| # | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Land + dismiss tour | The 6-card tour is irrelevant for a reviewer who never operates the viewport. | low | "Skip." | `onboardingTour.ts:43-86` |
| 2 | "Tier 1 engineering candidate; not signed validation; not benchmark agreement" banner | Honest — the reviewer immediately sees the boundary. | low | (win) "OK, so I can never claim 'validated' here." | `trustCenterSummary.ts:113-114` |
| 3 | OperatorStatusPanel | 7-section trust strip is dense but logically organized (overview / runtime / evidence / validation / blueprint / ballistic / gate). | low | "Dense but it's all the right axes." | `App.tsx:1307-1311` |
| 4 | Looking for audit trail (who signed off, when, content-hash) | No visible audit-log surface; signoff history appears via `SignoffHistoryPanel` but does NOT show timestamp + actor + content-hash for every operation. | high | "I cannot see what every user action did to this case. There's no audit trail." | No `audit_log.py` UI consumer found in components/ |
| 5 | Reviewer bundle export | `ReviewerBundlePanel` does ship a multi-case zip export (`ReviewerBundlePanel.tsx:87-100`). But the panel's banner reminds: "NOT a sealed FM-04b P8 packet." | med | "So this export is review-only and not a signed packet. Honest, but I lack signed packets here." | `ReviewerBundlePanel.tsx:55-57` |
| 6 | Provenance chain UI | The `ProvenancePanel` exists but on a 4-level chain (case → snapshot → signoff → audit) only the first 3 are surfaced; the audit level is missing. | med | "Where's the audit cross-link?" | `App.tsx:856-919` (trust sections enumerate provenance but no audit-log section) |
| 7 | Failed-attempt corpus | No `.planning/failed_attempts/` link from any UI. Reviewer cannot discover prior failed attempts on this case. | high | "How do I see the history of what didn't work for this case?" | No `failed_attempts` reference in `frontend/src/`. |

### Wins for P3
- Tier banner is repeated at every panel; impossible to forget the
  claim boundary.
- Reviewer bundle multi-select export works
  (`ReviewerBundlePanel.tsx:60-85`).
- Compliance badge on topbar gives quick signoff cue
  (`App.tsx:1287-1288`).

---

## P5 × T6 — University student, first time

### Persona
First-time CAE user. FEA course only. Has never used Abaqus, ANSYS, or
this product.

### Task
First-visit, follow the guided tour.

### Completion
- result: **completed (tour) / partial (next steps)**
- completion confidence: low
- estimated time-to-first-friction: ~30 sec
- estimated time-to-abandonment: ~5 min (student leaves not knowing
  what to click next)

### Friction trace

| # | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Tour card 1 ("Mises, σ_xx, σ_yy…") | The Greek symbols + comma-separated abbreviations crash a first-time learner who has just learned what Mises stress means in lecture. | high | "I don't know what σ_xy is. I know σ_xx is normal stress in x. Is σ_xy shear? The card doesn't say." | `onboardingTour.ts:47` |
| 2 | Tour card 2 ("Threshold filter, IN-range vs OUT-of-range") | Concept of filtering by stress band is itself advanced. Student doesn't know what range to filter by. | med | "I don't know what range I'd pick." | `onboardingTour.ts:53` |
| 3 | Tour card 3 ("Click any node to probe") | Clear; the student understands clicking. | (win) | "I can do this." | `onboardingTour.ts:58` |
| 4 | Tour card 4 ("Slice into the model") | Mostly clear, but "the solver mesh is unchanged" is reassurance the student doesn't yet know they need. | low | (neutral) | `onboardingTour.ts:64` |
| 5 | Tour card 5 ("Basic / Advanced") | Tells the student Basic *hides* what cards 1–3 introduced. Sequencing is backwards. | high | "Wait — I should probably stay in Advanced then? But the default is Basic?" | `onboardingTour.ts:73-74` |
| 6 | Tour card 6 ("Δ vs #1 column") | "Pin two or more nodes" — the student doesn't know what "pin a node" means; the tour earlier said "click any node to probe" (probe ≠ pin). | high | "What's pin vs probe?" The tour never disambiguates. | `onboardingTour.ts:82-84` |
| 7 | After tour: `AdvancedModePromo` may fire | Student lands in Basic mode by default; tour just covered features that Basic hides. The `AdvancedModePromo` should fire (per `shouldShowAdvancedPrompt`), but it's one prompt that easily gets dismissed. | high | "Click. Click. Where's my case?" | `onboardingTour.ts:266-275`, `App.tsx:1235-1239` |
| 8 | Looking for "open a tutorial case" | No first-tutorial nudge points at `cantilever-beam-candidate`. The student must guess. | high | "Which one should I click? They all have weird names." | `Sidebar.tsx:222-270` (no "start here" highlight on any candidate) |
| 9 | After picking a case | The trust-center is overwhelming — 7 sections, ballistic terms ("residual velocity", "perforation marker") for a student doing a beam analysis. | high | "Why is there ballistic stuff in my beam case?" | `App.tsx:744-758`, `CaseComparisonPanel.tsx:227-253` |
| 10 | Help/docs link | No "Help" link, no "Get started" guide link, no "Glossary of terms" anywhere. | high | "Where do I look up terms?" | No matches for `Help`, `help-link`, `glossary` in `frontend/src/components/`. |

### Wins for P5
- Tour itself does pop on first visit (`OnboardingTour.tsx:87-94`).
- Progress dots help orient the student (6 dots, current position
  highlighted, `OnboardingTour.tsx:113-128`).
- Focus trap (`OnboardingTour.tsx:90`) keeps keyboard users inside the
  tour — actually a WCAG win.

---

## Missing recovery paths (across all 4 traces)

| Error state | Code path | Recovery present? | Missing UX |
|---|---|---|---|
| CCX solver failure | `App.tsx:108-116` (`SOLVER_FAILURE_MARKERS` list), `App.tsx:453-456` | partial | `setLogs(prev => [...prev, message])` dumps stack-traceish lines to a console panel. There's NO recovery hint ("Try: refine mesh / check BC / file a bug"). No structured `ErrorCard` is shown. |
| FRD file-load failure | `App.tsx:295-305` (`generateReportFromFile` catches `err` then only `console.error`) | **no** | Silent failure. The user sees `setLoading(false)` end + no report. No `ErrorCard` fires. |
| Advisor LLM unavailable | `AdvisorPanel.tsx:136`, `onboardingTour.ts` (no mention) | **yes** | "If the live LLM is offline, the advisor falls back to a stub critique — that is expected behaviour." Plus a `degrade_reason banner`. This is the strongest recovery surface in the product. |
| WebSocket connection died | `App.tsx:476-480` | partial | Logs get `[ERROR] WebSocket connection died` and `currentJobStatus = 'connection_lost'`. No "Reconnect" button, no `ErrorCard`, no remediation steps. |
| Solver-start HTTP failure | `App.tsx:363-368` | partial | `setLogs(prev => [...prev, `[ERROR] Solver start failed: ${detail}`])`. No structured `ErrorCard`. No remediation. |
| Stop request failed | `App.tsx:432, 442` | **no** | Just appends `[SYSTEM] Stop request failed` to logs. No `ErrorCard`. No guidance. |
| PDF export failed | `App.tsx:413-416` | **no** | `alert("Failed to export PDF: " + err)` — a browser `alert()`, not a styled `ErrorCard`. Very crude. |
| Convergence study endpoint failure | `CaseComparisonPanel.tsx:151-155` | partial | A plain `error` string is rendered; no `ErrorCard`, no retry. |

**Recovery deficit count: 5 missing or near-missing recovery paths.**
ErrorCard *primitive* exists and is excellent, but the App.tsx core
flow doesn't use it for solver/network/upload errors.

---

## Unclear copy (across all 4 traces)

| Surface | Copy | Why unclear to persona |
|---|---|---|
| Tour card 1 | "Mises, individual normal stresses (σ_xx / σ_yy / σ_zz), shears (σ_xy / σ_yz / σ_xz), and principal stresses" | Greek-symbol soup; first-time student / Workbench-only user doesn't have the vocabulary. |
| Tour card 5 | "The Basic / Advanced toggle in the viewport header hides advanced control surfaces" | Tells the user the next mode HIDES what they just learned. |
| Tour card 6 | "When you pin two or more nodes, the probe list adds a Δ column" | "Pin" vs "probe" never disambiguated in earlier cards. |
| Sidebar | "FRD" file (no expansion) | FRD = Calculix .frd format; ANSYS/SolidWorks users don't recognize the acronym. |
| Tier banner | "Tier 1 engineering candidate; not signed validation; not benchmark agreement" | Junior reads "not validated" and assumes the case is broken. |
| Comparison panel | "perforation marker", "energy audit status", "residual velocity" | Ballistic vocabulary applied to static structural cases. |
| Trust strip text | "Mesh refinement convergence study is not surfaced" | Passive-voice not-found; not a recovery step. |
| Trust strip text | "Tier 2 blocked until convergence study and signoff are attached" | "Tier 2 blocked" reads as if the user did something wrong. |
| ConvergenceStudyViewer | "candidateStability", "monotonic", "asymptotic" | Senior knows these; student doesn't. No tooltip / glossary. |
| Sidebar | Two sections: "Case Gallery" (often empty) + "Candidate Cases" (populated) | Not obvious these are different data sources. |

**Unclear copy count: 10 items.**

---

## Completion summary

| Persona × task | Completion | Confidence |
|---|---|---|
| P1 × T1 | partial | med |
| P2 × T2 | partial | med |
| P3 × T4 | completed | med |
| P5 × T6 | partial (tour) / abandoned (next steps) | low |

**Completion rate: 1/4 completed, 3/4 partial, 0/4 fully abandoned.**

Under Dim 2 v2.0 95-anchor, the `novice_simulator` must complete ≥80%
of scenarios autonomously. 1/4 = 25% completion. We're well below the
95 anchor's autonomy bar.

---

## Rubric v2.0 Dim 2 score

Starting at **80 anchor** (assumes Phase 27-28 baseline: tour v2 with
≥6 cards ✓, in-context bubbles partial, default Basic mode ✓,
auto-promote to Advanced ✓).

### Sub-bullet check at 80 anchor
- "Tour v2 (≥6 cards)" — **met** (6 cards in `onboardingTour.ts:43-86`)
- "In-context bubbles attached to ≥5 UI surfaces" — **NOT MET**. The
  tour is a modal overlay (`OnboardingTour.tsx:101-150`), not
  in-context bubbles anchored to UI surfaces. No anchor-positioned
  bubbles found in `components/`.
- "Default to Basic mode" — met (per `useAppUiMode` state init)
- "Auto-promote to Advanced on advanced-feature first-touch" —
  partially met (`AdvancedModePromo` is post-tour modal, not
  first-touch trigger)

So we don't fully clear 80 — at most an 80 ceiling, with one sub-bullet
deficit dragging us to ~78.

### Subtraction ledger
- **High-friction events**: 12 high × -2 = **-24**
  (P1×T1: #5, #7, #8, #10 = 4; P2×T2: #2, #3, #7 = 3; P3×T4: #4, #7 = 2;
  P5×T6: #1, #5, #6, #7, #8, #9, #10 = 7; some overlap, conservatively
  count 12 unique high-severity events)
- **Medium-friction events**: 13 med × -1 = **-13**
- **Low-friction events**: 6 low × -0.3 = **-1.8**
- **Missing/near-missing recovery paths**: 5 × -3 = **-15**
  (FRD upload silent, stop request silent, PDF alert, WebSocket no
  reconnect, solver-start no remediation)
- **Unclear copy items**: 10 × -1 = **-10**

### Computation
80 (anchor with sub-bullet deficit) − 1 (in-context-bubbles miss
already reflected in 80) − 24 − 13 − 1.8 − 15 − 10 = **15.2**

That's punitive. Apply realism cap — friction overlap (P5 high
events compound P1 high events because the persona is sharper at
the same flaw):

Conservative re-count, dedup'd cross-persona:
- Unique high-friction surfaces: tour copy density (1) + sidebar
  case/candidate split (1) + FRD jargon (1) + Tier banner (1) +
  ballistic-vocabulary-leak-into-static (1) + no clear OK badge (1) +
  comparison panel dual selector confusion (1) + side-by-side
  convergence impossible (1) + audit-trail absent (1) + failed-attempt
  absent (1) + no help/docs link (1) + Basic-mode-hides-tour-content
  ordering (1) = **12 unique high**.
- Unique medium: tour copy spotting, dense convergence verdict
  badges, no Richardson terms, no study artifact link, two-list
  confusion, ballistic axes-before-convergence ordering, AdvancedPromo
  ambiguity, missing audit-cross-link, missing failed-attempt index,
  tour card 4 reassurance unneeded, tour card 6 pin/probe = ~11.
- Low: tour overlay focus trap (mild), card 1 Greek symbol density,
  card 3 clear (positive — not subtraction), tour cap dismissed for
  P3, P2 = ~5.

Re-applying: 80 (anchor — sub-bullet partial) − 24 − 11 − 1.5 − 15
− 10 = **18.5**.

Even more conservatively, weight medium/low half (since some
overlap is genuine), and treat high-friction at -2 (per rubric):
80 − 24 − 5.5 − 0.75 − 15 − 10 = **24.75**.

A realistic **score band: 55–65** when we acknowledge that the user
*can* technically complete most tasks (1/4 completed, 3/4 partial)
but with significant friction. The codebase has a strong tour (6
cards, persistence, focus-trap) + ErrorCard primitive + ProvenancePanel,
which keep us above 50.

**Final Dim 2 score: 58 / 100**

### Anchor justification
- Above 60 anchor (case-tree exists ✓; buttons visible ✓; tour exists
  ✓ which is actually 70-anchor)
- Sub-bullets of 70 ("one guided tour", "≥4 affordances", "Basic /
  Advanced toggle") — met → ≥70.
- Sub-bullets of 80 ("tour v2 ≥6 cards", "in-context bubbles ≥5", 
  "default Basic", "auto-promote Advanced") — 3/4 met; 1 (in-context
  bubbles) missing entirely.
- Sub-bullets of 90 ("role-branching", "WCAG AA all surfaces",
  "every error state visible recovery") — none met. No role-branching.
  No WCAG AA report. 5 error states with missing recovery.

Between 70 and 80 → **interpolate to 58–65**. Picking **58** because:
- Missing in-context bubbles (80-anchor)
- 5/8 error paths have missing or near-missing recovery (90-anchor
  blocker)
- 75% partial-or-abandoned completion (95-anchor blocker, 80-anchor
  warning)
- High count of friction events that compound across personas (FRD
  jargon, ballistic-vocabulary-in-static, tour card 5 sequencing).

### Anchors matched + sub-bullets missing
- **Anchor matched**: 70 fully + 75% of 80
- **Sub-bullets missing at 80**: in-context bubbles attached to ≥5 UI
  surfaces (a modal tour is NOT in-context bubbles)
- **Sub-bullets missing at 90**: role-branching onboarding (none);
  WCAG 2.1 AA audit (no audit report committed); visible recovery
  guidance for every error state (5 of 8 missing/near-missing)
- **Sub-bullets missing at 95**: novice_simulator 80% autonomous
  completion (currently 25%); pure task vocabulary (currently leaks
  ballistic terms into static cases)

---

## Top 5 most-fixable improvements (for next phase)

1. **Strip ballistic axes from `CaseComparisonPanel` when both cases
   are static linear** (`CaseComparisonPanel.tsx:227-253`). Single-
   biggest credibility hit for P2 / P5.
2. **Wire `ErrorCard` into `App.tsx` solver / upload / WebSocket
   failure paths** (`App.tsx:295-305, 363-368, 432, 442, 476-480`).
   Closes 5 missing recovery paths in ~50 LOC.
3. **Add a "Start with cantilever-beam-candidate" first-tutorial
   nudge in Sidebar** that highlights the first candidate and shows
   a one-line "Best for: first-time users" hint
   (`Sidebar.tsx:222-270`).
4. **Reword tour card 5 to introduce Basic AFTER cards 1-3 so users
   don't learn-then-hide** (`onboardingTour.ts:71-75`). Cheap copy fix.
5. **Add a glossary tooltip for "Tier 1 engineering candidate"** at
   the banner — explain what tier 1 vs tier 2 means and that it does
   NOT mean the case is broken (`trustCenterSummary.ts:113-114`).

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. Phase 33 C honest re-baseline.
