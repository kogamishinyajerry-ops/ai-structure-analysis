# FM-04a Phase 33 — Top-tier full-flow AI FEA · rubric v2.0 foundation phase

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-32. **17 consecutive Tier-2 phases**.

## User mandate (verbatim from authorization message)

> 批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程
> AI FEA 功能），瞄准蓝图进行开发，要有一套专门的测试子 agent，
> 真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评
> 分机制（要绝对诚实客观，且维度充足，包括 FEA 仿真全维度能力，
> 包括新手人类用户的使用难度、交互模式，包括 UI 设计是否能对标
> 顶级工业软件），一直迭代开发下去，直至达到你眼里的优秀水准
> （99 分以上）。

Reading the mandate against the existing honest contract:

1. **"顶级的全流程 AI FEA 功能"** — top-tier full-flow AI FEA.
   The current state has AI advisor surface (Phase 11) but the
   advisor is **not yet wired into the actual case workflow at
   every stage**. Phase 34+ feature work will close this.
2. **"专门的测试子 agent"** — dedicated test sub-agents. The
   current 3 audit sub-agents (UX / FEA / UI) score against rubric
   anchors but do NOT perform live functional evaluation. New
   architecture introduces **3 specialized testers**: functional
   tester, novice user simulator, industrial UI comparator.
3. **"明确的完成度评分机制 ... 绝对诚实客观，且维度充足"** —
   clear scoring mechanism, absolutely honest and objective, with
   sufficient dimensions. Current rubric v1.0 has 3 dimensions
   (UX / FEA / UI) at 18 sub-dimensions; user-requested expansion
   adds: AI workflow integration, visualization & tracking, trust
   & reproducibility. Rubric v2.0 = **6 dimensions × 30+
   sub-dimensions**.
4. **"99 分以上"** — 99+. The prior hard constraint "NEVER score
   above 99 (signed validation territory forbidden)" was bound
   to rubric v1.0's interpretation that 99 ≡ signed validation.
   **Rubric v2.0 redefines the 99 anchor** as "all 6 dimensions
   meet verifiable evidence criteria" — NOT signed validation.
   Under rubric v2.0, 99+ is reachable and the user's target is
   meaningful.

The 绝对诚实客观 contract remains unchanged. The 99-ceiling moves
because the scoring scale moves; the honesty discipline does not.

## Honest scope acknowledgment (upfront)

This is a **multi-phase journey, not a single-phase sprint**.
Phase 33 establishes:
- New scoring system (rubric v2.0)
- New evaluation infrastructure (3 specialized test sub-agents)
- Honest re-baseline of current state under the new system
- One Tier-1 FEA lift (`*CONTACT PAIR` Hertz case) to validate
  the loop end-to-end

Phase 33 does NOT attempt to reach 99+ in one phase. The honest
projection: **the current 89.68/v1.0 state will re-baseline at
~70-75/v2.0** under the more rigorous, multi-dimensional rubric.
That is feature, not bug — it's how an honest scale-change works.

Reaching 99+ will require **Phase 34 through Phase ~45+** of
disciplined per-dimension work. Each phase will lift 1-2 axes by
3-5 points. The path is in §"Multi-phase roadmap toward 99+"
below.

## Slice plan

