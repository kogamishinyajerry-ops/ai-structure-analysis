# Reference: mesh_visualization — Altair HyperMesh "Mesh" panels + Abaqus/CAE Mesh Module

## Source
- Altair HyperMesh 2022.x (Mesh ribbon: 2D Auto / 3D Tetra / Hex /
  Quality / Edit Element); Abaqus/CAE Mesh Module (Seed / Mesh /
  Verify / Assign Element Type / Assign Mesh Controls).
  Sources: HyperMesh User Guide ("Mesh", "Quality", "Edit Element"
  topics); Abaqus/CAE User's Guide (Chapter 17 "The Mesh Module");
  Altair University training; public CAE Associates / LearnCAx
  videos. General industry knowledge.

## Surface description
- **Layout**: 3D viewport center stage with mesh rendered as wireframe
  / shaded / shaded-with-edges. Right-side or floating-panel mesh-
  controls (seed density, element type, growth ratio, quality
  thresholds). Left-side or bottom mesh-statistics readout (node
  count, element count, per-element-class counts, quality histogram).
- **Information density**: ≥20-30 affordances at once — element count,
  node count, per-element-class counts, mesh quality summary (min /
  max / mean jacobian / warpage / aspect / skew / tet collapse),
  seed-density slider, element-type chooser, growth-ratio entry,
  smoothing toggles, quality-criterion sliders, render-mode (wireframe
  / shaded / shaded-with-edges / quality-color-coded).
- **Token use**: Mesh edges are a contrast color over the part surface
  (white or light-grey edges on dark; black edges on light). Quality
  visualization recolors elements by chosen metric (red = bad, green =
  good). Quality legend shows the threshold bands. Free edges / T-junc
  / duplicate elements highlighted in saturated warning colors (red,
  magenta).
- **Interaction affordances**:
  - **Mesh statistics readout** — nodes, elements, per-class
    (tet / hex / wedge / pyramid / tri / quad / beam), avg / min / max
    edge length, Jacobian min, warpage max.
  - **Quality color-coded view** — recolor by Jacobian / Aspect Ratio
    / Warpage / Skew / Tet Collapse, with a histogram below.
  - **Free-edges visualization** — highlights boundary edges so the
    user spots open shells / non-manifold geometry.
  - **Edit element**: split / merge / delete / replace element type;
    drag a node to remesh locally.
  - **Pick + probe element** — click an element → reveal its quality
    metrics + connectivity in a HUD.
  - **Seeding controls** — per-edge seed count, per-surface seed
    density, biased seed (geometric ratio).
  - **Mesh-control regions** — paint regions where mesh size should
    be smaller / finer; the mesher honors those locally.
  - **Element type assignment** — C3D8 / C3D8R / C3D10 / S4 / S3 / B31
    selection per region or per part.
  - **Quality criterion sliders** — set threshold for Jacobian /
    Warpage / Skew / Aspect; elements failing show in red.
  - **Element selection filter** — Node / Edge / Face / Element /
    Component scope for picking.
- **Accessibility**: Keyboard shortcuts for mesh / unmesh / quality
  toggle. Tooltip on every quality metric.
- **Motion**: Re-meshing surfaces a progress bar; final mesh draws
  in incrementally. Quality-color recolor is immediate. Element
  highlight on hover is immediate.

## Critical-to-success signals
1. **Mesh quality histogram + per-metric thresholds** — Jacobian /
   Aspect / Warpage / Skew / Tet Collapse; an engineer cannot
   submit a mesh without inspecting this.
2. **Free-edges / non-manifold visualization** — surfaces shell
   topology errors before solver submission.
3. **Per-element-class element count** — tet vs hex vs wedge inventory
   matters because each class has different solver behavior.
4. **Edit-element panel** — node drag, split, merge, replace —
   surgical fixes without full remesh.
5. **Element-type assignment (C3D4 / C3D8 / C3D10 / S4 / ...)** —
   explicit per-region.
6. **Seeding & mesh-control panels** — local refinement near contact
   surfaces / fillets / stress concentrators.
7. **Quality color-coded recolor** — visual map of where the bad
   elements live.
8. **Mesh statistics readout** — counts and ranges always visible
   when the mesh is loaded.
9. **Render-mode toggle** — wireframe / shaded / shaded-with-edges
   / quality-coded.
