# WF-00 External Write Dry Runs

**Issue:** ENG-32
**Date:** 2026-05-06
**Status:** Dry-run only except for the already-created Linear issue and Linear proof comment.

## GitHub Governance PR Creation Dry Run

Target repository: `kogamishinyajerry-ops/ai-structure-analysis`

Branch: `codex/wf-00-codex-primary-pilot`

Command withheld until explicit confirmation:

```bash
gh pr create \
  --repo kogamishinyajerry-ops/ai-structure-analysis \
  --base main \
  --head codex/wf-00-codex-primary-pilot \
  --title "[ENG-32] Establish Codex-primary governance pilot" \
  --body-file /tmp/wf00-pr-body.md
```

Proposed PR body:

```markdown
## Summary

- Establishes the Codex-primary workflow as repo policy: Codex executes, Linear controls work, GitHub/repo is code truth, Claude Opus 4.7 audits, and Notion mirrors after repo + Linear truth settle.
- Records WF-00 evidence for PR #126: Codex disposition and local Claude Opus audit both return BLOCKER for the Apex/Claude ownership model in the proposed AGENTS.md.
- Updates README, ADR-011, and STATE.md to align landed governance wording before any AERON L0 protocol salvage work.

## Linear

- ENG-32: WF-00 · Codex-primary / Claude-audited workflow pilot

## Review evidence

- `reports/codex_tool_reports/pr126_wf00_codex_primary_disposition.md`
- `reports/codex_tool_reports/pr126_wf00_claude_opus_audit.md`
- Current calibration cap: 50%, independent review mandatory.

## Verification

- `python3 scripts/compute_calibration_cap.py --human`
- `python3 scripts/compute_calibration_cap.py --check 50`
- `git diff --check`
- `uvx ruff check .`
- `uvx ruff format --check .`
- `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_checkpointer.py --ignore=tests/test_cold_smoke_e2e.py`

## Known test state

The broad pytest target still has pre-existing collection/runtime failures unrelated to this docs/governance patch:

- missing `langgraph` in `tests/test_human_fallback.py` and `tests/test_stub_imports.py::test_import[agents.graph]`
- Pydantic `EvidenceBundle` rebuild failure in report CLI doctor/figures/material tests

## Out of scope

- No merge/close action on PR #126.
- No Notion mutation.
- No Linear state transition.
- No AERON protocol code salvage in this PR.
```

## GitHub PR #126 Comment Dry Run

Target: `https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/126`

```markdown
## WF-00 Governance Disposition — BLOCKER

Do not merge this PR as-is.

Codex-primary workflow pilot ENG-32 reviewed PR #126 as the first control-plane
test. Codex and local Claude Opus both returned BLOCKER because the proposed
root `AGENTS.md` assigns Apex/Claude ownership and treats Codex as a delegated
PR worker, which conflicts with the user-approved workflow:

- Codex = primary executor
- Linear = work-control truth
- GitHub/repo = code truth
- Claude Opus 4.7 = reviewer/auditor
- Notion = architecture/control mirror after repo + Linear truth settle

Evidence:
- `reports/codex_tool_reports/pr126_wf00_codex_primary_disposition.md`
- `reports/codex_tool_reports/pr126_wf00_claude_opus_audit.md`

Required next action: split governance from protocol code. Land a Codex-owned
governance PR first, then salvage the AERON L0 protocol code in a separate
Codex-owned PR if still desired.
```

## Notion Mirror Update Dry Run

Targets:

- `AERON OS` — `352c6894-2bed-808e-b0f7-ec430856ff0d`
- `GSD-001 · AI-StructureAnalysis 接入 AERON L0 (Phase β 准备)` — `355c6894-2bed-8167-a587-de895ad752ad`

Mutation type: append a dated callout/status block near the top of each page;
do not delete existing AERON narrative until the governance PR lands and review
passes.

```markdown
## 2026-05-06 · WF-00 Workflow Correction

AI-StructureAnalysis now uses the Codex-primary Linear/Symphony workflow:

- Codex is the primary implementation agent.
- Linear is the work-control truth for issues, acceptance, blockers, and proof.
- GitHub/repo is the code truth.
- Local Claude Opus 4.7 is reviewer/auditor.
- Notion is the architecture/control mirror after repo and Linear truth settle.

PR #126 is blocked as-is because its proposed root AGENTS.md reintroduced
Apex/Claude ownership and Codex-as-delegated-worker routing. The AERON L0
protocol code can be revisited later in a separate Codex-owned PR after
workflow governance is aligned.

Evidence:
- Linear ENG-32
- Repo artifact: reports/codex_tool_reports/pr126_wf00_codex_primary_disposition.md
- Repo artifact: reports/codex_tool_reports/pr126_wf00_claude_opus_audit.md
```
