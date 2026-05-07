# FM-03 Candidate Report Spine Source Map

Claim tier: Tier 1 engineering candidate, not signed validation.

## Inspected Surfaces

- `AGENTS.md` — repo execution rules, forbidden surfaces, claim-tier wording.
- `.planning/STATE.md` — current Phase 2 candidate lane, FM-01/ENG-40..45 status, AERON provenance context.
- `.planning/ROADMAP.md` — FM-03 exit evidence: manifest, logs, report artifact, extraction command, hash list, explicit not-signed-validation wording.
- `docs/adr/ADR-023-lean-validation-workflow.md` — Tier 1 evidence spine requirements and Tier 2 signed-validation blockers.
- `backend/app/services/report_generator.py` — existing report metrics, validation, markdown, and now additive `candidate_report_spine`.
- `backend/app/api/routes/report.py` — `/api/v1/report/generate` response surface; now passes source file, original filename, and latest solver-job status into the spine builder.
- `backend/app/models/evidence_bundle.py` — existing structured evidence model; left unchanged because this slice is additive and report-upload oriented.
- `backend/app/services/report/` — existing richer report/evidence modules for static strength, boundary summaries, material provenance, DOCX export, and templates; left unchanged.
- `backend/app/services/solver.py` and `backend/app/api/routes/solver.py` — current in-memory solver logs/status path used as optional report-spine context.
- `agents/mesh.py` — mesh agent now writes `mesh_quality.json` from the existing quality checker output as a Tier 1 sidecar artifact.
- `checkers/jacobian.py` — existing mesh quality source for scaled Jacobian, aspect ratio, degenerate percentage, and findings; left unchanged.
- `frontend/src/App.tsx` — Trust Center consumes Candidate Report Spine fields.
- `frontend/src/components/ChatPanel.tsx` — Copilot Review/Evidence/Fix Plan cards consume candidate-spine status.
- `golden_samples/GS-001/gs001.inp` — read-only deck source used by the focused test to prove input mesh node/element/type inventory.
- `golden_samples/GS-001/gs001_result.dat` — read-only solver-side status artifact used as convergence/status evidence without claiming a convergence study.
- `project_state/**/mesh/mesh_convergence.json` or `mesh_refinement_convergence.json` — optional runtime-side mesh-refinement convergence study artifact consumed when present; not generated or fabricated by this report slice.

## Current Evidence Fields

- Report metrics: `max_displacement`, `max_von_mises`, `safety_factor`, report status, modal/buckling increments when present.
- Validation: report-side `status` and `error_percentage`.
- Candidate provenance: parser, FRD filename, original upload name, file size, parse time, binary flag, node count, element count, increment count, solver truth source.
- Candidate solver evidence: latest job id/status if visible, normal termination state, solver log tail when in-memory logs exist, and `.dat/.sta/.cvg/spooles.out` artifact references when present.
- Candidate assumptions: unit-system statement, material source when declared, BC/load source when declared, contact unavailable reason.
- Candidate manifest: sha256 records for uploaded/selected FRD, input deck, expected-results payload, and solver-side log/status artifacts visible beside the case.
- Candidate mesh evidence: FRD parser node/element/increment counts, `.inp` deck node/element/type inventory, mesh metadata sidecar references when visible, `mesh_quality.json` metrics when present, optional mesh-refinement convergence study when present, and explicit unavailable wording for each missing evidence layer.
- Candidate convergence evidence: solver job status when visible, `.dat/.sta/.cvg/spooles.out` artifact records and signals when visible, normal-termination availability, mesh-refinement study status when visible, missing `.sta/.cvg` or refinement-study reasons, and explicit "not signed validation" wording.
- Candidate limitations: not signed validation, no public benchmark agreement, no mesh convergence evidence, no independent reviewer/signoff, mesh quality metric gaps, solver convergence gaps, and unavailable provenance notes.
- Candidate review summary: `candidate_ready_for_review` or `needs_review`, blocked findings, and next actions.

## Explicit Non-Claims

- This source map does not promote any GS sample to signed validation.
- This slice does not modify solver truth, solver decks, CI policy, persistent schemas, dependencies, or `golden_samples/**`.
- `mesh_quality.json` is a Tier 1 reviewer artifact only; scaled-Jacobian/aspect-ratio metrics alone do not prove mesh convergence.
- Solver status artifacts are not the same as a mesh-refinement convergence study.
- `mesh_convergence.json` is candidate convergence evidence only; it still does not prove public benchmark agreement, tolerance compliance, or independent signoff.
- Tier 2 remains blocked until benchmark/source, tolerance comparison, convergence study evidence, artifact hashes, and independent reviewer/signoff are attached.

