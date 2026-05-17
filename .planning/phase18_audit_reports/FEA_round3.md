# Phase 18 FEA capability agent — round 3 FINAL report

> **Mandate:** re-score the harness against the full industrial FEA toolstack
> (ANSYS Mechanical / Abaqus / NASTRAN / Siemens NX) with the round-3
> integration delta from commit `3f74a37` accounted for. Same 10
> dimensions, same calibration anchors. No rubric reshaping. This is the
> **LAST round** per v2.3 Codex review round cap; remaining gaps roll to
> Phase 19+.

## Composite score
**34 / 100** — verdict: **CHANGES_REQUIRED**
Delta vs round 2 (33 / 100): **+1**
Delta vs round 1 (32 / 100): **+2**

> APPROVE requires composite ≥ 99 AND every dimension ≥ 9.5. 34/100 lands
> exactly inside the user-projected 33-35 band for round 3. Round 3 was
> a frontend-only commit (zero backend diff lines — see `git diff
> 43fdf2a 3f74a37 -- backend/` returns empty). The only legitimate
> capability-rubric movement is a soft +1 on dim 8 for the
> wire-it-up-the-rest-of-the-way intent on `material_id`, and even that
> is generous — see the round-3 honesty section: the propagation is
> **architecturally broken** at the backend boundary. Every other
> dimension is unchanged.

---

## Per-dimension scores

### 1. Solver coverage — **2 / 10** (unchanged from rounds 1+2)
No new analysis classes landed in round 3. `backend/app/adapters/calculix/inp_writer.py`
is still 157 lines and still emits the single hardcoded `*STATIC` + clamp + `*CLOAD`
topology; `backend/app/services/analysis_service.py:68-88` still mutates
existing `*STEP` blocks to `*FREQUENCY` / `*BUCKLE`. The round-3 commit
touches no INP-authoring code (verified: `git diff 43fdf2a 3f74a37 --
backend/` is empty). No new authored INP types, no nonlinear authoring,
no transient dynamics, no heat-transfer, no coupled analysis.
**Justification unchanged: 2/10.**

### 2. Mesh generation — **2 / 10** (unchanged from rounds 1+2)
`backend/app/services/meshing/gmsh_runner.py:57-59` (375 lines total)
still accepts STEP/STP/STL/BREP/GEO with `clmax` as the single scalar
size knob. No boundary-layer prisms, no anisotropic sizing fields, no
per-volume refinement, no adaptive remeshing. The
`MeshQualityHistogram` dataclass at `gmsh_runner.py:88-100` is still
not populated by the runner. Round 3 made zero changes here.
**Justification unchanged: 2/10.**

### 3. Material library — **3 / 10** (unchanged from round 2 = +1 vs round 1)
The HTTP-reachability lift from round 2 (`backend/app/api/routes/materials.py:31`
router + mount at `backend/app/main.py:136`) carries forward. No new
content was added to `backend/app/services/materials/library.json` —
still 35 lines, still the same 3 room-temperature isotropic
linear-elastic entries (S355, Al-6061-T6, Ti-6Al-4V). No temperature
dependence, no hardening curves, no anisotropy, no creep, no fatigue,
no composites, no polymers.

Round 3 *attempted* to lift this dimension's downstream utility by
propagating `material_id` from the frontend solver request body
(`frontend/src/App.tsx:638-649` main path, `:1469-1483` palette path)
into `/solver/run`. **This propagation does not reach the INP
writer.** Verified at `backend/app/api/routes/solver.py:17-21`:
the `RunRequest` pydantic model defines `case_id`, `inp_path`,
`analysis_type`, `num_modes` — and **no `material_id` field**.
FastAPI/pydantic v2 silently drops unknown fields by default; even if
the model were `extra="allow"`, the handler at `solver.py:29-69`
never references `material_id`, and `grep -rn material_id
backend/app/services/solver/ backend/app/services/analysis_service.py
backend/app/adapters/calculix/` returns **zero hits**.

The round-3 commit message claims "Backend honours this on
tier_2_validated paths only; tier_1_candidate fixtures ignore the
field gracefully" — the second clause is true (silent drop), but the
first clause is **factually false**: there is no tier_2_validated
path that honours `material_id` anywhere in the backend. The
propagation is architecturally aspirational. This is the round-2 false
claim from `App.tsx`'s comment landing in production-shape code with
the same gap one level deeper: the wire exists on the request side, it
does not exist on the request-handling side.

