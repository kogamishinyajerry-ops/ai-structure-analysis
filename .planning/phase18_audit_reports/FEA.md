# Phase 18 FEA capability agent — report

> **Mandate:** evaluate this harness against the **full industrial FEA toolstack**
> (ANSYS Mechanical / Abaqus / NASTRAN / CalculiX-with-prepost as a packaged
> product). Scoring is ruthless and calibrated against those products, per
> user directive "按整个工业 FEA 工具栈评" + "绝对诚实客观".
> Phase 18 is **the first session of a months-long Tier 2 transition** —
> the score reflects the gap, not the engineering quality of what landed.

## Composite score
**32 / 100** — verdict: **CHANGES_REQUIRED**

> APPROVE requires composite ≥ 99 AND every dimension ≥ 9.5. Neither
> threshold is approachable in a single-session opening move on a tool
> whose entire pre-Phase-18 charter was *"not a solver, an audit harness"*.
> 32/100 is **the honest score**, well inside the 30-50 band the user
> pre-acknowledged. It is not a verdict on Phase 18's engineering quality
> (the slices that landed are clean) — it is the honest gap to the
> industrial-tool benchmark the user asked me to score against.

---

## Per-dimension scores

### 1. Solver coverage — **2 / 10**

The harness can execute **exactly one analysis type end-to-end through a
production-grade pipeline**: linear static, single-step, single-material,
single-element-type C3D8 hex on a hand-emitted INP
(`backend/app/adapters/calculix/inp_writer.py:53-157` — the `write_minimal_hex_inp`
is hardcoded to `*STATIC` + a `*CLOAD` on the top face, no other path).
A legacy pre-Phase-18 string-mutation service in
`backend/app/services/analysis_service.py:68-88` can rewrite an existing INP's
`*STEP` block to `*FREQUENCY` (modal) or `*BUCKLE` (linear buckling), and the
FRD parser at `backend/app/parsers/frd_parser.py:52` admits the type strings
`'static' / 'vibration' / 'buckling'` — but there is no first-class INP author
for those types, no nonlinear static authoring, no transient dynamics, no
explicit dynamics, no heat-transfer, no coupled thermo-mechanical pathway.
ANSYS Mechanical and Abaqus ship all seven analysis classes plus
sub-modeling, substructuring, and submodel-cuts as one-click; CalculiX itself
supports far more than this harness exposes.

**Justification:** 1/10 = "single hardcoded canonical case, no breadth" maps
to *just* the inp_writer. The legacy modal/buckling string-mutation pulls it
to 2/10. Not 3/10 because the modal/buckling path was not built in Phase 18,
is not covered by the new tests, and does not author its own INP — it patches
one that exists.

### 2. Mesh generation quality — **2 / 10**

`backend/app/services/meshing/gmsh_runner.py:57-59` accepts STEP / STP / STL /
BREP / GEO inputs and produces a `.msh` (or `.inp`) via the real `gmsh`
subprocess. Element order is constrained to 1 or 2 (`:210-216`), characteristic
length is a single scalar `clmax` (`:251-263`) — no boundary-layer prisms,
no anisotropic sizing fields, no per-volume / per-face refinement, no mid-mesh
remeshing during solve, no adaptive p- or h-refinement, no quad/hex meshing of
arbitrary geometry, no mesh-quality remediation. The `MeshQualityHistogram`
dataclass exists (`:88-100`) but is **not populated** by the runner — there is
no logic on disk that reads gmsh's per-element quality output and fills the
histogram. ANSYS Meshing, Abaqus CAE, and Siemens NX all ship hex-dominant
meshers, adaptive refinement, prism-layer growth, quality-driven local
remesh, and per-region size controls. Gmsh+wrapper at default `clmax=0.05 m`
gives you a single uniform-density linear-tet mesh — a CFD-style starter,
not an industrial FEA mesh.

**Justification:** 1/10 + a half-step for STEP/STL/BREP/GEO ingestion and
optional quadratic order = 2/10.

