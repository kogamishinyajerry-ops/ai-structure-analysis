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

### Remaining act-on queue (deferred at 38 F)
#3 18/24 cohort absent from frontend fallback (HIGH) · #4 render_all
HTTP-unreachable · #5 CaseBrowser amber badge ≈3.3:1 (the 38 C GAP) · #6 silent
sensitivity-study error. Composite still pending the calibrated eval-fleet re-run.

---

## Phase 38 G/H/I addendum — act-on queue cleared (2026-05-24)

The remaining four findings were closed (or honestly assessed) autonomously:
`c428e43` (38 G, #5) · `a7ec424` (38 H, #3) · `9703f4e`+`302339e`+`a747e10`+`98d5979`
(38 I, #6) · #4 assessed + deferred.

### The biggest learning: the type-check was hollow (verification integrity)

While fixing 38 I I introduced a clear `Cannot find name 'pollExperiment'`
error — and `npx tsc --noEmit` reported **0 errors**. That contradiction
exposed that **the root `tsconfig.json` is a project-references stub
(`"files": []`)**, so `tsc --noEmit` against it type-checks *nothing*. The real
check is **`tsc -b`**, which shows **21 pre-existing errors** (App.tsx 9; +12
across 7 files) — and `eslint .` shows **55** (set-state-in-effect 26 /
react-refresh 21 / no-unused-vars 8).

Implications, recorded honestly:
- This session's earlier "tsc 0 errors in touched files" claims (Phase 38 F and
  likely prior phases) were **vacuously true** — they ran the no-op invocation.
  This does NOT retroactively change any composite score (those are eval-fleet
  driven, not tsc-driven), but it means the "tsc clean" line in past preambles
  carried no signal.
- Every 38 G/H/I change was re-verified against the REAL baselines via
  stash-on-HEAD: **0 net new `tsc -b` errors, 0 net new eslint errors.**
- The 21+55 pre-existing red is a **standing-debt finding for a dedicated
  cleanup phase**, not a drive-by mid-feature fix.
- **Methodology patch (carry forward):** the canonical frontend gates are
  `npx tsc -b` and `npx eslint .` (NOT `tsc --noEmit`). Compare touched-file
  deltas against a stash-on-HEAD baseline, not against zero.

This is the same class of trap as the earlier "read `tail`'s exit code, not
`tsc`'s" lesson — a verification command that *looks* green while checking the
wrong thing. The dual-engine caught the downstream symptom (Codex would have
flagged the dangling reference), but the discipline fix is to run the real gate.

### Codex round-cap arc on 38 I (3 rounds, converging, user-ratified)

The sensitivity-study fix drew the deepest Codex arc of the milestone — and a
*healthy* one (converging on real issues, unlike the N1.1 22-round runaway):

| Round | Findings | Theme |
|---|---|---|
| R0 | 3×P2 | the new Retry affordances weren't actually recoverable (start-retry discarded the experiment_id; poll-retry only dismissed; FAILED state not normalized) |
| R1 | 2×P2 + 1×P3 | loading lost on start-retry; re-poll-vs-relaunch confusion; FAILED experiment still painted healthy `accent` |
| R2 | 1×P1 + 1×P2 | a *retried* failed start stranded loading; a 404 (backend lost the experiment) re-polled forever |

Each round's findings were second-order effects of the *previous* fix — the
"every fix exposes an adjacent surface" pattern. At the **round cap (R2) with a
P1 remaining**, per the `~/CLAUDE.md` governance I **stopped and asked the user**
rather than looping to R3 autonomously. User ratified **"fix both, skip further
review"**; both fixed (cleanup moved inside the `withRecovery` closure so Retry
restores loading on every attempt; 404 → relaunch not re-poll; `runStateTone`
reads FAILED as warning), pinned by 11 hook tests. **The round cap + the
user-ratification gate worked exactly as designed** — it surfaced a genuine
"the fixes keep spawning fixes" signal for human judgment instead of an
unbounded loop.

### Honest non-fix pattern reinforced (38 G #5)

2 of the 3 WCAG surfaces the eval flagged as contrast fails **passed once
measured** against the real composited background (runner badge 5.77:1, not the
eval's ~3.3:1 — the harsh general-purpose proxy likely measured the amber
border). Recorded as **measured PASS, not a fabricated color edit** — "measure
before you fix; a suspected fail is worth verifying." Same spirit as not
fabricating a fix for finding #5 originally.

### Drift-guard-test pattern (38 H #3)

