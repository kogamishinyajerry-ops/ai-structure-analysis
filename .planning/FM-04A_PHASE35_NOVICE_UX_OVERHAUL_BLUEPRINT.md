# FM-04a Phase 35 — Novice UX overhaul + verdict YAML schema backfill

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-34. **19 consecutive Tier-2 phases**.

## Position in the 99+ journey

Phase 34 (the first feature-build phase under rubric v2.0) closed
at composite 72.50/100. Sub-agent R2 surfaced TWO new honest
friction points introduced by Phase 34 B (CaseOpenAdvisorCard
jargon-leak + static-vs-dynamic 4-Q-gate semantic ambiguity), plus
flagged the long-standing legacy verdict YAML schema heterogeneity.
Phase 35 closes those + does broader Novice UX work.

Projected lift: **Phase 35 composite 74-77 / v2.0** (+1.5-4.5).

## Slice plan

| Slice | What lands | Projected dim impact |
|---|---|---|
| 35 blueprint | This document | — |
| **35 A** | `CaseOpenAdvisorCard` jargon + static-gate fix. (1) Replace raw `notesExcerpt` rendering with a CURATED orientation derived from `displayLabel + analysis_type/case_kind detection from caseId + claim_boundary`. The 1-paragraph brief no longer leaks "Phase 21+ scope", "tier_2_validated", or "single-hex coupons" vocabulary. (2) Add `static · offline-first` styling hint to the 4-Q gate at this surface (muted color + "(client-side stub status)" subtitle) so reviewers can immediately distinguish from the AdvisorPanel's dynamic gate. Closes Phase 34 #27 + #28. | Dim 2 +3-5 / Dim 4 +1 |
| **35 B** | Verdict YAML schema 1.0 → 1.4 backfill. Add additive `solver_kind:` field to 9 legacy verdict YAMLs (GS-100, GS-101, GS-102, GS-102-refined, GS-102-hifi, GS-103-jet, leak case, plus any others still at schema 1.0). NO behavior change — pure metadata enrichment. Schema_version bumped 1.0→1.4 on each (additive minor). Closes Phase 34 #29. | Dim 6 +1 |
| **35 C** | `useUploadErrorRecovery` custom hook in `frontend/src/state/` + `ErrorCard` wiring into `App.tsx` upload + selectCase paths. Hook approach keeps App.tsx LOC under Phase 29 B <1500 pin (the Phase 33 D rollback lesson — extract state into a hook first, then wire). 2 of 5 missing error-recovery paths from Phase 33 C novice_simulator finding #2 closed. | Dim 2 +2-3 / Dim 6 +0.5 |
| **35 D** | 3 sub-agents R3 audit + FINAL composite + retro + STATE refresh + commit. | — |

**Total projected composite lift: +1.5-2.5 (72.50 → ~74-75)**

## Phase 35 anti-gaming guards

All Phase 33/34 guards (A-J) carry verbatim. Phase 35-specific:

- **K:-1** (NEW): Phase 35 A jargon fix must NOT break the
  `case-open-advisor-brief` test-id surface — the existing Phase 34 B
  tests should continue to pass; only the *content* changes.
- **L:-1** (NEW): Phase 35 B schema backfill is ADDITIVE ONLY —
  existing schema-1.0 verdict YAML readers must continue to work
  without modification. The new `solver_kind:` field is OPTIONAL
  per-schema.
- **M:-1** (NEW): Phase 35 C App.tsx LOC must stay under the
  Phase 29 B <1500 pin. Hook extraction must succeed BEFORE the
  ErrorCard wiring is added.

## Slice 35 A details

**Problem** (Phase 34 D novice_simulator finding #27 + #28):

1. **Jargon leak**: `CaseOpenAdvisorCard.tsx:104-109` calls
   `composeBrief(caseRecord)` which renders `notesExcerpt` verbatim.
   The notesExcerpt strings in `candidateCaseRegistry.ts:156-161`
   and similar entries leak internal vocabulary ("Phase 21+ scope",
   "tier_2_validated", "single-hex coupons") to novice personas.

2. **Static-vs-dynamic gate ambiguity**: `CaseOpenAdvisorCard.tsx:67-80`
   renders 4 static ✓ ticks unconditionally; `AdvisorPanel.tsx:184-190`
   renders the same 4 keys DYNAMICALLY from backend critique
   payload. Same vocabulary, different semantics. Reviewer P3 loses
   governance trust.

**Fix scope**:
- `composeBrief()` no longer reads `notesExcerpt`. Instead, infer
  the case type from `caseId` prefixes/patterns (e.g., starts with
  `cantilever-` → static structural; `plate-with-hole-` → stress
  concentration; `heat-transfer-` → heat transfer; etc.) and emit
  a CURATED 1-paragraph orientation appropriate to that type.
  Fallback to a generic "this is an engineering candidate case;
  open the Visual tab for full critique" message if the case kind
  isn't recognized.
- Add `static-gate-hint` styling at the 4-Q gate surface: muted
  color + small subtitle line "(client-side stub status; the
  Visual tab renders a backend-validated gate)" so the semantic
  difference is OBVIOUS at a glance.
