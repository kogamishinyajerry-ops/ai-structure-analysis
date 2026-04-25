# ADR-012: Calibration Cap for T1 Self-Pass-Rate

- **Status:** Accepted
- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
- **Date:** 2026-04-25
- **Supersedes:** RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system discipline (replaced for AI-Structure-FEA; other projects still under V61 may retain the honor-system version)
- **Related:** ADR-011 (parent), ADR-013 (branch protection — sibling, lands separately), DEC-T0-2026-04-25-001 (Notion record)
- **Branch:** `feature/AI-FEA-ADR-012-calibration-cap`

---

## Context

ADR-011 ratified RETRO-V61-001's honor-system: T1 writes a self-pass-rate per PR; ≤70% triggers pre-merge Codex; high estimates that fail are retro-debited next cycle. Session 2026-04-25 produced empirical evidence that this honor-system fails:

| PR | T1 self-estimate | Codex R1 actual outcome |
|---|---|---|
| #20 revert | 95% | CHANGES_REQUIRED · 1 BLOCKER (direction inversion) |
| #18 FF-02 | 95% | CHANGES_REQUIRED · 1 HIGH (over-claim + unflagged prescription) |
| #19 FF-05 | 95% | CHANGES_REQUIRED · 1 HIGH (stale post-merge state) |
| #21 chore | 90% | CHANGES_REQUIRED · 1 HIGH (open-PRs underreport) |
| #22 FF-06 | 80% | CHANGES_REQUIRED · 1 BLOCKER (rename/delete bypass) |

Empirical R1-pass-rate: **0/5 = 0%**. T1 self-estimates were systematically wrong by 80-95 percentage points each, *across the same session*. T0's diagnostic in AR-2026-04-25-001 §1: "this is not noise; it is the predictable failure mode of any honor-system metric where the rater and the rated party are the same agent in the same context window." The discipline cannot self-correct mid-session — T1 wrote "95%" five times in a row while Codex was actively contradicting it.

The retro-debit lag (next-cycle correction) is also too slow: by the time the retro lands, multiple PRs have already shipped with mis-calibrated confidence, and T1's session-end summary inherits the over-confidence as part of its training signal.

## Decision

Self-pass-rate becomes a **mechanically-derived ceiling** based on a rolling window of the last 5 PRs' Codex Round 1 outcomes. T1 cannot type a number; T1 reads a number computed by `scripts/compute_calibration_cap.py` from the append-only state file `reports/calibration_state.json`.

### Formula (canonical, ratified in AR-2026-04-25-001 §1)

```
Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR PRs excluded)
Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
                 (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)

Base ceiling (per next PR):
  0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
  1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
  3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
  5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING

Recovery (override on top of base):
  2 consecutive R1=APPROVE  → ceiling steps up one rung from base
  3 consecutive R1=APPROVE  → ceiling returns to 95%
```

Rung ladder is `30 → 50 → 80 → 95` (`step_up` saturates at 95).

### Codex gate derivation from final ceiling

| Ceiling | Mandatory Codex pre-merge | Blocking |
|---|---|---|
| 30 | yes | **yes** (no T1 self-merge; needs t0-approved or external review) |
| 50 | yes | no |
| 80 | no (recommended) | no |
| 95 | no (optional) | no |

Independently of the ceiling, ADR-011 §T2 amendments (M1-M5 triggers — governance text, sign/direction math, HF compliance claims, governance→enforcement translations, and any PR opened while ceiling ≤ 50%) may still mandate Codex review.

## Implementation contract

**Sources of truth:**

- `reports/calibration_state.json` — append-only state file, schema v1. Each entry: `{pr, sha, title, merged_at, r1_outcome, r1_severity, r1_review_report, notes}`. Authoritative for the formula's input.
- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes.
- `tests/test_compute_calibration_cap.py` — 42 unit tests covering each rung, recovery transitions, BLOCKER/NITS canon, edge cases, JSON output.

**T1 invocation surface:**

- At session-start, T1 runs `python3 scripts/compute_calibration_cap.py --human` and renders the result in the `MODEL COMPLIANCE CHECK` block of every reply that initiates work.
- The PR template (in `.github/PULL_REQUEST_TEMPLATE.md` once branch protection lands per ADR-013) prefills the `Self-pass-rate` field by calling the script. The field is **read-only** to T1.
- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.

