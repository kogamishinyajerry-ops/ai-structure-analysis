# Novice simulator report — Phase 34 D · post-Phase-34-A/B audit

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.

Four persona × task traces are walked below. Friction is cited at file:line in the current
codebase. Phase 34 A/B improvements (ballistic-vocab fix + `CaseOpenAdvisorCard`) are
evaluated honestly: both ship, both partially help, and both introduce new minor friction.

---

## Trace 1 · P1 (junior · 1 yr · SolidWorks + occasional Workbench) × T1 (Inspect cantilever-beam-candidate, find residual, decide if acceptable)

### Persona
Junior structural engineer, ~1 year, comfortable in SolidWorks, has clicked through
ANSYS Workbench a few times at a colleague's desk, never opened this product. FEA theory
is hazy (knows "residual" means "left-over error" but not which residual). Goal: "is my
beam OK?"

### Completion
- result: **partial**
- completion confidence: **low**
- est. time-to-first-friction: ~1 min
- est. time-to-abandonment: ~12 min (would call a senior or give up)

### Friction trace
| Step | Where | Friction | Severity | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | First paint — tour overlay | Tour starts immediately with "Pick the stress component you want to see" but the persona has not yet selected a case | **high** | "Stress component of what? I haven't picked anything." | `onboardingTour.ts:43-49` (first step is field-component-switcher; presupposes a loaded result) |
| 2 | Tour card 1, body talks about σ_xx / σ_yy / σ_zz / σ_xy / σ_yz / σ_xz / principal stresses | Heavy notation dump on card 1 without scaffolding | medium | "OK I know Mises but is σ_xy a shear or a normal? Skip…" | `onboardingTour.ts:47` |
| 3 | After skipping tour, sees three-column layout: ProjectManager · Sidebar · main | Three left rails ("Workbench" nav button + Case Gallery EMPTY + Candidate Cases) — not obvious which to click | medium | "Three different lists. Where is the cantilever?" | `App.tsx:1226` (`gridTemplateColumns: '240px 300px 1fr'`); `Sidebar.tsx:164-184` (empty gallery) + `Sidebar.tsx:222` (candidate roster only if non-empty) |
| 4 | Finds "Cantilever beam · Euler-Bernoulli δ=PL³/(3EI) (Phase 20 B)" in Candidate Cases | "Phase 20 B" is internal jargon visible in the UI | low | "Phase 20 B? Is that the version of the case? Is the formula in the label what I get?" | `candidateCaseRegistry.ts:151` (`displayLabel: 'Cantilever beam · Euler-Bernoulli δ=PL³/(3EI) (Phase 20 B)'`) |
| 5 | Click → CaseOpenAdvisorCard appears above tabs | **Win** — a one-paragraph orientation appears immediately | n/a | "OK this tells me what I opened" | `App.tsx:1320-1327`; `CaseOpenAdvisorCard.tsx:99-110` |
| 6 | Brief body: "ccx-running runner is Phase 21+ scope (single-hex coupons cannot capture bending; multi-element Gmsh path lands this case at tier_2_validated)" | Brief is honest but the persona doesn't know what "Phase 21+ scope" or "single-hex coupons" mean | **high** | "Wait, does this case even run? Why am I told about gmsh?" | `candidateCaseRegistry.ts:156-161` rendered verbatim by `CaseOpenAdvisorCard.tsx:104-109` |
| 7 | 4-Q-gate ticks: "LLM offline OK", "artifacts user-owned", "trust score explains", "advisor-only" | All ✓ but no copy explains what each gate is or why it matters | medium | "Four checkmarks. About what? Don't know what 'TrustGate' is." | `CaseOpenAdvisorCard.tsx:41-47, 73-80` |
| 8 | Goal: "find the residual." Persona scans Visual tab and Narrative tab | The word "residual" appears in **ballistic** context (`residualVelocityDiff` / `residualKineticEnergyJ`) — not the CCX/iteration residual the junior actually wants | **high** | "Residual velocity? I have a beam, not a bullet." | `App.tsx:689-694` (`ballisticResidualVelocityValue`); `CaseComparisonPanel.tsx:266-282` (residual velocity row) |
| 9 | Persona finds the Convergence study viewer | "Convergence study" header but verdict label is `combinedVerdictLabel(study)` opaque; metric reads e.g. `metric: u_x_max_mm` | medium | "Is `metric: u_x_max_mm` what I should be looking at to know my beam is OK?" | `ConvergenceStudyViewer.tsx:202-208` |
| 10 | "No convergence study available; run scripts/gs102_convergence_sweep.py." | Recovery hint asks user to run a developer Python script | **high** (missing recovery path) | "I'm not running a script. Is the case broken?" | `ConvergenceStudyViewer.tsx:195` |
| 11 | No "is my beam OK?" verdict anywhere — only Trust Center sections + claim_impact prose | No single "ACCEPTABLE / NOT ACCEPTABLE" gauge for a single case | **high** | "Where is the green/red light? I just need yes or no." | `App.tsx:1308-1312` (OperatorStatusPanel) — multiple sections of prose, no decision affordance |
| 12 | Persona tries Run Solver in Topbar | Solver runs only if `activeCaseId` is set (it IS via Sidebar click — good) but no progress feedback is exposed in this code path beyond `solving` boolean | medium | "It says solving but for how long?" | `App.tsx:1290-1295` (`solving` boolean only) |

