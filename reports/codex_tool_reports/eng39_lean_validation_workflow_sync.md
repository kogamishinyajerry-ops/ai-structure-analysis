# ENG-39 Lean Validation Workflow Sync Report

Date: 2026-05-06

Branch: `codex/ENG-39-lean-validation-workflow`

Linear issue: ENG-39

Scope: record the repo, Linear, GitHub, and Notion synchronization for the lean
validation workflow adjustment.

## Decision Summary

The project is shifting from heavy truth-management on every development step to
a claim-boundary workflow:

- Tier 0 sandbox/demo work moves quickly with explicit `demo-only` /
  `software-path evidence only` labels.
- Tier 1 engineering-candidate work captures a compact reproducibility spine:
  manifest, logs, units/material/BC/contact assumptions, hashes, limitations,
  and read-only Opus review when triggered.
- Tier 2 signed validation remains strict and requires benchmark source,
  metrics, tolerance comparison, convergence evidence, artifact hashes, and
  reviewer/signoff before physical-validation claims.

## Repo Artifacts

- `docs/adr/ADR-023-lean-validation-workflow.md`
- `AGENTS.md`
- `README.md`
- `docs/governance/routing.md`
- `docs/governance/onboarding.md`
- `.planning/STATE.md`

## External Sync Status

| Surface | Status | Evidence |
|---|---|---|
| Linear | created | ENG-39 `Lean validation workflow: fast candidate lane with strict signed-claim gate`, state `In Progress`, project `Governance` |
| GitHub | pending | PR not opened yet at initial artifact creation |
| Notion | pending | Mirror update planned after repo branch/PR and Linear issue are established; no Notion write has been performed |

## Notion Mirror Payload (proposed, not written)

Target root page: `345c68942bed80f6a092c9c2b3d3f5b9`

Proposed mirror entry:

```markdown
## 2026-05-06 · Lean Validation Workflow

The project is adopting a faster claim-boundary validation workflow.

Development lanes:
- Tier 0 Sandbox / Demo: fast iteration, software-path evidence only, no validation claim.
- Tier 1 Engineering Candidate: reproducible candidate with manifest, logs, units/material/BC/contact trace, hashes, limitations, and read-only Opus review when triggered.
- Tier 2 Signed Validation: strict physical-claim gate with public benchmark, metrics, tolerance comparison, convergence evidence, hashes, and reviewer/signoff.

What changes:
- ordinary demo/candidate development should move faster;
- duplicate validation packets/checklists should be avoided below Tier 2;
- local Claude Opus is called automatically as a read-only reviewer when reviewer evidence is required.

What does not change:
- demo-only fixtures are not signed validation;
- GS-101-demo-unsigned remains software-path evidence only;
- physical claims still require benchmark/convergence/signoff;
- Linear remains work-control truth, GitHub/repo remains code truth, Notion remains a mirror.

Repo truth:
- Linear: ENG-39
- ADR: docs/adr/ADR-023-lean-validation-workflow.md
- Branch: codex/ENG-39-lean-validation-workflow
```

## Verification Plan

```bash
.venv/bin/python scripts/check_commit_trailers.py --from-ref origin/main --require-codex-verified --require-reviewed-by
git diff --check origin/main..HEAD
python3 scripts/compute_calibration_cap.py --human
```

No solver deck, golden sample, schema, CI, dependency, or Notion sync code change
is required for this workflow adjustment.

## Claude Review Status

- R1 report: `reports/codex_tool_reports/eng39_lean_validation_workflow_claude_audit.md`
- R1 verdict: `CHANGES_REQUIRED`
- R2 verdict: `APPROVE`
- R1 remediation:
  - keep unrelated untracked files out of the ENG-39 PR;
  - make ADR-023 forbidden-claim wording explicit;
  - make the Notion mirror payload status explicit as proposed, not written.
