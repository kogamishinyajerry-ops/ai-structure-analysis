# Simulation sample manifest proposal

> Status: proposal.
> Date: 2026-05-12.
> Scope: AI-Structure-FEA development planning for ENG-AI-01.
> Claim tier: Tier 1 engineering-candidate infrastructure proposal.
> Non-claim: this document is not signed validation, not benchmark agreement, and not a runtime schema change.

## Purpose

The project needs a small durable data asset between solver runs and future AI
simulation features. The current Candidate Report Spine is already a strong
review artifact, but it is optimized for report evidence. A simulation sample
manifest should make each meaningful run reusable for:

- candidate report evidence;
- later scalar surrogate or reduced-order model training;
- out-of-domain and similarity scoring;
- variant comparison;
- reviewer/auditor inspection.

This proposal executes the first harness-light step from
`docs/strategy/ai-fea-commercial-benchmark-2026.md`: define the manifest shape
and map it to existing spine fields before writing implementation code.

## Working `/goal`

```text
/goal Execute ENG-AI-01 as a docs-only simulation sample manifest proposal.

Objective:
  Define the minimal simulation sample manifest that turns real solver/report
  runs into reusable data assets without adding a new harness layer.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis
  - File: docs/development/simulation_sample_manifest_proposal.md
  - Inputs: AGENTS.md, .planning/STATE.md, .planning/ROADMAP.md,
    docs/strategy/ai-fea-commercial-benchmark-2026.md,
    reports/fm03_candidate_report_spine_source_map.md, and
    backend/app/services/candidate_report_spine.py.

Constraints:
  - Do not edit solver code, public APIs, runtime schemas, persistent formats,
    CI, dependencies, solver decks, or golden_samples/**.
  - Do not start FM-04b and do not promote any Tier 0 or Tier 1 evidence to
    Tier 2.
  - Treat external Linear/Notion writes as gated and out of scope.
  - Mark unavailable evidence explicitly instead of fabricating values.

Done when:
  1. This document exists and names the proposed manifest fields.
  2. It maps current Candidate Report Spine fields to sample-manifest fields.
  3. It includes an example record or states why a real training-ready record
     is not yet available.
  4. It lists data-readiness gaps and the next implementation slice.
  5. `git diff --check -- docs/development/simulation_sample_manifest_proposal.md`
     exits 0.

Stop if:
  - The proposal requires editing golden_samples/**, solver decks, public APIs,
    runtime schemas, or validation claim state.
  - A field would imply benchmark agreement or signed validation without the
    ADR-023 Tier 2 evidence packet.
  - Existing repo evidence cannot support the mapping.
```

## Design rule

The manifest is a data record, not a new orchestrator.

It should be produced as a sidecar from an already completed run/report path.
It should not schedule jobs, mutate solver inputs, decide validation status, or
replace the Candidate Report Spine. Its job is to preserve the run as a
machine-readable sample that future AI features can train on, compare against,
or reject as out-of-domain.

## Proposed manifest identity

Draft name:

```text
simulation_sample_manifest.v0
```

This is a proposal name only. It does not change any persistent repo schema
until a later Linear issue explicitly authorizes implementation.

Recommended file locations for a future implementation:

- `project_state/runs/<case_id>/<run_id>/simulation_sample_manifest.json`
- `project_state/graph_executor/<case_id>/simulation_sample_manifest.json`

The first location is better for multiple runs per case. The second location is
acceptable for the current graph-executor style if only the latest run matters.

## Proposed top-level fields

```json
{
  "schema_version": "simulation_sample_manifest.v0",
  "manifest_id": "sample-...",
  "generated_at_utc": "2026-05-12T00:00:00Z",
  "claim_tier": "Tier 1 engineering candidate",
  "allowed_claim": "engineering candidate data sample, not signed validation",
  "case": {},
  "recipe": {},
  "solver": {},
  "inputs": {},
  "geometry_mesh": {},
  "physics_setup": {},
  "runtime": {},
  "outputs": {},
  "metrics": {},
  "artifact_manifest": {},
  "data_quality": {},
  "ai_readiness": {},
  "limitations": [],
  "tier2_blockers": []
}
```

### `case`

Required:

- `case_id`
- `case_name`
- `case_family`
- `run_id`
- `source_surface`

