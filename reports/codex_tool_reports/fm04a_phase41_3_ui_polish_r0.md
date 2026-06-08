# FM-04a Phase 41.3 — Codex governance review R0 (UI golden-path polish)

> ADR-026 risk-tier trigger: **cross-≥3-file** frontend change (App.tsx +
> ResultMeshPlaybackPanel.tsx + Topbar.tsx + index.css). Pre-commit review.

## Relay disposition (86gs 502 → CRS fallback)

- **Primary** `codex-review-relay --uncommitted` (86gs gpt-5.4 xhigh) — **FAILED**
  mid-review: `502 Bad Gateway: Upstream service temporarily unavailable`
  (`api.86gamestore.com/responses`, request id `9ca96b79-…`), after 5 reconnect
  attempts. Infrastructure failure, **not** a verdict.
- **Fallback** (per CLAUDE.md relay-degrade rule) `CODEX_HOME=$HOME/.codex-crs
  codex review --uncommitted -c model_reasoning_effort=high` (CRS, effort=high).
  Exit 0. Commit trailer marked `codex_review_relay: crs (effort=high, fallback)`.

## Scope reviewed

UI-only working-tree diff (4 files; verified clean — the GS-001 signed-dir solver
scratch from live testing was restored/removed before review so the diff is
strictly frontend):

| File | Change |
|---|---|
| `frontend/src/index.css` | +48: `@keyframes fm04a-spin` + real `.animate-spin` (Tailwind-inert bug fix), `.run-solver-btn` glow/hover/`[data-solving]` pulse, reduced-motion guards |
| `frontend/src/components/Topbar.tsx` | +8: Run-Solver `className="run-solver-btn"` + `data-solving`; Copilot toggle token tint |
| `frontend/src/components/ResultMeshPlaybackPanel.tsx` | net −53: 3 viewport toggles inline-style→`.vp-toggle`+`aria-pressed`; `eyebrow`/`heading-tight` adoption |
| `frontend/src/App.tsx` | +6: `.rise-in` on CaseBrowser/advisor-row/report; `.shimmer-active` skeleton |

## Verdict

**CLEAN / APPROVE — 0 P1 / 0 P2 / 0 P3.**

> "The reviewed changes are limited to UI styling and documentation updates, and I
> did not identify a discrete regression or correctness issue that is clearly
> introduced by this patch. The untracked files appear to be artifacts/data
> additions rather than code paths affected by the modified frontend components."

No findings. Proceed to commit.

## Verification (independent of Codex)

- vitest **951 pass / 0 fail** (65 files) — exact baseline match
- `tsc -b` **16** (all pre-existing; 0 net new)
- eslint **51** problems (≤ the pre-41.1 baseline of 70; 0 net new from this diff —
  CSS isn't linted; the .tsx edits are className-string additions + style removals)
- App.tsx **1492 / 1500** pin
- preview console: **0 errors** (the `result_mesh.json` 422 is a handled network
  error surfaced via the ErrorCard, not a runtime exception)
