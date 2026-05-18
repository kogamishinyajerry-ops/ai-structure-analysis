# Phase 36 D — Industrial UI comparator audit (Rubric v2.0, Dim 3)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Delta read against Phase 35 D baseline of
> 73/100.

## Scope

5 canonical surfaces vs Phase 33 C reference descriptions at
`.planning/test_subagents/references/{case_tree_panel,viewport_3d,results_plot,bc_setup_panel,mesh_visualization}.md`
(all 5 confirmed present). Codebase root
`/Users/Zhuanz/20260408 AI StructureAnalysis`, head commit `4188dc5`
(Phase 36 C).

Phase 36 deltas under review:
- **36 A** (`3c50572`) — PDF + stop-request silent paths routed
  through `useUploadErrorRecovery` hook (`App.tsx:403-440`); 2 new
  option-template helpers (`pdfExportRecoveryOptions`,
  `stopRequestRecoveryOptions`) in
  `state/useUploadErrorRecovery.ts`; "(Phase XX)" suffix stripped
  from 3 `displayLabel` entries in `candidateCaseRegistry.ts`.
- **36 B** (`8315aaa`) — ErrorCard mount **repositioned ABOVE**
  `OperatorStatusPanel` in `App.tsx:1313-1321` (was: between trust
  prose and `TabButtons` at Phase 35 C). ErrorCard gains
  `aria-labelledby` → `titleId` via `useId()`
  (`ErrorCard.tsx:55-68`), `codeFriendly` priority pin
  (`ErrorCard.tsx:43-77`), Retry FormData rebuild fix. 4 option
  templates now carry humanized `codeFriendly` strings: `'Upload'`,
  `'Case load'`, `'PDF export'`, `'Stop request'`.
- **36 C** (`4188dc5`) — 7-entry failed-attempt corpus seeded at
  `.planning/failed_attempts/` (planning artifact, NOT a UI
  surface). New `runnerAvailable` field on
  `CaseRecord` (`candidateCaseRegistry.ts:38,57,72,89,108,131,148,165`)
  + small amber "demo · no live runner" badge in
  `CaseOpenAdvisorCard.tsx:72-79`.

None of `App.tsx` mount changes, `ErrorCard.tsx`,
`CaseOpenAdvisorCard.tsx`, `useUploadErrorRecovery.ts`, or
`candidateCaseRegistry.ts` are one of the **5 canonical reference
surfaces** (case_tree / viewport_3d / results_plot / bc_setup /
mesh_visualization). Per Phase 34 D + Phase 35 D precedent
(non-canonical-surface changes evaluated for convention parity only,
not direct surface-parity score lift), the Phase 36 changes are
scored against industrial CAE error / status / availability
conventions.

---

## Reference UI descriptions consulted

All 5 in `.planning/test_subagents/references/`:

1. `case_tree_panel.md` — HyperMesh Model Browser.
2. `viewport_3d.md` — Abaqus CAE / ANSYS Mechanical Graphics.
3. `results_plot.md` — ANSYS Solution Information / HyperGraph.
4. `bc_setup_panel.md` — Abaqus Load Module / ANSYS BCs.
5. `mesh_visualization.md` — HyperMesh Mesh / Abaqus Mesh Module.

Industrial-error-surface references (NOT among canonical 5, relevant
for Phase 36 B convention check):
- **Abaqus CAE** — top banner alerts pinned ABOVE the viewport /
  content area; severity-iconed message bar at the top of the work
  canvas; modal alerts on hard failures.
- **HyperWorks** — slide-up Notification Panel + persistent status
  bar; status surfaces above (not below) operational content when
  the failure blocks the workflow.
