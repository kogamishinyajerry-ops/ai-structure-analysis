# FM-04a Phase 32 — FEA Audit · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Cites RUBRIC.md v1.0 anchors verbatim. 绝对诚
> 实客观 contract carried verbatim from Phase 18-31.

## Baseline anchor

Phase 31 FEA composite (per `.planning/audits/phase31_fea_audit.md`
line 182) was **85.83/100** under rubric v1.0 — sub-axis vector
{80, 89, 95, 86, 90, 75}. RUBRIC.md untouched at v1.0 (no v1.1
bump triggered in Phase 32). Phase 31 numbers are NOT re-scored
retroactively (additive D:-1).

What Phase 32 shipped against FEA dimensions (commits `1808c2f`
blueprint + `cda554d` Phase 32 A + `ee11aca` Phase 32 C; Phase 32
B `682e8f6` is frontend-only `useAppUiMode` and contributes zero
to FEA axes):

1. **Phase 32 A** — ubiquity lift on existing
   `convergence_study` + Richardson infrastructure to **3 more
   cases**: cantilever-beam (C3D10 static), plate-simply-supported
   (C3D10 plate), plate-with-hole (C3D4 Kirsch). Cohort coverage
   2/11 → **5/11 (45%)**. New `p ≤ 0` guard in
   `richardson_extrapolate` (~25 LOC) discovered by the plate-ss
   sweep, pinned by 3 tests.
2. **Phase 32 C C4** — cantilever-modal CLEAN r=2 spike SIBLING
   artifact (`convergence_study_r2.json`); honest finding that
   clean ratio lifts p 0.69 → 1.33, still not reaching theoretical
   2 — non-constant ratio NOT the dominant noise source.
3. **Blueprint deferrals (3)** — `*CONTACT PAIR`,
   `*COUPLED TEMP-DISP`, cylinder-pv BC redesign all explicitly
   deferred to Phase 33+ with documented schema-work-exceeds-
   single-slice rationale (commit `1808c2f` body lines re. recon).

## Sub-axes

### 1. Element-type breadth — **80/100**

- **Evidence:** No new element class shipped. Phase 32 A's 3
  cases reuse C3D10 (cantilever-beam, plate-ss) and C3D4
  (plate-kirsch) — verified by
  `golden_samples/cantilever-beam-candidate/convergence_study.json`
  `notes` ("C3D10 quadratic-tet mesh via gmsh"),
  `golden_samples/plate-simply-supported-candidate/convergence_study.json`
  `notes` ("C3D10 quadratic-tet mesh"),
  `golden_samples/plate-with-hole-candidate/convergence_study.json`
  `notes` ("C3D4 linear-tet mesh"). Element-class roster
  unchanged: {C3D4, C3D8, C3D10, B31, S4} — 5 classes.
- **Anchor match:** RUBRIC.md Dim 1 row "**80** — Shell elements
  (S4) validated; first non-solid non-beam element class" (Phase
  29 A landed verbatim, Phase 30-31 held). Phase 32 blueprint
  (`1808c2f` body) explicitly defers `*CONTACT PAIR` (Dim 1 → 90
  sub-bullet) to Phase 33+ — recon documented this is ~800-1000
  LOC runner + convergence-finicky NLGEOM exceeding single-slice.
- **Interpolation:** held flat at **80**. Phase 32 explicitly
  scoped not to touch Dim 1 — this is honest scope, not a
  regression.

### 2. Solver-kind coverage — **89/100**

