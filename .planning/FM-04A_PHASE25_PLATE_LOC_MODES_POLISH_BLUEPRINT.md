# FM-04a Phase 25 — 5th validated case + App.tsx reducer + Basic/Advanced modes + polish

> **Status:** PLANNED (this commit) · **Base:** Phase 24 R1 closed @ 80.9/100 ·
> Branch `claude/FM-04a-tier1-ballistic-candidate`.
> **Honesty contract carried verbatim:** 绝对诚实客观 — no rubric
> reshaping, no score gaming. If composite lands at 81.5 it gets
> recorded as 81.5, not 99.

## 1. Why this phase exists

Phase 24 closed +1.5 over Phase 23 but **sub-band** (80.9 vs 81-83
projection). Two of the three honest causes from the Phase 24 retro
are structural:

1. **FEA Dim 2 (validated cases) held flat** at 71. The blueprint
   for Phase 24 was honestly a "depth" phase (end-to-end closures);
   only adding a new validated case can move this dim. Phase 25
   makes that explicit.
2. **App.tsx LOC unchanged at 1498**. Phase 22 C reduced it once;
   Phase 23 + 24 didn't touch it. Phase 25 attacks this.
3. **OnboardingTour adds another thing to dismiss for returning
   reviewers**. A Basic-mode toggle gives them a non-modal
   alternative.

Two ancillary items from the Phase 24 punchlist (probe-list CSV
export, Apple-tier visual polish) bundle into one slice.

## 2. Slices (4 deliveries + 1 audit)

| Slice | Theme | Closes which Phase 24 honest gap / punchlist item |
|---|---|---|
| A | 5th validated cross-check case (simply-supported plate) | FEA Dim 2 held-flat at 71 |
| B | App.tsx reducer + topbar-config extraction | Phase 24 App.tsx unchanged 1498 LOC |
| C | Basic / Advanced mode toggle | Phase 24 UX cognitive-load deeper recovery |
| D | Apple-tier visual polish + probe-list CSV export | UI Dim 3 visual polish + UX Dim 1 reviewer flow |
| E | UX + FEA + UI auditor reports → FINAL → retro → STATE | n/a (closeout) |

## 3. Slice A — 5th validated cross-check case (FEA Dim 2 needle)

**Goal:** Flip validated count **4 → 5** by promoting a 5th case.
Pick a CLASSICAL analytical reference that:
1. Uses existing gmsh + C3D10 + ccx infrastructure (no new solver).
2. Has a well-known closed-form analytical result with citation.
3. Is **independent** of the 4 existing physics regimes (cylinder
   hoop / cantilever / plate-with-hole stress concentration /
   Euler buckling).

**Pick: simply-supported rectangular plate under uniform pressure.**
- Geometry: square plate `a × a × t`, ν=0.3 steel.
- Load: uniform pressure `q` on top face.
- BC: simply-supported on all 4 edges (w=0 along edges; rotations
  free).
- Analytical: Timoshenko plate theory closed-form
  `w_center = α · q · a⁴ / (E · t³)` with α=0.00406 for square
  plate, ν=0.3 (Roark's Formulas Table 11.4 case 1a / Timoshenko
  & Woinowsky-Krieger §30 case 1).
- Solver kind: linear static. Element: C3D10 quadratic tet (Phase
  22 A infrastructure).
- Expected residual envelope: 10% (FEA-element-vs-thin-plate-theory
  gap; gross thickness ratio constraint a/t ≥ 20 documented).

**What changes:**

- `backend/app/services/cross_check/plate_simply_supported.py`
  (~120 LOC) — `compute_timoshenko_plate_center_deflection(*, a, t,
  E, nu, q) -> float`, `TIMOSHENKO_ALPHA_SQUARE = 0.00406`,
  `PLATE_SS_CROSS_CHECK_TOLERANCE_PCT = 10.0`, citations baked into
  module docstring.
- `backend/app/services/cross_check/plate_ss_runner.py` (~180 LOC)
  — runs the meshed Tier 2 pipeline (gmsh → C3D10 → ccx);
  composes the .geo with parametric `a`, `t`; emits `*BOUNDARY`
  block clamping z (w) along 4 edges; emits `*DLOAD` for pressure;
  parses ccx output for w_center at the closest mesh node to the
  plate center; verdict YAML written to
  `golden_samples/plate-simply-supported-candidate/`.