### 3. Material library breadth + provenance — **2 / 10**

`backend/app/services/materials/library.json:1-36` ships **3 materials**:
S355 structural steel, Al-6061-T6, Ti-6Al-4V. Each carries Young's modulus,
Poisson's ratio, density, yield, ultimate, and a citation (EN 10025-2:2019 /
MMPDS-2023) — the provenance discipline (`backend/app/services/materials/api.py:100-106`
refuses entries without a `reference` field) is **best-in-class for a library
this size**. But ANSYS Granta MI ships **>500,000 alloys, polymers, composites,
ceramics, foams** with full temperature-dependent property curves;
Abaqus's default library covers ~150 baseline materials plus user-defined
UMATs/VUMATs for arbitrary constitutive models; even the open-source
CalculiX-distribution `ccx_2.X/test/` cases reference >30 materials.
Three room-temperature-only linear-elastic isotropic entries with no
plasticity hardening curves, no temperature dependence, no anisotropy, no
hyperelastic constants, no rate dependence, no fatigue S-N curves, no
fracture-toughness data is **a proof-of-concept slice**.

**Justification:** Strong per-entry discipline + canonical citations pulls
this up from 1/10 to 2/10. The breadth gap is enormous.

### 4. Geometry import — **3 / 10**

The Gmsh subprocess wrapper at
`backend/app/services/meshing/gmsh_runner.py:57-59` accepts STEP, STP, STL,
BREP, GEO. **IGES is not in the accepted-extension set** — a single-line
gap from the user-stated requirement set. There is no native CAD-kernel
parser in this codebase (no python-occ, no pythonocc-core, no Open Cascade
binding) — the harness delegates **everything** to gmsh, including the
boolean/healing/repair operations that Abaqus CAE and ANSYS DesignModeler
ship natively. There is no CAD parameter feedback (the case cannot edit
the source geometry and re-mesh), no assembly-mate import, no part-suppress,
no defeature-by-feature-tree, no mid-surface extraction for shells. The
path-guard (`gmsh_runner.py:226-236`) is correct security-side but is not a
geometry-import capability.

**Justification:** STEP + STL + BREP coverage via a real industrial mesher
is **non-trivial** — that's the half-step above proof-of-concept (3/10
rather than 2/10). IGES missing, no parametric round-trip, no assembly
handling = far from 5/10.

### 5. BC expressiveness — **1 / 10**

The only BC author on disk is `backend/app/adapters/calculix/inp_writer.py:137-145`:
**hardcoded clamp on bottom 4 nodes (DOF 1-3) + nodal `*CLOAD` on top 4 nodes
DOF 3 only.** That's it. There is no API surface for the user to specify
any other BC — no pressure load, no distributed load, no temperature BC,
no displacement BC at arbitrary nodes, no `*EQUATION` constraint, no
`*RIGID BODY`, no `*MPC`, no symmetry BC, no `*BOUNDARY, OP=NEW` step-wise
changes, no follower loads. The grep for `BOUNDARY|CLOAD|DLOAD` across the
backend returns exactly one hit (the minimal hex writer). Every industrial
tool ships dozens of BC types selectable via per-face / per-edge / per-vertex
GUI picking; here you have *one* BC topology and you can only swap the
load magnitude + the cube edge length.

**Justification:** Single canonical case, hardcoded topology = 1/10. The
`inp_writer.py:60-83` signature exposes `top_face_load_n` and `edge_length_m`
as the only knobs — nothing else.

### 6. Contact modeling — **0 / 10**

