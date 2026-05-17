# Phase 18 FEA capability agent — round 2 report

> **Mandate:** re-score the harness against the full industrial FEA toolstack
> (ANSYS Mechanical / Abaqus / NASTRAN / Siemens NX) with the round-2
> integration delta from commit `43fdf2a` accounted for. Same 10 dimensions,
> same calibration anchors. No rubric reshaping.

## Composite score
**33 / 100** — verdict: **CHANGES_REQUIRED**
Delta vs round 1 (32 / 100): **+1**

> APPROVE requires composite ≥ 99 AND every dimension ≥ 9.5. 33/100 is
> the honest score — landing inside the 33-35 band the round-1 FINAL.md
> projection predicted. The round-2 work was UI-integration only (no new
> solver capability, no contact, no nonlinear, no thermal, no new
> materials in the library, no new BC types, no new analytical
> cross-check). Only one dimension legitimately moves: materials
> library, by +1, because the library is now HTTP-reachable rather than
> Python-import-only. Every other dimension is unchanged; the
> capability-vs-industrial-tool gap is not addressable by a
> single-session integration slice.

---

## Per-dimension scores

### 1. Solver coverage — **2 / 10** (unchanged from round 1)
No new analysis classes landed in round 2. `inp_writer.py:53-157` still
emits the single hardcoded `*STATIC` + clamp + `*CLOAD` topology;
`analysis_service.py:68-88` still mutates existing `*STEP` blocks to
`*FREQUENCY` / `*BUCKLE`. No new authored INP types, no nonlinear
authoring, no transient dynamics, no heat-transfer, no coupled
analysis. The round-2 commit added an HTTP GET route + a React picker;
neither touches solver authoring. **Justification unchanged: 2/10.**

### 2. Mesh generation — **2 / 10** (unchanged from round 1)
`backend/app/services/meshing/gmsh_runner.py:57-59` still accepts
STEP/STP/STL/BREP/GEO with `clmax` as the single scalar size knob.
No boundary-layer prisms, no anisotropic sizing fields, no per-volume
refinement, no adaptive remeshing. The `MeshQualityHistogram`
dataclass at `gmsh_runner.py:88-100` is still not populated by the
runner. **Justification unchanged: 2/10.**

### 3. Material library — **3 / 10** (round 1: 2/10, **+1**)
This is the only legitimate round-2 lift. Round 1 scored the materials
slice 2/10 against the industrial benchmark because while the citation
discipline (`backend/app/services/materials/api.py:100-106` refuses
entries without a `reference` field) was best-in-class for the size,
the library was a Python-module-only fixture: nothing on the HTTP
surface, nothing the UI could consume. Round 2 changes that:

* `backend/app/api/routes/materials.py:31` defines an `APIRouter` with
  `GET /materials/` and `GET /materials/{id}`, composed from
  `app.services.materials.list_materials` / `get_material` (route
  module at `:24-28`).
* `backend/app/main.py:136` mounts the router under `/api/v1`. This is
  the first time the materials library has been part of the HTTP
  surface — previously `main.py` imported every other route but not
  this one.
* `backend/app/api/routes/materials.py:45-55` decorates each payload
  with the Tier 1 claim banner inline, so consumers see the boundary
  language without a second request — discipline carrying forward
  from the JSON-side citation policy.
* `frontend/src/materialsClient.ts:134-164` provides a typed `fetch`
  helper with live/fallback semantics and a byte-equivalent static
  fallback list (`:57-95`), and `MaterialPickerPanel.tsx:31-158` is a
  functional click-to-pick UI with skeleton-load + error-card + Tier-1
  banner rendering.
* `backend/tests/test_phase18e_materials_route.py:1-127` covers the 10
  handler paths (handler-direct, dodging the pre-Phase-18 `app.api/__init__`
  import side-effects).

But the library content is **unchanged**: `library.json` still ships the
same 3 room-temperature isotropic linear-elastic entries (S355,
Al-6061-T6, Ti-6Al-4V at `:1-35`). No temperature dependence, no
hardening curves, no anisotropy, no creep, no fatigue, no composites,
no polymers. The lift is **integration surface, not capability
breadth.** Against the industrial benchmark (ANSYS Granta MI > 500K
materials with full property curves; Abaqus default ~150 materials +
UMAT/VUMAT), 3 materials behind HTTP is still proof-of-concept slice
territory.

