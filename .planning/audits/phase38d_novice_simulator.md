# Novice simulator report — R6 calibrated re-score · Phase 38D

> Dim 2 — Novice user experience
> Scored strictly against RUBRIC_v2.md anchor checklist.
> Anti-gaming guards D:-1, F:-1, G:-1 observed.

---

## Personas × Tasks exercised

Four persona × task pairings were traced through the codebase:

- **P1 × T6** — Junior engineer (1 yr, SolidWorks + ANSYS Workbench), first visit, follows the guided tour
- **P1 × T3** — Same persona, opens a cantilever case, attempts to change BC, re-run solver
- **P3 × T4** — Reviewer / IV&V, inspects trust/provenance for a candidate case
- **P5 × T7** — University student, solver fails mid-run, tries to recover

---

## Persona 1 (P1) × Task 6 — first visit, guided tour

### Completion
- result: completed
- completion confidence: high
- estimated time-to-first-friction: 0 min (friction is immediate — tour content vocabulary)
- estimated time-to-abandonment: N/A (tour is completable but leaves confusion)

### Friction trace

| Step | Where | Friction | Severity | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Tour card 1 of 6 | Title "Pick the stress component you want to see"; body references "Mises, individual normal stresses (σ_xx / σ_yy / σ_zz), shears (σ_xy / σ_yz / σ_xz), and principal stresses." A 1-year engineer may know Mises; σ notation may not be clear for SolidWorks-primary users. | low | "I know von Mises. What are the shears exactly?" | `onboardingTour.ts:47-50` |
| 2 | Tour card 1 of 6 header eyebrow | Shows "Phase 23 B" — an internal development phase tag visible to the user. | medium | "What does Phase 23 B mean? Is my software out of date?" | `OnboardingTour.tsx:106-109` — `step.shippedInPhase` rendered unconcealed in the card header |
| 3 | Tour card 2 of 6 | "elements with no value (e.g. dead or projectile) remain visible" — "projectile" is ballistic-specific jargon the P1 structural engineer has no context for | medium | "What is a projectile? This isn't a ballistics tool, is it?" | `onboardingTour.ts:52-55` |
| 4 | Tour card 5 of 6 | "Basic / Advanced toggle in the viewport header hides advanced control surfaces" — but the toggle is in the *ResultMeshPlaybackPanel* header, not the topbar header. User sees "topbar" as Topbar.tsx's header; the toggle is lower in the page. | medium | "I can't find the toggle in the header, it must be lower somewhere" | `ResultMeshPlaybackPanel.tsx:449` vs `Topbar.tsx` — two different elements |
| 5 | Tour card 6 of 6 | "When you pin two or more nodes, the probe list adds a Δ column" — novice doesn't know how to "pin" a node yet. No instruction on HOW to pin is in the tour. | medium | "What does 'pin' mean? The tour says click nodes but now it's 'pin'?" | `onboardingTour.ts:83-85` (step id='probe-diff-column'); pinning = addProbeEntry(`probeList.ts`), not explained |
| 6 | AdvancedModePromo after tour dismissal | Eyebrow text "Phase 25 C · Phase 28 D" visible to end user | medium | "What is Phase 25 C? Why does my software show developer labels?" | `AdvancedModePromo.tsx:132` — `<span style={STYLES.eyebrow}>Phase 25 C · Phase 28 D</span>` |
| 7 | Landing state (no case selected) | The empty-state below the tab buttons shows an icon and "Select a structural case from the gallery to begin analysis" | low | "OK, I go to the sidebar?" | `App.tsx:1443-1446` — helpful message but generic; no arrow/highlight pointing to sidebar |
| 8 | CaseBrowser (when no case active) | `CaseBrowser` appears above tabs when `!activeCaseId` (`App.tsx:1314`). Its functional affordances overlap with the Sidebar. Two parallel case-selection flows exist with no explanation. | medium | "There are two lists of cases. Which one do I use?" | `App.tsx:1243-1271` (Sidebar) vs `App.tsx:1314-1318` (CaseBrowser) — dual case-selection paths |

---

## Persona 1 (P1) × Task 3 — change BC, re-run

### Completion
- result: partial
- completion confidence: low
- estimated time-to-first-friction: ~1 min (cannot locate BC editing UI)
- estimated time-to-abandonment: ~5 min

### Friction trace