Zero. There is no `*CONTACT PAIR`, `*SURFACE`, `*SURFACE INTERACTION`,
`*FRICTION`, `*TIE`, `*CONTACT INITIALIZATION`, `*CONTACT FILE` keyword
emitted anywhere in the codebase. The grep across `backend/app/` for any
of these returns nothing. The `reader_handle.py:` Layer-2 type briefly
mentions "contact-pair" in a docstring (`backend/app/core/types/reader_handle.py`)
but that is a forward-looking comment, not a capability. Industrial tools
(ANSYS Mechanical, Abaqus/Standard, Abaqus/Explicit) all ship full Coulomb +
penalty + augmented-Lagrange + tied-surface contact, plus self-contact, plus
general-contact algorithms; CalculiX itself supports `*CONTACT PAIR` natively.
The harness simply does not surface it.

**Justification:** 0/10 = capability isn't there. No partial credit.

### 7. Nonlinear solver capability — **0 / 10**

Zero. The harness writes `*STATIC` with no `NLGEOM=YES`, no `*PLASTIC`,
no `*HYPERELASTIC`, no `*VISCOELASTIC`, no `*CREEP`, no `*DAMAGE`,
no `*INELASTIC HEAT FRACTION`. The minimal inp_writer at
`backend/app/adapters/calculix/inp_writer.py:130-135` emits
`*MATERIAL, NAME=<m>` + `*ELASTIC` + Young/Poisson tuple only — linear
elastic isotropic, period. The legacy `analysis_service.py:_transform_inp`
also emits only `*FREQUENCY` / `*BUCKLE` (both linear analysis classes,
even buckling is **linear** eigenvalue buckling here, not Riks/arc-length
nonlinear post-buckling). No geometric nonlinearity, no material
nonlinearity, no contact nonlinearity. Abaqus/Standard ships all three
plus implicit dynamics, plus Riks; Abaqus/Explicit ships explicit dynamic
nonlinear; ANSYS Mechanical ships all of the above through the workbench.

**Justification:** 0/10. The capability is absent.

### 8. Result post-processing — **3 / 10**

This is the **strongest non-discipline dimension** by far. The `.frd`
parser at `backend/app/parsers/frd_parser.py:31-58` extracts displacement,
the full stress tensor (S11/S22/S33/S12/S13/S23), all 3 principal stresses,
and von Mises **per node**. The Layer-1 adapter at
`backend/app/adapters/calculix/reader.py:1-80` wraps that parser into the
`ReaderHandle` Protocol with explicit unit-system discipline (ADR-003 — units
are NEVER inferred). The `domain/modal_extraction.py:1-43` module pulls
eigenfrequencies + participation factors + effective modal mass out of
`.dat` files and even runs an Euler-Bernoulli analytical cross-check.
`backend/app/viz/vtu_exporter.py` produces a VTU file consumable by ParaView /
Trame / web-side viewports, and `backend/app/viz/animation_manifest.py`
exposes step-wise replay. **However**: there is no safety-factor field
computation (yield/ultimate ratio surfaced as a contour), no stress
linearization on user-picked SCLs (the `domain/stress_linearization/`
package is an empty `__init__.py` + `__pycache__`), no fatigue post-processing,
no shell-bending separation, no probe-along-path, no XYZ-result-history
plotting. CalculiX's own cgx prepost gives more interactive features for free.

**Justification:** Real .frd parsing + numpy field outputs + ADR-003 unit
discipline + VTU export + animation manifest = a credible 3/10 — well above
"single hardcoded canonical case", but far below industrial post-processing
that ships path operations, sub-modeling cuts, fatigue-Goodman lookup,
safety-factor contours, custom-result derived fields, and the
deformed-mesh-with-vector-overlay views that Abaqus Viewer / Mechanical /
ANSYS CFD-Post all ship out of the box.

### 9. Analytical cross-check infrastructure — **6 / 10**