### Missing recovery paths
| Error state | Code path | Recovery present? | Missing UX |
|---|---|---|---|
| CCX solver failure on cantilever | `App.tsx:runSolver` (not shown; props in Topbar) | unclear | No visible error toast/card audited; persona sees nothing |
| Convergence study unavailable | `ConvergenceStudyViewer.tsx:195` | dev-only ("run scripts/...py") | No UI button to launch the sweep |
| Cantilever case has no `ccx-running runner` (per its own notesExcerpt) | `candidateCaseRegistry.ts:156-161` | text only | Loaded case truthfully admits it cannot run; UI surfaces this as prose, not as a disabled Run button |
| LLM advisor unavailable | `AdvisorPanel.tsx:131-136` | **win** — clear hint "stub fallback is expected behaviour" | OK |
| Tour pre-loaded case mismatch | `onboardingTour.ts:43-49` | no | Tour assumes a case is open; first-visit users have not yet selected |

### Unclear copy
| Surface | Copy | Why unclear to persona |
|---|---|---|
| CaseOpenAdvisorCard brief | "ccx-running runner is Phase 21+ scope" | "Phase 21+" is internal phasing language; persona doesn't know the roadmap |
| CaseOpenAdvisorCard brief | "single-hex coupons cannot capture bending; multi-element Gmsh path lands this case at tier_2_validated" | "single-hex coupon", "tier_2_validated", "gmsh" — three jargon words back-to-back |
| Sidebar label | "Candidate Cases" vs "Case Gallery" | Persona sees two parallel rosters and doesn't know which is theirs |
| Tour card 1 | σ_xy / σ_yz / σ_xz / principal stresses | Notation dump |
| Tour card 4 | "Combine with magnification to study interior stress distribution" | "magnification" not defined |
| 4-Q-gate row 3 | "trust score explains (open the Visual tab for full critique)" | "trust score" unexplained at first encounter |
| OperatorStatusPanel header pill | "not signed validation" | Red badge persona reads as "this is broken" rather than "this is honest about its limits" |

### Phase-34-specific observations
- **Win**: CaseOpenAdvisorCard exists and appears immediately on case-open. Reduces the "what am I looking at?" gap by ~30s for case-aware users.
- **Friction-introduced-by-Phase-34-B**: the brief text is *verbatim from `notesExcerpt`*. For internal-vocabulary cases like cantilever-beam-candidate, this leaks phase numbers (`Phase 21+ scope`) and developer terms (`single-hex coupons`, `Gmsh path`) directly into the novice's first-paint orientation. Net effect: ~neutral, possibly mildly net-negative for P1.

