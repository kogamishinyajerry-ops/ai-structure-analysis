# FM-04a Phase 28 — FEA Audit

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Brutally honest, no inflation.

## Baseline anchor

Phase 27 retro § Honest scope misses #1 records FEA Dim 1 = **65/100**
held back by missing shell (S4) support. Phase 27 composite was
78.5/100; FEA sub-axis was the laggard. Phase 28 A adds **+1
validated case + a new BC type (k=2.0 cantilever) on the existing
B31 runner**, NOT a new element class and NOT a new solver kind.
Expected honest lift = +2 to +4 on FEA composite.

## Dimensions

### 1. Validated case count + element-type breadth — **66/100**

- **Evidence (count):** `golden_samples/*/cross_check_verdict.yaml`
  scan returns **8** PASS verdicts: cylinder-pv-candidate,
  cantilever-beam-candidate, plate-with-hole-candidate,
  euler-column-candidate, plate-simply-supported-candidate,
  cantilever-beam-modal-candidate, cantilever-beam-modal-l50-candidate,
  cantilever-buckle-candidate (Phase 28 A,
  `_claim_tier.py:138-150`; `test_phase28a_cantilever_buckle.py:131`
  hard-pins `len(validated) == 8`).
- **Evidence (element types):** {C3D8 (cylinder-pv,
  `cylinder_pv_runner.py:135`), C3D4 (cantilever-beam,
  `cantilever_runner.py:15`), C3D10 (plate-with-hole, plate-ss,
  cantilever-modal × 2; `plate_ss_runner.py:247`,
  `cantilever_modal_runner.py:171`), B31 (euler-column,
  cantilever-buckle; `buckling_b31_runner.py:150`)}. **4 element
  classes total** — same as Phase 27.