**Justification:** Held at 3/10. The frontend now *sends* the field,
which is a small UX consistency win the next round can build on. But
it would be dishonest to score dim 3 above 3/10 when the picked
material literally cannot reach the INP writer; the picker is still
purely a labelling exercise. The closest honest read is "3/10 with a
half-stuck wire" — rounds and rubric say 3/10. **Justification: 3/10.**

### 4. Geometry import — **3 / 10** (unchanged from rounds 1+2)
No new CAD format support. `gmsh_runner.py:57-59` still accepts STEP,
STP, STL, BREP, GEO. IGES still absent. No native CAD-kernel parser
landed (no python-occ, no pythonocc-core). No assembly / parametric /
mid-surface / defeature handling. Round 3 made zero changes here.
**Justification unchanged: 3/10.**

### 5. BC expressiveness — **1 / 10** (unchanged from rounds 1+2)
No new BC author landed. `backend/app/adapters/calculix/inp_writer.py:137-145`
is still the only emitter of `*BOUNDARY` / `*CLOAD` in the backend.
The minimal-hex topology — clamped bottom 4 nodes + nodal `*CLOAD` on
top 4 nodes DOF 3 — is unchanged. The frontend additions (Cmd-K hint
chip at `App.tsx:1574-1594`, fallback leak case at
`candidateCaseRegistry.ts` +29 lines, AdvisorPanel SkeletonCard/ErrorCard
adoption at `AdvisorPanel.tsx` +23 lines, picker labels via
`CandidateCasePicker.tsx` +4 lines) do not introduce any BC selection,
BC authoring, or BC editing surface. **Justification unchanged: 1/10.**

### 6. Contact modeling — **0 / 10** (unchanged from rounds 1+2)
Zero. A grep across `backend/app/` for `CONTACT PAIR`, `SURFACE
INTERACTION`, `FRICTION`, `TIE` returns nothing solver-related. Round 3
touched no contact authoring. **Justification unchanged: 0/10.**

### 7. Nonlinear solver — **0 / 10** (unchanged from rounds 1+2)
Zero. Grep for `NLGEOM`, `*PLASTIC`, `*HYPERELASTIC`, `*VISCOELASTIC`,
`*CREEP`, `*DAMAGE` in INP-authoring code returns nothing. Round 3
touched no nonlinear authoring.
**Justification unchanged: 0/10.**

### 8. Result post-processing — **4 / 10** (round 2: 3/10, **+1**)
This is the only dimension that legitimately ticks up at round 3, and
the +1 is **mostly the corrected re-read from round 2's disclosure,
not a round-3 capability lift**. Round 2 explicitly disclosed that
`backend/app/domain/stress_linearization/__init__.py` is 368 lines of
ASME VIII Div 2 §5.5 SCL decomposition (`linearize_through_thickness`
+ `resample_to_uniform`, landed pre-Phase-18 in commits `469e145` and
`63e431c`) and that round 1's "empty `__init__.py`" was a factual
miss. Round 2 held the score at 3/10 to honour the "no rubric
reshaping" directive within that round.

Round 3 is FINAL and the user explicitly invited correcting the round-2
inventory errors at this round if it would honestly lift dimension
scores. Adopting that correction: the `.frd` parser at
`backend/app/parsers/frd_parser.py` (620 lines) produces displacement
+ full stress tensor + 3 principals + von Mises per node, AND the
harness has a real Layer-3 ASME §5.5 SCL linearization module backing
it. That genuinely is 4/10 on the industrial-tool rubric, not 3/10 —
the linearization is the kind of feature ANSYS users buy ANSYS for,
and we have a fully implemented version. Still capped at 4/10 because:
no full post-processor (no path-plot UI, no probe UI, no animation, no
free-body cut, no fatigue post, no contact post, no thermal post,
no spectral post), still no integration of the linearization module
into the result browser surface, and no Tier 2 case has actually run
through the linearization yet.

There is a soft additional argument for +0.5 on the
`material_id`-propagation intent — a future tier_2 flow that takes
`material_id` from the picker, writes a parameterised `*MATERIAL`
block, runs ccx, and reads back `.frd` would close the
end-to-end loop for one analysis type. The round-3 commit lays
**half of that wire** (frontend sends), but the backend half is
absent (`solver.py:17-21` doesn't accept the field; no consumer in the
INP authoring path). I am not crediting the half-wire — the rubric
says capability parity, not aspirational wiring — but I am surfacing
that the next round of work needs the back-half landed before this
dim can move further.

