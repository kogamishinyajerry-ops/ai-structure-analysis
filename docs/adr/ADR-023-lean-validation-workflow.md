# ADR-023: Lean Validation Workflow and Claim-Boundary Gate

- **Status:** Accepted by user directive, implementation PR pending
- **Date:** 2026-05-06
- **Linear:** ENG-39
- **Related:** ADR-011, ADR-012, ADR-013, ADR-022, RFC-002 section 4.1

---

## Context

The project has accumulated strong truth-management machinery around Linear,
GitHub/repo, Notion mirrors, calibration checks, commit trailers, golden-sample
guards, and reviewer evidence. That machinery correctly prevents demo evidence
from being over-claimed as signed physical validation, but it has also started
to slow ordinary finite-element development.

The current failure mode is not that the project lacks gates. The failure mode
is that a gate designed for physical-validation claims can be applied too early
to sandbox, demo, planning, and candidate-iteration work. This creates large
review packets for steps that should be fast learning loops.

We need a faster workflow that still keeps solver/runtime claims honest.

## Decision

Adopt a three-tier validation workflow. The strict signed-validation gate moves
to the **claim boundary**: the point where the project wants to say a result is
validated physics, benchmark agreement, signed GS evidence, or a completed
physical simulation.

### Tier 0: Sandbox / Demo

Purpose: fast path discovery, UI/workbench exploration, adapter smoke coverage,
deck experiments, report wiring, and visual prototypes.

Allowed:

- run demos and candidate decks;
- generate reports, screenshots, manifests, and local artifacts;
- use synthetic or upstream demo fixtures when clearly labeled;
- iterate without a full validation packet for every step.

Required wording:

- `demo-only`
- `software-path evidence only`
- `candidate-only`
- `not signed validation`

Forbidden claims:

- `validated physics`
- `benchmark agreement`
- `signed GS evidence`
- `signed GS###`
- `steel perforation completed`
- `bullet-through-steel complete`
- `bullet-through-steel simulation complete`

Tier 0 requires ordinary local verification appropriate to the change, but not
a signed-validation evidence packet.

### Tier 1: Engineering Candidate

Purpose: produce an engineering-candidate run that is reproducible and suitable
for review, without claiming benchmark validation.

Minimum evidence spine:

- deck or model source and provenance;
- solver logs and normal/error termination state;
- unit system, coordinate assumptions, boundary conditions, contact assumptions,
  material source, and solver version;
- output metric list and extraction script/command;
- artifact manifest with hashes for deck, logs, frame lists, reports, and key
  derived outputs;
- known limitations and no-overclaim wording.

Tier 1 may use local Claude Opus 4.7 as an automatic read-only reviewer when a
review trigger fires. A single compact review artifact is sufficient unless the
reviewer returns `CHANGES_REQUIRED` or `BLOCKER`.

### Tier 2: Signed Validation

Purpose: support physical-validation claims.

Strict gate remains mandatory for any claim of validated physics, benchmark
agreement, signed GS evidence, or completed bullet-through-steel behavior.

All of the following evidence is required:

- one public, traceable benchmark source with residual velocity, perforation
  target, or other explicit target metrics;
- material and failure parameters traceable to the benchmark source or another
  credible source;
- deck provenance and solver logs;
- residual/perforation metrics and tolerance comparison;
- mesh/time-step or convergence evidence appropriate to the claim;
- artifact manifest and hashes;
- independent reviewer/signoff evidence;
- clear Linear/GitHub proof linkage.

No model, agent, or reviewer may replace the benchmark, convergence evidence, or
signoff required for Tier 2 claims.

## Claude Opus Review Automation

When a reviewer is required by ADR-011 M-triggers, calibration gates, governance
changes, signed-validation work, or explicit user request, Codex should invoke
local Claude Opus 4.7 automatically as a read-only reviewer if the local
`claude` CLI is available.

Default read-only constraints:

- allow file inspection only (`Read`, `Grep`, `Glob`);
- disallow edits, writes, shell execution, external writes, merge, and approval;
- capture the verdict as repo-local evidence when it affects a PR gate.

Codex should not pause merely to ask whether reviewer invocation is allowed.
Codex must still pause for explicit owner authority when the next action is a
merge, self-approval, Linear state transition, Notion mutation, branch
protection change, or signed-claim promotion.

## Workflow Simplification

Future development should prefer:

1. one bounded Linear issue or explicit user scope;
2. fast candidate implementation;
3. one reproducibility manifest when a run matters;
4. automatic read-only Opus review when required;
5. one signed-validation packet only at Tier 2 claim boundary.

Avoid:

- duplicate gate packets, checklists, routers, and dry-run payloads for the same
  Tier 0 or Tier 1 evidence;
- treating every demo report as a validation gate;
- blocking candidate development on signed-validation artifacts that are only
  needed at the claim boundary.

## GS101 Application

`GS-101-demo-unsigned` remains Tier 0 demo evidence only. It can be used to show
software-path execution and report generation. It cannot support steel
perforation, validated physics, signed GS101, benchmark agreement, or
bullet-through-steel completion.

The GS101 signed path remains Tier 2:

- ENG-24 selects the public benchmark source;
- ENG-25 authors a benchmark-traceable deck;
- downstream issues capture runtime artifacts, metrics, convergence, reporting,
  and signoff.

## Consequences

Positive:

- faster day-to-day development;
- fewer duplicated governance artifacts;
- clearer distinction between demos, candidates, and signed validation;
- Opus review becomes an automatic tool instead of a manual stop.

Tradeoffs:

- Tier 0 and Tier 1 artifacts are easier to produce and therefore require clear
  wording discipline;
- project summaries must name the claim tier explicitly;
- signed-validation claims remain slower by design.

## Non-Goals

This ADR does not:

- change branch protection or CI policy;
- change solver protocols, schemas, public APIs, or dependencies;
- mutate `golden_samples/**`;
- approve OpenRadioss as general solver truth;
- approve GS101 signed validation;
- authorize Notion-first truth changes.
