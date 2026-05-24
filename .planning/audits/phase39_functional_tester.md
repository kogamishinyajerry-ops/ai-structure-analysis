# FM-04a Phase 39 — functional-tester (REGISTERED fleet) · Dim 1 + Dim 5

> Authoritative re-score by the REGISTERED `subagent_type=functional-tester`
> (sonnet), post-restart. Anti-gaming B/D/F/G:-1 honored. Did NOT run real CCX;
> verified codepaths + counts + wiring; ran the suites. Code @ `67c2b8e`.

## Dim 1 — FEA simulation capability: **86 / 100**

### Cohort (13 CCX-backed PASS `cross_check_verdict.yaml`)
cantilever-beam (linear_static, C3D10) · cantilever-beam-modal + -modal-l50 (modal,
C3D10) · cantilever-buckle (buckling, B31) · cantilever-dynamic (dynamic, C3D10) ·
cylinder-pv (linear_static, C3D8) · euler-column (buckling, B31) · heat-transfer-1d
(heat_transfer_steady_state, C3D8) · hertz-contact (contact_pair_static) ·
plate-simply-supported (linear_static, C3D10) · plate-ss-shell (linear_static, S4) ·
plate-with-hole (linear_static, C3D4) · wedge-c3d6 (linear_static, C3D6).
24 `*-candidate/` dirs total; 13 validated; nafems-le10 is `verdict: REFERENCE_ONLY`
(`nafems-le10-thick-plate-candidate/published_reference.yaml:12`) — NOT a benchmark agreement.

- **6 solver kinds** (linear_static / modal / buckling / dynamic / heat_transfer_steady_state / contact_pair_static)
- **6 element classes** (C3D4 / C3D6 / C3D8 / C3D10 / S4 / B31)
- **Richardson 5/13 = 38.5%** (cantilever-beam p=1.483 PASS; cantilever-beam-modal p=0.688 PASS; plate-ss-shell p=2.480 PASS; plate-simply-supported p=−0.293 honest FAIL→extrapolated None; plate-with-hole p=3.871 PASS) — `golden_samples/*/convergence_study.json`
- **2 asymptotic-bias revelations**: S4+Mindlin +1.32% (`test_phase31c_richardson.py:340`); C3D4 −8.37% (`test_phase32a_convergence_ubiquity.py:27-30`)
- **p ≤ 0 guard**: `convergence_study.py` (plate-ss extrapolated_value=None)

### Anchor table
| Anchor | Status |
|---|---|
| 80 | ALL met (≥9 cases; ≥4 solvers; Richardson ≥30%; ≥1 bias) |
| 90 | 5/6 met — ✅ ≥12 cases(13) ✅ ≥5 solvers(6) ✅ ≥4 elem(6) ✅ ≥2 bias ✅ p≤0 guard; ❌ **Richardson ≥60% (have 38.5%)** |
| 95 | NOT met (cases 13<15; Richardson<80%; bias 2<3; NAFEMS REFERENCE_ONLY) |

**Score = 80 + (38.5/60 × 10) ≈ 86.** Only Richardson coverage blocks the 90-anchor.

> ⚠️ This is **−5 vs Phase 38's recorded Dim 1 = 91** (a `general-purpose` proxy
> read that claimed "90 fully met + 1/5 toward 95"). The 90-anchor is NOT fully
> met — Richardson 38.5% < 60%. The registered fleet's 86 is authoritative; the
> 91 was generous proxy drift. FEA code is byte-unchanged → this is a calibration
> correction, NOT a capability regression.

## Dim 5 — Visualization & tracking: **82 / 100**

### 80-anchor — ALL met
- 3D viewport `ResultMeshWebGLViewport.tsx:1` · probe list + persistence `ProbeListPanel.tsx:19` + `probeListStorage.ts:35` (`fm04a.probe-list.v1.` per-case) · section cuts X/Y/Z `ResultMeshWebGLViewport.tsx:75,286-300` · companion viewport `CompanionViewport.tsx:1-37` · time-series scrubber `ResultMeshPlaybackPanel.tsx:894` (range input) + play/pause `:318-319` · WebGL+SVG fallback `ResultMeshWebGLViewport.tsx:113-122,201-222` (`Phase21C_webgl.test.tsx:13`)

### 90-anchor — 1/4 met
| Sub-bullet | Met? | Evidence |
|---|---|---|
| iso-surface rendering | ❌ | no iso-surface code/test in `frontend/src/`; no marchingCubes/IsoSurface |
| CSV export | ✅ | `ProbeListPanel.tsx:119` `probe-export-csv`; `Phase25D_polish_csv_export.test.tsx:33` |
| real WebGL E2E via playwright | ❌ | no `frontend/e2e/`; vitest env `jsdom` (`vitest.config.ts:16`); WebGL mocked |
| **comparison cuts (overlay TWO results)** | ❌ | **`CompanionViewport.tsx:53-61` receives a single `frame` prop — renders the SAME result at a DIFFERENT section-cut, side-by-side. NOT an overlay of two different results.** `CaseComparisonPanel.tsx` compares packets via text/table, not overlaid 3D viewports. |

**Score = 80 + (1/4 × 10) = 82.**

> The companion-viewport overlay distinction is resolved DEFINITIVELY: it is a
> side-by-side compare-CUTS of ONE result, not an overlay of TWO — confirming the
> Phase 38 proxy's over-credit was wrong. Registered fleet lands 82 (not the
> proxy's 84) for the correct reason.

### Suites
Frontend vitest: **939 passed / 64 files / 0 fail**. Backend: 1150 passed; 2 fails
(NLP parser, unrelated) + 4 collection errors (httpx version mismatch in integration
tests, not FEA) — carry-forward.

agentId ab0227bc20a0f3436 (111440 tok, 83 tools).
