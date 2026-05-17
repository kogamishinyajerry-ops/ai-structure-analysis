# FM-04a Phase 18 — FINAL composite audit (round 1)

**Date:** 2026-05-17
**Scope:** synthesis of UX / FEA / UI testing-agent reports for the
Tier 2 transition arc (Slices A-D).
**Honest reporting commitment:** load-bearing per user directive
2026-05-17 ("绝对诚实客观"). No rubric reshaping; no rounding up.

---

## Composite

| Agent | Score | Verdict |
|---|---|---|
| UX (novice reviewer simulation) | **38/100** | CHANGES_REQUIRED |
| FEA capability (industrial toolstack benchmark) | **32/100** | CHANGES_REQUIRED |
| UI tier (vs ANSYS Workbench / SimScale / Abaqus) | **41/100** | CHANGES_REQUIRED |
| **Composite (mean)** | **37.0/100** | **CHANGES_REQUIRED** |

**APPROVE gate** = composite ≥ 99 AND each agent ≥ 99 AND no axis < 95%.
**Round-1 result:** all three gates failed by large margin.

---

## Where the gap lives (cross-cutting)

The dominant pattern across all three reports is **integration debt**:
Slice A (real CalculiX runner), Slice B (Tier 2 SSOT modules + ADR),
Slice C (materials library + Gmsh runner), Slice D (Cmd-K palette + UI
primitives) all landed as defensible *building blocks* with passing
unit tests (153 backend + 175 frontend = 328 tests green across
Phase 18 A–D), but the building blocks were not wired into the live
reviewer surface (`backend/app/main.py` + `frontend/src/App.tsx`).

Concrete unintegrated artefacts (cited by all three agents):

* `CommandPalette.tsx`, `useKeyboardShortcuts.ts`, `DriftBadge.tsx`,
  `SkeletonCard.tsx`, `ErrorCard.tsx`, `EmptyStateCard.tsx` — every
  Phase 18 D primitive imports cleanly in test files but has **zero
  imports in `frontend/src/App.tsx`**. Verified by independent greps
  in the UX and UI agent reports.
* `backend/app/services/materials/api.py` exists with full validation
  + 3 cited materials, but **no HTTP route** exposes it
  (`backend/app/api/routes/materials.py` was never created).
* `MaterialPickerPanel.tsx` / `MeshControlPanel.tsx` — Slice C
  frontend deliverables that were never created.
* `GmshRunner` exists + passes a real-gmsh end-to-end test, but **no
  consumer code** composes it with the CalculiX runner (no
  geometry → mesh → INP → ccx pipeline route).
* The Slice A `CalculiXRunner` is invoked only from its own test
  file; the live `/solver/run` route uses the pre-Phase-18
  `services/solver.py:35-50` path.

**The honest read:** Phase 18 shipped a **parts bin** (citable SSOTs,
typed APIs, test-pinned components) without shipping the **car**
(integrated reviewer flow that exercises those parts end-to-end). The
Phase 18 B Tier-2 SSOT modules (`_claim_tier.py`,
`_forbidden_tokens.py`, `gate_audit.py`) are the cleanest pieces of
the slice — they don't *require* immediate integration (they're
additive opt-in for future envelope paths) — but the UX and UI
slices were always going to need the integration step to score, and
that step didn't happen in this session.

---

## Where the gap is structural (will not yield to one more iteration)

The FEA agent's 32/100 — and specifically its 0/10 on contact and
0/10 on nonlinear solver — is **not an integration gap**. There is
no contact code anywhere in the repo. There is no nonlinear-solver
code anywhere in the repo. Closing those would require months of
work (writing a contact pair model, wiring a Newton-Raphson loop
with line search, adding tangent-stiffness assembly hooks, picking
material plasticity flow rules, etc. — see the FEA report's
"Phase 19+ scope recommendations" section for the full trajectory).

The UI agent's 3/10 on the 3D viewport — "static SVG `<polygon>`
projection, no WebGL, no orbit, no contour legend, no picking" — is
similarly a structural gap that requires a viewport rewrite, not
integration.