| Slice | What lands | Projected cost |
|---|---|---|
| 33 blueprint | This document | — |
| **33 A** | `.planning/RUBRIC_v2.md` — 6 dimensions, 30+ sub-dimensions, 60/70/80/90/95/99 anchors per dim. 99-anchor requires **named verifiable evidence** (test artifact, sub-agent report, file:line citation), NOT self-rating. | ~400-500 LOC markdown |
| **33 B** | `.planning/test_subagents/{functional_tester,novice_simulator,industrial_ui_comparator}.md` — protocol files specifying briefing template + evaluation procedure + evidence requirements + output schema for each specialized testing sub-agent. | ~200 LOC × 3 protocols |
| **33 C** | First honest re-baseline under rubric v2.0 — spawn 3 test sub-agents in parallel, aggregate per-dimension scores, write `.planning/audits/phase33c_rebaseline.md`. **Expected output: composite ~70-75/100/v2.0**. | ~50 LOC orchestration + 3 sub-agent runs |
| **33 D** | `*CONTACT PAIR` Hertz Tier-1 FEA lift — 12th validated case (`hertz-contact-candidate`). Closes Phase 31 A + Phase 32 blueprint deferral. CCX `*CONTACT PAIR` + `*RIGID BODY` reference node + analytical Hertz pressure distribution. NEW solver kind: `contact_pair_static`. | ~800-1000 LOC runner + reader extension |
| **33 E** | 3 test sub-agents R2 audit post-33-D + FINAL synthesis + retro + STATE refresh + commit. Expected: composite ~72-77/v2.0 after 33 D lift (Δ +2-3 over 33 C re-baseline). | — |

## Rubric v2.0 design preview (full text in 33 A)

### 6 dimensions (each scored 0-100)

| Dim | Name | Anchors at 60/70/80/90/95/99 |
|---|---|---|
| **1** | **FEA simulation capability** (full-spectrum) | 60: ≥3 validated cases / 70: ≥6 + ≥3 element classes / 80: ≥9 + ≥4 solver kinds + Richardson on 30% / 90: ≥12 + ≥5 solver kinds + Richardson on 60% + 1 asymptotic-bias revelation / 95: ≥15 + ≥6 solver kinds + Richardson on 80% + ≥3 bias revelations / **99: ≥18 + all major element classes (C3D4/8/10/20, S3/4/6/8, B31/32) + ≥7 solver kinds (static / modal / buckling / dynamic / contact / heat / coupled) + Richardson 100% applicable cases + ≥1 NAFEMS/ASME benchmark agreement evidence** |
| **2** | **Novice user experience** | 60: visible feature buttons / 70: 1 guided tour / 80: in-context bubbles ≥5 surfaces / 90: full role-branching onboarding + WCAG 2.1 AA pass / 95: novice sub-agent completes 80% of test scenarios autonomously / **99: novice sub-agent completes 100% of test scenarios autonomously + every error state has clear recovery path + role-branching paths for engineer/reviewer/student/domain-expert** |
| **3** | **Industrial UI parity** | 60: tokens-based design system / 70: motion vocabulary + dark/light theme / 80: drag-resize panels + density toggle + 4-quadrant layout / 90: panel-by-panel parity ≥7/10 vs Hyperworks/Abaqus reference / 95: parity ≥8/10 + token system fully documented + 5+ canonical reference comparisons / **99: industrial-UI sub-agent rates ≥9/10 on 5 reference surfaces with cited evidence + full motion + theme + density + 4-quadrant + collapsible rails all shipped** |
| **4** | **AI workflow integration** | 60: 1 advisor surface (Phase 11 baseline) / 70: 2 surfaces / 80: advisor at 3 workflow stages (case-open + setup + review) / 90: advisor at 5 stages (+ mesh + solve-monitor) + 4-Q-gate at each / 95: every advisor call narrates uncertainty with calibration markers / **99: advisor present at every major workflow stage (≥6) + 4-Q-gate audited inline at each + ≥3 LLM backend support documented + advisor actions wire back into pipeline (not pure read-only)** |
| **5** | **Visualization & tracking** | 60: 3D viewport + result mesh / 70: + probe lists + section cuts / 80: + companion viewport + time-series scrubber / 90: + iso-surface + CSV export + comparison cuts / 95: + provenance overlays + WebGL E2E playwright / **99: real WebGL E2E + 60fps for ≥100k nodes + iso-surface + comparison + time-series + probe + section cut + companion all shipped + export to 3 formats (CSV/VTU/PNG)** |
| **6** | **Trust & reproducibility** | 60: case directory + INP/manifest / 70: schema versioning / 80: snapshots + signoffs / 90: full provenance chain at every step / 95: failed-attempt corpus indexed + ADR archive complete / **99: every operation has audit trail + cross-validation pinning automatic + ≥10 failed-attempt entries indexed + ADR archive linked from every component** |

