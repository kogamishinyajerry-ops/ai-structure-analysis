# FM-04a Phase 34 — AI advisor case-open + *CONTACT PAIR ccx + Dim 2 vocab fix

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-33. **18 consecutive Tier-2 phases**.

## Position in the 99+ journey

Phase 33 closed the **scale-change foundation phase** at composite
69.33/100 (rubric v2.0). Phase 34 is the **first feature-build
phase** under the new scoring system.

The multi-phase roadmap (from Phase 33 FINAL) puts Phase 34 in the
AI-workflow-wiring + first-ccx-lift band, projection 70.5-73.

## User mandate (verbatim)

> 批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程
> AI FEA 功能），瞄准蓝图进行开发，要有一套专门的测试子 agent，
> 真实测评项目的功能、使用手感、可视化追踪……明确的完成度评分
> 机制（绝对诚实客观，且维度充足）……一直迭代开发下去，直至达到
> 你眼里的优秀水准（99 分以上）

Phase 34 acts on three of the 26 honest gaps Phase 33 surfaced:
1. **Gap #4 ballistic-vocab leak** (Dim 2 + Dim 3 cross-cut)
2. **Gap #13 advisor at case-open stage** (Dim 4)
3. **Gap #1 *CONTACT PAIR ccx integration** (Dim 1, closes Phase 33 D deferral)

## Slice plan

| Slice | What lands | Projected dim impact |
|---|---|---|
| 34 blueprint | This document | — |
| **34 A** | Ballistic-vocab fix in `CaseComparisonPanel.tsx:227-253`. Replace static "residual velocity / perforation marker / energy audit" axes with analysis-type-aware axes driven by `ANALYSIS_TYPE_TUPLE` (Phase 11 SSOT). For static-structural cases: "vM stress / max displacement / safety factor". For modal: "1st-mode frequency / mass participation / mode shape coherence". For ballistic: keep existing. | Dim 2 +1 / Dim 3 +0.5 |
| **34 B** | AI advisor at case-open stage. New `CaseOpenAdvisorCard.tsx` component (slimmer than full AdvisorPanel; surfaces 1-paragraph contextual brief + 4-Q-gate at mount). Renders in the case-overview area after case selection. Lifts advisor-stage count 1→2. | Dim 4 62→67 (+5) |
| **34 C** | `*CONTACT PAIR` ccx runner + validated case. Build `hertz_contact_runner.py` following Phase 31 A heat-transfer template (~550-700 LOC). Geometry re-tuned to elastic regime: R=0.050m, L=0.050m, F=5000N → p_0≈271 MPa (below S355 yield 355 MPa), δ≈4 µm. Mesh refinement near contact via gmsh `cl≈0.5mm at contact / cl≈5mm at far field`. CCX `*CONTACT PAIR, TYPE=SURFACE TO SURFACE` with `LINEAR` pressure-overclosure, NLGEOM=NO. Output: vertical displacement at cylinder top via `*NODE PRINT, NSET=CYLINDER_TOP, U`. Verdict YAML schema 1.3.0 → 1.4.0 (additive `solver_kind: contact_pair_static`). Cohort validated count 11→12. | Dim 1 78→82 (+4) |
| **34 D** | 3 sub-agents R2 audit + FINAL composite + retro + STATE refresh + commit. | — |

**Total projected composite lift: ~+1.5-2.0 (69.33 → 70.8-71.5)**

Lands in the lower-to-middle of the projected band 70.5-73; the
high end requires Dim 4 lifts beyond just case-open advisor (3-stage
push moves to Phase 35 or split-out 34 sub-D).

## Phase 34 anti-gaming guards

All Phase 33 anti-gaming guards (A-G) carry verbatim. Phase 34-specific:

- **H:-1** (NEW): Phase 34 C ccx integration must produce a REAL live
  ccx run before the case counts as validated. NO mocked output. If
  ccx doesn't converge in this session, Phase 34 C ships analytical
  + infrastructure only (Phase 33 D pattern) and Phase 35 D picks up
  the ccx integration. Cohort lift is GATED ON real ccx evidence.
- **I:-1** (NEW): Phase 34 B advisor case-open card must NOT degrade
  the Phase 11 `AdvisorPanel` already in `VisualTabPanel`. Both must
  coexist. Render-only addition.
- **J:-1** (NEW): Phase 34 A ballistic-vocab fix must NOT change the
  CSV export schema (Phase 25 D 5-column export pinned). Visible
  copy changes only; data schema stable.

## Slice 34 A details

**Problem** (from Phase 33 C novice_simulator triple-flagged finding):
`CaseComparisonPanel.tsx:227-253` shows axis labels:
- "residual velocity"
- "perforation marker"
- "energy audit"