| Step | Where | Friction | Severity | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | After selecting a case, looking for BC editing | The product has `BCSetupPillList` and `BCSetupAdvisorCard` which are *read-only* orientation panels, not editable BC editors. There is no form to change a BC value. | HIGH (DEAD-END) | "I see the BC described but I can't change it. Where do I change it?" | `BCSetupAdvisorCard.tsx:57-117` (read-only card); `BCSetupPillList.tsx` (read-only list); no BC input form exists in the frontend |
| 2 | SensitivityForm (Exploration tab) | The "Parametric Study" does allow Load magnitude and Young's Modulus variation — but it's hidden behind a 3rd tab ("Exploration") which only appears when a case is active (`App.tsx:1323`). No guidance points to this from the BC advisor cards. | HIGH | "There's no BC editor. The BC advisor shows my BCs but there's no edit button." | `App.tsx:1323` (`activeCaseId && <TabButton ... label="Exploration">`); `ExplorationTabPanel.tsx:30-77` |
| 3 | Exploration tab discovery | Tab "Exploration" with `<Compass size={16} />` icon. The label is "Exploration" — not "Parameter Study" or "Change BC". Novice may not recognize this as the BC-change entry point. | medium | "Exploration? That doesn't sound like 'edit BC'." | `App.tsx:1323` — tab label="Exploration" |
| 4 | Sensitivity form — parameter label | Dropdown shows "Load Magnitude (*CLOAD)" and "Young's Modulus (*ELASTIC)" — CalculiX card syntax visible to the user | medium | "What is *CLOAD? Is that the load I defined?" | `SensitivityForm.tsx:39-45` — raw CalculiX keyword labels |

---

## Persona 3 (P3) × Task 4 — reviewer audits trust + provenance

### Completion
- result: completed
- completion confidence: high
- estimated time-to-first-friction: ~2 min (vocabulary)

### Friction trace

| Step | Where | Friction | Severity | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | OperatorStatusPanel headings | "Validation & Trust Center / Evidence-first workbench state" — the P3 reviewer (IV&V background) will understand; good orientation. | win | "OK, trust center is clearly labeled." | `OperatorStatusPanel.tsx:73-74` |
| 2 | Trust strip + sections | 7 collapsible sections (Overview, Runtime, Evidence, Validation, Blueprint, Ballistic, Gate) — "Ballistic" is present even when the selected case is a structural cantilever. A reviewer for structural cases will see Ballistic section with "unavailable" data. | low | "Why is there a Ballistic section on my cantilever beam?" | `useTrustSections` always renders all 7 sections regardless of case type |
| 3 | "Tier 0 sandbox/demo" claim tier label | "Tier 0 sandbox/demo — not signed validation" is shown for any case without a spine. P3 reviewer may be unsure if this is an error or the expected state for internal review. | low | "Is Tier 0 bad? Am I doing something wrong?" | `App.tsx:543` (`const claimTier = candidateSpine?.claim_tier ?? 'Tier 0 sandbox/demo'`) |
| 4 | "CaeReviewCard / claim_boundary" | Reviewers need the right-rail `Copilot` panel to see the review cards. "Copilot" is a button label — a P3 reviewer may not know Copilot = trust review cards. | medium | "What is Copilot? Is that an AI chat? I want the reviewer checklist." | `Topbar.tsx:137-150` — Copilot button; `App.tsx:1463-1470` RightRail |

---

## Persona 5 (P5) × Task 7 — student, solver fails mid-run, recover

### Completion
- result: completed (with guidance)
- completion confidence: medium
- estimated time-to-first-friction: ~0.5 min (no case pre-selected)

### Friction trace

| Step | Where | Friction | Severity | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Solver start failure | `ErrorCard` surfaces with title "Could not start the solver", message, 3 remediation steps, Retry button. Clear and actionable. | WIN | "OK, I see the error with steps to fix it. I can retry." | `useUploadErrorRecovery.ts:159-168`, `App.tsx:1301-1305` — ErrorCard mounts above OperatorStatusPanel |
| 2 | Remediation step wording | Step 1: "Read the workbench console for the upstream detail message" — "upstream" is developer vocabulary. "Upstream" = backend. A student doesn't know what "upstream" means. | medium | "What is 'upstream'? Where is that?" | `useUploadErrorRecovery.ts:212` ("Confirm the backend at /api/v1/solver/run is reachable") — step 2 also exposes API path directly |
| 3 | WebSocket death mid-solve | `ws.onerror` appends "[ERROR] WebSocket connection died" to the console log and sets `currentJobStatus = 'connection_lost'`. The connection-lost status changes `runStateTone` to 'warning' (amber) in the OperatorStatusPanel, but there is **no ErrorCard** surfaced for WebSocket death — only a console log line that requires the user to have `showConsole=true`. | HIGH | "The solver stopped. I see something amber at the top but the console is hidden. What happened?" | `App.tsx:460-464` (`ws.onerror` → log only + status); contrast with ErrorCard for other failures |
| 4 | Sensitivity study failure | `useSensitivityStudy` hook wires failures to `withUploadRecovery` → `ErrorCard` (Phase 38 I). Study-run failures now surface an ErrorCard with Retry. | WIN | "Study failed but I can see the error and retry." | `useUploadErrorRecovery.ts:177-185`; `App.tsx:834-844` |

