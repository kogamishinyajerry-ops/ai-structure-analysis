# FM-04a Phase 18 blueprint — Tier 2 Transition (real solver + AI-driver + industrial workbench)

**Goal:** Pivot the harness from a Tier 1 reviewer-side audit tool to a Tier 2 production-class FEA workbench by (1) wiring a real solver subprocess (CalculiX `ccx`), (2) lifting the 9-token forbidden-positive-claim discipline that prevented "validated" language, (3) flipping AI from advisor-only to click-to-execute driver, (4) rebuilding the frontend as a command-paletted industrial workbench rendering all Phase 16-17 drift surfaces, and (5) honest 3-dimensional evaluation against industrial FEA toolstack standards.

**Authorization:** User directive 2026-05-17. Acknowledges this breaks the 17-phase Tier 1 SSOT chain. Explicit user choice in scope-tradeoff dialogue: "拆除 Tier 1 约束 · 真接 solver" + "5-slice 深打磨" + "按整个工业 FEA 工具栈评" + "绝对诚实客观".

**Honest scope warning (preserved verbatim from pre-execution dialogue):**
> Single-session full Tier 2 transition is unrealistic. Real CalculiX + mesh + materials + Tier 2 workbench + 3 testing agents typically spans weeks across multiple PRs. This phase will achieve the **first defensible Tier 2 milestone** (1 case end-to-end real solver + posture pivot + first-cut industrial UX) and **honestly score the gap** to a full Tier 2 toolstack. If the testing agents return 70/100, the retro records 70/100; the "99-point goal" is NOT met by rewording axes or shrinking the rubric. The remaining gap becomes Phase 19+ scope.

---

## 0. Tier 1 → Tier 2 posture pivot — what changes

| Discipline | Phase 1-17 (Tier 1) | Phase 18+ (Tier 2 transition) |
|---|---|---|
| Solver invocation | Never (CI synthetic-only) | **Real `ccx` subprocess** behind `@pytest.mark.requires_solver` (synthetic path remains for fast unit tests) |
| AI role | Advisor (read-only critique) | **Driver** — click-to-execute solver re-runs, mesh refinement suggestions, material swap |
| 4-question gate | Hard `400 Bad Request` if any answer no | **Reporting-only** — surfaces gate answers as audit metadata, doesn't block |
| 9-token forbidden-positive-claim audit | Hard refusal outside `not <claim>` form | **Tier-scoped**: tokens allowed when `tier == "tier_2_validated"` on the carrying envelope; refused on `tier == "tier_1_candidate"` envelopes |
| `claim_tier` schema field | Always `"Tier 1 engineering candidate"` | New enum `{"tier_1_candidate", "tier_2_validated"}` per envelope based on solver provenance |
| `claim_boundary` schema field | Always carries `not_signed_validation; not_benchmark_agreement` | Carries `not_signed_validation` only when `tier_1_candidate`; carries `cross_check_against_analytical` when `tier_2_validated` with analytical solution |
| Schema bumps | MINOR additive only | **MAJOR** bumps allowed for the tier discriminator field |

**What does NOT change** (preserved load-bearing invariants):
* HF1.7a signed-registry hard-stop (`^GS-\d{3}$` cases stay protected)
* HF1.7b `*-candidate` carve-out (Phase 18 work happens in `*-candidate` cases only; signed registry untouched)
* HF1.8 path-guard self-protection
* 5-case cohort SSOT (no new candidate cases unless solver run motivates one)
* tmp_path-only snapshot writes in tests (real `reports/snapshots/` byte-identical pre/post)
* Phase 16-17 drift attribution SSOT helpers (still consumed unchanged)

---

## 1. Slices

### Slice A — Real CalculiX runner subprocess

**Goal:** Add `CalculiXRunner` to `backend/app/adapters/calculix/`. Takes a case directory with an `.inp` file, spawns `ccx -i <jobname>`, captures stdout/stderr, returns the resulting `.frd` path. Reuses existing `CalculiXReader` for `.frd` parsing. Adds `@pytest.mark.requires_solver` pytest marker so the real-subprocess tests skip in CI but run locally on the dev box where `ccx` is installed.