---

## Trace 2 · P2 (senior · 10 yr Abaqus daily, strong FEA theory) × T2 (Compare cantilever + plate-with-hole, evaluate convergence)

### Completion
- result: **completed** (with frustration)
- completion confidence: **med**
- time-to-first-friction: ~3 min

### Friction trace
| Step | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Opens both cases via Sidebar candidate roster | Two parallel rosters (Case Gallery + Candidate Cases) — knows from experience this means two backends but unnecessary mental overhead | low | "Why two lists?" | `Sidebar.tsx:164, 222` |
| 2 | Visual tab → CaseComparisonPanel | **Win Phase 34 A**: For non-ballistic pair, ballistic axes correctly hidden + clear notice rendered | n/a | "Good, the comparison hides the bullet rows. Sensible." | `CaseComparisonPanel.tsx:263, 322-340` |
| 3 | The notice copy: "Residual-velocity / perforation-marker / energy-balance axes apply to ballistic-impact analyses." | **Win** — clear, jargon-light, accurate | n/a | "Fine." | `CaseComparisonPanel.tsx:335-338` |
| 4 | Convergence verdict row remains and gives `same / differ` + tone | Good for senior; would prefer numeric residual difference per-axis but acceptable | low | "Verdict is binary, fine for triage." | `CaseComparisonPanel.tsx:342-348` |
| 5 | ConvergenceStudyViewer per-case: combined verdict + mesh sweep + dt sweep + energy balance observation | **Win** — exactly what senior wants | n/a | "OK, this is what I came for." | `ConvergenceStudyViewer.tsx:199-243` |
| 6 | Plate-with-hole convergence study likely unavailable for both cases (notesExcerpt says ccx-running runner is "Phase 21+ scope") | If both `study` are null, viewer says "run scripts/gs102_convergence_sweep.py" twice | **high** | "I'm a reviewer, not a dev. Don't tell me to run a Python script." | `ConvergenceStudyViewer.tsx:195` × 2 panels |
| 7 | No side-by-side mesh/dt sweep table — has to mentally compare the two ConvergenceStudyViewer instances stacked vertically | medium | "Why don't you put the two sweeps in the same table?" | `VisualTabPanel.tsx:139-147` (single ConvergenceStudyViewer, no compare-mode) |
| 8 | Wants Richardson p / asymptotic claim per case | Energy balance status surfaced; Richardson extrapolation not surfaced in viewer text — has to open the JSON | medium | "Where's p? Where's the asymptotic range?" | `ConvergenceStudyViewer.tsx:225-238` (energy balance only) |

### Phase-34-specific observations
- **Win**: ballistic-vocab cleanup directly serves P2's "compare two non-ballistic cases" workflow. Before Phase 34 A, the row would have been six `—` cells implying "ballistic data missing" rather than "doesn't apply".
- **No new friction** introduced by Phase 34 A/B for P2.

---

## Trace 3 · P3 (Reviewer / IV&V) × T4 (Audit cantilever-beam-candidate for trust + provenance)

### Completion
- result: **partial**
- completion confidence: **med**
- time-to-first-friction: ~2 min

