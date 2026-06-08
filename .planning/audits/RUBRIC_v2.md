# FM-04a · Audit Scoring Rubric · v2.0 (Phase 33 A)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-32. **17 consecutive Tier-2 phases**.

## Purpose

Rubric v1.0 (Phase 29 D, `.planning/audits/RUBRIC.md`) measures the
product across **3 dimensions** (UX / FEA / UI), 18 sub-axes. Phase
33 A introduces rubric v2.0 to honor the user's Phase 33 mandate:

> "明确的完成度评分机制（要绝对诚实客观，且维度充足，包括 FEA
> 仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括 UI
> 设计是否能对标顶级工业软件）"

Rubric v2.0 has **6 dimensions** (FEA capability / novice UX /
industrial UI parity / AI workflow integration / visualization &
tracking / trust & reproducibility), at anchors 60 / 70 / 80 / 90
/ 95 / 99 per dimension. **99-anchor requires named verifiable
evidence in the codebase**, NOT signed validation; this resolves
the rubric-v1.0 99-ceiling that was bound to forbidden signed
validation.

## Coexistence with rubric v1.0

- **Rubric v1.0 is NOT replaced**, just supplemented. Phase 32 and
  prior audits remain measured on rubric v1.0.
- **Rubric v2.0 is the active scoring system from Phase 33 C
  onward.** Phase 33 C performs the first re-baseline.
- **Never compare a v1.0 score with a v2.0 score directly**
  (anti-gaming guard C:-1 from blueprint). They are different
  scales with different dimension counts.
- The user's "99 分以上" target is interpreted under rubric v2.0,
  not v1.0.

## Versioning

- **v2.0 (Phase 33 A)** — initial 6-dim pinning.
- Future bumps (v2.1, v2.2, ...) require explicit retro
  acknowledgment + a `vN.M` bump here; sub-agents always read the
  latest version. Old phase audits are NOT re-scored retroactively
  (additive D:-1 guard from v1.0 preserved).
- Anchor changes within a version are NOT silent edits — any
  rewording of a 60/70/80/90/95/99 anchor must ship as a
  phase-event commit citing rationale + impact on the next
  scoring cycle.

## Scoring procedure

1. For each of 6 dimensions, the sub-agent reads the relevant
   codebase surface + cites file:line evidence + selects the
   highest anchor whose "What you observe" all sub-bullets are
   met (NOT cherry-picked).
