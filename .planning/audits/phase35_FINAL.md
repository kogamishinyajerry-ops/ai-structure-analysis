# FM-04a Phase 35 · FINAL composite + scoring synthesis

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-34. **19 consecutive Tier-2 phases**.

> Anti-gaming guards A-G (rubric v2.0) + H/I/J (Phase 34 new) + K/L/M
> (Phase 35 new) all honored. Sub-agents R3 ran independently;
> main session synthesized Dim 4 + Dim 6 only.

## Composite

**Phase 35 composite: 73.83/100 (rubric v2.0)**
**Lift over Phase 34 D (72.50): +1.33**
**Projected band was 74-77; landed slightly below the band's low end.**

Per-dim:

| Dim | Phase 34 D | Phase 35 D | Δ | Score source | Confidence |
|---|---|---|---|---|---|
| 1 FEA capability | 87 | **87** | 0 | `phase35d_functional_tester.md` | high |
| 2 Novice UX | 59 | **65** | **+6** | `phase35d_novice_simulator.md` | medium |
| 3 Industrial UI parity | 73 | **73** | 0 | `phase35d_industrial_ui_comparator.md` | medium (±2 noise) |
| 4 AI workflow integration | 72 | **73** | +1 | `phase35d_dim4_ai_workflow.md` (main session) | high |
| 5 Visualization & tracking | 72 | **72** | 0 | `phase35d_functional_tester.md` | high |
| 6 Trust & reproducibility | 72 | **73** | +1 | `phase35d_dim6_trust_reproducibility.md` (main session) | high |

**Composite = (87 + 65 + 73 + 73 + 72 + 73) / 6 = 443 / 6 = 73.83**

Composite calculation: simple arithmetic mean per rubric v2.0
contract. **No weights / no transforms applied** (anti-gaming
guard from Phase 33).

## Honest assessment: below the projected band, but the mandate axis advanced

The projected band was **74-77**; the actual composite is **73.83**,
landing just below the low end. The honest accounting:

- **Dim 2 (Novice UX) lifted +6** — exactly the rubric axis Phase
  35 targeted. This is the **biggest single-dim lift since Phase
  33 C** established the v2.0 baseline, and it is the user's
  stated mandate axis (新手人类用户的使用难度、交互模式).
- **Dim 4 + Dim 6 each lifted +1** — both axes also touched by
  Phase 35 scope (gate clarity refinement + cohort solver_kind
  pin + error-code surface).
- **Dim 1 + Dim 3 + Dim 5 stayed flat** — Phase 35 did NOT invest
  in cohort capability, industrial parity, or visualization.
  Confirming that the audit reflects the actual investment
  pattern, not noise.

Why we missed the projected band by ~0.2: the Phase 35 blueprint
optimistically projected Dim 2 lift "+7 to +11" (to 66-70). The
realistic sub-agent score is **+6** (to 65). The honest reason: the
2 of 5 error-recovery paths closed (out of 5) is partial progress,
not the full closure the higher-end projection assumed. The 6
new friction points novice_simulator R3 flagged also keep Dim 2
below the optimistic projection.

## Per-dim narrative summaries

### Dim 1 — FEA capability (87, unchanged)

Phase 35 did not touch the FEA stack. The 12-case cohort with 6
distinct solver kinds (now ALL with `solver_kind` populated per
Phase 35 B) holds the 80-anchor. The element-class enumeration
that Phase 34 D's functional_tester flagged (C3D8 / S4 / B31) is
re-examined in Phase 35 D — `plate_kirsch_runner` uses C3D4 tet
mesh in its mesh-composer path, so cohort element-class coverage
is actually **C3D8 / C3D4 / S4 / B31** (4 classes, satisfying
the 90-anchor sub-bullet). Phase 35 D functional_tester confirms.

Phase 36+ path to 90+ requires actual cohort breadth investment:
buckling/static cases at non-cantilever geometry, more solver-kind
diversity (rolling contact, transient heat).

### Dim 2 — Novice UX (65, +6)

Phase 35 A closed Phase 34 D findings #27 (jargon leak) + #28
(static-vs-dynamic gate) cleanly. Phase 35 C wired 2 of 5 silent
error-recovery paths with a generic, reusable hook (good for
future error-path closures). Persona simulation:

| Persona × task | Phase 34 D | Phase 35 D |
|---|---|---|
| P1 first-time reviewer opens cantilever-beam | confused by Phase-21 vocab | **CLEAN** — gets engineering orientation |
| P3 governance reviewer audits 4-Q gate | confused by static-vs-dynamic | **CLEAR** — subtitle + muted color declares static-stub status |
| P5 anxious novice fails upload | silent console.error | **VISIBLE** — red ErrorCard with title + remediation + Retry |
| P3 governance reviewer fails case load | silent console.error | **VISIBLE** — same recovery path |

6 NEW Phase 35 friction points flagged for Phase 36+:
1. `candidateCaseRegistry.ts:151` displayLabel still carries "(Phase 20 B)" suffix (Phase 35 A only sanitised the orientation half of the brief)
2. ErrorCard mount sits BELOW `OperatorStatusPanel`; failed users see trust prose before the red error band
3. ErrorCard's `role="alert"` / `aria-live` semantics depend on the ErrorCard implementation; verify screen-reader announce behavior
4. Verbatim "UPLOAD" / "CASE-LOAD" codes surfaced to novices look like internal enums; humanize copy
5. `selectCase` Retry re-submits the same captured dummy `File`; minor smell
6. Phase 35 A removed the latent "no live CCX runner" warning for cantilever; needs structured `runner_available: false` badge

### Dim 3 — Industrial UI parity (73, unchanged)

`industrial_ui_comparator` R3 held the line at 73 (within ±2 noise
band). Phase 35 A's italic-muted static-gate subtitle + Phase 35
C's ErrorCard mount land "strong convention parity on non-canonical
surfaces" but the 5-surface mean parity is unchanged at 3.76/10.

Phase 36+ priorities: redesign the case picker + parameter dialogs
+ post-process toolbar.

### Dim 4 — AI workflow integration (73, +1)

Two surfaces (AdvisorPanel + CaseOpenAdvisorCard) unchanged in
count. The +1 lift comes from quality refinement at the existing
surfaces:

- 70-anchor "contextual nudge" sub-bullet: gets a quality lift
  from curated case-kind orientation copy (vs raw notesExcerpt
  passthrough).
- 80-anchor "4-Q-gate audited inline at each" sub-bullet: the
  static-vs-dynamic semantic tension that cost Phase 34 D ~ -1 on
  this sub-bullet is now resolved by the gate-hint subtitle +
  data-gate-kind="static" tag.

Phase 36+: BC-setup advisor surface (closes 80-anchor 3-stage
sub-bullet), dynamic 4-Q gate at case-open (resolves remaining
static ambiguity), ≥1 concrete LLM provider class.

### Dim 5 — Visualization & tracking (72, unchanged)

Phase 35 added zero progress to the 4 missing items the 90-anchor
gates require:
1. Iso-surface rendering
2. Real playwright WebGL E2E suite
3. VTU/PNG export from frontend
4. True overlay comparison

Dim 5 stays at 72 until a dedicated viz-investment phase lands.

### Dim 6 — Trust & reproducibility (73, +1)

Phase 35 B closed the cohort-wide solver_kind grep gap (12/12 cases
report kind, was 4/12). New test pin
(`test_phase35b_verdict_yaml_solver_kind_backfill.py`) asserts the
cohort invariant + the schema-heterogeneity preservation (so a
future "harmonisation" PR can't silently break the schema-1.0
reader contract).

Phase 35 C added an error-code surface (UPLOAD / CASE-LOAD) for
support-ticket / log-correlation provenance — minor 90-anchor lift
on the "trust score explains every UI step" sub-bullet.

Phase 36+ priorities for Dim 6 (high-leverage):
1. Failed-attempt corpus (`.planning/failed_attempts/INDEX.md` with ≥5 entries)
2. Audit-trail log (`backend/app/services/audit_log.py` append-only JSONL)
3. Reproducibility CLI (`cli/reproduce.py`)

## Anti-gaming guards summary

All Phase 18-34 guards (A-J) + Phase 35 new guards (K-M) honored:

- **A:-1** (no rubric reword): PASS — RUBRIC_v2.md unchanged
- **B:-1** (sub-agents score Dim 1/2/3/5; main syn Dim 4/6): PASS
  — 3 sub-agent reports cite file:line; main-session syntheses cite
  file:line; sub-agent dim scores NOT adjusted
- **C:-1** (no v1.0 vs v2.0 comparison): PASS — v2.0 trajectory only
- **D:-1** (file:line evidence): PASS — 5 audit files verified
- **E:-1** (99 evidence): N/A
- **F:-1** (anti-priming): PASS — sub-agent briefs declared the
  Phase 35 investment honestly, not as "must lift Dim 2 to 70+"
- **G:-1** (codebase IS not CLAIMS): PASS — sub-agents traced code
  + ran tests (Phase 35 B test 27/27 confirmed, frontend 807/807
  confirmed)
- **H:-1** (Phase 34, REAL ccx for cohort lift): N/A — Phase 35
  didn't invest in cohort capability
- **I:-1** (Phase 11 AdvisorPanel unmodified): PASS — `git diff`
  shows `AdvisorPanel.tsx` clean
- **J:-1** (Phase 25 D CSV export schema unmodified): PASS — 773
  prior frontend tests continue passing; CSV pins intact
- **K:-1** (NEW Phase 35, CaseOpenAdvisorCard test-ids preserved):
  PASS — all 5 test-ids (`case-open-advisor-card / -status-badge /
  -brief / -four-question-gate / -footer`) intact; new
  `case-open-advisor-gate-hint` test-id added (additive only)
- **L:-1** (NEW Phase 35, schema additive only): PASS —
  schema_versions preserved verbatim; only `solver_kind` field
  added; existing readers + Phase 21/29/30 test pins continue
  passing (232/232)
- **M:-1** (NEW Phase 35, App.tsx <1500 LOC): PASS — App.tsx at
  1478 LOC after Phase 35 C wiring; Phase 29 B regression pin
  holds with 22 LOC headroom

## Roadmap to 99+ (refined from Phase 34 FINAL)

Original Phase 34 projection: P35 ~74-77; P36-37 ~78-82; P38 ~80-84;
P39 ~83-87; P40 ~86-90; P41-43 ~89-93; P44-45 ~99-100.

Phase 35 actual: **73.83** (slightly under the low end). The
shortfall is small (~0.2 points) — fixable by hitting Phase 36
slightly harder on either Dim 2 (close 1-2 more error-recovery
paths + role-branching onboarding) or Dim 3 (one canonical-surface
parity win).

Updated phase-by-phase projection band:
- **P36**: 76-79 (closes 1-2 more error-recovery paths + WCAG audit
  + onboarding role-branching + maybe BC-setup advisor surface)
- **P37**: 79-82 (industrial UI parity round on case picker + parameter dialogs)
- **P38**: 82-85 (FEA cohort 13-15 + new solver kind class)
- **P39**: 85-88 (viz iso-surface + playwright WebGL E2E)
- **P40**: 88-91 (trust failed-attempt corpus + audit-log + reproduce CLI)
- **P41-43**: 91-95 (NAFEMS benchmark suite + cohort 16-18 + LLM provider)
- **P44-45**: 95-99 (final polish + first 99+ audit cycle)

**Projected reach of 99+: Phase ~45-46.** Phase 35's +1.33 is
slightly below the +2.5/phase average needed but the Novice UX
foundation laid here (the reusable `useUploadErrorRecovery` hook +
the case-kind orientation pattern + the static-gate semantic
distinction) accelerates Phase 36-37 Dim 2 work.

## Closing

Phase 35 is the 19th consecutive Tier-2 phase delivered without
rubric reshaping or score gaming. The user's mandate axis (Novice
UX) got first-class attention and showed the biggest single-dim
lift since the v2.0 baseline (Dim 2: 58 → 59 in Phase 34 → 65 in
Phase 35; +7 across 2 phases).

The composite of 73.83 is honestly just below the projected band's
low end. The honest reason is documented (5 error-recovery paths is
the full scope; 2 closed is partial; 3 carry to Phase 36+).
Anti-gaming discipline preserved — no retroactive scoring of prior
phases, no weight adjustments, no rubric softening to hit the
projection.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. 绝对诚实客观 across 19 consecutive Tier-2
phases.
