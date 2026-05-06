# ENG-22 GS101 Bullet-vs-Steel Validation Gate Packet

Date: 2026-05-06
Owner: Codex primary executor
Linear issue: ENG-22
Branch: codex/ENG-22-gs101-validation-gate
Scope: repo-local proof/planning artifact only; no Linear/GitHub/Notion mutation.

## Gate Verdict

Go for external ENG-22 carve-out review. No-go for any signed GS101 claim, golden-sample mutation, or "bullet-through-steel simulation complete" notification.

The current state supports only this narrow claim:

- The GS-101-demo-unsigned software path can bake OpenRadioss frames and generate a ballistic DOCX.
- The demo does not show steel plate perforation.
- The demo does not provide physical validation, signed validation, or benchmark agreement.

## Source Truth Snapshot

Repo and policy sources read:

- `AGENTS.md`: Linear is work-control truth; GitHub/repo is code truth; external writes are gated; `golden_samples/**` is read-only unless a signed validation/golden-sample issue explicitly authorizes change; smoke/synthetic/demo paths are not signed validation.
- `.planning/STATE.md`: remaining GS101 work is blocked behind ENG-22/GS101 contract; PR #115 is backlog evidence, not a merge target as-is; PR #141 is separate AERON-04 work and outside GS101.
- `docs/adr/ADR-022-gs101-demo-unsigned-fixture.md`: GS-101-demo-unsigned is accepted only as a demo fixture and passes none of the signed-fixture acceptance gates.
- `docs/RFC-002-multi-solver-workbench-retrospective.md` section 4.1: signed GS-101 requires published experimental parameter comparison, erosion timing within +/-10% of experiment, and physics-engineer signoff.
- `golden_samples/GS-101-demo-unsigned/README.md`: demo uses placeholder Johnson-Cook failure values, imposed displacement, and reports no steel perforation.
- Linear ENG-22 through ENG-30 were read on 2026-05-06 through the Linear connector.
- PR #141 was read on 2026-05-06 through `gh pr view 141`.

GitHub state observed:

- PR #141: open, non-draft, mergeable, checks successful (`lint-and-test (3.11)`, `trailer-check`, `golden-samples-validation`, `calibration-cap-check`), no `reviewDecision`. Keep separate; do not merge, self-approve, or use as GS101 evidence.
- PR #115 / ENG-23: open draft, mergeable, `lint-and-test (3.11)` successful, `calibration-cap-check` failed. Treat as pre-gate/backlog evidence only; do not merge as-is.

## ENG-22 Blocker State

ENG-22 is still `Pending Review` with `verify:pending`.

Decision needed:

- CalculiX remains the default structural solver truth source.
- OpenRadioss may become solver truth only for explicit-dynamics ballistic penetration cases whose benchmark source, deck, runtime artifacts, and validation tolerances are captured in Linear/GitHub evidence.
- Until this carve-out is explicitly accepted, all GS101 work remains `validation-candidate` or `demo-unsigned` and must not be labeled `signed`.

Current hard blockers:

- No ENG-22 T0/Opus acceptance or rejection is recorded.
- No public benchmark source has been selected in repo/Linear context. ENG-24 must select exactly one primary/public experiment with residual velocity or perforation target metrics.
- No signed OpenRadioss bullet-vs-steel source deck exists.
- No validation-grade runtime artifact manifest exists.
- No residual-velocity/perforation metric comparison exists.
- No convergence matrix exists.
- No physics-engineer signoff exists.

## Benchmark Requirement

ENG-24 must create the benchmark truth before any physical validation claim:

- exactly one primary/public ballistic plate penetration experiment;
- citation and reproduction/copyright limits;
- projectile and plate geometry;
- material definitions and traceable Johnson-Cook or equivalent parameters;
- impact velocity and boundary conditions;
- residual velocity and/or perforation target metric;
- units and coordinate conventions;
- target tolerances, including RFC-002 section 4.1 erosion/perforation timing tolerance of +/-10% when applicable.

Secondary blog posts, unverifiable tables, LLM-generated material parameters, and placeholder Johnson-Cook parameters are invalid validation truth.

## No-Overclaim Rules

Do not write or say any of the following unless every item in "Notification Threshold" is satisfied and review/signoff evidence exists:

- "perfect simulation";
- "signed GS101";
- "steel perforation completed";
- "validated physics";
- "OpenRadioss is the repo's general solver truth";
- any statement implying that GS-101-demo-unsigned proves physical bullet-through-steel behavior.

Allowed wording before gate close:

- "GS-101-demo-unsigned demonstrates the software path only."
- "Current local bake terminated normally and generated a DOCX, but no steel perforation was observed."
- "The real bullet-vs-steel validation path is blocked on ENG-22 approval and ENG-24 benchmark selection."

## Ordered Execution Chain

| Order | Issue | Purpose | Prerequisites | Acceptance checks | Evidence required | Stop conditions |
|---:|---|---|---|---|---|---|
| 0 | ENG-22 | OpenRadioss solver-truth carve-out gate | Existing ADR-021/ADR-022/RFC-002 context | T0/Opus explicitly accepts or rejects carve-out; demo remains unsigned; no `golden_samples/**` mutation before approval | Review verdict, gate decision, repo packet, dry-run then approved Linear proof | Stop if carve-out rejected/undecided and next action would imply signed validation |
| 1 | ENG-24 | Public benchmark source and `validation_source.yaml` | ENG-22 approved for candidate benchmark work | Exactly one primary/public experiment selected; residual velocity or perforation target captured; units/materials/tolerances/reproduction limits documented | Source citation, `validation_source.yaml`, source-map notes, reviewer check | Stop if no public benchmark with target metrics can be identified or only placeholder parameters are available |
| 2 | ENG-25 | Free-flight OpenRadioss bullet-vs-plate source deck | ENG-22 approved; ENG-24 benchmark selected | Projectile initial velocity, plate thickness, contact, constraints, material IDs, Johnson-Cook/failure data, erosion, unit system, mesh/time-step metadata captured; no imposed-displacement shortcut | Deck files, deck provenance, parameter trace to ENG-24, preflight notes | Stop if deck requires unverifiable material parameters, golden-sample mutation, or signed fixture creation before gate approval |
| 3 | ENG-26 | Bake harness and artifact manifest | ENG-25 source deck ready | Starter/engine entrypoint works; normal termination; exit codes/logs captured; frame list and hashes captured; NaN/Inf and energy-error checks recorded | Starter log, engine log, exit status, frame manifest, artifact hashes, energy/error summary | Stop if OpenRadioss fails, frames are missing, energy diverges, or dependency/CI changes are required |
| 4 | ENG-27 | Reader hardening for signed benchmark fields | ENG-26 baked artifacts available | Real frames expose velocity/stress/strain/plastic strain/part/material partitions as raw solver quantities only; GS-100 and demo regressions stay compatible | Reader tests on real/candidate frames, field inventory, regression output | Stop if fields must be fabricated or Layer 1 would derive engineering quantities |
| 5 | ENG-28 | Residual velocity, energy, and true perforation metrics | ENG-26 artifacts; ENG-27 reader fields | Residual velocity, projectile kinetic energy, absorbed energy, mass loss/eroded fraction, crater/plug indicators, true perforation verdict based on exit/residual velocity or through-thickness evidence | Metric JSON/CSV, comparison script output, plotted histories if available | Stop if verdict relies on any-eroded-facet or lacks residual/through-thickness evidence |
| 6 | ENG-29 | Candidate/signed report and viewport storyboard | ENG-28 metrics ready | Report distinguishes demo-unsigned, validation-candidate, and signed; includes citation, assumptions, materials, BCs, energy balance, residual velocity, perforation verdict, convergence table placeholder/links, hashes, keyframes | DOCX/report artifact, viewport frames, screenshots/storyboard, artifact manifest | Stop if copy implies signed validation before ENG-30/signoff or VTU/viewport dependency blocker prevents required visuals |
| 7 | ENG-30 | Convergence and closeout packet | Full candidate pipeline ready | Mesh/time-step convergence matrix; public target comparison <= +/-10% where applicable; refinement drift <= 5-10%; double-blind verification; signoff state explicit | Convergence table, benchmark comparison, artifact hashes, independent review/signoff | Stop if no physics-engineer signature and requested label is `signed`; close only as validation-grade candidate |

## Notification Threshold

Notify the user that "bullet-through-steel simulation complete" only when all of these verifiable artifacts exist together:

1. ENG-22 carve-out is explicitly accepted with review evidence.
2. A public benchmark source exists with citation, geometry, materials, impact velocity, residual velocity or perforation target, tolerances, and reproduction limits.
3. A free-flight OpenRadioss deck exists and traces every validation-sensitive parameter to the benchmark or a cited material source.
4. Starter and engine logs show successful execution, normal termination, exit status, and no NaN/Inf blocker.
5. A complete frame list exists with artifact hashes for source deck, logs, animation frames, derived metrics, reports, and viewport/storyboard artifacts.
6. Residual velocity and/or through-thickness perforation evidence is computed from solver artifacts, not inferred from any eroded facet.
7. Metrics are compared to the benchmark tolerance; target error is within +/-10% where RFC-002/benchmark applies.
8. Mesh/time-step convergence evidence is recorded with <= 5-10% refinement drift or an explicitly accepted tighter/looser benchmark-specific criterion.
9. Review/signoff evidence exists: at minimum T0/Opus gate acceptance for the carve-out and an explicit physics-engineer signature for any `signed` label.
10. Linear/GitHub evidence links the exact deck, logs, frame manifest, metric outputs, artifact hashes, convergence packet, and signoff packet.

