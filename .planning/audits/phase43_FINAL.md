# FM-04a Phase 43 — FINAL composite (rubric v2.0) · registered-fleet audit

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观. Composite = simple arithmetic mean of 6 dims, no weights,
> no transforms. Code @ `c3422b4` (Phase 40-43 head; working tree = untracked files
> only, no tracked modifications). **Phase 39 (80.67), Phase 38 (78.33), Phase 37
> (77.50) records are UNCHANGED** — this audit applies forward only; nothing
> backfilled.

## Composite: **81.33 / 100**

```
composite = (82 + 84 + 78 + 80 + 86 + 78) / 6 = 488 / 6 = 81.33
              D1   D2   D3   D4   D5   D6
```

| Dim | Phase 39 (recorded) | Phase 43 | Δ | Source | Basis of the Δ |
|---|---|---|---|---|---|
| 1 FEA capability | 86 | **82** | **−4** | functional-tester (fleet) | **Re-score variance, NOT a regression.** FEA code (`cross_check`/`solver`/`inp_writer`/`parsers`) is **byte-unchanged** since Phase 39 (`67c2b8e..HEAD` empty diff). The fleet this cycle applied a stricter 90-anchor read: Richardson <60% of refinable cases + NAFEMS LE10 is `REFERENCE_ONLY` (no agreement). Same precedent as Phase 39's own D1 −5. |
| 2 Novice UX | 82 | **84** | **+2** | novice-simulator (fleet) | **Real Phase 40-43 work** — 6 recovery templates + in-context hints fully deliver the "every error state has recovery" 90-sub-bullet (`useUploadErrorRecovery.ts:98-209`). Capped by no role-branching + no WCAG audit + 2 silent-boot/failed-solve recovery gaps. |
| 3 Industrial UI | 76 | **78** | **+2** | industrial-ui-comparator (fleet) | **Real Phase 40-43 work** — new chrome (ScaleBar legend, colormap selector, shortcuts overlay, nav gizmo, status bar, hero readout) lifts aspect mean to 8.0/10. Capped by absent drag-resize/density/collapsible-rails (the four 90-anchor layout systems). |
| 4 AI workflow | 80 | **80** | 0 | main synthesis | **Held** — no AI-workflow capability work this milestone (Phase 40-43 were frontend viz/UX). The sole AI-adjacent edit was the Copilot solve-start timestamp in `handleExecuteCopilotAction` — a timing-correctness fix, not a workflow-capability change. Anti-inflation: NOT lifted without work. |
| 5 Visualization | 82 | **86** | **+4** | functional-tester (fleet) | **Real Phase 40-43 work** — colormap engine (`colormaps.ts`, 4 ramps, default-preserving), ScaleBar legend, iso-surface overlay, honest never-fabricated progress. 80-anchor + 3/4 of 90. Capped by no playwright/real-WebGL E2E + no PNG/VTU UI export path. |
| 6 Trust & repro | 78 | **78** | 0 | main synthesis | **Held** — reproducibility infrastructure (manifests, hashes, claim-tier registry, honest GS-001 downgrade) byte-unchanged. The GS-001 stale-test units bug surfaced this cycle is **flagged, not lifting and not lowering** the score (see below). Phase 43's honesty-positive viz work (honest progress, legend-cannot-lie) is credited in D5, not D6. |

**APPROVE gate (99+ ⟺ all 6 dims ≥ 99) FAILED** — lowest dims are D3 = 78 and D6 =
78 (21 short); composite 81.33. Recorded honestly.

## Honest decomposition of the +0.66 (80.67 → 81.33)

The headline rises +0.66. Split by cause:

- **Real Phase 40-43 product work: +1.33** = (D2 +2 + D3 +2 + D5 +4) / 6 = +8/6.
  These three are where 65 frontend files / +3461 lines actually landed this
  milestone (viz engine, legend, onboarding/recovery, industrial chrome). Genuine,
  fleet-confirmed.
- **Independent re-score variance: −0.67** = D1 −4 / 6. **FEA code byte-unchanged**
  (`67c2b8e..HEAD` empty diff for all FEA paths) → this is NOT degradation; the fleet
  re-anchored the 90-anchor more strictly (no NAFEMS agreement; Richardson <60%). This
  is the inherent property of the F:-1 no-memory fleet design, documented at Phase 39.
- **D4 / D6 held: 0.** No AI-workflow or repro-infra work this milestone.

Net +1.33 − 0.67 = **+0.66**. The product genuinely advanced +1.33; the −0.67 is
audit variance on unchanged code, disclosed rather than smoothed.

## The GS-001 finding — verified, bounded, flagged (does not move D6)