### Composite

`composite = mean(dim1, dim2, dim3, dim4, dim5, dim6)` — **simple
arithmetic mean across 6 dimensions**. No weights, no transforms
(absolute honesty contract).

### Why 99 in rubric v2.0 ≠ signed validation

The rubric v1.0 99-anchor was "signed validation + independent
benchmark agreement", explicitly forbidden by the 绝对诚实客观
contract for Tier-1-candidate work. That's why v1.0 had a 99
ceiling.

Rubric v2.0 99-anchors are **verifiable engineering evidence**:
- Dim 1 99: cases × element classes × solver kinds counted from
  the codebase + Richardson coverage measured + ≥1 NAFEMS
  benchmark agreement evidence (NAFEMS test problems are public
  domain; agreement is not "signed validation by an authority").
- Dim 2 99: novice sub-agent transcript showing 100% scenario
  completion + WCAG audit report + role-branch coverage matrix.
- Dim 3 99: industrial-UI sub-agent report with reference-surface
  comparisons + cited file:line evidence.
- Dim 4 99: advisor-stage coverage matrix + 4-Q-gate audit at
  each + LLM backend documentation.
- Dim 5 99: playwright E2E report + performance metrics + format
  count.
- Dim 6 99: audit-trail inventory + failed-attempt index size +
  ADR cross-reference matrix.

All 6 are **codebase-verifiable**. 99+ under rubric v2.0 means
the codebase demonstrably has all these properties, NOT that an
authority signed off.

## 3 test sub-agent architecture preview (full protocols in 33 B)

### Sub-agent 1: `functional_tester`
- **Goal**: end-to-end run the product's real workflows and report
  what works / what breaks.