**This is where the harness is strongest relative to its mandate.**
ADR-025 (`docs/adr/ADR-025-tier2-transition.md:50-106`) defines the
Tier 1 → Tier 2 transition with a **tier-scoped forbidden-token policy**
(`backend/app/services/reporting/_forbidden_tokens.py:35-94`) that
*explicitly* separates "advisor authority" (5 tokens always refused) from
"solver evidence" (4 tokens allowed only on `tier_2_validated` envelopes
that cite an analytical cross-check verdict). The
`CLAIM_TIER_REGISTRY` SSOT at
`backend/app/services/reporting/_claim_tier.py:75-81` is **one place** that
maps `case_id → tier`, gated by code-edit-only promotion via
`register_tier_2_validated()` (`:126-145`) — no runtime API to silently
upgrade a case. The `build_gate_audit_record` reporting-only sibling at
`backend/app/services/reporting/gate_audit.py:64-118` separates audit metadata
from hard-refusal flow per ADR-025 §2.2. The pre-existing
`backend/app/domain/modal_extraction.py:1-43` carries the Euler-Bernoulli
closed-form cantilever solution + residual report + pinned tolerance
(MODAL_CROSS_CHECK_TOLERANCE_PCT). **No industrial tool ships this layer**
because no industrial tool has to defend a Tier 1 → Tier 2 boundary —
they sell themselves as Tier-2-implicit.

**Justification:** 6/10 because the **policy + SSOT + tier-scoped token
audit + gate-audit-record sibling + analytical cross-check module** is
a defensible and well-thought architectural slice. Not 8/10 because
the only analytical solution coded is Euler-Bernoulli cantilever modal —
no thin-cylinder hoop stress yet, no beam-deflection, no plate-bending,
no Lamé equation for thick cylinders, no stress concentration factors
(Pilkey). Not 10/10 because the registry is still empty of
`tier_2_validated` entries (every cohort case stays `tier_1_candidate`
at `_claim_tier.py:75-81`) — the discipline is in place but no case has
actually passed through it yet.

### 10. Documentation + ADR coverage — **7 / 10**

**The documentation discipline is excellent for a harness this size.**
15 ADRs (`docs/adr/ADR-011..ADR-025`) plus an RFC chain
(`docs/RFC-001-strategic-pivot-and-mvp.md`,
`docs/RFC-002-multi-solver-workbench-retrospective.md`), an architecture
doc (`docs/architecture.md`), a Phase 18 blueprint
(`.planning/FM-04A_PHASE18_BLUEPRINT.md` — 120+ lines just in the part I
read), and sprint-level retrospectives. Every Python file in
Phase 18 A/B/C ships a module-level docstring **citing the ADR** + the
RFC clause + the anti-gaming rubric position. Example:
`backend/app/adapters/calculix/runner.py:1-35` enumerates the RFC-001 §4.5
layer split, the HF1.7a defense, the bounded-timeout rationale, the
stdout-tail capture contract — **before any code**. Inline docstrings
on dataclasses are full Args/Returns/Raises (e.g.,
`runner.py:CalculiXRunResult:88-110`, `inp_writer.py:write_minimal_hex_inp:61-83`,
`gmsh_runner.py:GmshRunner.run:156-185`). **However**: no end-user-facing
*operator's manual* (no "how to set up a contact pair" guide because no
contact pair exists), no theory manual (CalculiX has one; ANSYS has the
canonical Theory Reference; Abaqus has the legendary Theory & User
manuals), no verification-suite documentation (NAFEMS benchmark set),
no validation report on a real geometry yet.

**Justification:** Excellent internal architectural ADR/RFC discipline
(7/10), let down by absence of the user-facing theory + verification
manuals that industrial tools ship as a hard requirement. Note: this is
the **only** dimension where the harness rivals industrial-tool quality.

---

## Top 3 capability gaps (most expensive to industrial users)

### Gap 1 — Nonlinear solver + contact (dimensions 6 + 7, currently 0 + 0)
**No real industrial FEA work product can be delivered without at least one
of:** geometric nonlinearity (NLGEOM), material plasticity (Ramberg-Osgood
or piecewise-linear hardening), or contact pairs (frictional / frictionless /
tied). Pressure vessels need *elastic-plastic + contact at the bolted
flange + buckling check post-yield*. Aerospace brackets need *plasticity +
contact at the fastener interface + fatigue post-processing*. The
single linear-elastic linear-static slice the harness can run today
covers <5% of real-world FEA workload. This gap blocks every
production case the user would actually want to certify.

