# Phase 33 C · Dim 6 — Trust & reproducibility (synthesis)

> Scored by main session because Dim 6 is best measured by structural
> inventory of audit-trail / snapshot / signoff / ADR / failed-attempt
> infrastructure. File:line evidence per RUBRIC v2.0 D:-1.

## Inventory (codebase as of `c581746`)

### Case directories + manifests (60 anchor)

- 21 directories under `golden_samples/*-candidate/`
- 11 with `cross_check_verdict.yaml` (validated cohort)
- 10 are scaffolded but not yet validated (`*-candidate` dirs without verdict)
- Each validated case has: `data/<case>.geo` + `expected_results.json` + `cross_check_verdict.yaml` + (for some) `convergence_study.json` + (for cantilever-modal) `convergence_study_r2.json`

### Schema versioning (70 anchor)

`grep -rn "schema_version" backend/app/services` shows ≥5 distinct
schema_version fields:
- `structural-deformation-animation-manifest.v1` (`backend/app/services/structural_animation.py:202`)
- `fm03-candidate-report-spine.*` (`backend/app/services/candidate_report_markdown.py:103`)
- Verdict YAML schema (1.0.0 / 1.1.0 / 1.2.0 / 1.3.0 across phases)
- Convergence study schema 1.0.0 → 1.1.0 (Phase 31 C additive `richardson` field)
- CASE_COMPLETENESS_SCHEMA 1.0.0 → 1.1.0 (Phase 11 analysis-type-aware)

### Cohort snapshots (80 anchor)

5 snapshots at `reports/snapshots/`:
- `2026-05-16T105918Z`
- `2026-05-16T105945Z`
- `2026-05-16T110004Z`
- `2026-05-16T110112Z`
- `2026-05-16T110131Z`

Phase 5 (`fd23f7f..4df64e2`) shipped the snapshot infrastructure.

### Reviewer signoffs (80 anchor)

`find reports/signoffs -type f | wc -l = 3` signoffs.
ALL 3 in `reports/signoffs/cylinder-pv-candidate/`:
- `2026-05-16T110004Z.json`
- `2026-05-16T110113Z.json`
- `2026-05-16T110132Z.json`

**Coverage: 1/11 validated cases (≈9%).** Signoff infrastructure
exists; corpus is minimal.

### Cross-validation pinning (80 anchor)

Multiple tests confirm cross-validation pinning:
- `backend/tests/test_phase31c_richardson.py` — re-runs Richardson
  math from convergence_study.json points and asserts agreement at
  ≥6 digits
- `backend/tests/test_phase32a_convergence_ubiquity.py:30` — same
  pattern across 3 cases
- Verdict YAML / INP / .dat round-trip pins exist

### Provenance chain (90 anchor)

`grep -rn "provenance" frontend/src/components | head` — multiple
components surface provenance:
- `ProvenancePanel.tsx` — provenance summary panel
- `trustCenterSummary.ts` — composite trust summary
- `CaseSummaryPanel.tsx` — case-level provenance (snapshot_id +
  signoff_id when present)

Provenance overlays present on ≥3 UI surfaces. **NOT yet at every
UI step** (e.g., not in toast notifications, not in error states).

### ADR archive (90 anchor)

`docs/adr/` contains 15 ADRs (`ls docs/adr/ | wc -l = 15`):
- ADR-011 through ADR-025 enumerated
- ≥10 requirement: **MET**

### Trust score (90 anchor)

Phase 11 introduced `case_completeness_schema` + analysis-type-aware
rubrics (ballistic / linear_static_pv / explicit_dynamics / modal)
with trust_score axes including `convergence_kind` discriminator.
Trust score is computed and rendered in `TrustCenterPanel.tsx`.

### Failed-attempt corpus (95 anchor)

`.planning/failed_attempts/` directory: **does NOT exist** as
indexed corpus. Failed-attempt narratives are scattered across:
- Retrospective files (Phase 28 A NotImplementedError, Phase 31 A
  contact-pair recon, Phase 31 C cylinder-pv BC redesign deferral,
  Phase 32 A plate-ss Richardson p≤0)
