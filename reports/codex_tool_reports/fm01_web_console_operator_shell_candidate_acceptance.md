# FM-01 Web Console Operator Shell Candidate Acceptance Packet

- Date: 2026-05-07
- Milestone: FM-01 Web Console Operator Shell
- Claim tier: Tier 0 sandbox/demo
- Status: candidate ready for human milestone-level experience check
- Human acceptance: pending

## Candidate Scope

FM-01 targets a visible Web Console operator shell where a user can open the
workbench and see workflow state, backend provenance, claim tier, and next
allowed action without reading repo history.

This packet is a candidate acceptance bundle. It does not claim signed
validation, validated physics, or completed human acceptance.

## Included Issue-Level Slices

| Issue | PR | Merge commit | Result |
|---|---|---|---|
| ENG-40 | <https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/144> | `776fdae401eaecd2986bad6aa9fd30a3fd6067e4` | Added the first Tier 0 operator status shell. |
| ENG-41 | <https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/145> | `4a6caf1da9e0e13211c49f6d760341725c72cce2` | Persisted delegated Claude Opus issue-level owner gate and human milestone acceptance boundary. |
| ENG-42 | <https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/146> | `222e9f4f500fb67df0c593e30c4398308007d692` | Made the operator shell derive case, run, evidence, latest-event, and next-action values from existing frontend state. |
| ENG-43 | <https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/147> | `f133f5a2c7e653612aa5c71866ce18213113b1d8` | Added current solver job id/status, analysis mode, and software-path backend provenance to the operator shell. |

## Proof Artifacts

| Artifact | Purpose |
|---|---|
| `reports/codex_tool_reports/eng40_fm01_operator_shell.png` | Baseline operator shell screenshot. |
| `reports/codex_tool_reports/eng40_fm01_operator_shell_smoke.md` | ENG-40 smoke evidence. |
| `reports/codex_tool_reports/eng40_fm01_operator_shell_claude_audit.md` | ENG-40 Claude review evidence. |
| `reports/codex_tool_reports/eng42_dynamic_operator_state.png` | Dynamic operator state screenshot. |
| `reports/codex_tool_reports/eng42_dynamic_operator_state_smoke.md` | ENG-42 smoke evidence. |
| `reports/codex_tool_reports/eng42_dynamic_operator_state_claude_audit.md` | ENG-42 Claude review evidence. |
| `reports/codex_tool_reports/eng43_job_provenance.png` | Job/provenance operator shell screenshot. |
| `reports/codex_tool_reports/eng43_job_provenance_smoke.md` | ENG-43 smoke evidence. |
| `reports/codex_tool_reports/eng43_job_provenance_claude_audit.md` | ENG-43 Claude review evidence. |

## Local Experience Path

Frontend-only idle shell:

```text
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

Expected first-viewport signals:

- `Operator status`
- `FM-01 Web Console Operator Shell`
- `Tier 0 sandbox/demo`
- `software-path evidence only`
- `Active case`
- `Analysis mode`
- `Current job`
- `Run state`
- `Evidence state`
- `Backend provenance`
- `Latest event`
- `Next action`

Full case/solver interaction requires the existing backend API to be available
at `http://localhost:8000/api/v1`. FM-01 does not add backend endpoints or
change solver behavior.

## Human Acceptance Checklist

Use this checklist only at the milestone-level experience checkpoint:

- The Web Console opens to a usable operator surface.
- The first viewport makes the current workflow state understandable without
  reading repo history.
- The claim tier and `software-path evidence only` wording are visible.
- The idle state clearly tells the user to select a gallery case or upload an
  FRD file.
- When a run is started in a configured backend environment, the panel exposes
  analysis mode, current job id/status, backend provenance, and latest event.
- No Tier 0 evidence is presented as signed validation or validated physics.

## Limitations

- This is Tier 0 sandbox/demo evidence.
- Browser smoke evidence used installed Google Chrome headless because local
  Python and Node Playwright packages were unavailable.
- The candidate packet does not prove real solver correctness or physical
  accuracy.
- Notion was not mutated by the FM-01 issue-level slices.
- Human acceptance is pending and must be recorded separately after experience
  review.

## Next Milestone Options

After human FM-01 acceptance, the next development choice is:

- FM-02 if the priority is one AERON-backed solve path through a user-facing
  caller.
- Another FM-01 polish slice only if the user experience check finds a concrete
  operator-shell gap.
