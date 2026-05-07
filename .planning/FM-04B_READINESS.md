# FM-04b — Tier 2 signed validation readiness (preparation only)

> **Status:** preparation document.
> **This document does NOT promote any artifact to Tier 2.**
> **Tier 2 promotion is gated by the user milestone-experience checkpoint per
> AGENTS.md and ADR-023 §Tier 2.**
>
> **Authored:** 2026-05-07 under user direct-execution authorization.
> **Last updated:** 2026-05-07 (FM-04a P9 closeout).

---

## Purpose

When the user is ready to start FM-04b (Tier 2 signed bullet-vs-steel
validation against Børvik 2002), this document is the single page that says:

- what FM-04a already prepared (so we don't re-do it),
- what FM-04a deliberately deferred (so we don't accidentally treat Tier 1
  output as Tier 2),
- what the FM-04b path must produce per ADR-023 §Tier 2,
- what the explicit gate is between FM-04a and FM-04b (the user milestone
  checkpoint).

Authoring this readiness page does NOT itself authorize any Tier 2 work.

---

## What FM-04a already prepared

The branch stack on `claude/FM-04a-tier1-ballistic-candidate` (descended from
`codex/evidence-first-workbench-trust-center`) lands the following Tier 1
foundation, all under explicit "not signed validation; not benchmark
agreement" wording:

| Slice | Commit | Asset | Tier 2 relevance |
|---|---|---|---|
| FM-03 | `5ba6e4e` | Candidate Report Spine v1 (assumptions / artifact manifest / mesh evidence / convergence evidence / reviewer summary / Tier 2 blockers) | spine consumer surface; FM-04b adds benchmark comparison fields without breaking v1 |
| FM-04a P1 | `7877e7a` | Spine schema v2 — `ballistic` block (V0 / vR / perforation_marker / energy_balance / animation_manifest / time_step_series / time_step_convergence_study / tier2_blockers_ballistic) | the read contract Tier 2 must produce sidecars against |
| FM-04a P2-lite | `d99c728` | `docs/adr/ADR-024-ballistic-benchmark-source-selection.md` (parameters-only Børvik 2002 cite; Tier 2 explicitly deferred) | superseded by ADR-024 (full) when FM-04b begins; supplies parameter source for P3 deck |
| FM-04a P3 | `9a358b4` | `golden_samples/GS-102-candidate/` (NEW directory, `^GS-\d{3}$` excluded; `expected_results.json` carries `tier2_promotion_blockers` list) | the deck location FM-04b promotes to GS-102 (drop the `-candidate` suffix) once signed; nothing about the directory yet implies Tier 2 |
| FM-04a P4 | `4e26041` | `aeron/drivers/openradioss_backend.py` + `SolverBackend.OPENRADIOSS` enum + 12 tests (mock-driven) | adapter is Tier-1-tagged; switching its claim metadata to Tier 2 is intentionally a separate, reviewer-gated change |
| FM-04a P5 | `28bc937` | spine `time_step_convergence_study` consumer + candidate stability rule (`candidate_observed_stable / unstable / unknown`) | health flag only; Tier 2 tolerance comparison is a different rule, lives in FM-04b code path |
| FM-04a P6 | `7a41f0e` | `backend/app/services/ballistics/metric_extraction.py` + frontend Trust Center "Ballistic candidate" section + three Copilot review cards | Trust Center wording deliberately uses `warning` colour for `perforated_candidate` so a Tier 1 surface never feels like Tier 2 victory |
| FM-04a P7 | `7e964e7` | `backend/app/services/ballistics/convergence_writers.py` + 9 tests (mesh + dt sidecar writers parallel to the spine reader) | gives FM-04b a stable producer surface; Tier 2 may extend the writers but not their schema |
| FM-04a P8 | `77987e7` | `scripts/fm04a_synthetic_pipeline.py` + 3 tests (synthetic e2e demo without OpenRadioss installed) | smoke handhold; FM-04b will replace synthetic data with real OpenRadioss output, not change the pipeline shape |

In short: FM-04a delivers a fully-shaped Tier 1 candidate stack with read +
write parity, schema discipline, and explicit claim-tier wording at every
layer. FM-04b is wiring real benchmark data + reviewer evidence on top of
this stack, not replacing it.

---

## What FM-04a deliberately did NOT do (Tier 2 prerequisites still missing)

These are the Tier 2 ingredients required by ADR-023 §Tier 2 that **none of
FM-04a P0–P8 supplies**. Treat any document, code, or wording that suggests
otherwise as a forbidden-wording violation.

1. **No public benchmark case is locked.** ADR-024 (lite) cites Børvik 2002
   for parameter source only; it explicitly defers locking a single
   `{nose, V0, plate thickness}` tuple to ADR-024 (full) under FM-04b.
2. **No tolerance specification.** ADR-024 (lite) lists `±10%` only as a
   *proposed* draft; the locked tolerance must be set by the FM-04b
   independent reviewer.
3. **No uncertainty interval / measurement traceability.** Børvik 2002
   experimental data carries its own uncertainty; this is reserved for
   ADR-024 (full).
4. **No citation compliance review for experimental data republication.**
   ADR-024 (lite) authorizes parameter-value citation only. Republishing
   experimental tables alongside candidate output requires a separate
   compliance review.
5. **No benchmark comparison artifact.** No `benchmark_comparison_candidate.
   json` (or signed equivalent) is produced; the spine has no consumer for
   such a payload yet.
6. **No artifact hash freeze / sealed packet.** Tier 2 requires every deck,
   log, animation, and metric file to be hashed into a sealed, immutable
   packet. FM-04a writes hashes per artifact but does NOT freeze them.
7. **No independent reviewer evidence.** ADR-011 + ADR-023 both require
   reviewer/signoff evidence for Tier 2. FM-04a runs no independent
   reviewer pass.
8. **No user milestone-experience acceptance.** AGENTS.md reserves human
   acceptance for feature-milestone checkpoints; FM-04a is not yet
   accepted, and FM-04b promotion needs its own user acceptance.
9. **No Tier 2 status flip.** `golden_samples/GS-102-candidate/expected_
   results.json` still carries `status = insufficient_evidence` and a
   `tier2_promotion_blockers` list. The flip to a `^GS-\d{3}$` signed
   sample (e.g. `GS-102`) requires every item above first.
10. **No Notion / Linear external mirror.** FM-04a never touched external
    write paths. FM-04b mirroring is itself gated by the user.

---

## FM-04b path (informational; do NOT execute without explicit user
authorization)

