# FM-04a Phase 38 — FINAL composite (rubric v2.0)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观. Composite = simple arithmetic mean of 6 dims, no
> weights, no transforms. Phase 37 baseline = 77.50. Head `2e7d49c`.

## Composite: **78.33 / 100** (Phase 37 → Phase 38: **+0.83**)

```
composite = (91 + 77 + 76 + 76 + 72 + 78) / 6 = 470 / 6 = 78.33
              D1   D2   D3   D4   D5   D6
```

| Dim | Phase 37 | Phase 38 | Δ | Source | Basis |
|---|---|---|---|---|---|
| 1 FEA capability | 87 | **91** | **+4** | functional-tester (fleet) | FRESH — real Phase 38 B work |
| 2 Novice UX | 77 | **77** | 0 | novice-simulator (fleet) | FRESH — net-neutral |
| 3 Industrial UI | 76 | **76** | 0 | industrial-ui-comparator (fleet) | FRESH — anchor unmoved |
| 4 AI workflow | 76 | **76** | 0 | main synthesis | HELD — advisor code byte-unchanged |
| 5 Visualization | 72 | **72** | 0 | main synthesis | HELD — viz code byte-unchanged |
| 6 Trust & repro | 77 | **78** | +1 | main synthesis | FRESH — real Phase 38 F/H work |

**APPROVE gate (99+ = all 6 dims ≥ 99) FAILED by 20.67 composite points** — recorded
honestly. 99-target reachable Phase ~45-46 per the standing roadmap.

## Honest delta attribution (the +0.83, decomposed)
- **Dim 1 +4 (REAL Phase 38 capability):** the C3D6 wedge 6th element class
  (`38 B`, real ccx σ_zz=−210 MPa 0.00% residual) lifts the cohort to 13 PASS / 6
  solver kinds / **6 element classes** — the 95-anchor "≥6 element classes" sub-bullet
  is now met. functional-tester placed it at anchor 90 fully + ~1/5 toward 95 (95
  still blocked: cohort 13<15; NAFEMS LE10 is `REFERENCE_ONLY`, not a solved-residual
  agreement).
- **Dim 6 +1 (REAL Phase 38 trust work):** `38 F` tier-2 API-boundary visibility +
  `38 H` drift-guard test + provenance script. Modest against the wide 90/95/99 gates.
