# ENG-22 GS101 External Review Handoff

Date: 2026-05-06
Branch: codex/ENG-22-gs101-validation-gate
Base packet: `reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md`
Evidence bundle: `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`
Scope: dry-run handoff only; no external mutation performed.

## Reviewer Decision Request

Please review ENG-22 and explicitly choose one decision:

1. `APPROVE-CARVEOUT`: CalculiX remains the default structural solver truth, but OpenRadioss may be accepted as solver truth for explicit-dynamics ballistic penetration cases only when benchmark source, deck, runtime artifacts, metrics, tolerances, convergence evidence, and signoff are captured in Linear/GitHub evidence.
2. `REJECT-CARVEOUT`: OpenRadioss must not be used as solver truth for GS101; GS101 remains demo/candidate only.
3. `CHANGES-REQUIRED`: ENG-22 packet is not sufficient; reviewer must list the missing evidence or policy change needed before approval.

## Non-Negotiable Evidence Boundary

The current repo-local packet supports only a software-path claim:

- GS-101-demo-unsigned can bake and generate a ballistic DOCX locally.
- The run terminates normally and produces 11 animation frames.
- The generated DOCX reports `0 facets` and `not observed / no perforation observed`.

It does not support:

- signed GS101;
- steel perforation completed;
- validated physics;
- public benchmark agreement;
- promotion of `GS-101-demo-unsigned` to signed validation.

## Approval Preconditions to Check

Before approving ENG-22, reviewer should confirm:

- ENG-22 remains the only gate being decided; PR #141 is unrelated AERON-04 work.
- No `golden_samples/**` mutation is bundled with the gate decision.
- PR #115 / ENG-23 remains pre-gate/backlog evidence and is not merged as-is.
- The next executable work after approval is ENG-24 benchmark selection, not deck authoring.
- Placeholder Johnson-Cook parameters are explicitly forbidden as validation truth.
- Any future completion notification is tied to benchmark source, deck, logs, frame list, hashes, residual/perforation metrics, tolerance comparison, convergence evidence, and review/signoff.

## Dry-Run Linear Comment

```markdown
ENG-22 review handoff prepared repo-locally.

Decision requested:
Choose one of APPROVE-CARVEOUT / REJECT-CARVEOUT / CHANGES-REQUIRED for the narrow OpenRadioss explicit-dynamics ballistic solver-truth carve-out.

Repo evidence:
- Gate packet: reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md
- Review handoff: reports/codex_tool_reports/eng22_gs101_external_review_handoff.md
- Evidence bundle: reports/codex_tool_reports/eng22_gs101_evidence_bundle.json
- Commit range: origin/main..codex/ENG-22-gs101-validation-gate

Current honest state:
- GS-101-demo-unsigned local bake/report path passes as software-path evidence.
- No steel plate perforation is observed.
- No signed GS101 or validated physics claim is made.
- VTU/viewport evidence is blocked locally by NumPy/PyVista binary incompatibility.

Recommended next step if approved:
Start ENG-24 only: select exactly one primary/public benchmark source with residual velocity or perforation target metrics and capture it in validation_source.yaml.

Stop if rejected or undecided:
Do not mutate golden_samples/**, do not author a signed GS101 deck, and do not claim bullet-through-steel completion.
```

## Dry-Run PR Body Addendum

```markdown
## ENG-22 Gate Summary

This PR is repo-local proof/planning only. It adds no solver code, deck, schema, golden sample, CI policy, dependency, frontend, API, or Notion sync change.

It prepares the ENG-22 decision gate for whether OpenRadioss can be solver truth only for explicit-dynamics ballistic penetration validation with benchmark-backed evidence. It does not approve the carve-out by itself.

No-overclaim state:
- GS-101-demo-unsigned remains demo-only.
- Local bake/report evidence shows normal termination and DOCX generation, but no steel perforation.
- Signed validation remains blocked on ENG-22 approval, ENG-24 benchmark selection, real deck/artifacts, residual/perforation metrics, convergence evidence, and signoff.
```

## Next Goal Only After ENG-22 Approval

Do not start this goal unless ENG-22 is explicitly approved.

```text
/goal Prepare ENG-24 GS101 public benchmark source selection for a future validation-candidate OpenRadioss bullet-vs-steel simulation.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis.
  - Read first: AGENTS.md, .planning/STATE.md, ENG-22 approval evidence, ENG-24, reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md, reports/codex_tool_reports/eng22_gs101_external_review_handoff.md.
  - Produce or update only repo-local proof/planning artifacts and the proposed validation_source.yaml location if ENG-24 explicitly authorizes that path.

Constraints:
  - Do not mutate golden_samples/**, OpenRadioss decks, schemas, solver protocols, API/frontend, Notion sync, CI/governance policy, or dependencies.
  - Do not use placeholder Johnson-Cook parameters as validation truth.
  - Do not claim signed GS101, steel perforation completed, or validated physics.
  - External Linear/GitHub/Notion writes remain dry-run unless explicitly approved.

Done when:
  1. Exactly one primary/public ballistic plate penetration benchmark candidate is selected or a blocker is recorded.
  2. Citation, geometry, materials, impact velocity, residual velocity or perforation target, boundary conditions, units, tolerances, and reproduction limits are captured.
  3. Source credibility and copyright/reproduction constraints are documented.
  4. Acceptance checks for ENG-25 deck authoring are derived from the benchmark.
  5. Verification commands and source-access outcomes are recorded.

Stop if:
  - No public benchmark with residual velocity or perforation target metrics can be identified.
  - Required material or Johnson-Cook parameters are not traceable to the benchmark or a credible cited source.
  - Any next action requires golden_samples/** mutation, dependency changes, CI policy changes, or signed validation before benchmark truth is established.
```

## Chinese User Handoff

当前建议：可以把 ENG-22 gate packet 交给外部 reviewer 做 carve-out 审批；不能继续声称子弹穿透钢板已经完成。批准后只进入 ENG-24：先找一个公开、可引用、带残余速度或穿透目标指标的真实实验 benchmark。没有 benchmark，就不要写真实 deck，也不要做 signed GS101。