---

## Missing recovery paths

| Error state | Code path | Recovery present? | Missing UX |
|---|---|---|---|
| CCX solver failure (CalculiX exit with error code) | `App.tsx:437-442` — `isSolverFailureLog` detects `'Solver exited with code:'` in log stream; sets `currentJobStatus='failed'`; console shows `[ERROR]` line | partial | Console shows the failure only if `showConsole` is open. The `runStateTone='warning'` amber appears in the OperatorStatusPanel header but there is no ErrorCard surfaced for CCX failures detected via WebSocket log (contrast: solver START failure has an ErrorCard; CCX failure during run does not) |
| Mesh failure | No dedicated mesh-failure error path exists in the frontend. `ResultMeshPlaybackPanel.tsx:471-481` shows ErrorCard for result_mesh.json load failure, with 2 remediation steps. | partial | Result-mesh load failure is recovered; but a failed mesh generation during solve is only visible in the console log |
| BC mismatch | No BC mismatch UI detection or error surface exists. BCs are read-only orientation panels; there is no user-editable BC form and no mismatch validator. | absent | A user who sets up a wrong BC has no feedback path in the UI |
| Advisor LLM unavailable | `AdvisorPanel.tsx:55` — "offline: 'LLM unavailable (stub fallback)'" status string. The stub is surfaced as a text badge; no blocking error. | present | Graceful degradation: AdvisorPanel displays "stub fallback" state. Recovery is transparent to user. |
| File format error (FRD upload) | `useUploadErrorRecovery.ts:98-108` → ErrorCard with "Could not generate report from upload" + Retry button. | present | ErrorCard clear. Step 2 advises "Try a smaller or alternative .frd / .inp file" — actionable. |
| WebSocket connection death mid-solve | `App.tsx:460-464` — `ws.onerror` → log-only + `currentJobStatus='connection_lost'` + `runStateTone='warning'` | partial | Only console log + amber tone. No ErrorCard, no explicit guidance to "refresh or re-select the case". This is a high-severity gap for novice users: the solver silently stalls with no actionable guidance in the main UI. |

---

## Unclear copy

| Surface | Copy | Why unclear to persona |
|---|---|---|
| OnboardingTour card header | "Phase 23 B" (eyebrow) | Developer internal phase tag; P1 student reads this as "my software is version Phase 23 B" or "is this out of date?" (`OnboardingTour.tsx:106`) |
| AdvancedModePromo eyebrow | "Phase 25 C · Phase 28 D" | Same problem: internal phase labels visible to end user (`AdvancedModePromo.tsx:132`) |
| Tour card 2 body | "elements with no value (e.g. dead or projectile)" | "projectile" implies ballistics context; irrelevant to P1 structural engineer; confusing. (`onboardingTour.ts:53`) |
| SensitivityForm parameter dropdown | "Load Magnitude (*CLOAD)" | CalculiX card syntax `*CLOAD` visible. P1 user knows load magnitude, not the keyword. (`SensitivityForm.tsx:41`) |
| Recovery step 1 | "Read the workbench console for the upstream detail message" | "upstream" = developer jargon for backend. Novice doesn't know what upstream means. (`useUploadErrorRecovery.ts:212`) |
| Recovery step 2 | "Confirm the backend at /api/v1/solver/run is reachable" | Exposes internal API path. A novice cannot "confirm a backend endpoint is reachable". (`useUploadErrorRecovery.ts:213`) |
| Topbar Copilot button | "Copilot" | P3 reviewer looking for signoff/review panel may not understand that "Copilot" = trust review cards panel. (`Topbar.tsx:151`) |

---

## Rubric v2.0 Dim 2 — anchor evaluation

### Anchor checklist

**Anchor 60 — base:**
- Feature buttons visible: YES (`App.tsx:1320-1324` tab buttons visible; Sidebar accessible)
- Case-tree exists: YES (`Sidebar.tsx`)
- No guidance on what to do first: PARTIALLY MET — empty state copy exists but no highlighted path

**Anchor 70 — one guided tour pops on first visit; covers ≥4 affordances; Basic/Advanced mode toggle exists:**
- One guided tour on first visit: YES (`OnboardingTour.tsx` with localStorage gate)
- Covers ≥4 affordances: YES — 6 cards (`onboardingTour.ts:43-86`)
- Basic/Advanced toggle: YES (`uiMode.ts`, `UiModeToggle.tsx`)
All 70-anchor sub-bullets: MET.

