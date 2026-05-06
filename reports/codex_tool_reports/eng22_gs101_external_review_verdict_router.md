# ENG-22 GS101 External Review Verdict Router

Generated: 2026-05-06T22:30:00+08:00
Branch: codex/ENG-22-gs101-validation-gate
Linear issue: ENG-22
Scope: repo-local decision router only; no external write performed.

## Decision

Exactly one verdict is valid:

- `APPROVE-CARVEOUT`
- `REJECT-CARVEOUT`
- `CHANGES-REQUIRED`
- `BLOCKER`

Reject the review result as incomplete if:

- no single verdict value is present;
- multiple verdict values are present;
- reviewer proof/reference is missing;
- no-overclaim confirmation is missing;
- the allowed next step is ambiguous.

## Decision Outcome

| Verdict | Outcome | Allowed claim | Forbidden interpretation |
|---|---|---|---|
| `APPROVE-CARVEOUT` | Narrow carve-out accepted | OpenRadioss may be considered solver truth only for future explicit-dynamics ballistic penetration validation cases with benchmark/deck/artifact/metric/tolerance/convergence/signoff evidence | Signed GS101, validated physics, steel perforation completed, or OpenRadioss general solver truth |
| `REJECT-CARVEOUT` | Carve-out rejected | GS101 signed-validation path is blocked under current policy | Continuing ENG-24..ENG-30 as if approved |
| `CHANGES-REQUIRED` | Review packet is insufficient | Only reviewer findings may be addressed in repo-local proof/planning artifacts | Treating requested changes as approval |
| `BLOCKER` | Hard blocker found | GS101 signed-validation continuation is paused until blocker is resolved | Starting benchmark/deck/report work despite blocker |

## Immediate Action Matrix

| Verdict | Local action | External write | Downstream GS101 work |
|---|---|---|---|
| `APPROVE-CARVEOUT` | Prepare ENG-24 benchmark-source `/goal` and dry-run Linear/PR verdict payloads | Still requires explicit user approval | ENG-24 only; no ENG-25 deck authoring yet |
| `REJECT-CARVEOUT` | Prepare a repo-local rejection/blocker summary | Still requires explicit user approval | Stop ENG-24..ENG-30 signed-validation continuation |
| `CHANGES-REQUIRED` | Prepare a repo-local response table mapping each finding to allowed evidence updates | Still requires explicit user approval | Do not start ENG-24 |
| `BLOCKER` | Prepare a repo-local blocker report and pause continuation | Still requires explicit user approval | Do not start ENG-24..ENG-30 |

## Execution Gate

Before any follow-up action, run:

```bash
git status --short --branch
git diff --check origin/main..HEAD
.venv/bin/python -m json.tool reports/codex_tool_reports/eng22_gs101_evidence_bundle.json >/dev/null
.venv/bin/python scripts/check_commit_trailers.py --from-ref origin/main --require-codex-verified
git diff origin/main --name-status
```

Required conditions:

- branch is `codex/ENG-22-gs101-validation-gate`;
- committed diff is limited to `reports/codex_tool_reports/eng22_gs101*.md` and `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`;
- no `golden_samples/**`, deck, schema, protocol, API/frontend, Notion sync, CI/governance policy, dependency, or workflow-policy file is changed;
- evidence bundle JSON parses;
- diff whitespace and HF5 trailer checks pass;
- PR #141 remains unrelated to GS101 and must not be treated as validation evidence;
- PR #115 remains pre-gate/backlog evidence and must not be merged as-is.

## No-Overclaim Guard

Before writing any summary, Linear payload, PR text, or user handoff, verify:

| Phrase or claim | Allowed? | Replacement |
|---|---:|---|
| `signed GS101` | no | `No signed GS101 evidence exists yet.` |
| `validated physics` | no | `No validated physics claim is approved.` |
| `steel plate perforation completed` | no | `No steel perforation is observed in the demo evidence.` |
| `perfect simulation` | no | `Validation remains gated on benchmark, metrics, convergence, and signoff.` |
| `OpenRadioss is general solver truth` | no | `CalculiX remains default; OpenRadioss carve-out is narrow and conditional.` |
| `GS-101-demo-unsigned proves bullet-through-steel behavior` | no | `GS-101-demo-unsigned is software-path evidence only.` |

Allowed statements:

- `GS-101-demo-unsigned is software-path evidence only.`
- `No signed evidence exists yet.`
- `No benchmark comparison or residual/perforation agreement is established yet.`
- `Current demo bake/report terminates normally, but no steel perforation is observed.`
- `If approved, the next executable work is ENG-24 benchmark source selection only.`

## Dry-Run Payloads

Do not post externally without explicit user approval.

### APPROVE-CARVEOUT

```markdown
ENG-22 external review verdict: APPROVE-CARVEOUT.

Scope:
OpenRadioss may be considered solver truth only for future explicit-dynamics ballistic penetration validation cases whose benchmark source, deck, runtime artifacts, metrics, tolerances, convergence evidence, and signoff are captured in Linear/GitHub evidence.

No-overclaim boundary:
- GS-101-demo-unsigned remains software-path evidence only.
- No signed GS101 evidence exists yet.
- No steel perforation is observed in the demo.
- No benchmark comparison or residual/perforation agreement is established yet.

Allowed next step:
Start ENG-24 benchmark source selection only.
```

### REJECT-CARVEOUT

```markdown
ENG-22 external review verdict: REJECT-CARVEOUT.

Result:
OpenRadioss is not approved as GS101 solver truth under the current gate.

Stop line:
- Do not enter ENG-24..ENG-30.
- Do not mutate golden_samples/**.
- Keep GS-101-demo-unsigned demo-only.
- No signed GS101, steel perforation completion, or validated physics claim is approved.
```

### CHANGES-REQUIRED

```markdown
ENG-22 external review verdict: CHANGES-REQUIRED.

Result:
The current packet is not approved. Requested changes must be addressed as repo-local proof/planning artifacts unless a separate explicit approval expands scope.

Stop line:
- Do not start ENG-24.
- Do not mutate golden_samples/**.
- Do not claim signed GS101, validated physics, or steel perforation completion.
```

### BLOCKER

```markdown
ENG-22 external review verdict: BLOCKER.

Result:
GS101 signed-validation continuation is paused until the blocker is resolved.

Stop line:
- Do not enter ENG-24..ENG-30.
- Do not mutate golden_samples/**.
- Do not open or update PR/Linear/Notion state without explicit approval.
- Do not claim signed GS101, validated physics, or steel perforation completion.
```

## Provenance

This router is derived from:

- `AGENTS.md`
- `reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md`
- `reports/codex_tool_reports/eng22_gs101_evidence_bundle.json`
- `reports/codex_tool_reports/eng22_gs101_external_review_handoff.md`
- `reports/codex_tool_reports/eng22_gs101_opus_review_request.md`
- `reports/codex_tool_reports/eng22_gs101_external_review_readiness_checklist.md`
- `reports/codex_tool_reports/eng22_gs101_external_review_publish_packet.md`

Subagent review input:

- Codex 5.3 Spark read-only audit recommended a single verdict-to-action router because existing artifacts had evidence, request, checklist, and publish payloads but no unified state transition map for all four verdicts.
