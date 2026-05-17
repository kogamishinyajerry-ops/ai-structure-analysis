# FM-04a Phase 24 — end-to-end σ-tensor + UX onboarding + LOC reversal + multi-probe

> **Status:** PLANNED (this commit) · **Base:** Phase 23 R1 closed @ 79.4/100 ·
> Branch `claude/FM-04a-tier1-ballistic-candidate`.
> **Honesty contract carried verbatim:** 绝对诚实客观 — no rubric reshaping,
> no score gaming. If the composite lands at 81 it gets recorded as 81, not 99.

## 1. Why this phase exists

Phase 23 closed +2.3 over Phase 22 but **sub-band** (79.4 vs 81-85
projection). The honest reasons recorded in the Phase 23 FINAL +
retro were:

1. **σ-tensor end-to-end flow not yet closed** — Phase 23 B shipped
   the frontend switcher + `stressDerivatives.ts` math, but no
   backend emitter writes `stressTensor` into `result_mesh.json`.
   UI looks complete; data flow isn't yet.
2. **UX cognitive-load -1 regression** — three new control surfaces
   (component switcher, threshold filter, node-pick HUD) shipped at
   once without onboarding to absorb the new complexity.
3. **UI LOC discipline -2 regression** — `ResultMeshWebGLViewport.tsx`
   grew from ~675 LOC (end of Phase 22) → ~820 (end of Phase 23) →
   930 (start of Phase 24, including post-Phase-23 verified
   measurement). Phase 23 retro filed this as a viewport-split task.
4. **Phase 23 C single-pick is the minimum** — reviewers actually
   want to compare nodes (pick A vs pick B vs pick C, see field
   value side-by-side).

Phase 24 attacks exactly these four. None are speculative new
features; each is a **named honest gap** from Phase 23.

## 2. Slices (4 deliveries + 1 audit)

| Slice | Theme | Closes which Phase 23 honest gap |
|---|---|---|
| A | σ-tensor backend exporter | Phase 23 B frontend-only gap (FEA Dim 5) |
| B | Onboarding tour / progressive disclosure | UX cognitive-load -1 |
| C | Viewport file split (raycaster + animation + geometry modules) | UI LOC discipline -2 |
| D | Multi-node pick / probe list (compare panel) | Phase 23 C single-pick minimum |
| E | UX + FEA + UI auditor sub-agents → FINAL → retro → STATE refresh | n/a (closeout) |

## 3. Slice A — σ-tensor backend exporter (FEA Dim 5)

**Goal:** Close the end-to-end σ-tensor flow. After Phase 24 A, an
OpenRadioss frame with 6-column stress (σ_xx, σ_yy, σ_zz, σ_xy,
σ_yz, σ_xz) emits a `stressTensor: { sxx, syy, szz, sxy, syz, sxz }`
field on each result-mesh element, the frontend reader parses it
(already wired in Phase 23 B), and the component switcher's
`computeVonMises` / `computePrincipalStresses` operate on real
solver-emitted tensor data — not synthetic.

**What changes:**

- `backend/app/viz/openradioss_dynamic_result_exporter.py`:
  `_build_json_frame` gains a per-element `stressTensor` emission
  when `frame.stress.shape[1] >= 6`. Behind a deterministic guard:
  when stress is None or has fewer than 6 columns, no `stressTensor`
  field is emitted (frontend already handles the missing case from
  Phase 23 B).
- `RESULT_SCHEMA_VERSION` stays at 1 (additive optional field, no
  break). Documented schema delta in `payload.fieldRanges` (no
  schema bump because field is optional).
- New backend tests pinning: (i) tensor emitted when 6-col stress
  present; (ii) tensor absent when stress is None; (iii) tensor
  absent when stress has < 6 cols; (iv) emitted `sxx/syy/szz/sxy/
  syz/sxz` exactly match input stress columns (no reordering, no
  scaling, no unit fold); (v) per-frame regression on a 2-element
  synthetic frame.
- E2E pin (no new requires_solver path — uses an in-memory
  synthetic `DynamicFrameData` with hand-rolled stress arrays so
  the test runs in <1s).

**Honest scope reduction:** Phase 24 A is OpenRadioss-only. The
CalculiX static path (`ResultMeshWebGLViewport` Phase 18-21 cohort)
doesn't have its own `result_mesh.json` writer in this repo — the
4 validated cross-check cases are validated against analytical
references, not against frontend viewer output. CalculiX→viewer
σ-tensor is **deferred to a future phase** if a static viewer
exporter is built.

**Anti-gaming guard:** A:-2 — test that confirms when input
`frame.stress` is None, the emitted element has **NO** `stressTensor`
field (not `stressTensor: null`, not `stressTensor: {}`).

**Projected lift:** FEA Dim 5 (Cross-check rigor): 83 → 88 (+5).
FEA composite delta: +1.0. End-to-end closure is the load-bearing
"honest" claim.

## 4. Slice B — Onboarding tour

**Goal:** Recover the UX cognitive-load -1 regression by introducing
a first-load progressive-disclosure overlay. Show the user the 4
new control surfaces from Phase 18-23 in order, each as a stepped
overlay with a clear "Got it" advance + "Skip tour" escape.

**What changes:**

- New `frontend/src/onboardingTour.ts` (~120 LOC) — pure-function
  state machine: `OnboardingState`, `nextStep`, `dismissTour`,
  `shouldShowTour`. LocalStorage key `fm04a.onboarding.v1.dismissed`
  controls one-time gating.
- 4 tour steps: (1) Field component switcher (legend dropdown);
  (2) Threshold filter (min/max sliders); (3) Node-pick (click any
  node → HUD probe overlay); (4) Section cut (depth slider).
