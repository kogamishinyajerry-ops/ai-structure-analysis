# Text-to-CAE open-source replacement recipe v1

> Status: proposal.
> Date: 2026-05-12.
> Scope: adapt the public Text-to-CAE bullet-plate workflow idea to
> AI-Structure-FEA without Abaqus.
> Claim tier: Tier 1 engineering-candidate infrastructure proposal.
> Non-claim: this document is not signed validation, not benchmark agreement,
> not a runtime schema change, and not a solver behavior change.

## Purpose

The public `Cai-aa/text-to-cae` repository shows a useful product pattern:

```text
natural-language / AI coding client
  -> editable case parameters
  -> CAE script builds, meshes, solves, and exports results
  -> browser viewer plays dynamic frames and contours
```

Its bullet-plate case is implemented with Abaqus/CAE and Abaqus/Explicit. This
project should copy the workflow shape, not the commercial dependency. The
open-source replacement for high-speed projectile penetration should be:

```text
Codex / local recipe
  -> cae_parameters.json-compatible intent
  -> Python/Gmsh or structured deck generator
  -> OpenRadioss starter + engine
  -> Vortex-Radioss reader / VTU / browser JSON exporter
  -> local viewer, GIF, report, and simulation sample manifest
```

For this ballistic problem, OpenRadioss is the primary free/open replacement.
CalculiX remains the preferred open-source path for static structural cases,
but it should not be treated as the main substitute for high-speed penetration
with explicit contact, plasticity, damage, and element erosion.

## Working `/goal`

```text
/goal Convert the Text-to-CAE bullet-plate Abaqus workflow into an
open-source OpenRadioss recipe for AI-Structure-FEA.

Objective:
  Define a narrow, executable recipe that reuses the Text-to-CAE product idea
  while replacing Abaqus/CAE, Abaqus/Explicit, ODB export, and Abaqus MCP with
  open-source components already compatible with this repository.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis
  - Primary file:
    docs/development/text_to_cae_openradioss_recipe_v1.md
  - Inputs: public Text-to-CAE repository, current GS-102 OpenRadioss scripts,
    ADR-023, ADR-024, and current sample-manifest/recipe direction.

Constraints:
  - Do not edit golden_samples/**.
  - Do not claim Tier 2 signed validation or benchmark agreement.
  - Do not add Abaqus, proprietary solvers, new orchestration platforms, or
    external writes.
  - Keep the replacement harness-light: recipe, deck generation, solver run,
    postprocessing, and evidence artifacts.

Done when:
  1. This file names the Text-to-CAE source workflow and bullet-plate assumptions.
  2. The Abaqus pieces are mapped to open-source replacements.
  3. The OpenRadioss recipe has stable input, run, export, and evidence fields.
  4. The next implementation slice is small enough to execute without changing
     public APIs or validation status.
  5. `git diff --check -- docs/development/text_to_cae_openradioss_recipe_v1.md`
     exits 0.

Stop if:
  - A replacement requires Abaqus, commercial LS-DYNA, ANSYS, or proprietary
    viewer tooling.
  - The work would require changing solver truth, schemas, CI policy,
    golden_samples/**, or signed-validation status.
  - The output wording would imply validated physics rather than a Tier 1
    engineering candidate.
```

## Source facts

Public source used:

- Text-to-CAE repository: <https://github.com/Cai-aa/text-to-cae>
- Text-to-CAE bullet-plate case:
  <https://github.com/Cai-aa/text-to-cae/tree/main/models/text-to-cae-bullet-plate>
- Bullet-plate Abaqus builder:
  <https://github.com/Cai-aa/text-to-cae/blob/main/models/text-to-cae-bullet-plate/bullet_plate_penetration_abaqus.py>
- Bullet-plate ODB exporter:
  <https://github.com/Cai-aa/text-to-cae/blob/main/models/text-to-cae-bullet-plate/export_bullet_mesh.py>
- OpenRadioss: <https://github.com/OpenRadioss/OpenRadioss>
- Gmsh: <https://gmsh.info/>
- CalculiX: <https://www.dhondt.de/>