- **Inputs**: a target scenario from `.planning/test_subagents/scenarios/`
  (e.g., "open `cantilever-beam-candidate`, set BC, solve, view
  results, export CSV").
- **Procedure**: read the relevant runner / reader / frontend
  source; simulate the workflow via test-fixture; report passes /
  failures with file:line evidence.
- **Output schema**: JSON with `scenario_id`, `result: pass|fail|partial`,
  `evidence: [{step, status, file:line, observation}]`, `friction_points`.
- **Triggers**: every phase audit cycle (33 C, 33 E, 34 C, ...).

### Sub-agent 2: `novice_simulator`
- **Goal**: simulate a novice engineer using the product for the
  first time; report friction points + recovery-path quality.
- **Inputs**: a persona (e.g., "structural engineer, 1 year exp,
  never used the product before") + a task ("inspect the
  cantilever case + read the residual + decide whether to refine
  mesh").
- **Procedure**: walk through the UI surface as a novice would
  (no prior knowledge of file paths or developer conventions);
  flag every point where help text / advisor narration / error
  recovery is missing or unclear.
- **Output schema**: JSON with `persona`, `task`, `friction_points:
  [{step, missing: 'help'|'recovery'|'feedback'|'narration', severity:
  high|medium|low, evidence}]`, `completion: yes|no|partial`,
  `time_to_friction: <step number>`.
- **Triggers**: every phase audit cycle.

### Sub-agent 3: `industrial_ui_comparator`
- **Goal**: compare specific UI surfaces against industrial-software
  reference descriptions (Hyperworks / Abaqus CAE / ANSYS Mechanical);
  rate parity per surface with cited evidence.
- **Inputs**: a UI surface (e.g., "case-tree panel" / "results plot"
  / "BC setup panel") + reference description from
  `.planning/test_subagents/references/`.
- **Procedure**: read the corresponding frontend source + compare
  against reference description (information density / token use /
  layout convention / interaction affordance / accessibility).
- **Output schema**: JSON with `surface`, `reference_software`,
  `parity_score: 0-10`, `gaps: [{aspect, missing|present_but_lower_quality,
  reference_behavior, current_behavior, file:line}]`,
  `wins: [{aspect, present_in_current_only|matched}]`.
- **Triggers**: every phase audit cycle.

Reference descriptions ship as **text descriptions of reference
behaviors** (NOT actual screenshots — we cannot ship commercial
software screenshots). The descriptions are based on publicly-
documented behaviors (vendor user manuals, public training
materials, public conference videos).

## Honest re-baseline projection (Phase 33 C)

Current state under rubric v1.0: **89.68/100** (Phase 32 FINAL).

Projected per-dimension scores under rubric v2.0 (BEFORE Phase 33 D
lift):

| Dim | Score | Reasoning |
|---|---|---|
| **1 FEA capability** | ~78 | 11 validated cases (90-anchor at 12) + 5/11 Richardson coverage (90-anchor at 60% = 6.6/11) + 2 asymptotic-bias revelations (90-anchor at 1) + 5 solver kinds (90-anchor at 5) ✓; close to 90 but not there |
| **2 Novice UX** | ~62 | basic-mode toggle + UiModeToggle + tour (Phase 25 / 30); no role-branching (95-anchor); no full WCAG audit (90-anchor); novice sub-agent has never run (95-anchor blocks); ≈60-65 range |
| **3 Industrial UI parity** | ~55 | motion vocabulary 7 surfaces + dark token primitives + companion + section cut + probe lists — substantial polish but NO drag-resize / NO density toggle / NO 4-quadrant / NO dark-light theme toggle (80-anchor blocks); ≈50-60 range |
| **4 AI workflow integration** | ~50 | 1 advisor surface (Phase 11 AdvisorPanel); advisor NOT wired into case workflow stages; 60 anchor met; below 70 |
| **5 Visualization & tracking** | ~72 | 3D viewport + result mesh + probe + section cut + companion + time-series + CSV export — 80-anchor met; no iso-surface (90-anchor blocks); no WebGL E2E playwright (95-anchor blocks); ≈70-75 |
| **6 Trust & reproducibility** | ~70 | snapshots + signoffs (Phase 8/9) + provenance + schema versioning — 80-anchor partially met; no failed-attempt corpus (95-anchor blocks); ≈68-72 |
| **Composite** | **~64-68** | Mean of above. **Re-baseline drop from 89.68/v1.0 → ~66/v2.0**. |

**This drop is honest, not regression.** Rubric v1.0 measured 3
axes well; rubric v2.0 measures 6 axes — and 3 of those axes are
underdeveloped because prior phases focused elsewhere. The 89.68
under v1.0 remains a true measurement of v1.0's 3 axes.

## Multi-phase roadmap toward 99+

| Phase | Focus | Expected dim lifts |
|---|---|---|
| **33** | rubric v2.0 + sub-agents + re-baseline + 1 FEA lift | Dim 1 78→82 (1 case + 1 solver kind) |
| **34** | AI workflow wiring (mega-phase) | Dim 4 50→80 (+30) |
| **35** | Novice UX overhaul + role-branching | Dim 2 62→85 (+23) |
| **36** | Industrial UI parity push 1 (drag-resize + density + 4-quadrant) | Dim 3 55→78 (+23) |
| **37** | Industrial UI parity push 2 (dark/light theme + canonical reference surfaces) | Dim 3 78→92 (+14) |
| **38** | FEA cohort expansion (cases 13-15: coupled-temp-disp, modal-intermediate-L/h, dynamic) | Dim 1 82→90 (+8) |
| **39** | Visualization push (iso-surface + WebGL E2E playwright + comparison cuts) | Dim 5 72→92 (+20) |
| **40** | Trust push (failed-attempt corpus + ADR cross-link matrix + cross-validation automation) | Dim 6 70→92 (+22) |
| **41-43** | FEA cases 16-18 + NAFEMS benchmark agreement (Dim 1 → 99) | Dim 1 90→99 |
| **44** | Dim 2/3/4 final polish to 99 | Dim 2/3/4 → 99 |
| **45** | Dim 5/6 final polish to 99 + first composite ≥99 audit cycle | Dim 5/6 → 99 |

**Expected reach of 99+: Phase ~45.** ~12 phases, each adding 1-2
dimension axes of structural work. Each phase commit chain
remains scope-disciplined (1 phase = 4-6 slices = 1 retro =
v2.3 governance unchanged).

This is the **honest projection**, NOT a marketing roadmap.
Each phase will deliver what it delivers, the sub-agents will
score what they score, and the composite will be whatever the
sub-agents measure. The 99+ landing is **possible** but bound to
the actual delivery rate.

## Phase 33 anti-gaming guards

- **A:-1**: rubric v2.0 cannot be silently bumped to v2.1 to lift
  scores. ANY rubric anchor change must ship as a documented
  phase event (e.g., "Phase 38 anchor v2.0 → v2.1 because Dim
  N-2 sub-bullet rephrased; rationale + impact on prior scores
  re-computed inline").
- **B:-1**: Re-baseline must be performed by **3 fresh sub-agent
  instances** (functional / novice / UI), NOT by main session.
  Main session synthesizes; sub-agents score.
- **C:-1**: Phase 32 89.68/v1.0 and Phase 33+ <whatever>/v2.0
  must NEVER be compared directly (different scales). Each
  rubric's score is internally meaningful only.
- **D:-1**: Sub-agent reports must include `file:line` evidence
  for EVERY claim (no rubber-stamp synthesis). If a sub-agent
  reports "Dim 1 84/100" without file:line cohort enumeration,
  the score is rejected.
- **E:-1**: 99-anchors all require named verifiable evidence;
  hitting 99 on any dim requires that evidence to be produced
  AND committed to the repo (test artifact / report markdown /
  audit trail).
- **F:-1** (NEW): novice_simulator and industrial_ui_comparator
  must NOT see prior phases' audit files when running. Their
  briefing is the codebase + the protocol + the rubric — NOT
  the prior FINAL or retro (avoids anchor inflation via
  "previous score was X" priming).

## Hard constraints (carried verbatim from Phase 18-32)

- HF1.7a signed-registry hard-stop respected
- HF1.7b `*-candidate` carve-out for new artifacts
- HF1.8 path-guard self-protection
- tmp_path-only test writes (except golden_samples/*-candidate/)
- v2.3 governance round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract (no rubric reshaping for score, no
  score gaming)
- prefers-reduced-motion honored on all new motion
- Anti-gaming guards (A:-1 through F:-1)
- Phase 1-N chain additive only
- **NEW: rubric v2.0 99-anchor reachable via verifiable evidence**
  (NOT signed validation)
- NEVER re-score prior phases retroactively (89.68/v1.0 stays;
  rubric v2.0 is a NEW measurement axis)
- NEVER apply weights/transforms to composite (must remain simple
  arithmetic mean)
- No push / no PR / no Linear / no Notion writes unless
  explicitly authorized

## Phase 33 commit chain projection

| Slice | Tag | Description |
|---|---|---|
| 33 blueprint | (this commit) | Rubric v2.0 design + sub-agent architecture + roadmap |
| 33 A | next | `.planning/RUBRIC_v2.md` |
| 33 B | next | `.planning/test_subagents/` protocols |
| 33 C | next | Re-baseline audit (3 sub-agents R1 vs current state) |
| 33 D | next | `*CONTACT PAIR` Hertz validated case |
| 33 E | next | 3 sub-agents R2 vs post-33-D state + FINAL + retro + STATE |

## Closing

Phase 33 is the **scale-change phase**. It does not chase a
single big number; it builds the apparatus needed to honestly
measure 99-class work. The +0.67 Phase 32 delta becomes a
historical mark on the v1.0 scale; Phase 33+ moves to v2.0
where the 99+ target is reachable but distant.

The user's mandate ("99 分以上") is taken seriously and
literally: we will iterate until the rubric v2.0 sub-agents
honestly score ≥99 across all 6 dimensions. The path is ~12
phases. Each phase remains scope-disciplined and honest.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 17 consecutive
Tier-2 phases.
