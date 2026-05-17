# FM-04a Phase 30 — First *DYNAMIC validated case + 2-quadrant viewport split + Tier-2 polish + convergence artifacts · BLUEPRINT

> Authorized by user 2026-05-18. 6 commits planned (blueprint + 5 slices).
> 绝对诚实客观 contract carried verbatim from Phase 18-29.

## Phase 29 → Phase 30 lift target (honest projection)

| Dimension | Phase 29 actual (rubric v1.0) | Phase 30 R1 projection |
|---|---|---|
| UX  | 89.2 | 90.5-91.5 (+1-2.5 from toast-surface corrupted-key warn) |
| FEA | 77.5 | 82.0-84.0 (+4.5-6.5 from *DYNAMIC unlock; convergence-study lifts Dim 5) |
| UI  | 86.0 | 88.0-90.5 (+2-4.5 from 2-quadrant viewport split + coord-readout tooltip) |
| **Composite** | **84.23** | **86.8-88.7 (+2.6-4.5)** |

Phase 30 targets the two biggest single-axis lifts identified in Phase
29 audits:
1. First `*DYNAMIC` validated case → unlocks FEA Dim 6 floor (50 → 75)
2. 2-quadrant viewport split → UI Dim 5 industrial-parity (82 → 88)

Phase 30 projected composite 86.8-88.7 brings honest delivery within
~7-9 points of the **~95 ethical ceiling** acknowledged in Phase 29 E
FINAL. After Phase 30, the gap to honest 95 narrows to 6-8 points
needing 2-3 more phases (contact + composite-layup + thermal + branch-
onboard + reducer extraction + WebGL E2E).

## Reconnaissance done before this blueprint

- **CCX *DYNAMIC ALPHA=0** integrates Hilber-Hughes-Taylor (default α)
  implicit time stepping. INP shape:
  ```
  *STEP
  *DYNAMIC, ALPHA=0
  dt_initial, t_total
  *AMPLITUDE-driven *CLOAD or *INITIAL CONDITIONS
  ...
  *NODE FILE, FREQUENCY=1
  U
  *END STEP
  ```
- **FRD parser already supports multi-increment data**
  (`backend/app/parsers/frd_parser.py:47` defines `FRDIncrement` with
  `value` = time-per-increment + `displacements[nid]`). Time-history
  extraction is straightforward.
- **Phase 26 A cantilever modal case** (L=0.5m × h=w=0.020m steel,
  f_1 = 66.84 Hz, T_1 = 14.96 ms) provides the GEOMETRY + ANALYTICAL
  reuse path. No new geometry needed; same C3D10 quad-tet mesh.
- **2-quadrant viewport** can reuse ResultMeshWebGLViewport almost
  verbatim by mounting two copies side-by-side with sectionCut state
  duplicated; threshold filter / field component / probe list stay
  shared.
- **Toast component** already exists at
  `frontend/src/components/polishStyles.ts` (`fm04a-restored-toast`
  class); a corrupted-key toast follows the same pattern.

## Slice plan (5 implementation slices + audit)

### Slice A — 10th validated case · cantilever free-vibration · first *DYNAMIC

**Why**: FEA Dim 6 (Ballistic Tier-2 readiness) has been anchored at
50 for 11 phases — no `*DYNAMIC` validated case in a ballistic-FEA
workbench cohort. Phase 29 audit named this as the single biggest
single-axis lift available (+25 on Dim 6 → +4 to +6 composite).
Shipping implicit `*DYNAMIC` (Dim 6 50 → 75 anchor) is the
honest-paced path; explicit `*DYNAMIC` (Dim 6 75 → 90) is reserved
for a future phase tackling ballistic-scale physics.

**Approach**: cantilever free-vibration twang-test.
- **Geometry**: REUSE Phase 26 A's `cantilever-beam-modal-candidate`
  (L=0.5m × h=w=0.020m steel s355). No new .geo file.
- **Mesh**: reuse gmsh-generated C3D10 quad tets (Phase 26 A's
  mesh: ~1,895 nodes / ~814 elements).
