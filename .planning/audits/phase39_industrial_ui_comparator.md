# FM-04a Phase 39 — industrial-ui-comparator (REGISTERED fleet) · Dim 3

> Authoritative re-score by the REGISTERED `subagent_type=industrial-ui-comparator`
> (sonnet), post-restart. Anti-gaming B/D/F/G:-1 honored. Parity vs Hyperworks /
> Abaqus / ANSYS / Simcenter on the 5 canonical surfaces. Code @ `67c2b8e`.

## Dim 3 — Industrial UI parity: **76 / 100**

### Per-surface parity (0-10)
| Surface | Codebase counterpart | Parity | Key gaps (file:line) |
|---|---|---|---|
| case_tree_panel | `CaseBrowser.tsx` | 3.0 | no drag-resize (`App.tsx:1225` fixed `240px 300px 1fr`); no per-row eye/swatch/rename/reorder/context-menu (`CaseBrowser.tsx:167-181` onClick only); no `role="tree"` |
| viewport_3d | `ResultMeshWebGLViewport.tsx` | 5.0 | orbit/pan/zoom/pick/section-cut/SVG-fallback present (`:380-477,286-300,547-552`); no view-cube/triad, no named views, no box-select, no F=fit, dark-only (`:173`) |
| results_plot | `ConvergenceStudyViewer.tsx` + `TrustScoreTimelineChart.tsx` | 1.7 | no interactive Cartesian plot — read-only tables + 60px static SVG sparkline (`TrustScoreTimelineChart.tsx:22-23`); no hover/zoom/log-scale |
| bc_setup_panel | `BCSetupPillList.tsx` | 1.2 | read-only by design (`:9`); pill list of text, no authoring/dialog/3D-overlay/CRUD |
| mesh_visualization | (no dedicated component — absence) | 1.3 | no MeshViewport; node/elem counts as text string `App.tsx:619`; no quality histogram / free-edge / render-mode toggle |
| **Mean** | | **2.4** | no surface reaches 7/10 → 90-anchor (parity ≥7 on ≥5) unambiguously unmet |

### Anchor table
- **60** ✅ token system `index.css:3-16`
- **70** ✅ motion vocabulary documented — `polishStyles.ts:77-234` (200ms ease-out entrance+exit curves), single theme polished
- **80** 2/3 sub-bullets: ✅ ≥7 motion surfaces (9 confirmed: `polishStyles.ts:99-126,162-193` + `index.css:82-87`); ✅ dark token primitives (`index.css:3-16`, no toggle); ❌ **"any 1 of 3" layout (drag-resize / density toggle / 4-quadrant)** — none cleanly shipped (Basic/Advanced toggle = feature-removal not density; companion = 2-quadrant within one zone, app layout is 3-column fixed)
- **90** ❌ (needs all 4 layout features + parity ≥7/10 on ≥5; mean parity 2.4)

**Score = 70 (all met) + partial credit for 2/3 of 80-anchor = 76.** Unchanged
from Phase 38's 76 — this confirms the prior value (the only dim where the
registered fleet and the prior proxy agree exactly).

agentId aa62f53389ea5e165 (110166 tok, 31 tools).
