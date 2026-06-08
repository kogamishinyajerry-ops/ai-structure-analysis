# FM-04a Phase 43 — functional-tester (Dim 1 FEA + Dim 5 Visualization)

> Registered evaluation fleet (`subagent_type=functional-tester`). Tier 1 / Tier 2
> engineering candidate; not signed validation; not benchmark agreement. 绝对诚实客观.
> Code @ `c3422b4` (working tree: untracked files only, no tracked modifications).
> Anti-gaming: scored by the sub-agent (B:-1), every claim cites file:line (D:-1),
> NOT given any prior audit/retro/blueprint (F:-1), scores what the code IS not what
> it CLAIMS (G:-1). Two findings were **corrected by main-session verification** — see
> the FINAL (`venv` "committed" claim and the GS-001 "solver" framing).

## Dim 1 — FEA simulation capability: **82 / 100**

Anchor 80 fully met; ~2/5 of anchor-90 sub-bullets met. Capped below 90 by
validated-case-vs-cohort Richardson ratio + absent NAFEMS *agreement* evidence.

**80-anchor (fully met):**
- **≥9 validated cases**: 13 `golden_samples/*/cross_check_verdict.yaml` (real cross-checks, not reference-only).
- **≥4 solver kinds**: `solver_kind` ∈ {`linear_static`, `modal`, `buckling`, `dynamic`, `heat_transfer_steady_state`, `contact_pair_static`} = **6 kinds**. Contact (`contact_pair_runner.py:507 run_contact_pair_cross_check`) + heat (`heat_transfer_runner.py:249-315`, `*HEAT TRANSFER, STEADY STATE`) both present → already satisfies the 90-anchor "≥5 kinds (+contact OR heat)".
- **Richardson on ≥30%**: 5 `convergence_study.json` carry `"richardson"` (cantilever-beam, cantilever-beam-modal, plate-simply-supported, plate-ss-shell, plate-with-hole).
- **≥1 asymptotic-bias revelation**: `convergence_study.py:319-325` (plate-ss p=-0.29 non-asymptotic); `cantilever-dynamic-candidate/NOTES.md:113` (numerical-noise peak bias).

**90-anchor partial (the cap):**
- ≥12 cases → met (13). p≤0 guard → met (`convergence_study.py:326 if p <= 0.0:` returns `extrapolated_value=None`, no fabricated f_∞).
- **Richardson ≥60% of refinable cases → NOT met** (only 5 of ~13).
- ≥2 asymptotic-bias revelations → partial (1 strong + 1 weak).
- ≥4 element classes → C3D8/C3D6/B31/S4 (+committed C3D20/T3D3) present, but **no C3D4/C3D10 tet family**.

**95/99 NOT met (honesty gate):** NAFEMS LE10 is `verdict: REFERENCE_ONLY`,
`analytical_only: true`, deliberately excluded from the verdict cohort
(`nafems-le10-thick-plate-candidate/published_reference.yaml`); residual check
"deferred to the Phase 41-43 NAFEMS suite". **Zero committed benchmark *agreement*
evidence** → 95-anchor "≥1 NAFEMS agreement" + 99-anchor "residual ≤2%" unmet.

→ **82** (low-90s ceiling pinned down by Richardson ratio + absent agreement).

## Dim 5 — Visualization & tracking: **86 / 100**

Anchor 80 fully met; ~3/4 of anchor-90 met. Capped below 90 by absence of a real
(non-jsdom) WebGL E2E.

**80-anchor (fully met):** 3D WebGL viewport + per-element coloring
(`ResultMeshWebGLViewport.tsx`, mounted `ResultMeshPlaybackPanel.tsx:655`); companion
compare-cuts (`CompanionViewport.tsx`, gated `:880`); time-series scrubber (`:140`,
`:325-338`); probe persistence (`probeListStorage.ts` + `ProbeListPanel.tsx`);
WebGL+SVG dual-render fallback (`ResultMeshWebGLViewport.tsx:316 webglcontextlost`,
SVG `:677`).

**90-anchor partial:** iso-surface met (`isoSurface.ts extractIsoSurface`, wired
`ResultMeshWebGLViewport.tsx:60,239`, tested); CSV export met
(`ProbeListPanel.tsx:119-124 probe-export-csv`); comparison cuts met (CompanionViewport).
**Real WebGL E2E via playwright → NOT met** (no `frontend/e2e/`, no `*.spec.ts`, no
playwright dep; all viewport tests under jsdom with mocked `getContext`).

**Bonus (not enough for 95):** switchable colormaps (`colormaps.ts:15`, wired into 3
components), ScaleBar legend (`ResultMeshWebGLViewport.tsx:53`), never-fabricated
SolverProgressPanel (`SolverProgressPanel.tsx:17-21`). **95 gaps:** no provenance
overlay stamped onto rendered frames; no measured fps/100k-node perf artifact.

→ **86**.

## Suite status (commands run)

- **vitest** (`cd frontend && npx vitest run`): **1233 passed / 1233, 99 files, 0 failures**.
- **tsc** (`npx tsc --noEmit`): exit 0, no type errors.
- **pytest FEA-core** (14 FEA test files, python3.11): 328 passed, **1 failed**
  (`test_golden_samples.py::TestGS001Cantilever::test_gs001_displacement_uy`).
- Full pytest not runnable in the agent's env (local venv 3.9; `pydantic_settings`
  missing under local 3.11). **NOTE — main-session correction:** `backend/venv` is
  *gitignored* (`.gitignore:30`), NOT committed; this is a local-env condition, not a
  reproducibility hazard. See FINAL.

## Top findings

1. **GS-001 golden test fails** (`test_golden_samples.py:79`). **Main-session
   verified root cause:** a **m-vs-mm unit mismatch** — parser correctly reads
   node-11 UY = **-0.49356 m**; `expected_results.json node_11_UY = -493.56` (same
   value in **mm**). Longstanding fixture inconsistency (Apr/May), **not** a Phase 43
   regression; GS-001 already downgraded to `insufficient_evidence` (commit
   `3eaccf3`/FP-001). Flagged for remediation (test-side, not the read-only fixture).
2. NAFEMS = reference, not agreement (honesty-correct; caps Dim 1 at <90).
3. No frontend PNG/VTU export path (VTU exists backend-only:
   `backend/app/viz/vtu_exporter.py`, wired to CLIs not UI). Caps Dim 5's 99-anchor.
4. No playwright/real-WebGL E2E (jsdom + mocked canvas only). Caps Dim 5's 90-anchor.