The original FM-04b plan from the deep-planning document still holds. The
phases below assume FM-04a has been **user-accepted at the milestone
checkpoint**; without that, FM-04b is blocked.

| FM-04b phase | Scope | Forbidden until previous phase signs off |
|---|---|---|
| **P2-full** | Supersede ADR-024 (lite) with ADR-024 (full): lock single benchmark case (e.g. Børvik 2002 hemispherical Ø20mm vs 12mm Weldox 460E plate at one specific V₀); lock tolerance; lock uncertainty interval; complete citation compliance review | None of P7..P9 |
| **P7 (Tier 2)** | Author `benchmark_comparison_candidate.json` schema + spine consumer + producer; populate from real OpenRadioss output vs locked benchmark experimental data | P8 / P9 |
| **P8 (Tier 2)** | Sealed packet: SHA-256 freeze of every deck / log / animation / metric / spine / comparison artifact; manifest of manifests; double independent reviewer pass (Claude Opus + Codex `gpt-5.5 xhigh` blind reviews per ADR-011) | P9 |
| **P9 (Tier 2)** | User milestone-experience acceptance; flip `golden_samples/GS-102-candidate/` to `golden_samples/GS-102/` with `expected_results.json status=active`; spine `claim_tier` switches to `Tier 2 signed validation against ADR-024 (Børvik 2002 …) within ±X% residual velocity tolerance`; Notion + Linear mirrors update from repo SSOT | — |

Any of these phases failing review must roll back to the failing phase, not
ship a partial Tier 2 claim.

---

## Hard rules for FM-04b authoring (when you start)

1. **No drift on FM-04a wording.** Every Tier 1 banner must keep saying "not
   benchmark agreement" until ADR-024 (full) is merged AND P7 lands AND P8
   reviewer evidence is archived AND P9 user acceptance is recorded. Even
   then, only the specific Tier 2 surface (the signed packet + the spine's
   own `claim_tier` field after P9) flips wording. Logs, decks,
   intermediate sidecars stay Tier 1 candidate so historical evidence
   remains honest.
2. **No ADR-024 (full) write without owner approval.** ADR-011 lists ADRs
   under the PR-protected zone (M1 trigger). ADR-024 (full) is a
   governance-changing document and must go through Codex review before
   merge.
3. **No HF1 override beyond what FM-04a already exercised.** FM-04a P3 used
   `HF1_GUARD_OVERRIDE` once for the GS-102-candidate registration cover.
   Promoting to GS-102 in FM-04b P9 needs a fresh override + ADR cover; do
   not reuse the FM-04a override token.
4. **No Linear / Notion writes until P9 owner-gate completes.** AGENTS.md is
   explicit: external writes are gated.
5. **No `agents/solver.py` HF1 override unless it's the actually-needed
   wiring.** If FM-04b can produce real OpenRadioss output through a less
   invasive path (e.g. a CLI wrapper that bypasses the LangGraph node),
   prefer that. The HF1 override token is a finite-trust resource.

---

## What this document is NOT

- **Not** an authorization to start FM-04b. The user must explicitly say
  "start FM-04b" with the FM-04a milestone accepted.
- **Not** an ADR. ADR-024 (full) is a separate document under
  `docs/adr/`; this readiness page lives under `.planning/` and is mutable
  preparation material.
- **Not** a benchmark-comparison artifact. No real or proposed numerical
  comparison appears in this file.
- **Not** a substitute for AGENTS.md, ADR-011, ADR-013, or ADR-023. Where
  this document conflicts with any of those, the ADRs and AGENTS.md win.

---

## How to use this document at FM-04b kickoff

1. Re-read AGENTS.md, ADR-023 §Tier 2, ADR-011 §HF1.
2. Capture user explicit authorization for FM-04b in writing (the kickoff
   request itself).
3. Write ADR-024 (full) as a draft PR; route through Codex M1 trigger and
   the owner gate.
4. Only after ADR-024 (full) merges, start P7 (Tier 2).
5. After every FM-04b phase, re-update this readiness page so a future
   reader can see where the Tier 2 path actually stands.
6. After P9, this file is superseded by the FM-04b retrospective; archive
   it and stop using it as live planning material.
