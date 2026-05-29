# FM-04a Phase 41.4 — make the demo's 3D centerpiece render + lead (corrected plan)

> Tier 0 demo direction (user 2026-05-29). Built from a workflow (4 read-only
> probes → synthesis → adversarial critique) **then corrected by live empirical
> verification**, which overturned the synthesis's load-bearing premise. 绝对诚实客观.

## Root cause — CORRECTED by live verification (not what the research assumed)

The research synthesis claimed Track A was "route the WebGL panel to `GS-102-candidate`,
whose `result_mesh.json` the route already serves **200**." **Live curl proved that false:**
the running backend 404'd `GS-102-candidate` too. The agents read the file *on disk* but
never hit the *live route*.

**Actual root cause (proven):** the result-mesh route resolves its payload via
`Path.cwd()/project_state/...` (`_viz_helpers.py:_resolve_result_mesh_artifact_path`),
but the dev backend (PID 41022) was launched as `uvicorn app.main:app` **from `backend/`**,
so `Path.cwd()` = `<repo>/backend`, and `<repo>/backend/project_state` does not exist →
**404 even though the 388 KB mesh is on disk** at `<repo>/project_state/visualizations/
GS-102-candidate/result_mesh.json`.

Evidence (live, this session):
- broken backend (cwd `backend/`, port 8000): `GS-102-candidate` → **404** "result_mesh.json not found".
- throwaway backend from **repo root** (port 8002): `GS-102-candidate` → **200** (388,717 B); `GS-003` → 422; `plate-with-hole-candidate` → 404.
- throwaway from **wrong cwd `backend/`** WITH the fix (port 8003): `GS-102-candidate` → **200**. ✅ fix is cwd-independent.

`_resolve_result_mesh_artifact_path` is the **only** result-mesh route on `Path.cwd()`; its
5 siblings (`acceptance_packet` / `trust_score` / `reviewer_bundle` / `case_completeness` /
`tier1_report`) all use file-anchored `_repo_root()` = `Path(__file__).resolve().parents[4]`.

## Track A — make ≥1 demo case render (DONE, pending Codex + commit)

**The fix = 1 function, matching the sibling pattern.** `_viz_helpers.py`: added `_repo_root()`
(file-anchored) + `_resolve_result_mesh_artifact_path` now anchors `project_state_root` to
`_repo_root()` instead of `Path.cwd()`. Robust to launch cwd; **no remap, no honesty wrinkle**
(candidates render under their own id — the research's mis-attribution risk is moot).

- Test adaptation (intent-preserving, not threshold-gaming): `tests/test_result_mesh_viewer_endpoint.py`
  pinned `_repo_root` via `monkeypatch.setattr` instead of `monkeypatch.chdir` — the cwd-dependence
  it exercised *was the bug*. Traversal + artifact-allowlist + case_id-shape assertions unchanged.
- Verification: **74 passed** (result-mesh endpoint + signed-registry refusal meta-guard + plot shim).
- Signed `GS-###` still 422 (refusal guard fires before path resolution — correct, untouched).
- Risk-tier: security-sensitive path-resolution helper → **Codex review before commit** (CRS, in flight).

### Still-open operational fact (NOT code)
The running 8000 backend has no `--reload`, so it must **restart to serve the fix**. Two clean ways,
both correct after this code fix: relaunch from anywhere (the code is now cwd-independent). For the
live preview to render, the 8000 instance needs a restart — **user's running process → ask first.**

### Remaining unknown (the only one left)
WebGL *render* path (canvas actually draws the 200 mesh) is unverified live — the preview proxies to
the still-broken 8000. Data path is proven (200, 388 KB). The panel auto-falls-back to an SVG 2D
projection if `detectWebGLSupport()` is false (`ResultMeshPlaybackPanel.tsx:230-233`). Resolve by
restarting 8000 then re-screenshotting `GS-102-candidate`.

## Track B — recompose the visual tab 3D-first (frontend, after Track A renders)

Confirmed by code (this session): `App.tsx:1345` `<VisualTabPanel>` (19 governance panels) renders
BEFORE the viewport-hero block at `App.tsx:1365-1457`, so the 3D viewport is always below the wall.

- **B.1 (App.tsx):** hoist the visual-branch viewport grid above `<VisualTabPanel>`. **Caveat
  (critique-confirmed):** the `1365-1457` block is SHARED with the narrative tab via the
  `activeTab==='visual' ? grid : NarrativeTabPanel` ternary at `:1392` — a naive cut-paste moves the
  narrative body too. Render the visual grid above `<VisualTabPanel>` **only within the visual branch**.
- **B.2 (VisualTabPanel.tsx, 208 LOC, NO pin):** wrap the 19 children in a collapsible "Evidence &
  Trust" surface (sub-tab or default-collapsed `<details>`). **Preserve the only 2 pins:** keep
  `data-testid="visual-tab-panel"` (`:122`, pinned `Phase21D_polish.test.tsx:139`) + the
  Provenance/Advisor null-gating (`:176-190`, pinned `:147-148`).
- **B.3 ErrorCard 422 copy** (`ResultMeshPlaybackPanel.tsx:480-482` — the *displayed remediation*
  array; NOT `:278-283`, the thrown message — critique fix): for a signed `GS-###` the current
  "Run the solver" copy is misleading; change to "This is a sealed signed-registry case — switch to
  a candidate case to view the 3D result."

### Hard constraints (critique-verified)
- **App.tsx <1500 is CI-enforced strict** (`Phase29B_section_frame_collapse.test.tsx:534`,
  `toBeLessThan(1500)`; file 1492 → ~7 lines headroom). Do logic in unpinned `VisualTabPanel.tsx`/a
  helper; keep App.tsx **net flat-or-negative**; **split A and B into separate commits**; run Phase29B
  between. B.1 is NOT a free reorder (shared-block extraction is net-positive LOC) → budget it.
- **No visual-tab DOM-order test exists** (no test does `render(<App>)`); only `Phase21D` imports
  `VisualTabPanel`. Net: **0 of ~951 tests break** if the 2 pins are kept. Test-discipline-clean.
- Honesty: `GS-102-candidate` self-labels **Tier 1 engineering candidate / "not signed validation"**
  (`result_mesh.json:10-12`, rendered at `ResultMeshPlaybackPanel.tsx:466`) — leading with it is
  honest (real OpenRadioss projectile-plate geometry; no fabricated physics). Note: this is Tier-1
  wording, stricter than the brief's "Tier-0 demo" — reconcile in copy, do not imply validation.

## Sequencing
A (backend cwd fix) → commit → **restart 8000 + verify WebGL renders live** → B.3 copy → B.1 hoist →
B.2 wall-demote → B.4 additive `VisualTabPanel` test. A is load-bearing; B alone only relocates an
error block.

## Genuine decisions for the user
1. **Restart the running 8000 backend** so the live demo serves the fix? (your process — won't kill unilaterally)
2. **Signed `GS-###` selection** once candidates render: honest "switch to candidate" ErrorCard (simplest), the PyVista `/plot` iframe of the real case (more work, conditional 200), or both?
3. **Default boot case** = a renderable candidate (e.g. `GS-102-candidate`) so the 3D shows on load? (`activeCaseId` boots `null` today).
4. **Evidence/Trust wall demotion** = sub-tab (hidden until clicked) vs below-the-fold `<details>`?