The functional-tester surfaced `test_golden_samples.py::test_gs001_displacement_uy`
failing (`assert 0.999 <= 0.1`). **Main-session verification (B:-1 / G:-1) established
the true cause:** the parser correctly reads node-11 UY = **-0.49356 m**;
`expected_results.json node_11_UY = -493.56` is the **same value in mm**. It is a
**m-vs-mm unit mismatch in the test assertion**, not a solver/parse defect, and
longstanding (fixtures Apr/May) — **not a Phase 43 regression**. GS-001 was already
honestly downgraded to `insufficient_evidence` (commit `3eaccf3` / FP-001), so this is
a stale assertion on an already-disclaimed sample, not a hidden Tier-claim lie.

- **Does not lift D6** (anti-inflation; it's a defect, not a credit).
- **Does not lower D6 either**: it's a pre-existing condition identically present at
  Phase 39 (D6=78), on an already-disclaimed sample; lowering Phase 43's D6 for a flaw
  that predates it and is unrelated to any Phase 43 work would itself be noise. D6's
  *infrastructure* (the very honesty that downgraded GS-001) is intact and is what earns
  the 78.
- **Flagged for remediation** — fix belongs in the *test* (units-normalize the
  assertion, or xfail/skip in line with the `insufficient_evidence` downgrade). The
  GS-001 fixture is signed-registry (`^GS-\d{3}$` = read-only per ADR-011) and is **not**
  touched. This is a risk-tier change (golden-sample boundary) → out of scope for a
  scoring pass; routed to the retro/follow-up queue.

## Two main-session corrections to fleet findings (G:-1 in action)

The fleet runs without prior context and reports what it observes; main-session
verification corrected two over-attributions before they could distort the score:

1. **"committed `backend/venv` is Python 3.9 → reproducibility hazard"** — FALSE.
   `backend/venv` is gitignored (`.gitignore:30`); `git ls-files` tracked-count = 0. A
   local-env condition, not a committed hazard. Did not penalize D6.
2. **GS-001 "solver" failure framing** — corrected to a test-side units bug (above).

These corrections are the dual-engine guard working as designed: the fleet finds, the
main session verifies against ground truth, neither inflates nor sandbags.

## Why this is NOT a retroactive re-score

- Phase 39's record stays **80.67 / 86·82·76·80·82·78**. Phase 38 = 78.33, Phase 37 =
  77.50. Nothing backfilled.
- The fleet scores D1/D2/D3/D5 fresh each cycle (F:-1 no-memory by design); the
  main-synthesis dims D4/D6 are **held** at their last value unless real work changed
  them — and neither did this milestone.
- Composite = simple arithmetic mean of the 6 dims. No weights, no transforms.

## Anti-gaming compliance (ADR-026, verbatim)

- **B:-1** ✓ D1/D2/D3/D5 scored by the registered fleet; D4/D6 by main synthesis
  (the two dims with no fleet agent). Main session did NOT override any fleet score
  upward.
- **D:-1** ✓ every dimension cites file:line evidence (see per-agent reports).
- **F:-1** ✓ each fleet prompt explicitly forbade `.planning/audits/**`,
  `.planning/retrospectives/**`, and `*BLUEPRINT*`; agents scored fresh.
- **G:-1** ✓ tested what the code IS; the two over-attributions above were caught and
  corrected against ground truth.

## Carry-forward / open findings (→ retro/follow-up queue)

1. **GS-001 test units mismatch** — m-vs-mm in `test_gs001_displacement_uy`; fix
   test-side, leave the read-only fixture. (P2, risk-tier — needs Codex review.)
2. **Two silent-boot recovery gaps** — `/cases` fetch failure + `<NoResultState/>`
   dead CTA (`App.tsx:234-237`, `:1420`). (Dim 2, P2.)
3. **Industrial layout 90-anchor** — drag-resize / density toggle / collapsible rails
   absent (`App.tsx:1226`). The single highest-leverage Dim 3 lift. (P1 for the 99-path.)
4. **No playwright/real-WebGL E2E** + **no PNG/VTU UI export** — the two Dim 5
   90/99 caps.
5. **NAFEMS agreement deferred** — LE10 still `REFERENCE_ONLY`; the Dim 1 95-anchor
   gate.

## Path to 99

All six dims must reach ≥99 for the APPROVE gate. Binding constraints, lowest first:
**D3 = 78** (industrial layout systems) and **D6 = 78** (reproduce-CLI + audit-log;
plus closing GS-001-class test hygiene). D1=82 will recover toward 86+ on the next
NAFEMS-agreement work (code unchanged this cycle). Composite 81.33; the +1.33 of real
Phase 40-43 product work confirms the frontend track is moving. 99-target trend intact.
