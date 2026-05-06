# ENG-22 GS101 Opus/T0 Review Request

Date: 2026-05-06
Branch: codex/ENG-22-gs101-validation-gate
Linear issue: ENG-22
Scope: review-request template only; no external write performed.

## Review Objective

Decide whether to approve the narrow OpenRadioss solver-truth carve-out for future GS101 explicit-dynamics ballistic penetration validation.

This review must not approve a signed GS101 fixture, steel perforation result, validated physics claim, or any `golden_samples/**` mutation.

## Required Inputs

Review these repo-local artifacts:

- `reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md`
- `reports/codex_tool_reports/eng22_gs101_external_review_handoff.md`
- `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`

Then compare them against:

- `AGENTS.md`
- `.planning/STATE.md`
- `docs/adr/ADR-022-gs101-demo-unsigned-fixture.md`
- `docs/RFC-002-multi-solver-workbench-retrospective.md` section 4.1
- `golden_samples/GS-101-demo-unsigned/README.md`
- Linear ENG-22 through ENG-30

## Verdict Format

Return exactly one verdict:

- `APPROVE-CARVEOUT`
- `REJECT-CARVEOUT`
- `CHANGES_REQUIRED`
- `BLOCKER`

Use `APPROVE-CARVEOUT` only if all approval checks pass and the approval is limited to the solver-truth carve-out below:

> CalculiX remains the default structural solver truth. OpenRadioss may be accepted as solver truth only for explicit-dynamics ballistic penetration cases whose benchmark source, deck, runtime artifacts, validation tolerances, convergence evidence, and signoff are captured in Linear/GitHub evidence.

## Approval Checks

Reviewer must answer yes/no for each:

1. Does the packet preserve CalculiX as the default structural solver truth?
2. Does the packet limit OpenRadioss truth to explicit-dynamics ballistic penetration cases only?
3. Does the packet require a primary/public benchmark with residual velocity or perforation target metrics before deck authoring?
4. Does the packet forbid placeholder Johnson-Cook parameters as validation truth?
5. Does the packet keep `GS-101-demo-unsigned` demo-only?
6. Does the packet avoid mutating `golden_samples/**`, OpenRadioss decks, schemas, solver protocols, API/frontend, Notion sync, CI/governance policy, and dependencies?
7. Does the packet avoid claiming signed GS101, steel perforation completed, validated physics, or perfect simulation?
8. Does the packet define a mechanical notification threshold for future bullet-through-steel completion?
9. Does the evidence bundle preserve PR #141 as unrelated and PR #115 as pre-gate/backlog evidence?
10. Does the evidence bundle record enough local demo evidence, hashes, NaN/Inf scan, energy rows, and environment versions to support an external gate review?

## Demo Evidence Boundary

The current local GS-101-demo-unsigned evidence may support only:

- OpenRadioss starter/engine normal termination for the demo path;
- 11 generated animation frames;
- ballistic DOCX generation;
- no steel perforation observed.

The current evidence must not support:

- signed GS101;
- steel perforation completed;
- validated physics;
- benchmark agreement;
- any production or engineering signoff.

## Required Reviewer Output

Use this structure:

```text
Verdict: APPROVE-CARVEOUT | REJECT-CARVEOUT | CHANGES_REQUIRED | BLOCKER

Scope accepted:
- <one or two bullets>

Approval check table:
- 1: yes/no - <note>
- 2: yes/no - <note>
- 3: yes/no - <note>
- 4: yes/no - <note>
- 5: yes/no - <note>
- 6: yes/no - <note>
- 7: yes/no - <note>
- 8: yes/no - <note>
- 9: yes/no - <note>
- 10: yes/no - <note>

Required changes before approval:
- <empty if approved>

Allowed next step:
- If approved: ENG-24 benchmark source selection only.
- If rejected/changes/blocker: stop GS101 signed-validation continuation.

No-overclaim confirmation:
- GS-101-demo-unsigned remains demo-only.
- No steel perforation or validated physics claim is approved.
```

## Stop Conditions for Reviewer

Return `BLOCKER` instead of approval if any of these are true:

- The decision would imply signed GS101 before a public benchmark, real deck, artifact manifest, residual/perforation metrics, convergence evidence, and signoff exist.
- The decision would allow placeholder Johnson-Cook parameters as validation truth.
- The decision would allow mutating `golden_samples/**` before ENG-22 approval.
- The decision would treat PR #141 or GS-101-demo-unsigned as physical validation evidence.
- The decision would start ENG-25 deck authoring before ENG-24 benchmark truth exists.

## Dry-Run Linear Follow-Up After Review

No Linear write has been performed. If the reviewer returns a verdict, use this dry-run payload:

```markdown
ENG-22 external review returned: <VERDICT>.

Reviewer evidence:
- Review request: reports/codex_tool_reports/eng22_gs101_opus_review_request.md
- Gate packet: reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md
- Handoff: reports/codex_tool_reports/eng22_gs101_external_review_handoff.md
- Evidence bundle: reports/codex_tool_reports/eng22_gs101_evidence_bundle.json

Decision boundary:
- No signed GS101 claim is approved by demo evidence.
- No steel perforation is observed in GS-101-demo-unsigned.
- If approved, next work is ENG-24 benchmark source selection only.
```