**Deliverables:**
* `backend/app/adapters/calculix/runner.py` (NEW): `CalculiXRunner(ccx_binary: Path | str = "ccx", timeout_sec: float = 300.0)` class with `run(case_dir: Path, jobname: str) -> CalculiXRunResult` method. `CalculiXRunResult` dataclass carries `(returncode, stdout_path, stderr_path, frd_path, dat_path, runtime_sec)`. Raises `CalculiXRunError` with diagnostics on non-zero exit. **No CI mocking** — when the marker is on, the test really runs ccx.
* `backend/app/adapters/calculix/inp_writer.py` (NEW): `write_linear_static_inp(case_dir, *, geometry, material, boundary_conditions, load) -> Path` builds a minimal valid linear-static INP for the linear_static_pv analysis type. Targets the cylinder-pv-candidate case as first end-to-end victim.
* `pytest.ini` / `pyproject.toml`: register `requires_solver` marker; default `addopts` skips it; `make test-solver` opts in.
* `backend/tests/test_phase18a_calculix_runner.py`: at least 10 tests covering (a) runner subprocess success path on a synthetic 1-element model, (b) timeout handling, (c) non-zero exit raising structured error with stderr tail, (d) `.frd` parser handoff to existing `CalculiXReader`, (e) cylinder-pv-candidate end-to-end (geometry → INP → ccx → .frd → metrics) marked `requires_solver`, (f) the synthetic-path unit tests still run without ccx.

**Anti-gaming guards (per Phase 18 binding rubric §3.A):**
* **M:-1** — `CalculiXRunner` and `CalculiXReader` are separate classes; runner doesn't know about parsing, reader doesn't know about subprocess (clean Layer-1 split per RFC-001).
* **T:-3** — End-to-end pin: cylinder-pv-candidate run produces `.frd` with `len(node_count) > 0` AND `frd_path.stat().st_size > 0` AND stress field present (not just an empty solver wrapper).
* **C:-2** — Runner refuses signed-registry paths (`^GS-\d{3}$` in `case_dir.name` raises before subprocess).
* **A:-2** — Subprocess always invoked with bounded timeout; long-running jobs killed and `runtime_sec` capped.
* **V:-3** — All runner workspaces under tmp_path; the real `golden_samples/cylinder-pv-candidate/` data file is read but not modified.

---

### Slice B — Tier 1 → Tier 2 posture pivot

**Goal:** Document the pivot via a new ADR + lift the 9-token forbidden audit to a tier-scoped check + introduce the `claim_tier_enum` schema discriminator + flip AI advisor 4-question gate to reporting-only.

**Deliverables:**
* `docs/adr/ADR-014-tier2-transition.md` (NEW): records the authorized pivot, the broken invariants, the new tier discriminator, the rationale (real solver enables real validation against analytical solutions, not "endorsing without evidence"), and the migration path for the 5-case cohort.
* `backend/app/services/reporting/_claim_tier.py` (NEW): SSOT enum `ClaimTier = Literal["tier_1_candidate", "tier_2_validated"]` + `CLAIM_TIER_REGISTRY` mapping case_id → tier (cylinder-pv-candidate becomes `tier_2_validated` after slice A success).
* `tests/_test_utils/__init__.py`: extend `assert_tier1_trio` → add sibling `assert_tier2_trio` that verifies tier_2_validated envelopes carry `tier: "tier_2_validated"` + analytical cross-check evidence reference + cleared 4-question gate result.
* `backend/app/services/reporting/_forbidden_tokens.py` (NEW; replaces inline 9-token tuple): `is_token_allowed(token, *, tier) -> bool` — when tier is tier_2_validated, the 5 advisor-class tokens (`production ready` / `certified` / `approved for service` / `asme compliant` / `signed off`) are still refused (those are reviewer judgment, not solver output), but the 4 solver-class tokens (`validated against` / `validated physics` / `perforation completed` / `bullet-through-steel complete`) are ALLOWED if the carrying envelope cites an analytical cross-check verdict.
* `backend/app/services/advisor.py` (or wherever the 4Q gate lives): change `gate_response_or_reject` → `gate_response_with_audit`; surfaces gate answers as `gate_audit_metadata: dict` on the response, never raises.
* `backend/tests/test_phase18b_tier_pivot.py`: at least 12 tests covering tier discriminator, tier-scoped token policy, 4Q gate now reporting-only, ADR-014 referenced from STATE.