For a cantilever-beam case or a plate-with-hole case, these labels
are nonsensical and confused P1 (junior eng), P2 (senior eng), and
P5 (student). All three flagged the same finding independently.

**Fix scope**:
- Read `ANALYSIS_TYPE_TUPLE` from Phase 11 (likely at
  `backend/app/services/reporting/case_completeness.py` or similar)
- In `CaseComparisonPanel.tsx`, derive axis labels from the case's
  `analysis_type` (static / modal / buckling / ballistic / heat
  transfer / contact)
- Provide a fallback to a "generic" label set for any analysis type
  not in the catalogue
- Pin axis-label mapping with a frontend test

**Anti-gaming guards within 34 A**:
- B:-1: axis labels for "ballistic" case kind unchanged (avoid
  regressing the original use case)
- C:-1: existing CSV export schema (Phase 25 D) unchanged
- D:-1: pin tests assert each case kind's axis labels

## Slice 34 B details

**Problem** (Phase 33 C functional_tester finding + Dim 4
synthesis): the existing `AdvisorPanel` is mounted only at
`VisualTabPanel.tsx:185`, which is the post-solve review stage.
A novice opens a case, but at that moment they have NO advisor
narration about what the case is, its assumptions, or its
expected outcome.

**Fix scope**:
- New component `CaseOpenAdvisorCard.tsx` (~150 LOC)
- Renders a 1-paragraph advisor brief about the current case
  (assumptions / setup / what to look for)
- 4-Q-gate audit visible inline (LLM offline? / artifacts? /
  TrustGate? / advisory-only?)
- Uses existing `AdvisorProvider` + `StubAdvisor` (no new backend
  protocol)
- Mount point: in the case-overview region (likely after
  `Sidebar` case-select returns, before `VisualTabPanel` mounts)
- StubAdvisor fallback for offline / LLM-unavailable

**Anti-gaming guards within 34 B**:
- I:-1: existing `AdvisorPanel` in `VisualTabPanel` not changed
- D:-1: 4-Q-gate audit visible at this surface
- E:-1: advisor stage count goes 1→2 (verifiable: grep usages)

## Slice 34 C details

**Problem** (Phase 33 D deferral): cohort stuck at 11 validated
cases because `*CONTACT PAIR` ccx integration was deferred. Hertz
analytical SSOT module shipped Phase 33 D; live ccx integration
is the remaining work.

**Fix scope**:

1. **Geometry re-tune to elastic regime**:
   - Cylinder: R=0.050 m, L=0.050 m
   - Block: W=0.200 m, D=0.200 m, H=0.100 m (4R × 4R far-field)
   - Material: steel-s355 (E=210 GPa, ν=0.3, yield=355 MPa)
   - Load: F=5000 N vertical on cylinder top
   - Analytical (re-computed via hertz_contact.py):
     - f_per_length = 100,000 N/m
     - b = sqrt(4 × 100000 × 0.050 / (π × 1.154e11)) ≈ 235 µm
     - p_0 = 2 × 100000 / (π × 235e-6) ≈ 271 MPa (≤ yield ✓)
     - δ ≈ (100000/(π × 1.154e11)) × (1 + 2 ln(4 × 0.050/235e-6)) ≈ 4.0 µm
   - Mesh: cl=0.5mm at contact zone (~12 elements across b),
     cl=5mm at far field. Estimated ~30-50k C3D8 nodes.

2. **Geometry generation** (`cylinder_on_block.geo`):
   - GMSH script generating two solids
   - Physical groups for: CYLINDER_VOLUME, BLOCK_VOLUME,
     CYLINDER_TOP_FACE (load surface), CYLINDER_BOTTOM_FACE
     (master contact surface), BLOCK_TOP_FACE (slave contact
     surface), BLOCK_BOTTOM_FACE (fixed BC)

3. **INP composer** (`hertz_contact_runner.py`):
   - Standard mesh-from-gmsh import
   - Two `*SOLID SECTION` blocks (one per body)
   - `*SURFACE, NAME=CYLINDER_LOWER, TYPE=ELEMENT` from cylinder
     bottom face
   - `*SURFACE, NAME=BLOCK_UPPER, TYPE=ELEMENT` from block top face
   - `*CONTACT PAIR, INTERACTION=hertz_interaction, TYPE=SURFACE
     TO SURFACE, SMALL SLIDING`
     `CYLINDER_LOWER, BLOCK_UPPER`
   - `*SURFACE INTERACTION, NAME=hertz_interaction`
   - `*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR`
     `1.0e15, 1.0e-9` (very high stiffness with small softening)
   - `*STEP, NLGEOM=NO` (small deformation)
   - `*STATIC, DIRECT, 1.0, 1.0`
   - `*CLOAD` on `CYLINDER_TOP_FACE` distributing F=5000N over the
     nodes (or `*DLOAD` if pressure-loading)
   - `*BOUNDARY` on `BLOCK_BOTTOM_FACE`: 1,3 = 0
   - `*NODE PRINT, NSET=CYLINDER_TOP_CENTER` to get U_z

