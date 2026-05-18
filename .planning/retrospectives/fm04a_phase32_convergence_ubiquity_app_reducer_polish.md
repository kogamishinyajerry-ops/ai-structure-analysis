# FM-04a · Phase 32 retro · convergence ubiquity + App-root reducer + Tier-2 polish bundle

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-31. 16 consecutive Tier-2 phases.

## Scope

| Slice | What landed | Commit | Tests |
|---|---|---|---|
| 32 blueprint | 4-slice plan; recon documented 3 honest deferrals (`*CONTACT PAIR` ~800-1000 LOC NLGEOM + ADR-002 CanonicalField enum lock; `*COUPLED TEMPERATURE-DISPLACEMENT` Material SSOT α-field extension; cylinder-pv BC redesign would re-create Phase 19 B Poisson lockup); anti-gaming meta-guard introduced — Dim 5 capped AT 92 for partial cohort coverage (NOT above) until 11/11. Projection band 89.5-91.0. | `1808c2f` | — |
| 32 A | Extend convergence_study + Richardson to 3 additional runners (cantilever-static / plate-ss / plate-kirsch). Cohort coverage 2/11 → 5/11 (45%; was 18%). **3 live ccx 2.23 + gmsh runs per artifact**, all `schema_version=1.1.0`. Plate-ss revealed `richardson_extrapolate` failure mode: empirical p = -0.29 (non-physical for converging sequence — successive differences GROWING, not shrinking). **Added p ≤ 0 guard** (`backend/app/services/cross_check/convergence_study.py:309-345`): returns `extrapolated_value=None` + `observed_order_p` preserved for diagnostic visibility + detailed `notes`. NO FABRICATED f_∞ when sequence isn't asymptotic. Plate-kirsch sweep revealed **C3D4 -8.4% asymptotic bias** (f_∞=3.427e6 Pa vs analytical 3.74e6 Pa, p=3.87) — second canonical "asymptotic-bias revelation" finding after Phase 30 D plate-ss-shell S4+Mindlin +1.2%. Cantilever-static p=1.48, residual=+0.11%. Same Phase 30 D cl-floor gotcha: gmsh .geo Points fix the mesh-size floor; first plate-ss sweep at cl=80/60/45 mm produced identical meshes for cl≥60, re-ran at 60/40/25 to refine *downward* from the floor. | `cda554d` | 35 backend pins |
| 32 B | `useAppUiMode.ts` (104 LOC NEW) App-root reducer hook mirroring Phase 31 B's `useViewportLayout` pattern at the appUiMode + appTourDismissedInSession cluster. PARTIAL closure of Phase 31 honest gap #7 — App.tsx LOC byte-identical at 1457 (17+/17- swap NET ZERO). Honest acknowledgment: the blueprint's "1457 → 1200-1250 LOC" projection was over-optimistic; ~36 state-related surfaces remain inline in App.tsx and each needs a dedicated Phase 33+ slice for safe extraction. The smallest cohesive cluster was extracted — additive scope, not the full reducer ambition. Test failure caught: initial test used `'fm04a.uiMode.v1'` localStorage key; corrected to `'fm04a.ui.mode.v1'` per `UI_MODE_LS_KEY` constant at `uiMode.ts:43`. | `682e8f6` | 14 frontend |
| 32 C | Tier-2 polish bundle (4 affordances): (1) **coord-readout advanced-mode gating** — `'coord-readout'` added to `ADVANCED_FEATURE_IDS`; 30Hz floating XYZ tooltip now wrapped in `shouldShowFeature(uiMode, 'coord-readout')` (closes Phase 30 FINAL gap #9 + Phase 31 UX honest gap #2); (2) **companion entrance opacity fade** — `POLISH_CLASS_COMPANION_MOUNT` class + `@keyframes fm04a-companion-mount-fade-in` at 200ms ease-out; opacity-only (no transform) for SR-safer motion; prefers-reduced-motion: reduce honored (7th surface in FM-04a motion vocabulary; closes Phase 31 UX honest gap #3); (3) **Compare-cuts basic-mode unlock** — `'companion-viewport'` REMOVED from `ADVANCED_FEATURE_IDS` (registry swap, count held at 5); `showCompanionViewportToggle = true` unconditional; Hyperworks/Abaqus parity for ALL reviewers (closes Phase 30 FINAL gap #10 + Phase 31 UI honest gap #11; Phase 31 D's origin-stamping wrapper removed the write-conflict risk that originally motivated the gate); (4) **cantilever-modal clean r=2 sibling artifact** — `convergence_study_r2.json` (live ccx + gmsh at cl=12/6/3 mm clean r=2). **Honest finding**: even with clean r the empirical p stabilizes near 1.33 (Phase 31 C non-constant ratio was a noise source — lifted from 0.69 to 1.33 — but NOT the dominant source; theoretical C3D10 modal p=2 still unreached). Sibling preserves Phase 30 D canonical record. **3 structural-not-behavioral pins updated** (Phase 25 C registry list; Phase 30 B 'HIDDEN basic' inverted to 'VISIBLE basic'; Phase 30 B registry pin) — additive scope, NOT regression, each documented in commit body. Test failure caught: keyframe regex `/@keyframes...{([^}]+)}/` truncated on nested {} blocks; fixed with `indexOf` + slice approach. | `ee11aca` | 21 frontend |
| 32 D | 3 sub-agent audits (UX 92.7 / FEA 86.33 / UI 90.0); FINAL synthesis composite **89.68/100**; this retro; STATE refresh | (this commit) | — |

**Total: 70 new tests** (35 backend + 35 frontend across 32 A/B/C). All
prior phases' tests still pass; 3 structural pins documented as
tracking the explicit registry swap (NOT behavioral regression).

## Composite trajectory (honest)

| Phase | Honest composite | Per-phase Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 26 | 74.7 | +2.5 (honest re-baseline event) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| 29 | 84.23 | +4.63 |
| 30 | 87.16 | +2.93 |
| 31 | 89.01 | +1.85 |
| **32** | **89.68** | **+0.67** |

**Phase 32 is the seventh inside-band landing in a row**. Cumulative
lift since Phase 26 honest re-baseline = **+14.98 over 6 phases**
(89.68 - 74.7), averaging **+2.50/phase**. Phase 32 is the smallest
per-phase Δ since Phase 28 (+1.1) — the **decelerating trajectory**
is exactly what the rubric anchors predict: easy single-axis wins
are increasingly behind us; remaining lifts are Tier-3 architectural
multi-phase items at higher implementation cost. UI carried the
largest single-axis lift (+1.0); UX and FEA each added +0.5.

## What worked

### Anti-gaming meta-guard worked exactly as designed
- Phase 32 blueprint introduced a Dim-5-specific meta-guard: cohort
  coverage 2/11 → 5/11 LANDS AT the 92 cap, not above. Sub-agent
  FEA auditor independently scored Dim 5 at **92** — agreement
  with the pre-declared cap.
- The guard prevented the easy Phase-30-D-style score inflation
  trap where "extending convergence to N more cases" could be
  scored as "Dim 5 90 → 95" by an under-disciplined auditor. The
  meta-guard pre-declares the ceiling so 92 is the honest answer.

### Three documented honest pivots in three phases (pattern matures further)
- Phase 30 D: cylinder-pv → plate-ss-shell (extend in-tree)
- Phase 31 A: `*CONTACT PAIR` → `*HEAT TRANSFER` (substitute solver kind)
- Phase 31 C: cylinder-pv BC redesign → Richardson post-processing
- **Phase 32 A: `*CONTACT PAIR` → convergence_study ubiquity** (extend pattern to existing runners)
- **Phase 32 C C4: theoretical p=2 confirmation → honest "p stabilized at 1.33"** finding
- The pattern has 5 examples now. **Each pivot preserved the
  original deferral target in-tree** (32 A's blueprint NOTES + 32
  C C4's preserved canonical convergence_study.json + sibling
  convergence_study_r2.json). FEA Dim 3 anchored at 96.

### Rubric v1.0 calibration stability (4 phases running)
- Phase 29 D pinning → Phase 30 (0.01 absolute/delta agreement)
  → Phase 31 (0.003) → **Phase 32 (0.003)**.
- Sub-agent FEA absolute = 86.33; UX absolute = 92.7; UI absolute
  = 90.0. Delta-from-Phase-31 method: 89.01 + (0.5+0.5+1.0)/3 =
  89.677. Both methods agree to 0.003.
- **Four independent sub-agent instances across four phases** are
  scoring within ±2 points of the projected band. The v1.0 anchors
  with concrete file:line examples continue doing their calibration
  job. No anchor inflation observed.

### Asymptotic-bias revelation pattern emerges as canonical
- Phase 30 D: plate-ss-shell S4+Mindlin +1.2% asymptotic residual
- Phase 32 A: plate-kirsch C3D4 -8.4% asymptotic residual
- Two cases now ship "Richardson reveals a property the single-mesh
  residual cannot show" — the rubric Dim 5 anchor 90 use case
  verbatim. This is **not a bug-find**, it's an honest property
  of the element formulation under refinement. FEA Dim 3 anchored
  with two canonical examples.

### p ≤ 0 guard prevents NO-CONFIDENCE fabrication
- Without the guard, plate-ss would have shipped a Richardson
  estimate of f_∞ = +1.6e-04 m extrapolated *20% off* analytical —
  a confidently-wrong number propagated to anyone reading the
  artifact. With the guard, the artifact ships
  `extrapolated_value=null` + diagnostic `notes` explaining the
  non-physical p. **The system declares "I cannot extrapolate
  here" instead of fabricating.** FEA Dim 3 anchor 90 / 95 sub-bullet
  reinforced.

### Spike-class did NOT activate (correctly)
- All 4 implementation slices exceeded the ≤30-LOC + 1-test
  spike-class bound (32 A ~250 LOC orchestration + 35 tests + 3
  artifacts, 32 B 104 LOC + 14 tests, 32 C ~80 LOC across 4 files
  + 21 tests + 1 sibling artifact). All 4 are correctly full
  sub-DEC scope per v2.3 round-1 loosen.

## What didn't work / honest

### App.tsx 1457 LOC unchanged (reducer debt 90% open)
- The blueprint projected "1457 → 1200-1250 LOC" after `useAppUiMode`
  extraction. Reality: 17+ / 17- swap = NET ZERO. The smallest
  cohesive cluster (appUiMode + appTourDismissedInSession) was
  extracted; ~36 surrounding state-related surfaces remain inline.
- **Honest acknowledgment**: full App.tsx extraction is multi-phase
  work (state is coupled throughout: setup, lifecycle, error
  surfaces, viewport, advisor, cohort, persistence). Each cluster
  needs a dedicated Phase 33+ slice. UX Dim 3 capped at ~93 until
  meaningfully decomposed.
- The blueprint's projection was over-optimistic; the audit
  scoring honestly reflected this (UX Dim 3 91 → 92 = +1, not
  +2 to +3).

### Richardson p still not at theoretical 2 even with clean r=2
- Phase 32 C C4 confirmed non-constant ratio was a noise source
  but NOT the dominant source. Even with clean r=2 the empirical
  p stays around 1.33. Three Richardson runs now contradict the
  theoretical predictions:
  - cantilever-static: p = 1.48 vs C3D4 quasi-linear theoretical 2
  - cantilever-modal: p = 1.33 vs C3D10 modal theoretical 2
  - plate-kirsch: p = 3.87 (super-convergence; analytical-reference
    is a stress-concentration approximation, not exact)
  - plate-ss: p = -0.29 FAILED
- Phase 33+ investigation: regime change (h crossing mesh-quality
  threshold where element distortion stops dominating) vs element-
  order limit (C3D10 quadratic should give p=2 in pure bending,
  but cantilever-modal first-mode has bending dominant only
  asymptotically) vs analytical-reference noise (Kirsch K=3.74
  is exact only for infinite plate; finite-plate correction
  affects measured residual).

### 3 structural test pin updates
- Phase 25 C registry list; Phase 30 B 'toggle HIDDEN basic'
  inverted to 'toggle VISIBLE basic'; Phase 30 B registry pin
  block — each updated to track the explicit registry swap
  (`'companion-viewport'` → `'coord-readout'`).
- These are not regressions; they are SSOT-tracking updates. The
  Phase 32 C commit body documents each one as "additive scope,
  NOT behavioral regression." But the **honest cost**: the
  D:-1 anti-gaming guard (Phase 1-N additive) is *almost* purely
  additive, with a documented carve-out when the registry
  itself changes. The pattern is now established (Phase 30 C
  color-pin update during 31 D was the first instance); a future
  Phase 33+ guard could pin the registry registry (the test
  that pins what the registry is) one level up.

### Real WebGL E2E still future (Phase 26-32 carry-over)
- Persistent. Same Phase 31 D limitation: jsdom can't fire
  `webglcontextlost`. Phase 32 C's companion entrance fade is
  similarly pinned via CSS class assertions + slice-and-match
  on the keyframe definition, NOT live animation event dispatch.
  playwright integration would cover both; remains future.

### Cohort coverage still partial (5/11; 6 cases lack convergence_study)
- cylinder-pv variants (3) Saint-Venant 1-element coupon; euler-
  column tunable mesh open; cantilever-modal-l50 + cantilever-
  buckle + cantilever-dynamic + heat-transfer-1d each have
  case-specific reasons. Some cases have no tunable mesh param
  in the runner; others are in deferred-runner territory
  (e.g. heat-transfer-1d is hand-rolled 10×2×2 hex without gmsh).
- FEA Dim 5 capped at 92 until full coverage; the meta-guard
  pre-declared this exact cap before the audit ran.

## Phase 33 forward look

See `.planning/audits/phase32_FINAL.md` "Phase 33 priority
recommendations" for the consolidated list. Top 3:

1. **`*CONTACT PAIR` Hertz contact case** — closes the
   Phase 31 A + Phase 32 blueprint + Phase 32 FEA gap #1 deferral.
   FEA Dim 1 80 → 85 = +0.83 composite. **HIGHEST single-axis
   FEA lift on the table**. Requires ~800-1000 LOC NLGEOM, contact
   pair reader extension, and verification against Hertz analytical.
2. **`*COUPLED TEMPERATURE-DISPLACEMENT`** with Material SSOT α-field
   schema extension — closes Phase 32 FEA gap #2. ~+0.5 composite.
3. **App-root deeper extraction (case-selection or comparison
   cluster)** — closes more of Phase 31 honest gap #7. UX Dim 3
   92 → ~93. ~+0.3 composite.

**Phase 33 projection band: 90.0 - 91.0** if 2 Tier-1 items ship;
89.7 - 90.5 if 1 Tier-1 + 1 Tier-2.

The 99 target remains intentionally unreached. Per RUBRIC.md the
ceiling is 99; reaching it requires items the honest contract
explicitly forbids (signed validation, independent benchmark
agreement). Phase 32's 89.68 represents **engineering-honest
craft at the Tier-1/Tier-2 boundary** — seven inside-band
landings in a row, three structural lifts (Richardson ubiquity +
asymptotic-bias revelation pattern + clean-r=2 honest finding),
one App-root reducer hook (partial), and three pieces of
distributed polish (coord-readout gating + companion fade +
Compare-cuts unlock) delivered without rubric reshaping or score
gaming.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 16 consecutive
Tier-2 phases.