- Case NOTES.md files (e.g., `golden_samples/heat-transfer-1d-candidate/NOTES.md`)
- Phase blueprint recon sections

**Indexed corpus: 0 entries at the canonical path.** Phase 32
FINAL named this as a Phase 33 Tier-2 priority.

### ADR cross-reference matrix (95 anchor)

`.planning/adrs/CROSS_REFERENCE.md`: **does NOT exist**. ADRs are
linked from individual ADR bodies but no cross-reference matrix.

### Audit-trail log (99 anchor)

`backend/app/services/audit_log.py`: **does NOT exist**. No central
audit-trail infrastructure. Per-operation timestamps live in
verdict YAML + snapshot metadata but no unified audit log.

### Reproducibility CLI (99 anchor)

`cli/reproduce.py` or equivalent: **does NOT exist**. Case directories
contain all needed artifacts for manual reproduction but no `harness
reproduce <case-id>` CLI shipping.

## Anchor matching

| Anchor | Status | Sub-bullet detail |
|---|---|---|
| 60 | ✓ | case dirs + INP + manifest all present |
| 70 | ✓ | schema_version everywhere + verdict YAML stable |
| 80 | partial (~70%) | snapshots ✓ + cross-val pinning ✓ + signoffs partial (1/11 cases) |
| 90 | partial (~55%) | full provenance at every UI step partial; ADR ≥10 ✓; trust_score ✓ |
| 95 | partial (~10%) | failed-attempt corpus 0/10; ADR cross-link matrix absent |
| 99 | ~0% | audit-trail log absent; reproduce CLI absent |

## Score interpolation

- 70 fully met → 70
- 80 anchor: 2/3 bullets fully met (snapshots + cross-val), signoffs
  partial — net 70 + ~6 = **76**
- 90 anchor bullets that DO contribute (independent of 80):
  - ADR ≥10 ✓ (rare positive)
  - trust_score ✓
  - Adds ~1 point for "infrastructure above 80 floor"

**Dim 6 score: 72/100**

Confidence: high.

The score honestly reflects that Phase 22-32 work built solid Trust
infrastructure (schema versioning, snapshots, ADR archive, trust score),
but two Tier-1 sub-bullets are absent:
1. Failed-attempt corpus (95 anchor blocker)
2. Audit-trail log + reproducibility CLI (99 anchor blocker)

And one 80-anchor bullet is severely under-coveraged:
3. Reviewer signoffs (only 1/11 cases have any signoffs)

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 21 candidate dirs | `ls golden_samples/*-candidate/ \| wc -l` |
| 11 validated | `find golden_samples -name "cross_check_verdict.yaml" \| wc -l` |
| 5 snapshots | `ls reports/snapshots/` |
| 3 signoffs / 1 case | `find reports/signoffs -type f` |
| 15 ADRs | `ls docs/adr/` |
| schema_version pervasive | `grep -rn "schema_version" backend/app/services` |
| trust_score present | `TrustCenterPanel.tsx` |
| ADR cross-link matrix absent | `ls .planning/adrs/CROSS_REFERENCE.md` ENOENT |
| failed_attempts dir absent | `ls .planning/failed_attempts/` ENOENT |
| audit_log absent | `find backend/app -name "audit_log*.py"` empty |
| reproduce CLI absent | `find . -name "reproduce*.py"` empty (outside venv) |

## Phase 34+ priorities derived from this score

| Priority | Item | Anchor blocked | Composite lift |
|---|---|---|---|
| 1 | Failed-attempt corpus index (`.planning/failed_attempts/INDEX.md` + ≥5 initial entries) | 95 | +1.5-2.5 (Phase 40 target) |
| 2 | Audit-trail log infrastructure | 99 | +2-3 |
| 3 | Reproducibility CLI | 99 | +2-3 |
| 4 | Reviewer signoff coverage to ≥6/11 cases | 80 | +0.5-1 |
| 5 | ADR cross-reference matrix | 95 | +0.5 |