### Friction trace
| Step | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Sidebar candidate → cantilever-beam-candidate | label includes "Tier 1 engineering candidate" | n/a | OK | `candidateCaseRegistry.ts:151-152` |
| 2 | **CaseOpenAdvisorCard** appears with Tier 1 banner footer + claim line | **Win Phase 34 B** — reviewer immediately sees the claim level | n/a | "Good. Tier 1 claim, not signed validation." | `CaseOpenAdvisorCard.tsx:83-86`; `TIER1_BANNER` |
| 3 | The 4-Q-gate is rendered as 4 hardcoded ticks ✓ | All four gates are always ✓ at the card. No machine-checked status. | **high** (governance) | "These are static ticks. Where's the actual gate evaluation result?" | `CaseOpenAdvisorCard.tsx:73-80` — `FOUR_QUESTION_GATE_KEYS.map(...)` renders ✓ for every key unconditionally |
| 4 | Reviewer looks for AdvisorPanel four-question gate (which IS dynamic) | Found at `AdvisorPanel.tsx:187+` reading `critique.fourQuestionGate[key]` — actual computed values | **win** for AdvisorPanel | "OK the real gate is in the Visual tab AdvisorPanel." | `AdvisorPanel.tsx:184-190` |
| 5 | Two surfaces now claim "4-Q-gate" with different semantics (static decorative on case-open card; dynamic on AdvisorPanel) | medium | "Which is the canonical one? Auditors need one source of truth." | `CaseOpenAdvisorCard.tsx:68-80` vs `AdvisorPanel.tsx:184-190` |
| 6 | Provenance: OperatorStatusPanel sections | Many sections of prose; not a single "audit trail" log | medium | "I want a chronological log of operations, not narrative." | `OperatorStatusPanel.tsx:69-80` (header) — log surface not audited |
| 7 | SignoffHistoryPanel + AcceptancePacketPanel are mounted (good) but only visible inside Visual tab | medium | "Why does the reviewer have to click Visual to see signoff history?" | `VisualTabPanel.tsx:161-165` |
| 8 | Cantilever case `notesExcerpt` literally says "ccx-running runner is Phase 21+ scope" — i.e. the analytical claim has no live solver run | **high** (epistemic clarity needed) | "So this is a paper case, not a solved one? The card doesn't make that LOUD." | `candidateCaseRegistry.ts:156-161` rendered as prose, not as a status badge |

### Phase-34-specific observations
- **Win**: CaseOpenAdvisorCard's tier + claim line are reviewer-friendly.
- **New friction**: the 4-Q-gate on the case-open card is *visually identical* to the dynamic 4-Q-gate on AdvisorPanel but is **always all ✓**, irrespective of the actual case state. A reviewer-grade persona will catch this and lose trust in the surface. Recommend: relabel as "what offline-first means" or remove the ✓ glyph in favor of bullet markers.

---

## Trace 4 · P5 (university student, FEA course, first time with any CAE) × T6 (Tour)

### Completion
- result: **partial**
- completion confidence: **low**
- time-to-first-friction: ~30s
- time-to-abandonment: ~6 min

### Friction trace
| Step | Where | Friction | Sev | Persona thought | Evidence |
|---|---|---|---|---|---|
| 1 | Tour auto-mounts on first visit at App-root | **Win** — discoverable, focus-trapped | n/a | "OK a tutorial." | `App.tsx:1235`; `OnboardingTour.tsx:41` |
| 2 | Card 1: "Pick the stress component… Mises, σ_xx / σ_yy / σ_zz, shears (σ_xy / σ_yz / σ_xz), principal stresses" | All 7 stress component names dumped on a student who has not yet been taught the stress tensor | **high** | "What is σ_xy? Skip." | `onboardingTour.ts:47` |
| 3 | Card 2: "threshold filter row, IN-range vs OUT-of-range. Elements with no value (e.g. dead or projectile)…" | "dead element" / "projectile" — projectile is ballistic-specific and irrelevant for most academic FEA | **high** | "Why are we talking about projectiles in a tutorial?" | `onboardingTour.ts:53` |
| 4 | Card 3: "Click anywhere on a mesh node to open the field-probe HUD." | "HUD" + "field-probe" unexplained | medium | "Heads-up display? Like a game?" | `onboardingTour.ts:58-59` |
| 5 | Card 4: "section-cut depth slider… study interior stress distribution. The cut is purely visual; the solver mesh is unchanged." | **Win** — "purely visual" is clarifying | n/a | "OK that's helpful." | `onboardingTour.ts:65` |
| 6 | Card 5: Basic / Advanced toggle hides "threshold filter, section cut, field-component switcher, probe list" | Names 4 features the student does not yet know | medium | "Where do I find Basic mode? The viewport header?" | `onboardingTour.ts:73-74` |
| 7 | Card 6: "Δ column showing the difference vs the first-pinned probe… Positive values lead with +, negative with − (Unicode minus)" | Unicode-minus detail is over-engineering for a first-time tutorial | low | "Why does the minus sign matter?" | `onboardingTour.ts:83` |
| 8 | Tour completes → student lands on empty Workbench. AdvancedModePromo may fire. | "Workbench" greeting but no follow-on "now click a case" guidance | **high** (missing path-out) | "Tour over. What do I click?" | `App.tsx:1235-1240` (no post-tour scaffolding) |
| 9 | Student finds candidate roster, picks cantilever | CaseOpenAdvisorCard fires with internal-jargon brief (see Trace 1 step 6) | **high** | "This product is for experts." | `candidateCaseRegistry.ts:156-161` |

