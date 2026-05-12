# Static structural CalculiX analysis recipe v1

> Status: proposal.
> Date: 2026-05-12.
> Scope: ENG-AI-02, first analysis recipe for AI-Structure-FEA.
> Claim tier: Tier 1 engineering-candidate infrastructure proposal.
> Non-claim: this document is not signed validation, not benchmark agreement,
> not a runtime schema change, and not a solver behavior change.

## Purpose

This document defines the first reusable analysis recipe for the project:

```text
static_structural_calculix_candidate.v1
```

The recipe captures how a CalculiX static structural candidate case should be
prepared, checked, postprocessed, and converted into future AI simulation data.
It is intentionally a small engineering contract, not a new harness. A harness
proves plumbing repeatedly. A recipe makes one class of engineering work
replayable, auditable, and useful for later surrogate or similarity workflows.

## Working `/goal`

```text
/goal Execute ENG-AI-02 as a docs-only static structural CalculiX recipe v1.

Objective:
  Define the first analysis recipe that future sample manifests and AI features
  can attach to without changing solver code or validation claims.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis
  - Primary file:
    docs/development/static_structural_calculix_recipe_v1.md
  - Optional cross-reference:
    docs/development/simulation_sample_manifest_proposal.md
  - Inputs: AGENTS.md, ADR-023 claim-tier rules, the commercial AI-FEA
    benchmark strategy, and the existing Candidate Report Spine direction.

Constraints:
  - Do not edit solver code, public APIs, runtime schemas, persistent formats,
    CI, dependencies, solver decks, or golden_samples/**.
  - Do not claim Tier 2 signed validation.
  - Do not create a generic workflow platform or a broad orchestration layer.
  - Keep the recipe narrow to static structural CalculiX candidate evidence.

Done when:
  1. The recipe has a stable recipe_id and explicit applicability boundaries.
  2. Required inputs, preflight checks, output metrics, and limitations are
     named in this file.
  3. The sample-manifest attachment fields are specified for a later code
     slice.
  4. The focused documentation diff check exits 0:
     git diff --check -- \
       docs/development/static_structural_calculix_recipe_v1.md \
       docs/development/simulation_sample_manifest_proposal.md

Stop if:
  - The recipe needs changes to solver decks, golden_samples/**, runtime
    schemas, public interfaces, CI, or claim-state policy.
  - Existing evidence would force a Tier 2 validation claim.
  - The requested case is nonlinear contact, ballistic/transient, modal,
    buckling, thermal, or non-CalculiX.
```

## Recipe identity

```yaml
recipe_id: static_structural_calculix_candidate.v1
recipe_version: v1
case_family: static_structural
solver_family: calculix
claim_tier: Tier 1 engineering candidate
allowed_claim: engineering candidate analysis recipe, not signed validation
recipe_status: proposed
```

The recipe is eligible to become `attached` in a simulation sample manifest only
after a runtime implementation performs the required preflight checks.

## Applicability

Use this recipe for:

- linear or near-linear static structural candidate cases;
- CalculiX-origin decks and result files;
- displacement, stress, and safety-factor KPI extraction;
- engineering-candidate comparison and future scalar surrogate training;
- Trust Center evidence display with explicit limitations.

Do not use this recipe for:

- Tier 2 signed validation;
- OpenRadioss ballistic, impact, or other transient dynamics cases;
- modal, buckling, thermal, fatigue, contact-heavy nonlinear, or plasticity
  claims;
- field-aware surrogate training unless mesh/result-field normalization is
  separately implemented and verified.

## Required inputs

The future runtime recipe implementation should treat these fields as required
for a complete attached recipe:

| Field | Expected content | Training impact |
| --- | --- | --- |
| `case_id` | Stable case identifier | Blocks grouping if missing |
| `input_deck` | CalculiX `.inp` artifact with hash | Blocks replay and training |
| `result_file` | CalculiX result artifact, usually `.frd` | Blocks target extraction |
| `solver_version` | CalculiX version or backend truth | Blocks training if unknown |
| `unit_system` | Normalized model/stress/force units | Blocks metric comparison |
| `material_descriptor` | Elastic material model and parameters | Blocks physics grouping |
| `bc_descriptor` | Boundary and load summary | Blocks similarity scoring |
| `mesh_summary` | Element count, node count, mesh notes if available | Weakens reuse if missing |
| `runtime_status` | Success, failure, or manual-upload state | Blocks completed-run reuse |
| `artifact_hashes` | Hashes for deck, results, logs, and report evidence | Blocks audit trail |

