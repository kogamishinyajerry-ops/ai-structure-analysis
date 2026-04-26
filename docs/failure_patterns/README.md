# Failure Patterns (FP-{nnn})

This directory holds **FailurePattern** entries — root-cause attributions for golden-sample (or production) deviations that the project cannot silently retry past. Each FP captures *why* a sample failed, *what category* the fault belongs to (per `schemas/sim_state.py::FaultClass`, ADR-004), and *what action* unblocks Phase / acceptance gates.

## Convention

- **Naming:** `FP-{nnn}-{slug}.md` (zero-padded, mirrors `docs/adr/ADR-{nnn}-{slug}.md`).
- **Authority:** A FailurePattern does not change behavior on its own — it is governance evidence. The `recommended_action` may, in turn, motivate an ADR or a corrective PR.
- **Status lifecycle:** `proposed → accepted → resolved | superseded`. `accepted` means the FP is the agreed root cause; `resolved` requires linked PR/commit. `superseded` requires a successor FP id. **Direct `proposed → resolved` is allowed** when a downstream PR/commit acts on the recommendation without a separate "accepted" governance step (the link in body or PR description satisfies the "linked PR/commit" requirement).
- **Reference linkage:** ADR-011 §HF3 governs the relationship — any GS without a defensible reference reads as `insufficient_evidence` until a FP raises (or refutes) the deviation.

## Schema

Frontmatter (YAML), required fields:

```yaml
---
id: FP-XXX
status: proposed | accepted | resolved | superseded
created: YYYY-MM-DD
related_gs: [GS-XXX, ...]
related_adr: [ADR-XXX, ...]
classification: <FaultClass enum value>     # one of: geometry_invalid / mesh_jacobian / mesh_resolution / solver_convergence / solver_timestep / solver_syntax / reference_mismatch / unknown / none
blocks: [<phase-or-task-id>, ...]
owner: <agent-or-person-id>
schema_version: 1
gs_artifact_pin:                             # SHA / version pin — invalidates FP if upstream artifact changes
  expected_results_version: "<from JSON metadata.version>"
  inp_sha: "<git short sha or n/a>"
  readme_sha: "<git short sha or n/a>"
---
```

**Severity is intentionally not a frontmatter field at the FF-02 level.** Phase / task blocking is signaled by the `blocks: [...]` field instead, and human-vs-machine adjudication priority is governed by ADR-011 §HF1-HF5 zoning, not by a per-FP severity tag. If a downstream consumer (e.g., FF-08 GS registry schema) needs a numeric severity, it must derive it from `classification` + `blocks` and pin its mapping in its own ADR, not retroactively introduce a field here.

Body sections (in order):

1. **Observed deviation** — concrete numbers, file:line citations.
2. **Hypothesized root causes (ranked)** — confidence label per cause.
3. **Evidence** — file:line list.
4. **Recommended action** — IMMEDIATE / SHORT-TERM / ARCHITECTURAL bullets.
5. **Open questions** — anything the FP author could not resolve.

## What a FailurePattern is NOT

- Not a debugging log — those go in `runs/` or session transcripts.
- Not an ADR — ADRs are decisions; FPs are findings. If the recommended action requires changing project policy, escalate to an ADR.
- Not a test — the regression guard goes in `tests/`. A FP may *cite* the test name added to prevent recurrence, but is not the test itself.

## Index

| ID | Title | Status | Related GS | Classification |
|----|-------|--------|------------|----------------|
| [FP-001](./FP-001-gs001-cantilever-spec-fork.md) | Cantilever GS theory↔FEA gap unresolvable as configured | resolved | GS-001 | reference_mismatch |
| [FP-002](./FP-002-gs002-truss-element-substitution.md) | Truss declared T3D2 but ships B31 | resolved | GS-002 | reference_mismatch |
| [FP-003](./FP-003-gs003-missing-hole-and-bc-direction.md) | Plate-with-hole has no hole + BC direction inverted | resolved | GS-003 | geometry_invalid |

> **FP-001 / FP-002 / FP-003** were resolved by PR #32 (golden_samples/GS-001/002/003 marked `insufficient_evidence` per these FPs).