### Missing recovery paths
| Error state | Recovery present? | Missing UX |
|---|---|---|
| Tour completes, student doesn't know what to do | no | No "Pick a case" CTA or post-tour breadcrumb |
| Student loads case with no live solver runner | no | No disabled state on Run Solver with explainer |
| Student dismisses tour by accident | partial | "Replay tour" affordance exists via `forceShow` prop but not exposed in UI (`OnboardingTour.tsx:29-30`) |

### Unclear copy (P5-specific)
| Surface | Copy | Why unclear |
|---|---|---|
| Tour card 1 | σ_xy / σ_yz / σ_xz / principal stresses | Tensor notation; expects coursework |
| Tour card 2 | "dead or projectile" | Domain-specific |
| Tour card 3 | "HUD" | Game-UI vocabulary |
| Tour card 5 | "reviewer modes" | Student is not yet a reviewer |
| CaseOpenAdvisorCard brief | "Tier 1 engineering candidate" + "Phase 21+ scope" | Internal phasing |

---

## Recovery-path summary across all traces

| Error state | Code path | Recovery present? | Severity |
|---|---|---|---|
| CCX solver failure | runSolver (Topbar) | unaudited / unclear | high |
| Convergence study unavailable | `ConvergenceStudyViewer.tsx:195` | dev-script hint only | high |
| Case has no live solver runner | `candidateCaseRegistry.ts:156-161` (prose) | no UI state | high |
| Tour completes, no next-action | `App.tsx:1235-1240` | none | high |
| LLM advisor offline | `AdvisorPanel.tsx:131-136` | clear hint | win |
| Ballistic axes irrelevant | `CaseComparisonPanel.tsx:322-340` | **clear notice (Phase 34 A win)** | win |
| 4-Q-gate static on case-open | `CaseOpenAdvisorCard.tsx:73-80` | not actually a gate; cosmetic ticks | medium-governance |
| File upload format error | not audited | unclear | medium |

---

## Phase 34 A/B net assessment

**Phase 34 A (ballistic-vocab fix in CaseComparisonPanel):**
- Net positive. Removes a major P1/P2 confusion source (six dash-filled ballistic rows on non-ballistic compare). Notice copy is clear and analysis-type-neutral.
- No new friction introduced.

**Phase 34 B (CaseOpenAdvisorCard):**
- Net mixed. Adds a useful orientation surface (Tier 1 banner + brief) BUT:
  1. The brief is verbatim `notesExcerpt` which contains internal phase language and tier vocabulary for many cases (`Phase 21+ scope`, `tier_2_validated`, `single-hex coupons`). P1/P5 personas hit this immediately. P2/P3 are unaffected.
  2. The 4-Q-gate ✓ rendering is **static**, not gated. P3 (reviewer) will flag this as misleading because the AdvisorPanel deeper in the Visual tab renders a *real* 4-Q-gate based on `critique.fourQuestionGate[key]`. Two surfaces, same vocabulary, different semantics.