4. **Reader**: standard `.dat` or `.frd` parsing for U_z at the
   center-top node of the cylinder

5. **Residual computation**:
   - observed_indentation_m = max(|U_z|) at cylinder top
   - residual = residual_pct(observed, analytical_delta)
   - Tolerance: 15% (per Phase 33 D NOTES.md projection); contact
     mesh resolution + Hertz line-contact end-effect noise

6. **Verdict YAML** at
   `golden_samples/hertz-contact-candidate/cross_check_verdict.yaml`:
   - schema_version: 1.4.0 (additive bump for `solver_kind`)
   - solver_kind: contact_pair_static
   - verdict: PASS or FAIL based on residual ≤ tolerance
   - cohort_membership: tier_2_validated

7. **Tests** (~6-8 backend pin tests):
   - INP composer pins (CONTACT PAIR keyword presence + surface
     pair correctness)
   - Reader-runner round-trip pin
   - Verdict YAML schema pin
   - residual_pct sign-alignment pin
   - cohort count assertion (11 → 12)

**Anti-gaming guards within 34 C**:
- H:-1: ccx must converge with REAL output. Mock-ccx tests
  forbidden for validation; only allowed at the unit-test layer
  for INP composer.
- A:-1: analytical pin tests from Phase 33 D unchanged
- D:-3: analytical formulas reused from `hertz_contact.py`, no
  parallel implementation

**Honest fallback path** (if ccx doesn't converge):
- Ship infrastructure (INP composer + reader integration + runner
  scaffolding + tests against INP keyword presence) with
  `verdict: INFRASTRUCTURE_ONLY_PHASE_34_C` in expected_results.json
- Cohort count stays 11
- Document the convergence issue in NOTES.md
- Schedule Phase 35 or 36 with a re-tuned penalty / mesh

## Slice 34 D details

**Audit cycle**:
- 3 sub-agents R2 in parallel (functional_tester / novice_simulator
  / industrial_ui_comparator); briefing names the codebase post-34-C
  state; forbidden from reading prior FINAL / retro / blueprint
  (F:-1 anti-priming carries verbatim)
- Main-session syntheses for Dim 4 + Dim 6 (file:line cited)
- FINAL composite synthesis
- Phase 34 retro covering 4 slices + honest tensions
- STATE.md refresh with Phase 34 stamp; Phase 33 stamp demoted
  to context-retained section

## Phase 34 projection

| Dim | Phase 33 | Phase 34 projected | Δ | Lift source |
|---|---|---|---|---|
| 1 FEA | 78 | **82** | +4 | Contact-pair cohort 11→12 + solver kind #6 |
| 2 Novice UX | 58 | **59** | +1 | Ballistic-vocab fix removes 1 high-friction event |
| 3 Industrial UI | 74 | **74.5** | +0.5 | Vocab fix touches Dim 3 secondarily |
| 4 AI workflow | 62 | **67** | +5 | Case-open advisor stage (1→2 surfaces; 4-Q-gate at new surface) |
| 5 Visualization | 72 | 72 | 0 | Untouched |
| 6 Trust | 72 | 72 | 0 | Untouched |
| **Composite** | **69.33** | **~71.1** | **+1.8** | Within projected 70.5-73 |

**Phase 34 projection: 70.5-73 / v2.0**; this plan targets ~71.

## Hard constraints

All Phase 18-33 hard constraints carry verbatim:
- HF1.7a/b/8 signed-registry hard-stop + *-candidate carve-out
  + path-guard
- tmp_path-only test writes
- v2.3 round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract
- prefers-reduced-motion honored on any new motion
- Anti-gaming guards A through G + new H/I/J for this phase
- Phase 1-N additive only (no test threshold edits)
- Rubric v2.0 99-anchor reachable via verifiable evidence
- NEVER re-score prior phases retroactively
- NEVER apply weights/transforms to composite
- No push / no PR / no Linear / no Notion writes

## Closing

Phase 34 begins the **multi-phase feature build-out toward 99+**.
After Phase 33's apparatus-building, this is the first phase
producing real composite Δ on the v2.0 scale. The projected lift
is modest (+1.8) — honest, scope-disciplined, and matched to the
session budget. Phase 35+ continues with Novice UX role-branching
and Industrial UI infrastructure.

The user's 99+ target is reached at Phase ~45 via cumulative
~30-point composite lift across ~12 phases. Each phase contributes
within its honest scope; no rubric reshaping; no score gaming.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 18 consecutive
Tier-2 phases.
