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

---

## Phase 38 F addendum — findings #1 + #2 shipped (2026-05-24)

Acted on the two highest-value act-on-queue items. `611cc0f` (#2, BC pill copy,
not risk-tier) + `9439841` (#1, tier-2 surfacing at the API boundary, risk-tier).

### Codex round economics (ADR-026 dual-engine, first multi-round arc)

| Round | Verdict | Findings | Disposition |
|---|---|---|---|
| R0 | CHANGES_REQUIRED | P1 frontend type decl (claimTier on wrong interface); P2 schema 1.0.0→1.1.0 | both fixed |
| R1 | CHANGES_REQUIRED | P2-a root-scoping (accessors ignore repo_root); P2-b hidden hertz promotion | both fixed |
| R2 | CHANGES_REQUIRED | P2 registry-SSOT bypass in root path (stray verdict self-promotes) | fixed (membership gate) |
| R3 | CHANGES_REQUIRED | **P1 false positive** (cited `test_schema_versions_stamping.py` — does not exist); P2 picker boundary suffix; P2 stale hertz NOTES | 2 fixed, 1 dismissed w/ evidence |

**Methodology learnings:**
- **Dual-engine earned its keep, decisively.** R0-P1 caught a real frontend type
  break my own `tsc` self-check missed — I had read `tail`'s exit code after a
  pipe (not `tsc`'s) and `tail -8` hid the error. Single-agent self-review would
  have shipped it. Lesson: capture the real tool exit code; don't trust a piped
  `$?`.
- **Each fix exposed an adjacent surface** (API → root-scoping → SSOT gate →
  picker UI / stale doc). Findings *converged* (2→2→1→[1 false +2 mechanical]),
  which is the healthy signal the round cap is meant to protect — not the N1.1
  22-round runaway. Stopped at R3 per cap; no real finding remained.
- **Codex is not infallible.** R3-P1 referenced a non-existent test. Verified
  before acting (the file does not exist; the full suite shows no such failure)
  and dismissed with evidence rather than fabricating a fix. Trust-but-verify
  applies to the reviewer too.
- **A "promote it" finding (R1-P2-b) and a "that's an overclaim" tension
  (R3-P2) resolved by reading the artifacts, not the labels.** hertz's verdict
  (Phase 34 C) said tier_2; its NOTES (Phase 33 D) said INFRASTRUCTURE_ONLY. The
  timeline (NOTES predates validation, "Phase 34 *will* land") proved the NOTES
  stale, not the promotion wrong. The honesty contract was served by updating
  the stale doc + keeping the honest scope caveat (stacked-cube proxy, not Hertz
  curvature), NOT by reflexively backing out or reflexively promoting.

### Remaining act-on queue (deferred)
#3 18/24 cohort absent from frontend fallback (HIGH) · #4 render_all
HTTP-unreachable · #5 CaseBrowser amber badge ≈3.3:1 (the 38 C GAP) · #6 silent
sensitivity-study error. Composite still pending the calibrated eval-fleet re-run.