**Anti-gaming guards (per §3.B):**
* **M:-2** — Tier discriminator is a single SSOT enum (not duplicated per envelope); a future maintainer adding a third tier value lands in one place.
* **T:-4** — Migration test: cylinder-pv-candidate tier flips ONLY after slice A end-to-end ccx run produces a .frd with stress field; other 4 candidates stay tier_1_candidate.
* **C:-1** — Tier-scoped forbidden-token policy refuses advisor-class tokens regardless of tier (those represent reviewer authority, not solver evidence).
* **A:-3** — Backward compatibility: every envelope schema must declare `tier` field at MAJOR bump; reading a pre-tier envelope defaults to `tier_1_candidate` (conservative).

---

### Slice C — Mesh + Materials library

**Goal:** Minimal mesh generator (Gmsh subprocess) + materials JSON library + UI panels. Demonstrates the geometry → mesh → material → solver flow end-to-end through one realistic case.

**Deliverables:**
* `backend/app/services/meshing/gmsh_runner.py` (NEW): subprocess wrapper over `gmsh` CLI producing linear tet meshes from STEP/STL/BREP input. Returns mesh metadata (node count, element count, quality histogram).
* `backend/app/services/materials/library.json` (NEW): structured material database with steel-S355, aluminium-6061-T6, titanium-Ti-6Al-4V (E [Pa], ν, ρ [kg/m³], yield_stress [Pa], ultimate_stress [Pa], reference source).
* `backend/app/services/materials/api.py` (NEW): `list_materials() -> list[Material]`, `get_material(material_id) -> Material`.
* `backend/app/api/routes/materials.py` (NEW): `GET /api/v1/materials/`, `GET /api/v1/materials/<id>`.
* `frontend/src/components/MaterialPickerPanel.tsx` (NEW): React component browsing material library.
* `frontend/src/components/MeshControlPanel.tsx` (NEW): React component for mesh density / element order selection.
* `backend/tests/test_phase18c_mesh_materials.py`: ≥15 tests covering mesh subprocess (marked `requires_gmsh`), materials library lookup, route shape validation, end-to-end pipeline (geometry → meshed INP → solver ready).
* `frontend/test/MaterialPickerPanel.test.tsx` + `frontend/test/MeshControlPanel.test.tsx`: ≥8 tests covering component rendering, material selection, error states.

**Anti-gaming guards (per §3.C):**
* **M:-1** — Materials library JSON is a single SSOT file; tests pin specific values to prevent silent material-property drift (e.g., steel E == 210e9 Pa exactly).
* **T:-3** — End-to-end pipeline test: requesting "cylinder + steel + medium mesh + linear static" produces an INP that the slice-A runner can consume.
* **C:-1** — Material library values carry citation references (`reference_doi` / `reference_isbn` / `reference_url` field); a value without provenance fails the SSOT loader.
* **A:-2** — Gmsh subprocess refuses paths outside the case workspace; can't be tricked into reading arbitrary files.

---

### Slice D — Tier 2 Frontend workbench

**Goal:** Refactor `App.tsx` (1926 LOC monolith) into a layout shell + panel composition. Add command palette (Cmd-K) + keyboard shortcuts + empty state design + loading skeletons + Phase 16-17 drift surface rendering. Extend 3D viewport for new CalculiX .frd output (stress contour overlay).