Rather than only hand-adding the 17 missing fallback entries, shipped a
**coverage test** that reads `golden_samples/` and fails when the static
fallback diverges from disk — fixing the *class* of bug (silent drift) not just
the instance. Data sourced from the `_claim_tier` SSOT (no over-claim:
nafems-le10 stays Tier 1) via a committed provenance script.

### #4 honest deferral

`render_all` viz "HTTP-unreachable" is largely mitigated already — the backend
`/visualize/plot` returns friendly HTML for viz-unavailable + render-failed. The
residual (raw 404 for a report without an on-disk FRD; the fundamental
iframe-to-down-backend limitation) is narrow and the robust fix is
disproportionate to a MED finding from the harsh proxy. Deferred as a bounded
follow-up, not forced.

### Recommendations (next session)
1. **Restart → invoke the calibrated eval fleet via `subagent_type=` → R6
   re-score → finalize the Phase 38 composite** (the one blocker to a score).
2. **Dedicated `tsc -b` + eslint debt-cleanup phase** (21 + 55 pre-existing),
   with CI wired to the REAL gate so it can't silently rot again.
3. Optional: the deferred #4 viz-failure overlay if Dim 5 needs the lift.

## Phase 38 D addendum — composite FINALIZED at 78.33 (2026-05-24, next session)

The one blocker is cleared. Composite = **78.33** (Phase 37 → +0.83). Full audit at
`.planning/audits/phase38_FINAL.md`; per-dim fleet reports at `phase38d_*.md`.

### The registration "restart" recommendation was incomplete — and the fix matters
Recommendation #1 above said "restart → invoke the fleet via `subagent_type=`". That
is necessary but **not sufficient**: the session was launched from `/Users/Zhuanz`
(home), so the project's `.claude/agents/` are never discovered, AND those agent
files reference their protocol via **relative** `.planning/...` paths — so even
copying them to `~/.claude/agents/` (user-level) wouldn't resolve from a non-project
cwd. **The real fix is to launch from the project directory**
(`cd "/Users/Zhuanz/20260408 AI StructureAnalysis" && claude`). Until then, R6 runs
via `general-purpose` proxies briefed with **absolute** paths to the protocol +
RUBRIC_v2.md. Methodology patch: carry this in the next-session checklist.

### Calibration cuts both ways — the Dim 5 generous-drift catch
The prior (harsh) R6 proxy crashed Dim 2/3 by scoring "from zero vs commercial CAE."
The fix (anchor to RUBRIC_v2.md's feature-checklist anchors) worked — Dim 1/2/3 came
back calibrated. **But the same fresh-absolute method drifted GENEROUS on Dim 5**:
the proxy read it 84 (+12 over Phase 37's 72) on **byte-identical viz code**, and
over-credited the 90-anchor "comparison cuts (overlay two results)" sub-bullet —
`CompanionViewport.tsx:1-6` is side-by-side compare-CUTS of one result, not an
overlay of two. Per the no-retroactive-rescore guard + the prior anti-drift caveat,
the composite **HOLDS** Phase 37's calibrated values for the dims Phase 38 didn't
touch in code (Dim 4 = 76, Dim 5 = 72). The proxy's higher reads are logged as
**Phase 39 re-baseline candidates** for the REGISTERED agent — prospective, never
retroactive. Lesson: a proxy is uncalibrated in *both* directions; on byte-unchanged
code, trust the last calibrated value over a proxy re-read.

### Honest delta: most of a re-score's "movement" can be measurement-basis, not work
+0.83 composite, **entirely Dim 1 (+4, real C3D6 6th element class) + Dim 6 (+1, real
38 F/H trust work)**. Dim 2/3/4/5 flat. The project's carry-forward practice (hold
"untouched" dims) means a fresh-absolute re-score can *look* like a big jump when it's
really a basis shift — so the FINAL decomposes the delta into real-work vs held, and
refuses to bank calibration drift as progress. This is the same discipline as the
v1.0→v2.0 "never compare across bases" guard (C:-1), applied within v2.0.

### Carry-forward findings (independent of calibration)
GS-001 legacy unit-mismatch test runs+fails in the default sweep (no `@pytest.mark.legacy`);
38 D BC dead-end (no BC editor); WS-death mid-solve has no ErrorCard. All → Phase 39 /
debt-cleanup. The `tsc -b` 16 + eslint 50 pre-existing red remains the dedicated
debt-cleanup phase (CI must be wired to the REAL `tsc -b` gate).