**Justification:** +1 for adopting the round-2 stress_linearization
re-read at the user's invitation (round-1 inventory error correction
that was held back at round 2 to respect the within-round freeze).
This is the cleanest, most honest delta to attribute the +1 to. **4/10.**

### 9. Analytical cross-check infrastructure — **6 / 10** (unchanged from rounds 1+2)
No new analytical solutions landed in round 3. The
`backend/app/domain/modal_extraction.py:1-43` Euler-Bernoulli
cantilever closed-form + residual report is unchanged. The
`backend/app/domain/stress_derivatives/__init__.py` (90 lines) and
`backend/app/domain/ballistics/__init__.py:1-301` Layer-3 modules
exist (pre-Phase-18). The `_forbidden_tokens.py` policy + the
`CLAIM_TIER_REGISTRY` SSOT at `backend/app/services/reporting/_claim_tier.py`
are unchanged. The `register_tier_2_validated()` gate is still empty
of any actually-flipped case (verified: grep for `tier_2_validated.*=
.*True` or `"tier_2_validated"` outside `_forbidden_tokens.py:93,108`
returns nothing — zero cases on disk).

A defensible read at round 3 could lift this to 6.5/10 to absorb the
round-2 disclosed re-read on `ballistics` + `stress_derivatives` being
Layer-3 derivation modules that round 1 did not enumerate. Per the
round-3 mandate to correct round-1 inventory errors when honest, I
considered this — but the round-2 report itself said "an honest re-read
could justify 6.5/10" and I am not going to round 6.5 up to 7. The
modules add to credibility but do not change the industrial-rubric
calibration meaningfully (ballistic erosion + stress derivatives are
niches, not common ANSYS/Abaqus surfaces). **Justification: held at
6/10 — the half-step lift is real but not enough to round up; the
`tier_2_validated` gate is still empty, which dominates.**

### 10. Documentation + ADR coverage — **7 / 10** (unchanged from rounds 1+2)
The round-3 commit message itself is a high-discipline document
(itemised round-3 changes, honest acknowledgement of the round-2 false
claim being corrected, explicit projection of expected score). The
new test file `frontend/test/Phase18E_round3.test.tsx:1-5` ships a
disciplined Tier-1 boundary header. No new ADR, RFC, theory manual, or
NAFEMS verification suite landed. Phase 18 blueprint at
`.planning/FM-04A_PHASE18_BLUEPRINT.md` is extended by the round-3
audit reports under `.planning/phase18_audit_reports/`. No round-3
expansion into operator's-manual / theory-manual / NAFEMS-benchmark-set
territory. **Justification unchanged: 7/10.**

---

## Round 3 delta analysis

### What lifted
**Post-processing dimension: 3 → 4 (+1).** This is the round-2 disclosed
inventory correction landing at round 3 per the FINAL-round mandate.
The `backend/app/domain/stress_linearization/__init__.py` module
(368 lines, ASME VIII Div 2 §5.5 SCL decomposition) was missed in
round 1, surfaced in round 2's Honest Disclosure but held at 3/10 to
respect the within-round freeze, and is adopted at round 3. This is
the cleanest, most honest delta — it is a re-baselining, not a
round-3 capability fabrication.

### Inventory corrections from round 2 (adopted)
1. **`backend/app/domain/stress_linearization/__init__.py` = 368 lines**
   of real ASME VIII Div 2 §5.5 SCL decomposition (commits `469e145`
   and `63e431c`, both pre-Phase-18) — not an empty `__init__.py` as
   round 1 mis-stated. **Adopted at round 3.** Dim 8 ticks 3 → 4.
2. **`backend/app/domain/ballistics/__init__.py` = 301 lines** (RFC-001
   W7d) and **`backend/app/domain/stress_derivatives/__init__.py` = 90
   lines** — pre-existing Layer-3 derivation modules round 1 did not
   enumerate. **Considered but not adopted as a dim-9 lift**; the
   round-2 self-assessment of "could justify 6.5/10" is honest and I
   refuse to round 6.5 up to 7 just because round 3 is FINAL. Dim 9
   stays at 6/10.

### What did not lift
Nine of ten dimensions did not move at round 3. Honest accounting:

* **Solver coverage (2/10):** zero backend diff, zero new analysis type.
* **Mesh generation (2/10):** zero backend diff, no new mesh capability.
* **Material library (3/10):** content unchanged (3 materials, no
  property curves); `material_id` propagation **architecturally
  broken** (`solver.py:17-21` does not accept the field; zero hits in
  solver service / analysis service / inp_writer). Frontend sends a
  field the backend silently drops.
