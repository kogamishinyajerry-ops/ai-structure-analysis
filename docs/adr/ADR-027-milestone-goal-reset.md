# ADR-027: Milestone Goal Reset — FM-04a v1.0 Closeout, Retire the 6×99 Gate, Define a Lean On-Mission v2

- **Status:** **Accepted** (2026-06-03 — ratified by the human owner after Codex relay
  governance review R0→R1 closed all findings; evidence
  `reports/codex_tool_reports/adr027_r0_r1_goal_reset_governance_review.md`. The 5 acceptance-gate
  doc edits landed in the same ratification commit. Drafted by Claude Opus 4.8 (1M) under the
  "状态归真 + 重设目标" / Path-A directive.)
- **Date:** 2026-06-03
- **Decider:** Human owner (ratified 2026-06-03). Drafted by Claude Opus 4.8.
- **Amends:** ADR-026 §"Governance carried · Composite rubric mandate" (the operative ship
  goal). **Supersedes** `.planning/ROADMAP.md` (the FM-01..05 Linear/Codex-primary milestone
  model, last updated 2026-05-07 — already contradicted by ADR-026).
- **Does NOT touch:** ADR-011 HF1–HF5 path guards · ADR-012 calibration cap · ADR-013 branch
  protection · ADR-023 Tier 0/1/2 claim system · ADR-026 dual-engine team architecture · the
  6-dim rubric definition itself · solver truth · schemas · `golden_samples/**` · public APIs · CI.
- **Related:** ADR-023 (Tier system — the real ship discipline), ADR-026 (team architecture),
  `~/CLAUDE.md` honesty contract.
- **Related Phase:** FM-04a (post Phase 43 authoritative composite 81.33; code at ~Phase 45 unscored).

---

## Context

A 2026-06-03 deep-takeover review (5-agent independent verification workflow
`ai-fea-deep-takeover`, run under the G:-1 "test what the codebase IS, not what it CLAIMS"
doctrine, measuring HEAD `fcd986c` without trusting `STATE.md`) established the following
**verified** ground truth. It exposes a goal-design problem, not an engineering one.

### What is genuinely strong (verified)

- **The honest FEA core is real and is the moat.** 13 candidate cases are
  `tier_2_validated` by real ccx 2.23 runs with recorded residuals within declared tolerance
  (SSOT `backend/app/services/reporting/_claim_tier.py`, 17-entry registry, 13 PASS / 4 tier_1).
  Live re-run of `heat-transfer-1d` reproduced node-6 = 323.15 K at residual 0.0%. Signed
  `^GS-\d{3}$` cases are refused (422). The Tier discipline (ADR-023) holds end-to-end.
- **The Tier-0 demo renders** (live: `GS-102-candidate` result-mesh 200 / 388 KB from repo
  root; signed 422; traversal 400; real Three.js WebGLRenderer).
- **CI is green and the branch is pushed** (`0/0` vs origin; 5 required checks). `tsc -b` = 0,
  `npm run build` passes, 1287 vitest tests pass.

### The goal-design problem