- **Dim 2/3/4/5 = 0:** Phase 38 made no anchor-moving change to novice UX or industrial
  UI (the WCAG fixes don't move the feature-checklist anchors), and made **no code
  change at all** to the advisor wiring (Dim 4) or the viz layer (Dim 5).

The Phase-38-attributable lift is **+0.83, entirely from Dim 1 (FEA) + Dim 6 (trust)** —
the two things the phase actually built. No dimension was inflated to manufacture a
larger headline.

## R6 methodology — calibrated, with an honest limitation

The 3-agent eval fleet (`functional-tester` / `novice-simulator` /
`industrial-ui-comparator`) is **NOT registered as `subagent_type`** this session:
the agents live in the project's `.claude/agents/` but Claude Code was launched from
`/Users/Zhuanz` (home), so project-level agents aren't discovered — **and their
protocol paths are relative (`.planning/...`), so even a `~/.claude/agents/` copy
would not resolve them from a non-project cwd.** The durable fix is to launch the
next session from the project directory (`cd "/Users/Zhuanz/20260408 AI
StructureAnalysis" && claude`); then `subagent_type=functional-tester` works natively.

R6 therefore ran via **`general-purpose` proxies briefed with absolute paths to the
canonical protocol + RUBRIC_v2.md**, instructed to score against the rubric's
anchor structure (NOT the harsh absolute "from-zero vs commercial CAE" formula that
crashed the prior R6 to Dim 3 = 45 / Dim 2 = 58). This **fixed the harsh-drift**:
Dim 1 (91), Dim 2 (77), Dim 3 (76) all came back calibrated and consistent with the
actual Phase 38 changes.

**But a fresh-absolute proxy can drift in the GENEROUS direction too** — and Dim 5
exposed exactly that:

- The proxy scored Dim 5 = 84, a **+12 jump over Phase 37's 72 on byte-identical viz
  code** (`git diff f56f6ce..HEAD` shows zero changes to `ResultMeshWebGLViewport`,
  `CompanionViewport`, `ProbeListPanel`, etc.).
- It also **over-credited a 90-anchor sub-bullet**: it read `CompanionViewport` as
  "comparison cuts (overlay two results)", but `CompanionViewport.tsx:1-6,54-56`
  shows it renders a SECOND viewport **side-by-side**, sharing the **same frame**
  with an independent section-cut — i.e. compare-CUTS of one result, not an OVERLAY
  of two results. Corrected, only 1/4 of the Dim 5 90-anchor sub-bullets is met (CSV
  export; iso-surface + playwright E2E + comparison-overlay all absent — confirmed:
  no `frontend/e2e/`, no iso-surface code).

**Decision (per the no-retroactive-rescore guard + the prior R6 anti-drift caveat):**
for the dims where Phase 38 changed **no code** (Dim 4 advisor wiring, Dim 5 viz),
the composite **HOLDS the Phase 37 calibrated values** rather than adopting a
proxy re-read that would inject an unverifiable jump and implicitly signal that
prior phases under-scored. Holding is the conservative, anti-inflation, continuity
choice. The higher proxy reads are logged below as a **Phase 39 deliberate
re-baseline candidate**, to be resolved by the REGISTERED calibrated agent (not a
proxy) — applied prospectively, never retroactively.

> This is the symmetric application of the caveat that warned against *crashing* the
> composite on an uncalibrated harsh proxy: we equally refuse to *inflate* it on an
> uncalibrated generous proxy. Calibration uncertainty on byte-unchanged code →
> hold the last calibrated value.

### Phase 39 re-baseline candidates (proxy-flagged, NOT applied)
- **Dim 5**: proxy read 82–84 (corrected ~82) vs held 72. If the registered agent
  confirms anchor 80 is fully met (companion + time-series scrubber + probe
  persistence + WebGL/SVG fallback — all present by file:line), Dim 5's true floor
  is ≥80 and 72 was a stale carry-forward. Resolve via the registered fleet.
- **Dim 4**: held 76; anchor-80 sub-bullets (3 advisor stages + 4-Q gate at each) are
  present by file:line, but Phase 37's deliberate 73→76 interpolation stands for
  unchanged code. Re-confirm via the registered fleet.

## Fleet reports (full evidence base)
- `.planning/audits/phase38d_functional_tester.md` — Dim 1 + Dim 5
- `.planning/audits/phase38d_novice_simulator.md` — Dim 2
- `.planning/audits/phase38d_industrial_ui_comparator.md` — Dim 3
- `.planning/audits/phase38d_dim4_ai_workflow.md` — Dim 4 (main synthesis)
- `.planning/audits/phase38d_dim6_trust_reproducibility.md` — Dim 6 (main synthesis)

## Carry-forward findings (valid regardless of calibration)
1. **GS-001 legacy test failing in the default sweep** (functional-tester, MED-HIGH):
   `backend/tests/test_golden_samples.py:79` expects `−493.56` (mm) but the FRD reader
   yields `−0.493560` (m) — a unit mismatch in the pre-Phase-20 legacy fixture, with
   **no `@pytest.mark.legacy` marker**, so it runs (and fails) in the default CI sweep.
   Does not affect the production `*-candidate/` SI path. → debt-cleanup phase.
2. **38 D BC dead-end** (novice-simulator, HIGH): `BCSetupAdvisorCard` /
   `BCSetupPillList` show "expected BCs" with **no affordance to set them** and no BC
   editor exists (`SensitivityForm` uses raw `*CLOAD` syntax behind an "Exploration"
   tab). A novice told to "set the BCs before running" has nowhere to go. → Phase 39.
3. **WebSocket-death mid-solve has no ErrorCard** (novice, HIGH): `App.tsx:460-464`
   appends `[ERROR]` to the console only; no recovery surface (contrast: solver-start
   failures get an ErrorCard + Retry). → Phase 39.
4. **Developer "Phase X" labels leak to end users** (novice, MED): `OnboardingTour.tsx`
   eyebrow + `AdvancedModePromo.tsx:132`. → debt/UX-polish.
5. **`tsc -b` 16 + eslint 50 pre-existing red** (standing debt): the real gate is
   `npx tsc -b` (NOT `tsc --noEmit`, which no-ops on the project-reference root).
   → dedicated debt-cleanup phase, CI wired to the real gate.

## Hard-constraint compliance
- Composite = simple arithmetic mean of 6 dims (no weights/transforms). ✓
- No retroactive re-score of any prior phase (Phase 37 record stays 77.50 / 87·77·76·76·72·77). ✓
- No fabrication; the one main-session adjustment (Dim 5 proxy 84→corrected ~82) was a
  **downward** correction of a cited factual over-credit, and Dim 5 was then HELD at 72
  anyway (byte-unchanged code). ✓
- Tier 0/1 evidence not implying Tier 2 (NAFEMS LE10 kept `REFERENCE_ONLY` / Tier 1). ✓
- Phase 1-N chain additive only; no test-threshold edits; App.tsx < 1500. ✓
- 23rd consecutive Tier-2 phase. Nothing pushed (local-commit only).
