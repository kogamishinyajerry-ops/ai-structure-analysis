# ENG-22 GS101 External Review Publish Packet

## Metadata & Scope

Date: 2026-05-06
Linear issue: ENG-22
Branch: codex/ENG-22-gs101-validation-gate
Purpose: unified dry-run packet for external review write-up.

Decision options:

- `APPROVE-CARVEOUT`
- `REJECT-CARVEOUT`
- `CHANGES-REQUIRED`

Scope boundary:

- This packet does not perform any Linear, GitHub, or Notion write.
- This packet does not approve ENG-22 by itself.
- This packet does not start ENG-24, ENG-25, or any downstream GS101 execution.
- This packet does not mutate `golden_samples/**`, OpenRadioss decks, schemas, solver protocols, API/frontend, Notion sync, CI/governance policy, or dependencies.

## Evidence Index

Core repo-local evidence:

| File | Role |
|---|---|
| `reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md` | Full ENG-22 gate packet: blocker state, benchmark requirement, ENG-24..ENG-30 chain, notification threshold, local demo evidence, dry-run Linear payload |
| `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json` | Compact machine-readable evidence: Linear/PR snapshots, demo artifact hashes, NaN/Inf scan, energy rows, environment versions, VTU blocker |
| `reports/codex_tool_reports/eng22_gs101_external_review_handoff.md` | Reviewer decision request, dry-run Linear comment, dry-run PR addendum, ENG-24 next-goal text |
| `reports/codex_tool_reports/eng22_gs101_opus_review_request.md` | Opus/T0 verdict format and approval checks |
| `reports/codex_tool_reports/eng22_gs101_external_review_readiness_checklist.md` | One-page external review readiness checklist |

Hard facts captured:

- ENG-22: `Pending Review`, `verify:pending`; carve-out decision still required.
- ENG-24..ENG-30: `Todo`, `verify:pending`; all remain downstream of ENG-22 and benchmark/deck/artifact/metric/convergence readiness.
- PR #141: open, non-draft, mergeable, checks green, no review decision; unrelated AERON-04 evidence.
- PR #115: open draft, mergeable, calibration-cap-check failed; pre-gate/backlog evidence only.
- Local GS-101-demo-unsigned bake path: starter/engine `NORMAL TERMINATION`; starter `0 ERROR(S)` and `0 WARNING(S)`; 11 animation frames.
- NaN/Inf scan: no matches in starter/engine text logs.
- Energy evidence: max recorded absolute energy error about 9.9%; final recorded error -7.4%.
- DOCX evidence: 3.00032 ms, 125.396 mm peak displacement, 0 facets, no perforation observed.
- Artifact hashes: source rad files, starter/engine logs, DOCX outputs, and 11 frame hashes captured in the evidence bundle.
- VTU/viewport blocker: NumPy 2.4.4 with PyVista 0.43.1 / Matplotlib 3.8.2 ABI import failure; DOCX-only fallback succeeded.

## Review Verdict Checklist

Reviewer fills `yes` or `no` and notes. Approval requires all checks to be `yes`.

| # | Approval check | yes/no | Note |
|---:|---|---|---|
| 1 | CalculiX remains the default structural solver truth. |  |  |
| 2 | OpenRadioss truth is limited to explicit-dynamics ballistic penetration cases only. |  |  |
| 3 | A primary/public benchmark with residual velocity or perforation target metrics is required before deck authoring. |  |  |
| 4 | Placeholder Johnson-Cook parameters are forbidden as validation truth. |  |  |
| 5 | `GS-101-demo-unsigned` remains demo-only. |  |  |
| 6 | No `golden_samples/**`, deck, schema, protocol, API/frontend, Notion sync, CI/governance policy, or dependency mutation is included. |  |  |
| 7 | No signed GS101, steel perforation completed, validated physics, or perfect simulation claim is made. |  |  |
| 8 | Future completion notification threshold is mechanical and artifact-based. |  |  |
| 9 | PR #141 remains unrelated and PR #115 remains pre-gate/backlog evidence. |  |  |
| 10 | Evidence bundle is sufficient for external gate review without relying on chat history. |  |  |

Reviewer verdict:

```text
Verdict: APPROVE-CARVEOUT | REJECT-CARVEOUT | CHANGES-REQUIRED
Required changes before approval:
- <fill in>
Allowed next step:
- <fill in>
No-overclaim confirmation:
- <fill in>
```

## Copy-Paste Payloads

### Linear Payload

Do not post unless external writes are explicitly authorized and the ENG-22 review verdict allows it.