- `golden_samples/plate-simply-supported-candidate/` — NEW dir
  (in `*-candidate` carve-out per HF1.7b). Contains
  `data/plate_ss.geo`, `cross_check_verdict.yaml` (PASS verdict),
  `NOTES.md` (Timoshenko α citation).
- `_claim_tier.py` overlay promotes the case on next module load.
- Strict registry pin `test_phase25a_validated_count_is_five`
  trips if any of the 5 verdict files are removed.
- E2E pin `test_phase25a_plate_ss_runner_residual_below_10pct`
  runs real gmsh + real ccx, asserts |residual| < 10%.

**Anti-gaming guard A:-1** — the runner MUST read w_center at the
mesh node nearest the plate center (not just `max(w)` across mesh;
that would game any edge-overshoot artifact). Pinned by a dedicated
test inspecting `_locate_center_node` output for a 1m × 1m plate.

**Projected lift:** FEA Dim 2 (validated cases): 71 → 75 (+4) by
analogy to Phase 23 A which flipped count 3→4 and lifted Dim 2 +7;
the +4 here is more conservative because Phase 23 A was the first
buckling solver kind promotion (Dim 4 +4 too), whereas plate-SS is
the same linear-static solver kind as 3 existing validated cases.
FEA composite delta: +0.8 to +1.0.

## 4. Slice B — App.tsx reducer + topbar-config extraction (UI Dim 1)

**Goal:** Reduce `App.tsx` from 1498 LOC to **<1300 LOC** by
extracting the scenario state machine + Cmd-K palette + topbar
configuration into dedicated modules.

**What changes:**

- `frontend/src/state/scenarioReducer.ts` (NEW, ~180 LOC) — extract
  all `useReducer` / `useState` calls related to scenario / case /
  material / analysis-type into a single reducer with typed
  actions.
- `frontend/src/state/topbarConfig.ts` (NEW, ~120 LOC) — extract
  topbar dropdown option construction, material picker option
  mapping, Cmd-K command registration.
- `App.tsx` shrinks to <1300 LOC. ZERO behavior change. All Phase
  18-24 tests pass without modification.

**Anti-gaming guard B:-1** — `wc -l frontend/src/App.tsx` must
return strictly less than 1300 (post-extraction snapshot pin).
Verified by audit, not by an extracted test.

**Projected lift:** UI Dim 1 (LOC discipline): 93 → 95 (+2). UI
composite delta: +0.4.

## 5. Slice C — Basic / Advanced mode toggle (UX Dim 3)

**Goal:** Give returning reviewers a non-modal way to hide the
control surface complexity. Topbar-mounted Basic | Advanced toggle.
Default: Basic on first load; Advanced once the user has dismissed
the onboarding tour OR explicitly toggled.

**What changes:**

- `frontend/src/uiMode.ts` (NEW, ~90 LOC) — pure-function state
  machine: `UiMode = 'basic' | 'advanced'`, `setMode(mode)`,
  `isAdvancedFeature(featureId)`, `shouldShowFeature(mode, id)`.
  LocalStorage key `fm04a.ui.mode.v1`.
- `frontend/src/components/UiModeToggle.tsx` (NEW, ~80 LOC) —
  segmented control in the topbar.
- Threshold filter / section cut / probe list / per-component
  switcher visibility gated on `shouldShowFeature('advanced', id)`.
  In Basic mode: only legend (Mises only) + node-pick HUD shown.
- 8+ frontend tests: mode toggle, feature gating, persistence,
  C:-1 anti-gaming guard (Basic mode does NOT silently drop the
  current threshold filter — it preserves state, just hides the
  UI; toggling back to Advanced restores the same filter).

**Anti-gaming guard C:-1** — state preservation across mode
toggle. Pin: set a threshold filter in Advanced → toggle to Basic
→ toggle back to Advanced → assert the same filter values are
still active. (Without this guard, "Basic mode" could
silently destroy advanced settings.)

**Projected lift:** UX Dim 3 (cognitive load): 78 → 82 (+4). UX
Dim 5 (novice usability): 82 → 84 (+2). UX composite delta: +1.2.

## 6. Slice D — Apple-tier visual polish + probe-list CSV export

**Goal:** Concrete polish-pass items (not amorphous "polish"):
1. OnboardingTour fade-in (200ms ease-out) + slide-in (12px from
   top).
