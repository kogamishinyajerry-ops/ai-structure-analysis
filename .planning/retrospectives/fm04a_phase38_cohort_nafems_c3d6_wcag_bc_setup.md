# FM-04a Phase 38 retrospective — cohort + NAFEMS + C3D6 + WCAG + BC-setup

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观 — 22nd consecutive Tier-2 phase. **Composite NOT
> finalized this phase** (eval-fleet calibration caveat; see below).

## What shipped (38 A-D, all committed + verified)

| Slice | Commit | Substance | Verification |
|---|---|---|---|
| 38 A | `4c8d77a` | NAFEMS LE10 published-reference (analytical-only); honest-corrected to `published_reference.yaml` REFERENCE_ONLY (not tautological PASS), signed −5.38e6, NOT registered | 8 tests; Codex R0 2 fixed |
| 38 B | `5f97f04` | C3D6 wedge — 6th element class, **real ccx** σ_zz=−210 MPa, 0.00% residual → genuine tier_2_validated | full suite 1155 passed; Codex R0 clean |
| 38 C | `59bd253` | WCAG 1.4.3 sweep — real `wcagContrast.ts` helper (spec-verified), `--text-muted` 3.74→5.4:1 fix; audit honest 7/10 PASS | 17 tests; frontend 886 passed |
| 38 D | `dcc9ee1` | BC-setup: flexDirection row + `shouldShowBCSetupAdvisor` gating + `BCSetupPillList` | 10 tests; frontend 896 passed; App.tsx 1479<1500 |

## ADR-026 dual-engine in action (first milestone using it)

- **Codex relay (code review):** activated after a 38-phase dormancy. 38 A R0
  caught 2 real issues (Phase 35 B cohort pin break → I renamed the artifact to
  keep it out of the verdict cohort; sign error +5.38e6 → −5.38e6). 38 B R0
  clean. Both reviews ALSO surfaced pre-existing untracked clutter (snapshots,
  cylinder-pv `data/`) — scoped out, flagged for cleanup.
- **Eval fleet (R6):** caught real frictions including one **38 D introduced**
  (BCSetupPillList "not yet assigned" dead-end) and independently confirmed the
  CaseBrowser amber-badge contrast fail that 38 C honestly left as a GAP.

The dual-engine earned its keep: independent review caught issues single-agent
self-review missed.

## Eval fleet R6 — composite NOT finalized (honest stance)

Scores (full detail + caveat: `.planning/audits/phase38_eval_fleet_r6.md`):
Dim 1 ≈82-86 (≈baseline 87), Dim 2 **58** (baseline 77), Dim 3 **45**
(baseline 76), Dim 5 62-68 (baseline 72). Dim 4/6 not scored (no sub-agent).

**Why I did NOT finalize a composite:**
- The custom `.claude/agents/` eval fleet is **not registered as `subagent_type`
  this session** (needs a restart). R6 ran via `general-purpose` proxies with
  harsh framing → Dim 2/3 scored on a harsher-than-calibrated scale (Dim 1/5,
  scenario-based, track baseline; Dim 2/3, absolute-formula, crashed).
- Mechanically averaging → ~68 would **retroactively re-score prior phases on an
  uncalibrated scale** — violates the additive-only + no-retroactive-rescore
  guards. Fabricating the projected 79-82 would ignore the eval evidence. Both
  are dishonest. So: **findings pass, composite deferred to a calibrated re-run.**

## Act-on queue (real findings, calibration-independent)

1. **Tier-2 promotion invisible at the API boundary** (HIGH, pre-existing):
   `candidate_cases.py:39` + `cohort_overview.py:36` hard-code "Tier 1" and never
   call `_claim_tier.get_claim_tier`. The whole tier-2 system is a dead letter to
   users. Highest-value fix.
2. **38 D BCSetupPillList dead-end** (HIGH, NEW): "expected BCs — not yet
   assigned" with no path to assign + no BC editor. My 38 D affordance created a
   novice dead-end; needs either a workaround note or honest "BCs are
   case-defined" framing.
3. **18/24 cohort cases absent from frontend fallback** (HIGH, pre-existing).
4. **`render_all` viz HTTP-unreachable** (MED, pre-existing) — Dim 5 drag.
5. **CaseBrowser amber badge contrast ≈3.3:1** (the 38 C GAP, confirmed).
6. **Silent sensitivity-study error** `App.tsx:484` (MED).

## Recommendation

Restart session → invoke the real calibrated eval fleet via `subagent_type=` →
R6 re-score → THEN finalize the composite. In parallel, act on findings #1 + #2
(highest value) as a Phase 38 follow-up or Phase 39 opener.