Recommended values:

- `case_family`: `static_structural`, `ballistic_candidate`,
  `modal_screen`, `buckling_screen`, or `unknown`.
- `source_surface`: endpoint, CLI, graph executor, or manual upload path that
  produced the record.

Why it matters:

- Future AI work needs grouping by problem family. Mixing a static cantilever
  with transient ballistic data in one training set should be mechanically
  detectable.

### `recipe`

Required:

- `recipe_id`
- `recipe_version`
- `recipe_status`
- `recipe_inputs_complete`

Current status:

- ENG-AI-02 defines the first proposed recipe in
  `docs/development/static_structural_calculix_recipe_v1.md`. Runtime manifest
  generation does not yet have a recipe registry, so generated records should
  keep `recipe_status = "not_attached"` until ENG-AI-02A implements attachment
  checks.

Why it matters:

- Commercial AI/CAE tools scale because setup practice is captured and replayed.
  This field is the bridge from raw report evidence to reusable engineering
  workflow.

### `solver`

Required:

- `solver_name`
- `solver_backend`
- `solver_version`
- `truth_source`
- `job_id`
- `job_status`
- `normal_termination_state`
- `log_artifacts`

Allowed unknowns:

- `solver_version = null` is allowed only with
  `data_quality.missing_required_for_training[]` explaining the gap.

Why it matters:

- AI predictions are not portable across solver families without evidence.
  CalculiX, OpenRadioss, Abaqus, Nastran, and ANSYS-origin data must remain
  distinguishable.

### `inputs`

Required:

- `input_deck`
- `result_file`
- `expected_results`
- `source_geometry`
- `source_parameters`

Each item should use the artifact record shape:

```json
{
  "status": "available",
  "path": "safe/path/or/upload:name",
  "sha256": "...",
  "size_bytes": 123,
  "role": "input_deck"
}
```

Why it matters:

- A future training sample must point back to the exact deck/result pair that
  created the target values.

### `geometry_mesh`

Required:

- `node_count`
- `element_count`
- `element_types`
- `increment_count`
- `mesh_metadata`
- `mesh_quality`
- `mesh_convergence_study`

Recommended future additions:

- bounding box;
- units for coordinates;
- part count;
- material-region count;
- mesh alignment transform when a surrogate pipeline normalizes geometry.

Why it matters:

- Altair-style mesh/CAD learning and similarity scoring require mesh and
  geometry descriptors, not only scalar KPIs.

### `physics_setup`

Required:

- `unit_system`
- `materials`
- `boundary_conditions`
- `loads`
- `contact`
- `failure_model`
- `domain_specific`

Recommended `domain_specific` examples:

- ballistic: initial velocity, projectile geometry, plate thickness, material
  source, failure model source, time-step policy;
- static structural: support type, load type, stress criterion, allowable
  stress source.

Why it matters:

- AI/ROM reuse should abstain when material, BC, contact, or failure-model
  context is missing or mismatched.

### `runtime`

Required:

- `started_at_utc`
- `finished_at_utc`
- `duration_s`
- `host`
- `runner`
- `container_image`
- `command`
- `exit_code`

Current status:

- Candidate Report Spine can surface latest job id/status and log artifacts,
  but it does not yet guarantee full command/container/runtime capture.

Why it matters:

- A reproducible data asset needs enough runtime context to distinguish a real
  solver sample from a manual report upload.

### `outputs`

Required:

- `result_fields`
- `field_files`
- `report_artifacts`
- `sidecars`

Sidecars should include known current artifacts:

- `mesh_quality.json`
- `mesh_convergence.json` or `mesh_refinement_convergence.json`
- `ballistic_metrics.json`
- `animation_manifest.json`
- `time_step_series.json`
- `time_step_convergence.json` or `dt_refinement_convergence.json`

Why it matters:

- Field files and sidecars become the training target inventory.

### `metrics`

Required:

- `output_metric_keys`
- `values`
- `extraction_command`
- `target_candidates`

Recommended `target_candidates` shape:

```json
[
  {
    "name": "max_von_mises",
    "value": 123.4,
    "unit": "MPa",
    "target_type": "scalar_regression",
    "training_ready": false,
    "blocked_by": ["unit_system_not_machine_normalized"]
  }
]
```

