---
id: FP-003
status: applied
created: 2026-04-25
related_gs: [GS-003]
related_adr: [ADR-011]
classification: geometry_invalid
blocks: [Phase-2-activation, FF-02]
owner: claude-code-takeover
schema_version: 1
gs_artifact_pin:
  expected_results_version: "1.0"
  inp_sha: "n/a (working tree)"
  readme_sha: "n/a (working tree)"
---

# FP-003: GS-003 has no hole in the mesh and the prescribed displacement direction contradicts the case description

## Observed deviation

README (`golden_samples/GS-003/README.md:7-21, 96-99`) and `expected_results.json:7-22, 73-79` describe a 100×200 mm plate with a 20 mm central hole, expecting Peterson stress-concentration factor `K_t ≈ 2.506` and `σ_max ≈ 1315.73 MPa` (`expected_results.json:48-53`).

`gs003.inp:11-27` defines a uniform **3-column × 5-row grid of 15 nodes** with **8 CPS4R quads tiling the full rectangle** — **no hole node has been removed, no element has been deleted around node 5** (which sits where the hole center should be). A stress-concentration factor cannot exist in a geometry without the concentration feature.

**Secondary defect** — the README diagram (`README.md:9-21`) shows a horizontal arrow on the right edge labeled `Δ=0.5 mm` suggesting horizontal tension, while the theory section (`README.md:51-55`) computes strain `ε = Δ/H` using the **vertical** dimension H=200. The `.inp` then applies `UX=0.5 mm` to the **top edge** (y=200, nodes 13-15; `gs003.inp:58-61`) — i.e., horizontal displacement on a horizontal edge whose other edge constrains UY only (`gs003.inp:51-54`). Result: a shear-dominated, asymmetrically-loaded patch — neither uniaxial-tension-with-hole (the theory) nor the picture in the README.

## Hypothesized root causes (ranked)

1. **Mesh authored without geometric hole feature** *(very high confidence)*. The 15-node lattice is a placeholder; either the geometry pipeline (FreeCAD/Gmsh) was never run for this case, or the author drafted the `.inp` by hand and forgot to subtract the hole. `expected_results.json:78` notes "粗网格简化的带孔板" — but a coarse-with-hole still requires removing the central element, which has not occurred.

2. **Displacement BC direction selected without rechecking the figure** *(high)*. The intent appears to be vertical tension UY=0.5 on top edge with UX free; the actual BC swaps roles. Strain calculation in `plane_stress_theory.py:104` and `expected_results.json:33-39` assumes `ε = Δ/H`, which is only valid if the displacement and H are along the same axis.

3. **Theory vs FEA comparison is structurally infeasible** *(high)*. With no hole, `K_t = 1` trivially; FEA `σ_max` from this `.inp` cannot validate the `K_t = 2.506` claim no matter how it is run.

## Evidence

- `golden_samples/GS-003/README.md:9-21, 51-55, 96-103`
- `golden_samples/GS-003/expected_results.json:7-22, 33-79, 78`
- `golden_samples/GS-003/gs003.inp:11-27, 30-38, 51-54, 58-61`
- `golden_samples/GS-003/plane_stress_theory.py:104, 110-113`

## Recommended action

**All SHORT-TERM and ARCHITECTURAL items below are *hypotheses pending GS-revalidation* per ADR-011 §HF3.** A FailurePattern's authority is limited to attribution and to the IMMEDIATE governance status update; the listed paths/ADRs must be re-validated (hot-smoke + review) before any code or schema action is taken.

### IMMEDIATE
- Mark GS-003 status `insufficient_evidence` in Notion control plane. **Per ADR-011 §HF3, this case has no defensible GS reference: the `.inp` mesh has no hole feature so a `K_t ≈ 2.506` Peterson reference cannot be validated against this geometry, irrespective of solver behavior.**
- Pin current `expected_results.json` metadata version in the `gs_artifact_pin` frontmatter (now pinned to `"1.0"`).
- Cross-link FP-003 from ADR-011 consequences.

### SHORT-TERM (≤ 2 weeks) — *hypotheses, require GS-revalidation*
- Regenerate `gs003.inp` from a parametric geometry source that actually contains the hole (refined mesh ≥ ~200 elements with biased seeding around the hole edge).
- Correct the BCs to: `UY = 0.5` on top edge (y=200), `UY = 0` on bottom edge (y=0), `UX` free except at one anchor node.
- Rerun CalculiX; recompute `K_t` from peak SXX at the hole edge; compare against `plane_stress_theory.py` Peterson curve.

### ARCHITECTURAL
- Reinforces a future ADR (number TBD; was "ADR-012 (proposed)" in earlier draft, reassigned per AR-2026-04-25-001): **"Golden-sample triplet contract"** — a triplet-validation gate should reject any GS where the README diagram axis disagrees with the `.inp` BC axis.
- Reinforces a future ADR (number TBD; was "ADR-013 (proposed)" in earlier draft, reassigned): **"Comparison-validity precondition"** — the router should refuse to claim `REFERENCE_MISMATCH` against a Peterson `K_t` reference when the FEA mesh has no concentration feature.

## Open questions

- Was an earlier `.inp` for this case ever generated with a hole, and overwritten by the current placeholder? Check git history of `gs003.inp` if it exists in any prior branch.
- The README diagram appears to have been authored independently from the `.inp` — what was the source of truth at authoring time?
