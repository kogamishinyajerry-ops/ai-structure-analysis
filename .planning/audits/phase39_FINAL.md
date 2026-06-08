# FM-04a Phase 39 — FINAL composite (rubric v2.0) · REGISTERED-fleet prospective re-baseline

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观. Composite = simple arithmetic mean of 6 dims, no
> weights, no transforms. Code @ `67c2b8e` (Phase 39 A/B head; frontend
> byte-unchanged since `b8bb8fc`). **Phase 38 (78.33) + Phase 37 (77.50) records
> are UNCHANGED — this re-baseline is PROSPECTIVE, applied forward only.**

## Composite: **80.67 / 100**

```
composite = (86 + 82 + 76 + 80 + 82 + 78) / 6 = 484 / 6 = 80.67
              D1   D2   D3   D4   D5   D6
```

| Dim | Phase 38 (recorded) | Phase 39 (registered re-baseline) | Δ | Source | Basis of the Δ |
|---|---|---|---|---|---|
| 1 FEA capability | 91 | **86** | **−5** | functional-tester (REGISTERED) | **Calibration** — Phase 38's 91 was a `general-purpose` proxy that wrongly claimed the 90-anchor fully met. The registered fleet finds Richardson coverage 38.5% < the 60% the 90-anchor requires → 80 + interpolation = 86. **FEA code byte-unchanged → NOT a regression.** |
| 2 Novice UX | 77 | **82** | **+5** | novice-simulator (REGISTERED) | **REAL Phase 39 A/B work** — 39 A (BC dead-end copy + WS-death ErrorCard) + 39 B (5 in-context hints) closed the last 80-anchor sub-bullet (in-context bubbles ≥5 surfaces) + 5/7 error-recovery paths. All 80-anchor met; interpolation to 82. |
| 3 Industrial UI | 76 | **76** | 0 | industrial-ui-comparator (REGISTERED) | **Confirmed** — registered fleet and the prior proxy agree exactly. 70 fully met + 2/3 of 80 (≥7 motion + dark tokens; no drag-resize/density/4-quadrant). Mean parity 2.4/10. |
| 4 AI workflow | 76 | **80** | **+4** | main synthesis (file:line) | **Calibration** — 76 was a stale Phase-37 interpolation; advisor code byte-unchanged. 80-anchor fully met (3 stages + 4-Q gate each); nothing of 90. → 80. (`phase39_dim4_ai_workflow_PREP.md`) |
| 5 Visualization | 72 | **82** | **+10** | functional-tester (REGISTERED) | **Calibration** — 72 was a stale Phase-37 HELD value; viz code byte-unchanged. 80-anchor fully met + 1/4 of 90 (CSV export; iso-surface + playwright E2E + two-result overlay absent). CompanionViewport confirmed side-by-side same-result (NOT overlay) → 82, the *correct* value (the Phase 38 proxy's 84 over-credited the overlay). |
| 6 Trust & repro | 78 | **78** | 0 | main synthesis | **Held** — Phase 38 *fresh* value (real 38 F/H work); Phase 39 made no trust/repro change. 80-anchor fully met + provenance/ADR(16)/trust-score (90) + failed-attempt corpus 8 (95); 99-anchor audit-log + reproduce-CLI absent. Anti-inflation: NOT pushed up without new work. |

**APPROVE gate (99+ ⟺ all 6 dims ≥ 99) FAILED** — lowest dim is Dim 3 = 76 (23
short); composite 80.67. Recorded honestly. 99-target reachable Phase ~45-46.

## Honest decomposition of the +2.33 (78.33 → 80.67)

The headline rises +2.33, but **only +0.83 of that is real Phase 39 product work.**
The rest is a one-time calibration basis-shift. Split verbatim:

- **Real Phase 39 A/B product work: +0.83** = Dim 2 +5 / 6. This is the ONLY
  dimension where code actually changed this milestone (the in-context-hint +
  error-recovery work). It is genuine and fleet-confirmed.
- **Calibration re-baseline: +1.50** = (Dim 1 −5 + Dim 4 +4 + Dim 5 +10) / 6 =
  +9/6. This is the registered fleet replacing Phase 38's mixed
  proxy/stale-carry estimates on **byte-unchanged code**:
  - Dim 1 **−5**: the Phase 38 proxy was **generous** (claimed 90-anchor met; it
    is not — Richardson 38.5% < 60%).
  - Dim 4 **+4** & Dim 5 **+10**: Phase 38 **conservatively HELD** stale
    Phase-37 values on byte-unchanged code (flagged at the time as "re-baseline
    candidates"); the authoritative reads are 80 and 82.

**The calibration cuts BOTH ways** (the exact bidirectional-drift the re-score
was warned to watch): the proxy drifted *generous* on Dim 1 and Dim 5-as-84,
while the stale carries under-credited Dim 4/5. The registered fleet is the
authoritative arbiter; from Phase 39 onward, **80.67 is the new baseline**
(registered-fleet-calibrated). Phase 38's 78.33 stands as its
proxy/stale-carry-calibrated record — the two are not apples-to-apples, exactly
as a v1.0→v2.0 basis shift is not.

## Why this is NOT a retroactive re-score

- Phase 38's record stays **78.33 / 91·77·76·76·72·78**. Phase 37 stays 77.50.
  Nothing was backfilled.
- The re-baseline is **prospective**: it establishes the registered-fleet
  baseline going forward, declared transparently, per the standing
  "PROSPECTIVE re-baseline (like v1.0→v2.0)" authorization.
- The one main-session-controlled dim with no fleet agent (Dim 6) was **held**,
  not lifted — the anti-inflation discipline applied to the dim I synthesize.

## Methodology win: the registry fix that unblocked authoritative scoring

The prior session ran R6 via `general-purpose` proxies because the eval fleet
was not registered as `subagent_type`. Root cause (corrected this session): the
Agent registry loads only from `~/.claude/agents/` (user-level) + plugins, never
the project's `<repo>/.claude/agents/`, and it loads only at session init.
**Durable fix:** the 3 agents are installed at `~/.claude/agents/` with ABSOLUTE
protocol paths (resolve from any cwd) + a session restart. This re-score is the
**first authoritative registered-fleet composite in FM-04a** — and it immediately
paid off by catching the Dim 1 generous-proxy drift the proxy era had banked.

## Fleet reports (evidence base)
- `.planning/audits/phase39_novice_simulator.md` — Dim 2 = 82
- `.planning/audits/phase39_functional_tester.md` — Dim 1 = 86, Dim 5 = 82
- `.planning/audits/phase39_industrial_ui_comparator.md` — Dim 3 = 76
- `.planning/audits/phase39_dim4_ai_workflow_PREP.md` — Dim 4 = 80 (main synthesis)
- Dim 6 = 78 held (this doc) — main synthesis

## Carry-forward findings (valid regardless of calibration)
1. **GS-001 legacy unit-mismatch** still failing in default sweep (no `@pytest.mark.legacy`) → debt-cleanup.
2. **Dev "Phase X" labels leak to end users** — `AdvancedModePromo.tsx:132`, `OnboardingTour.tsx:107` (shippedInPhase chips) → UX-polish.
3. **Results iframe has no error state** — `App.tsx:1424-1430` bare `<iframe>` → Dim 2/5 follow-up.
4. **BC-mismatch has no recovery surface** (read-only advisor) → Dim 2 follow-up.
5. **Backend 4 collection errors** (httpx version mismatch in integration tests) + 2 NLP-parser fails → debt-cleanup.
6. **`tsc -b` 16 + eslint 69 pre-existing red** → dedicated debt-cleanup phase.

## Hard-constraint compliance
- Composite = simple arithmetic mean of 6 dims (no weights/transforms). ✓
- No retroactive re-score (Phase 38 = 78.33, Phase 37 = 77.50 unchanged). ✓
- Re-baseline prospective + transparently split (real +0.83 vs calibration +1.50). ✓
- Calibration vigilance applied BOTH directions (Dim 1 down, Dim 4/5 up). ✓
- Tier 0/1 not implying Tier 2 (NAFEMS LE10 kept REFERENCE_ONLY; Dim 1 90-anchor honestly unmet). ✓
- No code touched in the re-score; Phase 1-N chain additive; App.tsx < 1500. ✓
- 24th consecutive Tier-2 phase. Local-commit only; nothing pushed.