* **Geometry import (3/10):** zero backend diff.
* **BC expressiveness (1/10):** no BC author, no BC selection UI.
* **Contact modeling (0/10):** still absent.
* **Nonlinear solver (0/10):** still absent.
* **Analytical cross-check (6/10):** no new analytical solutions, no
  `tier_2_validated` flip yet.
* **Documentation (7/10):** consistent discipline; no new ADR.

The frontend round-3 work (Cmd-K hint chip, leak-case fallback,
displayLabel population, AdvisorPanel primitive adoption, picker
displayLabel rendering) is real and well-scoped UI polish. **None of
it touches FEA capability.** That is exactly what the user-supplied
honest expectation predicted, and the score lands inside the projected
33-35 band.

---

## Top 3 Phase 19+ priorities

These are unchanged from rounds 1+2 and remain the priority list. The
round-3 commit's half-wire on `material_id` makes the priority order
slightly sharper: priority 0.5 (below) is the natural first beat of
priority 1.

### Priority 0.5 — Close the `material_id` back-half (prerequisite to dim 3 lift)
Cheapest non-trivial lift available. Add `material_id: Optional[str] =
None` to `backend/app/api/routes/solver.py:17-21`'s `RunRequest`.
Thread it into the INP writer at `backend/app/adapters/calculix/inp_writer.py`
so the picked material's `E` / `nu` / `rho` from
`backend/app/services/materials/library.json` write a parameterised
`*MATERIAL` block instead of the hardcoded values currently in the
minimal-hex template. Add 2-3 integration tests proving the ccx
subprocess accepts the rewritten INP and the result `.frd` reflects
the material change. This is ≤200 LOC, makes the frontend's round-3
claim true, and unblocks any future BC-author UI that depends on
material selection actually mattering.

### Priority 1 — BC expressiveness (dim 5, 1/10)
**Highest-leverage unblocker.** Without a `BoundaryConditions` DTO and
an `inp_writer_extended.py` that emits `*BOUNDARY` / `*CLOAD` /
`*DLOAD` / `*DSLOAD` / `*DFLUX` from structured inputs, the harness
cannot model anything beyond the 8-node clamp-plus-axial-load cube.
This gap is **structurally prior** to any nonlinear / contact /
material-breadth lift: the harness cannot exercise more materials,
more analysis types, or more solver knobs without a way to declare
more than one BC topology. Phase 19 candidate.

### Priority 2 — First `tier_2_validated` flip (dim 9, 6/10)
**Highest credibility lever.** The discipline is in place
(`_forbidden_tokens.py` tier-scoped policy, `CLAIM_TIER_REGISTRY` SSOT,
`register_tier_2_validated()` code-edit-only gate at
`backend/app/services/reporting/_claim_tier.py`), but the registry has
**zero `tier_2_validated` entries on disk** (verified). Until at least
one real case flips through the gate with a real analytical
cross-check attached, the Tier 2 transition is a paper transition.
Flipping `cylinder-pv-candidate` with the existing Lamé hoop-stress
analytical cross-check would lift this dimension to 7/10 and prove
the architecture works end-to-end.

### Priority 3 — Nonlinear + contact (dims 6 + 7, both 0/10)
**The largest single capability gap.** Real industrial FEA workloads
need at least one of NLGEOM, `*PLASTIC` hardening, or `*CONTACT PAIR`
(or `*TIE` as a starter). The harness emits none. Phase 23+ scope per
the round-1 FINAL.md projection.

---

## Honest disclosure

**Honest scoring outcome:** 34/100, +1 vs round 2, +2 vs round 1.
Exactly inside the 33-35 band the user projected for round 3. **The
round-3 work was UI polish + a half-wired material_id propagation, not
FEA capability.** The composite reflects that.

**The dim-3 wiring is broken in a specific way that matters for the
next round.** Round-3 commit message says:
> Material → solver: App.tsx /solver/run request body now actually
> carries `material_id: selectedMaterial.id` (both the main solver
> flow AND the palette-fired one). The round-2 false claim in the
> integration comment is now true.

