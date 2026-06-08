# FM-04a Phase 41.4 — Codex review R0→R2 (retro P2 closeout: lazy-mount + promo shimmer-timing)

> Closes the two retro-queue P2 from the tour-gate/B.2 change. ADR-026 risk-tier:
> cross-≥3-file frontend (App.tsx + useBootCaseSelect.ts + VisualTabPanel.tsx +
> MaterialPickerPanel.tsx + 2 tests). Relay: CRS effort=high (86gs xhigh 502'd the
> whole milestone). Round cap = 3 reached (R0 + R1 + R2). De-risked up-front by two
> parallel multi-agent workflows (scope/design + adversarial P1 verification).

## Scope

| File | Change |
|---|---|
| `frontend/src/components/VisualTabPanel.tsx` | 22 evidence panels lazily mounted behind a `hasOpened` latch (mount on first open, KEPT mounted after — no boot-path fetches, no re-fetch on reopen). Controlled `<details open onToggle>`. |
| `frontend/src/state/useBootCaseSelect.ts` | 7th param `bootResultReady`; `promoAutoShow = tourAutoShow \|\| (casesLoaded && bootResultReady)` — surfaces on the no-case landing (tour-end) OR once a result paints; off boot-pending/shimmer/upload. |
| `frontend/src/App.tsx` | hook call passes `bootResultReady = Boolean(report) && !loading`; `openMaterialPickerPanel` palette command opens the lazy wall (clicks the closed `<summary>` → native toggle → latch) then rAF-scrolls. |
| `frontend/src/components/MaterialPickerPanel.tsx` | scroll-anchor `id="material-picker-panel"` added to the loading-skeleton `<section>` too (was only on loaded content). |
| `frontend/test/Phase41_4_boot_autoshow.test.tsx` | promo policy re-pinned (shimmer-suppressed, reachable post-paint even with sessionActive true, reachable on no-case landing). |
| `frontend/test/Phase41_4_evidence_lazy_mount.test.tsx` | NEW — body absent + zero fetch while collapsed; present after open. |

## Review arc (3 rounds, all REAL, all fixed)

- **R0 — 2×P2:** (1) promo could never become visible — `sessionActive=Boolean(file||report)`
  killed `ready` the instant `report` (which also armed it) became truthy; (2) `{open &&}`
  unmounted all panels on collapse → state loss + re-fetch. **FIX:** decouple promo from
  `ready` (gate on the painted-result edge); `hasOpened` latch keeps the subtree mounted.
- **R1 — 1×P1 + 1×P2:** (P1) gating promo on `bootResultReady` alone made it unreachable on
  the no-case landing where the tour ends (no report there). (P2) lazy-mount removed
  `#material-picker-panel`, breaking the `cmd-material-picker-open` palette jump. **FIX:**
  `promoAutoShow = tourAutoShow || (casesLoaded && bootResultReady)` (a workflow adversarially
  traced this against ALL 6 prior promo findings — re-breaks none); palette command opens the
  wall before scrolling. A parallel workflow swept for OTHER lazy-mount-broken consumers →
  none beyond the material anchor.
- **R2 — 1×P2 + 1×P3:** (P2) the open+single-rAF still raced the materials fetch — the panel's
  skeleton lacked the id, so the jump no-op'd on first invocation. **FIX (live-verified, post-cap,
  no R3):** the scroll-anchor id now renders on the loading skeleton too, so it is present right
  after mount (decoupled from the fetch). (P3) `golden_samples/cylinder-pv-candidate/data/generator.py`
  bad SRC path — **pre-existing UNTRACKED file** (session-start `?? golden_samples/cylinder-pv-candidate/data/`),
  not part of this change, not staged → out of scope (flagged to owner; recurring incidental hit on `--uncommitted`).

## Verification

- `tsc` clean; vitest **966 passed**; App.tsx **1498** (Phase29B pin <1500 green); eslint
  0 introduced (1 pre-existing `withUploadRecovery` on HEAD).
- LIVE (preview): boot → evidence body NOT mounted (`testid count inside visual-tab-panel` = 1
  vs ~177; zero panel fetches on the boot path), 3D hero renders; open → body mounts (183 testids);
  collapse → body STAYS mounted (latch). Palette open-step: fresh collapsed wall → `#material-picker-panel`
  absent → after click+60ms → wall open + anchor present (well before the fetch).
- Promo P1 fix verified by unit test (reachable post-paint EVEN with sessionActive true; reachable on
  the no-case landing) + the workflow's 6-scenario adversarial trace.

## Residual (retro / out-of-scope)

- The promo also arms after a COMPLETED user upload (file+report+!loading) — pre-existing under the
  prior expression too, bounded to once-per-browser by `shouldShowAdvancedPrompt`'s one-shot flag; not
  a regression introduced here.
- `generator.py` SRC path (P3) — owner's call, separate untracked candidate-data file.