- **Evidence:** Phase 32 ships zero new `*STEP` kinds. Cohort
  solver-kind roster from Phase 31 (`*STATIC` × 5, `*BUCKLE` × 2,
  `*FREQUENCY` × 2, `*DYNAMIC` × 1, `*HEAT TRANSFER` × 1 = 5
  kinds) carries unchanged. `*COUPLED TEMP-DISP` deferred to
  Phase 33+ per blueprint (`1808c2f` body, "Material dataclass
  has no alpha field; schema extension needed").
- **Anchor match:** RUBRIC.md Dim 2 anchors {**85** = + *DYNAMIC*
  (Phase 30), **92** = + *DYNAMIC EXPLICIT*, **99** = + heat /
  visco / coupled-temp-disp}. Phase 31 landed 1/3 of the 99
  span (heat).
- **Interpolation:** held flat at **89**. Phase 32 was
  explicitly scoped not to touch Dim 2 — honest hold.

### 3. Honest-scope discipline — **96/100**

- **Evidence (Phase 32 A plate-ss Richardson FAILURE recorded
  honestly):**
  `golden_samples/plate-simply-supported-candidate/convergence_study.json`
  lines 36-41 record `extrapolated_value: null` and
  `observed_order_p: -0.2927` with the verbatim note
  "Richardson failed: observed order p = -0.2927 ≤ 0
  (non-physical for a converging sequence; the triple is not yet
  in the asymptotic regime — successive differences |f_i -
  f_{i+1}| are growing, not shrinking, as the mesh refines).
  Reported triple is the data; no extrapolation attempted." **No
  fabricated f_∞.** This is the canonical "fail in-tree with
  documented rejection" pattern.
- **Evidence (new `p ≤ 0` guard pinned in code):**
  `backend/app/services/cross_check/convergence_study.py:309-345`
  (~36 LOC NEW) implements the `if p <= 0.0:` short-circuit that
  returns `extrapolated_value=None` + diagnostic `observed_order_p`
  + 5-line in-code rationale comment explaining why the closed-
  form formula is unphysical. Pinned by **3 new tests** in
  `backend/tests/test_phase32a_convergence_ubiquity.py:347-390`
  (`test_negative_p_returns_none`, `test_p_at_zero_returns_none`,
  `test_positive_p_still_works` — regression guard for both
  failure path AND Phase 31 C textbook p=1 sanity).
- **Evidence (plate-kirsch C3D4 BIAS REVEAL):**
  `plate-with-hole-candidate/convergence_study.json` Richardson
  delivers `p = 3.87`, `extrapolated_residual_pct = -8.37%`.
  Analogous to Phase 30 D's plate-ss-shell S4+Mindlin +1.2%
  finding: convergence study reveals an asymptotic property
  (C3D4 linear-tet stress-concentration UNDERPREDICTION bias)
  the single-mesh residual cannot show. Honest scope: the case
  remains PASS at all 3 meshes per its 20% tolerance pin, but
  Richardson tells the truth — refining mesh further will not
  close the ~8% gap, that's a linear-tet limitation.
- **Evidence (Phase 32 C C4 sibling artifact, NOT replacement):**
  `cantilever-beam-modal-candidate/convergence_study_r2.json`
  (NEW) coexists with the original `convergence_study.json`. Same
  "preserve the historical record" pattern as Phase 31 A's
  contact→heat deferral. Notes line 5 explicitly: "SIBLING to
  convergence_study.json — does NOT replace the original Phase
  30 D record." Honest finding `p=1.33` documented (non-constant
  ratio was ~0.65 of p but NOT dominant; still doesn't reach
  theoretical 2).
- **Evidence (3 blueprint deferrals documented with named root
  causes):** commit `1808c2f` body documents Phase 33+ deferrals
  for `*CONTACT PAIR` (ADR-002 locked + ~800-1000 LOC NLGEOM),
  `*COUPLED TEMP-DISP` (Material dataclass alpha-field schema
  gap; Phase 31 A k-invariance precedent does NOT apply since
  thermal-stress σ=-E·α·ΔT is not α-invariant), and cylinder-pv
  BC redesign (Phase 19 B Poisson lockup avoidance unchanged).
  All three named with the actual blocker, not vague "future
  work".
