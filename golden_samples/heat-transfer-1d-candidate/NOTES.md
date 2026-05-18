# heat-transfer-1d-candidate — FM-04a Phase 31 A

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement.

## Documented pivot from Phase 31 blueprint Slice A

The Phase 31 blueprint (`acce14c`) scoped this slice as a `*CONTACT
PAIR` Hertz contact case. During reconnaissance the contact setup
proved structurally complex:

* CCX `*SURFACE, TYPE=...` does not support analytical sphere /
  cylinder surfaces — both bodies must be meshed.
* A rigid indenter requires either `*RIGID BODY` + reference-node
  bookkeeping OR a much-stiffer second elastic body as a shim.
* Contact-output reading (CDIS / CSTR fields) is NOT in the
  existing `reader.py` field-code table; the canonical-field enum
  is ADR-002-locked at 6 members and expanding it requires an RFC.

To preserve the Phase 30 A risk-reduction lesson ("prefer cases
with KNOWN-SAFE pitfalls") and to ship a reliable Slice A within
the phase budget, the slice pivoted to a `*HEAT TRANSFER,
STEADY STATE` cross-check.

**The contact case is NOT lost — it moves to Phase 32** per the
blueprint Phase 32 forward look. The honest argument: heat
transfer and contact pair both close +5-8 single-axis FEA lifts;
shipping the lower-risk one first is the same call Phase 30 D
made when it deferred cylinder-pv convergence with a regression-
pin test rather than fabricating a stub.

## What this case validates

**The first `*HEAT TRANSFER` (steady-state heat conduction)
validated case in the cohort.** Adds a new solver-kind axis
beyond the static/buckle/frequency/dynamic-implicit set Phase 19-30
already cover.

## Cross-validation logic

1D linear steady-state heat conduction through a uniform rectangular
bar with prescribed end-face temperatures and insulated lateral
surfaces. The governing PDE (with no volumetric source and constant
isotropic conductivity) reduces to:

```
d²T/dx² = 0
```

with the linear closed-form solution:

```
T(x) = T_left + (T_right - T_left) · x / L
```

**Crucially, T(x) is INDEPENDENT of k**, the thermal conductivity.
Conductivity affects only the heat flux Q = -k · dT/dx, not the
temperature field. This is why the slice can use a hardcoded
k = 50 W/(m·K) (textbook S355 value) without extending the
material SSOT — the cross-check residual is k-invariant.

## Configuration

- **Geometry**: 0.100 m × 0.020 m × 0.020 m steel bar (L × h × w).
- **Material**: steel-s355 from SSOT library (E + ν + ρ taken
  from SSOT; conductivity hardcoded at 50 W/(m·K) per the
  k-invariance note above; documented in
  `heat_transfer_runner.py` HEAT_TRANSFER_DEFAULT_CONDUCTIVITY_W_MK
  constant).
- **Mesh**: hand-rolled structured 10 × 2 × 2 = 40 C3D8 hex
  elements (99 nodes). No gmsh dependency.
- **BC**: T_left = 373.15 K (= 100 °C) on x=0 face;
  T_right = 273.15 K (= 0 °C) on x=L face. DOF 11 (temperature)
  is fixed on every node of those two faces. Lateral surfaces
  are NOT constrained → insulated by default (zero heat flux).
- **Initial conditions**: T = 293.15 K everywhere (CCX requires
  an initial temperature for the temperature DOF, even in
  steady-state).
- **Solver**: `*HEAT TRANSFER, STEADY STATE` (no transient
  time-integration). Output via `*NODE PRINT, NSET=ALL_NODES; NT`
  → .dat plain-text table.

## Result (live ccx 2.23 · 2026-05-18)

| Quantity | Value |
|---|---|
| midplane node id | 6 |
| midplane node x | 0.050000 m (exactly L/2) |
| analytical T(L/2) | 323.150000 K |
| observed T(L/2) | 323.150000 K |
| residual | **+0.000000%** |
| verdict | **PASS** (envelope ±1%) |
| n_nodes | 99 |
| n_elements | 40 (C3D8) |

## Why the residual is essentially zero

C3D8 (8-node trilinear hex) shape functions can represent a
function that is linear in each Cartesian direction **exactly**.
The analytical T(x) is linear in x and uniform in y, z — so the
finite-element discretization reproduces it node-for-node without
any discretization error. The observed residual at 6 significant
figures is exactly 0.

The 1% tolerance envelope is generous because:
1. ASCII precision of the .dat output (CCX writes ~5 significant
   figures, e.g. `3.731500E+02`) could in principle inject tiny
   numerical noise — observed: none at this configuration.
2. Future configurations with non-linear analytical (heat source,
   temperature-dependent conductivity) would benefit from the
   envelope.

## What this case does NOT validate

- Transient heat conduction (`*HEAT TRANSFER` without STEADY
  STATE).
- Volumetric heat sources (`*DFLUX`).
- Surface convection / radiation (`*FILM`, `*RADIATE`).
- Coupled temperature-displacement (`*COUPLED TEMPERATURE-
  DISPLACEMENT` step) — separate solver path; deferred to a
  later phase.
- Temperature-dependent material properties.
- Heat flux Q at boundary surfaces — would need k-coupled
  validation and an extended SSOT.

These are deferred to future phases. The validated claim is
narrow: **uniform 1D conduction with prescribed end-face
temperatures, insulated sides, room-temperature steel, C3D8
hex mesh** — reproduces the linear analytical T(x) to within
0.000% at the midplane probe.

## Anti-gaming guards

- **A:-1**: midplane T compared against analytical at the SAME
  exact x-coordinate (no interpolation to a "nearest" node that
  could pad the residual).
- **B:-1**: k = 50 W/(m·K) hardcoded in
  `heat_transfer_runner.py` with a comment documenting
  k-invariance of the residual. NOT a parallel material SSOT.
- **D:-3**: analytical helper SSOT-pinned in
  `heat_transfer_1d.py`; runner and tests reuse it verbatim;
  no parallel re-definition of the formula.
- **E:-1**: BC temperature spread pinned at 100 K (373.15 →
  273.15 K) so the residual denominator has a clean value.
- **C:-1**: NSET names (`LEFT`, `RIGHT`, `ALL_NODES`) are pure
  identifiers; the INP composer builds them deterministically
  from the structured mesh.

## Files

- Runner: `backend/app/services/cross_check/heat_transfer_runner.py`
- Analytical: `backend/app/services/cross_check/heat_transfer_1d.py`
- Tests: `backend/tests/test_phase31a_heat_transfer.py`
- Verdict: `golden_samples/heat-transfer-1d-candidate/cross_check_verdict.yaml` (schema 1.3.0)
- INP snapshot: `golden_samples/heat-transfer-1d-candidate/data/heat_transfer_xcheck.inp`

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