2. ProbeListPanel row add: fade-in + slide-down (180ms).
3. ProbeListPanel row remove: fade-out + slide-up (140ms).
4. Threshold-filter slider: custom track with gradient matching
   the legend.
5. NEW probe-list CSV export button: downloads
   `probe-list-<timestamp>.csv` with header
   `node_label,x_m,y_m,z_m,field_value` and one row per pinned
   entry.

**What changes:**

- `frontend/src/components/OnboardingTour.tsx` — CSS keyframes for
  fade+slide; `animation` property on the card; respects
  `prefers-reduced-motion`.
- `frontend/src/components/ProbeListPanel.tsx` — same animation
  pattern on row mount/unmount via `key` + CSS class. Add CSV
  export button + `exportProbeListAsCsv` pure-function helper.
- `frontend/src/components/probeList.ts` — `serializeProbeListAsCsv`
  pure-function returning the CSV text string. Header line +
  per-entry row. Empty list → header only (still valid CSV).
- 6+ frontend tests: CSV serialization, header presence, comma
  escaping in field values, prefers-reduced-motion respect.

**Anti-gaming guard D:-1** — `serializeProbeListAsCsv` must
preserve PIN ORDER (carries forward Phase 24 D's D:-2 guard at the
export layer). Pin: serialize a list of 5 in known pin order → CSV
row order must match.

**Projected lift:** UI Dim 3 (visual polish): 80 → 84 (+4) from the
3 motion items + 1 slider track. UX Dim 1 (reviewer flow): 89 → 90
(+1) from CSV export. UI composite delta: +0.8.

## 7. Composite projection (honest band)

| Axis | Phase 24 R1 | Phase 25 projection | Conservative low | Optimistic high |
|---|---|---|---|---|
| UX | 82.6 | 84-85 | 83.5 | 85.5 |
| FEA | 74.8 | 76-77 | 75.8 | 77.0 |
| UI | 85.2 | 86-87 | 86.0 | 87.5 |
| **Composite** | **80.9** | **81.5-83.0** | **81.5** | **82.5** |

**Projection logic:**
- A: +1.0 to FEA composite (5th validated case)
- B: +0.4 to UI composite (App.tsx LOC reduction)
- C: +1.2 to UX composite (cognitive-load deeper recovery via
  Basic mode)
- D: +0.8 to UI composite (motion polish) + +0.2 to UX (CSV
  export)

**If Phase 25 lands below 81.5:** retro records the honest miss
(would be third sub-band landing in a row — pattern signal).
**If Phase 25 lands at 83+:** that would be first inside-band
landing since Phase 22.

## 8. Hard constraints — preserved verbatim from Phase 18-24

- HF1.7a signed-registry hard-stop: no new GS-registry entries
  (the new `plate-simply-supported-candidate` lives in the
  `*-candidate` carve-out, NOT in the signed registry).
- HF1.7b `*-candidate` carve-out: only `plate-simply-supported-
  candidate/` touched + verdict YAML written.
- HF1.8 path-guard self-protection: pre-commit hook stays green.
- tmp_path-only test snapshot writes (except the explicit
  candidate-dir verdict YAML).
- No push (Phase 23 push remained the only push; Phase 24 + 25
  stay local until user authorizes).
- No PR, no Linear/Notion writes.
- Phase 1-24 chain preserved (additive only; the Phase 24 strict
  pin `test_phase23a_validated_count_is_four` will need a loosen
  to subset-of when validated count flips to 5 — pattern matches
  Phase 23 A's loosen of Phase 21 A's pin; preserves Phase 23
  intent as guard against accidentally losing the Phase 23 verdict
  files).

## 9. v2.3 round-cap discipline

Round cap = 3. If Phase 25 round 1 surfaces any Phase 20-style
"real defects unit tests missed" findings, spawn R2 with surgical
fixes. Otherwise no R2.

## 10. Honesty contract restatement

Phase 25 carries the absolute-honesty contract forward:

- Composite is whatever the audit reports it to be — no
  re-aiming the rubric mid-phase
- Honest scope reductions are recorded **in this blueprint**, not
  post-hoc retro explanations
- Anti-gaming guards are predicate-level (A:-1 center-node, B:-1
  LOC measurement, C:-1 state preservation, D:-1 CSV pin order)
- If the composite lands sub-band (third in a row), the FINAL
  records the pattern and the per-phase trend tracking continues

Not signed validation. Not benchmark agreement.

---

End of Phase 25 blueprint.
