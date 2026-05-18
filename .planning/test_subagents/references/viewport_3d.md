# Reference: viewport_3d — Abaqus/CAE Viewport + ANSYS Mechanical Graphics window

## Source
- Abaqus/CAE 2022 viewport behavior; ANSYS Mechanical Graphics window
  (Workbench 2022 R2 era). Sources: Abaqus/CAE User's Guide
  ("Viewport" sections), ANSYS Mechanical User's Guide ("Graphics
  Window" and "View Manipulation"). Public training videos
  (LearnCAx, CAE Associates, public ANSYS Innovation Courses).
  General industry knowledge.

## Surface description
- **Layout**: Center stage of the application. Top-edge view-cube /
  triad indicator (X/Y/Z + isometric snap buttons). Left-edge column
  of view-mode tool buttons (Wireframe / Hidden Line / Shaded /
  Shaded-with-edges / Contour). Right-edge or bottom-edge legend bar
  (color scale + min/max + units + component selector). Cursor
  coordinate / pick-info HUD top-left or bottom-left.
- **Information density**: View-cube + triad + ≥8 view-mode toggles
  + per-component contour switcher + min/max readouts + section-cut
  controls + clip-plane HUD + units + result-step / time scrubber
  + animation play/pause/scrub controls. Typically 25-40 affordances
  visible.
- **Token use**: Dark or light background (toggleable). Mesh edges
  rendered in a contrast color to the surface fill. Selected entity
  highlighted with saturated accent (often red or yellow). Contour
  legend uses canonical rainbow or blue-to-red gradient.
- **Interaction affordances**:
  - **Orbit**: Middle-mouse drag (Abaqus) / right-mouse + Ctrl
    (Mechanical) / left-mouse with view-tool active.
  - **Pan**: Middle-mouse + Shift, or dedicated pan tool.
  - **Zoom**: Mouse wheel, or middle-mouse drag with Ctrl.
  - **Fit-all**: F key (Abaqus) / "Zoom-to-Fit" button.
  - **Pick**: Left-click selects nearest entity (node / element /
    face / surface). Selection respects the active "selection filter"
    (Node / Element / Edge / Face / Volume).
  - **Box / Polygon / Lasso selection**: drag a region; Shift adds,
    Ctrl removes.
  - **Section cuts**: dedicated dialog with planar / cylindrical /
    spherical cuts; slider to drag the cut plane along its normal;
    multiple cuts can be active.
  - **Probe**: hover or click on a node/element shows scalar value +
    coordinates; persistent probe annotations can be pinned (Mechanical
    "Probe" results, Abaqus "Query" tool).
  - **View saves**: User saves named camera views (ISO, +X, etc.)
    and recalls them via menu or hotkey.
  - **Animation**: Play / pause / speed / loop controls on the bottom
    rail; scrub bar for step / increment / mode.
- **Accessibility**: Keyboard shortcuts for view manipulation (F = fit,
  1/2/3 = standard views, etc.). View-cube clickable on its faces /
  edges / corners. Color blindness options for the contour legend in
  recent versions.
- **Motion**: View transitions between named views animate over
  ≈300-500ms (camera tween). Section-cut drag is immediate (no tween).
  Animation playback at the user-specified frame rate.

## Critical-to-success signals
1. **Probe / pick affordance** — click a node → see coords + value +
   element ID. Pinnable, multi-pin (Mechanical "Probes" list).
2. **Section / clip plane** — at least one planar cut with positional
   slider + half-side toggle. Required for any interior result review.
3. **Contour legend + component switcher** — legend visible at all
   times with min/max + units; user can switch between vM / σ_xx /
   principal / displacement / etc.
4. **Persistent camera state** — orbit/pan/zoom is sticky across
   field/component switches; user does not have to re-frame the view
   on every step change.
5. **View-cube or triad with click-to-snap** — orientation is fast and
   doesn't require keyboard hunting.
6. **Animation scrubber for time / mode / increment** — modal +
   dynamic + transient cases all need scrub.
7. **Pick / hover surfacing of nodal value + coordinates** — the
   Hyperworks "result-info" overlay style.
8. **Selection filter** — restrict picking to Node / Element / Face /
   etc. so a 1M-node model is still usable.
9. **Fallback render path** — when GPU / WebGL is unavailable, some
   meaningful 2D representation still renders.