- **ANSYS Workbench** — docked "Messages" window above the project
  schematic / properties grid; severity-icon + description +
  remediation hyperlinks; vocabulary in plain English ("Could not
  read CAD file") rather than internal enums.
- **Siemens Simcenter** — error pill carries a human-readable
  category label first ("Import error"), internal enum visible via
  hover/tooltip only.

Industrial-runner-availability convention (relevant for Phase 36 C):
- **HyperWorks** — imported model without a corresponding solver
  deck shows an "imported · no solver" tag near the model name in
  the browser tree; muted amber/yellow tone.
- **Abaqus CAE** — read-only model database shows "(read-only)" or
  "(legacy)" suffix on the model name; user cannot accidentally
  submit a solve.
- **ANSYS Mechanical** — demo / training models often carry a small
  "Sample" or "Demo" pill near the analysis-system header.

---

## Per-pillar parity table (5 canonical surfaces)

| Surface | Phase 35 D parity /10 | Phase 36 changes touching this surface | Phase 36 D parity /10 |
|---|---|---|---|
| case_tree_panel | 4.3 | none (no `Sidebar.tsx` edit in 36 A/B/C) | 4.3 |
| viewport_3d | 6.5 | none (`ResultMeshWebGLViewport.tsx` unchanged) | 6.5 |
| results_plot | 3.5 | none (no chart/plot file touched) | 3.5 |
| bc_setup_panel | 1.5 | none (still no BC authoring surface) | 1.5 |
| mesh_visualization | 3.0 | none (no quality / seeding / histogram added) | 3.0 |
| **Mean** | **3.76/10** | — | **3.76/10** |

**Evidence of zero canonical-surface delta:**
- `git show --stat 3c50572 8315aaa 4188dc5` touched files:
  `frontend/src/App.tsx`,
  `frontend/src/components/ErrorCard.tsx`,
  `frontend/src/components/CaseOpenAdvisorCard.tsx`,
  `frontend/src/state/useUploadErrorRecovery.ts`,
  `frontend/src/candidateCaseRegistry.ts`,
  `.planning/failed_attempts/*` (planning artifact).
- None of `Sidebar.tsx`, `ResultMeshWebGLViewport.tsx`,
  `CompanionViewport.tsx`, `ConvergenceStudyViewer.tsx`,
  `TrustScoreTimelineChart.tsx`, `CaseComparisonPanel.tsx`,
  `MaterialPickerPanel.tsx`, `viewportGeometry.ts`,
  `ResultsPlot.tsx`, `MeshViewport.tsx`, or any
  `BCSetupPanel.tsx`-equivalent touched.

---

## Phase 36 changes vs industrial conventions

### Phase 36 A — PDF + stop-request silent paths closed via hook reuse

**What landed (`App.tsx:403-440`, `useUploadErrorRecovery.ts` +40 LOC):**
- PDF export `try/catch → alert("Failed to export PDF: " + err)`
  replaced by `withUploadRecovery(...,
  pdfExportRecoveryOptions(activeCaseId))` → ErrorCard surface
  with title "Could not export PDF report" + 3 remediation steps +
  Retry + `PDF-EXPORT` code.
- Stop-solver `console.error + setLogs` replaced by
  `withUploadRecovery(..., stopRequestRecoveryOptions(jobId))` →
  ErrorCard with title "Could not stop the running solver" + 3
  remediation steps + Retry + `STOP-REQUEST` code.
- `displayLabel` "(Phase 19 B)", "(Phase 20 B)", "(Phase 20 C)"
  suffixes dropped from 3 candidate-case records.

**Industrial-convention parity:**
- Routing all 4 error paths (Upload / Case-load / PDF / Stop)
  through a single recovery hook + ErrorCard surface: ✅ matches
  ANSYS Workbench Messages window's unified handler — vendor
  products converge to one error surface rather than scattered
  per-feature alerts.
- Browser `alert()` removal: ✅ vendor products do not use OS-modal
  alerts for routine operational failures; in-context red banner is
  canonical.
- "(Phase XX)" jargon strip from `displayLabel`: ✅ matches Abaqus /
  HyperWorks vocabulary discipline — user-visible labels carry
  domain terms, not internal versioning.
- Lands inside `App.tsx` (root container) and a state hook; **NOT a
  canonical-surface change**.

### Phase 36 B — ErrorCard mount repositioned ABOVE trust panel + WCAG hardening + humanized pill

**What landed:**
- `App.tsx:1313-1321` — ErrorCard mount now sits ABOVE
  `OperatorStatusPanel` (Phase 35 C had it below trust prose,
  between `OperatorStatusPanel` and `TabButtons`).
- `ErrorCard.tsx:55-68` — `aria-labelledby={titleId}` with
  `useId()`-generated stable id on the title `<strong>`; screen
  readers now announce the title crisply, not the entire card text.
- `ErrorCard.tsx:43-77` — new optional `codeFriendly?: string` field
  that takes priority over `code` for the visible pill copy; raw
  `code` preserved via `data-error-code` attribute for support /
  log correlation. 4 templates updated with `'Upload'`,
  `'Case load'`, `'PDF export'`, `'Stop request'`.
- `selectCase` + `generateReportFromFile` Retry FormData rebuild fix.

**Industrial-convention parity:**
- **Error placement above content** (`App.tsx:1313`): ✅ matches
  Abaqus CAE top-banner + HyperWorks slide-up + ANSYS Workbench
  Messages docked-above. Phase 35 D's inline-flow positioning was
  flagged as the weakest axis ("inline vs banner/docked"); Phase 36
  B materially closes that gap — the error surface now precedes
  the trust prose in the document flow, which mirrors banner-pinned
  vendor conventions on a CSS-flow workbench layout.
- **`aria-labelledby` → title id** (`ErrorCard.tsx:55-68`): ✅
  exceeds vendor norms — most CAE products rely on focus shift
  alone; this codebase already had `role="alert"` +
  `aria-live="assertive"` and now adds a proper accessible name.
- **Humanized pill** (`codeFriendly` taking priority over enum
  `code`, `ErrorCard.tsx:51,75`): ✅ matches Simcenter "Import
  error" + ANSYS Workbench plain-English summaries; preserves the
  internal enum via `data-error-code` for support tickets — that
  dual-surface pattern (human label visible + machine code in DOM
  attribute) is a clean industrial convention.
- Mount remains inline-flow rather than fixed/sticky/banner-pinned:
  ⚠️ partial — the document-order win is real, but a truly
  banner-pinned implementation (CSS `position: sticky` at the
  workbench-top) would land full parity with Abaqus.
- Gap: still no severity tiering (info / warning / error /
  critical) and no log-correlation deep-link beyond the
  `data-error-code` attribute.

**Net assessment for Phase 36 B:** **measurable** convention-parity
lift on placement (the explicit Phase 35 D weak axis) + humanized
vocabulary + WCAG accessible-name. All lands in `App.tsx` mount
position and `ErrorCard.tsx` (Phase 18 D component) — neither is one
of the 5 canonical surfaces.

### Phase 36 C — `runnerAvailable` badge + failed-attempt corpus

**What landed:**
- `candidateCaseRegistry.ts` — `runnerAvailable?: boolean` field on
  `CaseRecord` (line 38); 4 demo cases marked `false`
  (cylinder-pv, plate-with-hole, cantilever, contact-pair Hertz
  variant), 3 marked `true` (live ccx-runnable cases).
- `CaseOpenAdvisorCard.tsx:72-79` — when `runnerAvailable === false`,
  render small "demo · no live runner" badge in the header next to
  the existing "stub · offline-first" status badge.
- `.planning/failed_attempts/` — 7-entry corpus (planning artifact,
  NOT a UI surface; not scored for Dim 3).

**Industrial-convention parity:**
- "demo · no live runner" badge: ✅ matches HyperWorks's "imported ·
  no solver" tag + ANSYS Mechanical "Sample" / "Demo" pill + Abaqus
  "(read-only)" suffix conventions. The vocabulary is in plain
  English ("demo", "live runner"), not internal enums.
- Placement next to the existing stub-badge in the
  `CaseOpenAdvisorCard` header: ✅ groups status-class badges
  together, matching vendor practice of clustering availability /
  read-only / preview tags near the model name.
- Lands inside `CaseOpenAdvisorCard.tsx`, which is **NOT a canonical
  surface** (advisor card surface, not case_tree / viewport_3d /
  results_plot / bc_setup / mesh_visualization).

**Net assessment for Phase 36 C:** small but clean convention-parity
win for runner-availability transparency; lands on a non-canonical
surface so no Dim 3 score lift.

---

## Anchor matching for Dim 3 (rubric v2.0)

Re-verified against current head `4188dc5`:

- **60-anchor** — tokens-based design system, single theme: ✅ met
  (`frontend/src/index.css:3-31`, unchanged).
- **70-anchor** — motion vocabulary documented (≥1 timing curve,
  ≥1 entrance + exit): ✅ met (`polishStyles.ts:77-235`, unchanged).
- **80-anchor** — ≥7 motion-vocabulary surfaces + drag-resize OR
  density toggle OR 4-quadrant layout + dark token primitives:
  partial — same as Phase 34/35 D (5/5 sub-criteria with caveats:
  2-quadrant proxy, no drag-resize, no density toggle, no theme
  toggle). No Phase 36 change.
- **90-anchor** — drag-resize + density + 4-quadrant + collapsible
  rails ALL shipped + parity ≥7/10 on ≥5 surfaces: ❌ not met. Mean
  parity still 3.76; viewport_3d alone at 6.5.
- **95 / 99-anchor** — ❌ not met.

**Phase 36 D Dim 3 score: 73/100.** Confidence: **medium** (rubric
noise band ±2). The Phase 36 B mount-repositioning + codeFriendly
humanization + Phase 36 C `runnerAvailable` badge are **real
convention-parity wins** that land on industrial-CAE-aligned axes
(error-above-content, humanized vocabulary, availability
transparency), but **all three land on non-canonical surfaces**
(`App.tsx` mount position, `ErrorCard.tsx`,
`CaseOpenAdvisorCard.tsx`) — not on case_tree / viewport_3d /
results_plot / bc_setup / mesh_visualization.

**Delta vs Phase 35 D's 73: 0 (held).**

The task brief explicitly anticipated this outcome ("Δ 0 to +1
within noise band"). Phase 36 B closes the single weakest axis the
Phase 35 D audit called out ("inline vs banner/docked positioning"),
which would justify a within-noise-band +1 if it landed on a
canonical surface — but the wins compound on Dim 2 (novice UX —
error visibility, vocabulary clarity) and Dim 4 (AI workflow
integration — advisor status discrimination) rather than on Dim 3's
5-surface mean. Held at 73 per anti-gaming guard G:-1 (measure what
the codebase IS at the canonical surfaces, not what the convention
lifts deserve in adjacent zones).

---

## Wins (non-canonical surfaces — Dim 3 ledger, uncountable)

1. Error surface placement above trust prose (`App.tsx:1313`) — closes
   Phase 35 D's flagged weakest axis vs Abaqus/HyperWorks/ANSYS
   conventions. **Real convention parity lift; non-canonical surface.**
2. `aria-labelledby` → `useId()` title id on ErrorCard
   (`ErrorCard.tsx:55-68`) — exceeds vendor norms on screen-reader
   accessibility.
3. `codeFriendly` humanized pill with `data-error-code` preservation
   (`ErrorCard.tsx:43-77`) — clean dual-surface pattern (human label
   visible + machine code in DOM attribute) matching Simcenter /
   Workbench plain-English convention.
4. `runnerAvailable` "demo · no live runner" badge
   (`CaseOpenAdvisorCard.tsx:72-79`) — matches HyperWorks "imported ·
   no solver" + ANSYS "Demo" pill conventions.
5. "(Phase XX)" suffix strip from `displayLabel`
   (`candidateCaseRegistry.ts`) — vendor-aligned vocabulary
   discipline.

---

## Open gaps (carry-forward from Phase 35 D, unchanged)

Top-5 anchor-leverage gaps for Phase 37+ still apply verbatim:

1. **Drag-resize panels** (90-anchor blocker) —
   `react-resizable-panels` splitter on left+right rails. Not started.
2. **Density toggle (compact/comfortable)** (90-anchor blocker) —
   `UiModeToggle.tsx` extension. Not started.
3. **4-quadrant default layout** (90-anchor + 95-anchor blocker) —
   promote `CompanionViewport` from 2-quadrant to 4-region grid. Not
   started.
4. **Collapsible left/right rails** (90-anchor blocker) — chevron
   collapse, motion vocabulary already exists. Not started.
5. **Light/dark theme toggle** (95-anchor blocker) — light token set
   + class-switch root. Not started.

Surface-specific carry-forward gaps (unchanged from Phase 35 D):
- case_tree_panel: right-click context menu, inline rename, drag
  reorder, search box, eye-icon column.
- viewport_3d: view-cube, selection filter, named views, fit-all
  hotkey, color-blind palette toggle.
- results_plot: true Cartesian XY pane with pan/zoom/log-scale +
  CSV export.
- bc_setup_panel: out of scope (product-position; reviewer not
  authoring).
- mesh_visualization: quality histogram, free-edges overlay,
  render-mode toggle, quality recolor.

Phase 36 candidate for "would have moved Dim 3" — a true sticky /
banner-pinned ErrorCard at workbench-top (CSS `position: sticky`)
plus severity tiering (info / warning / error / critical) would
push the error-surface parity past full ANSYS Workbench Messages
parity. Phase 36 B got the document-order win but not the sticky
behavior.

---

## Honest summary

Phase 36 A routes 2 silent error paths (PDF export, stop-request)
through the same `useUploadErrorRecovery` + ErrorCard surface that
Phase 35 C established — unifying 4 error paths on one surface, an
industrial-convention win for handler consolidation. Phase 36 B
repositions the ErrorCard mount ABOVE `OperatorStatusPanel`
(`App.tsx:1313-1321`), adds `aria-labelledby` → `useId()` title id
(`ErrorCard.tsx:55-68`), and introduces a `codeFriendly` humanized
pill that takes priority over enum `code` while preserving the raw
code in `data-error-code` (`ErrorCard.tsx:43-77`) — three crisp
convention-parity wins that close the Phase 35 D weakest axis
("inline vs banner/docked"). Phase 36 C adds a `runnerAvailable`
boolean to the candidate-case registry and surfaces a "demo · no
live runner" badge in the case-open advisor header
(`CaseOpenAdvisorCard.tsx:72-79`), matching HyperWorks / ANSYS / Abaqus
availability-tag conventions.

All three Phase 36 wins live OUTSIDE the 5 canonical-reference
surfaces (case_tree / viewport_3d / results_plot / bc_setup /
mesh_visualization) and therefore do **not** move the surface-parity
mean of 3.76/10.

**Dim 3 stays at 73/100 (medium confidence, delta 0 vs Phase 35 D,
inside the ±2 rubric noise band).** Phase 36's investments
accrued to Dim 2 / Dim 4 surface polish + vocabulary
discipline, not to Dim 3 layout / density / theme / canonical-parity
foundations. The "hold the line at 73" outcome anticipated by the
task brief is the honest read.

Anti-gaming guards observed: A:-1 (no anchor reword), D:-1 (every
parity claim cited to file:line or marked absence), G:-1 (no credit
for convention-parity wins on non-canonical surfaces — rubric
measures what the canonical surfaces ARE).

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
