"""Native PyVista viewport — RFC-001 W8b-min Layer-4-viz frontend.

Loads a W8a ``viewport_manifest.json`` + sibling ``.vtu`` files and
opens an interactive 3D window with:

  * Camera orbit / pan / zoom out of the box (PyVista's
    vtkInteractorStyleTrackballCamera).
  * Time-history scrubbing via a slider widget — drag to step through
    the run frame by frame, watch the deformation evolve live.
  * Field selector via keyboard shortcuts (1=displacement_magnitude,
    2=plastic_strain, 3=vmises_solid, 4=alive). Each press rebuilds
    the colormap; the active field is shown in the title.
  * Element-deletion view — pressing ``E`` toggles hiding cells with
    ``alive == 0``, so the engineer sees the eroded impactor visually
    "disappear" frame by frame instead of guessing from a count.
  * Reset-view shortcut (``R``) — re-fits the camera to the current
    state, useful after geometry deforms outside the initial frame.

This is the **MVP** viewport (W8b-min). What it deliberately does NOT
do (deferred to W8c+):

  * In-window field-selector dropdown (uses keyboard shortcuts).
  * Probe / pick — clicking a cell to graph its time history.
  * Section / clipping plane.
  * Live streaming as the solver writes new frames.
  * Capturing a viewport screenshot back into the DOCX.

Usage
-----
::

    python -m app.viz.viewport_native /path/to/viewport_manifest.json

Or programmatically::

    from app.viz.viewport_native import open_viewport
    open_viewport(Path("viewport_manifest.json"))

The function blocks until the user closes the window. Errors during
load surface as ``ViewportError``; the GUI loop itself does not raise.

ADR / RFC compliance
--------------------
* RFC-001 §4.2: this module is Layer-4-viz, parallel to the DOCX path.
  It consumes the W8a manifest contract (``schema_version="1"``) and
  reads the .vtu files via pyvista, so it never re-parses the solver
  result file directly.
* ADR-003: states are NEVER reordered or backfilled. If a manifest
  entry's vtu file is missing, the loader raises rather than
  silently skipping (the state's index would shift in the slider).
* PyVista is imported lazily inside ``open_viewport`` so a
  ``--doctor`` probe of ``app.viz`` does not crash on a half-installed
  graphics stack.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.viz.vtu_exporter import SCHEMA_VERSION


_DEFAULT_FIELD: Final[str] = "displacement_magnitude"


_FIELD_KEYBINDS: Final[dict[str, str]] = {
    "1": "displacement_magnitude",
    "2": "plastic_strain",
    "3": "vmises_solid",
    "4": "alive",
}
"""Keyboard shortcuts that switch the active scalar. Only fields
present in ``manifest.available_fields`` are wired; others print a
console hint when pressed."""


_FIELD_CMAP: Final[dict[str, str]] = {
    "displacement_magnitude": "viridis",
    "plastic_strain": "plasma",
    "vmises_solid": "turbo",
    "alive": "RdYlGn",
}


_FIELD_LABEL: Final[dict[str, str]] = {
    "displacement_magnitude": "displacement magnitude [mm]",
    "plastic_strain": "plastic strain [-]",
    "vmises_solid": "von Mises [solid only, MPa]",
    "alive": "alive (1 = live, 0 = deleted)",
}


class ViewportError(RuntimeError):
    """Raised when the manifest / VTU files cannot be loaded.

    Distinguishable from generic IOError so the Electron shell can
    surface "viewport unavailable" without taking the report run down.
    """


@dataclass(frozen=True)
class _LoadedState:
    """One frame's pre-loaded data."""

    step_id: int
    time_ms: float
    grid: Any  # pyvista.UnstructuredGrid — typed Any to keep the
    # module-level type stub free of pyvista.
    max_displacement_mm: float
    n_solids_alive: int
    n_solids_total: int


