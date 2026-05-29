# FM-04a Phase 41.4 Track A — Codex review R0 (result-mesh cwd-anchor fix)

> ADR-026 risk-tier trigger: **CalculiX/solver-adjacent backend path** + a
> security-sensitive path-resolution helper with traversal guards. Pre-commit.

## Relay disposition

- Primary `codex-review-relay` (86gs gpt-5.4 xhigh) had 502'd on the prior 41.3
  review; used the **CRS fallback** directly: `CODEX_HOME=$HOME/.codex-crs codex
  review --uncommitted -c model_reasoning_effort=high`. Exit 0.
- Commit trailer: `codex_review_relay: crs (effort=high, fallback)`.

## Scope reviewed

| File | Change |
|---|---|
| `backend/app/api/routes/_viz_helpers.py` | add `_repo_root()` (file-anchored `parents[4]`); `_resolve_result_mesh_artifact_path` anchors `project_state_root` to `_repo_root()` instead of `Path.cwd()` |
| `tests/test_result_mesh_viewer_endpoint.py` | 2 tests re-pinned via `monkeypatch.setattr(_repo_root)` instead of `monkeypatch.chdir` (the cwd-dependence they exercised was the bug); traversal + allowlist + case_id-shape assertions unchanged |

## Root cause (proven by live verification)

`_resolve_result_mesh_artifact_path` resolved `Path.cwd()/project_state/...`; the dev
backend ran `uvicorn app.main:app` from `backend/`, so the route 404'd every
`*-candidate` payload despite the mesh being on disk at `<repo>/project_state/...`.
It was the **only** result-mesh route on `Path.cwd()`; its 5 spine siblings already
use file-anchored `_repo_root()`. Live curl: broken `cwd=backend/` → 404; repo-root →
200 (388 KB `GS-102-candidate` mesh); wrong-cwd **with fix** → 200 (cwd-independent).

## Verdict

**CLEAN / APPROVE — 0 findings.**

> "The touched code consistently switches result-mesh artifact lookup from
> `Path.cwd()` to a file-anchored repo root, and the accompanying tests were
> updated to exercise that new behavior. I did not identify a discrete regression
> in the modified paths that would break existing functionality."

## Verification

- `tests/test_result_mesh_viewer_endpoint.py` + `..._signed_registry_refusal.py` +
  `test_visualize_plot_get_shim.py` → **74 passed**.
- Signed `GS-###` still 422 (refusal guard fires before path resolution — untouched).
- Path-traversal + artifact-allowlist + case_id-shape guards intact.
- **Live render PROVEN:** backend restarted from repo root → `GS-102-candidate`
  renders a real WebGL 3D mesh (projectile-plate, von Mises field, 2-frame
  playback, probe pinning) in `result-mesh-webgl-viewport` (860×560 canvas).
- No golden_samples write; no solver-truth / schema / `inp_writer` change.
