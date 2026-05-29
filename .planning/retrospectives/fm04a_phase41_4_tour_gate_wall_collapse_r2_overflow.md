# FM-04a Phase 41.4 — retro queue: 2 P2 past the round cap → **BOTH CLOSED @`8790b91`**

> Source: Codex R2 (CRS effort=high) on the tour/promo boot-gate + evidence-wall
> collapse change. Round cap = 3 reached (R0 + R1 + R2). Both residual findings are
> P2 (no P1 outstanding), so per `~/CLAUDE.md` they defer here rather than forcing an
> R3 iteration. Full arc: `reports/codex_tool_reports/fm04a_phase41_4_tour_gate_wall_collapse_r0_r2.md`.
>
> **UPDATE — both RESOLVED in the retro-P2-closeout commit `8790b91`** (its own
> R0→R2 review arc, de-risked by 2 multi-agent workflows). P2-A → promo gated on the
> painted-result edge `promoAutoShow = tourAutoShow || (casesLoaded && bootResultReady)`;
> P2-B → `hasOpened` lazy-mount latch. See
> `reports/codex_tool_reports/fm04a_phase41_4_retro_p2_closeout_r0_r2.md`. Sections below
> are the original deferral rationale (kept for the decision trail).

## Carried forward (now resolved — see header)

### P2-A — Promo can cover the loading shimmer (timing refinement)
`useBootCaseSelect` returns `promoAutoShow = casesLoaded && !sessionActive && !bootPending`
where `bootPending = preferredAvailable && !activeCaseId`. `selectCase()` sets
`activeCaseId` synchronously *before* the `/report/generate` POST resolves, so for a
returning Basic-mode user (tour dismissed, promo unseen) `promoAutoShow` flips true while
the result/viewport is still loading — the one-time advanced-mode modal can pop over the
shimmer instead of the settled 3D result.

- **Scope reality:** narrow segment (returning Basic users who have never dismissed the
  promo) AND a moving target — R1 said the promo was *permanently unreachable*; the fix
  made it reachable-after-boot; R2 says it's reachable *slightly too early*. The clean
  hero on a TRUE fresh first-visit is unaffected (promo predicate is false until the tour
  is dismissed) and is live-verified.
- **Proper fix (next):** thread a "boot case settled" signal (e.g. `Boolean(report) && !loading`)
  into the hook and gate `promoAutoShow` on it, so the promo waits for the viewport to
  paint. Add a test for the shimmer window.

### P2-B — Collapsed evidence panels still mount + fetch on first paint (perf)
The B.2 collapse wraps VisualTabPanel's 22 panels in a default-closed `<details>`. That
hides them *visually* but does not unmount them, so each panel's mount-time fetch effect
(`CohortDashboardPanel`, `AcceptancePacketPanel`, `CohortSnapshotPanel`, `TrustScoreGauge`,
…) still fires on first paint. The request burst / perf cost of the wall therefore stays
on the boot path on slower backends.

- **Scope reality:** the *visual* first-paint goal (clean 3D hero, wall tucked away) IS
  met and live-verified; this is a request-burst concern, negligible on the warm local
  demo backend but real elsewhere.
- **Proper fix (next):** lazily mount the children on the `<details open>` state
  (`onToggle` → `useState`), rendering the panel stack only once expanded. Requires a test
  sweep first: 39 child-testid refs across ~10 test files — most render the panel
  components directly (unaffected), but any App-integration path that renders
  `<VisualTabPanel>` and queries a child by testid must be cleared (Phase21D only asserts
  the outer `visual-tab-panel` div + Provenance/Advisor null-gating, which stay green).

## Also flagged this session (separate decision, not a Codex finding)
- **OperatorStatusPanel ("VALIDATION & TRUST CENTER")** remains a full governance wall
  below the collapsed VisualTabPanel disclosure. It is the product's flagship
  "Evidence-first" panel (persistent trust center, `sections` already SectionFrame-
  collapsible). Whether to also fold it behind a disclosure is a product-identity call
  surfaced to the user, not auto-applied.