Why it matters:

- The first useful surrogate should be scalar KPI prediction. This block makes
  target selection mechanical.

### `artifact_manifest`

Required:

- `hash_algorithm`
- `hash_count`
- `items[]`

This can reuse the Candidate Report Spine artifact item concept. A future
implementation should avoid hashing huge generated frame trees unless the
artifact is selected as a training target or review deliverable.

### `data_quality`

Required:

- `sample_status`
- `training_ready`
- `missing_required_for_training[]`
- `warnings[]`
- `outlier_status`
- `deduplication_key`

Recommended `sample_status` values:

- `candidate_recorded`
- `not_training_ready`
- `training_ready_scalar`
- `training_ready_field`
- `rejected_incomplete`

Why it matters:

- This is where the project avoids turning every report artifact into a
  training sample. Incomplete records stay useful for review, but they do not
  silently enter an AI dataset.

### `ai_readiness`

Required:

- `intended_use`
- `allowed_model_tasks`
- `disallowed_model_tasks`
- `similarity_features_available`
- `abstention_required`

Recommended values:

- `allowed_model_tasks`: `scalar_kpi_baseline`,
  `similarity_indexing`, `outlier_detection`.
- `disallowed_model_tasks`: `tier2_validation_claim`,
  `benchmark_agreement_prediction`, `full_field_training` until enough
  normalized field data exists.

Why it matters:

- The manifest should make it easy to build an abstaining AI feature first,
  before attempting full-field prediction.

## Mapping from Candidate Report Spine

| Simulation sample field | Candidate Report Spine source | Notes |
|---|---|---|
| `schema_version` | new field | Proposed `simulation_sample_manifest.v0`; do not reuse `fm03-candidate-report-spine.v2`. |
| `manifest_id` | `artifact_manifest.manifest_id` | May reuse as input seed but should be namespaced as a sample id. |
| `claim_tier` | `claim_tier` | Preserve exact Tier 1 wording unless a future issue explicitly changes it. |
| `allowed_claim` | `allowed_claim`, `no_overclaim` | Must include `not signed validation`. |
| `case.case_id` | `case.case_id` | Existing value can be `uploaded-artifact`; not enough for training grouping by itself. |
| `case.case_name` | `case.case_name` | Direct mapping. |
| `case.case_family` | infer from `ballistic.status`, report kind, or recipe | Inference must be explicit and reviewable. |
| `case.source_surface` | `provenance.report_surface` | Direct mapping for report upload path. |
| `solver.solver_name` | `solver.truth_source`, `provenance.solver_truth_source` | Normalize later to `calculix`, `openradioss`, etc. |
| `solver.job_id` | `solver.latest_job_id` | May be null for manual uploads. |
| `solver.job_status` | `solver.latest_job_status` | Direct mapping. |
| `solver.normal_termination_state` | `solver.normal_termination_state` | Direct mapping. |
| `solver.log_artifacts` | `solver.logs`, `artifact_manifest.items[kind=solver_log]` | Preserve both summary and hash record. |
| `inputs.result_file` | `artifact_manifest.items[kind=result_frd]` | Direct mapping when present. |
| `inputs.input_deck` | `artifact_manifest.items[kind=input_deck]` | Direct mapping for CalculiX deck when present. |
| `inputs.expected_results` | `artifact_manifest.items[kind=expected_results]` | Keep claim-tier caveats; expected results are not benchmark agreement. |
| `geometry_mesh.node_count` | `provenance.node_count` | Direct mapping. |
| `geometry_mesh.element_count` | `provenance.element_count` | Direct mapping. |
| `geometry_mesh.increment_count` | `provenance.increment_count` | Direct mapping. |
| `geometry_mesh.element_types` | `mesh_evidence` input-deck inventory | Available only when deck inventory is surfaced. |
| `geometry_mesh.mesh_quality` | `mesh_evidence.quality_summary` | Tier 1 health evidence only. |
| `geometry_mesh.mesh_convergence_study` | `mesh_evidence.convergence_study` | Candidate stability flag only; not Tier 2 convergence. |
| `physics_setup.unit_system` | `assumptions.unit_system` | Requires later normalization for training. |
| `physics_setup.materials` | `assumptions.material_source` | Must abstain if missing or free-text only. |
| `physics_setup.boundary_conditions` | `assumptions.boundary_conditions` | Must abstain if missing or free-text only. |
| `physics_setup.contact` | `assumptions.contact` | Direct mapping where available. |
| `physics_setup.domain_specific.ballistic` | `ballistic` | Keep candidate-only wording. |
| `runtime.command` | `metrics.extraction_command` and future job metadata | Current spine only records report extraction command. |
| `outputs.sidecars` | `artifact_manifest.items` plus `ballistic` sub-artifacts | Direct mapping for sidecars that already have artifact records. |
| `metrics.output_metric_keys` | `metrics.output_metric_keys` | Direct mapping. |
| `metrics.values` | `metrics.values` | Direct mapping. |
| `metrics.extraction_command` | `metrics.extraction_command` | Direct mapping. |
| `limitations` | `limitations` | Direct mapping. |
| `tier2_blockers` | `tier2_blockers`, `ballistic.tier2_blockers_ballistic` | Merge both lists without removing original blockers. |

