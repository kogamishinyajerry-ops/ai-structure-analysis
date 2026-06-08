# FM-04a Phase 32 — Convergence-ubiquity + App-root reducer + Tier-2 polish bundle

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-31. 16 consecutive Tier-2 phases.

## Headline (honest projection)

**Phase 32 honest composite projection: 89.5 - 90.5/100**
(target: +0.5 to +1.5 over Phase 31's 89.01; aiming at the rubric
v1.0 95-ceiling acknowledged in Phase 29 D / Phase 30 / Phase 31).

## Strategy

Phase 31 closed 6 of Phase 30 FINAL's 17 honest gaps with a
distributed-polish phase that nonetheless landed two structural
FEA verticals (heat transfer + Richardson). Phase 32 takes
**conscious lower-FEA-ambition** in exchange for closing
infrastructure debt that's been accumulating since Phase 27.

### Recon completed in this blueprint (honest pivot)

The 3 Tier-1 items the Phase 31 FINAL ranked as cheapest big lifts
each turn out to require schema work that exceeds single-phase
scope under the v2.3 governance round-cap = 3:

1. **`*CONTACT PAIR` Hertz contact case** — recon at
   `backend/app/core/types/enums.py:41` confirms `CanonicalField`
   is ADR-002-locked at 6 members; CDIS / CSTR contact-output is
   NOT in the enum. While the Hertz case CAN be made to validate
   on DISPLACEMENT only (indenter depth δ = a²/R from Hertz),
   the runner itself is ~800-1000 LOC + meshed indenter + meshed
   plate + `*SURFACE TYPE=ELEMENT` + `*CONTACT PAIR INTERACTION`
   + `*SURFACE BEHAVIOR PRESSURE-OVERCLOSURE=EXPONENTIAL` +
   nonlinear `*STATIC NLGEOM` with finicky increment control.
   **Risk profile**: convergence failures eat the slice budget;
   honest pivot precedent from Phase 31 A (contact→heat) and
   Phase 31 C (cylinder-pv→Richardson) says **defer to Phase 33+
   when the runner can have dedicated scope**, not bundle it
   into a 4-slice phase.
2. **`*COUPLED TEMPERATURE-DISPLACEMENT`** — recon at
   `backend/app/services/materials/api.py` confirms the
   `Material` dataclass has NO thermal-expansion coefficient
   `alpha`. Adding it is a Material SSOT schema extension —
   not ADR-002-class but still requires an additive schema bump
   + library.json edits per material + tests. Phase 31 A
   precedent (k=50 W/(m·K) hardcoded in the heat-transfer
   runner with documented k-invariance) does NOT apply here:
   the analytical reference (free thermal expansion ΔL = α·L·ΔT
   or thermal stress σ = -E·α·ΔT in a constrained bar) is
   NOT α-invariant. Deferring α SSOT extension to Phase 33+.
3. **Cylinder-pv BC redesign** — recon at
   `cylinder_pv_runner.py:200`-ish (`# Statically-determinate
   BCs for PURE uniaxial σ_xx (Saint-Venant). Over-constraining
   the x=0 face... creates Poisson lockup → σ_xx reads ~14%
   high`) documents the Phase 19 B Poisson-lockup trap. The
   BC redesign for a refinable mesh requires careful Saint-
   Venant decay zone treatment — a high-risk operation that
   would likely consume more than its single-slice budget.
   **Pivot**: instead of cylinder-pv BC redesign, extend the
   convergence + Richardson pattern to OTHER existing runners
   that already have a tunable mesh parameter
   (`cantilever_runner.py:176` characteristic_length_m default
   0.025; `plate_ss_runner.py:323` characteristic_length_m
   default 0.060; `plate_kirsch_runner.py:193`
   characteristic_length_m default 0.003). Same FEA Dim 5
   ubiquity-axis lift, much lower risk.

### Phase 32 slice breakdown

| Slice | Primary axis lift | Magnitude | Cross-axis |
|---|---|---|---|
| A Convergence ubiquity (3 more cases) | FEA Dim 5 90 → 92 | +2/6 = +0.33 FEA | Dim 4 86 → 87 (incremental) |
| B App-root useAppLayout | UX Dim 3 91 → 93 | +2/6 = +0.33 UX | UI Dim 6 86 → 88 (maintainability) |
| C Tier-2 polish bundle | UX Dim 6 + UX Dim 4 + UI Dim 5 | combined ~+0.5 | Phase 31 honest-gap closures |
| D 3 audits + FINAL + retro + STATE | telemetry | — | — |

