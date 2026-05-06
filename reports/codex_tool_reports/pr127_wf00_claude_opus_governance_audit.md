# PR #127 WF-00 Claude Opus Governance Audit

**Pilot issue:** ENG-32 · WF-00 Codex-primary / Claude-audited workflow pilot
**Target PR:** #127 · `[ENG-32] Establish Codex-primary governance pilot`
**Command:** `claude -p <packet> --model opus --no-session-persistence --tools "" --max-budget-usd 0.80`
**Tool access:** Disabled

# Verdict: APPROVE

## Evidence-focused findings

### Governance correctness

- **Role model encoded faithfully** in `AGENTS.md` and `ADR-011` amendment AR-2026-05-06-001: Codex = primary executor, Linear = work-control truth, GitHub = code truth, Claude Opus = reviewer/auditor, Notion = post-truth mirror. Matches approved model verbatim.
- **Banned routes updated** correctly to forbid "Antigravity as default executor / Opus direct development by default / direct main-code commits / Notion-first truth changes."
- **Commit trailer convention** revised to `Execution-by: codex-primary` + `Reviewed-by: claude-opus47` + `Linear-Issue: ENG-<id>` — consistent with new role split.
- **Routing Comparison table** correctly rebases "Before" to the prior Claude-Code-single-path state, preserving accurate amendment history.

### Gate honesty

- Self-pass-rate **50%**, mechanically derived from `compute_calibration_cap.py`, declared in PR body. No inflation.
- Codex pre-merge gate explicitly marked **MANDATORY**.
- M1 trigger, governance text touching `AGENTS.md` and `docs/adr/**`, correctly self-identified; independent review evidence required.
- Known test failures, `langgraph` missing and `EvidenceBundle` rebuild, disclosed in PR body as pre-existing.
- No green-CI-equals-approval claim; explicitly stated that green CI is not sufficient for governance changes.

### PR #126 disposition

- Both `pr126_wf00_codex_primary_disposition.md` and `pr126_wf00_claude_opus_audit.md` return **BLOCKER** with consistent reasoning: PR #126's root `AGENTS.md` reverses approved execution model.
- **Split recommendation correct**: governance PR first, AERON L0 protocol code salvage as separate Codex-owned PR later.
- AERON protocol salvage explicitly listed as out of scope.
- STATE.md records #126 as **BLOCKER under WF-00** with evidence pointers.

### Role drift checks

- Claude Opus role is bounded to prepared-packet/diff review and is not default executor or repo owner.
- Codex does not self-merge and does not claim completion beyond evidence.
- External writes remain gated; only confirmed PR creation and Linear comment were executed, while Notion and PR #126 comment remain dry-run.

### Minor observations, non-blocking

- ADR-011 Routing Comparison "Before" column now reads as "Claude Code single-path"; accurate for this amendment, with the amendment cycles list available for full history.
- STATE.md drops the prior "calibration state file backfill" carry-over without a stated disposition. Likely subsumed by ADR-012/013 enforcement, but a future STATE refresh could add a one-line closure reason.
- ADR-011 still references ADR-012 for M5 calibration ceiling; presumed intact because ADR-012 was not modified in this diff.

### Safety as governance baseline before AERON salvage

This PR is the correct ordering: it lands the Codex-primary governance baseline and the BLOCKER disposition for #126 before any AERON L0 protocol salvage attempt. Merging this first ensures the next AERON PR is reviewed under the correct role model rather than the inverted one #126 would have established.

## Summary

Governance content is faithful to the approved role model, gates are honest, scope is bounded, PR #126 is correctly blocked with split-PR remediation, and AERON salvage is explicitly out of scope. Safe to land as the governance baseline.
