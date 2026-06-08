# Reference: case_tree_panel — Altair HyperWorks (HyperMesh) Model Browser

## Source
- Altair HyperMesh / HyperWorks ~2022.x and later
- Sources: Altair HyperMesh user manual ("Model Browser" topic), public
  Altair University training videos, public Altair Innovation Conference
  recordings. General industry knowledge of the product.

## Surface description
- **Layout**: Vertical left-hand rail (resizable, drag-handle on the
  right edge) holding a multi-section tree (Components / Assemblies /
  Properties / Materials / Loadcollectors / Boundary Conditions /
  Solver Decks / Sets). The tree is a single browser pane; switching
  "view filters" at the top (Component View / Entity View / Set View /
  Solver View) re-roots it.
- **Information density**: Typically ≥30 affordances visible without
  scrolling on a 1080p display. Each row carries:
  - expand/collapse chevron (16px)
  - visibility eye-icon (per-entity 3D viewport on/off)
  - mesh / geometry hide toggle (separate from visibility — shows mesh
    but hides surfaces, etc.)
  - color swatch (per-component, click to recolor)
  - entity-type icon (component / property / material / load /
    constraint / contact — each gets a glyph)
  - entity name (double-click to inline-rename)
  - entity ID number (right-aligned, monospaced)
- **Token use**: Dark neutral palette by default (recent versions ship
  a Light theme too). Selected row highlighted with a saturated accent
  band on the left edge + tinted background. Inactive items muted
  greys. Color swatches per component are the only saturated chips in
  the tree.
- **Interaction affordances**:
  - Single-click selects (highlights in 3D viewport).
  - Shift-click / Ctrl-click for range / multi-select.
  - Double-click on name → inline edit (rename).
  - Drag-and-drop to reorder, to reparent into assemblies, to move
    elements between components.
  - Right-click context menu with ≥10 actions (Make Current, Isolate,
    Show Only, Hide, Reverse, Card Edit, Delete, Renumber, Organize,
    Color, Find Attached, Export Solver Deck, etc.).
  - Keyboard shortcuts: F2 rename, Del delete, F5 refresh,
    Ctrl-F find-by-name, arrow keys traverse, Space toggles visibility.
  - "View" filters (top of panel): Component / Assembly / Property /
    Material / Set / Solver tree perspectives — switching re-roots the
    same data.
  - Search box at the panel header — incremental filter as you type.
- **Accessibility**: Keyboard navigation across the tree (arrow keys
  expand/collapse + traverse). High-contrast theme available on
  request. Tooltip on every icon. Mouse-wheel scrolls; pinch on
  trackpads scrolls.
- **Motion**: Expand/collapse animates the chevron rotation (≈150ms)
  + reveals child rows with a brief height transition (≈150-200ms).
  Visibility eye-icon does NOT animate the 3D viewport (instant). Drag
  feedback is a translucent ghost row following the cursor.

## Critical-to-success signals
1. **Multi-section single-tree organization** — one panel covers
   components / properties / materials / loadcollectors / constraints
   / contacts / sets / solver decks. The user does not navigate to
   separate panels for each entity class.
2. **Per-row 3D visibility toggle (eye-icon)** — clicking the eye
   per-entity hides/shows that entity in the 3D viewport WITHOUT
   selecting it. This is non-negotiable for any non-trivial assembly.
3. **Right-click context menu with destructive + organizational
   actions** — Isolate, Show Only, Card Edit, Find Attached, Delete,
   Renumber.
4. **Inline rename (double-click name → text input)** — entity names
   are part of the analyst's idiom (LC_FRONT_FIXED, MAT_AL_T6); rename
   speed determines how usable the tree feels.
5. **Drag-to-reorder + drag-to-reparent** — assembly-tree organization
   without leaving the tree.
6. **Search / incremental filter at the panel header** — assemblies
   with 1000+ components are common; search is required.
7. **Color swatch per component** — visual identification of parts in
   the 3D viewport when many components share similar geometry.
8. **Tree-view perspectives switcher** — Component / Assembly /
   Property / Material / Set / Solver Deck rooting of the same data.
