# FM-04a Phase 41.4 — Codex review R0→R1 (FRD path resolution: cwd → repo-root)

> ADR-026 risk-tier: security-sensitive path-resolution helper (path-traversal
> allowlist). Relay: CRS effort=high. Completes the Track A cwd-hardening — the
> result-mesh route was fixed in `cdab713`; this does the FRD/PyVista path too.

## Scope

| File | Change |
|---|---|
| `backend/app/api/routes/_viz_helpers.py` | `_allowed_fs_roots()` anchors the 3 roots to `_repo_root()` not `Path.cwd()`; `_resolve_frd_path()` `db_frd_path=None` fallback anchors `case_dir` to `_repo_root()/golden_samples/<case_id>` not `./golden_samples/...` |
| `tests/test_visualize_plot_get_shim.py` | `TestR2AllowedRootHelper` (×2) re-pinned via `monkeypatch.setattr(_repo_root)` not `chdir`; new `test_resolves_None_path_independent_of_cwd` guard |

## R0 — 1 finding (REAL, fixed)

- **[P2]** the fix was **incomplete**: `_allowed_fs_roots` moved to the repo anchor,
  but `_resolve_frd_path`'s `db_frd_path=None` fallback still built
  `Path("./golden_samples/{case_id}")` (cwd-relative). Launched from `backend/`,
  that candidate would be **rejected as out-of-root** by the now-repo-anchored
  allowlist → a valid FRD reported as missing. Codex reproduced:
  `chdir(repo/'backend')` → `_resolve_frd_path('GS-001', None)` → `None` despite
  `golden_samples/GS-001/gs001_result.frd` existing.
  **FIX:** the `None` fallback `case_dir` is now `_repo_root()/golden_samples/<case_id>`;
  added `test_resolves_None_path_independent_of_cwd` (chdir to a non-repo dir,
  assert GS-001 still resolves).

## R1 — CLEAN / APPROVE (0 findings)

> "The helper change consistently anchors FRD lookup to the repo root and keeps the
> allowlist aligned; the added tests exercise the new cwd-independent fallback
> without showing a discrete regression."

## Verification

- viz sweep **94 passed** (incl. re-pinned allowed-root + new cwd-independence guard).
- path-traversal allowlist semantics unchanged (still confined to golden_samples/
  project_state/ calculix_cases/); only the anchor source moved cwd → repo file.
- The running demo backend launches from repo root, so behavior is identical there;
  this is latent robustness for any other launch cwd.