**Anchor 80 — Tour v2 (≥6 cards); in-context bubbles on ≥5 UI surfaces; default Basic mode; auto-promote to Advanced on first-touch:**
- Tour v2 (≥6 cards): YES — `ONBOARDING_STEPS` has 6 entries; comment says "FM-04a Phase 27 D — tour copy refreshed to v2 (6 steps)" (`onboardingTour.ts:3-7`)
- In-context bubbles on ≥5 surfaces: **ABSENT.** The product has no in-context tooltip bubbles attached to individual UI surfaces. The `CoordReadoutTooltip` is a coordinate-readout hover, not an in-context "here's what this button does" bubble. No `data-tippy`, no `Popover`, no contextual overlay system attached to ≥5 surfaces. Only the tour modal and the two advisor cards exist.
- Default Basic mode: YES (`UI_MODE_INITIAL: 'basic'` in `uiMode.ts:56`)
- Auto-promote to Advanced on advanced-feature first-touch: **PARTIAL.** The product auto-promotes via `AdvancedModePromo` after tour dismissal (`onboardingTour.ts:266-275`), but this fires on tour dismissal, not on actual first-touch of an advanced feature. The spec says "auto-promote on advanced-feature first-touch"; the implementation is "prompt after tour ends". This is close but not the same — basic mode users who skip the tour never see the promo unless they dismiss the tour.

**80-anchor verdict:** The **in-context bubbles on ≥5 surfaces** sub-bullet is NOT met. This is a checklist item, not a partial condition. The anchor says "ALL sub-bullets met." Therefore the product does NOT fully clear anchor 80.

The product clears all 70-anchor sub-bullets and partially meets 80 (2 of 3 sub-bullets fully met; 1 absent; 1 partial).

**Interpolation:**

70 fully met + 2/3 of 80's sub-bullets met → 70 + (2/3 × 10) = ~76.7, round to **77**.

However, against the scored friction and recovery paths:

- **Error recovery coverage**: 5 of 6 major error paths have at least partial recovery. The WebSocket mid-run death has NO ErrorCard (HIGH gap). CCX failure during run has NO ErrorCard (HIGH gap — only console log which may not be visible).
- **Role-branching paths**: absent (90-anchor). The product only has Basic/Advanced; no engineer/reviewer/student branching.
- **WCAG 2.1 AA**: Phase 38 G updated all 10 surfaces to PASS for the 6 audited criteria — this is partial but not a full AA audit. Additional criteria (1.4.11, 2.4.7, 3.3.3, 4.1.3) remain TODO.
- **Developer labels leaked to users**: Two internal "Phase X" labels visible in the live UI (OnboardingTour.tsx:106, AdvancedModePromo.tsx:132) are a novice trust/confusion issue.

The WebSocket death gap (HIGH severity: no ErrorCard; console only; solver stalls with no visible recovery path in main panel) is a notable usability hole but does not constitute a full dead-end (the amber tone in OperatorStatusPanel is visible). Combined with the developer labels and the BC-editing dead-end, the score sits in the 75-78 range rather than above 80.

**Final Dim 2 score: 77**

---

## Rubric v2.0 Dim 2 contribution

- Anchor landed: **70** (all sub-bullets confirmed met)
- Interpolation rationale: 2 of 3 anchor-80 sub-bullets met: Tour v2 ✓ · default Basic mode ✓ · in-context bubbles ✗ (absent on ≥5 surfaces). Auto-promote partial (tour-dismiss trigger, not first-touch trigger). → 70 + (2/3 × 10) ≈ 77.
- 2 HIGH-severity friction events: (a) BC-editing dead-end — no editable BC form; advisor cards are read-only; Exploration tab partially substitutes but is unlabelled as BC-change; (b) WebSocket death mid-solve — no ErrorCard, no recovery guidance visible without open console panel.
- 1 HIGH missing recovery path: WebSocket connection death (`App.tsx:460-464`) — log + tone change only; no ErrorCard with remediation steps.
- 3 medium friction events: developer "Phase X" labels in onboarding UI; dual case-selection flows (Sidebar + CaseBrowser); CalculiX `*CLOAD` jargon in SensitivityForm.
- WCAG: 6-criterion sweep PASS on 10 surfaces (Phase 38 G); 4 additional criteria (1.4.11, 2.4.7, 3.3.3, 4.1.3) not yet audited — partial coverage, not full AA.
- Role-branching paths: absent (90-anchor requirement not met).
- **Dim 2 score: 77 / 100**