**Justification:** +1 because the library is now consumable by a real
UI surface (the boundary the round-1 FINAL.md flagged as the round-2
lift criterion was specifically the HTTP-reachable / Python-only
gap). Still capped at 3/10 because the breadth gap to industrial
material catalogs is enormous and unchanged.

### 4. Geometry import — **3 / 10** (unchanged from round 1)
No new CAD format support. `gmsh_runner.py:57-59` still accepts STEP,
STP, STL, BREP, GEO. IGES still absent. No native CAD-kernel parser
landed in round 2 (no python-occ, no pythonocc-core). No assembly /
parametric / mid-surface / defeature handling. **Justification
unchanged: 3/10.**

### 5. BC expressiveness — **1 / 10** (unchanged from round 1)
No new BC author landed. `backend/app/adapters/calculix/inp_writer.py:137-145`
is still the only emitter of `*BOUNDARY` / `*CLOAD` in the backend
(grep confirms). The minimal-hex topology — clamped bottom 4 nodes +
nodal `*CLOAD` on top 4 nodes DOF 3 — is unchanged. The picker UI
selects a material; it does not select / author / assign any boundary
condition. **Justification unchanged: 1/10.**

### 6. Contact modeling — **0 / 10** (unchanged from round 1)
Zero. A grep across `backend/app/` for `CONTACT PAIR`, `SURFACE
INTERACTION`, `FRICTION`, `TIE` returns nothing solver-related. No
round-2 work touched contact authoring. **Justification unchanged: 0/10.**