**Deliverables:**
* `frontend/src/layout/WorkbenchShell.tsx` (NEW): 3-pane layout shell extracted from App.tsx. App.tsx shrinks to <500 LOC composition root.
* `frontend/src/components/CommandPalette.tsx` (NEW): Cmd-K (Mac) / Ctrl-K (other) opens fuzzy-search panel. Commands sourced from `frontend/src/commands/registry.ts` — every reviewer action registers a command (`switch tab visual`, `run solver`, `select case <id>`, `submit signoff`, `open material picker`, `request mesh refine`, etc).
* `frontend/src/hooks/useKeyboardShortcuts.ts` (NEW): global shortcut binding. `?` opens cheatsheet, `g + 1..4` switches tabs, `[ / ]` cycles cases, `s` submits signoff.
* `frontend/src/components/empty/`: standard empty-state cards for no-case-selected / no-snapshots / no-drift-detected with onboarding affordances.
* `frontend/src/components/loading/SkeletonCard.tsx` (NEW): standardized loading shimmer.
* `frontend/src/components/error/ErrorCard.tsx` (NEW): standard error display with structured remediation steps.
* `frontend/src/components/DriftBadge.tsx` (NEW): renders `{dominant_axis} {±N.N%}` with severity color (info/warn/danger from per-axis floor).
* `frontend/src/components/DriftAttributionCard.tsx` (NEW): renders from/to snapshot + per-axis delta breakdown + Phase 16-17 provenance.
* **CohortAnomaliesPanel** extended: renders BOTH `cohort_drift_attribution` (latest pair · Phase 16 B) AND `cohort_cumulative_drift_attribution` (cumulative · Phase 17 A).
* **CohortTrendAnomaliesPanel** extended: renders BOTH raw `slope` (Phase 9 D) AND `percentage_delta_slope` (Phase 17 C) — cross-axis comparability badge.
* **SignoffHistoryPanel** extended: renders BOTH `drift_attribution_at_signoff_time` (latest · Phase 16 C) AND `cumulative_drift_attribution_at_signoff_time` (cumulative · Phase 17 B).
* **ResultMeshPlaybackPanel** extended: accepts new CalculiX .frd payload schema; renders stress contour overlay.
* `frontend/test/`: ≥25 new tests covering layout shell, command palette fuzzy search, keyboard shortcuts, empty states, drift badge color-coding, drift attribution card rendering, extended panel drift fields.

**Anti-gaming guards (per §3.D):**
* **M:-1** — App.tsx LOC count assertion test (`<= 500 lines after refactor`) prevents monolith regression.
* **T:-3** — Command palette registry test: every command exposes (id, label, hotkey?, handler); duplicate command IDs trip a registry assertion.
* **C:-1** — Tier 1 disclaimer trio still surfaces on tier_1_candidate envelopes in the UI (Tier 2 envelopes show different boundary copy).
* **A:-2** — Keyboard shortcuts don't fire when focus is in a text input.
* **V:-3** — Visual smoke: dev server `npm run dev`, click through demo flow, verify drift badges render with real data. (Documented; not automatable in this session — testing agent does manual eval.)

---

### Slice E — 3 testing agents + honest 99-pt scoring + closure

**Goal:** Three independent testing agents evaluate three orthogonal dimensions and return brutally honest scores. The retro records the actual composite, not an idealized one. If composite < 99, the retro documents which axes need iteration in Phase 19.

**Testing agent definitions:**

**Agent 1 — UX testing agent (novice reviewer simulation)**

Spawned as `general-purpose` subagent with prompt: "Simulate a new structural engineer who has never seen this tool. Walk through these 5 tasks, scoring each 0-20 on (a) task completion, (b) clicks/keystrokes count vs minimal, (c) error recovery quality, (d) onboarding clarity, (e) plain-language explanation availability:
1. Open the workbench, find the leak case, understand what's wrong.
2. Submit a signoff with the verdict `needs_more_evidence`.
3. Trigger a real solver re-run on cylinder-pv-candidate via Cmd-K.
4. Swap the material from steel to aluminium and re-run.
5. View the resulting stress contour overlay.
Return per-task score (5 × 0-20 = 0-100), composite score, top 3 deficiencies with file:line citations, and one specific UX improvement that would lift the lowest-scoring task. Be ruthless — if onboarding requires reading source code, deduct."

**Agent 2 — FEA capability agent (industrial toolstack benchmark)**

Spawned as `general-purpose` subagent. **The user explicitly chose to evaluate against the full industrial FEA toolstack**. Scoring dimensions (0-10 each, 10 dimensions = 100 pts):
1. Solver coverage (linear static / nonlinear static / modal / buckling / explicit dynamics / thermal / coupled)
2. Mesh generation quality (element types supported, quality metrics, adaptive refinement)
3. Material library breadth + provenance
4. Geometry import (STEP/IGES/STL coverage)
5. Boundary condition expressiveness
6. Contact modeling support
7. Nonlinear solver capability (material / geometric / contact nonlinearity)
8. Result post-processing (stress / strain / displacement / safety factor)
9. Analytical cross-check infrastructure (Tier 1 → Tier 2 transition discipline)
10. Documentation quality + ADR coverage
Return per-dimension 0-10 score with one-line justification each, composite (0-100), and a verdict (APPROVE if composite ≥ 99 AND every dimension ≥ 9.5; CHANGES_REQUIRED otherwise). **Honest pre-warning:** This score is highly likely to be in the 30-50 range after Phase 18; that's the truth, not a failure of the slice work.