Observed Text-to-CAE pattern:

- The README describes a local Abaqus simulation workspace where an AI coding
  client edits Abaqus Python scripts, runs Abaqus/CAE, exports solver results,
  and opens a browser result viewer.
- The viewer consumes browser-readable result payloads such as
  `result_mesh.json`, parameters, metadata, time frames, contours, and model
  tree state.
- The bullet-plate case uses Abaqus/Explicit, a rigid-equivalent projectile by
  default, a clamped armor steel plate, Johnson-Cook-style plasticity/rate
  dependence, damage/element deletion where available, hard contact with
  friction, and high frame output for animation.
- Its default parameters are close to a real engineering intent: 150 x 150 x
  8 mm plate, 7.62 mm class projectile, 28 mm projectile length, 9.6 g mass,
  830 m/s impact velocity, 80 microsecond event time, and 240 requested output
  intervals.
- Its exporter reads Abaqus ODB frames, extracts surface faces, computes
  per-face von Mises values, adds a visual projectile mesh, and writes
  `dynamicFrames` into `result_mesh.json`.

## Replacement decision

Use OpenRadioss for ballistic penetration.

Reasons:

- The case is transient explicit dynamics, not static structural analysis.
- The interesting behavior is contact, large deformation, plasticity, failure,
  and possible element deletion.
- The repository already has a working GS-102 OpenRadioss path: deck copy,
  velocity patching, solver execution, A-file reading, ballistic metrics,
  cloud animation, and Tier 1 report output.
- OpenRadioss is open-source and designed for dynamic event analysis.

Do not use CalculiX as the primary replacement for this case.

Reasons:

- CalculiX is valuable for Abaqus-like input and static structural work, but a
  bullet perforation workflow needs an explicit impact solver as the truth path.
- Treating CalculiX as the ballistic substitute would push the project toward
  unsupported physics claims or another heavy workaround layer.

## Abaqus-to-open-source mapping

| Text-to-CAE / Abaqus role | Open-source replacement | Current repo status |
| --- | --- | --- |
| Abaqus/CAE geometry scripting | Python structured generator first; later Gmsh OCC for full 3D geometry | GS-102 structured deck path exists |
| Abaqus mesh generation | Structured hexa deck generator or Gmsh mesh export | Coarse hexa deck exists; refined generator exists |
| Abaqus/Explicit solver | OpenRadioss starter + engine | Working through Docker image |
| Abaqus ODB | OpenRadioss `.A###` animation files and logs | Working via Vortex-Radioss |
| ODB Python postprocessor | Python exporter over Vortex-Radioss arrays | GIF/cloud renderer exists; browser JSON exporter is next |
| `result_mesh.json` dynamic frames | Repo-native VTU/manifest first; optional Text-to-CAE-compatible JSON | Not yet implemented for GS-102 |
| Abaqus MCP live session | Codex edits recipe/deck scripts and runs CLI locally | Current Codex flow already works |
| Browser run button | Local API endpoint can call recipe runner later | Not in this slice |
| Abaqus model tree | Derived recipe tree: parts, materials, BCs, contact, outputs | Should be generated from recipe metadata |

## Recipe identity

```yaml
recipe_id: openradioss_bullet_plate_candidate.v1
recipe_version: v1
case_family: ballistic_penetration
solver_family: openradioss
source_inspiration: Cai-aa/text-to-cae bullet-plate case
claim_tier: Tier 1 engineering candidate
allowed_claim: solver-backed candidate workflow, not signed validation
recipe_status: proposed
```

## Parameter model

The recipe should accept a Text-to-CAE-like parameter file so user prompts and
browser controls can stay simple.

Required parameters:

| Field | Meaning | Initial target |
| --- | --- | --- |
| `plate_length_mm` | target plate x/y span | 150 |
| `plate_width_mm` | target plate x/y span | 150 |
| `plate_thickness_mm` | impact thickness | 8 |
| `plate_material` | steel, resin, or explicit material preset | `armor_steel_candidate` |
| `bullet_diameter_mm` | projectile diameter | 7.62 |
| `bullet_length_mm` | projectile total length | 28 |
| `bullet_nose_length_mm` | conical/ogive equivalent nose length | 8 |
| `bullet_mass_g` | projectile mass target | 9.6 |
| `impact_velocity_mps` | initial projectile velocity | 830 |
| `impact_time_s` | engine termination time | 8.0e-5 |
| `plate_seed_mm` | target mesh size or structured cell size | start coarse, then refine |
| `bullet_seed_mm` | target projectile mesh size | start coarse, then refine |
| `rigid_projectile` | keep projectile undeleted/rigid-like | true for first visual candidate |
| `output_frames` | requested animation frames | 150 to 240 |
| `friction_coefficient` | contact friction candidate | 0.16 |

The current GS-102 scripts do not yet honor all of these fields. The next code
slice should implement a parameter adapter that maps this JSON into the
existing OpenRadioss runtime deck path.

## OpenRadioss deck strategy

The first implementation should not attempt a perfect Abaqus script clone.
Instead, it should turn the Text-to-CAE intent into a reproducible OpenRadioss
deck family:

1. Geometry:
   - Keep projectile and plate as separate parts.
   - Use x-axis impact to match current GS-102 extraction logic.
   - Start with structured hexa meshes so element IDs, part IDs, and deletion
     history remain easy to debug.
   - Add Gmsh only when the structured path cannot represent the desired
     projectile shape or local refinement.

2. Materials:
   - Support named presets:
     `armor_steel_candidate`, `resin_visual_candidate`,
     `rigid_projectile_candidate`, and `deformable_projectile_candidate`.
   - Preserve Johnson-Cook wording as candidate-only unless benchmark source,
     tolerance, and reviewer evidence exist.
   - Separate visual candidates from physical candidates. A no-failure resin
     cloud run is useful for visualization, but it is not a fracture model.

3. Contact and boundary conditions:
   - Plate edges clamped.
   - Projectile initial velocity patched in the runtime deck.
   - OpenRadioss contact card must be explicit in the recipe metadata.
   - Friction should be recorded as an input even if the first deck cannot
     exactly match Abaqus general contact semantics.

4. Output:
   - Engine animation interval should be derived from `impact_time_s` and
     `output_frames`.
   - Required fields: coordinates, element alive/deleted state, part IDs, stress
     or stress-derived proxy when available, plastic strain when available.
   - Output artifacts must include starter log, engine log, frame list, metrics,
     animation manifest, and report hash.

## Export strategy

There are two export targets. Build them in this order.

### Target 1: repo-native viewport/VTU

Use existing repo direction first:

- OpenRadioss A-files become reader arrays.
- Reader arrays become VTU or a viewport manifest.
- The Trust Center/report links to hashed artifacts.

This preserves current architecture and avoids copying another viewer schema
too early.

### Target 2: Text-to-CAE-compatible JSON

Add only after the repo-native path is stable.

Proposed exporter:

```text
scripts/gs102_export_text_to_cae_result_mesh.py
```

Input:

- `project_state/runs/<case_id>/data/model_00A###`
- `project_state/graph_executor/<case_id>/ballistic/ballistic_metrics.json`
- optional recipe parameter JSON

Output:

- `project_state/visualizations/<case_id>/result_mesh.json`

Required payload shape:

- `schemaVersion`
- `source`
- `analysisType: dynamic`
- `fieldLabel`
- `nodes`
- `elements`
- `fieldRanges`
- `dynamicFrames`

Differences from Text-to-CAE should be explicit:

- The projectile should come from OpenRadioss part geometry when available, not
  a synthetic visual-only bullet, unless the frame lacks projectile mesh output.
- The field can be `pressure_delta`, `von_mises`, or `plastic_strain`, but
  pressure-derived fields must be labelled as proxies.
- Element deletion should be carried as a first-class field, not hidden by
  omitting deleted faces.

## Immediate implementation slice

Implemented first slice:

```text
openradioss_bullet_plate_candidate.v1 adapter
```

Files:

- Recipe document:
  `docs/development/text_to_cae_openradioss_recipe_v1.md`
- Parameter adapter:
  `scripts/gs102_prepare_text_to_cae_openradioss_variant.py`
- Focused tests:
  `tests/test_gs102_prepare_text_to_cae_openradioss_variant.py`

Behavior:

1. Read a Text-to-CAE-like `cae_parameters.json`.
2. Clamp parameters to safe ranges.
3. Write runtime source decks under `project_state/diagnostic_sources/`.
4. Patch:
   - plate material preset;
   - projectile material preset;
   - projectile velocity;
   - engine animation interval from `impact_time_s / output_frames`;
   - metadata manifest with claim-tier limits.
5. Reuse `scripts/gs102_transient_candidate_pipeline.py`.
6. Reuse `scripts/gs102_render_cloud_animation.py` for high-resolution GIF.

Done criteria for that slice:

- `uv run pytest tests/test_gs102_prepare_text_to_cae_openradioss_variant.py -q`
  exits 0.
- A runtime deck generated from Text-to-CAE default parameters lands only under
  `project_state/`.
- OpenRadioss can run either a coarse 150-frame candidate or a documented
  `--skip-solver` reuse path.
- Generated report states Tier 1 only and does not say signed validation or
  benchmark agreement.

## Larger roadmap

After the parameter adapter:

1. Local refinement:
   - refine impact zone mesh;
   - preserve stable element/part IDs for history;
   - compare coarse vs refined outputs as Tier 1 convergence evidence.

2. Viewer compatibility:
   - export dynamic browser JSON;
   - add model-tree metadata from recipe fields;
   - expose play controls for dynamic frames.

3. AI data layer:
   - attach `openradioss_bullet_plate_candidate.v1` to simulation sample
     manifests;
   - index material, dimensions, velocity, mesh size, residual velocity,
     crossing time, frame count, deleted element history, and artifact hashes.

4. Design exploration:
   - run safe parameter sweeps over thickness, material preset, velocity, and
     mesh policy;
   - train only scalar Tier 1 candidate surrogates first, such as residual
     velocity or crossing time;
   - keep full-field AI until result normalization and similarity/outlier
     scoring exist.

5. Validation boundary:
   - promote only with locked benchmark source, benchmark data file, mesh/time
     convergence, material citation, tolerance table, independent review, and
     signed validation evidence.

## Current repo fit

Already aligned:

- `scripts/gs102_transient_candidate_pipeline.py` runs OpenRadioss from
  `project_state` and emits metrics/report artifacts.
- `scripts/gs102_prepare_text_to_cae_openradioss_variant.py` reads a
  Text-to-CAE-like parameter set and maps velocity, run time, and frame cadence
  onto a project_state-only OpenRadioss source deck.
- `scripts/gs102_prepare_resin_plate_variant.py` demonstrates material-preset
  variant generation outside `golden_samples/**`.
- `scripts/gs102_render_cloud_animation.py` demonstrates high-resolution
  pressure-proxy/von-Mises/plastic-strain style animation from real A-files.
- Current GS-102 reports already preserve Tier 1 wording.

Missing:

- OpenRadioss deck generator that can scale from the small GS-102 mesh to
  150 x 150 x 8 mm plate intent.
- Browser JSON/VTU exporter for dynamic frames with full projectile visibility.
- Recipe attachment in `simulation_sample_manifest`.

## Decision

Adopt the Text-to-CAE architecture pattern, but replace Abaqus with an
OpenRadioss-centered, open-source, recipe-first pipeline:

```text
Text-to-CAE idea: AI edits Abaqus script -> Abaqus solves -> ODB exporter -> viewer.
AI-Structure-FEA path: AI edits recipe/params -> OpenRadioss solves -> A-file exporter -> viewer/report/manifest.
```

This is the correct direction for the bullet penetration workflow because it
keeps the solver real, removes the Abaqus license dependency, and turns each
run into a reusable simulation data asset without creating another heavy
harness.