2. Interpolation between anchors is allowed (e.g., "all of 80
   met + 1/3 of 90's sub-bullets met → 83").
3. Each dim → 1 score 0-100.
4. **Composite = mean(dim1, dim2, dim3, dim4, dim5, dim6)** —
   simple arithmetic mean, no weights, no transforms.
5. 99+ requires **all 6 dimensions ≥ 99**. This is the user's
   stated target.

## Anti-gaming guards (rubric v2.0)

- **A:-1**: rubric anchor reword = phase-event commit (no silent
  bump).
- **B:-1**: scoring done by fresh sub-agent instances per phase
  (no main-session synthesis of dimension scores).
- **C:-1**: never compare v1.0 vs v2.0 scores directly.
- **D:-1**: every claimed anchor needs file:line evidence in the
  sub-agent's report. Bare "Dim N = 84" rejected.
- **E:-1**: 99-anchor evidence must be COMMITTED to the repo
  (test artifact, audit report markdown, code path). No "would
  reach 99 if we shipped X" interpolation to 99.
- **F:-1**: novice_simulator + industrial_ui_comparator NEVER read
  prior FINAL / retro files when scoring (avoids priming).
- **G:-1**: rubric v2.0 must measure what the codebase IS, not
  what it CLAIMS to be. Marketing copy, README ambitions, or
  TODO comments are NOT evidence.

---

## Dim 1 — FEA simulation capability (full-spectrum)

How broad and deep is the validated FEA solver coverage; how
honest the convergence / asymptotic story is.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | ≥3 validated cases ship in `golden_samples/`. Linear-static + ≥1 element class. INP composer + reader + verdict YAML. | Phase 11-15 baseline |
| 70 | ≥6 validated cases. ≥3 element classes (e.g., C3D8 / S4 / B31). Live `ccx` runs verified. Single solver kind (linear static). | Phase 22 baseline (~75/v1.0) |
| 80 | ≥9 validated cases. ≥4 solver kinds (linear static + modal + buckling + dynamic). Richardson extrapolation on ≥30% of cases. ≥1 asymptotic-bias revelation flagged. | Phase 30 D baseline |
| 90 | ≥12 validated cases. ≥5 solver kinds (+ contact OR coupled OR heat). Richardson coverage ≥60% of refinable cases. ≥2 asymptotic-bias revelations. ≥4 element classes (C3D4/8/10 + S3/4 OR B31). p ≤ 0 guard implemented. | Phase 32 + 1 Tier-1 lift |
| 95 | ≥15 validated cases. ≥6 solver kinds. Richardson ≥80% of refinable cases. ≥3 asymptotic-bias revelations. ≥1 NAFEMS test problem agreement evidence. ≥6 element classes. Failed-attempt corpus indexed. | Phase ~40 target |
| **99** | ≥18 validated cases. **All major element classes** (C3D4/8/10/20, S3/4/6/8, B31/32). **≥7 solver kinds** (linear static + modal + buckling + dynamic implicit + dynamic explicit + contact + heat + coupled temp-disp). Richardson 100% of refinable cases. **≥1 NAFEMS or ASME benchmark agreement evidence committed** (test problem with documented analytical reference + residual ≤2%). Failed-attempt corpus ≥10 entries with retrospective indexing. | Phase ~45 target |

**99-anchor evidence requirements (codebase-verifiable):**
- Cohort count: `ls golden_samples/*-candidate/ | wc -l` ≥ 18
- Element class catalogue: grep across runners
- Solver kind: distinct `solver_kind:` values in verdict YAML
- NAFEMS agreement: dedicated `golden_samples/nafems-*-candidate/`
  with public test problem + analytical reference + residual

---

## Dim 2 — Novice user experience

How well a beginner (e.g., structural engineer with FEA basics
but never used the product) can complete real workflows. Scored
by `novice_simulator` sub-agent transcript analysis.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Feature buttons are visible; case-tree exists; engineer can click around but has no guidance on what to do first. | Phase 22 baseline |
| 70 | One guided tour pops on first visit. Covers ≥4 affordances. Basic / Advanced mode toggle exists. | Phase 25-26 |
| 80 | Tour v2 (≥6 cards). In-context bubbles attached to ≥5 UI surfaces. Default to Basic mode. Auto-promote to Advanced on advanced-feature first-touch. | Phase 27-28 |
| 90 | + Role-branching paths (engineer / reviewer / student / domain-expert) selectable during onboarding. + WCAG 2.1 AA audit pass for all major surfaces. + Every error state has visible recovery guidance. | Phase ~35 target |
| 95 | + `novice_simulator` sub-agent completes ≥80% of test scenarios autonomously (no developer intervention). + In-context help text references actual file paths only when relevant; otherwise pure task vocabulary. | Phase ~38 target |
| **99** | + `novice_simulator` sub-agent completes **100%** of test scenarios autonomously. + Recovery path documented + tested for every error state (CCX failure, mesh failure, BC mismatch, file format, advisor LLM unavailable). + Role-branching paths fully implemented for all 4 personas. + WCAG 2.1 AA full audit report committed. + Tour personalizes by role. | Phase ~44 target |

**99-anchor evidence requirements:**
- `novice_simulator` transcript at
  `.planning/audits/phase<N>_novice_simulator.md` showing 100%
  completion across all scenarios.
- WCAG 2.1 AA audit report at `.planning/audits/wcag_audit.md`.
- 4 role personas documented + role-branching coverage matrix.

---

## Dim 3 — Industrial UI parity

How closely the visual + interaction patterns parallel top-tier
industrial CAE software (Altair Hyperworks, Abaqus CAE, ANSYS
Mechanical, Siemens Simcenter). Scored by
`industrial_ui_comparator` sub-agent reports.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Tokens-based design system (colors / spacing / typography defined as variables, not magic numbers). Single-theme. | Phase 22 baseline |
| 70 | + Motion vocabulary documented (≥1 timing curve, ≥1 entrance + exit pattern). + Single theme polished. | Phase 25-26 |
| 80 | + ≥7 motion-vocabulary surfaces. + Drag-resize panels OR density toggle OR 4-quadrant layout (any 1 of 3). + Dark token system primitives (NOT yet a toggle). | Phase 32 baseline |
| 90 | + Drag-resize panels + density toggle + 4-quadrant layout + collapsible left/right rails — **all 4 shipped**. + `industrial_ui_comparator` sub-agent rates parity ≥7/10 on ≥5 reference surfaces. + Reference descriptions documented at `.planning/test_subagents/references/`. | Phase ~36 target |
| 95 | + Dark / light theme toggle (full token coverage in both themes). + 4-quadrant default layout (engineer can choose alternative). + `industrial_ui_comparator` parity ≥8/10 on ≥5 reference surfaces. + Token system fully documented at `.planning/design_system/`. | Phase ~37 target |
| **99** | + `industrial_ui_comparator` parity **≥9/10** on **5 canonical reference surfaces** (case-tree panel / 3D viewport / results plot / BC setup / mesh visualization), with cited evidence file:line for every parity / gap claim. + Full motion + theme + density + layout systems all shipped + audited. + Vendor-equivalence narrative documented (which industrial software each surface mirrors). | Phase ~44 target |

**99-anchor evidence requirements:**
- `industrial_ui_comparator` reports at
  `.planning/audits/phase<N>_industrial_ui_<surface>.md` for each
  of the 5 reference surfaces, parity ≥9/10 cited.
- Reference descriptions at
  `.planning/test_subagents/references/{case_tree,viewport,results_plot,bc_setup,mesh_viz}.md`.
- Token system at `.planning/design_system/tokens.md`.

---

## Dim 4 — AI workflow integration

How deeply the AI advisor is wired into the product's actual
workflows (NOT just a standalone advisor panel). User's mandate
specifically called this out: "顶级的全流程 AI FEA 功能".

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | 1 AI advisor surface exists. Read-only critique panel. | Phase 11 baseline (AdvisorPanel + AdvisorCritique + StubAdvisor) |
| 70 | 2 advisor surfaces: critique panel + 1 contextual nudge (e.g., post-solve summary). | Phase ~33 baseline (if Phase 11 wiring extended) |
| 80 | Advisor present at **3 workflow stages**: case-open (overview), setup (BC sanity-check), review (results narrative). 4-Q-gate audit (4 questions: LLM-offline? artifacts? TrustGate? advisory-only?) visible at each. | Phase ~34 target |
| 90 | + Advisor at **5 stages** (+ mesh-setup advice + solve-monitor narration). 4-Q-gate audited inline at each. Calibration-marker prose ("confidence: high/med/low") on every advisor output. | Phase ~34-35 target |
| 95 | + Every advisor call narrates **uncertainty with calibration markers** + cites specific file or artifact when claiming a fact. + Failed-LLM fallback to StubAdvisor proven via test. | Phase ~36 target |
| **99** | + Advisor present at **≥6 major workflow stages** (case-open + mesh + BC + solve + results + export). + 4-Q-gate audited inline at every stage. + **≥3 LLM backend support** documented (StubAdvisor + at-least-2-LLM-providers with env-var gating). + **Advisor actions wire back into the pipeline** (not pure read-only — e.g., advisor can suggest "refine mesh at region X" and the workbench has a button to apply it). + Coverage matrix at `.planning/audits/ai_advisor_coverage.md`. | Phase ~44 target |

**99-anchor evidence requirements:**
- Coverage matrix: `.planning/audits/ai_advisor_coverage.md`
  enumerating each workflow stage × advisor wiring + 4-Q-gate
  audit result.
- ≥3 LLM provider gated: code paths visible for ≥3 of {Stub,
  OpenAI, Anthropic, Gemini, local-Ollama}.
- ≥1 "advisor → action" pipeline wiring (e.g., refine-mesh
  suggestion routes back into the workflow).

---

## Dim 5 — Visualization & tracking

The depth of 3D / time-series / probe / export visualization
infrastructure. Includes performance + accessibility of the viz
layer.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | 3D viewport renders result mesh; static displacement / vM contour. | Phase 22-23 baseline |
| 70 | + Probe list (click a node, see value). + Section cuts on at least 1 axis. | Phase 24-26 |
| 80 | + Companion viewport for compare-cuts. + Time-series scrubber for dynamic / modal cases. + Probe persistence across reload. + WebGL + SVG dual-render fallback. | Phase 30-32 baseline |
| 90 | + Iso-surface rendering. + CSV export. + Real WebGL E2E test via playwright (not just jsdom). + Comparison cuts (overlay two results). | Phase ~39 target |
| 95 | + Provenance overlays (every viz frame links back to its case-id / snapshot-id / signoff-id). + Performance ≥30fps for ≥100k nodes. + Time-series + probe + iso-surface + comparison + section cut + companion ALL shipped. | Phase ~40 target |
| **99** | + Performance **≥60fps for ≥100k nodes** (or ≥30fps for ≥1M). + Export to **3 formats** (CSV + VTU + PNG). + Real WebGL E2E playwright test suite committed + green in CI. + Full provenance chain visible in viz overlays. | Phase ~45 target |

**99-anchor evidence requirements:**
- Playwright test suite at `frontend/e2e/webgl_*.spec.ts`,
  documented running in CI.
- Performance benchmark artifact at
  `.planning/perf/viz_benchmark.md` with measured fps × node-count.
- Export functions for 3 formats (CSV / VTU / PNG) all tested.

---

## Dim 6 — Trust & reproducibility

How well the product's outputs can be audited / re-run / verified
months later. Includes provenance chain, snapshot integrity, ADR
discipline, and failed-attempt corpus.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Case directory + INP file + manifest. | Phase 22 baseline |
| 70 | + Schema versioning on artifacts (`schema_version: 1.0.0`). + Verdict YAML stable. | Phase 25-27 |
| 80 | + Cohort snapshots (Phase 5). + Reviewer signoffs (Phase 8-9). + Cross-validation pinning between artifacts. | Phase 28-30 baseline |
| 90 | + Full provenance chain visible at every UI step (case → snapshot → signoff → audit). + ADR archive with ≥10 ADRs. + Trust score from CASE_COMPLETENESS_SCHEMA + analysis-type-aware rubrics. | Phase 32 baseline (~70 here) |
| 95 | + Failed-attempt corpus indexed at `.planning/failed_attempts/` with retrospective discovery (e.g., contact-pair recon, cylinder-pv BC redesign, Richardson p ≤ 0 finding, C3D4 -8.4% bias all cataloged). + ADR archive complete + cross-linked from components. | Phase ~40 target |
| **99** | + Every operation has an **audit trail entry** (case-open, mesh-edit, BC-change, solve, signoff, export — all logged with timestamp + actor + content-hash). + **Cross-validation pinning automatic** (every artifact write produces a verification re-read pin in the test suite). + Failed-attempt corpus ≥10 entries indexed. + ADR archive linked from every major component. + Reproducibility CLI: any case can be re-run with `harness reproduce <case-id>` and byte-match the original artifacts. | Phase ~45 target |

**99-anchor evidence requirements:**
- Audit-trail log: `backend/app/services/audit_log.py` + DB schema
  + log entries for ≥6 operation types.
- Reproducibility CLI: `cli/reproduce.py` or equivalent with E2E
  test producing byte-match artifact.
- Failed-attempt corpus: `.planning/failed_attempts/INDEX.md` ≥10
  entries.
- ADR cross-reference matrix:
  `.planning/adrs/CROSS_REFERENCE.md`.

---

## Composite

```
composite = mean(dim1, dim2, dim3, dim4, dim5, dim6)
```

Simple arithmetic mean across 6 dimensions. **No weights. No
transforms.** Composite is honest only if each dim score is
honest. Sub-agents score each dim independently; main session
synthesizes the composite but does not adjust dim scores.

## 99+ target definition

**99+ ⟺ all 6 dimensions score ≥ 99**, with the named verifiable
evidence committed to the repo.

A composite of 95 with 5 dims at 99 and 1 dim at 71 is NOT a
99+ result. Each dim must independently reach 99 with evidence.

This is the user's stated target. The Phase 33-45 roadmap is the
plan to get there.

## Honest projection for Phase 33 C re-baseline

Without Phase 33 D's `*CONTACT PAIR` lift:

| Dim | Projected v2.0 score | Reasoning |
|---|---|---|
| 1 FEA | ~78 | 11 validated cases (90-anchor needs 12); 5/11 Richardson (90-anchor needs 60% = 6.6/11); 2 bias revelations ✓; 5 solver kinds (90-anchor: 5 ✓) — near 90 but cohort count short |
| 2 Novice UX | ~62 | Tour + Basic/Advanced + in-context bubbles partial; no role-branching (90-anchor); no novice_simulator pass yet (95-anchor); ~60-65 |
| 3 Industrial UI | ~55 | Motion vocabulary 7 surfaces + dark token primitives + companion + section cut; NO drag-resize / density / 4-quadrant / theme toggle (90-anchor); ~50-60 |
| 4 AI workflow | ~50 | Phase 11 AdvisorPanel = 1 surface; not wired into workflow stages; 60-anchor met; below 70 |
| 5 Visualization | ~72 | 3D + probe + section + companion + time-series + CSV — 80-anchor met; no iso-surface (90-anchor); no playwright E2E (90-anchor); ~70-75 |
| 6 Trust | ~70 | Snapshots + signoffs + provenance + schema versioning — 80-anchor met; partial 90-anchor; no failed-attempt corpus (95-anchor); ~68-72 |
| **Composite v2.0** | **~64-68** | mean of above |

After Phase 33 D (`*CONTACT PAIR` Hertz case): Dim 1 lifts to
~82 (12th case + contact_pair solver kind added). Composite
delta: +0.5-0.8. Phase 33 final projection: **~65-70/v2.0**.

This is the honest scale-change result. Phase 32's 89.68/v1.0
remains the v1.0 measurement; rubric v2.0 starts fresh at the
re-baselined value.

## Coexistence and migration

Phase 33-onward audits will produce:
- `phase<N>_FEA_audit.md` (rubric v1.0, for trajectory continuity)
  — OPTIONAL, can be retired Phase 35+
- `phase<N>_dim<1-6>_audit.md` (rubric v2.0, primary scoring)
  — REQUIRED from Phase 33 C onward

The dual-tracked period is Phases 33-34. From Phase 35 onward,
rubric v1.0 is retired (its purpose served).

## Closing

Rubric v2.0 is the scoring apparatus for the multi-phase journey
to 99+. It does not by itself produce any score lift; it just
measures the codebase honestly across the 6 dimensions the user
asked for. The actual lift comes from Phase 33 D + Phase 34-45
implementation work.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. 绝对诚实客观 across 17 consecutive Tier-2
phases.