**State maintenance:**

After each PR merges, the maintainer (T1 or T0) appends a new entry to `reports/calibration_state.json` with the actual R1 outcome. Entry SHOULD be added in the same PR as housekeeping or in the next PR's first commit. State updates do NOT themselves count as PRs in the formula — the formula counts PRs that touched code/governance content.

## Bootstrap state (initial 5 entries)

Per AR-2026-04-25-001 §1, initialize from PRs #18-#22 (PR #17 excluded as the ADR-011 baseline establishment). All 5 are `CHANGES_REQUIRED` per session 2026-04-25 record:

| PR | SHA | R1 outcome | R1 severity |
|---|---|---|---|
| #18 | `77e6813` | CHANGES_REQUIRED | 1 HIGH + 3 MEDIUM |
| #19 | `4a64cfd` | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM |
| #20 | `9362f6d` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
| #21 | `2bbf0f1` | CHANGES_REQUIRED | 1 HIGH |
| #22 | `ac98fc3` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |

Resulting ceiling at ADR-012 land: **30%, MANDATORY pre-merge Codex, BLOCKING**.

This means ADR-012 itself (this PR), ADR-013, and ADR-011 amendments all open under the 30% blocking regime. That is exactly correct given the empirical record.

## Recovery path

To return to the 95% honor-system regime from the bootstrap 30%, T1 needs:

- **One** R1=APPROVE PR after this one → state `4 of last 5 = CR` → ceiling 50, MANDATORY but not blocking
- **Two consecutive** R1=APPROVE → recovery clause overrides base → ceiling steps from `4 of 5 → base 50` to step-up `80`, RECOMMENDED only
- **Three consecutive** R1=APPROVE → recovery clause resets ceiling to 95, OPTIONAL

In other words: three clean PRs in a row, no R1 BLOCKER/HIGH, restores honor-system. The formula is forgiving but evidence-grounded.

## Consequences

**Intended:**

- T1's self-rated confidence becomes irrelevant to ceiling derivation. Calibration error cannot affect the gate.
- Ceiling = leading indicator (predicts likely R1 outcome) rather than RETRO-V61-001's lagging indicator (corrects after the fact).
- Recovery is mechanical and fast (3 clean PRs ≈ 1-2 sessions of clean work), so T1 isn't permanently penalized for one bad session.
- Bootstrap 30%/BLOCKING for the immediate next 3 PRs (ADR-012, ADR-013, ADR-011 amendment) is exactly what the empirical record warrants.

**Acknowledged:**

- The recovery thresholds (2 → step up, 3 → reset) are reasonable but not empirically grounded yet (T0 self-rated 88% on this clause). Revisit after 10 more PRs of post-ADR-012 data; either ratify or tighten via ADR-012 amendment.
- The formula assumes Codex R1 quality is stable. If Codex itself becomes lenient over time (NITS-with-ulterior-motive or APPROVE-without-checking), the formula's signal degrades. This is a Codex-quality concern, not an ADR-012 concern, but should be tracked.
- "Last 5" is small enough that one anomalous session can flip the ceiling. A larger window (10 or 20) is statistically more robust but slower to respond. T0's choice of 5 prioritizes responsiveness; revisit if ceiling thrashes after the bootstrap recovery completes.
- Cross-project portability: the formula assumes Codex is the de facto reviewer (per ADR-011 §T2). Projects without Codex must adapt the canon (e.g., human review verdict).

**Out of scope:**

- ADR-013 (branch protection) is the surface that *enforces* the gate (a 30%-blocking ceiling means nothing if T1 can self-merge anyway). ADR-012 is the calibration math; ADR-013 is the access-control wrapper. They are sibling ADRs landed in the same session under the same T0 verdict.
- Codex role rewording (anti-shenanigans backstop, M1-M5 triggers) is part of the ADR-011 amendment PR, not ADR-012.

## Open follow-ups

- Add CI step calling `compute_calibration_cap.py --check` against PR body's claim, after `.github/PULL_REQUEST_TEMPLATE.md` lands (in ADR-013's batch).
- After 10 post-ADR-012 PRs, write a calibration-stability retro: confirm or amend recovery thresholds based on empirical thrashing rate.
- Notion control plane: DEC-T0-2026-04-25-001 captures this ADR; future ADR-012 amendments must update the same DEC entry.