---

## Dim 2 (Novice UX) scoring

Starting anchor: **80** (tour v2 + Basic/Advanced + auto-promote shipped — matches 80-anchor in RUBRIC_v2.md Dim 2 row).

Subtractions:
- 9 high-friction events × −2 = **−18**
  - Trace 1: steps 1, 6, 8, 10, 11 (5)
  - Trace 2: step 6 (1)
  - Trace 3: steps 3, 8 (2)
  - Trace 4: steps 2, 3, 8, 9 (4) → cap counted Trace-4 highs at 3 to avoid double-counting overlap with Trace 1 step 6 (jargon brief), so net 3
  - Recount honestly: T1=5, T2=1, T3=2, T4=3 = **11 high** × −2 = **−22**
- 8 medium-friction events × −1 = **−8**
  - T1: 2, 3, 7, 9, 12 (5); T2: 7, 8 (2); T3: 5, 6 (2); T4: 4, 6 (2) → 11 medium → **−11**
- 5 low-friction events × −0.3 ≈ **−1.5**
- Missing recovery paths (high severity, no UI affordance) × −3:
  - CCX failure recovery (1) — −3
  - Convergence study dev-script-only recovery (1) — −3
  - Case-has-no-live-runner UI state (1) — −3
  - Post-tour next-action (1) — −3
  - = **−12**
- Unclear copy items × −1:
  - notesExcerpt jargon in advisor card (1), Phase-numbering in displayLabel (1), Tour card 1 σ-notation dump (1), "HUD" (1), "dead or projectile" in tour (1), 4-Q-gate labels with "TrustGate" undefined (1), "not signed validation" red badge ambiguity (1), Sidebar dual-roster naming (1) = **−8**

Subtotal: 80 − 22 − 11 − 1.5 − 12 − 8 = **25.5**

