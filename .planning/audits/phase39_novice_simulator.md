# FM-04a Phase 39 — novice-simulator (REGISTERED fleet) · Dim 2

> Authoritative re-score by the REGISTERED `subagent_type=novice-simulator`
> (sonnet), launched post-restart from the user-level `~/.claude/agents/`
> install. Anti-gaming B/D/F/G:-1 honored (the agent scored; file:line cited;
> no prior audit/FINAL/retro/STATE read; scored what the code IS). Code @ `67c2b8e`.

## Dim 2 — Novice user experience: **82 / 100**

Persona P1 (junior structural engineer, SolidWorks/ANSYS Workbench, weak FEA
theory). Task: full first-run flow (open case → confirm BCs → solve → read
results). Completion: partial; med confidence.

### 80-anchor — ALL sub-bullets MET

| Sub-bullet | Met? | Evidence |
|---|---|---|
| (a) first-visit tour ≥6 cards | ✅ | `onboardingTour.ts:43-86` — 6 steps (field-component, threshold-filter, node-pick, section-cut, basic-advanced-mode, probe-diff-column) |
| (b) Basic/Advanced toggle | ✅ | `uiMode.ts:53-54`, `UiModeToggle.tsx` |
| (c) default Basic | ✅ | `uiMode.ts:56` — `UI_MODE_INITIAL: UiMode = 'basic'` |
| (d) auto-promote to Advanced | ✅ | `onboardingTour.ts:266-276` `shouldShowAdvancedPrompt`; `AdvancedModePromo.tsx:62-163` |
| (e) in-context bubbles ≥5 DISTINCT surfaces, surface-specific copy | ✅ | 5 distinct hintIds + 5 unique texts: CaseBrowser `CaseBrowser.tsx:108-112`; BCSetupPillList `BCSetupPillList.tsx:89-93`; OperatorStatusPanel `OperatorStatusPanel.tsx:72-76`; ProbeListPanel `ProbeListPanel.tsx:103-107`; AdvisorPanel `AdvisorPanel.tsx:107-111` |

### 90-anchor — NOT fully met

| Sub-bullet | Met? | Evidence |
|---|---|---|
| Role-branching (engineer/reviewer/student/domain-expert) | ❌ 0% | `onboardingTour.ts:43-86` single-path; `OnboardingTourProps` (`OnboardingTour.tsx:24-39`) has no role prop |
| WCAG 2.1 AA across major surfaces | ◑ ~40% | `wcagContrast.ts:1-90` algorithm wired; `OnboardingTour.tsx:244` ≥1 AA fix landed; systematic audit not verifiable from code (F:-1 barred reading `.planning/wcag_audit.md`) |
| Every error state has visible recovery | ◑ ~65% | 5/7 paths have ErrorCard recovery; MISSING: results-iframe blank/error (`App.tsx:1424-1430` bare `<iframe>`, no onError) + BC-mismatch (read-only advisor, no error surface) |

### Score rationale
Selected anchor 80 (all met). Interpolation toward 90: weighted partial credit
(0 + 0.40 + 0.65)/3 = 0.35 × 10 = +3.5; friction deductions −1 (dev "Phase X"
labels visible in production UI: `AdvancedModePromo.tsx:132` "Phase 25 C · Phase
28 D" + `OnboardingTour.tsx:107` per-card shippedInPhase chips) −0.5 (iframe no
error state) → **82**.

### Friction / carry-forward (novice-flagged)
- **Dev "Phase X" labels leak to end users** (MED): `AdvancedModePromo.tsx:132`,
  `OnboardingTour.tsx:107` (+ `onboardingTour.ts:33-41` shippedInPhase chips).
- **Results iframe has zero error state** (HIGH): `App.tsx:1424-1430`.
- **BC-mismatch has no recovery surface** (MED): BCSetupPillList/BCSetupAdvisorCard read-only.
- **Tour tensor notation** (σ_xx…) un-glossed for weak-theory persona: `onboardingTour.ts:47`.
- **"Evidence-first workbench state"** internal term: `OperatorStatusPanel.tsx:80`.
- WINS: 6-card tour, Basic default + auto-promote, 5 distinct genuine hint surfaces,
  ErrorCard recovery on solver-start/upload/case-load/WS-death/PDF, advisor stub fallback.

agentId ae2dd64fb75304f1c (112154 tok, 25 tools).
