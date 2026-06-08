# Phase 11 E — TAA report

**Slice commit:** `4ffc8e8`
**Verdict:** APPROVE
**Test count:** 20 new (each `it()` is one test; 20 unique it-statements in `frontend/test/AdvisorPanel.test.tsx`)
**Test pass:** 20/20 new; frontend sweep 97 passed (+20 over 77 slice-D baseline); backend sweep 2054 passed + 7 skipped (unchanged)

## Per-axis evidence

- **M (12/12)** — Frontend SSOTs match the backend `advisor_critique.py` byte-for-byte. Independent runtime dump:
  - `ADVISOR_STATUS_TUPLE = ["online","offline","stub"]` ≡ backend line 69 `("online","offline","stub")`.
  - `FOUR_QUESTION_GATE_KEYS = ["llm_offline_ok","artifacts_user_owned","trustgate_explains","advisor_only"]` ≡ backend line 79-84.
  - `ADVISOR_FORBIDDEN_TOKENS` count == 9, each token character-identical to backend lines 105-117 including the case-folded `'asme compliant'` form.
  Each rendered section carries a stable testid: `advisor-panel`, `advisor-status-badge`, `advisor-degrade-reason`, `advisor-gate-checklist`, `advisor-gate-<key>` (×4), `advisor-mesh-concerns`, `advisor-bc-questions`, `advisor-failure-modes`, `advisor-unhandled-loads`, `advisor-mesh-concerns-item-<idx>` w/ `data-safe` attribute, `advisor-claim-footer`, `advisor-panel-loading`, `advisor-panel-error`. Three SSOT-pin tests assert the tuples directly.

- **T (15/15)** — Blueprint §3.E required ≥8; delivered 20. Required surface coverage: offline-status renders cleanly; forbidden-token preview client-side (per-token parametrize × 9 + tainted-entry suppression); 4-Q-gate missing-key surfaces; forward-compat parsing of pre-Phase-11 payload. Additional defensive coverage: `parseAdvisorCritique` null/missing-case_id rejection; `parseAdvisorStatus` round-trip; case-folded `ASME Compliant` catch; `NOT` (uppercase) disclaimer-form relief; fetch-error banner; unknown-status badge anti-gaming guard.

- **C (12/12)** — Tier 1 disclaimer trio surfaces twice (defense in depth): header banner via `TIER1_BANNER` constant from `trustCenterSummary.ts`; payload-side footer testid `advisor-claim-footer` renders `critique.claimTier` + `critique.claimBoundary` + `critique.claimImpact` as three `<div>` lines. Test `renders the Tier 1 disclaimer trio in the footer` asserts all three substrings present. X:-2: `_STATUS_LABEL.unknown = 'unknown advisor status (frontend out of date)'` — does NOT contain "live LLM" or "online".

- **A (8/8)** — All three defensive layers wired:
  - A:-2: `parseAdvisorStatus` returns `'unknown'` for `undefined` or any value not in `ADVISOR_STATUS_TUPLE`. `parseAdvisorCritique` rejects null/non-object/missing case_id, coerces every other field with safe defaults.
  - A:-3: `isAdvisorEntrySafe` runs in `_Section` component before rendering each entry; unsafe entries render `'[entry suppressed — contains a forbidden positive claim outside not <claim> form]'` with `data-safe="false"` and red italic styling.
  - X:-2: Unknown-status badge surfaces neutral grey with explicit "frontend out of date" label.

- **E (8/8)** — Frontend new-panel sweep `vitest run test/AdvisorPanel.test.tsx` → `20 passed, 0 failed, 708ms`. Full frontend sweep → `Test Files 11 passed (11), Tests 97 passed (97), 1.67s` — matches commit claim. `tsc --noEmit` → exit 0, zero output. Backend full sweep unchanged from slice-D close.

- **V (8/8)** — APPROVE: rubric fully met. `git show --stat 4ffc8e8` confirms exactly 5 files changed. No `golden_samples/**` writes, no signed-registry mutation, no backend service code touched, no node_modules churn. App.tsx mount guard at line 1659 is byte-identical structure to the ProvenancePanel guard. Slice-D TAA archive is a valid 5032-byte report.

## Findings

(no HIGH / MEDIUM / LOW findings)

Side notes (informational, not findings):
- The four-question-gate checklist correctly renders `?` for missing keys (parser defaults to `{}` for forward-compat payloads). This is the only path where a key may be neither `true` nor `false`. Not a test gap.

## Cumulative slice E axes
M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 8 = **63 / 63**