## Example record

No complete training-ready non-golden sample record is currently committed under
a stable runtime artifact directory. The repo does have a non-golden source map
for FM-03 and code paths that can build a Candidate Report Spine, but a durable
sample manifest does not yet exist.

The example below is therefore intentionally marked
`example_only_not_training_ready`. It is based on existing Candidate Report
Spine field names and current report-upload behavior, not on a new solver run.

```json
{
  "schema_version": "simulation_sample_manifest.v0",
  "manifest_id": "sample-example-uploaded-artifact",
  "generated_at_utc": "2026-05-12T00:00:00Z",
  "claim_tier": "Tier 1 engineering candidate",
  "allowed_claim": "engineering candidate data sample, not signed validation",
  "case": {
    "case_id": "uploaded-artifact",
    "case_name": "example-only report upload",
    "case_family": "unknown",
    "run_id": "example-only",
    "source_surface": "POST /api/v1/report/generate"
  },
  "recipe": {
    "recipe_id": null,
    "recipe_version": null,
    "recipe_status": "not_attached",
    "recipe_inputs_complete": false
  },
  "solver": {
    "solver_name": "calculix",
    "solver_backend": "unknown_or_report_upload",
    "solver_version": null,
    "truth_source": "CalculiX FRD artifact",
    "job_id": null,
    "job_status": null,
    "normal_termination_state": "unknown",
    "log_artifacts": []
  },
  "inputs": {
    "input_deck": {"status": "unavailable", "role": "input_deck"},
    "result_file": {"status": "available", "role": "result_frd", "path": "upload:example.frd"},
    "expected_results": {"status": "unavailable", "role": "expected_results"},
    "source_geometry": {"status": "unavailable", "role": "source_geometry"},
    "source_parameters": {"status": "unavailable", "role": "source_parameters"}
  },
  "geometry_mesh": {
    "node_count": 0,
    "element_count": 0,
    "element_types": [],
    "increment_count": 0,
    "mesh_metadata": {"status": "unavailable"},
    "mesh_quality": {"status": "unavailable"},
    "mesh_convergence_study": {"status": "unavailable"}
  },
  "physics_setup": {
    "unit_system": "unknown",
    "materials": {"status": "unavailable"},
    "boundary_conditions": {"status": "unavailable"},
    "loads": {"status": "unavailable"},
    "contact": {"status": "unavailable"},
    "failure_model": {"status": "unavailable"},
    "domain_specific": {}
  },
  "runtime": {
    "started_at_utc": null,
    "finished_at_utc": null,
    "duration_s": null,
    "host": null,
    "runner": "report_upload",
    "container_image": null,
    "command": "POST /api/v1/report/generate",
    "exit_code": null
  },
  "outputs": {
    "result_fields": [],
    "field_files": [],
    "report_artifacts": [],
    "sidecars": []
  },
  "metrics": {
    "output_metric_keys": [],
    "values": {},
    "extraction_command": "POST /api/v1/report/generate with a CalculiX .frd upload or selected case artifact",
    "target_candidates": []
  },
  "artifact_manifest": {
    "hash_algorithm": "sha256",
    "hash_count": 0,
    "items": []
  },
  "data_quality": {
    "sample_status": "not_training_ready",
    "training_ready": false,
    "missing_required_for_training": [
      "stable case family",
      "solver version",
      "input deck hash",
      "unit-system normalization",
      "material and boundary-condition normalization",
      "non-empty target metrics"
    ],
    "warnings": [
      "example record only; not produced by a real manifest writer"
    ],
    "outlier_status": "not_evaluated",
    "deduplication_key": null
  },
  "ai_readiness": {
    "intended_use": "proposal_example_only",
    "allowed_model_tasks": [],
    "disallowed_model_tasks": [
      "tier2_validation_claim",
      "benchmark_agreement_prediction",
      "full_field_training",
      "scalar_kpi_training"
    ],
    "similarity_features_available": false,
    "abstention_required": true
  },
  "limitations": [
    "not signed validation",
    "not benchmark agreement",
    "not training-ready"
  ],
  "tier2_blockers": [
    "public benchmark/source is not attached",
    "Tier 2 tolerance comparison and signed convergence evidence are not attached",
    "independent reviewer/signoff is not attached"
  ]
}
```