- Update Phase 34 B tests accordingly (existing test for "brief
  mentions notesExcerpt content" inverted to "brief does NOT
  contain internal jargon tokens like 'Phase 21' or
  'tier_2_validated'").

**Anti-gaming guards within 35 A**:
- K:-1: `case-open-advisor-brief` + `case-open-advisor-four-question-gate`
  test-ids preserved
- D:-1: jargon-leak test pin asserts absence of specific tokens
- C:-1: AdvisorPanel UNCHANGED (I:-1 from Phase 34 carries forward)

## Slice 35 B details

**Problem** (Phase 34 D functional_tester finding):
9 legacy verdict YAMLs at schema 1.0 lack `solver_kind:` field;
cohort-wide grep under-counts solver kinds. Affects:
- `GS-100-candidate`, `GS-101-candidate`, `GS-102-candidate`,
  `GS-102-refined-candidate`, `GS-102-hifi-candidate`,
  `GS-103-jet-impingement-candidate`,
  `rod-wave-impact-energy-leak-candidate` (ballistic/dynamic class)
- 2 more legacy entries (check the actual cohort directory listing)

**Fix scope**:
- For each legacy verdict YAML at schema 1.0:
  - Determine the case's solver kind from its analysis context
    (most legacy cases are `explicit_dynamics` ballistic per the
    GS-100 series)
  - Add `solver_kind: <kind>` line (additive)
  - Bump `schema_version: "1.0.0"` → `"1.4.0"` (additive minor;
    matches Phase 34 C schema)
- NO behavior change. The reader's existing schema-1.0 path
  continues to work; new field is optional read-only enrichment.
- Backend test pin: `test_phase35b_verdict_yaml_solver_kind_backfill.py`
  asserts every cohort verdict YAML now has `solver_kind:` field +
  the field's value is one of the 6 known enum values.

**Anti-gaming guards within 35 B**:
- L:-1: pure additive; no breaking changes; existing readers work
- D:-1: backfill mapping documented per case (case_id → solver_kind)
- C:-1: schema enum unchanged (6 values: linear_static, modal,
  buckling, dynamic, heat_transfer_steady_state, contact_pair_static,
  + new `explicit_dynamics` for ballistic OR re-use existing
  `dynamic` if appropriate)

## Slice 35 C details

**Problem** (Phase 33 C novice_simulator finding #2 + Phase 33 D
rollback):
5 silent error-recovery paths in App.tsx (FRD upload silent
console.error / PDF export crude alert / WebSocket death no
reconnect / stop request silent / solver-start raw [ERROR] log).
Phase 33 D attempted ErrorCard wiring but reverted because the
~71-LOC growth tripped the Phase 29 B <1500 pin.

**Fix scope**:
- Extract error-recovery state into `frontend/src/state/useUploadErrorRecovery.ts`
  (~80 LOC NEW file). Custom hook follows Phase 32 B
  `useAppUiMode` pattern. Returns `{ uploadError, setUploadError,
  clearUploadError, withRecovery }` where `withRecovery(asyncFn,
  options)` wraps a try/catch and surfaces errors via ErrorCard
  shape on failure.
- Wire 2 of the 5 paths through the hook:
  1. `generateReportFromFile` upload path
  2. `selectCase` case-load path
- App.tsx growth target: ≤10 LOC (the hook absorbs the state +
  catch blocks; App.tsx just gains 1 import + hook call + 1 render).
- Backend WebSocket / PDF export / stop request paths deferred to
  Phase 36+ (broader scope; need separate hook extractions).

**Anti-gaming guards within 35 C**:
- M:-1: App.tsx LOC stays under 1500 (verified via wc -l after
  edit + before commit)
- I:-1 (carryover from Phase 34): `ErrorCard.tsx` unchanged
- D:-1: hook tests pin the `withRecovery` contract; ErrorCard
  render tests reuse the existing Phase 18 D test surface

## Phase 35 projection

| Dim | Phase 34 | Phase 35 projected | Δ | Lift source |
|---|---|---|---|---|
| 1 FEA | 87 | 87 | 0 | Untouched (Phase 36+ cohort expansion) |
| 2 Novice UX | 59 | 66-70 | +7-11 | Jargon-leak fix (#27) + static-gate distinction (#28) + 2 error-recovery paths closed |
| 3 Industrial UI | 73 | 73 | 0 | Untouched |
| 4 AI workflow | 72 | 73 | +1 | Static-gate visual distinction at CaseOpenAdvisorCard improves 4-Q-gate semantic clarity |
| 5 Visualization | 72 | 72 | 0 | Untouched |
| 6 Trust | 72 | 73-74 | +1-2 | Schema 1.0→1.4 backfill closes cohort grep under-counting; error-recovery paths add provenance coverage |
| **Composite** | **72.50** | **~74-75** | **+1.5-2.5** | Within projected band 74-77 |

## Hard constraints

All Phase 18-34 hard constraints carry verbatim:
- HF1.7a/b/8 signed-registry hard-stop + *-candidate carve-out
- tmp_path-only test writes
- v2.3 round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract
- prefers-reduced-motion honored on any new motion (35 A static-gate
  styling will respect reduce-motion)
- Anti-gaming guards A-J + new K/L/M for this phase
- Phase 1-N additive only (no test threshold edits; App.tsx <1500)
- Rubric v2.0 99-anchor reachable via verifiable evidence
- NEVER re-score prior phases retroactively
- NEVER apply weights/transforms to composite
- No push / no PR / no Linear / no Notion writes

## Closing

Phase 35 closes the unanticipated Phase 34 B friction points
(#27 + #28) plus the long-standing schema heterogeneity (#29) and
adds 2 concrete error-recovery paths. The composite lift is modest
(+1.5-2.5) but the Novice UX axis advances meaningfully — Dim 2
59 → ~66-70 is the biggest single-dim lift since Phase 33 C
established the rubric v2.0 baseline.

This is the user's stated mandate axis (新手人类用户的使用难度、
交互模式) finally getting first-class attention after Phase 33-34's
foundation + cohort-and-advisor focus.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 19 consecutive
Tier-2 phases.
