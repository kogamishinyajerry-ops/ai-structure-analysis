# Reference: bc_setup_panel — Abaqus/CAE "Load Module" + ANSYS Mechanical "Boundary Conditions"

## Source
- Abaqus/CAE Load Module (2022); ANSYS Workbench Mechanical
  "Environment" branch / "Insert > Boundary Conditions" menu.
  Sources: Abaqus/CAE User's Guide (Chapter 16-17 "Loads & BCs");
  ANSYS Mechanical User Guide ("Boundary Conditions" section);
  public Abaqus / ANSYS training (LearnCAx, CAE Associates, ANSYS
  Innovation Courses). General industry knowledge.

## Surface description
- **Layout** (Abaqus Load Module): Left module-bar (Step / Type /
  Region / Geometry selection) + center 3D viewport for region pick
  + bottom prompt area + dialog-driven Create Load / Create BC /
  Create IC entry points. Each created load/BC appears in the
  Load Manager (separate dialog).
  (ANSYS Mechanical): Tree-browser branch "Static Structural" → right
  click → Insert → Force / Pressure / Fixed Support / Displacement /
  etc. Selected BC shows a Details panel below the tree (Magnitude,
  Direction, Geometry selection, Coordinate System, Suppressed?).
- **Information density**: A single BC's Details panel shows ~8-15
  fields (Scope, Geometry / Named Selection, Type, Magnitude /
  components, Coordinate System, Step Application, Suppressed, etc.).
  Manager view shows ≥20 BCs across steps at once.
- **Token use**: Each BC category has a glyph (arrow for force,
  flag/cone for fixed support, distributed-pressure pattern for
  pressure). 3D viewport overlays the BC visualization (arrow vectors
  / triangle constraints / pressure decals). Tree icons mirror those
  glyphs.
- **Interaction affordances**:
  - **Create BC**: Menu / toolbar button opens a typed dialog
    (Force / Pressure / Moment / Fixed / Displacement / Pin / Velocity
    / Acceleration / Temperature / Heat Flux / Convection).
  - **Region/scope pick**: Click into the 3D viewport to select
    surfaces / edges / nodes / sets. "Selection filter" restricts to
    Surface / Edge / Vertex / Node / Element.
  - **Magnitude entry**: per-component (Fx / Fy / Fz / Mx / My / Mz)
    or magnitude+direction or tabular (time-varying via amplitude
    curve / load-history).
  - **Coordinate system**: pick global / part-local / user-defined CS.
  - **Per-step assignment**: which analysis step the BC is active in
    (Abaqus Step Manager, Mechanical Step Controls).
  - **Visualization**: arrows / cones / decals overlaid on the model
    in 3D viewport; legend showing BC name + magnitude.
  - **Edit**: double-click in manager / tree → re-opens dialog;
    user can change magnitude / region / type.
  - **Duplicate**: right-click → Copy → paste into another step.
  - **Suppress**: per-BC toggle, included in solver run or not.
  - **Validation**: Abaqus runs an input check before submitting;
    ANSYS Mechanical surfaces yellow/red flags for incomplete or
    conflicting BCs.
  - **Named sets**: BCs are typically applied to named element / node
    sets (rather than picking geometry every time). Sets are managed
    in their own panel; the BC panel references them.
- **Accessibility**: All entry fields are tabbable. Per-field tooltip
  documenting units, range, sign convention. Keyboard shortcuts for
  Create-Force / Create-Pressure / etc.
- **Motion**: BC arrow / cone overlay appears immediately on creation.
  Dialog open animation ≈150-200ms. Manager scroll smooth.

## Critical-to-success signals
1. **Typed BC creation dialog** — separate entry per BC kind (Force,
   Pressure, Fixed, Displacement, Temperature, etc.), each with its
   own field schema.
2. **3D-viewport region picking** — click surfaces / edges / nodes
   to scope the BC. Selection filter restricts type.
3. **Per-step / per-loadcase assignment** — BC can be active in step
   1 only, or steps 1-3, or ramped via amplitude curve.
4. **3D-viewport overlay visualization** — arrows / cones / decals
   show where the BC is and which direction.
5. **Magnitude entry with units + sign convention** — explicit, with
   per-component or magnitude+direction choices.
6. **Edit / Suppress / Delete / Duplicate** — full CRUD via right-click
   or dialog, not "delete the case and start over".
7. **Validation feedback** — incomplete or conflicting BCs surface a
   warning before solver submit.
8. **Named-sets integration** — BCs reference named entity sets so the
   same constraint can be re-used across cases.
9. **Time-varying / amplitude curves** — for dynamic / transient runs,
   the magnitude can be a function of time, not just a constant.
