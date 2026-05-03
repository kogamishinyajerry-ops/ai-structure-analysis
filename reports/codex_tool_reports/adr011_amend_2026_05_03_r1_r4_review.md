# Codex R1-R4 — ADR-011 AR-2026-05-03-001 amendment (no-date-deadlines)

- **Branch**: `feature/ADR-011-amendment-AR-2026-05-03-001-no-date-deadlines`
- **Commits**: `1168db5` (R1) → `3bf96d1` (R2 fixes) → `4d7a5f3` (R3 fixes) → `2adef57` (R4 fixes) → `f341fe7` (R4 verbatim nits)
- **Reviewer**: Codex via 86gs `gpt-5.4 (xhigh)` — `codex-relay` exec mode (governance baseline)
- **Risk-tier triggers HIT**: M1 (`docs/adr/**` HF1.9 PR-protected zone) + M4 (governance text amendment) + M5 (calibration ceiling = 30% BLOCKING — Codex MANDATORY)

## Round arc

| Round | Verdict | Severity | Key issues |
|-------|---------|----------|------------|
| R1 | BLOCKER | 2 BLOCKER + 2 HIGH + 1 LOW | Calendar-based gates remained; close-out predicate ambiguous; counter undefined; FF-07/08 too loose; summary scope incomplete |
| R2 | BLOCKER | 1 BLOCKER + 2 HIGH + 1 LOW | `Phase_2_activation_imminent` undefined; rollback can self-nullify; counter not collision-safe; HF5/HF3 anti-overclaim is policy not enforcement |
| R3 | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM | ADR-013 enforcement claim overstated; `_queued` vs `_opened` not normalized |
| R4 | **APPROVE_WITH_NITS** | 2 LOW | Normalization sentence overstated; T0 audit artifact + ownership implicit |

R4 NITS counts as APPROVE per ADR-012 outcome canon. R4-nit fixes applied verbatim per RETRO-V61-001 verbatim-exception 5 conditions (≤20 LOC, ≤2 files, no public API, citing round + finding ID).

## Final verdict

**APPROVE_WITH_NITS** (R4) → APPROVE per outcome canon.

## Cumulative changes (after R1-R4)

- §HF1 Recovery: HF2 calendar window → completion-driven
- §Enforcement Maturity:
  - HF2/HF3/HF5 Status column dates removed
  - FF-07/FF-08/FF-09 hard prerequisites bound to `Phase_2_Gate_opened` (or `Phase_2_Gate_queued` for FF-07's pre-Calibration-close-out clause)
  - "In summary" line date removed
  - HF5/HF3 anti-overclaim labeled discipline-only
- §Calibration Mode:
  - 4 周 calendar window replaced with explicit Boolean predicate
  - Defined `Phase_2_Gate_queued` and `Phase_2_Gate_opened` as ordered pair
  - Prohibited other Phase 2 state names ("imminent", "pending", "in flight")
- §Risks #4: "终止日期 2026-05-23 不可滑动" deleted
- §Rollback:
  - "观察窗口 4 周" → rolling Calibration window
  - HF2 post-close-out trigger: "first 10 post-close-out T1 sessions/PRs"
  - Audit log: rolling `reports/hf_audit.md` + `reports/archive/hf_audit_window-NNN.md`
  - Counter NNN computed against origin/main at merge commit (collision-safe)
  - T0 sole arbiter for all 3 close-out paths
  - T0 ratification reference = concrete artifact (Decisions DB id OR linked PR comment URL)
  - T1 self-audit at next post-close-out PR with `closeout-audit: PASS / FAIL` attestation
- ADR header metadata updated (Status / Date / Branch / Amendment cycles)
- `reports/hf2_calibration.md` header line updated

## Calibration entry (post-merge backfill target)

```json
{
  "pr": "<TBD>",
  "sha": "<merge-commit-sha-tbd>",
  "title": "[ADR-011] AR-2026-05-03-001 — remove all date-based deadlines",
  "merged_at": "<TBD>",
  "r1_outcome": "BLOCKER",
  "r1_severity": "2 BLOCKER + 2 HIGH + 1 LOW",
  "r1_review_report": "reports/codex_tool_reports/adr011_amend_2026_05_03_r1_r4_review.md",
  "notes": "4-round arc R1 BLOCKER → R2 BLOCKER → R3 CR → R4 APPROVE_WITH_NITS. Backend: 86gs gpt-5.4 (xhigh)."
}
```

## R1-R4 round-by-round verdict text

(Full Codex output preserved at `/private/tmp/claude-502/.../bjsk2dxxt.output` (R1), `breabgsxt.output` (R2), `btzezrjsr.output` (R3), `b00p2mpa1.output` (R4) at the time of this report — copies not committed because some rounds exceeded 100kB and contain unrelated stack traces. The structured findings and verdicts are summarized above.)
