# FM-04a Phase 40 — Dim 5 (Visualization) → 90-anchor · PLAN

> Turnkey plan for the next phase, de-risked by the Phase 39 viz data-model
> investigation. Goal: lift Dim 5 from the re-baselined **82** toward **~88-90**
> by closing 90-anchor sub-bullets. Tier 1 / Tier 2 candidate; 绝对诚实客观.
> Code @ `67c2b8e`. Author: main session (Opus), 2026-05-25.

## Goal & acceptance
- **Goal:** close ≥1 Dim 5 90-anchor sub-bullet authoritatively (registered-fleet
  verified), additively, without touching the solver-truth path.
- **Acceptance (per increment):** new logic unit-tested (jsdom OK for pure math);
  new UI additive (existing viewport byte-unchanged where possible); App.tsx < 1500;
  `tsc -b` 0 net new (baseline 16); eslint 0 net new (baseline 69); vitest +N green,
  0 regressions; then a registered `functional-tester` re-score of Dim 5.

## Investigation finding (the design fork that gates iso-surface)
`resultMeshPlayback.ts:18-43`: `ResultMeshFrame` = `nodes[]` (coords/deformed/
displacement, **no nodal scalar**) + `elements[]` (`value` / `stressTensor` =
**per-ELEMENT** scalar). The viewport colors per-element (`ResultMeshWebGLViewport.tsx:303`
`vertexColors: true` fed from element values). **There is no nodal scalar field.**

→ A true iso-surface (where field == threshold) needs a NODAL field. Two paths:
- **(A) Frontend element→node averaging** (chosen default): pure-frontend, NO
  solver-truth change, unit-testable. **HONESTY CAVEAT:** averaging smooths a
  genuinely discontinuous per-element stress field; a naive smoothed iso-surface
  can imply false continuity. **MUST** be labeled a *smoothed viz approximation
  (Tier 0 viz; not the solved per-element field)* on the surface + in copy, and
  the per-element coloring must remain the default truth view. This honesty
  framing is the load-bearing design requirement, not optional polish.
- **(B) Backend emits nodal fields** — more correct, but touches the result-export
  /solver-truth path = **risk-tier Codex review required**. Defer unless (A)'s
  honesty framing proves insufficient.

## 90-anchor sub-bullets — status, cost, risk, sequencing
| Sub-bullet | Status | Cost | Risk | Solver-truth? |
|---|---|---|---|---|
| CSV export | ✅ DONE | — | — | no |
| **iso-surface rendering** | ❌ | ~150-200 LOC pure extraction (marching-tets over volumetric elements via path A) + new component + tests | med (geometry correctness + **FEA-honesty labeling**) | no (path A) |
| comparison cuts (overlay two results) | ❌ | moderate-large: 2nd-result load + mesh-correspondence + difference field | med-high (alignment; rubric strict "overlay" reading) | maybe (alignment) |
| real WebGL E2E via playwright | ❌ | new dev dep + chromium + e2e spec | med infra; **"green in CI" unverifiable on no-push branch** (honest partial only) | no |

**Recommended sequence:**
- **40 A — iso-surface (path A, honesty-framed).** Highest single-sub-bullet ROI,
  frontend-only, no risk-tier. Build: (1) `frontend/src/components/isoSurface.ts`
  pure module — element→node averaging + marching-tets extraction at a threshold,
  fully unit-tested (deterministic geometry, no WebGL); (2) wire an optional
  iso-surface mesh into `ResultMeshWebGLViewport` behind a toggle, default OFF,
  per-element coloring stays the default truth view; (3) honesty label + copy.
  New anti-gaming guard **T:-1 (Phase 40):** iso-surface is a smoothed viz
  approximation, labeled as such, never implying the solved field is continuous;
  existing per-element render byte-unchanged.
- **40 B — comparison overlay** (after 40 A) — design the two-result alignment +
  difference field; reassess whether path B (backend) is needed.
- **40 C — playwright WebGL E2E** — defer until a push/CI path exists (the
  90-anchor "green in CI" cannot be satisfied on the current no-push local branch;
  landing the spec locally earns only honest partial credit).

## Why this is a PLAN, not a session-tail rush
Marching-tets geometry + the FEA-honesty framing of a smoothed iso-surface are
genuinely complex and correctness/honesty-sensitive (per the project contract).
Per the discipline rules (small surgical reversible changes; do not rush complex
tasks), 40 A is started CLEAN next session: pure extraction module + tests first,
then the additive viewport wiring, then the fleet re-score. Phase 39's re-baseline
(80.67) + the durable registry fix are the committed foundation this builds on.

## Other dims' next moves (for roadmap context, not this phase)
- Dim 1 → 90: Richardson 38.5%→≥60% (≈3 more `convergence_study.json`) — **blocked
  on a real CCX runner**; cannot fabricate (honesty). Needs solver infra.
- Dim 2 → 90: role-branching (4 personas) + WCAG AA audit + recovery paths (note:
  results-iframe error state was assessed Phase 38 I as hacky/low-ROI; BC-mismatch
  recovery contradicts the read-only-by-design BC model — both need rethink).
- Dim 6 → 90-95: audit-log + reproduce CLI — touches repro/solver-truth (risk-tier).