So even a fully-integrated Phase 18 — every primitive wired, every
empty/loading/error state replaced, full materials swap UI working
— would still likely cap somewhere around **composite 55-65** in
round-2 / round-3 agent evals. The 99 target was acknowledged by the
user as conditional from the start of this phase:

> Single-session full Tier 2 transition is unrealistic. ... If the
> testing agents return 70/100, the retro records 70/100; the
> "99-point goal" is NOT met by rewording axes or shrinking the
> rubric.
> — Phase 18 blueprint §0 (honest scope warning, user-acknowledged)

---

## Decision: round 2 iteration scope

Per blueprint Slice E + v2.3 governance round-cap = 3, the system
allows up to 2 more agent rounds before mandatory honest closure.
**Round 2 will target the integration gap only** — not the
structural one — because the integration gap is the one a single
session can move.

### Round 2 work list (scope-bounded; ~150-300 LOC)

1. **Wire CommandPalette + useKeyboardShortcuts into App.tsx**:
   bind `mod+k` to open the palette; register 6-8 commands covering
   the 5 user-task verbs (find case / submit signoff / run solver /
   swap material / view stress / open help cheatsheet).
2. **Add `/api/v1/materials/` route** exposing
   `list_materials() + get_material(id)` JSON shapes, with the same
   tier discriminator pattern used elsewhere.
3. **Add `MaterialPickerPanel.tsx`** rendering the 3 baseline
   materials with name + E + ν + ρ + yield + reference.
4. **Add human display labels to candidate cases**: extend
   `FALLBACK_CANDIDATE_CASES` and the picker dropdown to show a
   human label (`"Cylinder pressure-vessel candidate (Tier 1)"`)
   alongside the raw `case_id`.
5. **Replace ≥3 bespoke loading states with `SkeletonCard`** and
   **≥2 bespoke error states with `ErrorCard`** in the most-visible
   panels (`CohortDashboardPanel`, `AdvisorPanel`, `CandidateCasePicker`).
6. **Wire `EmptyStateCard`** into 1-2 of the highest-traffic blank
   panel paths.

### Out-of-scope for round 2 (deferred to Phase 19+)

* Contact, nonlinear, thermal, modal, buckling solver coverage.
* WebGL 3D viewport rewrite.
* Materials library breadth (3 → ≥50 entries).
* Full App.tsx refactor into a `<500 LOC` WorkbenchShell (high
  regression risk against 175 existing passing tests; deferred).
* Tier-2-validated envelope production (still gated on a real
  cylinder-pv-candidate end-to-end ccx + analytical cross-check).

### Round 2 expected lift (honest projection, no inflation)

| Agent | Round 1 | Round 2 projection | Driver |
|---|---|---|---|
| UX | 38 | 50-58 | T3 + T4 + T5 each rise from 0-5 → 6-10 when palette + materials API + picker land |
| FEA | 32 | 33-35 | Negligible — materials route is +1 dim, otherwise structural gap untouched |
| UI | 41 | 52-60 | Axes 2, 4, 5, 7 each rise 2-3 pts when integrated; axes 1, 8, 10 essentially unchanged |
| **Composite** | **37.0** | **~46-50** | |

**Round 2 will not reach 99.** Round 3 would not either. The retro
will record honest closure at whatever round 2 composite turns out
to be, with the structural Phase 19+ carry-forwards documented.

---

## Per-agent report pointers

* `/Users/Zhuanz/20260408 AI StructureAnalysis/.planning/phase18_audit_reports/UX.md`
* `/Users/Zhuanz/20260408 AI StructureAnalysis/.planning/phase18_audit_reports/FEA.md`
* `/Users/Zhuanz/20260408 AI StructureAnalysis/.planning/phase18_audit_reports/UI.md`

This file (`FINAL.md`) is round-1 synthesis; a round-2 update will
append a "## Round 2 results" section below after the integration
work + agent re-run.