## FM-04a P1 — Ballistic Candidate Block (schema v2, additive)

The schema is bumped to `fm03-candidate-report-spine.v2`. The bump adds a top-level `ballistic` key. The bump is purely additive: every other field, status, and wording from v1 is preserved.

### Inspected / consumed surfaces (read-only)

- `project_state/graph_executor/<case_id>/ballistic/ballistic_metrics.json` — optional Tier 1 candidate metrics sidecar. Schema (when present): `status`, `projectile_initial_velocity_m_per_s`, `residual_velocity_candidate_m_per_s`, `perforation_marker ∈ {still, embedded_candidate, perforated_candidate, stopped_candidate, unknown}`, `energy_balance{ initial_kinetic_energy_j, plastic_dissipation_j, contact_friction_j, hourglass_energy_j, residual_kinetic_energy_j }`, `claim_boundary`. **Not produced by this slice.** Will be authored by P6 after the OpenRadioss adapter (P4) yields a concrete candidate run.
- `project_state/graph_executor/<case_id>/ballistic/animation_manifest.json` — optional ballistic animation manifest sidecar. Hash + size + safe path are surfaced; frame contents are not parsed.
- `project_state/graph_executor/<case_id>/ballistic/time_step_series.json` — optional time-step series summary sidecar (`step_count`, `min_dt_s`, `max_dt_s`, `mean_dt_s`).
- `expected_results.json` ballistic fallback: `expected_results.ballistic.projectile_initial_velocity_m_per_s` is consumed only when the runtime metrics sidecar omits initial velocity. ADR-024 (lite) governs which value is allowed here.

### Surfaced fields under `ballistic`

- `status`: `unavailable` (no metrics sidecar) | `candidate_observed` (metrics sidecar present and parseable).
- `claim_impact`: constant `Tier 1 candidate ballistic evidence only; not benchmark agreement; not signed validation`.
- `claim_boundary`: from sidecar when present, otherwise constant `tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement`.
- `projectile_initial_velocity{ status, value_m_per_s, source | unavailable_reason }`. Sidecar wins over `expected_results.json` when both declare a value.
- `residual_velocity_candidate{ status, value_m_per_s, extraction_source, claim_impact | unavailable_reason }`.
- `perforation_marker{ status, evidence_path, claim_impact | unavailable_reason }`. Unknown when sidecar absent or marker not in the allowed candidate set.
- `energy_balance_candidate{ status, initial_kinetic_energy_j, plastic_dissipation_j, contact_friction_j, hourglass_energy_j, residual_kinetic_energy_j, energy_ratio, claim_impact | unavailable_reason }`. `energy_ratio = (plastic + contact + hourglass + residual) / initial` when initial > 0; only used as a Tier 1 candidate health indicator.
- `animation_manifest{ status, path, sha256, size_bytes, claim_impact | unavailable_reason }`.
- `time_step_series_summary{ status, source, step_count, min_dt_s, max_dt_s, mean_dt_s, claim_impact | unavailable_reason }`.
- `tier2_blockers_ballistic[]`: explicit list of what blocks any Tier 2 ballistic claim — public benchmark/source not attached, tolerance comparison not attached, independent reviewer/signoff not attached, payload is explicitly not benchmark agreement and not signed validation. When the metrics sidecar is missing, "no ballistic_metrics.json sidecar" is added as the first blocker.

### Spine-level integrations triggered by the ballistic block

- `_build_limitations` adds `ballistic candidate evidence is unavailable` whenever `ballistic.status != "candidate_observed"`.
- `_build_reviewer_summary` adds `ballistic candidate metrics unavailable` to `blocked_findings` when the metrics sidecar is missing.
- `artifact_manifest.items` includes `ballistic_metrics`, `animation_manifest`, `time_step_series` records (status `available` | `unavailable`) so reviewers can hash and audit them.

### Explicit non-claims (P1 specific)

- This slice does not produce any ballistic sidecar; it only consumes them when present.
- `energy_ratio ∈ [0.95, 1.05]` is explicitly a Tier 1 candidate health indicator and **not** benchmark agreement.
- `perforation_marker = "perforated_candidate"` is **not** the same as "steel perforation completed", "bullet-through-steel complete", "signed GS101", or "validated physics" (all forbidden by ADR-023).
- ADR-024 (lite) supplies parameters only; no public benchmark agreement is claimed in P1.