### Gap 2 — BC expressiveness + analysis-type breadth (dimensions 5 + 1, currently 1 + 2)
The harness can declare ONE BC topology (clamped-bottom + Z-load-top) on
ONE geometry (a hex cube) running ONE analysis type (linear static).
Industrial tools provide a BC palette: pressure on a face, displacement
on a face, prescribed temperature, bolt preload, distributed coupling,
remote force, gravity, centrifugal, prescribed velocity (for dynamics),
acoustic pressure. **Without a BC expressiveness layer the harness
cannot model anything other than the toy cube.** This is structurally
prior to closing Gap 1 — you can't add nonlinearity to a model whose only
BC author hardcodes 8 nodes.

### Gap 3 — Material library breadth + temperature dependence (dimension 3, currently 2)
Three room-temperature-only isotropic linear-elastic materials covers
< 0.1% of an industrial alloy/polymer/composite catalog. There is no
temperature-dependent elasticity, no stress-strain hardening curve, no
anisotropy (composites), no creep coefficient, no thermal conductivity,
no thermal expansion coefficient — without these, *any* coupled thermal-
mechanical analysis is impossible. Industrial tools ship 100-500+ default
materials; ANSYS Granta MI ships 500K+. The materials discipline
(citations, JSON SSOT, refuse-on-missing-reference) is solid — it just
needs ~50× more entries with multi-axis properties.

---

## Phase 19+ scope recommendations to close the largest gaps

**Phase 19 — BC palette layer.** Build an `inp_writer_extended.py` (sibling
to `inp_writer.py`, NOT a replacement — Phase 18 A's minimal-hex remains a
smoke fixture forever) that accepts a structured `BoundaryConditions`
DTO carrying lists of `(node_set | face_id, dof, value)` tuples and emits
`*BOUNDARY`, `*CLOAD`, `*DLOAD` (pressure), `*DSLOAD` (face pressure),
and `*DFLUX` (heat flux). Add `NodeSet` / `ElementSet` / `SurfaceSet`
authoring helpers (CalculiX `*NSET`, `*ELSET`, `*SURFACE`). Score Δ on
dim 5: 1 → 5.

**Phase 20 — Analytical cross-check library.** Extend the
`domain/stress_linearization/` empty package with: thin-cylinder hoop
stress (Lamé), thick-cylinder Lamé, beam-bending closed-form (cantilever,
simply-supported), plate-bending Timoshenko, stress-concentration-factor
Pilkey tables, and the analytical solutions Phase 18 promised but didn't
land. Each is < 50 LOC of pure-Python math. Add one
`tier_2_validated` flip per analytical-evidence case. Score Δ on
dim 9: 6 → 8.5.

**Phase 21 — Modal/buckling first-class.** Rebuild the legacy
`analysis_service.py` string-mutation as a proper `inp_writer_modal.py` +
`inp_writer_buckling.py` that author the INPs from clean DTOs (not by
splitting on `*STEP`). Add a `tier_2_validated` analytical cross-check
on first-mode frequency (the Euler-Bernoulli code is already present).
Score Δ on dim 1: 2 → 4.

**Phase 22 — Material library expansion.** Add a `library_extended.json`
with at least: 5 more steels (S235 / S275 / S420 / S460 / 304L stainless),
5 more aluminums (2024-T3 / 7075-T6 / 5083 / 6063 / Al-Li 2099), 3
plastics (PEEK / PA66 / ABS), 3 composites (T300/5208 / IM7/8552 / Kevlar
49). Add temperature-dependent E(T) tables for the 3 incumbent metals.
Citation discipline carries forward unchanged. Score Δ on dim 3: 2 → 4.