Incomplete inputs should not fail the whole report path. They should make the
recipe attachment explicit:

```json
{
  "recipe_id": "static_structural_calculix_candidate.v1",
  "recipe_version": "v1",
  "recipe_status": "incomplete",
  "recipe_inputs_complete": false,
  "missing_inputs": ["solver_version", "unit_system"]
}
```

## Preflight checks

The preflight checks should be deterministic and local:

| Check | Required outcome |
| --- | --- |
| Solver family | Must resolve to `calculix` |
| Case family | Must resolve to `static_structural` |
| Claim tier | Must remain Tier 0 or Tier 1; never Tier 2 |
| Deck artifact | Must have a path or upload label plus hash for training |
| Result artifact | Must have a path or upload label plus hash for training |
| Units | Must be normalized before scalar training readiness |
| Material | Must have a non-empty descriptor before scalar training readiness |
| Boundary/load setup | Must have a non-empty descriptor before scalar training readiness |
| Metrics | Numeric metrics must be finite, not strings such as `nan` |
| Limitations | Missing evidence must be recorded, not hidden |

If any required training field is missing, the sample may still be reportable as
candidate evidence, but AI readiness must remain `not_training_ready`.

## Output metrics

The v1 recipe standardizes these candidate KPIs:

| Metric | Unit expectation | Notes |
| --- | --- | --- |
| `max_displacement` | model length unit | Include source node/region when available |
| `max_von_mises` | MPa or normalized stress unit | Do not compare without unit normalization |
| `safety_factor` | dimensionless | Requires material allowables or explicit assumption |

Optional later metrics:

- reaction-force balance;
- mesh convergence notes;
- solver residual or termination summary;
- maximum principal stress;
- displacement at named probe points.

## Sample manifest attachment

When the runtime implementation is added, a complete manifest recipe block
should look like:

```json
{
  "recipe_id": "static_structural_calculix_candidate.v1",
  "recipe_version": "v1",
  "recipe_status": "attached",
  "recipe_inputs_complete": true,
  "case_family": "static_structural",
  "solver_family": "calculix",
  "preflight_status": "passed"
}
```

Until that implementation exists, generated sample manifests should keep
`recipe_status = "not_attached"` and explain that the runtime recipe registry is
not yet connected.

## Trust Center mapping

The recipe should eventually support these Trust Center surfaces:

- recipe identity and version;
- solver truth and runtime status;
- input completeness;
- KPI cards for displacement, stress, and safety factor;
- limitations and missing evidence;
- AI readiness state: `training_ready_scalar`, `not_training_ready`, or
  `abstain`;
- next safe action, such as rerun with normalized units or attach material
  descriptors.

## AI capability enabled

This recipe supports the first safe AI-FEA lane:

- scalar KPI surrogate experiments after enough normalized samples exist;
- case similarity and out-of-domain checks;
- variant ranking for candidate designs;
- report evidence summarization with explicit limitations.

It does not support:

- signed validation prediction;
- replacing real solver runs;
- field-level surrogate claims without mesh/field normalization;
- autonomous design release decisions.

## Implementation follow-up

Recommended next slice:

```text
ENG-AI-02A: implement a pure Python recipe descriptor and attach it to the
simulation sample manifest builder when the spine evidence satisfies this
document.
```

Suggested files for that slice:

- `backend/app/services/analysis_recipes.py`
- `tests/test_analysis_recipes.py`
- `tests/test_simulation_sample_manifest.py`

Acceptance for the follow-up should require:

- no solver execution;
- no schema migration;
- no public API contract change;
- one complete static structural CalculiX spine maps to an attached recipe;
- incomplete evidence maps to `recipe_status = "incomplete"` or
  `not_attached`;
- focused pytest coverage passes.