**Agent 3 — UI tier agent (vs ANSYS Workbench / SimScale / Abaqus CAE)**

Spawned as `general-purpose` subagent with prompt: "Compare the Phase 18 workbench UI against ANSYS Workbench, SimScale, and Abaqus CAE on these 10 axes (0-10 each):
1. Information density vs whitespace balance
2. Command accessibility (palette / menu / shortcuts)
3. Visual hierarchy and typography
4. Error/warning surface design
5. Empty state and onboarding affordances
6. Accessibility (ARIA labels, keyboard nav, color contrast)
7. Loading state design (skeleton/shimmer vs spinner)
8. Responsiveness/feel (interaction latency perception)
9. Industrial aesthetic (dark/light theme maturity, brand consistency)
10. 3D viewport quality + result visualization clarity
Return per-axis 0-10 with one-line justification, composite, verdict (APPROVE if composite ≥ 99 AND every axis ≥ 9.5)."

**Composite scoring:**
* Final score = `(UX + FEA + UI) / 3` rounded to 1 decimal.
* **APPROVE** iff: (a) composite ≥ 99, AND (b) each individual agent score ≥ 99, AND (c) no individual axis < 95% of cap.
* Anything less = CHANGES_REQUIRED. Retro documents which axes failed and what Phase 19+ would need to do.

**Deliverables:**
* `.planning/phase18_audit_reports/UX.md`, `FEA.md`, `UI.md`, `FINAL.md` (4 NEW reports written by the 3 agents + a synthesis).
* `.planning/retrospectives/fm04a_phase18_tier2_transition.md` (NEW): scope, per-slice summary, quantitative outcome, what-worked, what-didn't, **honest composite score**, Phase 19+ carry-forwards.
* `.planning/STATE.md` refresh.
* **Iteration loop:** if FINAL composite < 99, spawn at most 2 additional iteration rounds focused on the lowest-scoring axes, re-run the 3 agents, update FINAL.md. If still < 99 after 3 rounds total, **stop and honestly report the gap** — do not fabricate a 99 score.

---

## 2. Hard constraints (preserved)

* HF1.7a signed-registry hard-stop (signed-registry cases stay untouched)
* HF1.7b `*-candidate` carve-out
* HF1.8 path-guard self-protection
* tmp_path-only test snapshot writes (real `reports/snapshots/` byte-identical pre/post)
* No push, no PR, no Linear / Notion writes (local branch work only)
* No new GS-registry entries
* Phase 16-17 drift attribution SSOT helpers preserved (frontend renders them; backend doesn't replace)
* 5-case cohort SSOT preserved unless solver run motivates a 6th case (e.g., real CalculiX validation case)

## 3. Honest evaluation framework

Three agents, one composite, no rubric reshaping:

| Dimension | Cap | Honest realistic projection (single-session Phase 18) |
|---|---|---|
| UX (novice flow + clarity) | 100 | 60-85 (depends on Slice C/D depth) |
| FEA capability (industrial benchmark) | 100 | 30-55 (single solver + minimal mesh + 3 materials) |
| UI tier (vs ANSYS/SimScale/Abaqus) | 100 | 55-80 (Cmd-K + shortcuts + drift surface rendering; no 3D viewport rewrite from scratch) |
| **Composite** | **100** | **48-73** (single session); 99 likely requires Phase 19+ |

**If final composite is below 99, the user is informed honestly. Phase 18 closure is conditional on truthful reporting, not on hitting 99.**

## 4. Acceptance criteria

* [ ] All 5 slices A-D ship deliverables with their binding sub-rubric scores met.
* [ ] Slice E archives 4 audit reports + retrospective + STATE refresh.
* [ ] Three testing agents return scored reports.
* [ ] Hard constraints all PASS (HF1, signed registry untouched, tmp_path only, no push/PR/Notion).
* [ ] **Composite score documented honestly** in the retro (whether 99+ or not).
* [ ] If composite < 99, Phase 19+ carry-forward list documents the gap path.

---

**Phase 18 thesis:** Tier 1 reviewer-harness → Tier 2 production-class first milestone with real solver. Honest evaluation against industrial benchmarks. No score gaming.
