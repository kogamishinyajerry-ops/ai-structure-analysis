# ENG-22 GS101 External Review Readiness Checklist

Date: 2026-05-06
Branch: codex/ENG-22-gs101-validation-gate
Purpose: one-page reviewer checklist before any ENG-22 external approval write-back.

## Decision Request

Reviewer must choose exactly one:

- `APPROVE-CARVEOUT`
- `REJECT-CARVEOUT`
- `CHANGES-REQUIRED`
- `BLOCKER`

Linear state snapshot:

- ENG-22: `Pending Review`, `verify:pending`
- ENG-24..ENG-30: `Todo`, `verify:pending`
- Dependency chain: ENG-24 may start only after ENG-22 `APPROVE-CARVEOUT`; ENG-25..ENG-30 remain downstream of benchmark/deck/artifact/metric/convergence readiness.

## Evidence Index

Repo-local artifacts:

- Gate packet: `reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md`
- Handoff: `reports/codex_tool_reports/eng22_gs101_external_review_handoff.md`
- Evidence bundle: `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`
- Review request: `reports/codex_tool_reports/eng22_gs101_opus_review_request.md`

Hard facts captured in the evidence bundle:

| Evidence | Snapshot |
|---|---|
| Linear ENG-22 | `Pending Review`, labels include `verify:pending`; decision gate only |
| Linear ENG-24..ENG-30 | `Todo`, labels include `verify:pending`; blocked downstream work |
| PR #141 | open, non-draft, mergeable, checks green, no review decision; unrelated AERON-04 evidence |
| PR #115 | open draft, mergeable, calibration-cap-check failed; pre-gate/backlog evidence only |
| GS-101-demo starter | `NORMAL TERMINATION`, `0 ERROR(S)`, `0 WARNING(S)` |
| GS-101-demo engine | `NORMAL TERMINATION`, 4777 cycles, 11 frames |
| NaN/Inf scan | no matches in starter/engine text logs |
| Energy rows | max recorded absolute energy error about 9.9%; final recorded error -7.4% |
| DOCX evidence | 3.00032 ms, 125.396 mm peak displacement, 0 facets, no perforation observed |
| Artifact hashes | rad/out/docx plus 11 frame hashes captured |
| VTU/viewport blocker | NumPy 2.4.4 with PyVista 0.43.1 / Matplotlib 3.8.2 ABI import failure; DOCX-only fallback succeeded |

## Acceptance Checks

Reviewer should check each before approval:

- [ ] The packet only requests a narrow OpenRadioss explicit-dynamics ballistic carve-out.
- [ ] CalculiX remains the default structural solver truth.
- [ ] GS-101-demo-unsigned remains demo-only.
- [ ] No `golden_samples/**` mutation is included.
- [ ] No OpenRadioss deck, schema, solver protocol, API/frontend, Notion sync, CI/governance policy, or dependency change is included.
- [ ] No signed GS101, validated physics, steel perforation, or benchmark agreement is claimed.
- [ ] Placeholder Johnson-Cook parameters are forbidden as validation truth.
- [ ] ENG-24 benchmark source selection is the only allowed next execution step after approval.
- [ ] Completion notification threshold requires benchmark source, deck, logs, frame list, hashes, residual/perforation metrics, tolerance comparison, convergence evidence, and review/signoff.

## No-Overclaim Wording

Forbidden:

- `signed GS101`
- `validated physics`
- `steel plate perforation completed`
- `perfect simulation`
- `OpenRadioss is general solver truth`
- any claim that GS-101-demo-unsigned proves real bullet-through-steel behavior

Allowed:

- `GS-101-demo-unsigned is software-path evidence only.`
- `No signed evidence exists yet.`
- `No benchmark comparison or residual/perforation agreement is established yet.`
- `Current demo bake/report terminates normally, but no steel perforation is observed.`

## Stop Line

If ENG-22 is not `APPROVE-CARVEOUT`, stop all signed-GS101 continuation:

- do not enter ENG-24..ENG-30 execution;
- do not edit `golden_samples/**`;
- do not author a signed GS101 deck or report;
- do not claim bullet-through-steel completion;
- do not treat PR #141, PR #115, or GS-101-demo-unsigned as physical validation evidence.

If ENG-22 is approved, start only ENG-24 benchmark-source selection. Do not start ENG-25 deck authoring until ENG-24 establishes a primary/public benchmark with residual velocity or perforation target metrics.

## Copy-Paste Reviewer Payload

```markdown
ENG-22 is ready for external carve-out review.

Decision requested:
Choose exactly one: APPROVE-CARVEOUT / REJECT-CARVEOUT / CHANGES-REQUIRED / BLOCKER.

Evidence:
- Gate packet: reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md
- Handoff: reports/codex_tool_reports/eng22_gs101_external_review_handoff.md
- Evidence bundle: reports/codex_tool_reports/eng22_gs101_evidence_bundle.json
- Review request: reports/codex_tool_reports/eng22_gs101_opus_review_request.md
- Readiness checklist: reports/codex_tool_reports/eng22_gs101_external_review_readiness_checklist.md

Current state:
- ENG-22 remains Pending Review / verify:pending.
- ENG-24..ENG-30 remain Todo / verify:pending.
- GS-101-demo-unsigned demonstrates software path only: normal termination, 11 frames, DOCX generation, no steel perforation observed.
- PR #141 is unrelated AERON-04 evidence and has no review decision.
- PR #115 is an open draft with calibration-cap-check failure; pre-gate/backlog evidence only.

No-overclaim boundary:
No signed GS101, validated physics, steel perforation completion, or public benchmark agreement is claimed.

If approved:
Start ENG-24 benchmark source selection only.

If rejected, changes-required, or blocker:
Stop GS101 signed-validation continuation until the blocker is resolved.
```