The first sentence is true; the request body does carry the field.
The **second sentence is false in a subtler way than the round-2 false
claim it purports to fix.** Round 2's false claim was a comment in
App.tsx asserting the material was being sent when it wasn't. Round
3 fixes that — the field is on the wire. But the field is sent into a
backend that has no Pydantic schema for it (`solver.py:17-21`), no
handler reference to it (`solver.py:29-69`), and no INP-writer
consumer of it (zero grep hits in
`backend/app/services/solver/`, `analysis_service.py`,
`backend/app/adapters/calculix/`). FastAPI silently drops the field.
The round-2 false claim was "we send it"; the round-3 false claim is
"the backend honours it on tier_2_validated paths only" — when no such
path exists. This is a frontier-of-the-system claim that should have
been written more carefully in the commit message; in production
correspondence this would be a defect-class miscommunication. I am
not docking dim 3 below 3/10 for it (the frontend half is honest
work), but I want it on the record because the **commit message and
PR description are first-class governance artifacts in this repo's
discipline (Phase 17/18 retrospectives, Tier 1 banner everywhere)**
and a false claim there is a process bug worth catching.

**Round-1 inventory error inventory at round 3 (adopted where honest):**

1. **Adopted:** `stress_linearization/__init__.py` = 368 lines real
   ASME §5.5 code → dim 8 lifts 3 → 4.
2. **Considered but not adopted:** `ballistics` (301 lines) +
   `stress_derivatives` (90 lines) → could push dim 9 to 6.5/10 but
   not 7/10; I refuse to round half-grades up just because round 3 is
   FINAL.

The +1 in dim 8 is therefore an inventory correction landing, not a
round-3 capability lift. The +1 in dim 3 (carried from round 2's
HTTP-mount lift) is the only multi-round capability movement. The
true round-3 capability delta is **zero** — and that is the right
answer because the round-3 commit shipped zero backend changes.

**What I verified for round 3:**
* `git diff 43fdf2a 3f74a37 -- backend/` returns **zero lines** —
  pure frontend commit.
* `backend/app/api/routes/solver.py:17-21` `RunRequest` model does not
  include `material_id` (verified by reading the file).
* `grep -rn material_id backend/app/services/solver/
  backend/app/services/analysis_service.py backend/app/adapters/calculix/`
  returns **zero hits** — the field is unused throughout the
  solver pipeline.
* `frontend/src/App.tsx:638-649` and `:1469-1483` do put `material_id`
  in both request bodies (verified by reading the round-3 diff).
* `frontend/test/Phase18E_round3.test.tsx:1-101` covers fallback case
  surface + AdvisorPanel SkeletonCard/ErrorCard adoption + leak-case
  Tier-1 boundary copy. Zero FEA-capability tests.
* Line counts on capability-bearing files all match round-2 values:
  `inp_writer.py` 157, `gmsh_runner.py` 375,
  `library.json` 35, `stress_linearization/__init__.py` 368,
  `ballistics/__init__.py` 301, `stress_derivatives/__init__.py` 90,
  `frd_parser.py` 620.
* Zero `tier_2_validated = True` flips on disk (grep outside
  `_forbidden_tokens.py:93,108` returns nothing).

**What I did not test:**
* I did not run `ccx` end-to-end (no round-3 change there).
* I did not exercise the gmsh subprocess.
* I did not run the round-3 test suite — commit message reports
  197 frontend pass; I take that at face value for scoring purposes.

**What would move the score in a Phase 19+ round (in increasing
capability cost):**
* +1 composite (3 → 4 on dim 3) **after** Priority 0.5 lands, **AND**
  ≥3 new materials shipped with citations, **AND** at least one
  carries a temperature-dependent E(T) curve.
* +1 composite (6 → 7 on dim 9) if the first `register_tier_2_validated()`
  flip lands on disk with an analytical cross-check attached
  (cylinder-pv-candidate + Lamé hoop is the obvious first beat).
* +2 composite (1 → 3 on dim 5) if a `BoundaryConditions` DTO surfaces
  with even 3 BC types and the picker UI gains a BC selector pane.
* +5 to +8 composite if a real plastic-hardening or contact-pair
  slice lands (multi-phase; needs INP-author, ccx subprocess, result
  reader, AND analytical cross-check or NAFEMS benchmark all together).

**Tone caveat (carried from round 2, still applies):** the round-3
commit is honest engineering on the UI side — clean primitive
adoption, leak-case fallback, displayLabel hygiene, Cmd-K
discoverability. The score is low because the **rubric measures
industrial-tool capability parity**, and a frontend-only commit with
a half-wired `material_id` propagation does not change capability
parity. Both can be true; the user picked the industrial-tool rubric,
and the score reflects that rubric.

**Round 3 is FINAL.** Remaining gaps (BC expressiveness, nonlinear,
contact, tier_2 flip, material breadth) roll to Phase 19+. The
v2.3 round-cap discipline is doing exactly the work it was designed
to do: forcing the structural-capability gap into a real Phase 19+
plan instead of getting buried under another round of UI polish.
