# GS-102 Design Exploration Plan - 2026-05-12

> Status: Tier 1 design exploration plan.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Use existing GS-102 velocity sidecars to choose the next candidate
OpenRadioss runs. This plan is meant to loosen Tier 1 exploration speed
without promoting any physical validation claim.

## Current Evidence

| V0 m/s | Marker | Back crossed | Residual m/s | Solver normal | Metrics |
|---:|---|---|---:|---|---|
| 150 | `embedded_candidate` | false | 1.189671 | true | `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/ballistic/ballistic_metrics.json` |
| 285 | `embedded_candidate` | false | 4.667462 | true | `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/ballistic/ballistic_metrics.json` |
| 325 | `embedded_candidate` | false | 5.614325 | true | `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/ballistic/ballistic_metrics.json` |
| 345 | `embedded_candidate` | false | 12.244106 | true | `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/ballistic/ballistic_metrics.json` |
| 365 | `perforated_candidate` | true | 34.469076 | true | `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/ballistic/ballistic_metrics.json` |
| 365 | `perforated_candidate` | true | 34.469076 | true | `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/ballistic/ballistic_metrics.json` |
| 385 | `embedded_candidate` | false | 1.988066 | true | `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/ballistic/ballistic_metrics.json` |
| 405 | `embedded_candidate` | false | 14.932447 | true | `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/ballistic/ballistic_metrics.json` |
| 445 | `embedded_candidate` | false | 12.725867 | true | `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/ballistic/ballistic_metrics.json` |
| 485 | `embedded_candidate` | false | 11.857689 | true | `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/ballistic/ballistic_metrics.json` |
| 505 | `perforated_candidate` | true | 40.374543 | true | `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/ballistic/ballistic_metrics.json` |
| 520 | `perforated_candidate` | true | 19.570806 | true | `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/ballistic/ballistic_metrics.json` |
| 600 | `perforated_candidate` | true | 52.676288 | true | `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/ballistic/ballistic_metrics.json` |

## Transition Bracket

Non-monotonic candidate response detected.

- `345 m/s` to `365 m/s`: embedded -> perforated
- `365 m/s` to `385 m/s`: perforated -> embedded
- `485 m/s` to `505 m/s`: embedded -> perforated

- Treat this as a Tier 1 diagnostic signal, not a physical threshold.
- Prefer diagnostic probes before narrowing a single transition bracket.

## Recommended Next Runs

| V0 m/s | Reason | Claim tier |
|---:|---|---|
| 355 | refine lower transition window | Tier 1 candidate only |
| 375 | diagnose non-monotonic reversal window | Tier 1 candidate only |
| 495 | refine upper transition window | Tier 1 candidate only |

## AI Exploration Freedoms Used

- The model may propose velocity probes and design hypotheses from
  existing sidecars before a benchmark is locked.
- The proposal may prioritize information gain over validation-packet
  completeness.
- The next run set may be changed quickly after each new sidecar lands.

## Hard Boundaries

- Do not write runtime outputs under `golden_samples/**`.
- Do not treat recommended probes as signed physical results.
- Do not claim benchmark agreement or completed bullet-through-steel
  behavior from this plan.
- Any Tier 2 promotion still needs benchmark source, tolerance,
  convergence evidence, sealed hashes, and independent review.
