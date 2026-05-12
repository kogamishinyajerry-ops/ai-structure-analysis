# AI-FEA commercial benchmark and simulation-capability strategy

> Status: strategy research note.
> Date: 2026-05-12.
> Scope: AI-Structure-FEA product and simulation roadmap only.
> Claim tier: planning / Tier 0 strategy artifact. This document is not signed validation, not benchmark agreement, and not an authorization to start FM-04b.

## Executive conclusion

The strongest commercial AI/CAE products are not winning by building heavier harnesses. They are winning by turning simulation into a continuously improving engineering loop:

1. high-fidelity solvers remain the source of truth;
2. geometry, mesh, material, boundary condition, solver logs, and results become durable data assets;
3. AI is placed around the solver as preprocessing guidance, surrogate/ROM inference, design-space exploration, out-of-domain detection, and report generation;
4. the user-facing workflow starts from engineering intent and returns auditable decisions, not just raw result files;
5. strict validation is reserved for the physical-claim boundary, while sandbox and candidate work move quickly with clear labels.

For this repository, the practical shift is:

- stop treating a heavy harness as the product center;
- make the AERON-backed solve path, candidate report spine, and Trust Center the product center;
- build a small simulation data asset layer from real runs;
- add surrogate/ROM capability first for scalar KPIs and later for full-field mesh outputs;
- keep Tier 2 validation gates strict only where the project claims validated physics.

## Working `/goal` for this strategy slice

```text
/goal Research top commercial AI/FEA and AI/CAE products and turn the findings into a repo-local AI-Structure-FEA development strategy.

Objective:
  Create a sourced strategy document that explains how AI-Structure-FEA should reduce dependence on heavy harness workflows while increasing real simulation capability.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis
  - New artifact only: docs/strategy/ai-fea-commercial-benchmark-2026.md
  - Inputs: AGENTS.md, .planning/STATE.md, .planning/ROADMAP.md, .planning/FM-04B_READINESS.md, ADR-023, official commercial product sources, and selected technical ML-for-simulation research.

Constraints:
  - Do not edit solver code, public interfaces, schemas, state machines, CI, golden_samples/**, or validation artifacts.
  - Do not start FM-04b or promote Tier 0/Tier 1 evidence to Tier 2.
  - Use official product sources where possible; label inference separately from source facts.
  - Keep the recommendation actionable for this repository's existing FM-02/FM-03/FM-04 roadmap.

Done when:
  1. docs/strategy/ai-fea-commercial-benchmark-2026.md exists.
  2. The document names top commercial product patterns with source links.
  3. The document maps those patterns into a harness-light AI-Structure-FEA roadmap.
  4. The document defines near-term slices that avoid forbidden surfaces and preserve claim-tier wording.
  5. `git diff --check -- docs/strategy/ai-fea-commercial-benchmark-2026.md` exits 0.

Stop if:
  - The work would require editing golden_samples/**, solver decks, schemas, public APIs, or validation claim state.
  - A recommendation would imply signed validation without benchmark, tolerance, convergence, hashes, and reviewer/signoff evidence.
  - Source claims cannot be backed by official vendor pages, product documentation, or research pages.
```

## Commercial product map

### 1. Ansys: SimAI, optiSLang, Engineering Copilot, Mechanical agents

Relevant source facts:

- Ansys SimAI trains AI models from simulation results and geometry input, then predicts new designs as continuous 3D physical fields.
- SimAI reports a confidence level and can tell the user when a design is too far from the training data and should trigger retraining.
- 2026 R1 separates SimAI into local desktop Pro and cloud-scale Premium offerings, with expanded data handling for high-resolution archives.
- Ansys 2026 R1 connects optiSLang with SimAI for an end-to-end workflow from training data generation to AI training to optimization/design studies.
- Ansys is also adding agentic help directly inside simulation products, such as a Mechanical mesh agent for preprocessing failures and a Discovery validation agent for setup issues.

Development lesson:

Ansys is not replacing Mechanical, Fluent, Icepak, optiSLang, or Discovery with a chat wrapper. It is wrapping existing solver products with data generation, surrogate training, confidence, optimization, and embedded agents at brittle workflow points.

What to copy:

- Build a first-class `run -> manifest -> train/evaluate -> confidence -> retrain queue` loop.
- Show out-of-domain confidence before showing AI predictions as useful evidence.
- Put AI assistance at preprocessing and validation friction points first: mesh failures, missing BCs, unsupported materials, nonconverged jobs.
- Offer local-first execution for sensitive data and cloud/HPC later.

What not to copy yet:

- Do not start with broad SaaS or massive data infrastructure.
- Do not claim "full-fidelity comparable" until a real dataset and benchmark protocol exist.

### 2. Altair: PhysicsAI inside HyperWorks/HyperMesh

Relevant source facts:

- Altair PhysicsAI trains from existing simulation studies, including older concepts, similar parts, or different programs.
- It operates directly on mesh or CAD models and uses geometric deep learning.
- PhysicsAI supports solver-agnostic native CAE files and can train regardless of data origin.
- The 2025.1 release added Transformer Neural Simulator (TNS), native extraction of thickness/material IDs from solver decks, mesh alignment for translation invariance, dataset outlier detection, and similarity score output for predictions.
- Supported deck metadata extraction includes OptiStruct, Radioss, LS-DYNA, Nastran, Abaqus, and ANSYS.

Development lesson:

Altair's pattern is "data reuse without hand parameterization." The high-value product move is not a single perfect benchmark. It is turning messy historical CAE results into a geometric learning set, then giving engineers similarity/outlier tools so they know when the prediction is trustworthy.

What to copy:

- Make solver decks and result archives ingestible as training samples.
- Start with mesh/CAD-level features, not only hand-authored scalar parameters.
- Add outlier and similarity scoring before exposing any AI prediction in the UI.
- Treat material IDs, thicknesses, units, and solver profile as model inputs, not free text around the run.

What not to copy yet:

- Do not train a full-field model before the project can reliably normalize mesh, material, BC, and result data.
- Do not hide known issues; surface model applicability limits in the Trust Center.

### 3. Siemens: Simcenter ROM and HEEDS AI Simulation Predictor

Relevant source facts:

- Simcenter Reduced Order Modeling builds, validates, compares, and exports ROMs from simulation and test data.
- Siemens positions ROMs as using high-fidelity simulation or test data from any source for fast predictions, co-simulation, real-time applications, control, and monitoring.
- Simcenter ROM supports methods ranging from response surfaces to neural networks, AI, and ML.
- It supports export targets such as FMI, ONNX, and Amesim submodels.
- Siemens' HEEDS AI Simulation Predictor and Simcenter ROM are described as improving design-space prediction and reducing simulation time for large design studies.

Development lesson:

Siemens treats AI simulation as an engineering model artifact that can be validated, compared, exported, and reused. The ROM is not just a model file; it is a workflow object with metrics and deployment targets.

What to copy:

- Build a "candidate surrogate card" format: training data hash, target metrics, error table, domain of validity, export path, limitations.
- Start with scalar and low-dimensional ROMs for residual velocity, max displacement, peak stress, safety factor, mesh quality, and solve time.
- Export model artifacts in open formats where possible later, especially ONNX for inference.

What not to copy yet:

- Do not make model export a blocker for the first useful surrogate. A JSON manifest plus deterministic inference script is enough for the first slice.

### 4. Dassault Systemes SIMULIA / 3DEXPERIENCE

Relevant source facts:

- 3DEXPERIENCE SIMULIA emphasizes Simulation Data Science: best-practice capture, publication, reuse, and replay.
- 2026x adds AI-powered virtual-twin physics behavior for quick performance evaluations of design alternatives.
- SIMULIA also highlights KPI-focused results exploration and pass/fail views to identify problems and root causes.

Development lesson:

Dassault's pattern is enterprise simulation memory: capture the best workflow, publish it, replay it, and align it with business requirements. AI is only useful if it can reuse trusted practices and present KPI-oriented decisions.

What to copy:

- Introduce reusable "analysis recipes" as product objects: geometry prep, mesh policy, BC/material/contact setup, solver config, postprocessing, required evidence.
- Make the Trust Center KPI-first: result, confidence, evidence, limitation, next action.
- Let users replay a known analysis recipe before asking them to configure a new run.

What not to copy yet:

- Do not build a full enterprise PLM/control mirror in the repo. Keep repo truth local and Linear/GitHub aligned.

### 5. SimScale: cloud-native simulation plus Engineering AI agents

Relevant source facts:

- SimScale positions Engineering AI agents as autonomous orchestration tools that extract technical intent from specifications and execute the validation workflow from CAD preparation and meshing through solver configuration and final report.
- SimScale states the agents can encode a team's standards, solver preferences, and compliance rules.
- The platform integrates CFD, FEA, electromagnetics, and thermal simulation in a cloud-native workflow.
- It emphasizes auditable, proposal-ready validation reports.

Development lesson:

This is the clearest commercial signal for the "intent-to-report" direction. The agent is valuable only because it controls a real simulation platform with standards, solver preferences, and audit output.

What to copy:

- Build the agent as an orchestrator over explicit recipes and solver capabilities, not as an unconstrained code-writing agent.
- Start from engineering intent, but translate it into a deterministic case plan before running.
- Keep audit reports as a first-class output of every meaningful run.

What not to copy yet:

- Do not make the agent autonomous across all physics. Pick one vertical wedge and enforce narrow guardrails.

### 6. Neural Concept and PhysicsX: AI-native engineering intelligence

Relevant source facts:

- Neural Concept positions its platform as an enterprise layer above existing CAD/CAE stacks, using 3D deep learning and AI copilots for design generation, performance tradeoffs, ranking, filtering, and simulation workflow connection.
- It can be SaaS or private cloud, indicating data sensitivity is a core adoption issue.
- PhysicsX positions its platform as combining fast AI-driven physics inference with numerical simulation across the product lifecycle for mission-critical engineering.

Development lesson:

AI-native players are not selling "run a solver faster" as the whole story. They sell a new design loop: generate options, predict physics quickly, rank tradeoffs, and hand the right candidates back to high-fidelity simulation.

What to copy:

- Shift UI from "run one case" to "compare variants and choose the next candidate."
- Represent design intent, objectives, constraints, and tradeoffs explicitly.
- Keep numerical simulation in the loop for correction and trust.

What not to copy yet:

- Do not jump to generative CAD before the project has stable case setup and result comparison.

### 7. Hexagon MSC Apex, nTop, and Autodesk Fusion: design-native simulation

Relevant source facts:

- Hexagon MSC Apex Generative Design uses FEA-based optimization with well-defined elements rather than only density fields, generating multiple design candidates under constraints.
- nTop integrates FEA with parametric implicit modeling so stress, displacement, modal, thermal, and topology-optimization studies update as the design changes. It also exports analysis-ready geometry to trusted solvers and supports simulation directly on implicit geometry through integrations.
- Autodesk Fusion combines generative design, modeling, simulation, and manufacturing in one platform; its Simulation Extension includes nonlinear static stress, buckling, modal, thermal, thermal stress, and event simulation, plus cloud solves and generative design.

Development lesson:

Design-native products shorten the loop before solver execution: geometry updates, mesh/BC refresh, simulation, and manufacturability checks stay in the same workflow. The product center is iteration speed, not a one-off validation packet.

What to copy:

- Treat geometry/model preparation as part of the simulation product, not a file upload detail.
- Build small parametric variant generation before advanced AI design generation.
- Make mesh/BC updates deterministic when a parameter changes.

What not to copy yet:

- Do not attempt full CAD kernel ownership.
- Do not add a new design framework until one existing case can update parameters, rerun, and compare results reliably.