- New `frontend/src/components/OnboardingTour.tsx` (~140 LOC) —
  React component that reads onboarding state, renders the overlay
  with progress dots (1/4 · 2/4 · 3/4 · 4/4), positions tooltip
  near the relevant control surface.
- App.tsx wires `<OnboardingTour />` into the result-mesh panel
  context. ≤ +20 LOC to App.tsx.
- 10+ frontend tests: tour step progression, dismissal persistence,
  reset path, anti-gaming guard (B:-1 = tour does NOT auto-advance
  on its own — only on explicit user click).

**Anti-gaming guard:** B:-1 — assert that calling `nextStep` from
the test fires only when user explicitly invokes it, not via a
timer.

**Projected lift:** UX cognitive-load axis: -1 → +1 (+2 from baseline
+ regression recovery). UX composite delta: +1.5 to +2.0.

## 5. Slice C — Viewport file split

**Goal:** Reverse the LOC discipline regression. Split
`ResultMeshWebGLViewport.tsx` (~930 LOC) into 3 modules:

- `viewportRaycaster.ts` (~150 LOC) — pure-function raycaster
  helpers + node-pick state (extracted from Phase 23 C work).
- `viewportAnimation.ts` (~120 LOC) — animation loop + interpolation
  (extracted from Phase 22 B work).
- `viewportGeometry.ts` (~180 LOC) — Three.js mesh construction +
  material setup (existing geometry build code).
- `ResultMeshWebGLViewport.tsx` shrinks to ~500 LOC — orchestrator
  only, imports from the 3 extracted modules.

**Constraint:** ZERO behavior change. Pure module extraction. All
46 frontend tests from Phase 18-23 must continue to pass without
modification (or with only trivial import-path updates).

**Anti-gaming guard:** C:-3 — diff comparison test: extract the
viewport file's exported API surface before + after; assert all
public exports remain identical.

**Projected lift:** UI LOC discipline: -2 → 0 (+2). UI composite
delta: +1.0 to +1.5.

## 6. Slice D — Multi-node pick / probe list

**Goal:** Extend Phase 23 C single-node pick to multi-pick. User
can pick up to 8 nodes via cmd/shift+click (or click a "+Pin"
button on the HUD). Each pinned node gets an entry in a probe-list
panel showing label + xyz + field value + a remove button. The
panel pins to the right side of the viewport.

**What changes:**

- `viewportRaycaster.ts` (post-Slice-C) gains
  `addPickedNode(state, node)`, `removePickedNode(state, label)`,
  `clearAllPicks(state)`. Max 8 entries (FIFO eviction if pinning
  9th).
- New `frontend/src/components/ProbeListPanel.tsx` (~110 LOC) —
  renders the pinned-node table.
- `ResultMeshWebGLViewport` orchestrator forwards multi-pick state
  to `<ProbeListPanel />`. Existing single-pick HUD behavior
  preserved as the "active pick" — pinning is a separate explicit
  action.
- 8+ frontend tests: pin/unpin, FIFO at 8, clear-all, anti-gaming
  guard.

**Anti-gaming guard:** D:-2 — pin 5 nodes with labels [7, 42, 99,
11, 3]; assert the probe list renders them in PIN-ORDER (not
sorted by label and not by array index).

**Projected lift:** UX reviewer-flow axis: +1. UI industrial-CAE
comparison: +1 (multi-probe is a standard CAE feature). UX
composite delta: +0.5 to +1.0. UI composite delta: +0.5.

## 7. Composite projection (honest band)

| Axis | Phase 23 R1 | Phase 24 projection | Conservative low | Optimistic high |
|---|---|---|---|---|
| UX | 80.8 | 82-84 | 82.0 | 84.5 |
| FEA | 74.0 | 75-77 | 75.0 | 77.0 |
| UI | 83.4 | 84-86 | 84.0 | 86.5 |
| **Composite** | **79.4** | **81-83** | **81.0** | **83.5** |

**Projection logic:**
- A: +1.0 to FEA composite (cross-check rigor end-to-end closure)
- B: +1.5 to +2.0 to UX (cognitive-load recovery + onboarding =
  industrial-tool affordance)
- C: +1.0 to +1.5 to UI (LOC discipline reversal, no other lift)
- D: +0.5 UX + +0.5 UI (multi-probe reviewer affordance)

**If Phase 24 lands below 81:** retro records the honest miss and
identifies the cause (no rubric reshape). **If Phase 24 lands at
83+:** that's first inside-band landing since Phase 22.

## 8. Hard constraints — preserved verbatim from Phase 23

- HF1.7a signed-registry hard-stop: no new GS-registry entries
- HF1.7b `*-candidate` carve-out: only candidate dirs touched
- HF1.8 path-guard self-protection: pre-commit hook stays green
- tmp_path-only test snapshot writes
- No push (Phase 23 already pushed; Phase 24 commits stay local
  until user authorizes)
- No PR, no Linear/Notion writes
- Phase 1-23 chain preserved (additive only — no test rewrites
  that change Phase N intent; only loosen-to-subset where Phase
  N+1 promotes additional cases)

## 9. v2.3 round-cap discipline

Round cap = 3. If Phase 24 round 1 surfaces any of the Phase 20-
style "real defects unit tests missed" findings, spawn Round 2
with surgical fixes. Otherwise no R2.

## 10. Honesty contract restatement

Phase 24 carries the absolute-honesty contract forward:

- Composite is whatever the audit reports it to be — no
  re-aiming the rubric mid-phase
- Honest scope reductions are recorded **in this blueprint**, not
  as post-hoc retro explanations
- Anti-gaming guards are predicate-level, not vibe-level
- If a slice fails its projection, the FINAL records the honest
  cause and the next-phase punchlist files it

Not signed validation. Not benchmark agreement.

---

End of Phase 24 blueprint.
