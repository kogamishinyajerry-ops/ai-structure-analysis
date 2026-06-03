# NAFEMS LE10 — Thick Plate Pressure (real ccx benchmark agreement)

> **Tier 2 real-solver validated · PUBLIC-BENCHMARK AGREEMENT (NAFEMS LE10).**
> NOT signed validation (no independent reviewer signoff per ADR-023 Tier-2-signed
> / ADR-027 G-2). Real ccx 2.23 solve; sign normalized to the solver convention.

## What this case is (V2-1 / ADR-027, 2026-06-03)

This is the project's **first genuine public-benchmark agreement** — every other
`tier_2_validated` case is a real-ccx cross-check against an *analytical closed
form*; this one compares a real ccx solve against the **published NAFEMS LE10
reference value** σ_yy(D) = −5.38 MPa.

**Result:** real ccx 2.23, full-integration **C3D20**, 40×20×6 (4800 el) →
**σ_yy(D) = −5.4379 MPa, residual +1.08%** vs the published −5.38 MPa (tolerance
3%) → **PASS**, with **monotone mesh convergence**. Reproduce:
`python data/generator.py [--ladder]`. Artifacts: `cross_check_verdict.yaml`
(verdict), `convergence_study.json` (ladder), `published_reference.yaml`
(the published target).

### Convergence (monotone, from above)

| mesh (nc×nr×nt) | C3D20 el | σ_yy(D) MPa | residual |
|---|---|---|---|
| 12×6×3 | 216 | −5.567 | +3.47% |
| 16×8×4 | 512 | −5.526 | +2.72% |
| 24×12×4 | 1152 | −5.511 | +2.43% |
| 32×16×5 | 2560 | −5.479 | +1.84% |
| **40×20×6** | **4800** | **−5.4379** | **+1.08%** |

Full-integration C3D20 was chosen over reduced-integration C3D20R, which was
noisier at this sharp inner-edge stress (+2.11 / +0.65 / +1.80 / +2.05% — non-
monotonic). Coarser meshes (<216 el) are non-monotonic coarse-mesh artifacts and
are excluded from the convergence branch.

## Benchmark definition (NAFEMS LE10 — triangulated 2026-06-03)

| Property | Value | Provenance |
|---|---|---|
| Target | σ_yy = **−5.38 MPa** (compressive) at point D | magnitude unanimous across 6+ CAE sources; sign per FeenoX/Code_Aster + ccx |
| **Point D** | **(2.0, 0, +0.3) m — UPPER surface**, inner-ellipse MAJOR-axis tip on the y=0 plane | FeenoX evaluates `sigmay(2000,0,+300)` |
| Material | E = 210 GPa, ν = 0.3, ρ = 7800 kg/m³ | confirmed |
| Load | uniform normal pressure 1.0 MPa on the UPPER surface (downward) | confirmed |
| BC | ux=0 (ABA'B', x=0); uy=0 (DCD'C', y=0); ux=uy=0 (BCB'C' outer rim); uz=0 (line EE'/outer-rim mid-plane) | confirmed |
| Geometry | outer ellipse 3.25×2.75 m, inner ellipse 2.0×1.0 m, t=0.6 m, quarter, full thickness | confirmed |

### ⚠️ Correction of a prior error in this case's own records (honesty)

The earlier `published_reference.yaml` / `NOTES.md` stated point D was on the
**"lower surface, … on the minor axis"**. **Both were WRONG.** The 2026-06-03
multi-source triangulation (FeenoX/Code_Aster, ESRD StressCheck Benchmarks Guide,
Abaqus/Altair) established that D is on the **UPPER (loaded) surface** and is the
inner-ellipse **MAJOR-semi-axis tip (x=2.0) lying on the y=0 symmetry plane**
(it merely *lies on* the plane perpendicular to the minor axis). FeenoX evaluates
`sigmay(2000,0,+300)` = the upper extruded face; the lower twin D'=(2,0,−0.3) is a
different value. This case's prior records carried the error precisely because the
geometry had **never been verified against an authoritative source** — which the
file itself flagged. V2-1 verified it, found and fixed the error, and built on the
corrected point.

### Sign caveat (disclosed)

The **magnitude** 5.38 MPa is unanimous and community-canonical. The **sign** is
convention-split in the literature: FeenoX/Code_Aster report it SIGNED as −5.38 MPa
(compressive); several CAE docs (Abaqus/Altair/SimScale/ESRD-as-magnitude) report
the magnitude 5.38 MPa, some reading it tensile at the "inside top corner" — a
stress-orientation / surface-labeling convention artifact, not a physics dispute.
ccx (tension-positive, like Code_Aster) reproduced **−5.4379 MPa (negative)**,
matching the FeenoX −5.38 MPa convention. The residual is computed signed vs
−5.38 MPa; the agreement holds in both magnitude (+1.08%) and sign (compressive in
the ccx convention). The primary NAFEMS TNSB Rev.3 document was **not directly
fetched**; geometry and sign rest on the authoritative secondary reproductions
below.

## Bibliography

- **NAFEMS Publication TNSB Rev.3**, "The Standard NAFEMS Benchmarks", October 1990,
  ISBN 1-874376-04-0 — primary source; σ_yy = −5.38 MPa at point D. (Cited, not
  directly fetched.)
- **FeenoX / Code_Aster** parametric LE10 (seamplex.com/feenox; runnable `.comm` +
  `nafems-le10-cad.geo`) — evaluates `sigmay(2000,0,300)` = −5.38 MPa. Primary
  geometry/point/sign anchor.
- **ESRD StressCheck** "Standard NAFEMS Benchmarks: Linear Elastic Tests" guide —
  "Direct stress in y-direction at point D is −5.38 MPa".
- **Abaqus Benchmarks Guide** LE10 + **Altair OptiStruct** OS-V:0060 + **SimScale**
  thick-plate validation — material, load, BC, target magnitude (mind the
  surface/sign convention split above).