**Phase 23 — Contact (smallest viable slice).** Add a `*TIE` constraint
authoring helper to bind two surfaces — this is the **simplest** contact
class (rigid bond, no friction, no sliding) and unblocks assembly
modeling without the implementation cost of true frictional contact.
Frictional `*CONTACT PAIR` slots into Phase 24+. Score Δ on dim 6:
0 → 2.

**Phase 24+ — Nonlinear (NLGEOM + *PLASTIC).** This is the largest
single capability gap and probably warrants its own multi-phase
sub-program (mirror what Phase 18 did for "real solver"). Beyond Phase 19
scope.

**Targeted composite trajectory:** Phase 19+20+21+22+23 lifts the harness
from 32 → ~50-55, *if* every phase lands clean. That puts the harness at
"minimum viable production state" (5/10 across the board for the basic
dimensions) which is where most internal-to-company FEA tools live.
Industrial-tool parity (composite ≥ 80) is a 12-18 month roadmap minimum.

---

## Honest disclosure

**What I did not test:**
* I did not run `ccx` end-to-end on the minimal hex INP. The runner exists
  and looks correct; tests under `@pytest.mark.requires_solver` exist but
  I did not invoke them (Phase 18 A's deliverable is that those tests
  pass on a dev box with ccx installed; my mandate is capability scoring,
  not test execution).
* I did not exercise the gmsh subprocess on a real STEP file. The runner
  looks correct; the `MeshQualityHistogram` dataclass is present but
  unpopulated by the runner code I read — I did not search for an external
  populator.
* I did not validate the analytical cross-check claims by running them
  against the cylinder-pv-candidate cohort.
* I did not benchmark performance — wall-clock per element, memory
  footprint, parallel scaling — because these are not in the score axes.

**Assumptions I made:**
* "Industrial FEA toolstack" = the canonical big four (ANSYS Mechanical /
  Abaqus / NASTRAN / Siemens NX Nastran). I scored CalculiX-as-packaged-
  product (e.g., PrePoMax) somewhere between 6/10 and 8/10 on each axis
  as a calibration point.
* The legacy `analysis_service.py:_transform_inp` modal/buckling path is
  pre-Phase-18 code and not part of the Phase 18 scope. I counted it for
  solver-coverage dimension (still gives 2/10 not 1/10) but did not assume
  it has Phase 18 test coverage.
* The `claim_tier_2_validated` flip for cylinder-pv-candidate has NOT
  yet happened on disk (registry shows all 5 candidates still
  `tier_1_candidate` at `_claim_tier.py:75-81`). Phase 18 A's blueprint
  promises the flip after end-to-end ccx success; that has not landed in
  the file state I read.

**What would change my score:**
* +5 composite if an actual production cohort case (cylinder-pv-candidate)
  has flipped to `tier_2_validated` with a real analytical cross-check
  attached to the envelope.
* +3 on dim 5 (BC expressiveness) if a `BoundaryConditions` DTO surfaces
  with even 3-4 BC types beyond clamped-+-cload.
* +2 on dim 3 (materials) if the library has ≥ 15 entries with at least
  one carrying a temperature-dependent E(T) curve.
* -2 on dim 9 if I discover the `_forbidden_tokens.py` policy is not
  actually wired into any envelope-producing path (i.e., consumers still
  hardcode the old 9-token check inline).
* -3 on dim 10 if the Phase 18 ADR-025 has not yet been referenced from
  any other ADR / RFC / blueprint (currently it self-references its own
  cross-references at `:210-219` but I did not verify reverse linkage).

**Tone caveat:** the engineering quality of what Phase 18 A/B/C **did**
land is genuinely good — clean layer split, ADR-025 is a defensible
piece of architecture, the materials JSON discipline is best-in-class for
its size, the docstrings consistently cite RFC + ADR + rubric anchors.
The 32/100 score reflects the **gap to the full industrial toolstack**,
which the user explicitly asked me to score against. A score against
"first viable Tier 2 milestone of a months-long transition" would be
materially higher (~ 70-75). The two scores measure different things;
the user picked the harder one.