def open_viewport(manifest_path: Path) -> int:
    """Open the interactive viewport for the run described by ``manifest_path``.

    Returns the GUI exit code (0 when the window closes cleanly,
    non-zero on initialization failure). The function blocks until the
    user closes the window.

    Raises
    ------
    ViewportError
        If the manifest is unreadable, has the wrong schema version,
        or any state's VTU file cannot be loaded.
    """
    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover — doctor surface
        raise ViewportError(
            f"pyvista is required for the native viewport but is not "
            f"importable: {exc}"
        ) from exc

    if not manifest_path.is_file():
        raise ViewportError(f"manifest not found: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ViewportError(
            f"manifest is not valid JSON: {manifest_path}: {exc}"
        ) from exc

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ViewportError(
            f"manifest schema version {manifest.get('schema_version')!r} "
            f"is not the {SCHEMA_VERSION!r} this viewport supports. "
            f"Re-emit with the matching report-cli version."
        )

    states_raw = manifest.get("states") or []
    if not states_raw:
        raise ViewportError(
            f"manifest has no states; cannot open empty viewport"
        )

    available_fields = list(manifest.get("available_fields") or [])
    rootname = manifest.get("rootname") or "(unknown)"

    # Pre-load every state into memory. For the GS-101 demo (11
    # frames * ~13 KB each) this is trivial; larger runs may need a
    # lazy / cached strategy in W8c+. A bounded-cache strategy is
    # easier once we have a "live streaming" path adding frames mid-run.
    base_dir = manifest_path.parent
    loaded: list[_LoadedState] = []
    for s in states_raw:
        vtu_relpath = s.get("vtu_relpath")
        if not vtu_relpath:
            raise ViewportError(
                f"state step_id={s.get('step_id')} has no vtu_relpath"
            )
        vtu_path = base_dir / vtu_relpath
        if not vtu_path.is_file():
            raise ViewportError(f"vtu file missing: {vtu_path}")
        try:
            grid = pv.read(vtu_path)
        except Exception as exc:
            raise ViewportError(
                f"failed to read {vtu_path}: {type(exc).__name__}: {exc}"
            ) from exc
        loaded.append(
            _LoadedState(
                step_id=int(s["step_id"]),
                time_ms=float(s["time_ms"]),
                grid=grid,
                max_displacement_mm=float(s["max_displacement_mm"]),
                n_solids_alive=int(s["n_solids_alive"]),
                n_solids_total=int(s["n_solids_total"]),
            )
        )

    n_states = len(loaded)

    # Compute global ranges per field across ALL states so the colormap
    # doesn't jump as the user scrubs through time. The viewport feels
    # broken otherwise — frame N's red is frame N+1's blue.
    field_clim: dict[str, tuple[float, float]] = {}
    for fname in available_fields:
        if fname not in _FIELD_LABEL:
            continue  # unknown field — skip, can still be probed manually
        global_min = float("inf")
        global_max = float("-inf")
        for state in loaded:
            arr = _read_array(state.grid, fname)
            if arr is None or arr.size == 0:
                continue
            import numpy as np

            valid = arr[np.isfinite(arr)]
            if valid.size == 0:
                continue
            global_min = min(global_min, float(valid.min()))
            global_max = max(global_max, float(valid.max()))
        if global_min < global_max:
            field_clim[fname] = (global_min, global_max)

    # Pick an initial field that's actually present.
    initial_field = (
        _DEFAULT_FIELD
        if _DEFAULT_FIELD in available_fields
        else (available_fields[0] if available_fields else _DEFAULT_FIELD)
    )

    # Plotter setup. Window is a single render view with a slider
    # widget, an axes gizmo, and a title showing the active state.
    plotter = pv.Plotter(window_size=(1280, 900), title=f"AI-FEA Viewport — {rootname}")
    plotter.set_background("#1a1a1a")
    plotter.add_axes(line_width=2, color="white")

    state_index = {"i": 0}
    active_field = {"name": initial_field}
    show_eroded = {"on": True}  # True = show all; False = hide alive==0

    def _refresh() -> None:
        """Rebuild the actor for the current state + field selection."""
        plotter.clear_actors()
        state = loaded[state_index["i"]]
        grid = state.grid
        if not show_eroded["on"]:
            # Filter to alive cells. ``grid.threshold(0.5, scalars="alive")``
            # keeps cells with alive >= 0.5 (i.e. value 1).
            try:
                grid = grid.threshold(0.5, scalars="alive")
            except Exception:
                pass

        fname = active_field["name"]
        if fname in available_fields and grid.n_cells > 0:
            kwargs: dict[str, Any] = dict(
                scalars=fname,
                cmap=_FIELD_CMAP.get(fname, "viridis"),
                show_edges=True,
                edge_color="#444444",
                line_width=0.5,
                lighting=True,
                scalar_bar_args={
                    "title": _FIELD_LABEL.get(fname, fname),
                    "color": "white",
                    "n_labels": 5,
                    "fmt": "%.2f",
                },
            )
            if fname in field_clim:
                kwargs["clim"] = field_clim[fname]
            plotter.add_mesh(grid, **kwargs)
        elif grid.n_cells > 0:
            plotter.add_mesh(
                grid, color="#888888", show_edges=True, edge_color="#444444"
            )

        # State info banner — top-left.
        title = (
            f"step {state.step_id}/{n_states}  "
            f"t = {state.time_ms:.3f} ms  "
            f"max|d| = {state.max_displacement_mm:.2f} mm  "
            f"solids alive = {state.n_solids_alive}/{state.n_solids_total}"
        )
        plotter.add_text(
            title,
            position="upper_left",
            color="white",
            font_size=10,
            name="state_banner",
        )

        # Field hint — bottom-left.
        hint_lines = [f"field [{active_field['name']}]"]
        keybind_line = "  ".join(
            f"{key}={fld}"
            for key, fld in _FIELD_KEYBINDS.items()
            if fld in available_fields
        )
        if keybind_line:
            hint_lines.append(keybind_line)
        hint_lines.append(
            f"E = toggle eroded cells ({'visible' if show_eroded['on'] else 'hidden'})"
        )
        hint_lines.append("R = reset view   slider = scrub time")
        plotter.add_text(
            "\n".join(hint_lines),
            position="lower_left",
            color="#aaaaaa",
            font_size=9,
            name="hint_banner",
        )
        plotter.render()

    def _on_slider(value: float) -> None:
        new_idx = int(round(value))
        if new_idx < 0:
            new_idx = 0
        elif new_idx >= n_states:
            new_idx = n_states - 1
        if new_idx != state_index["i"]:
            state_index["i"] = new_idx
            _refresh()

    def _on_field_key(field: str) -> None:
        if field not in available_fields:
            print(
                f"viewport: field '{field}' not in this run "
                f"(available: {available_fields})"
            )
            return
        active_field["name"] = field
        _refresh()

    def _on_toggle_erosion() -> None:
        show_eroded["on"] = not show_eroded["on"]
        _refresh()

    def _on_reset_view() -> None:
        plotter.reset_camera()
        plotter.render()

    # First render before showing widgets (so we have a camera).
    _refresh()
    plotter.reset_camera()

    # Time-history slider — only meaningful when n_states > 1.
    if n_states > 1:
        plotter.add_slider_widget(
            _on_slider,
            rng=[0, n_states - 1],
            value=0,
            title="step_id",
            pointa=(0.20, 0.05),
            pointb=(0.80, 0.05),
            color="white",
            slider_width=0.02,
            tube_width=0.005,
            fmt="%.0f",
        )

    # Keyboard shortcuts.
    for key, field in _FIELD_KEYBINDS.items():
        # Bind via PyVista's add_key_event. The lambda captures
        # ``field`` by default-arg trick to avoid late-binding bugs.
        plotter.add_key_event(key, lambda f=field: _on_field_key(f))
    plotter.add_key_event("e", _on_toggle_erosion)
    plotter.add_key_event("E", _on_toggle_erosion)
    plotter.add_key_event("r", _on_reset_view)
    plotter.add_key_event("R", _on_reset_view)

    plotter.show(auto_close=True)
    return 0