- **BC**: clamp x=0 face (u_x=u_y=u_z=0 on all nodes).
- **Load**: single-step *DYNAMIC with *AMPLITUDE-ramped tip force.
  Apply half-sine impulse at the tip (200 N peak, 1 ms duration),
  then zero. Beam vibrates freely after the impulse.
- **Integration**: Hilber-Hughes-Taylor implicit, α=0 (no numerical
  damping). dt_initial = 1e-4 s. t_total = 60 ms (≈ 4 periods at
  T_1 = 14.96 ms).
- **Output**: `*NODE FILE, FREQUENCY=1, NSET=TIP_NODE` U.
- **Post-process**: extract tip u_y(t) time-history from
  FRDIncrement list; find observed period via zero-crossing
  detection. Compare to T_analytical = 1/f_1 = 14.96 ms.

**Files**:
- NEW `backend/app/services/cross_check/cantilever_dynamic_runner.py`
  (~280 LOC; reuses Phase 26 A's gmsh + cantilever_modal analytical)
- NEW `golden_samples/cantilever-dynamic-candidate/data/` (symlink
  or copy of Phase 26 A's .geo)
- NEW `golden_samples/cantilever-dynamic-candidate/cross_check_verdict.yaml`
  (schema 1.2.0 — adds `observed_period_s` + `analytical_period_s`)
- NEW `golden_samples/cantilever-dynamic-candidate/NOTES.md`
- MODIFIED `backend/app/services/reporting/_claim_tier.py` (+1 entry)
- MODIFIED `backend/tests/test_phase29a_plate_ss_shell.py` (loosen
  `len(validated) >= 9` to `>= 9`; already loose, no change needed)
- MODIFIED `backend/tests/test_phase29d_registry_tolerance_pin.py`
  (+1 entry to CANONICAL_TOLERANCES)
- NEW `backend/tests/test_phase30a_cantilever_dynamic.py` (~12
  unit tests + @requires_solver E2E)

**Anti-gaming guards**:
- **A:-1**: observed period derived from zero-crossing midpoints,
  NOT max-amplitude tracking (which could pad the verdict via
  numerical-noise bias).
- **D:-3**: ctx-not-mutated pin on runner result builder.
- **E:-1**: time-step Courant pin — dt must be << T_analytical/20
  (default dt=1e-4s ≪ 14.96 ms / 20 = 0.75 ms; ~7.5× safety).
- **E:-2**: damping pin — α must be 0.0 (no numerical damping; the
  natural period should reproduce exactly, not be damped away).

**Risks**:
- HHT-α with α=0 reduces to Newmark trapezoidal — no built-in
  numerical damping. Sufficient mesh refinement (Phase 26 A's mesh)
  + small dt should keep high-frequency artifacts bounded.
- Period extraction via zero-crossings requires 4+ zero crossings;
  4 periods of integration gives 8 zero crossings (more than
  enough).
- If the half-sine impulse excites higher modes too strongly, the
  zero-crossing analysis could be noisy. Mitigation: pin observed
  period within ±5% of analytical T_1 (rubric Dim 5 envelope).

**Commit message stem**: `FM-04a Phase 30 A: FIRST *DYNAMIC validated case (cantilever free-vibration) → 9 → 10 validated`

### Slice B — 2-quadrant viewport split + section-cut companion

**Why**: Phase 29 UI audit (Dim 5 industrial-parity) flagged "no
multi-viewport split + no measurement/coord tools. Abaqus/CAE ships
4-quadrant view by default; this is single-viewport. Hyperworks
coord-readout floating panel absent." This is the second-biggest
single-axis UI lift available.

**Approach**: side-by-side 2-quadrant layout when a new "compare"
toggle is on. Left pane: primary viewport (current). Right pane:
companion viewport at a different section-cut position. Shared
field/component/threshold state.

- NEW `frontend/src/components/CompanionViewport.tsx` (~120 LOC):
  thin wrapper around ResultMeshWebGLViewport that takes its own
  sectionCut state independent of the primary. Initial cut position
  = primary + half-thickness offset.
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`:
  add `showCompanionViewport` state (Phase 25 C UI mode advanced-
  only by default); add "Compare cuts" toggle in viewport header;
  when on, render flex layout with primary + companion side-by-side;
  when off, primary fills full width.
- localStorage persistence: `fm04a.companion-viewport.enabled.v1` and
  `fm04a.companion-viewport.cut-position.v1` (companion cut position).
- prefers-reduced-motion: layout transitions respect @media reduce.

**Anti-gaming guards**:
- **C:-1**: companion viewport state SCOPED separately from primary;
  toggling Compare off → state preserved (companion cut position
  doesn't reset).
- **D:-1**: default OFF (additive; existing reviewers see no change).
- **E:-1**: shared state (field component, threshold filter, probe
  list) confirmed identical in both viewports — pinned by test.

**Files**:
- NEW `frontend/src/components/CompanionViewport.tsx`
- NEW `frontend/src/components/companionViewportStorage.ts` (~60 LOC)
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`
- NEW `frontend/test/Phase30B_companion_viewport.test.tsx` (~25 tests)

**Risks**:
- WebGL contexts have per-canvas limits (~16 contexts typical).
  Two viewports should be well under; flagged for monitoring.
- Performance: 2× rendering load. Mitigation: companion uses lower
  LOD or is updated less frequently. Honest scope reduction
  acceptable for first ship.

**Commit message stem**: `FM-04a Phase 30 B: 2-quadrant viewport split with section-cut companion`

### Slice C — Toast-surface corrupted-key warn + coord-readout tooltip

**Why**: Bundle of two Tier-2 polish items from Phase 29 audits.

1. **Toast-surface corrupted-key warn**: Phase 29 D added a
   console.warn at probeListStorage parse-fail, but it's
   devtools-only observability. UX auditor flagged this caps Dim 5
   at 86 vs 90 anchor. A user-visible toast surfacing the warning
   is the missing piece.

2. **Coord-readout tooltip**: Hyperworks-style floating tooltip on
   viewport hover showing (x, y, z) of the cursor's mesh position.
   UI Dim 5 industrial parity secondary lift.

**Approach**:
- **Toast**: when `loadProbeList` returns initial state due to
  parse/shape failure AND a stored key existed (so it WAS something),
  surface a `restored-toast`-like UI ("Discarded corrupted probe
  list for case X — starting fresh"). Reuse the
  POLISH_CLASS_RESTORED_TOAST styling.
- **Coord readout**: a small fixed-positioned overlay that follows
  the mouse cursor in the WebGL viewport area. Shows current cursor
  XYZ in 3D world coords. Uses the existing raycaster's hit-point
  computation. Throttle to 30Hz.

**Files**:
- MODIFIED `frontend/src/components/probeListStorage.ts` (export
  signal for "discarded a corrupt key")
- MODIFIED `frontend/src/components/ResultMeshPlaybackPanel.tsx`
  (consume the signal; render toast)
- NEW `frontend/src/components/CoordReadoutTooltip.tsx` (~80 LOC)
- MODIFIED `frontend/src/components/ResultMeshWebGLViewport.tsx`
  (raycast for hover; emit coords)
- NEW `frontend/test/Phase30C_corrupt_toast_coord_readout.test.tsx`
  (~15 tests)

**Anti-gaming guards**:
- **D:-1**: corrupt-toast does NOT block use; offers a dismiss button.
- **E:-1**: coord readout throttled; no perf regression.
- **B:-1**: prefers-reduced-motion suppresses toast animation
  (already covered by the `restored-toast` reduce-motion rule).

**Commit message stem**: `FM-04a Phase 30 C: toast-surface corrupted-key warn + coord-readout tooltip`

### Slice D — Convergence-study artifacts for representative cases

**Why**: Phase 29 FEA audit (Dim 5) suggested "+ convergence-study
(mesh refinement) documented for each case; + Richardson
extrapolation residual." Currently no case has a convergence study;
each has just ONE mesh and ONE residual. A convergence study
strengthens the validation chain.

**Approach**: ship convergence artifacts for 2-3 representative
cases (one per element class). Each artifact = JSON table of
`(mesh_size, observed_value, residual_vs_analytical)` across 3+ mesh
refinements + Richardson extrapolation if applicable.

**Honest scope**: this is a PROOF-OF-PATTERN ship. Doing all 9 cases
in one phase is over-scope; pattern with 2-3 cases lets future
phases extend.

- NEW `backend/app/services/cross_check/convergence_study.py`
  (~120 LOC): runs the same case at N mesh refinements; produces
  the convergence artifact.
- NEW convergence artifacts for:
  - `plate-ss-shell-candidate` (S4 shell) — refinements 10×10,
    20×20, 40×40.
  - `cylinder-pv-candidate` (C3D10) — gmsh characteristic-length
    refinements 0.05, 0.025, 0.0125.
  - `cantilever-beam-modal-candidate` (C3D10 modal) — same.
- Each artifact written to
  `golden_samples/<case>/convergence_study.json`.
- NEW test pinning the convergence trend is monotone (residuals
  decrease as mesh refines).

**Files**:
- NEW `backend/app/services/cross_check/convergence_study.py`
- NEW `golden_samples/plate-ss-shell-candidate/convergence_study.json`
- NEW `golden_samples/cylinder-pv-candidate/convergence_study.json`
- NEW `golden_samples/cantilever-beam-modal-candidate/convergence_study.json`
- NEW `backend/tests/test_phase30d_convergence_study.py` (~8 tests)

**Anti-gaming guards**:
- **E:-1**: residual must MONOTONICALLY decrease with mesh
  refinement (or be within noise). Pinned per case.
- **D:-3**: no result is fabricated; live ccx runs at each mesh
  size produce the artifact.

**Risks**:
- Running 3 mesh sizes × 3 cases = 9 live ccx runs. Time-bound;
  acceptable.

**Commit message stem**: `FM-04a Phase 30 D: convergence-study artifacts for 3 representative cases`

### Slice E — 3 testing sub-agents + FINAL + retro + STATE

**Why**: per Phase 26-29 convention.

**Approach** identical to Phase 29 E. Each sub-agent reads
`RUBRIC.md v1.0` (no bump expected at this phase — anchors should
still apply). FINAL synthesis reports composite + per-axis breakdown.

**Honest expectation**: composite 86.8-88.7/100. Within ~7-9 points
of the honest ~95 ceiling. APPROVE gate still expected to FAIL by
6-12 points but the GAP NARROWS materially.

**Commit message stem**: `FM-04a Phase 30 E: 3 testing agents + honest composite <X>/100 + retro + STATE`

## Phase 30 hard constraints (carry-over from Phase 18-29)

- HF1.7a signed-registry hard-stop respected
- HF1.7b `*-candidate` carve-out
- HF1.8 path-guard self-protection
- tmp_path-only test snapshot writes
- v2.3 round cap = 3
- DEC frontmatter 6-field minimum per slice
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观: no rubric reshaping (RUBRIC.md v1.0 untouched in
  Phase 30 — anchors hold)
- prefers-reduced-motion honored on all new motion
- Anti-gaming guards at predicate level
- Phase 1-N chain additive only
- No push / no PR / no Linear writes unless explicitly authorized

## Phase 31 forward look (NOT this phase)

If Phase 30 lands at ~88/100:
- Contact case `*CONTACT PAIR` (FEA Dim 1 80 → 85)
- Composite-layup S4 case (FEA Dim 1 80 → 82)
- `*HEAT TRANSFER` validated case (FEA Dim 2 78 → 85)
- App.tsx reducer extraction (UI Dim 6 maintainability)
- Branching onboarding paths (UX Dim 1 90 → 99)
- Real WebGL E2E via playwright (process maturity)
- Iso-surface rendering (UI Dim 5 secondary)

That's ~6-8 items to cover in 2-3 more phases, lifting to ~92-95.
The final 95 → 99 gap likely requires signed external verification
or NIST benchmark agreement, which the project explicitly forbids.

**Honest planning anchor: Phase 30 aims for 87 ± 2. Phase 31-33
aim for 92-95. 95 is the ceiling under the Tier-1-candidate honest
contract.**