Expected composite Δ ≈ 0.33 (FEA) + 0.33 (UX) + (UX +0.2, UI +0.2)
= **+1.0 to +1.6 composite** → projection band 89.5 - 90.5.

**Anti-gaming guard meta:** if any one slice over-delivers by
+2 axis points beyond the rubric anchor, audit it for rubric
drift (signal of inflation, not real progress). Phase 30 / 31
absolute-delta agreement (0.01 / 0.003) indicates rubric v1.0
is calibration-stable; Phase 32 should match or tighten further.

## Slice A — Convergence + Richardson extension to 3 more cases

**Why**: Phase 30 D shipped convergence_study + Richardson
infrastructure for 2 cases (plate-ss-shell + cantilever-modal).
Phase 31 C added Richardson math. **Pattern proven; ubiquity
still partial** — 9 of 11 cases lack convergence_study.json.
Phase 31 FINAL FEA Dim 5 = 90 capped by "still only 2/11 cases
have convergence_study"; lifting to 5/11 hits the 92-anchor
interpolation ("Convergence-study documented for each case" =
99-anchor; partial = mid-band).

**Candidate cases** (each already has tunable mesh param):
1. **cantilever-beam-candidate** — `cantilever_runner.py:176`
   `characteristic_length_m: float = 0.025`. C3D10 quadratic-tet
   under static tip load. Analytical: Euler-Bernoulli
   `δ = FL³/(3EI)`. 3 refinements at cl ∈ {0.020, 0.012, 0.007}
   (geometric ratio ≈ 1.6-1.7 — note non-constant, will flag
   in richardson.notes).
2. **plate-ss-candidate** — `plate_ss_runner.py:323`
   `characteristic_length_m: float = 0.060`. C3D8 solid (NOT
   the S4 shell variant). Analytical: same Timoshenko α=0.00406
   at ν=0.3 series as plate-ss-shell. 3 refinements at cl ∈
   {0.080, 0.060, 0.040} (geometric ratio 1.33-1.5).
3. **plate-kirsch-candidate** — `plate_kirsch_runner.py:193`
   `characteristic_length_m: float = 0.003`. C3D10 stress
   concentration at circular hole. Analytical: σ_max = K·σ_∞ = 3.
   3 refinements at cl ∈ {0.005, 0.003, 0.002} (geometric ratio
   1.5-1.67; ratio direction = `param_is_h` since smaller cl =
   finer mesh).

**LOC budget**: ~50 LOC of orchestrator wrappers per case (the
3 live runs invoke existing runners verbatim) + 3 new
convergence_study.json files (~80 lines each, baked from the
live results). Total ~250 LOC of new code + 3 new artifacts +
~25 lines of new tests pinning the artifacts.

**Anti-gaming guards**:
- A:-1: each artifact's `richardson.extrapolated_value`
  matches `compute_richardson_from_artifact(payload, h_dir)`
  exactly (round-trip pin like Phase 31 C).
