---
id: FP-002
status: proposed
created: 2026-04-25
related_gs: [GS-002]
related_adr: [ADR-011]
classification: reference_mismatch
blocks: [Phase-2-activation, FF-02]
owner: claude-code-takeover
schema_version: 1
gs_artifact_pin:
  expected_results_version: "1.0"
  inp_sha: "n/a (working tree)"
  readme_sha: "n/a (working tree)"
---

# FP-002: GS-002 advertises a truss but ships beam elements; theoretical and FEA quantities are comparing different physics

## Observed deviation

README and `expected_results.json` consistently describe a 3-bar truss with T3D2 elements (`golden_samples/GS-002/README.md:142-146`; `golden_samples/GS-002/expected_results.json:88-89` says `"element_type": "T3D2"`). The actual `.inp` declares `*ELEMENT, TYPE=B31` (`golden_samples/GS-002/gs002.inp:12`) — Euler-Bernoulli beam-in-3D. `gs002.inp:1-3` even admits this in a comment: *"Static Analysis - Using Beam Elements to Simulate Truss"*.

Truss theory (axial-only, pin-jointed) and B31 (rotational DOFs at every node) yield different reactions in a 3-bar triangle once node 1 has all 6 DOFs fixed (`gs002.inp:30`). Theory expects 577.35 N axial force in each member (`expected_results.json:46-58`; `truss_theory.py:286`); B31 with the actual BCs distributes load partly through bending.

## Hypothesized root causes (ranked)

1. **Element-type substitution to work around CalculiX limitations** *(high confidence)*. CalculiX's T3D2 has restrictions on combination with point loads / BCs in some versions; the `.inp` author swapped to B31. The `expected_results.json` was never updated — `tags: ["truss", "validation"]` (`expected_results.json:145`) and `element_type: T3D2` (`:88`) still claim truss.

2. **Boundary-condition over-constraint** *(high confidence)*. Truss theory assumes pin joints at all nodes. `gs002.inp:30` fixes node 1 in **all 6 DOFs** (UX, UY, UZ, RX, RY, RZ). For T3D2 (no rotational DOFs), DOFs 4-6 are silently ignored. For B31 (which the file actually uses), they are *enforced*, creating a clamped joint that resists moment.

3. **Unit ambiguity (secondary)**. `truss_theory.py:14-15, 305-310` uses SI (L=10 m, E=210e9 Pa). `expected_results.json:31-33` uses MPa. `gs002.inp:6-9, 19-20` uses bare 10.0 with E=210000.0 — only consistent with mm-MPa. This makes the predicted node-3 displacement of `-2.37e-9 m` (`expected_results.json:73`) unverifiable in absolute terms.

## Evidence

- `golden_samples/GS-002/README.md:1, 35, 142-146`
- `golden_samples/GS-002/expected_results.json:5, 88, 145`
- `golden_samples/GS-002/gs002.inp:1-3, 12, 23-25, 30`
- `golden_samples/GS-002/truss_theory.py:14, 305-310`

## Recommended action

**All SHORT-TERM and ARCHITECTURAL items below are *hypotheses pending GS-revalidation* per ADR-011 §HF3.** A FailurePattern's authority is limited to attribution and to the IMMEDIATE governance status update; the listed paths/ADRs must be re-validated (hot-smoke + review) before any code or schema action is taken.

### IMMEDIATE
- Mark GS-002 status `insufficient_evidence` in Notion control plane. **Per ADR-011 §HF3, this case has no defensible GS reference: README/JSON declare a T3D2 truss while the `.inp` ships a B31 frame, so the comparison reference is not defensible.**
- Pin `expected_results.json` metadata version in the `gs_artifact_pin` frontmatter (now pinned to `"1.0"`).
- Cross-link FP-002 from ADR-011 consequences.

### SHORT-TERM (≤ 2 weeks) — *hypotheses, require GS-revalidation*
Two-track decision (pick one and record in a small ADR / runbook):

- **Track A (preserve truss intent — recommended)**: Rewrite `gs002.inp` with `*ELEMENT, TYPE=T3D2` and pin-joint BCs (constrain only translational DOFs); regenerate FRD; theory remains valid. Cheapest, aligns with file naming.
- **Track B (preserve current `.inp`)**: Rewrite README and `expected_results.json` to declare a **frame** problem and recompute reference with stiffness-matrix solution including bending.

Track A is cheaper and aligns with the `truss_theory.py` calculator already in the directory.

### ARCHITECTURAL
- Reinforces the case for **ADR-012** ("Golden-sample triplet contract") — element-type drift between README/JSON/INP would be caught at authoring time.
- Reinforces **ADR-013** ("Comparison-validity precondition") — a router that knew the .inp uses B31 should refuse to compare against truss-theory references.

## Open questions

- Was the B31 substitution documented anywhere outside the inline comment? If yes, the runbook should reference that history.
- Does any consumer of `expected_results.json` (test, viz, report generator) rely on `element_type: "T3D2"`? Audit before flipping to "B31" or starting Track A.