1. **The 6×99 APPROVE gate is a treadmill.** The operative goal (ADR-026 "Composite rubric
   mandate: 6-dim rubric v2.0 toward 99+") requires **all six dimensions ≥ 99**. The
   authoritative trajectory is 77.50 (P37) → 78.33 (P38) → 80.67 (P39) → **81.33 (P43)**. The
   real per-phase product slope, after removing one-time calibration basis-shifts, is
   **≈ +0.33–0.54/phase** — the weakest stretch (P40–43) is the most recent. Honest 99-reach is
   **≈ Phase 50–55**, not the standing doc projection of "Phase 45–46." That projection is
   fiction.

2. **Two of the gate's anchors are arguably mission-incompatible.** Dim 3 = 99 demands
   commercial-CAE UI parity (Hyperworks/Abaqus/ANSYS-grade layout systems); Dim 1 = 99 demands
   signed public-benchmark agreement. For a deliberately **CalculiX-only, honesty-first** tool,
   chasing commercial-CAE UI parity is scope the product never set out to win, and is the
   lowest-mission-value of all the open work.

3. **The score is too noisy to be a binary gate.** The eval fleet re-scores D1/D2/D3/D5 fresh
   each cycle (F:-1 no-memory by design); P43 moved Dim 1 86 → 82 on **byte-unchanged FEA
   code** ("audit variance," disclosed honestly). A measurement with ±4–5 noise on unchanged
   code cannot meaningfully target a 99-precision finish line. The rubric is an excellent
   **direction signal**; it is a poor **ship gate**.

4. **Mission drift.** Phases 40–45 are almost entirely frontend/demo work (3D-first recompose,
   density toggle, resizable rails, tour gating) chasing Dim 2/3/5 fractions, while the
   differentiated core (Dim 1 FEA depth / NAFEMS real benchmark) stagnated — NAFEMS LE10
   remains `REFERENCE_ONLY` with **zero real public-benchmark agreements**. The best engine
   (Opus + Codex review rounds) is being spent on UI chrome to farm rubric points.

5. **Two contradictory goal SSOTs coexist.** `.planning/ROADMAP.md` still describes an
   FM-01..05 **Linear/Codex-primary** model ("Use Codex as primary executor and local Claude
   Opus 4.7 as read-only reviewer"; "next slice = FM-01 or FM-02"). ADR-026 **reversed** that
   role assignment, and the project has actually run the FM-04a Opus-primary rubric march. The
   **AERON** subsystem (`aeron/protocols` + `aeron/drivers/{calculix,openradioss}`) carries the
   stale FM-02 "AERON-Backed Solve Path" *framing* from that superseded ROADMAP world — but a
   full-repo import/use audit (recorded 2026-06-03; see D4) shows the **code itself is live and
   tested**: imported by `agents/solver.py`, exercised by ≥5 test files (`test_aeron_*`,
   `test_solver_agent`, `test_simulation_sample_manifest`, `test_packaging`), shipped as a
   `pyproject` package (`aeron*`), and reachable from the live backend via the
   `backend/app/workbench` facade. `aeron/drivers/calculix_backend.py` is a "narrow AERON
   wrapper around the existing CalculiX path" over the real `tools.calculix_driver`. **What is
   orphaned is the *milestone framing and the unmerged `codex/ENG-35/36/38` remote branches*,
   not the code.** (An earlier draft of this ADR and the verification workflow mis-stated AERON
   as "never imported" — a scoped-grep error that checked only `backend/`+`frontend/` and missed
   the top-level `agents/` package; Codex R0 P1 caught it. The correction is itself an instance
   of the G:-1 doctrine.)

6. **Honesty-doctrine drift at the meta level.** The project's identity is 绝对诚实客观, yet its
   own live docs had drifted out of truth: `STATE.md` reported 41.4 / vitest 962 / tsc 16 /
   eslint 51 while reality is 81.33@P43 / 1287 / 0 / 70; `CLAUDE.md` claims "22+ consecutive
   Tier-2 phases" while P40–45 are Tier-0 demo work. The code stayed honest; the narrative did
   not. (The `STATE.md` truth-up is already landed alongside this ADR.)

## Decision

Reframe the operative goal from "drive a noisy composite to an unreachable 6×99 gate" to
"**ship the honest candidate, then deepen the one thing that is the actual moat.**" Concretely:

### D1 — Declare FM-04a v1.0 = "Honest Engineering Candidate" milestone COMPLETE

FM-04a has delivered a coherent, defensible v1.0. **Exit evidence (all already on disk /
green):** 13 `tier_2_validated` ccx cross-checks across 6 solver kinds + 6 element classes; a
rendering Tier-0 demo with intact signed-registry refusal; the ADR-026 dual-engine governance
(Codex review re-activated, round-cap 3); 1287 vitest + backend suite green; CI green on a
pushed branch; the Tier 0/1/2 claim discipline honored end-to-end.

**Release label (narrow, per Codex R0 — must not blur ADR-023/025 boundaries):**
> "**FM-04a v1.0 — engineering-candidate, complete.** Includes 13 per-envelope
> `tier_2_validated` real-ccx ↔ closed-form analytical cross-checks; **zero public-benchmark
> agreements; not signed validation.**"

That label is the *only* sanctioned summary; the `tier_2_validated` cases are per-case
analytical cross-checks, **not** the signed Tier-2 of ADR-023 (which still requires a public
benchmark + signoff). This is a real finish line the project has actually crossed —  without
overclaiming the tier.

### D2 — Retire the binary 6×99 APPROVE gate as the operative ship goal

The 6-dim rubric v2.0 **definition is unchanged** and continues to be computed each milestone
as a **health dashboard / direction signal**. What changes: "all-6-dims-≥99" is **no longer the
finish line**, and phases are **no longer justified by the rubric points they farm**. This ends
the treadmill and the mission drift. (No retroactive re-scoring; all prior phase records stay
frozen per ADR-023 / ADR-026.)

**The guardrail that replaces the gate (per Codex R0 P2 — "dashboard" alone is not enough).**
Retiring the score as a gate must NOT relax rigor. Two hard guardrails replace it, neither of
which any rubric score can compensate for:

- **G-1 — Regression floor (the 13 candidates must not silently degrade).** Two invariants:
  **(i) the signed-`^GS-\d{3}$` refusal stays intact** — *already* CI-enforced by the `ci.yml`
  `lint-and-test` pytest job (`tests/test_solver_run_signed_registry_refusal.py`,
  `test_phase14_cross_route_signed_registry_refusal.py`, `test_phase13_refused_claims.py`);
  **(ii) the 13 `cross_check_verdict.yaml` residuals stay within their declared tolerances.**
  **Honest gap (per Codex R1 — do NOT over-claim CI):** invariant (ii) is currently pinned only
  by the *committed* verdict YAMLs + registry-consistency tests, **NOT** by a live-ccx re-solve
  in CI; the `golden-samples-validation` workflow validates only the signed `GS-###` registry
  metadata, not candidate residuals. Wiring an automated residual-floor gate is **v2 item V2-0
  (enabling, small)** below. Until V2-0 lands, the floor is a **documented release-blocker
  invariant, not an automated gate** — stated plainly rather than claimed as enforced.
- **G-2 — Tier-2 evidence packet (ADR-023, made explicit).** Any case promoted to a *signed*
  Tier-2 claim (e.g. V2-1 NAFEMS) requires the full packet, no item substitutable by a score:
  (1) public, traceable benchmark source + sign convention from the primary document; (2) real
  ccx run with deck provenance + solver logs; (3) residual/metric vs published target + tolerance;
  (4) mesh/convergence evidence appropriate to the claim; (5) artifact manifest + hashes;
  (6) reproduce-CLI audit log (V2-2); (7) independent review/signoff. Missing any item ⇒ the
  claim stays Tier-1, regardless of rubric dimensions.

### D3 — Define v2 = FM-05 "Outward-Credible Validation & Reproducibility" (lean, evidence-gated)

v2 is a **small** set of on-mission objectives, each gated by **concrete Tier-2 evidence (ADR-023)**,
**not** by a rubric number:

- **V2-0 — Residual-floor CI gate (enabling, small; closes the G-1 honest gap).** On every PR,
  assert the 13 committed `cross_check_verdict.yaml` residuals against their declared tolerances
  (and, budget permitting, live re-solve ≥1 representative case per solver-kind under `ccx`).
  Turns the G-1 invariant (ii) from a documented promise into an automated gate.
- **V2-1 — NAFEMS LE10 real benchmark agreement (highest value).** Turn "13 self-consistent
  analytical cross-checks" into the project's **first genuine public-benchmark agreement**:
  gmsh-mesh the thick plate, re-confirm the LE10 sign convention from the primary source, run
  real ccx, record residual vs the published −5.38 MPa σ_yy at point D within tolerance →
  promote from `REFERENCE_ONLY` to a signed Tier-2 case. *This is the single item that makes
  "validated" outward-credible.* (Dim 1 95-anchor — but pursued for the **agreement**, not the
  point.)
- **V2-2 — Reproducibility CLI + audit log (the real Dim-6 substance).** A `reproduce <case_id>`
  CLI that re-derives a case's result + verdict from committed inputs, plus a structured
  audit-trail log. On-mission (this is *trust/honesty infrastructure*, not chrome) and broadly
  useful.
- **V2-3 (enabling, optional) — Structural debt unblock.** Decompose `App.tsx` (1496/1500, 4
  LOC headroom) and burn down the eslint backlog (70/70 ceiling, zero headroom) so future work
  is not blocked by the pins. Pursue only as needed to unblock V2-1/V2-2 or genuinely-wanted UX.

**Explicitly de-scoped from v2:** commercial-CAE UI parity (the Dim-3 = 99 anchor). UI work is
capped at "usable and honest," not "Hyperworks parity." If the owner later wants it, it becomes
its own opt-in milestone — not a standing gate that blocks everything else.

### D4 — AERON disposition: CLARIFY, do NOT archive the code (corrected per Codex R0 P1)

A full-repo import/use audit (2026-06-03, evidence below) **overturns** the "orphaned" premise:
`aeron/` is **live, imported, and tested**, so blanket-archiving it would break `agents/solver.py`
and ≥5 test files. The disposition is therefore **clarify status + retire only the stale
framing**, not archive the code:

- **Preserve all `aeron/` code unchanged.** It is the FEABackend protocol seam
  (`aeron/protocols`) + the CalculiX driver (wrapping `tools.calculix_driver`) + the OpenRadioss
  driver (the FM-04a-P4 ballistic path). All tested, all shipped as the `aeron*` package.
- **Retire only the obsolete *direction*:** the ROADMAP FM-02 "AERON-Backed Solve Path"
  milestone framing (superseded by ADR-026) is marked dead in the ROADMAP supersession (D5).
- **Prune the dead remote branches:** `codex/ENG-35`, `ENG-36`, `ENG-38` are unmerged into
  `origin/main` and superseded; recommend deletion from origin (housekeeping, reversible — the
  code already lives on the FM-04a branch). `ENG-37` is already merged; leave it.
- **Record the audit** as a one-paragraph note (`aeron/README.md` or a STATE line): "AERON is a
  live, tested FEABackend seam used by `agents/solver.py` via the workbench facade; it is NOT
  the active *milestone* (ADR-026 rubric march is), and it is NOT signed-validated. Its
  OpenRadioss driver is the intended ballistic backend."
- **Owner decision (2026-06-03):** AERON is **not pursued** — focus stays on the AI-FEA core.
  The `agents/solver.py`→AERON path is left **as-is** (a tested-but-secondary seam; code
  untouched, NOT wired into the live workbench solve flow, NOT a v2 item). Dead `codex/ENG-35/36/38`
  remote branches are **ticketed** for housekeeping deletion (not executed here — an outward git
  action left to the owner).

**Audit evidence (verbatim):** `grep -rn 'aeron' --include='*.py'` →
`agents/solver.py:11,67,69` (`from aeron.protocols import …`; `from aeron.drivers import
CalculiXFEABackend`; instantiation); `tests/test_aeron_calculix_backend.py`,
`tests/test_aeron_fea_backend_protocol.py`, `tests/test_openradioss_backend.py`,
`tests/test_solver_agent.py`, `tests/test_simulation_sample_manifest.py`; `pyproject.toml:132`
`"aeron*"`; egg-info `top_level.txt` lists `aeron`.

### D5 — Reconcile the docs (truth + single SSOT)

- `STATE.md` — truthed-up (landed with this ADR).
- `CLAUDE.md` — correct the "Composite rubric mandate … toward 99+ … reach Phase ~45-46" line
  to point at this ADR's reset; correct/qualify the "22+ consecutive Tier-2 phases" claim
  (P40–45 are Tier-0 demo). **Only after** Codex review + user ratification (governance-locked
  file).
- `.planning/ROADMAP.md` — mark **SUPERSEDED by ADR-027** (header note; the FM-01..05
  Linear/Codex-primary model is no longer operative).

## Consequences

**Positive:**
- Ends the treadmill: effort redirects from farming a noisy score toward the one item
  (NAFEMS agreement) that materially raises external credibility.
- Restores the honesty doctrine at the meta level (docs match reality; one goal SSOT).
- Gives the project a real, crossed finish line (v1.0) instead of a perpetually-receding one.
- Removes the structural pretense that commercial-CAE UI parity is in scope.
- Replaces the false "AERON orphaned" framing with a verified status (a live, tested FEABackend
  seam vs a stale *milestone direction*) — no live code disturbed.

**Tradeoffs:**
- "99 on all dims" was a clean, legible target; replacing it with evidence-gated milestones is
  less of a single number to point at. Mitigated by keeping the rubric as a published dashboard.
- Declaring v1.0 "complete" risks reading as lowering the bar. Mitigated: the bar is *raised*
  for the core (real benchmark agreement > self-cross-check) and only *removed* where it was
  off-mission (UI parity).

## Non-Goals

This ADR does **not**:
- delete or rewrite any historical audit / retro / blueprint / `STATE_ARCHIVE` record (frozen,
  point-in-time; the no-retroactive-rescore guard of ADR-023/026 stands);
- change the 6-dim rubric definition, the Tier 0/1/2 system, calibration cap, branch
  protection, `golden_samples` guards, solver truth, schemas, public APIs, CI, or dependencies;
- archive, dormant-mark, or delete any `aeron/` code (D4 corrected to "clarify, don't
  archive" — the code is live and tested); the only AERON action is retiring the stale
  *milestone framing* + pruning dead unmerged remote branches;
- re-score any prior phase or backfill any composite;
- mandate a push/PR posture change (the current pushed+CI posture for this branch is recorded
  as fact, not changed by this ADR).

## Ratification

Per ADR-026 / AGENTS.md ("repo-level policy changes need explicit review evidence"), this
goal-reset is itself reviewed via the Codex relay (governance risk-tier) before user
ratification. Flow: draft (this file, Proposed) → `codex-relay-with gpt-5.5` governance review
→ APPROVE → user ratify → Status → Accepted.

**Required acceptance gates (per Codex R0 P3 — doc reconciliation is part of acceptance, NOT
deferred cleanup). ALL must land in the single ratification commit before Status flips to
Accepted:**

1. `CLAUDE.md` — the "Composite rubric mandate … toward 99+ … reach Phase ~45-46" line is
   corrected to reference this ADR's reset (rubric = dashboard, not gate); the "22+ consecutive
   Tier-2 phases" claim is corrected/qualified (Phases 40–45 are Tier-0 demo work).
2. `.planning/ROADMAP.md` — header marked **SUPERSEDED by ADR-027**; the FM-02 AERON framing
   marked dead.
3. `STATE.md` truth-up — landed (done) and consistent with the corrected AERON status.
4. The AERON status note (D4) recorded; dead `codex/ENG-35/36/38` remote-branch pruning either
   done or explicitly ticketed.
5. Codex governance review APPROVE evidence archived under `reports/codex_tool_reports/`.

The 6-dim rubric definition, Tier system, calibration cap, branch protection, `golden_samples`
guards, solver truth, schemas, and CI are **untouched** by this acceptance.