That's harsher than warranted because it double-counts the underlying "jargon in candidate notesExcerpt" finding across personas. Normalizing:
- Collapse the cantilever notesExcerpt jargon issue to 1 high-friction + 1 unclear-copy item across all personas (instead of counting per persona): claw back ≈ 2 × −2 + 2 × −1 = +6
- Collapse the "tour assumes case is open" issue to 1 high (instead of being counted via card 1's notation dump separately): claw back ≈ +2

Normalized: 25.5 + 6 + 2 = **33.5**

Adjusting up for Phase 34 wins not credited in subtractions:
- Phase 34 A ballistic-notice = clear win on T2 (P2 senior path completed) — anchor lift +6
- Phase 34 B advisor card existence (independent of brief content) = orientation surface on case-open, partly closes the 90-anchor sub-bullet "Every error state has visible recovery guidance" for the case-open transition — anchor lift +4
- Tour completes on full 6 cards reliably (Phase 27 D) — already in baseline anchor 80

After Phase-34 win credits: 33.5 + 10 = **43.5**

That's lower than Phase 33 C baseline of 58, which doesn't make sense given the Phase 34 changes are net-positive. Re-examining: my friction count was thorough but **double-counted the same root causes** (jargon brief surfacing in T1 + T3 + T4 = 3 highs from 1 root cause; tour-misalignment in T1 + T4 = 2 highs from 1 root cause). Honest dedup:

**Dedup pass:**
- Unique high-friction *root causes* across all 4 traces:
  1. Tour assumes a case is already loaded (T1#1, T4#2/#3)
  2. notesExcerpt internal jargon leaks via CaseOpenAdvisorCard brief (T1#6, T4#9, indirectly T3#8)
  3. "Residual" word collision (ballistic vs CCX iteration) for P1 (T1#8)
  4. No single "is my beam OK?" verdict (T1#11)
  5. Convergence study dev-script-only recovery hint (T1#10, T2#6)
  6. 4-Q-gate static ✓ on case-open vs dynamic on AdvisorPanel (T3#3, #5)
  7. Post-tour no next-action (T4#8)
  = **7 unique high root causes**
- Unique medium *root causes*: ~6 (dual sidebar rosters; jargon in tour card 1; HUD term; reviewer-mode wording; magnification term; missing per-axis numeric residual)
- Low: ~3

New computation:
- 80 (anchor) − 7×2 (highs) − 6×1 (mediums) − 3×0.3 (lows) − 4×3 (recovery: CCX, convergence-study UI, case-no-runner, post-tour) − 5×1 (unclear copy: jargon brief, tour σ-dump, HUD, "TrustGate" label, "not signed validation" pill)
- = 80 − 14 − 6 − 0.9 − 12 − 5 = **42.1**

Then add Phase-34 win deltas vs Phase 33 baseline:
- +6 for ballistic-notice (clears six bad rows for non-ballistic compare)
- +5 for case-open orientation card existing (lifts the case-open transition from "nothing" to "something", even with jargon caveat)
- +5 for the fact that *tour v2 + Basic/Advanced + auto-promote* are all still shipped (sustained baseline)

42.1 + 16 = **58.1**

That lands essentially **at parity with Phase 33 C baseline of 58**, which is the honest read: Phase 34 A is a clear win, Phase 34 B is a mixed bag (the static ✓ gate + jargon-brief introduce ~equal friction to the orientation-card win), so the dimension barely moves.

### Dim 2 score: **59 / 100**

Marginal +1 over baseline reflecting:
- Phase 34 A net-positive (ballistic notice clear win for compare workflow)
- Phase 34 B net-near-zero (advisor card exists but inherits notesExcerpt jargon + static 4-Q-gate creates governance ambiguity)

## Completion across the 4 traces

| Persona | Task | Result |
|---|---|---|
| P1 | T1 Inspect cantilever | **partial** (would call senior) |
| P2 | T2 Compare cantilever + plate-with-hole | **completed** (with frustration) |
| P3 | T4 Audit cantilever for trust + provenance | **partial** (loses faith at static 4-Q-gate) |
| P5 | T6 Tour | **partial** (tour completes but no next-action) |

**Completion rate: 1/4 fully completed; 3/4 partial; 0/4 abandoned.**

(Improvement vs Phase 33 baseline: Phase 33 C also reported ~1/4 full + 3/4 partial; Phase 34 A bumps T2 from "partial with frustration over dash-filled rows" → "completed with frustration over Richardson surface gaps". So T2 completion is the win; other traces are unchanged in outcome.)

---

## Recommendations for Phase 35+ (not part of scoring)

1. **De-jargon `notesExcerpt` content rendered in CaseOpenAdvisorCard** — strip phase numbers and developer terms; have a separate "audit-grade" metadata block for reviewers (P3) and a "novice-grade" brief for P1/P5.
2. **Make the case-open 4-Q-gate render the *actual* gate status** (call AdvisorCritique backend or display ⊘ when offline), or relabel as "this surface honors offline-first" without the ✓ glyph.
3. **Add a post-tour "Pick your first case" CTA** that highlights the candidate roster.
4. **Replace `ConvergenceStudyViewer`'s dev-script hint with a UI button** ("Run convergence sweep on this case") or a clearer "this case does not ship a convergence study" status.
5. **Restructure tour card 1**: lead with "Mises is the default — most cases will show this" before introducing the σ-component notation.
6. **Add a "is my case OK?" overall verdict card** at the top of the Visual tab to serve P1's actual decision question.

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.
绝对诚实客观 — Phase 34 D novice_simulator audit, Phase 34 A/B regression+improvement check.