If any item is missing, the allowed notification is only a blocker/unblocked status update, not completion.

## Current GS-101-Demo-Unsigned Evidence

Local bake/report probe path: `/tmp/gs101-bake-codex`.

Observed artifacts:

- Starter deck output `model_00_0000.out` reports `NORMAL TERMINATION`, `0 ERROR(S)`, `0 WARNING(S)`.
- Engine output `model_00_0001.out` reports `NORMAL TERMINATION` and `TOTAL NUMBER OF CYCLES : 4777`.
- 11 animation frames exist: `model_00A001.gz` through `model_00A011.gz`.
- Engine output reports 30 `DELETE SOLID ELEMENT` lines, consistent with aluminum impactor erosion.
- No steel shell deletion/perforation evidence was observed.
- Generated DOCX `/tmp/gs101-bake-codex/GS-101-demo.docx` contains:
  - duration `3.00032 ms`;
  - peak displacement `125.396 mm`;
  - final eroded facets `0 facets`;
  - perforation event `not observed / no perforation observed`.

Hashes from local probe:

```text
37d538d7e4cbfc94159a13bbdeb92d645069b246bbdbcce125bcd42c46d29f05  /tmp/gs101-bake-codex/model_00_0000.rad
872a28fe51b7420f114ac2cea3f7b7251203c524b73c87ae5cb04ddbdd82882f  /tmp/gs101-bake-codex/model_00_0001.rad
2b064b3fa964ea8609f09aad325aadcc7ead43a55fcb7ce23364c5e2769e869e  /tmp/gs101-bake-codex/model_00_0000.out
83bb271070f5ec243df9840a792cce3b31f0ebc5fd39d662a7b6284845757a2e  /tmp/gs101-bake-codex/model_00_0001.out
c42708171eb6daad7dc49a64d42316ea0d5fc75d12324091262b1ca7b90d5873  /tmp/gs101-bake-codex/GS-101-demo.docx
```

Frame hashes:

```text
b9784b5910e0b8861c5bf9a9b5488f8ba3a65550292f2290a59b9de91fcd571e  model_00A001.gz
3e4e4fb0c111a3b09ed1f9da27f8bc99a325638c22b68b0e1593f17a93eef6bd  model_00A002.gz
96bbdddfaa1cf6b8f1a6becf155f4093131862f462338817cbf6a77430c488f1  model_00A003.gz
17593aaf2ae72d708be4a0be98b02cceffa3872199dc13aba42bb1862b5a3ffb  model_00A004.gz
d7e0719e916f998df21e906a184d91ef30064d1033e4d1cbd65643c2269e5d5b  model_00A005.gz
62477488f4c4fa18244e89c35ba8e8a7a1c614c448a0123fc28f09bec30bddf4  model_00A006.gz
bf90778981189200f0c580192892f9a26486e8772b8d1b94c3fcc84c45372c08  model_00A007.gz
782a40632df8cf59a498214cc69c4361dadb14f7d64ae15fde97fab80b3067d1  model_00A008.gz
2144bee642b50bec32210a575096497ce8ad157f8914270de91bd8a54ea566f6  model_00A009.gz
2ecfd41c3d7b294f8f19b0c61c27a7250e235eab7a03c537138d3f86b97d2b14  model_00A010.gz
9c4453d305cfc888fe376023cb46a2b0e76972b6a9858aa88b3a4f25835f2db4  model_00A011.gz
```

Interpretation:

- This evidence is sufficient to say the demo software path still runs locally.
- This evidence is not sufficient to say steel perforation occurred.
- This evidence is not sufficient to say physical validation passed.
- This evidence is not sufficient to create or promote a signed `golden_samples/GS-101/` fixture.

## Verification Commands and Outcomes

Commands run on 2026-05-06:

```bash
git status --short --branch
```

Outcome: started from `codex/ENG-38-aeron-well-harness-graph` with unrelated untracked files; switched to isolated branch `codex/ENG-22-gs101-validation-gate` from `origin/main`. Untracked files were not modified.

