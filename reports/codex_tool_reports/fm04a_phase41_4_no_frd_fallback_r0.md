# FM-04a Phase 41.4 — Codex review R0 (no-FRD friendly-HTML fallback)

> ADR-026 risk-tier: visualization route change. Relay: CRS effort=high.

## Scope (the change being committed — 3 files)

| File | Change |
|---|---|
| `backend/app/api/routes/_viz_helpers.py` | add `_fallback_html_no_frd(case_name)` — friendly HTML panel (html.escape'd, no path leaks), mirrors the unavailable/render-failed fallbacks |
| `backend/app/api/routes/visualization.py` | `/visualize/plot` no-FRD path returns `HTMLResponse(_fallback_html_no_frd(...))` instead of `raise HTTPException(404, ...)`; import + `__all__` updated |
| `tests/test_visualize_plot_get_shim.py` | 3 new tests (escapes case name / None handling / no path leak) |

## Why

The demo boots on `GS-102-candidate` (explicit-dynamics, no FRD). The visual grid's
2nd row iframe loaded `/visualize/plot?case_id=GS-102-candidate`, which 404'd with a
raw JSON body (`{"detail":"no FRD result on disk"}`) — the browser then rendered its
JSON viewer right under the hero 3D viewport. The route already returned friendly
HTML for viz-unavailable + render-failed; only this narrow no-FRD path raw-404'd
(the deferred "raw-404 MED" finding). Now it returns a friendly "use the interactive
3D Scene viewport above" panel.

## Verdict

**CLEAN for the reviewed change:** "The visualization-route change looks fine."

- **1 × P2 — OUT OF SCOPE / NOT committed:** Codex (reviewing `--uncommitted`)
  incidentally flagged `golden_samples/cylinder-pv-candidate/data/generator.py:37`
  (hardcoded `SRC` → FileNotFoundError). That file is **pre-existing UNTRACKED**
  (`?? golden_samples/cylinder-pv-candidate/data/` was in the session-start git
  status), unrelated to this change, in the `*-candidate` writable carve-out, and is
  NOT staged in this commit. Noted for the owner; not addressed here (scope).

## Verification

- `tests/test_visualize_plot_get_shim.py` + `test_result_mesh_viewer_endpoint.py` +
  `..._signed_registry_refusal.py` → **77 passed** (74 + 3 new).
- LIVE (backend restarted from repo root): `/visualize/plot?case_id=GS-102-candidate`
  → **200 text/html** friendly panel; the iframe under the hero now shows the green
  case-name message, not the raw JSON viewer.
- signed-registry refusal + path-traversal + XSS-escaping guards intact.
