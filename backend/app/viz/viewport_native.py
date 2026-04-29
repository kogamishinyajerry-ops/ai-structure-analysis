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
that survive the RENDERABLE_FIELDS filter AND are present-and-finite
in every state (the open_viewport intersection) are wired; others
are unbound — never the raw union from manifest.available_fields."""


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


# Codex R2 PR #112 NIT — canonical "renderable field" predicate shared
# by ``render_snapshots`` and the ``open_viewport`` keybind wiring. The
# exporter's manifest ``available_fields`` advertises raw VTK arrays
# (e.g. the 3-component ``displacement`` vector + ``cell_kind`` ints)
# that the viewport does NOT know how to colour-map. Source of truth
# for "what the viewport can show" is _FIELD_LABEL.
RENDERABLE_FIELDS: Final[frozenset[str]] = frozenset(_FIELD_LABEL.keys())


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


def open_viewport(
    manifest_path: Path,
    *,
    live: bool = False,
    poll_interval_ms: int = 1500,
) -> int:
    """Open the interactive viewport for the run described by ``manifest_path``.

    Returns the GUI exit code (0 when the window closes cleanly,
    non-zero on initialization failure). The function blocks until the
    user closes the window.

    Parameters
    ----------
    live
        When True (W8c), poll the manifest every ``poll_interval_ms``
        for newly appended states; the slider range and field colormap
        ranges grow as the streaming exporter writes new frames. The
        viewport must still be opened against a manifest that already
        has at least one state (no zero-state startup), so the caller
        is responsible for waiting on the first frame before invoking.
    poll_interval_ms
        Polling cadence for live mode. Ignored when live is False.

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

    # Codex R3 PR #112 MEDIUM — open_viewport must derive the
    # selectable/live-renderable set from RENDERABLE_FIELDS, not raw
    # manifest.available_fields (which advertises non-renderable raw
    # arrays like ``displacement`` vector + ``cell_kind``). Live and
    # snapshot now agree on the predicate.
    raw_available = list(manifest.get("available_fields") or [])
    available_fields = [f for f in raw_available if f in RENDERABLE_FIELDS]
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
        # Codex R3 PR #112 LOW + R4 LOW — pyvista returns an empty
        # grid (n_points=0) on corrupt/truncated XML rather than
        # raising; a VTU with points but no cells (n_cells=0) is also
        # structurally empty. Live viewport now matches the snapshot
        # path's refusal for both.
        if getattr(grid, "n_points", 0) == 0:
            raise ViewportError(
                f"failed to read {vtu_path}: empty grid (corrupt VTU?)"
            )
        if getattr(grid, "n_cells", 0) == 0:
            raise ViewportError(
                f"failed to read {vtu_path}: VTU has 0 cells "
                f"(structurally empty grid)"
            )
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

    # Codex R4 PR #112 MEDIUM — narrow available_fields from
    # union-across-frames (the exporter's manifest contract) to
    # intersection-across-frames-with-finite-data. The interactive
    # viewport must NOT silently render gray geometry when the user
    # scrubs to a state where the active field is missing or all-NaN.
    # Either every state carries a field's data, or that field is
    # unselectable; no halfway "scrub-and-pray" UX.
    import numpy as np

    field_clim: dict[str, tuple[float, float]] = {}
    renderable_in_every_state: list[str] = []
    for fname in available_fields:
        global_min = float("inf")
        global_max = float("-inf")
        present_and_finite_in_all = True
        for state in loaded:
            arr = _read_array(state.grid, fname)
            if arr is None or arr.size == 0:
                present_and_finite_in_all = False
                break
            valid = arr[np.isfinite(arr)]
            if valid.size == 0:
                present_and_finite_in_all = False
                break
            global_min = min(global_min, float(valid.min()))
            global_max = max(global_max, float(valid.max()))
        if not present_and_finite_in_all:
            continue
        renderable_in_every_state.append(fname)
        if global_min < global_max:
            field_clim[fname] = (global_min, global_max)
    available_fields = renderable_in_every_state

    # Codex R4 PR #112 MEDIUM follow-up — if the intersection is empty,
    # refuse rather than open a gray geometry-only window with no
    # selectable fields. Engineer cannot read anything from such a
    # viewport, and silently degrading is exactly the contract ADR-003
    # forbids.
    if not available_fields:
        raise ViewportError(
            "no field is present and finite in every state; refusing to "
            "open a viewport with no selectable scalars. "
            "Re-emit the manifest from a complete run."
        )

    # Pick an initial field that's actually present.
    initial_field = (
        _DEFAULT_FIELD
        if _DEFAULT_FIELD in available_fields
        else available_fields[0]
    )

    # Plotter setup. Window is a single render view with a slider
    # widget, an axes gizmo, and a title showing the active state.
    plotter = pv.Plotter(window_size=(1280, 900), title=f"AI-FEA Viewport — {rootname}")
    plotter.set_background("#1a1a1a")
    plotter.add_axes(line_width=2, color="white")

    state_index = {"i": 0}
    active_field = {"name": initial_field}
    show_eroded = {"on": True}  # True = show all; False = hide alive==0
    # W8c live mode shared state. Always declared (with static-mode
    # defaults) so the slider callback closure works in both modes
    # without conditional branches.
    n_states_ref = {"v": n_states}
    auto_follow_ref = {"on": True}

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
        n = n_states_ref["v"]
        if new_idx < 0:
            new_idx = 0
        elif new_idx >= n:
            new_idx = n - 1
        # Auto-follow tracks whether the user is at the live edge.
        # In static mode this is always True (n is constant) and has
        # no observable effect; in live mode it gates whether new
        # states yank the displayed frame forward.
        auto_follow_ref["on"] = (new_idx == n - 1)
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

    # Time-history slider — only meaningful when n_states > 1 OR when
    # live mode might add states. We always create the slider in live
    # mode so the range can grow as the streaming exporter feeds new
    # frames; the initial range collapses to [0, 0] if only one state
    # has been written so far.
    slider_widget_holder: dict[str, Any] = {"w": None}
    if n_states > 1 or live:
        slider_widget_holder["w"] = plotter.add_slider_widget(
            _on_slider,
            rng=[0, max(n_states - 1, 0)],
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

    # W8c — live mode: poll the manifest for newly appended states,
    # load their VTUs, extend the slider range + field_clim. The
    # polling callback is wired onto pyvista's render-loop timer so
    # it does not need its own thread. We use add_callback because
    # pyvista's lifecycle owns the iren timer; spawning a sidecar
    # thread that mutates plotter state from outside the GUI loop is
    # the documented recipe for crashes on close.
    if live:
        last_mtime_ref = {"v": manifest_path.stat().st_mtime}

        def _poll_manifest() -> None:
            try:
                mtime = manifest_path.stat().st_mtime
            except OSError:
                return
            if mtime <= last_mtime_ref["v"]:
                return
            try:
                new_payload = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                # Mid-write race or transient FS error. The atomic
                # write contract should prevent this, but if it
                # happens we just retry next tick.
                return
            new_states = new_payload.get("states") or []
            current_n = n_states_ref["v"]
            if len(new_states) <= current_n:
                last_mtime_ref["v"] = mtime
                return

            # Load only the freshly appended states.
            for s in new_states[current_n:]:
                vtu_relpath = s.get("vtu_relpath")
                if not vtu_relpath:
                    continue
                vtu_path = base_dir / vtu_relpath
                if not vtu_path.is_file():
                    continue
                try:
                    grid = pv.read(vtu_path)
                except Exception:
                    return  # try again next tick (vtu mid-write)
                if (
                    getattr(grid, "n_points", 0) == 0
                    or getattr(grid, "n_cells", 0) == 0
                ):
                    return
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

            new_n = len(loaded)
            if new_n == current_n:
                last_mtime_ref["v"] = mtime
                return

            # Update field_clim with newly observed extrema. We only
            # widen the range — never shrink — so per-frame normalisation
            # remains stable for the user's perception.
            for fname in available_fields:
                arr_min = field_clim.get(fname, (float("inf"), float("-inf")))[0]
                arr_max = field_clim.get(fname, (float("inf"), float("-inf")))[1]
                for state in loaded[current_n:new_n]:
                    arr = _read_array(state.grid, fname)
                    if arr is None or arr.size == 0:
                        continue
                    valid = arr[np.isfinite(arr)]
                    if valid.size == 0:
                        continue
                    arr_min = min(arr_min, float(valid.min()))
                    arr_max = max(arr_max, float(valid.max()))
                if arr_min < arr_max:
                    field_clim[fname] = (arr_min, arr_max)

            n_states_ref["v"] = new_n

            # Grow the slider range. PyVista returns vtkSliderWidget;
            # GetSliderRepresentation gives access to MinimumValue /
            # MaximumValue.
            sw = slider_widget_holder["w"]
            if sw is not None:
                rep = sw.GetSliderRepresentation()
                rep.SetMaximumValue(new_n - 1)

            # Auto-advance to the latest state IF the user is currently
            # at the end of the (old) timeline; otherwise leave them
            # where they are.
            if auto_follow_ref["on"]:
                state_index["i"] = new_n - 1
                if sw is not None:
                    sw.GetSliderRepresentation().SetValue(new_n - 1)
                _refresh()
            else:
                # User has scrubbed back — just rerender the banner
                # so the new total state count shows up.
                _refresh()

            last_mtime_ref["v"] = mtime

        plotter.add_callback(_poll_manifest, interval=poll_interval_ms)

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
    """Off-screen renders one PNG per state for environments where
    opening the live window is not feasible (CI, headless engineer
    review, screenshot-only audits).

    Returns the ordered list of per-state PNG paths written to
    ``output_dir``.
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

    # Codex R1 MEDIUM (PR #112): refuse silent zero-PNG success on
    # empty states list. ADR-003 says don't fabricate / don't silently
    # degrade — refusing is the only honest answer.
    states_raw = manifest.get("states") or []
    if not states_raw:
        raise ViewportError(
            f"manifest has no states (n_states=0): {manifest_path}"
        )

    # Codex R1 MEDIUM (PR #112): refuse early when the requested field
    # is unknown so the engineer is not lied to with gray geometry.
    # Canonical predicate from RENDERABLE_FIELDS so both ``render_snapshots``
    # and ``open_viewport`` agree on what's supported (Codex R2 NIT PR #112).
    if field not in RENDERABLE_FIELDS:
        raise ViewportError(
            f"unknown field {field!r}; expected one of "
            f"{sorted(RENDERABLE_FIELDS)!r}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    base_dir = manifest_path.parent

    # Compute global colour range so the mosaic is comparable across
    # states (matches the live viewport's behaviour). Wrap pv.read so
    # corrupt VTU files surface as ViewportError instead of pyvista
    # IO exceptions (Codex R1 MEDIUM PR #112).
    #
    # Codex R3 PR #112 MEDIUM — strict per-state refusal: every state
    # must carry the field array AND at least one finite sample. The
    # "anywhere" semantics of R2 still let mixed-state runs silently
    # render gray geometry for the missing/all-NaN frames. ADR-003 says
    # don't paint gray over a real run; that means refusing the *run*,
    # not just the empty *aggregate*.
    global_min, global_max = float("inf"), float("-inf")
    states_grids: list[Any] = []
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
        # pyvista returns an empty grid (n_points == 0) on corrupt /
        # truncated XML — it only emits a UserWarning. n_cells == 0
        # (points-only) is also structurally empty (Codex R5 PR #112).
        # Catch both so the snapshot path matches open_viewport.
        if getattr(grid, "n_points", 0) == 0:
            raise ViewportError(
                f"failed to read {vtu_path}: empty grid (corrupt VTU?)"
            )
        if getattr(grid, "n_cells", 0) == 0:
            raise ViewportError(
                f"failed to read {vtu_path}: VTU has 0 cells "
                f"(structurally empty grid)"
            )
        states_grids.append((s, grid))
        if field in grid.point_data:
            arr = np.asarray(grid.point_data[field]).ravel()
        elif field in grid.cell_data:
            arr = np.asarray(grid.cell_data[field]).ravel()
        else:
            raise ViewportError(
                f"field {field!r} missing in state step_id={s.get('step_id')} "
                f"({vtu_path}); refusing to emit a gray frame for this state"
            )
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            raise ViewportError(
                f"field {field!r} has no finite samples in state "
                f"step_id={s.get('step_id')} (all NaN/Inf); refusing to "
                f"emit an uncoloured frame for this state"
            )
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
    live = False
    poll_interval_ms = 1500
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
        elif a == "--live":
            live = True
        elif a == "--poll-interval-ms":
            i += 1
            if i >= len(args):
                print(
                    "error: --poll-interval-ms requires a value",
                    file=sys.stderr,
                )
                return 2
            try:
                poll_interval_ms = int(args[i])
            except ValueError:
                print(
                    f"error: --poll-interval-ms must be an integer; "
                    f"got {args[i]!r}",
                    file=sys.stderr,
                )
                return 2
            if poll_interval_ms <= 0:
                print(
                    "error: --poll-interval-ms must be positive",
                    file=sys.stderr,
                )
                return 2
        else:
            positional.append(a)
        i += 1

    if len(positional) != 1:
        print(
            "usage: python -m app.viz.viewport_native MANIFEST_PATH "
            "[--snapshots OUTPUT_DIR] [--field NAME] "
            "[--live] [--poll-interval-ms MS]",
            file=sys.stderr,
        )
        return 2

    if live and snapshots_dir is not None:
        print(
            "error: --live and --snapshots are mutually exclusive "
            "(snapshots are a one-shot render, live polls a growing "
            "manifest)",
            file=sys.stderr,
        )
        return 2

    manifest = Path(positional[0]).expanduser().resolve()
    try:
        if snapshots_dir is not None:
            paths = render_snapshots(manifest, snapshots_dir, field=field)
            print(f"wrote {len(paths)} PNG(s) to {snapshots_dir}")
            return 0
        return open_viewport(
            manifest, live=live, poll_interval_ms=poll_interval_ms
        )
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