- **Gap:** SHELL (S4 / S3) **still absent**. AXISYMMETRIC (CAX) absent.
  CONTACT pairs absent. C3D8I, C3D20 absent. The Phase 27 punchlist
  #1 (shell + CalculiX shell-output reader plumbing) is **unmoved**.
  The 8th case reuses the existing B31 runner verbatim
  (`test_phase28a_cantilever_buckle.py:8` "NO new runner, NO new
  element type").
- **Score discipline:** Phase 27 retro held this dimension at
  **65/100** specifically because of the shell gap. Phase 28 A's
  count lift (7→8) earns +1 point. The hard cap "do not score
  above 75 while shells are absent" applies; 66/100 reflects "1
  more case, same element library, shell gap intact". Counting
  Phase 28 A as a "new BC type lift" would double-count what is
  already captured in Dim 3.

### 2. Solver coverage — **55/100**

- **Evidence:** Three CalculiX modes covered: linear static
  (cylinder-pv, cantilever-beam, plate-with-hole, plate-ss),
  `*BUCKLE` (euler-column k=1, cantilever-buckle k=2),
  `*FREQUENCY` (cantilever-modal × 2 at L/h=25 and L/h=50).
- **Gap:** No CONTACT (`*CONTACT PAIR` / surface-to-surface), no
  LARGE-DEFORMATION (`*NLGEOM`), no `*DYNAMIC explicit` (ballistic),
  no `*HEAT TRANSFER`, no `*VISCO`, no `*COUPLED TEMPERATURE-
  DISPLACEMENT`. The product is a **ballistic** FEA review
  workbench; the absence of explicit-dynamic validated cases is a
  structural Tier-2 gap. Phase 28 added zero new solver kinds
  (Phase 28 A explicitly is `*BUCKLE` again, NOTES.md "This case
  does NOT lift FEA Dim 4").
- **Score:** 3 of ~8 plausible modes ≈ 37.5%, but linear-static is
  the heaviest weight (4/8 cases live there) so we credit
  breadth-of-mode at 55/100. Unchanged from Phase 27.

### 3. Honest-scope discipline — **92/100**

- **Evidence (preservation of failed attempt):**
  `buckling_runner.py:417-423` — the C3D8 hex runner raises
  `NotImplementedError` for any non-`pinned-pinned` end_condition,
  with a verbatim docstring (lines 404-416) recording the **256%
  residual** failure (3.6× analytical) due to C3D8 shear locking
  on a fully-clamped base. `_write_cantilever_buckle_inp`
  (lines 245-352) is preserved as **documented honest-scope
  evidence**, not deleted nor hidden.
- **Evidence (test pin):**
  `test_phase28a_cantilever_buckle.py:78` explicitly tests that the
  C3D8 runner refuses fixed-free with `NotImplementedError`. The
  rejected path is regression-locked.
- **Evidence (NOTES.md):**
  `golden_samples/cantilever-buckle-candidate/NOTES.md` § "Honest
  scope record — C3D8 hex cantilever attempt (rejected)" names
  observed 24622 N vs analytical 6908 N, root-cause analysis
  (shear locking), and pivot to B31. **No hedge language.**
- **Verdict:** This is **honest**, not hedging. The pivot was
  recorded in the runner docstring + NOTES + a regression test.
  Phase 27's "pivot BEFORE execution" pattern is replicated here:
  attempt logged, failure surfaced, pivot to existing infra.
- **Minor deduction (-8):** The 8th case rides on an existing
  runner (B31) which means Phase 28 A's net new FEA code surface
  is approximately zero. Honest, but the "new validated case"
  framing slightly oversells what was added relative to Phase
  22 A's B31 work. NOTES.md does call this out ("NO new runner");
  the +0.0298% residual being "tightest across all 8" is
  arithmetically true but residual-on-existing-runner is a weak
  proxy for FEA capability lift.

### 4. Residual budget + tolerance discipline — **80/100**

- **Evidence (per-case tolerances in verdict YAMLs):**
  cylinder-pv 5% / cantilever-beam 15% / plate-with-hole 20% /
  euler-column 10% / plate-ss 15% / cantilever-modal 12% /
  cantilever-modal-l50 12% / cantilever-buckle 10%. Tolerances
  are **per-runner**, set in code as module constants
  (e.g., `BUCKLING_CROSS_CHECK_TOLERANCE_PCT` in
  `buckling_euler.py`).
- **Evidence (residuals):** -6.87% / -6.87% / +0.13% / +0.21% /
  -5.79% / +0.13% / +0.14% / **+0.0298%** (Phase 28 A). All
  signed; all comfortably inside their per-runner envelopes.
- **Gap:** `_claim_tier.py` registry pins **only the verdict**
  (`payload.get("verdict") == "PASS"` overlay), NOT the
  tolerance value nor the residual envelope. A future regression
  could LOOSEN a tolerance from 5% to 50% and the registry would
  still promote. There is no SSOT pin that "cylinder-pv must
  remain at ≤5%". Phase 25-26 anti-gaming-guard pattern (two-tier
  pin) exists on rigid-body filter but NOT on tolerance.
- **Score:** Discipline is real (per-case tolerances are
  justified in NOTES.md and runner docstrings); pinning is
  partial (verdict yes, tolerance no). 80/100, unchanged from
  Phase 27.

### 5. Claim-tier registry signed-set discipline — **88/100**

- **Evidence:** `_claim_tier.py:80-151` declares 12 case_ids at
  baseline `tier_1_candidate`; `_apply_verdict_overlay()`
  (lines 154-184) promotes to `tier_2_validated` if and only if
  the per-case `cross_check_verdict.yaml` exists, parses as
  JSON, and reports `verdict == "PASS"`. 8 cases satisfy this;
  the remaining 4 (rod-wave-impact-candidate,
  swing-arm-fatigue-candidate, ballistic-plate-candidate,
  leak-shell-candidate) correctly remain at tier_1_candidate
  (no verdict file in `golden_samples/`).
- **Evidence (signed-registry refusal):** `_SIGNED_REGISTRY_PATTERN`
  (line 189) refuses `GS-NNN` lookups with `ValueError` (HF1.7a
  defense). Verified by `test_phase18b_tier_pivot.py`.
- **Inflation check:** No `*-candidate` case is currently
  registered as `tier_2_validated` without a corresponding live
  PASS verdict yaml. **No token "validated" entries.**
- **Gap (-12):** The registry's baseline list (`_claim_tier.py:80-151`)
  silently lists cases like `swing-arm-fatigue-candidate` and
  `ballistic-plate-candidate` whose validation path is not even
  staged — there is no runner, no analytical formulation, no
  cross-check kind. These are baseline-only and correctly
  tier_1, but the registry doesn't distinguish "candidate with a
  pending runner" from "candidate with no validation plan". A
  future operator reading the registry alphabetically would
  assume ballistic-plate-candidate is on the same roadmap as
  cylinder-pv-candidate, which it is not.

### 6. Ballistic Tier 2 readiness — **42/100**

- **Evidence (frontend builder):**
  `frontend/src/state/trustCenterViewModel.ts:367-422`
  `buildBallisticSection` is a pure builder; it consumes
  `BallisticSectionContext.candidateBallistic` (from backend)
  and `ballisticTier2BlockerSummary` (composed at
  `App.tsx:720-722` from
  `candidateBallistic.tier2_blockers_ballistic.join('; ')`).
- **Evidence (blockers are HONEST):** The summary is **sourced
  from the backend candidate ballistic spine**
  (`tier2_blockers_ballistic` is a backend field, not a frontend
  literal). The fallback when no ballistic block is present is
  `'Ballistic Tier 2 blockers are not surfaced (no ballistic
  block).'` — also honest (no fabricated all-clear).
- **Evidence (claim impact strings):**
  `trustCenterViewModel.ts:379, 390, 396, 402, 413` all carry
  verbatim Tier-1 language: "Tier 1 candidate; not signed
  validation; not benchmark agreement", "perforated_candidate is
  NOT 'perforation completed'", "energy ratio is a Tier 1
  candidate health indicator only", "Tier 2 dt convergence is
  reserved for FM-04b". These are SSOT-anchored, not token.
- **Gap (-58):** The blockers are *surfaced honestly*, but the
  underlying **physics gap is enormous**: NO validated explicit-
  dynamic case, NO contact-pair runner, NO large-deformation
  case, NO erosion/failure model in the validated cohort. Phase
  28 B is "pure builder extraction" (frontend refactor), zero
  new FEA capability. The ballistic surface area of the validated
  cohort is **0/8 cases**. The product is a ballistic FEA review
  workbench whose validated cohort has zero ballistic content.
  The blocker UI is honest **because it correctly reflects how
  far away Tier 2 ballistic is**.

## Composite FEA score: **(66 + 55 + 92 + 80 + 88 + 42) / 6 = 70.5/100**

## Phase-28 lift over Phase 27 FEA baseline: **~+0.5 to +1.5**

Phase 27 FEA Dim 1 was 65 (retro § Honest scope misses #1). Phase
28 A lifts Dim 1 by +1 (count 7→8) and Dim 3 by ~+2 (preserved
honest C3D8 rejection + new k=2 validation point). Dims 2, 4, 5,
6 are unchanged. Honest FEA composite delta from Phase 27 ≈ +1.
Defended: **this is within the predicted "+2 to +4 max" band on
the low end**, because the 8th case rides an existing runner and
adds no new element class / solver kind. Anyone selling Phase 28 A
as a "+4 FEA lift" is double-counting count-vs-discipline.

## Phase 29 recommendations (top 3)

1. **Ship the shell element (S4) validated case + CalculiX
   shell-output reader plumbing.** This is now Phase 27 punchlist
   #1 carried into Phase 28 carried into Phase 29. The hard cap
   on FEA Dim 1 (≤75 while shells absent) survives until this
   ships. Highest single lift available: +8 to +12 on Dim 1, +5
   on Dim 2 (shell solver path is new code).
2. **Ship the first `*DYNAMIC explicit` (or `*DYNAMIC, EXPLICIT`
   in CalculiX) validated case** — the product is ballistic. A
   simple 1D wave-propagation rod (e.g., Hopkinson bar elastic
   regime) with a closed-form transit-time + reflection amplitude
   cross-check would lift Dim 2 by +10 and Dim 6 by +15-20.
   Without an explicit-dynamic validated case the ballistic
   workbench framing is structurally unsupported.
3. **Pin per-case tolerance values in the registry, not just
   verdicts.** Extend `_claim_tier.py` overlay to record
   `(verdict, tolerance_pct, residual_pct_at_promotion)` so a
   future loosening of `BUCKLING_CROSS_CHECK_TOLERANCE_PCT` from
   10% to 50% would trip a regression test. Cheap (≤30 LOC +
   1 test, qualifies as spike-class per CLAUDE.md v2.3); lifts
   Dim 4 from 80 → ~92.

---

Not signed validation; not benchmark agreement.
