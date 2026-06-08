# FM-04a Phase 3 — Reviewer Workbench Polish · Retrospective

> **Branch:** `claude/FM-04a-tier1-ballistic-candidate`
> **Phase span:** `7f726bb..de3e90d` (5 commits, 2026-05-16, single session)
> **Boundary stamp:** Tier 1 engineering candidate; **not signed validation;
> not benchmark agreement; not a sealed FM-04b P8 bundle**.
> **Authorization:** user direct-execution authorization 2026-05-07/16
> ("全权授予你开发权限，你作为项目负责人…直至达成蓝图目标"). No push,
> no PR, no Linear / Notion / external-system writes; no real OpenRadioss
> dependency exercised.

---

## What this retrospective is NOT

- Not a Tier 2 promotion.
- Not an FM-04b prerequisite.
- Not a benchmark comparison.
- Not an ADR-024 (full) artifact.
- Not a signed-registry mutation; the `^GS-\d{3}$` registry is unchanged.
- Not a Linear ENG-* closeout; reviewer-side issues remain the user's
  to author.

---

## Phase 3 input: the five reviewer-experience gaps (R1..R5)

The Phase 2 industrial-polish pass left five reviewer-side gaps still
open on the Workbench surface. Phase 3 closed each one with an
additive, read-only, Tier-1-banner-preserving slice — no FM-04b
prerequisite crossed.

| Gap | Phase | Status | Closure summary |
|-----|-------|--------|-----------------|
| **R1** Acceptance evidence packet missing | A | ✅ closed | JSON manifest with artifact hashes + claim boundary + 8-tuple of FM-04b blockers remaining; pure builder + endpoint + CLI + 9 unit tests. |
| **R2** No structured case-vs-case diff | B | ✅ closed | Two acceptance packets diffed across 5 numeric + 2 artifact axes; pure builder + endpoint + 9 unit tests. |
| **R3** Reviewer surface not wired in Workbench | C | ✅ closed | Two typed clients + two React panels + Visual-tab integration + two Trust Center cards; 15 frontend tests. |
| **R4** Convergence study still raw JSON | D | ✅ closed | Sidecar endpoint + typed client + viewer component with tone-coded per-axis tables and combined-verdict badge; 6 backend + 10 frontend tests. |
| **R5** Phase 2/3 endpoints lack HTTP-layer tests | E | ✅ closed | 16-test TestClient suite via httpx.AsyncClient + ASGITransport (supported migration path post starlette.testclient incompatibility); covers status / content-type / disposition / Tier 1 boundary / cross-endpoint positive-claim audit. |

---

## Commit ledger

| Commit | Phase | Files changed | Tests added | One-line summary |
|--------|-------|---------------|-------------|------------------|
| `f22f619` | Plan | 1 (`.planning/FM-04A_PHASE3_BLUEPRINT.md`) | — | Phase 3 blueprint authored: R1..R5 closure plan. |
| `7f726bb` | A | 5 (`acceptance_packet.py` × 2 + script + test + main.py) | +9 | Acceptance evidence packet builder + endpoint + CLI. |
| `c7d71eb` | B | 4 (`case_comparison.py` × 2 + test + main.py) | +9 | Case-vs-case comparison builder + endpoint. |
| `73c4b3d` | C | 7 (2 clients + 2 components + 2 client tests + App.tsx) | +15 (frontend) | Reviewer panel wired into Visual tab + 2 Trust Center cards. |
| `2796a20` | D | 7 (endpoint + client + viewer + endpoint test + client test + main.py + App.tsx) | +6 backend / +10 frontend | Convergence study sidecar endpoint + viewer. |
| `de3e90d` | E | 1 (`test_api_endpoints_integration.py`) | +16 | HTTP-layer integration tests across every Phase 2/3 endpoint. |
| (this) | F | `.planning/STATE.md` + `fm04a_phase3_reviewer_workbench.md` | — | STATE refresh + retrospective. |

---

## Mechanical verification baseline

Each commit cleared its own verification gate before being authored; the
final post-Phase-E numbers are the bookend:

- **Backend pytest:** 1333 passed / 8 skipped (Phase 2 baseline 1293
  → +40 tests, zero regressions).
- **Frontend node:test:** 54 passed (Phase 2 baseline 29 → +25 tests,
  zero regressions).
- **TypeScript:** `tsc -b` clean.
- **Vite build:** `npm run build` clean (1739 modules; 325.96 kB
  bundle / 95.13 kB gzipped).
- **Ruff:** `ruff check` + `ruff format` clean on every commit.
- **HF1 path-guard:** every commit cleared the pre-commit guard.

---

## What worked

1. **Pure-function builders + thin endpoint/CLI wrappers.** Same
   pattern as Phase 2 E (`tier1_candidate_report`) carried straight
   into Phase 3 A (`acceptance_packet`) and 3 B (`case_comparison`).
   Each new feature got: one pure module, one endpoint wrapping
   `Response(content=...)` so no `tempfile.NamedTemporaryFile`
   SIM115 noise, one dedicated test file.
2. **Build-time `_assert_no_overclaim` guards.** Phase 3 A's builder
   refuses to emit "validated against", "benchmark agreement",
   "signed validation", "perforation completed",
   "bullet-through-steel complete", "validated physics" at build
   time. Phase 3 B and the cross-endpoint audit in Phase 3 E reuse
   the same forbidden list. Each ships its own test that strips the
   "not <claim>" disclaimer phrases first, then audits the residue.
   This makes accidental promotion mechanically impossible.
3. **`_assert_not_in_golden_samples`.** The same one-function check
   from Phase 2 (orchestrator + report writer) extends to Phase 3 A
   (`write_acceptance_packet`). No new writer path crosses the
   signed-registry boundary, and the test asserts on the exact
   `golden_samples` path-segment match.
4. **HTTP-layer tests via httpx.AsyncClient + ASGITransport.** Found
   starlette.testclient incompatible with httpx 0.28
   (`Client.__init__() got an unexpected keyword argument 'app'`).
   Wrote a tiny `_SyncASGIClient` wrapper around the supported
   migration path rather than pin httpx down. Local to the test file
   so the rest of the repo can stay on starlette.testclient when its
   version pinning catches up.
5. **Cross-endpoint positive-claim audit in one test.** Phase 3 E's
   final test hits five endpoints in one go and asserts every body is
   free of the forbidden tokens. This catches accidental leakage
   anywhere in the surface stack — builders, renderers, route
   handlers, error messages — without per-endpoint duplication.
6. **Reusing `trustCenterSummary.convergenceTone` in Phase 3 D.** The
   viewer's per-axis badge + combined-verdict badge both route
   through the existing Phase 2 D tone helper. No new tone-rule
   surface; the Trust Center card and the viewer stay aligned by
   construction.
7. **Static fallback lists in the frontend.** `acceptancePacketClient`
   + `caseComparisonClient` + `convergenceStudyClient` all return
   structured `{ packet|comparison|study, source: 'live'|'fallback',
   error }` shapes. Even when the backend is unreachable, the
   Workbench surfaces the picker UI with a tagged-fallback banner
   rather than a blank panel.
8. **`.ts`-suffix imports for node:test.** `node --test
   --experimental-strip-types` rejects extension-less relative
   imports. Adding `.ts` to `./trustCenterSummary` in
   `convergenceStudyClient.ts` matched the same pattern already in
   `main.tsx` (`import App from './App.tsx'`) and tsc/vite stayed
   clean.

---

## What was deliberately deferred (FM-04b prerequisites unchanged)

These remain on the FM-04b side. Phase 3 A's acceptance packet lists
each one verbatim in its `tier2_blockers_remaining` array; the Trust
Center cards surface the same boundary in the operator strip:

1. **ADR-024 (full)** — locked benchmark case + tolerance + uncertainty
   interval. Phase 3 stayed on ADR-024 lite (parameters-only citation).
2. **`benchmark_comparison_candidate.json`** schema + producer (FM-04b
   P7). No comparison vs experimental data was written in Phase 3.