```bash
gh pr view 141 --json number,state,isDraft,mergeable,reviewDecision,statusCheckRollup,headRefName,baseRefName,url,updatedAt
```

Outcome: PR #141 open, non-draft, mergeable, checks successful, no review decision. No PR action taken.

```bash
gh pr view 115 --json number,state,isDraft,mergeable,reviewDecision,statusCheckRollup,headRefName,baseRefName,url,updatedAt
```

Outcome: PR #115 open draft, mergeable, no review decision, CI success for `lint-and-test (3.11)`, failure for `calibration-cap-check`. No PR action taken.

```bash
Linear fetch ENG-22..ENG-30
```

Outcome: ENG-22 remains `Pending Review` / `verify:pending`; ENG-24..ENG-30 are `Todo` / `verify:pending` and blocked by ENG-22 and downstream benchmark/deck/artifact readiness. ENG-23 is `Pending Review` / `verify:passed` but still bounded to pre-gate candidate tooling.

```bash
find /tmp/gs101-bake-codex -maxdepth 1 -type f -name 'model_00A*.gz' | wc -l
```

Outcome: 11 frames.

```bash
rg -n "NORMAL TERMINATION|DELETE SOLID|TOTAL NUMBER OF CYCLES|ERROR|WARNING" /tmp/gs101-bake-codex
```

Outcome: starter and engine normal termination; starter has `0 ERROR(S)` and `0 WARNING(S)`; engine has 30 solid deletions and 4777 cycles.

```bash
unzip -p /tmp/gs101-bake-codex/GS-101-demo.docx word/document.xml | tr '<' '\n' | rg -n "perforation|Perforation|not observed|0 facets|125|3\\.00|GS-101"
```

Outcome: DOCX contains duration, peak displacement, `0 facets`, and `not observed / no perforation observed`.

```bash
.venv/bin/python -m pytest backend/tests/test_ballistics.py backend/tests/test_ballistic_summary_draft.py backend/tests/test_report_cli.py -q -o addopts=''
```

Outcome: `78 passed in 1.86s`.

```bash
.venv/bin/report-cli --kind ballistic --openradioss-root /tmp/gs101-bake-codex --rootname model_00 --unit-system si-mm --project-id GS-101-DEMO --task-id BULLET-PLATE-INT25 --report-id RPT-GS101-DEMO-VTU-PROBE --output /tmp/gs101-bake-codex/GS-101-demo-vtu-probe.docx --viewport-out /tmp/gs101-vtu-codex --no-validate-template --no-figures
```

Outcome: DOCX export completed, but VTU viewport export failed and was downgraded to DOCX-only:

```text
VTUExportError: pyvista is required for VTU export but is not importable: numpy.core.multiarray failed to import
```

The underlying message states that a module compiled using NumPy 1.x cannot run in NumPy 2.4.4. This is recorded as a local dependency blocker for viewport/VTU evidence. No dependency or CI policy changes were made.

## Dry-Run Linear Payload

No Linear mutation was performed. Suggested dry-run comment for ENG-22:

```markdown
ENG-22 gate packet prepared repo-locally.

Value target:
Prepare the GS101 bullet-vs-steel validation gate so continuation toward real OpenRadioss perforation simulation does not over-claim demo evidence.

Current gate state:
- ENG-22 remains Pending Review / verify:pending.
- OpenRadioss solver-truth carve-out still needs explicit T0/Opus accept-or-reject.
- Existing GS-101-demo-unsigned remains demo-only and is not promoted.

Repo-local evidence:
- Packet: reports/codex_tool_reports/eng22_gs101_validation_gate_packet.md
- PR #141 checked separately: open, mergeable, checks green, no review decision; no action taken.
- PR #115 checked separately: open draft, calibration-cap-check failing; treat as pre-gate/backlog evidence only.
- Local GS-101-demo-unsigned bake/report: starter + engine normal termination, 11 frames, DOCX generation passes.
- Honest demo result: no steel plate perforation observed; no signed validation claimed.
- VTU/viewport evidence is blocked locally by NumPy/PyVista binary incompatibility.

Decision needed:
Approve or reject the narrow OpenRadioss explicit-dynamics ballistic solver-truth carve-out. If approved, next executable step is ENG-24 benchmark-source selection. If rejected or undecided, do not start signed GS101 fixture/deck work.
```

## Recommendation

Proceed with external ENG-22 review/approval request using this packet. Do not continue into ENG-24..ENG-30 execution until ENG-22 is accepted and a primary public benchmark with residual-velocity or perforation target metrics is selected.
