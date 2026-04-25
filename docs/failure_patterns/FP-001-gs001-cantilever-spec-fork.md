---
id: FP-001
status: proposed
created: 2026-04-25
related_gs: [GS-001]
related_adr: [ADR-011]
classification: reference_mismatch
blocks: [Phase-2-activation, FF-02]
owner: claude-code-takeover
schema_version: 1
gs_artifact_pin:
  expected_results_version: "3.0"
  inp_sha: "n/a (working tree)"
  readme_sha: "n/a (working tree)"
---

# FP-001: Cantilever GS theory↔FEA gap is unresolvable as configured; spec carries three versions of the case

## Observed deviation

UY ratio FEA/theory = **648×** (`golden_samples/GS-001/expected_results.json:117`); SXX ratio = 0.79 (`expected_results.json:122-126`). The README declares FEA the baseline ("以FEA结果作为本案例的验证基准", `golden_samples/GS-001/README.md:96-97`, repeated `:208-211`), while the same directory's `expected_results.json:108-141` declares the case **`FAILED - SIGNIFICANT ERROR DETECTED`**. Both verdicts cannot be simultaneously correct; the case is in conflict with itself.

## Hypothesized root causes (ranked)

1. **Unit-system inconsistency between authoring layers** *(highest confidence)*. `README.md:14-18` claims `L=100 m, b×h=10 m × 10 m, I=833.33 m⁴`. `expected_results.json:11-18, 177-201` declares `mm-N-MPa, L=100 mm, h=10 mm, I=833.33 mm⁴`. `gs001.inp:6-50` lists nodes with bare numbers (0.0–100.0); CalculiX is unitless and interprets per material card. Material is `210000.0` (`gs001.inp:67-68`), only consistent with **MPa+mm**. The README's "100 m beam under 400 N" interpretation is therefore physically wrong. The `expected_results.json:262-266` history (v1→v2→v3) shows this as a still-unresolved fork.

2. **Beam-theory comparison is invalid for this mesh regardless of units** *(medium confidence)*. 10× C3D8 elements over `L/h = 10` is a deep stubby block, not an Euler-Bernoulli candidate (`README.md:128`). Even with consistent mm-N-MPa, a B31 beam reference run would be the right comparator. The README's defense ("以FEA作为本案例的验证基准") is post-hoc re-baselining, not a validation criterion.

3. **`*SOLID SECTION 10.0, 10.0` is a CalculiX no-op for C3D8** *(supporting)*. `gs001.inp:71-72` and `expected_results.json:158-162` show two parameters the solver ignores for solid elements — they only document intent. Some authoring tool likely round-tripped a `*BEAM SECTION` into `*SOLID SECTION` and dropped the cross-section semantics.

## Evidence

- `golden_samples/GS-001/README.md:14-18, 96-97, 117-119, 208-211, 222-223`
- `golden_samples/GS-001/expected_results.json:108-141, 158-162, 209-219, 256-266`
- `golden_samples/GS-001/gs001.inp:6-50, 53-63, 67-72`
- `golden_samples/GS-001/cantilever_theory.py` — uses SI (L=100 m, E=210e9 Pa); disagrees with both README and JSON

## Reading of the README vs JSON conflict

**Observed:** README v2 (2026-04-09) updated the case to "cantilever" but kept v1's unit assumption (meters). JSON v3 corrected units to mm but concluded the *model* is broken. The two artifacts therefore disagree on whether the FEA model is broken or the comparison reference is broken.

**Hypothesis (NOT verified in present working tree):** if rerun under the mm-N-MPa unit convention declared in JSON v3, the 3D-solid FEA model *may* produce a defensible bending result while the Euler-Bernoulli comparison would still be inappropriate (slenderness L/h = 10 places it at the thin-beam boundary). This hypothesis requires a hot-smoke ccx run + manual cross-check before being treated as fact; it is *not* asserted here.

Per ADR-011 §HF3, with two mutually-incompatible artifacts and no externally-defensible reference, this case has **no defensible GS reference** → status should be **`insufficient_evidence`**, not `pending_review`.

## Recommended action

**All SHORT-TERM and ARCHITECTURAL items below are *hypotheses pending GS-revalidation* per ADR-011 §HF3.** A FailurePattern's authority is limited to attribution and to the IMMEDIATE governance status update; the listed paths/ADRs must be re-validated (hot-smoke + review) before any code or schema action is taken.

### IMMEDIATE
- Mark GS-001 as `insufficient_evidence` in the Notion control plane (do **not** edit `golden_samples/**` per HF1).
- Add this FP-001 link to ADR-011's consequences section.
- Pin `expected_results.json:258` `version: "3.0"` in the `gs_artifact_pin` frontmatter so future drift is detectable.

### SHORT-TERM (≤ 2 weeks)
- Choose one of two paths and document in a follow-up ADR:
  - **Path A**: Re-author `gs001.inp` with B31 beam elements; rerun CalculiX; theory comparison becomes valid.
  - **Path B**: Reclassify GS-001 as a *parser/IO regression fixture* (no theory comparison, validation = "FRD parses cleanly + node coordinates / element table round-trip").

### ARCHITECTURAL
- This case + GS-002 + GS-003 jointly motivate a future ADR (number TBD; was "ADR-012" in earlier draft but ADR-012 has been reassigned to calibration cap per AR-2026-04-25-001): **"Golden-sample triplet contract"** — SHA-pinned README + schema-validated `expected_results.json` + theory script as the single calculator.
- Also motivates a future ADR (number TBD; was "ADR-013" in earlier draft, reassigned to branch protection): **"Comparison-validity precondition for `REFERENCE_MISMATCH` retry routing"** — refuse re-dispatch when reference physics class ≠ FEA physics class.

## Open questions

- Is GS-001's intent in the project plan (Notion PRD v0.2) actually beam validation, or is it a 3D-solid validation that was mislabeled? Resolving this picks Path A vs Path B.
- Are there CI tests that currently consume `expected_results.json` numerical values? If yes, they need updating in lockstep with the path decision.