3. **Sealed packet** — SHA freeze + manifest of manifests (FM-04b P8).
   The Phase 3 A acceptance packet is a Tier 1 candidate manifest,
   explicitly **not** a sealed Tier 2 bundle, and the test asserts
   the wording.
4. **Independent reviewer signoff** (FM-04b P8). Not attached.
5. **User milestone-experience acceptance** (FM-04b P9). Reserved.
6. **`^GS-\d{3}$` registry flip** from `-candidate` (FM-04b P9).
   Candidate-cases endpoint regex filters out the signed registry
   shape by construction.
7. **Linear / Notion mirror writes** — user-controlled. Phase 3
   wrote nothing external.
8. **Per-term plastic / contact / hourglass energy breakdown** via
   `/TH/PART`. Phase 2 A's `closed_aggregate` audit still aggregates
   into `I-ENERGY`; the per-term split is FM-04b track.

---

## Process notes

- **Single-session, single-author, no Codex relay.** Authorized by
  user direct-execution; Codex review remains required to flip the
  branch back to Codex-primary or to promote Tier 1 → Tier 2. The
  full 27-commit local arc (Phase 2 `b3c97ef` through Phase 3
  `de3e90d` + planning files) sits ahead of `de65d15` without a
  push.
- **No HF1 forbidden zones touched.** Every new file lives under
  `backend/app/services/reporting/`, `backend/app/api/routes/`,
  `frontend/src/`, `frontend/test/`, `tests/`, or `.planning/`.
  `pre-commit run hf1-forbidden-zone-path-guard` passed on every
  commit.
- **No `uv.lock` mutation.** Convention from the local-arc closure
  (`f55b228`) preserved; `uv.lock` is intentionally untracked.
- **No real OpenRadioss execution.** Every Phase 3 test uses
  synthetic fixtures. CI behavior unchanged.
- **Frontend test runner.** `node --test --experimental-strip-types`
  used as in Phase 2 D / C; no Jest / Vitest dependency added.
- **Trailer rewrite reserved for push time.** `Execution-by:
  codex-primary` / `Linear-Issue: ENG-<id>` HF5 trailers are NOT
  applied locally; they remain a push-time concern when the user
  promotes the branch (CI's `trailer-check` workflow will enforce).

---

## Candidate next slices (each independently shippable, none cross FM-04b)

1. **Cross-case ranked dashboard** — for a single Workbench user
   reviewing many candidate cases, render a one-page leaderboard of
   every `golden_samples/*-candidate/` case scored by combined
   verdict + energy balance error + perforation marker + last
   modification timestamp. Pure read; no new builder. ~250 LOC.
2. **Acceptance packet diff** — extend Phase 3 B to diff *acceptance
   packet JSON files* (not just live re-builds), so a reviewer can
   bring two archived packets and see how their assumptions /
   limitations / blockers lists changed. Strict additive.
3. **Per-axis convergence sparkline** — adds an inline SVG sparkline
   (no chart library) next to each AxisTable badge showing the
   sweep's metric trajectory. Stays in the existing viewer scope.
4. **DOCX renderer for the acceptance packet** — mirror Phase 2 E's
   markdown + DOCX shape but for the acceptance manifest instead of
   the report. Same `python-docx` dep, same `Response(content=...)`
   pattern.
5. **Empty-state telemetry** — surface a Trust Center card listing
   *every* candidate case whose `convergence_study.json` is missing,
   so the picker dropdown can be sorted by evidence completeness
   instead of alphabetical case_id. Pure read; reuses the Phase 3 D
   resolver.

Each is in scope under the existing user authorization. None requires
ADR-024 (full), benchmark data, sealed packets, signed registry, or
external-system writes.

---

## Closure

FM-04a Phase 3 is operationally complete on `claude/FM-04a-tier1-ballistic-candidate`.
Reviewer side now has: a structured acceptance manifest, a
case-vs-case diff, a Workbench panel that surfaces both, a
visualized convergence study, and HTTP-layer tests covering every
Phase 2 / Phase 3 endpoint. Tier 1 boundary is preserved at builder
level, endpoint level, frontend level, and test-audit level.
FM-04b prerequisites are unchanged. Nothing pushed.