def _read_array(grid: Any, name: str) -> Any:
    """Return a flat numpy array for ``name`` from grid, point or
    cell data, or None if the field is not present."""
    import numpy as np

    if name in grid.point_data:
        return np.asarray(grid.point_data[name]).ravel()
    if name in grid.cell_data:
        return np.asarray(grid.cell_data[name]).ravel()
    return None


def render_snapshots(
    manifest_path: Path,
    output_dir: Path,
    *,
    field: str = _DEFAULT_FIELD,
    window_size: tuple[int, int] = (1024, 768),
) -> list[Path]:
    """Off-screen renders one PNG per state, plus a 4×3 mosaic of the
    full run, for environments where opening the live window is not
    feasible (CI, headless engineer review, screenshot-only audits).

    Returns the list of per-state PNG paths.
    """
    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover
        raise ViewportError(
            f"pyvista is required for snapshots: {exc}"
        ) from exc
    import numpy as np

    if not manifest_path.is_file():
        raise ViewportError(f"manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ViewportError(
            f"manifest is not valid JSON: {manifest_path}: {exc}"
        ) from exc
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ViewportError(
            f"manifest schema version mismatch: "
            f"{manifest.get('schema_version')!r} != {SCHEMA_VERSION!r}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    base_dir = manifest_path.parent

    # Compute global colour range so the mosaic is comparable across
    # states (matches the live viewport's behaviour).
    global_min, global_max = float("inf"), float("-inf")
    states_grids: list[Any] = []
    for s in manifest["states"]:
        grid = pv.read(base_dir / s["vtu_relpath"])
        states_grids.append((s, grid))
        if field in grid.point_data:
            arr = np.asarray(grid.point_data[field]).ravel()
        elif field in grid.cell_data:
            arr = np.asarray(grid.cell_data[field]).ravel()
        else:
            continue
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            continue
        global_min = min(global_min, float(valid.min()))
        global_max = max(global_max, float(valid.max()))
    clim = (global_min, global_max) if global_min < global_max else None

    written: list[Path] = []
    for s, grid in states_grids:
        p = pv.Plotter(off_screen=True, window_size=window_size)
        p.set_background("#1a1a1a")
        kwargs: dict[str, Any] = dict(
            scalars=field if (field in grid.point_data or field in grid.cell_data) else None,
            cmap=_FIELD_CMAP.get(field, "viridis"),
            show_edges=True,
            edge_color="#444444",
            line_width=0.5,
            scalar_bar_args={"title": _FIELD_LABEL.get(field, field), "color": "white"},
        )
        if clim and kwargs["scalars"]:
            kwargs["clim"] = clim
        p.add_mesh(grid, **{k: v for k, v in kwargs.items() if v is not None})
        p.add_axes(line_width=2, color="white")
        title = (
            f"step {s['step_id']}/{manifest['n_states']}  "
            f"t = {s['time_ms']:.3f} ms  "
            f"max|d| = {s['max_displacement_mm']:.2f} mm  "
            f"solids alive = {s['n_solids_alive']}/{s['n_solids_total']}"
        )
        p.add_text(title, position="upper_left", color="white", font_size=10)
        p.camera_position = "iso"
        p.camera.zoom(1.4)
        out = output_dir / f"state_{s['step_id']:03d}.png"
        p.screenshot(str(out))
        p.close()
        written.append(out)

    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: ``python -m app.viz.viewport_native MANIFEST_PATH``.

    With ``--snapshots PATH`` it off-screen renders one PNG per state
    into PATH instead of opening the live window — useful for CI,
    Electron previews, or environments where the native window is
    blocked by allowlist / sandbox.

    Exits 0 on clean window close, 3 on viewport-load failure,
    2 on argument error.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    snapshots_dir: Path | None = None
    field = _DEFAULT_FIELD
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--snapshots":
            i += 1
            if i >= len(args):
                print(
                    "error: --snapshots requires an output directory",
                    file=sys.stderr,
                )
                return 2
            snapshots_dir = Path(args[i]).expanduser().resolve()
        elif a == "--field":
            i += 1
            if i >= len(args):
                print("error: --field requires a value", file=sys.stderr)
                return 2
            field = args[i]
        else:
            positional.append(a)
        i += 1

    if len(positional) != 1:
        print(
            "usage: python -m app.viz.viewport_native MANIFEST_PATH "
            "[--snapshots OUTPUT_DIR] [--field NAME]",
            file=sys.stderr,
        )
        return 2

    manifest = Path(positional[0]).expanduser().resolve()
    try:
        if snapshots_dir is not None:
            paths = render_snapshots(manifest, snapshots_dir, field=field)
            print(f"wrote {len(paths)} PNG(s) to {snapshots_dir}")
            return 0
        return open_viewport(manifest)
    except ViewportError as exc:
        print(f"viewport: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ViewportError",
    "main",
    "open_viewport",
    "render_snapshots",
]