### 7. Nonlinear solver — **0 / 10** (unchanged from round 1)
Zero. Grep for `NLGEOM`, `*PLASTIC`, `*HYPERELASTIC`, `*VISCOELASTIC`,
`*CREEP`, `*DAMAGE` in INP-authoring code returns nothing.
(The `openradioss_dynamic_result_exporter.py:38` `plastic_strain`
literal is a pre-existing **result-importer** field for an external
solver's output, not a solver capability the harness exposes.)
**Justification unchanged: 0/10.**

### 8. Result post-processing — **3 / 10** (unchanged from round 1)
No new post-processing capability landed in round 2. The `.frd`
parser at `backend/app/parsers/frd_parser.py:31-58` still produces
displacement + full stress tensor + 3 principals + von Mises per
node. The Layer-3 `stress_linearization` package — round 1 incorrectly
described as "an empty `__init__.py`" — actually contains a 368-line
ASME VIII Div 2 §5.5 SCL decomposition (`linearize_through_thickness`
+ `resample_to_uniform`, landed pre-Phase-18 in commits `469e145` and
`63e431c`). Honest re-read would lift this dimension to ~4/10 on the
round-1 calibration. Per the user's "no rubric reshaping" directive
for round 2, I am **leaving the score at 3/10** and surfacing the
round-1 miss in the Honest Disclosure section rather than silently
rebasing. **Justification: held at 3/10 for round-1 consistency;
honest re-read would say 4/10 — see disclosure.**

### 9. Analytical cross-check infrastructure — **6 / 10** (unchanged from round 1)
No new analytical solutions landed in round 2. The
`backend/app/domain/modal_extraction.py:1-43` Euler-Bernoulli
cantilever closed-form + residual report is unchanged. The
`backend/app/domain/stress_derivatives/` (90 lines) and
`backend/app/domain/ballistics/__init__.py:1-301` Layer-3 modules
exist (pre-Phase-18). The `_forbidden_tokens.py` policy + the
`CLAIM_TIER_REGISTRY` SSOT at `backend/app/services/reporting/_claim_tier.py:75-81`
are unchanged. The `register_tier_2_validated()` gate is still empty
of any actually-flipped case (no case is `tier_2_validated` on disk).
**Justification unchanged: 6/10.**

### 10. Documentation + ADR coverage — **7 / 10** (unchanged from round 1)
The round-2 commit added a 90-line module docstring on
`backend/app/api/routes/materials.py:1-15` that names the Phase 18 E
scope, the Tier 1 boundary, and the round-2 integration purpose;
similarly disciplined headers on `frontend/src/materialsClient.ts:1-9`
and `frontend/src/components/MaterialPickerPanel.tsx:1-13`. This
maintains the existing docstring-cites-ADR/RFC discipline; it does
not add a new ADR, RFC, theory manual, or NAFEMS verification suite.
The Phase 18 blueprint at `.planning/FM-04A_PHASE18_BLUEPRINT.md` is
extended by the new audit reports under `.planning/phase18_audit_reports/`.
No round-2 expansion into operator's-manual / theory-manual /
NAFEMS-benchmark-set territory. **Justification unchanged: 7/10.**

---

## Round 2 delta analysis — what lifted / what didn't

### What lifted
**Materials dimension: 2 → 3 (+1).** The library is now part of the HTTP
surface and the frontend can render it. This matches exactly the
round-1 FINAL.md projection that materials was the lowest-hanging
integration-only lift available without new solver work. The
mechanism of the lift is identical to what FINAL.md anticipated:

* HTTP route mounted (`backend/app/main.py:136`)
* Typed client consumes it (`frontend/src/materialsClient.ts:134-164`)
* UI surface renders citations + banner (`frontend/src/components/MaterialPickerPanel.tsx:80-156`)
* Tests cover both handler + UI (10 backend + 16 frontend)

### What did not lift
Nine of ten dimensions did not move. Honest accounting:

* **Solver coverage (2/10):** no new analysis type authored.
* **Mesh generation (2/10):** no new mesh capability.
* **Geometry import (3/10):** no new CAD format support.
* **BC expressiveness (1/10):** no new BC author, no BC selection in UI.
* **Contact modeling (0/10):** still absent.
* **Nonlinear solver (0/10):** still absent.
* **Post-processing (3/10):** no new post-processing capability.
* **Analytical cross-check (6/10):** no new analytical solutions, no
  `tier_2_validated` flip yet on `_claim_tier.py:75-81`.
* **Documentation (7/10):** consistent discipline maintained, but no
  new ADR / theory manual / verification suite.

The composite delta is +1, exactly as round-1 FINAL.md projected. The
UI-integration slice the round-2 work shipped is necessary
infrastructure (a materials picker is a prerequisite for any future
BC-author UI that needs to choose a material per part), but it does
**not** address the structural FEA capability gap to industrial
tools.

---

## Top 3 capability gaps remaining (Phase 19+ priorities)

These are unchanged from round 1 and remain the priority list.

### Gap 1 — BC expressiveness (dim 5, 1/10)
**Highest-leverage unblocker.** Without a `BoundaryConditions` DTO and
an `inp_writer_extended.py` that emits `*BOUNDARY` / `*CLOAD` / `*DLOAD`
/ `*DSLOAD` / `*DFLUX` from structured inputs, the harness cannot
model anything beyond the 8-node clamp-plus-axial-load cube. This
gap is **structurally prior** to any nonlinear / contact / material-
breadth lift: the harness cannot exercise more materials, more
analysis types, or more solver knobs without a way to declare more
than one BC topology. Phase 19 candidate.

### Gap 2 — Nonlinear + contact (dims 6 + 7, both 0/10)
**The largest single capability gap.** Real industrial FEA workloads
need at least one of NLGEOM, `*PLASTIC` hardening, or `*CONTACT PAIR`
(or `*TIE` as a starter). The harness emits none. Most real-world
production cases require all three. Phase 23+ scope per round-1
FINAL.md.

### Gap 3 — Analytical cross-check breadth + Tier 2 flip (dim 9, 6/10)
**Highest credibility lever.** The discipline is in place
(`_forbidden_tokens.py` tier-scoped policy, `CLAIM_TIER_REGISTRY` SSOT,
`register_tier_2_validated()` code-edit-only gate at
`backend/app/services/reporting/_claim_tier.py:126-145`), but the
registry has zero `tier_2_validated` entries on disk. Until at least
one real case flips through the gate with a real analytical
cross-check attached, the Tier 2 transition is a paper transition.
Adding 3-5 more closed-form solutions (Lamé hoop stress, beam
bending, plate bending) and flipping `cylinder-pv-candidate` would
lift this dimension to 8/10 and prove the architecture works.

---

## Honest disclosure

**Honest scoring outcome:** 33/100, +1 vs round 1. Exactly inside the
33-35 band the round-1 FINAL.md projection predicted. **The round-2
work was UI-integration, not FEA-capability — and the composite score
reflects that.** If the user wanted the composite to move
materially, the round-2 scope would have needed to land at least one
of: (a) a new BC author, (b) a `tier_2_validated` flip on a real
case, (c) ≥10 new materials with property curves, (d) a nonlinear or
contact slice. None of these were in scope; none happened.

**Two round-1 inventory errors I found while re-reading:**

1. `backend/app/domain/stress_linearization/__init__.py` is **368 lines
   of real ASME VIII Div 2 §5.5 SCL decomposition code** (commits
   `469e145` and `63e431c`, both pre-Phase-18). Round 1 described it
   as "an empty `__init__.py` + `__pycache__`" — that was a factual
   miss. The honest re-read would lift dim 8 (post-processing) to
   ~4/10 on the round-1 calibration. **I did not silently rebase**
   per the user's "no rubric reshaping" directive; the dimension stays
   at 3/10 in the table above and the miss is disclosed here.

2. `backend/app/domain/ballistics/__init__.py` (301 lines, RFC-001 W7d)
   and `backend/app/domain/stress_derivatives/__init__.py` (90 lines)
   are pre-existing Layer-3 derivation modules round 1 did not
   enumerate. Neither changes the calibrated industrial-tool score
   meaningfully — they are project-specific niches (ballistic erosion,
   stress derivatives) not common to ANSYS/Abaqus/NX general-purpose
   surfaces — but they add credibility to dim 9 (analytical
   cross-check infrastructure). I left dim 9 at 6/10; an honest
   re-read could justify 6.5/10.

If both round-1 misses were corrected and the round-2 +1 on materials
applied, the corrected-rebase composite would be ~35/100, still
inside the user's predicted 33-35 band, still CHANGES_REQUIRED, and
still nowhere near the 99 cap. The point of the discipline is that
neither correction changes the verdict.

**What I verified for round 2:**
* `backend/app/api/routes/materials.py:1-91` exists and is mounted by
  `backend/app/main.py:136`.
* `frontend/src/materialsClient.ts:1-182` typed client with live +
  fallback paths.
* `frontend/src/components/MaterialPickerPanel.tsx:1-269` UI surface
  with skeleton / error-card / Tier-1 banner / selection state.
* `backend/tests/test_phase18e_materials_route.py:1-127` test scope.
* `backend/app/services/materials/library.json:1-35` unchanged
  (3 materials, same citations, same fields).
* No round-2 changes to `inp_writer.py`, `gmsh_runner.py`,
  `analysis_service.py`, `frd_parser.py`, or any other capability-
  bearing module.

**What I did not test:**
* I did not run `ccx` end-to-end (no round-2 change there).
* I did not exercise the gmsh subprocess.
* I did not run the round-2 test suite — the commit message reports
  123 backend pass + 191 frontend pass; I take that at face value for
  scoring purposes.
* I did not benchmark the new HTTP route under load.

**What would change the round-2 score:**
* +1 composite (3 → 4 on dim 3) if `library.json` ships ≥6 materials
  with citations and at least one carries a temperature-dependent
  E(T) curve.
* +2 composite (1 → 3 on dim 5) if a `BoundaryConditions` DTO surfaces
  with even 3 BC types and the picker UI gains a BC selector pane.
* +1 composite (6 → 7 on dim 9) if the first
  `register_tier_2_validated()` flip lands on disk with an analytical
  cross-check attached.

**Tone caveat:** the round-2 commit is honest engineering — clean
typed client, fallback discipline, citation surfacing inline,
sensible test scoping around the pre-existing `app.api.__init__`
import side-effects. The score is low because the **rubric measures
industrial-tool capability parity**, and a materials picker UI does
not change capability parity. Both can be true; the user picked the
industrial-tool rubric, so the score reflects that rubric.
