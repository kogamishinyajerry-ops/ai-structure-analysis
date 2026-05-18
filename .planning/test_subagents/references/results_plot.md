# Reference: results_plot — ANSYS Mechanical "Solution Information" + Altair Hyperworks HyperView/HyperGraph

## Source
- ANSYS Workbench Mechanical 2022 R2 "Solution Information" worksheet
  (residual / energy / time-step plots) and "Chart" results;
  Altair HyperGraph 2D (paired with HyperView for results plotting).
  Sources: ANSYS Mechanical User Guide ("Solution Information" topic);
  Altair HyperGraph User's Guide; public ANSYS Learning Hub courses;
  Altair University training. General industry knowledge.

## Surface description
- **Layout**: A dedicated plot pane (in Mechanical this is the
  "Solution Information" tab below the 3D viewport; in HyperGraph it
  is its own window) with:
  - Top toolbar: file / page / window / view / curves / axis /
    annotate / export.
  - Left panel: page / window / curve hierarchical tree.
  - Center: 2D plot canvas (Cartesian axes, gridlines, legend).
  - Right panel: curve / axis / annotation property editor.
  - Bottom: data-table view of the current curve (numeric).
- **Information density**: Typical session shows 4-9 windows on a
  single page (residual-vs-iteration / energy / time-step size / max
  contact pressure / etc.), each with full axes + legend + multiple
  curves. ≥40 affordances on screen.
- **Token use**: Light background with saturated curve colors (canonical
  red/green/blue/orange) per curve, or dark "presentation" mode.
  Curve line styles differ (solid / dashed / dot-dash) for
  black-and-white print compatibility. Axes use neutral greys.
- **Interaction affordances**:
  - Click curve → properties panel populates.
  - Pick point on curve → coordinates + interpolated value readout.
  - Drag to pan; wheel to zoom (uniform or per-axis); rubber-band box
    zoom.
  - Right-click on axis → "fit", "log scale", "min/max", "label",
    "tick step".
  - Right-click on curve → "delete", "color", "linestyle", "math
    expression", "FFT", "filter", "shift", "scale".
  - Drag-and-drop curve from data-browser into a window; drop multiple
    onto the same axes to overlay.
  - Synchronized x-axis across stacked windows (Mechanical convergence
    plots auto-sync iteration x-axes).
  - Export: PNG / SVG / CSV / TSV / clipboard / report-template.
  - Math: derived curves via expressions (e.g., `c1 - c2`,
    `integral(c1)`).
  - Annotations: text / arrow / measurement / horizontal & vertical
    cursors that snap to nearest point.
- **Accessibility**: Keyboard navigation across windows (Tab between
  curves; arrow keys move cursor along curve). Tooltip on every
  toolbar icon. Color-blind palette available.
- **Motion**: Pan / zoom are immediate (no tween — this is data
  exploration). Window add / remove fades over ≈150ms.

## Critical-to-success signals
1. **Cartesian axes with min/max + units + gridlines** — not just a
   sparkline. Tick labels, axis titles, legend.
2. **Multiple curves on shared axes** — overlay comparison of residual
   / energy / step-size on one window; runs A vs B comparison.
3. **Hover / click readout of curve point** — exact (x, y) value at
   cursor.
4. **Pan / zoom / fit-to-data** — interactive navigation, not just
   static SVG.
5. **Log-scale axis option** — residual plots are useless on linear.
6. **Export to CSV + image** — engineer's report workflow.
7. **Per-axis tolerance / threshold lines** — Mechanical's
   convergence-criterion line; HyperGraph's reference line. Tells the
   user "you crossed the threshold here."
8. **Derived / math curves** — at least the ability to overlay an
   analytical reference (e.g., `y = analytical_solution(x)`) on a
   numeric result curve.
9. **Multi-window page layout** — engineers compare ≥3 result series
   simultaneously, not one at a time.