## Cross-product patterns that matter most

### Pattern A: solver truth plus AI acceleration

The top products keep a real solver, test data, or validated high-fidelity model as the truth source. AI accelerates prediction, setup, exploration, or decision-making. It does not erase the need for solver provenance.

Repo implication:

- Keep CalculiX/OpenRadioss/AERON as the truth path.
- Make AI predictions "candidate guidance" until they are benchmarked.
- Store the solver run that produced each training sample and prediction.

### Pattern B: data assets, not harness scripts

Commercial systems treat simulation archives as reusable data: geometry, mesh, solver deck, material IDs, BCs, units, output fields, scalar KPIs, logs, convergence notes, and hashes.

Repo implication:

- Replace large bespoke harness loops with a small, durable "simulation sample" record.
- The candidate report spine is already close to this. Extend it toward a training-sample manifest rather than another orchestration layer.

### Pattern C: confidence, similarity, and outlier detection are product features

Ansys confidence, Altair similarity/outlier tools, and Siemens validation/comparison all show the same rule: users need to know when AI is outside its training domain.

Repo implication:

- Any AI prediction must ship with applicability status:
  - `in_domain`
  - `near_boundary`
  - `out_of_domain`
  - `unknown_insufficient_training_data`
- The UI should display "why" using geometry distance, parameter range, material/BC mismatch, mesh resolution mismatch, and solver-profile mismatch.

### Pattern D: KPI-first result exploration

Commercial products increasingly present pass/fail, goals, KPIs, and root-cause hints instead of forcing users to inspect raw field files first.

Repo implication:

- Trust Center should lead with:
  - target metric;
  - observed value;
  - evidence source;
  - confidence/applicability;
  - limitation;
  - next allowed action.
- Raw plots, logs, and decks remain available, but they are supporting evidence.

### Pattern E: one vertical wedge beats broad platform sprawl

Every successful pattern depends on a tight physical domain first. "AI for all simulation" is the product narrative; the build path is one solver, one family of cases, one set of metrics, one validation loop.

Repo implication:

- Pick one near-term wedge:
  - static structural candidate loop with CalculiX, or
  - ballistic Tier 1 candidate loop with OpenRadioss, without Tier 2 promotion.
- Do not try to improve all solvers and all physics simultaneously.

## Recommended AI-Structure-FEA direction

### North star

AI-Structure-FEA should become an evidence-first AI simulation workbench:

> A user describes or selects an engineering case; the system prepares a deterministic analysis recipe, runs a real solver or qualified candidate surrogate, reports KPIs and limitations, compares variants, and tells the user the next safe engineering action.

This is different from a heavy harness:

- A harness repeatedly proves that internal plumbing works.
- A workbench helps the engineer make a better design decision.

### Product architecture shift

Current useful assets:

- AERON backend direction gives a solver abstraction.
- Candidate Report Spine gives a reproducibility spine.
- Trust Center / operator shell gives a UI location for provenance, warnings, and next action.
- ADR-023 gives a claim-tier model that supports fast Tier 0/Tier 1 iteration without weakening Tier 2.

Missing capability:

- durable simulation data samples;
- analysis recipes;
- design variant comparison;
- AI/surrogate applicability scoring;
- a narrow "intent-to-case-plan" orchestrator;
- a real training/evaluation lane for candidate surrogates.

### Recommended capability layers

Layer 1: simulation kernel

- One deterministic case runner per solver family.
- Inputs: model/deck, material, BC/contact, mesh policy, solver config.
- Outputs: logs, result fields/KPIs, convergence notes, artifact hashes.
- Goal: fewer harness scripts, more real solver runs.

Layer 2: simulation sample manifest

- One record per meaningful run.
- Fields: case id, source files, solver version, geometry/mesh summary, material/BC/contact assumptions, output metrics, logs, hashes, claim tier, limitations.
- Goal: every run can later become training data or evidence without reverse engineering.