- **Anchor match:** RUBRIC.md Dim 3 row "**95** — Honest-scope
  NOTES.md documents root cause + lesson learned". Phase 32
  demonstrates the discipline at FOUR distinct surfaces in one
  phase:
  1. plate-ss Richardson FAILURE recorded with null f_∞ + notes
     (NOT fabricated)
  2. plate-kirsch C3D4 asymptotic bias REVEALED via Richardson
     (analogous to Phase 30 D S4+Mindlin)
  3. cantilever-modal r=2 spike honest finding (non-constant
     ratio was a contributor, NOT the root cause)
  4. 3 documented deferrals with named root causes (contact /
     coupled / cylinder-pv)
  PLUS code-level enforcement: the `p ≤ 0` guard is now
  pinned by regression test, so future loosening trips it. This
  is anchor 95 verbatim PLUS a step toward anchor 99's
  "failed-attempt corpus indexed" sub-bullet: the guard + 3 tests
  + the plate-ss artifact constitute the first piece of an
  indexed "what doesn't work" catalog (failure mode = "triple
  not yet in asymptotic regime"; canonical example pinned).
- **Interpolation:** **+1** over Phase 31's 95 → **96**. Anchor
  99 (cross-case indexed "what-doesn't-work" corpus) is now
  partially landed — one canonical failure mode is reproducibly
  pinned. Considered +2 but reserved final anchor jump for when
  a `.planning/failed_attempts/` index across multiple failure
  modes exists. **NEVER score above 99**: held at 96.

### 4. Validated-cohort size — **86/100**

- **Evidence:** No new case added. Registry
  `backend/app/services/reporting/_claim_tier.py` still pins 11
  `*-candidate` entries (verified by grep:
  cylinder-pv / rod-wave-impact / swing-arm-fatigue /
  ballistic-plate / leak-shell / cantilever-beam / plate-with-
  hole / euler-column / plate-simply-supported / cantilever-
  beam-modal / cantilever-beam-modal-l50 / cantilever-buckle /
  plate-ss-shell / cantilever-dynamic / heat-transfer-1d — 15
  registry entries, of which 11 are validated PASS). Phase 29 D
  tolerance pin test `test_phase29d_registry_tolerance_pin.py`
  unchanged at 11 entries.
- **Anchor span:** RUBRIC.md Dim 4 anchors {**82** = 9 cases inc.
  first non-solid, **86** = current interpolation at 11 cases,
  **88** = 12+ cases covering 3+ element classes + 3+ solver
  kinds, **99** = 25+ cases}.
- **Interpolation:** held flat at **86**. Phase 32 was scoped
  not to touch Dim 4 — honest hold.

### 5. Residual budget + tolerance discipline — **92/100**

- **Evidence (cohort coverage 2/11 → 5/11):**
  `backend/tests/test_phase32a_convergence_ubiquity.py:398-433`
  `TestConvergenceCohortCoverage` pins exactly 5 artifacts:
  plate-ss-shell-candidate + cantilever-beam-modal-candidate
  (Phase 30 D) + cantilever-beam-candidate + plate-simply-
  supported-candidate + plate-with-hole-candidate (Phase 32 A).
  All 5 carry `schema_version: 1.1.0` per
  `test_all_artifacts_schema_v110`. Coverage 45% (5/11).
- **Evidence (Richardson tightness on new cases):**
  - **cantilever-beam-candidate**: residuals -0.097% → -0.016%
    → +0.034%, Richardson `p=1.483`, `extrapolated_residual_pct
    = +0.112%`. TIGHTEST cohort (C3D10 + slender Euler-Bernoulli
    geometry).
  - **plate-with-hole-candidate**: residuals -19.61% → -10.71%
    → -8.86%, Richardson `p=3.87`,
    `extrapolated_residual_pct = -8.37%`. Asymptotic gap reveals
    C3D4 linear-tet stress-concentration bias.
  - **plate-simply-supported-candidate**: residuals -5.79% →
    -3.61% → -1.11%, Richardson FAILS HONESTLY
    (`extrapolated_value: null`, p = -0.29 not yet asymptotic).
- **Evidence (`p ≤ 0` guard = code hardening of Dim 5 honesty):**
  `convergence_study.py:309-345` short-circuits unphysical
  extrapolation, ensuring artifacts never carry a fabricated
  f_∞ when the triple is non-asymptotic. Pinned by 3 tests
  (lines 347-390).
- **Anchor span:** RUBRIC.md Dim 5 anchors {**80** = per-case
  tolerance pin + residuals ≤ 5% for most (Phase 29 D),
  **90** = + convergence-study FOR EACH CASE + Richardson
  extrapolation residual (verbatim 2 sub-bullets;
  Phase 31 C landed the Richardson half), **99** = + independent
  third-party verification + UQ}.
- **Interpolation:** Phase 31 sat at 90 with the Richardson
  sub-bullet verbatim landed but the "for each case" sub-bullet
  partial (2/11 = 18%). Phase 32 lifts coverage to 45% (5/11).
  Linear interpolation between Phase 31's 90 (Richardson done +
  18% case coverage) and a hypothetical full 95 (Richardson +
  100% case coverage): 90 + (5/11 - 2/11) / (11/11 - 2/11) × 5
  = 90 + (3/9) × 5 ≈ **91.67**. Rounded honestly to **92**.
  **Anti-gaming meta-guard enforced** (per Phase 32 blueprint
  `1808c2f` body: "do not score Dim 5 above 92 without all 11
  cases having artifacts"): score lands AT the guard, not
  above. Considered the new `p ≤ 0` guard a separate sub-bullet
  warranting +1 nudge, but the guard is a SAFETY mechanism
  (anti-fabrication), not a NEW capability — its honest home is
  Dim 3 (already lifted +1 to 96), not double-counted on Dim 5.

### 6. Ballistic Tier-2 readiness — **75/100**

- **Evidence:** Phase 32 ships zero `*DYNAMIC` changes — Phase
  30 A's `cantilever-dynamic-candidate` still the only dynamic
  case. `*DYNAMIC, EXPLICIT` still Milestone 4 future per Phase
  32 blueprint deferral list (`1808c2f` body: "**`*DYNAMIC,
  EXPLICIT`** stays deferred — Milestone 4 work").
- **Anchor match:** RUBRIC.md Dim 6 row "**75** — + First
  `*DYNAMIC` validated case (transient, implicit). **Future**" —
  Phase 30's landing carried forward through Phase 31 → 32.
- **Interpolation:** held flat at **75**. Phase 32 explicitly
  scoped not to touch Dim 6 — honest scope, not a regression.

## Composite FEA score: **(80 + 89 + 96 + 86 + 92 + 75) / 6 = 86.33/100**

Arithmetic mean of 6 sub-axes (no weights). Three decimals:
86.333; public-facing **86.3**.

## Phase-32 lift over Phase 31 FEA (85.83): **+0.50**

The composite jumped 85.83 → 86.33 — a +0.50-point lift,
**smaller than** Phase 31's +1.66 and Phase 30's +6.67. This is
the smallest FEA lift since Phase 26 honest re-baseline. **The
deceleration is honest and expected** — Phase 32 explicitly
chose the lower-FEA-ambition substitution path (ubiquity over
new element/solver/contact axes) after recon surfaced that
`*CONTACT PAIR` / `*COUPLED TEMP-DISP` / cylinder-pv BC redesign
all exceed single-slice scope. The blueprint projection band
89.5-90.5 composite (Phase 31 89.01 + ~+1.0) is consistent with
this FEA +0.5 contribution (the other +0.5-1.0 lives in UX/UI
slices B + C).

| Sub-axis | Phase 31 | Phase 32 | Δ | Why |
|---|---|---|---|---|
| 1. Element-type breadth | 80 | 80 | 0 | No new class; contact-pair stays deferred (recon documented in blueprint) |
| 2. Solver-kind coverage | 89 | 89 | 0 | No new *STEP kind; coupled-temp-disp stays deferred (Material α schema gap documented) |
| 3. Honest-scope discipline | 95 | **96** | **+1** | Three new honest findings landed (plate-ss Richardson failure + p≤0 guard pinned; plate-kirsch C3D4 -8.4% asymptotic bias; cantilever-modal r=2 sibling); first canonical failure mode reproducibly pinned (step toward anchor 99 "indexed corpus") |
| 4. Validated-cohort size | 86 | 86 | 0 | Still 11 cases; cohort count unchanged |
| 5. Residual budget + tolerance | 90 | **92** | **+2** | Coverage 2/11 → 5/11 (anchor 90 "for each case" sub-bullet half-landed; linear interp 90 + (3/9)×5 ≈ 91.7); anti-gaming meta-guard ("not above 92 without 11/11") enforced |
| 6. Ballistic Tier-2 readiness | 75 | 75 | 0 | Phase 32 explicitly out of scope for Dim 6 |

The lift composition is honest and rubric-aligned: Dim 5 (+2)
and Dim 3 (+1) carry the entire +3 axis-sum (÷6 = +0.5
composite). Dim 1 / 2 / 4 / 6 honestly held — and the
blueprint deferrals for each were documented with named root
causes BEFORE the score sub-agent ran. This is the
"absolute-honest" anti-inflation contract.

## Phase 32 honest gaps (Phase 33 forward look)

1. **`*CONTACT PAIR` case still future** (Dim 1 hard-capped at
   80). Phase 32 blueprint (`1808c2f` body) names the actual
   cost: ~800-1000 LOC runner + convergence-finicky
   `*STATIC, NLGEOM` Hertz validation. Phase 33+ dedicated-slice
   target. Composite lift available: 80 → 85 anchor = ~+0.8.

2. **`*COUPLED TEMPERATURE-DISPLACEMENT` still future** (Dim 2
   ceiling at 89). Material dataclass needs thermal-expansion α
   field; Phase 31 A k-invariance precedent does NOT apply
   because σ_thermal = -E·α·ΔT is not α-invariant. Phase 33+
   target. Composite lift available: 89 → 92 anchor = ~+0.5.

3. **Cylinder-pv runner BC redesign still deferred** (Dim 5
   ceiling at ~93). Phase 31 C rationale unchanged (Phase 19 B
   Poisson lockup avoidance). After this, Phase 32 A's coverage
   pattern can extend to 6 more cases.

4. **Cohort coverage still 5/11 (45%)** (Dim 5 ceiling at 92
   per anti-gaming meta-guard). Remaining 6 = cylinder-pv (3
   variants) + euler-column + cantilever-modal-l50 +
   cantilever-buckle + cantilever-dynamic + heat-transfer-1d.
   Each lacks tunable-mesh-param infrastructure OR sits in
   deferred-runner territory. Full FOR-EACH-CASE coverage would
   push Dim 5 toward 95.

5. **Cantilever-modal r=2 spike NOT closed**: clean r=2 lifted
   p 0.69 → 1.33 but still doesn't reach C3D10 theoretical
   p=2. Hypothesis (per `convergence_study_r2.json` notes):
   regime change or element-order limit at fine h. Phase 33+
   spike-class investigation.

6. **`*DYNAMIC, EXPLICIT` still future** (Dim 6 floored at 75).
   Unchanged from Phase 30/31 honest gap. Milestone 4 item.

7. **Failed-attempt corpus indexing** — Phase 32 landed the
   first canonical failure mode (Richardson `p ≤ 0` non-
   asymptotic regime pinned by 3 tests + plate-ss artifact);
   anchor 99 would require an indexed
   `.planning/failed_attempts/` catalog spanning multiple
   failure modes (contact-pair-not-yet, coupled-temp-disp-α-
   gap, cylinder-pv-BC-redesign, S4+Mindlin-bias, C3D4-stress-
   concentration-bias, etc.). Dim 3 96 → 99 lift available.

8. **Plate-kirsch C3D4 bias quantified but not mitigated**:
   Richardson reveals ~-8.4% asymptotic bias is a LINEAR-TET
   limitation. Phase 33+ candidate: replicate at C3D10
   quadratic-tet to confirm the bias is element-order-bound
   (would also widen cohort element-class × case matrix
   coverage).

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. 绝对诚实客观 across 16 consecutive Tier-2
phases.
