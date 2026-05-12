# AI exploration fast lane

> Status: working development rule.
> Date: 2026-05-12.
> Scope: Tier 0 and Tier 1 exploration in AI-Structure-FEA.
> Non-claim: this document does not authorize Tier 2 signed validation,
> benchmark agreement, external writes, or signed golden-sample promotion.

## Purpose

The project has enough governance to protect signed claims. The current
bottleneck is different: physics exploration, design search, and AI data
generation are still moving too slowly.

This fast lane deliberately relaxes Tier 0 and Tier 1 iteration so large
models can help with:

- parameter and variant suggestions;
- candidate deck and recipe hypotheses;
- sidecar-driven design exploration;
- simulation sample inventory;
- scalar KPI target selection;
- out-of-domain and missing-evidence warnings.

The output is always a candidate next action unless a separate Tier 2 gate is
opened and satisfied.

## What is relaxed

Tier 0 and Tier 1 work may proceed without a signed-validation packet when it
is clearly labeled and locally verified.

Allowed fast-lane work:

- generate parameter sweeps and candidate run plans from existing sidecars;
- create or update reports under `reports/` from existing runtime evidence;
- add local scripts that read `project_state/**` and propose next runs;
- build sample-manifest, recipe, and dataset-index helpers;
- use synthetic or candidate data for UI, report, and AI-readiness experiments;
- let models propose hypotheses, feature gaps, and next-run priorities.

The standard of proof is "useful candidate evidence", not "signed physical
truth".

## What is not relaxed

These boundaries still hold:

- no runtime writes under `golden_samples/**`;
- no signed-validation or benchmark-agreement claims from Tier 0 or Tier 1;
- no mutation of public APIs, persistent schemas, CI, branch protection, or
  solver truth without explicit scope;
- no Linear, GitHub, Notion, or branch-protection external writes unless the
  user explicitly asks for them;
- no promotion from `insufficient_evidence` to active signed sample without
  the Tier 2 packet.

Tier 2 still requires benchmark source, tolerance, convergence evidence,
sealed artifact hashes, and independent review.

## Practical rule

For Tier 0 and Tier 1 exploration, prefer this loop:

1. Read existing sidecars, logs, manifests, or reports.
2. Propose the smallest next experiment that increases information.
3. Write runtime outputs only under `project_state/**` or reports under
   `reports/**`.
4. Keep all generated text explicit about claim tier and limitations.
5. Add focused tests for any reusable script or data transform.

Avoid this loop:

1. Build a larger harness before the next physical question is clear.
2. Create a validation packet before there is a validation claim.
3. Block candidate runs on evidence that only Tier 2 needs.

## Current first application

The first concrete fast-lane artifact is:

```text
scripts/gs102_design_exploration.py
reports/gs102_design_exploration_20260512.md
```

It reads the current GS-102 velocity sidecars and proposes the next candidate
velocity probes:

- `365 m/s`
- `445 m/s`
- `520 m/s`

These are Tier 1 exploration probes only. They are selected to reduce the
current transition bracket between the highest embedded candidate and the
lowest perforated candidate.

## Next applications

Recommended follow-up slices:

- add a dataset index over simulation sample manifests;
- add missing-field and out-of-domain status to candidate samples;
- add a Trust Center "design exploration" card;
- run the three GS-102 candidate velocity probes and regenerate the bracket;
- start a scalar surrogate feasibility packet once enough samples exist.