## Training-readiness gates

A sample is not training-ready unless all required gates for its intended use
are met.

### Scalar KPI baseline

Required:

- stable `case_family`;
- solver name and version;
- result artifact hash;
- input deck or source-parameter hash;
- unit system normalized to machine-readable values;
- material and BC/load descriptors present;
- at least one numeric target metric with unit;
- sample split key or deduplication key.

Allowed missing:

- full field files;
- mesh alignment transform;
- Tier 2 benchmark comparison.

### Full-field mesh surrogate

Required:

- everything from scalar KPI baseline;
- mesh nodes/elements available in normalized form;
- element types and field names stable;
- geometry or mesh alignment policy recorded;
- node/element result fields available as target arrays;
- enough samples per case family to make a train/test split meaningful.

Allowed missing:

- signed validation evidence, unless the model output is being used for a
  Tier 2 claim.

### Similarity/outlier index

Required:

- case family;
- solver profile;
- mesh summary;
- material and BC/load descriptors;
- geometry or parameter vector features;
- deduplication key.

Allowed missing:

- numeric target metrics, if the index is only used to abstain or route a case
  to a real solver.

## Implementation recommendation

Next implementation issue:

```text
ENG-AI-01A: Candidate Report Spine to simulation sample manifest converter
```

Scope:

- Add a pure function that converts a `candidate_report_spine` dict into a
  `simulation_sample_manifest.v0` dict.
- Add focused unit tests with hand-built spine fixtures.
- Do not write files by default.
- Do not modify report API response shape until a separate issue authorizes it.

Suggested files:

- `backend/app/services/simulation_sample_manifest.py`
- `backend/tests/test_simulation_sample_manifest.py`

Acceptance:

- preserves `claim_tier`, `allowed_claim`, `limitations`, and `tier2_blockers`;
- maps available result/input/log/sidecar artifact hashes;
- marks report-upload samples without solver job/runtime context as
  `not_training_ready`;
- marks scalar KPI samples as `training_ready_scalar` only when required fields
  are present;
- never emits Tier 2 wording from Tier 0/Tier 1 input.

## Linear dry-run payload

External Linear writes are out of scope for this local execution. If the user
chooses to mirror this proposal to Linear, use this as the dry-run payload:

```text
Title: ENG-AI-01 Simulation sample manifest proposal

Outcome:
  Define the minimal simulation sample manifest so solver/report artifacts can
  become reusable AI simulation data assets without adding a heavy harness.

Repository route:
  /Users/Zhuanz/20260408 AI StructureAnalysis

Acceptance:
  - docs/development/simulation_sample_manifest_proposal.md exists.
  - The document defines proposed manifest fields.
  - It maps Candidate Report Spine fields to manifest fields.
  - It includes an example record or explains why no training-ready record is
    available.
  - `git diff --check -- docs/development/simulation_sample_manifest_proposal.md`
    exits 0.

Boundaries:
  - Docs only.
  - No solver code, schemas, public APIs, CI, dependencies, solver decks, or
    golden_samples/** edits.
  - No FM-04b start and no Tier 2 promotion.

Evidence required:
  - Link to the committed proposal document.
  - Verification command and result.

Claim tier:
  Tier 1 engineering-candidate infrastructure proposal; not signed validation.
```