```markdown
ENG-22 external review packet is ready.

Decision requested:
APPROVE-CARVEOUT / REJECT-CARVEOUT / CHANGES-REQUIRED.

Evidence:
- Gate packet: reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md
- Evidence bundle: reports/codex_tool_reports/eng22_gs101_evidence_bundle.json
- Handoff: reports/codex_tool_reports/eng22_gs101_external_review_handoff.md
- Opus/T0 review request: reports/codex_tool_reports/eng22_gs101_opus_review_request.md
- Readiness checklist: reports/codex_tool_reports/eng22_gs101_external_review_readiness_checklist.md
- Publish packet: reports/codex_tool_reports/eng22_gs101_external_review_publish_packet.md

Current state:
- ENG-22 remains Pending Review / verify:pending.
- ENG-24..ENG-30 remain Todo / verify:pending.
- GS-101-demo-unsigned is software-path evidence only.
- No steel perforation is observed.
- No signed evidence, benchmark comparison, or residual/perforation agreement is established yet.

Stop if not approved:
- Do not enter ENG-24..ENG-30.
- Do not edit golden_samples/**.
- Do not author signed GS101 deck/report work.
- Do not claim bullet-through-steel completion or validated physics.

If approved:
Start ENG-24 benchmark source selection only.
```

### PR Body Addendum

Do not open or update a PR unless external writes are explicitly authorized and the ENG-22 review verdict allows it.

```markdown
## ENG-22 Gate Scope

This PR contains repo-local proof and review artifacts only. It does not merge solver code, OpenRadioss decks, schemas, protocols, golden samples, dependencies, CI/governance policy, API/frontend changes, or Notion sync changes.

## Decision Requested

External reviewer must choose: APPROVE-CARVEOUT / REJECT-CARVEOUT / CHANGES-REQUIRED.

## Evidence Boundary

- GS-101-demo-unsigned is software-path evidence only.
- Local demo evidence shows normal termination, 11 frames, and DOCX generation.
- No steel perforation is observed.
- No signed evidence, benchmark comparison, or residual/perforation agreement is established yet.

## Allowed Next Step

If ENG-22 is approved, start ENG-24 benchmark source selection only. Do not start ENG-25 deck authoring until ENG-24 establishes a primary/public benchmark with residual velocity or perforation target metrics.
```

### Reviewer-Facing Change Summary

```markdown
This branch prepares the ENG-22 decision gate for a narrow OpenRadioss explicit-dynamics ballistic solver-truth carve-out.

It adds five review/proof artifacts plus this publish packet under reports/codex_tool_reports/. The artifacts define the blocker state, ordered ENG-24..ENG-30 chain, notification threshold, local demo evidence, evidence hashes, review verdict format, and no-overclaim rules.

The branch does not claim signed GS101, validated physics, or steel perforation. The current GS-101-demo-unsigned bake/report only proves the software path can run locally and generate a DOCX; the DOCX says no perforation observed.
```

## Publish Safety

Allowed wording:

- `GS-101-demo-unsigned is software-path evidence only.`
- `No signed evidence exists yet.`
- `No benchmark comparison or residual/perforation agreement is established yet.`
- `Current demo bake/report terminates normally, but no steel perforation is observed.`

Forbidden wording:

- `signed GS101`
- `validated physics`
- `steel plate perforation completed`
- `perfect simulation`
- `OpenRadioss is general solver truth`
- any statement that GS-101-demo-unsigned proves real bullet-through-steel behavior

Stop line:

- If ENG-22 has not explicitly returned `APPROVE-CARVEOUT`, do not perform external write-back for Linear comments, PR opening, PR comments, Notion updates, or GitHub state changes.
- If ENG-22 is rejected or changes-required, stop GS101 signed-validation continuation until the blocker is resolved.
- Do not enter ENG-24..ENG-30 execution unless ENG-22 is `APPROVE-CARVEOUT`.
- Do not edit `golden_samples/**`.
- Do not start signed-grade deck/report work.
- Do not claim bullet-through-steel completion.

## Pre-Publish Local Check

Run before any future authorized external write:

```bash
git status --short --branch
git diff --check origin/main..HEAD
.venv/bin/python -m json.tool reports/codex_tool_reports/eng22_gs101_evidence_bundle.json >/dev/null
.venv/bin/python scripts/check_commit_trailers.py --from-ref origin/main --require-codex-verified
git diff origin/main --name-status
```

Required local result:

- branch is `codex/ENG-22-gs101-validation-gate`;
- diff is limited to `reports/codex_tool_reports/eng22_gs101*.md` and `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`;
- no forbidden paths are changed;
- JSON, whitespace, and trailer checks pass.