- E:-1: when `trend_monotone=false` the artifact records it
  HONESTLY (like Phase 30 D's plate-ss-shell did).

**Honest expectations**:
- Cantilever-static will likely show monotone-decreasing
  residual (smooth bending field, C3D10 quadratic).
- Plate-ss (C3D8) may show similar +1.2% asymptotic bias as
  plate-ss-shell did (same Timoshenko reference; different
  element class). If so → richardson.notes flags it.
- Plate-kirsch convergence is the tightest test — stress
  concentration peaks are mesh-sensitive; expect
  trend_monotone=true with residual approaching ~5% at finest
  mesh (Phase 23 D 8-element-circumference initial reading).

## Slice B — App-root reducer extraction (`useAppLayout`)

**Why**: Phase 31 B extracted state from `ResultMeshPlaybackPanel`
(8 useState + 5 useEffect) into `useViewportLayout`. App.tsx
itself is still 1457 LOC byte-identical from Phase 30 (verified
via `git diff e935c63 a8a1932 -- frontend/src/App.tsx` empty
in Phase 31 UX audit). The reducer-extraction debt is half-
closed; this slice completes it.

**Approach**: mirror Phase 31 B pattern:
1. Audit App.tsx for state surfaces + effect cascades.
   Candidate state to lift (verified existing in App.tsx via
   prior Phase 25 C / 29 C work):
   - `uiMode` + storage adapter
   - `tourDismissedInSession`
   - `selectedTab` (Visual / Narrative / Trust / ...)
   - `caseId` (active case selection)
   - Probably 4-6 more candidates surfaced via the audit step.
2. Create `frontend/src/state/useAppLayout.ts` mirroring
   `useViewportLayout.ts`:
   ```ts
   export function useAppLayout(): { state, actions }
   ```
3. Refactor App.tsx to consume the hook; aim for ~250 LOC
   reduction (Phase 31 B got -104 from panel; App.tsx has
   more surface so more lift possible).
4. Add `Phase32B_use_app_layout.test.tsx` mirroring Phase 31 B's
   test file (~25 tests covering state shape, action contracts,
   effect cleanup, no-stale-closure).

**Target**: App.tsx 1457 → ~1200-1250 LOC.

**Anti-gaming guards**:
- C:-1: ALL existing App.tsx behavioral tests must still pass.
  Hook landing is structural — if a test trips, the change is
  semantically wrong.
- D:-1: hook is opt-in via explicit import; no context / global
  state leakage.
- E:-1: effect cleanup respects unmount (Phase 31 B precedent).

**Honest scope note**: Phase 31 B's `useViewportLayout`
discovered a race condition (first-render persistence effect
beat the toggleCompanion null-check). App.tsx may have similar
ordering subtleties around uiMode storage + tour gating. Plan
to land any discoveries as Phase 32 B retro lessons.

## Slice C — Tier-2 polish bundle

Four micro-affordances, each closing a Phase 31 honest gap:

### C1 — Coord-readout advanced-mode gating
Phase 30 FINAL gap #9 (still unaddressed in Phase 31). Phase 31 UX
audit flagged this debit-of-omission verbatim. ~5 LOC + 1
feature-id entry in `uiMode.ts`.

Current state (`ResultMeshPlaybackPanel.tsx`): CoordReadoutTooltip
renders unconditionally inside primary-viewport-slot when
viewportMode === 'webgl'. Basic-mode novices see the floating
XYZ they didn't pre-Phase 30 C.

Change:
- Add `'coord-readout'` to `ADVANCED_FEATURE_IDS` in
  `frontend/src/uiMode.ts`.
- Wrap the existing render with `shouldShowFeature(uiMode,
  'coord-readout')`.
- Extend `Phase25C_ui_mode_toggle.test.tsx` registry pin.

### C2 — Companion entrance opacity fade
Phase 31 UX audit honest gap #3: "Companion entrance fade NOT
shipped — only flex transition". Full motion treatment adds
a 200ms opacity fade on CompanionViewport's first render
matching the rest of the FM-04a 200ms motion vocabulary.

- New `@keyframes fm04a-companion-fade-in` (0 → 1 opacity over
  200ms ease-out).
- Apply via `POLISH_CLASS_COMPANION_MOUNT` on the outermost
  `data-testid="companion-viewport"` div.
- Honor prefers-reduced-motion: reduce.
- ~6 LOC CSS + 1 className wire + 2 tests (rule present + reduced-
  motion compliance).

### C3 — Compare-cuts basic-mode unlock
Phase 30 FINAL gap #10 + Phase 31 UI honest gap #11. Currently
`'companion-viewport'` is in `ADVANCED_FEATURE_IDS` — basic-mode
reviewers never see the 2-quadrant lift. The companion is
read-only-pickable now (Phase 31 D), no longer a write-conflict
risk. Removing the gate is a single-line change in `uiMode.ts`.

- Remove `'companion-viewport'` from `ADVANCED_FEATURE_IDS`.
- Update `Phase25C_ui_mode_toggle.test.tsx` registry pin.
- **HOWEVER**: there's a tension with **C1** — we're gating
  coord-readout to advanced WHILE un-gating compare-cuts.
  Honest UX rationale: coord-readout is a CONTINUOUS visual
  affordance (always-on when in webgl mode) which is heavy
  on novice cognitive load; compare-cuts is OPT-IN (the
  reviewer must click "Compare cuts" toggle to activate).
  The latter has user-driven entry; the former is uninvited.

### C4 — Richardson p-anomaly cantilever-modal r=2 spike
Phase 31 honest gap #5: cantilever-modal observed p = 0.688
vs C3D10 theoretical p=2, flagged as side-effect of non-
constant refinement ratio (cl=12/8/5 mm → r_12=1.5, r_23=1.6).

Spike: re-run cantilever-modal at cl ∈ {12, 6, 3} mm — clean
r=2 ratio. Verify Richardson p stabilizes near 2 (or document
the actual asymptotic order honestly if it doesn't).

- Run 3 live ccx + gmsh refinements at cl=0.012/0.006/0.003.
- If p stabilizes near 2 → write a NEW
  `cantilever-beam-modal-candidate/convergence_study_r2.json`
  (sibling artifact, schema 1.1.0; documents the cleaner
  ratio supports the theoretical-p claim).
- If p does NOT stabilize → honestly document in NOTES.md why
  (e.g., C3D10 + gmsh-elastic-impulse + finite L/h regime
  changes are the real story).

## Slice D — 3 audit sub-agents + FINAL + retro + STATE

Standard Phase 28-31 pattern:
- 3 parallel sub-agents (UX / FEA / UI) read RUBRIC.md v1.0 +
  the prior phase's audit + this commit chain.
- Each scores 6 sub-axes with file:line evidence per anchor.
- FINAL composite = simple arithmetic mean of 3 sub-composites.
- Retro covers what worked / didn't work / Phase 33 forward look.
- STATE.md gets the Phase 32 stamp prepended.

## Anti-gaming meta-guard (Phase 32 specific)

**FEA Dim 5 is the most-tempting axis to inflate**: with 5
artifacts (after Phase 32 A) the rubric anchor 99 ("For-each-
case + Richardson") gets within ~50% completion. **Do not score
above 92 on Dim 5 without all 11 cases having artifacts** — the
"per case + Richardson" anchor 90 sub-bullet partially landed
(5/11) is correctly interpolated at 91-92, NOT 95.

Cross-check: if Phase 32 A's sub-agent scores FEA Dim 5 >= 93
without the cylinder-pv runner being mesh-tunable yet, audit
the score for inflation.

## What this phase does NOT do (honest forward look)

- **`*CONTACT PAIR`** stays deferred — Phase 31 A NOTES.md
  contact-pair deferral persists. Phase 33+ target with
  dedicated slice scope.
- **`*COUPLED TEMPERATURE-DISPLACEMENT`** stays deferred —
  needs Material SSOT thermal-expansion α field. Phase 33+
  target.
- **`*DYNAMIC, EXPLICIT`** stays deferred — Milestone 4 work.
- **Cylinder-pv BC redesign** stays deferred — Phase 31 C
  rationale unchanged; substituting convergence_study coverage
  for 3 other cases is the lower-risk equivalent.
- **Composite-layup S4** stays deferred — Phase 29 carry.
- **Iso-surface rendering / drag-to-resize / density toggle /
  4-quadrant default / collapsible rails** — Tier 3
  architectural multi-phase items unchanged.
- **Real WebGL E2E via playwright** stays deferred — process
  maturity item; Phase 26-31 carry-over.

## v2.3 disposition

- Phase 32 is **not a charter** (no governance-rule change; no
  >=3 cross-module sharing; all work within bounded scopes:
  backend/app/services/cross_check/ + golden_samples/ +
  frontend/src/state/ + frontend/src/components/ +
  frontend/src/uiMode.ts + frontend/src/App.tsx + .planning/).
- 1 sub-phase = Phase 32 (4 implementation slices + 32 D audit)
  = 1 retro at phase-close.
- counter += 4 (telemetry only).
- No Codex review predicted (no auth / signing / 安全边界 hit).
- Round cap 3: planned to NOT trigger; if a sub-agent flags
  Phase-20-style real defects, round 2 is allowed per v2.3.
- Spike-class assessment: Slice C4 (Richardson p-anomaly clean-
  ratio re-run) may qualify as spike-class if ≤30 LOC + 1 test
  and ships as a sibling artifact with no schema break. Will
  evaluate on landing.

## Hard-constraint commitments

- HF1.7a signed-registry hard-stop: respected.
- HF1.7b `*-candidate` carve-out: respected (cantilever-beam
  + plate-ss + plate-kirsch are all already in `*-candidate`).
- HF1.8 path-guard self-protection: respected.
- tmp_path-only test writes (except golden_samples per HF1.7b).
- v2.3 governance round-cap = 3.
- `confidence: <h|m|l>` on every commit.
- 绝对诚实客观 contract (no rubric reshaping, no score gaming).
- prefers-reduced-motion honored on all new motion (C2).
- Anti-gaming guards at predicate level (A:-1, B:-1, C:-1,
  D:-1/2/3, E:-1) per slice.
- Phase 1-N chain additive only.
- NEVER score above 99 (signed validation territory forbidden).
- NEVER re-score prior phases retroactively.
- NEVER apply weights/transforms to composite (must be simple
  arithmetic mean).
- No push / no PR / no Linear / no Notion writes unless
  explicitly authorized.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 16 consecutive
Tier-2 phases.