Layer 3: analysis recipe

- Reusable definition of how a class of problems is prepared and judged.
- Examples:
  - "cantilever static stress quick candidate"
  - "thin plate impact Tier 1 ballistic candidate"
  - "modal/buckling screen"
- Goal: encode best practice once and replay it.

Layer 4: surrogate/ROM lane

- Stage 1: scalar KPI surrogate using existing tabular metadata and metrics.
- Stage 2: field-aware surrogate using mesh/graph features after enough normalized samples exist.
- Stage 3: design exploration that proposes variants, but sends high-value candidates back through real solvers.
- Goal: AI speeds exploration, not validation claims.

Layer 5: engineering agent

- Converts user intent/spec into a case plan.
- Checks missing inputs and recipe compatibility.
- Runs only allowed deterministic tools.
- Produces report and next action.
- Goal: agentic workflow only after recipes and sample manifests exist.

## Development roadmap

### Slice 1: Harness-light simulation sample manifest

Claim tier: Tier 1 engineering candidate infrastructure.

Goal:

- Add a compact manifest for real solver runs that can double as candidate report evidence and future training data.

Deliverables:

- A document or schema proposal for `simulation_sample_manifest`.
- Mapping from existing Candidate Report Spine fields to training-sample fields.
- One read-only conversion path from an existing Tier 1 candidate run into a sample record.

Boundaries:

- Do not change golden samples.
- Do not change solver deck truth.
- Do not promote any evidence to Tier 2.

Why first:

- Commercial AI simulation depends on reusable data. Without this, surrogate work becomes a toy.

### Slice 2: Analysis recipe v1

Claim tier: Tier 0/Tier 1 workflow infrastructure.

Goal:

- Define one recipe format that explains setup, run, metrics, limitations, and next action for a single case family.

Recommended first recipe:

- CalculiX static structural candidate, if the priority is robustness and faster iteration.
- OpenRadioss ballistic Tier 1 candidate, if the priority is matching the current FM-04a direction.

Deliverables:

- Recipe doc.
- Fixture-free dry-run planner.
- UI/Trust Center mapping for recipe status.

Why second:

- Recipes are the bridge between expert best practice and future agents.

### Slice 3: Scalar surrogate baseline

Claim tier: Tier 1 candidate only.

Goal:

- Train and evaluate a basic surrogate for scalar KPIs before full-field AI.

Candidate targets:

- max displacement;
- peak von Mises stress;
- safety factor;
- residual velocity candidate metric;
- perforation marker candidate status;
- solver runtime or mesh quality risk.

Required evidence:

- train/test split recorded by manifest hashes;
- error table;
- applicability range;
- "not signed validation" wording;
- abstain/out-of-domain behavior.

Why scalar first:

- It exercises the data loop and confidence UX with less data than full-field prediction.

### Slice 4: Variant exploration workbench

Claim tier: Tier 0/Tier 1 depending on evidence.

Goal:

- Let the user compare variants by objective/constraint rather than manually inspect one run at a time.

Features:

- parameter grid or DOE;
- table of KPIs, warnings, confidence, and artifact links;
- "rerun selected candidate with real solver";
- "mark as training candidate" action.

Why fourth:

- This is where commercial value becomes visible. The user sees faster decisions, not just internal architecture.

### Slice 5: Intent-to-case-plan agent

Claim tier: Tier 0 orchestration first; Tier 1 only when backed by real solver artifacts.

Goal:

- Convert a user request or engineering spec into a bounded case plan using existing recipes.

Rules:

- Agent may plan and call deterministic runners.
- Agent may not invent material/failure parameters.
- Agent may not promote validation state.
- Agent must ask for missing physical inputs before running if no safe default exists.

Why last:

- Commercial agentic simulation works because the underlying platform has recipes, data, solvers, and reports. Building the agent before those assets recreates the heavy-harness problem.

## Immediate next three Linear-sized issues

### ENG-AI-01: Simulation sample manifest proposal

Objective:

- Produce the minimal manifest proposal and map it to Candidate Report Spine fields.

Scope:

- docs only, likely under `docs/strategy/` or `docs/development/`.

Acceptance:

- names required fields;
- includes one example record from an existing non-golden Tier 1 candidate artifact if available;
- states what is not training-ready yet.

### ENG-AI-02: One analysis recipe for an existing run family

Objective:

- Define a reusable recipe for one existing solver path.

Scope:

- one solver family only;
- no schema or public API changes in the planning issue.

Acceptance:

- recipe lists inputs, preflight checks, run command, output metrics, limitations, and Trust Center mapping;
- includes stop conditions for missing physics data.

### ENG-AI-03: Scalar surrogate feasibility packet

Objective:

- Determine whether current artifacts are enough for a scalar surrogate baseline.

Scope:

- read-only artifact inventory plus a proposal.

Acceptance:

- count candidate samples;
- identify available targets and missing fields;
- recommend one model type and one abstention rule;
- no training claim unless data count and split are actually present.

## What to stop doing

- Stop adding broad harness layers before a real product workflow needs them.
- Stop treating every Tier 0/Tier 1 run like a signed-validation packet.
- Stop adding adapters unless a user-visible recipe or variant loop will use them.
- Stop writing AI/coprocessor features that cannot cite solver artifacts, manifests, or applicability limits.
- Stop trying to solve full-field AI before scalar KPIs and data quality are working.

## What to protect

- Keep AGENTS.md and ADR-023 claim-tier discipline.
- Keep `golden_samples/**` protected.
- Keep solver/runtime claims honest.
- Keep Tier 2 strict and slow.
- Keep the next implementation slice small enough for one PR and one review packet.

## Source map

Commercial product sources:

- Ansys SimAI: https://www.ansys.com/products/ai/simai
- Synopsys / Ansys 2026 R1 AI product release: https://investor.synopsys.com/news/news-details/2026/Synopsys-Launches-Ansys-2026-R1-to-Re-Engineer-Engineering-with-Joint-Solutions-and-AI-Powered-Products/default.aspx
- Altair PhysicsAI: https://altair.com/physicsai
- Altair HyperWorks 2025.1 PhysicsAI release notes: https://help.altair.com/hwdesktop/altair_help/topics/release_notes/rn_2025_hypermesh_physicsai_r.htm
- Siemens Simcenter Reduced Order Modeling: https://www.siemens.com/en-us/products/simcenter/integration-solutions/reduced-order-modeling/
- Siemens HEEDS AI Simulation Predictor / Simcenter ROM release: https://news.siemens.com/en-gb/heeds-ai-simulation-predictor-simcenter-rom/
- Dassault Systemes 3DEXPERIENCE SIMULIA: https://www.3ds.com/products/simulia/3dexperience-simulia
- SimScale Engineering AI: https://www.simscale.com/product/engineering-ai/
- SimScale Engineering AI agents press release: https://www.simscale.com/press/simscale-opens-engineering-ai-agents/
- Neural Concept platform: https://www.neuralconcept.com/platform
- Monolith AI engineering product development platform: https://www.monolithai.com/
- PhysicsX platform: https://www.physicsx.ai/platform
- Hexagon generative design: https://hexagon.com/solutions/generative-design
- nTop simulation: https://www.ntop.com/software/capabilities/simulation/
- Autodesk Fusion generative design AI: https://www.autodesk.com/solutions/generative-design-ai-software
- Autodesk Fusion Simulation Extension: https://www.autodesk.com/products/fusion-360/simulation-extension

Technical research anchors:

- Learning Mesh-Based Simulation with Graph Networks: https://arxiv.org/abs/2010.03409
- Graph Neural Network Based Surrogate Model of Physics Simulations for Geometry Design: https://arxiv.org/abs/2302.00557
- DeepFEA: Deep Learning for Prediction of Transient Finite Element Analysis Solutions: https://arxiv.org/abs/2412.04121
