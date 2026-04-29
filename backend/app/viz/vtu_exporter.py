"""OpenRadioss → VTU + manifest exporter for the Layer-4-viz path.

RFC-001 W8a (Layer-4-viz) — the live-CAE-viewport companion to the
DOCX path. Where ``services.report.draft`` produces an evidence-cited
DOCX as the sign-off artefact, this module produces a per-state
``.vtu`` file plus a JSON manifest that an Electron / vtk.js viewport
consumes to scrub through the run.

Output layout for a run rooted at ``output_dir``::

    output_dir/
        viewport_manifest.json
        states/
            <rootname>_state_001.vtu
            <rootname>_state_002.vtu
            ...

``viewport_manifest.json`` schema::

    {
      "schema_version": "1",
      "rootname": "model_00",
      "unit_system": "si-mm",
      "n_states": 11,
      "available_fields": ["displacement", "vmises_solid", ...],
      "states": [
        {
          "step_id": 1,
          "time_ms": 0.0,
          "vtu_relpath": "states/model_00_state_001.vtu",
          "max_displacement_mm": 0.0,
          "n_solids_alive": 120,
          "n_solids_total": 120,
          "n_facets_alive": 180,
          "n_facets_total": 180
        },
        ...
      ]
    }

ADR / RFC compliance:
  * ADR-001: each state's geometry uses the deformed coordinates from
    the solver result file (``coorA``); displacement is computed as
    ``coorA(state) - coorA(state_0)`` (mirrors the W7b reader contract).
  * ADR-003: when a state lacks a field (e.g. plastic strain not
    output), we omit the array rather than synthesising zeros, so the
    viewport can grey out the field selector.
  * RFC-001 §4.2: this module is Layer-4 (viz). It imports
    ``vortex_radioss`` directly (Layer 1) instead of going through the
    W7b ``OpenRadiossReader`` because the ``ReaderHandle`` Protocol
    deliberately does not expose element connectivity (point-only Mesh
    Protocol per W7c). The exporter is the smallest scope that needs
    connectivity, and pulling it through Layer 2 would expand the
    Protocol surface used by exactly one consumer. Future RFC may
    promote a ``SupportsElementConnectivity`` capability to Layer 2 if
    a second consumer (e.g. CalculiX viewport) needs the same wiring.

This module deliberately:
  * does NOT render PNG/MP4 frames — that's W5f's matplotlib
    territory; the viewport is interactive and live.
  * does NOT compute Layer-3 derivations — those still live in
    ``app.domain.ballistics`` / ``app.domain.stress_derivatives``.
  * does NOT touch the DOCX path — the manifest is a fresh artefact.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final

import numpy as np

from app.core.types import UnitSystem


SCHEMA_VERSION: Final[str] = "1"
"""Bumped when the manifest JSON shape changes. Renderer code MUST
guard on this value."""


_VTK_QUAD: Final[int] = 9
_VTK_HEXAHEDRON: Final[int] = 12
"""VTK cell-type integers (vtkCellType.h). Hardcoded so this module
does not need ``vtk`` at import time — pyvista is imported lazily
inside ``export_run`` so a half-installed graphics stack does not
crash a doctor probe."""


class VTUExportError(RuntimeError):
    """Raised when the OpenRadioss frames cannot be turned into VTU.

    Distinguishable from generic IOError so the Electron shell can
    surface a "viewport unavailable" hint without taking the whole
    report run down."""


@dataclass(frozen=True)
class _StateRecord:
    """One row of the manifest."""

    step_id: int
    time_ms: float
    vtu_relpath: str
    max_displacement_mm: float
    n_solids_alive: int
    n_solids_total: int
    n_facets_alive: int
    n_facets_total: int


class _StreamingExporter:
    """Stateful frame-to-VTU exporter shared by ``export_run`` (one-shot)
    and ``export_run_streaming`` (W8c watcher).

    Owns:
      - the persistent decompression scratch directory
      - the lazy-loaded ``pyvista`` + ``RadiossReader`` modules
      - the reference-frame state (anchored on the FIRST frame seen,
        so streaming runs that start mid-bake still produce a stable
        displacement reference; export_run feeds frames in step-id
        order so the anchor is the true t=0 frame in the one-shot
        case as well)
      - the records / available_fields accumulators that feed the
        manifest

    Each ``export_one(frame_path)`` call decompresses the frame,
    parses it, emits ``<output_dir>/states/<rootname>_state_NNN.vtu``,
    and appends a ``_StateRecord``. ``write_manifest()`` atomically
    rewrites ``viewport_manifest.json`` (write to ``.tmp``, fsync,
    ``os.replace``) so a viewer reading the manifest never observes
    a half-finished state list.
    """

    def __init__(
        self,
        *,
        rootname: str,
        output_dir: Path,
        unit_system: UnitSystem,
        pv: Any,
        reader_cls: Any,
    ) -> None:
        self.rootname = rootname
        self.output_dir = output_dir
        self.unit_system = unit_system
        self._pv = pv
        self._reader_cls = reader_cls

        self.states_dir = output_dir / "states"
        self.states_dir.mkdir(parents=True, exist_ok=True)

        # Reference frame state — populated on the first export_one call.
        self.ref_coords: np.ndarray | None = None
        self.n_solids_total: int | None = None
        self.n_facets_total: int | None = None
        self.n_nodes: int | None = None

        self.records: list[_StateRecord] = []
        self.available_fields: set[str] = set()

        # Track which source frame paths have already been exported so
        # streaming polls can be idempotent. Keyed by absolute path so
        # that re-running against a renamed dir doesn't double-process.
        self.processed: set[Path] = set()

        # Persistent scratch directory for gz decompression. Closed by
        # the context manager.
        self._scratch_tmpdir = tempfile.TemporaryDirectory(
            prefix="vtu-stream-"
        )
        self.scratch = Path(self._scratch_tmpdir.name)

    def __enter__(self) -> _StreamingExporter:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._scratch_tmpdir.cleanup()

    def export_one(
        self, frame_path: Path, *, step_num: int | None = None
    ) -> _StateRecord:
        """Decompress + parse + render a single frame.

        Parameters
        ----------
        frame_path
            Source ``A###`` (or ``A###.gz``) frame.
        step_num
            Canonical A### step number for this frame, parsed from the
            filename by the caller. If omitted, the exporter falls back
            to ``len(self.records) + 1`` for backwards compatibility
            with one-shot ``export_run`` (which feeds frames already
            sorted A001..A0NN with no gaps). Streaming MUST pass the
            explicit step_num parsed from the filename so a manifest
            written after observing {A001, A005} cannot mislabel A005
            as state 2 (Codex R1 PR #113 HIGH).

        Returns the freshly appended ``_StateRecord``. Does NOT rewrite
        the manifest — call ``write_manifest()`` after one or more
        ``export_one`` calls so the on-disk JSON remains atomic.

        Raises VTUExportError if the frame's mesh topology disagrees
        with the reference (cell counts, node count), or if step_num
        breaks contiguous-from-1 ordering (gap or duplicate).
        """
        if frame_path in self.processed:
            raise VTUExportError(
                f"frame already exported in this session: {frame_path}"
            )

        # Canonical step assignment + contiguous-from-1 contract.
        # One-shot export_run feeds frames sorted A001..A0NN already so
        # the implicit fallback matches the explicit case. Streaming
        # must pass step_num so we catch out-of-order or gap frames.
        expected_step = len(self.records) + 1
        if step_num is None:
            step_num = expected_step
        if step_num != expected_step:
            raise VTUExportError(
                f"frame {frame_path.name} step number {step_num} is not "
                f"contiguous with previously exported step "
                f"{expected_step - 1}; expected {expected_step}. The "
                f"streaming exporter requires A001..A### with no gaps "
                f"so the displacement reference (A001) and step ids "
                f"stay sound."
            )
        decompressed_paths = _decompress_frames_to(self.scratch, [frame_path])
        decompressed = decompressed_paths[0]

        reader = self._reader_cls(str(decompressed))
        arrays = reader.raw_arrays
        header = reader.raw_header
        time_ms = float(header["time"])
        coords = np.asarray(arrays["coorA"], dtype=np.float64)

        if self.ref_coords is None:
            # First frame ever — anchor the reference.
            self.ref_coords = coords
            self.n_solids_total = int(header["nbElts3D"])
            self.n_facets_total = int(header["nbFacets"])
            self.n_nodes = int(header["nbNodes"])
        else:
            if coords.shape != (self.n_nodes, 3):
                raise VTUExportError(
                    f"frame {frame_path.name} node count {coords.shape[0]} "
                    f"differs from reference {self.n_nodes}; mesh topology "
                    f"changed mid-run, which the viewport contract forbids"
                )

        n_solids_total = self.n_solids_total
        n_facets_total = self.n_facets_total
        assert n_solids_total is not None  # invariant: anchored above
        assert n_facets_total is not None
        assert self.ref_coords is not None

        disp = coords - self.ref_coords
        disp_mag = np.linalg.norm(disp, axis=1)

        connect_3d = np.asarray(arrays["connect3DA"], dtype=np.int64)
        connect_2d = np.asarray(arrays["connectA"], dtype=np.int64)

        _validate_deletion_flags(
            arrays["delElt3DA"], "delElt3DA", frame_path.name
        )
        _validate_deletion_flags(
            arrays["delEltA"], "delEltA", frame_path.name
        )
        del_3d = np.asarray(arrays["delElt3DA"], dtype=bool)
        del_2d = np.asarray(arrays["delEltA"], dtype=bool)

        # Length asserts — same contract as the W8a reference frame.
        if connect_3d.shape[0] != n_solids_total:
            raise VTUExportError(
                f"frame {frame_path.name} solid connectivity rows "
                f"({connect_3d.shape[0]}) differ from reference "
                f"nbElts3D ({n_solids_total}); mesh topology changed "
                f"mid-run, viewport contract forbids."
            )
        if del_3d.shape[0] != n_solids_total:
            raise VTUExportError(
                f"frame {frame_path.name} solid delElt array length "
                f"({del_3d.shape[0]}) differs from nbElts3D "
                f"({n_solids_total})."
            )
        if connect_2d.shape[0] != n_facets_total:
            raise VTUExportError(
                f"frame {frame_path.name} facet connectivity rows "
                f"({connect_2d.shape[0]}) differ from reference "
                f"nbFacets ({n_facets_total}); mesh topology changed "
                f"mid-run, viewport contract forbids."
            )
        if del_2d.shape[0] != n_facets_total:
            raise VTUExportError(
                f"frame {frame_path.name} facet delElt array length "
                f"({del_2d.shape[0]}) differs from nbFacets "
                f"({n_facets_total})."
            )

        cells_blocks: list[np.ndarray] = []
        cell_types: list[int] = []
        cell_alive: list[bool] = []
        cell_kind: list[int] = []
        for row, alive in zip(connect_3d, del_3d, strict=True):
            cells_blocks.append(np.array([8, *row], dtype=np.int64))
            cell_types.append(_VTK_HEXAHEDRON)
            cell_alive.append(bool(alive))
            cell_kind.append(0)
        for row, alive in zip(connect_2d, del_2d, strict=True):
            cells_blocks.append(np.array([4, *row], dtype=np.int64))
            cell_types.append(_VTK_QUAD)
            cell_alive.append(bool(alive))
            cell_kind.append(1)

        cells = np.concatenate(cells_blocks)
        grid = self._pv.UnstructuredGrid(
            cells, np.array(cell_types, dtype=np.uint8), coords
        )

        grid.point_data["displacement"] = disp.astype(np.float32)
        grid.point_data["displacement_magnitude"] = disp_mag.astype(np.float32)
        self.available_fields.update(["displacement", "displacement_magnitude"])

        efunc_solid = np.asarray(arrays.get("eFunc3DA"), dtype=np.float32)
        efunc_shell = np.asarray(arrays.get("eFuncA"), dtype=np.float32)
        if (
            efunc_solid.size == n_solids_total
            and efunc_shell.size == n_facets_total
        ):
            grid.cell_data["plastic_strain"] = np.concatenate(
                [efunc_solid, efunc_shell]
            )
            self.available_fields.add("plastic_strain")

        tens_3d = np.asarray(arrays.get("tensVal3DA"), dtype=np.float32)
        if tens_3d.shape == (n_solids_total, 6):
            vm_solid = _von_mises_voigt6(tens_3d)
            vm_full = np.full(
                n_solids_total + n_facets_total, np.nan, dtype=np.float32
            )
            vm_full[:n_solids_total] = vm_solid
            grid.cell_data["vmises_solid"] = vm_full
            self.available_fields.add("vmises_solid")

        grid.cell_data["alive"] = np.array(cell_alive, dtype=np.uint8)
        grid.cell_data["cell_kind"] = np.array(cell_kind, dtype=np.uint8)
        self.available_fields.update(["alive", "cell_kind"])

        # step_num is now the canonical A### number, not a per-call
        # counter. Filename + manifest both use it, so a streaming run
        # that pauses + resumes (or one whose first observed frame is
        # A005) cannot relabel its way into a wrong timeline.
        state_idx = step_num
        vtu_path = self.states_dir / f"{self.rootname}_state_{state_idx:03d}.vtu"
        # Atomic VTU write: write to a sibling ``*.tmp.vtu`` (pyvista
        # validates extensions, so ``.tmp`` alone is rejected) then
        # ``os.replace`` so a polling viewer never reads a half-written
        # .vtu (W8c contract).
        tmp_vtu = vtu_path.with_name(
            f"{vtu_path.stem}.tmp{vtu_path.suffix}"
        )
        grid.save(str(tmp_vtu))
        os.replace(tmp_vtu, vtu_path)

        record = _StateRecord(
            step_id=state_idx,
            time_ms=time_ms,
            vtu_relpath=f"states/{vtu_path.name}",
            max_displacement_mm=float(disp_mag.max()),
            n_solids_alive=int(del_3d.sum()),
            n_solids_total=n_solids_total,
            n_facets_alive=int(del_2d.sum()),
            n_facets_total=n_facets_total,
        )
        self.records.append(record)
        self.processed.add(frame_path)
        return record

    def write_manifest(self) -> Path:
        """Atomically rewrite ``viewport_manifest.json``.

        Writes to a sibling ``.tmp`` file, fsyncs, then ``os.replace``
        onto the canonical name so a polling viewer either sees the
        previous manifest or the new one — never a truncated middle
        state.
        """
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "rootname": self.rootname,
            "unit_system": self.unit_system.value,
            "n_states": len(self.records),
            "available_fields": sorted(self.available_fields),
            "states": [
                {
                    "step_id": r.step_id,
                    "time_ms": r.time_ms,
                    "vtu_relpath": r.vtu_relpath,
                    "max_displacement_mm": r.max_displacement_mm,
                    "n_solids_alive": r.n_solids_alive,
                    "n_solids_total": r.n_solids_total,
                    "n_facets_alive": r.n_facets_alive,
                    "n_facets_total": r.n_facets_total,
                }
                for r in self.records
            ],
        }
        manifest_path = self.output_dir / "viewport_manifest.json"
        tmp = manifest_path.with_name(manifest_path.name + ".tmp")
        body = json.dumps(manifest, indent=2, ensure_ascii=False)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, manifest_path)
        return manifest_path


def _resolve_pyvista_and_reader() -> tuple[Any, Any]:
    """Lazy import of pyvista + vortex_radioss with VTUExportError on
    missing deps. Shared by export_run and export_run_streaming so the
    failure mode is identical between the two entry points.
    """
    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover — doctor surface
        raise VTUExportError(
            f"pyvista is required for VTU export but is not importable: {exc}"
        ) from exc
    try:
        from vortex_radioss.animtod3plot.RadiossReader import RadiossReader
    except ImportError as exc:  # pragma: no cover — doctor surface
        raise VTUExportError(
            f"vortex_radioss is required for VTU export but is not importable: {exc}"
        ) from exc
    return pv, RadiossReader


def _check_unit_system(unit_system: UnitSystem) -> None:
    """ADR-003 refusal: only SI_MM is honest until manifest grows
    explicit per-key units. Shared by both export entrypoints."""
    if unit_system is not UnitSystem.SI_MM:
        raise VTUExportError(
            f"viewport export currently only supports SI_MM; got "
            f"{unit_system.value}. Multi-unit manifest schema is "
            f"planned for W8a-units."
        )


def export_run(
    *,
    openradioss_root: Path,
    rootname: str,
    output_dir: Path,
    unit_system: UnitSystem = UnitSystem.SI_MM,
) -> Path:
    """Convert an OpenRadioss animation run into per-state VTU files.

    Parameters
    ----------
    openradioss_root
        Directory containing the engine output frames named
        ``<rootname>A001`` … ``<rootname>A0NN``. Frames may be either
        plain or gzip-compressed (``.gz``) — the exporter handles both
        by decompressing into a temp dir.
    rootname
        OpenRadioss run rootname (e.g. ``model_00``). Same value the
        engine deck used.
    output_dir
        Where to write ``viewport_manifest.json`` and ``states/*.vtu``.
        Created if it does not exist; existing contents are NOT
        deleted but state files are overwritten.
    unit_system
        Tagged into the manifest so the renderer can label axes
        correctly.

    Returns
    -------
    Path
        Absolute path to the manifest file.

    Raises
    ------
    VTUExportError
        If no animation frames are found, the rootname does not match,
        or the frame parser fails.
    """
    pv, RadiossReader = _resolve_pyvista_and_reader()
    _check_unit_system(unit_system)

    if not openradioss_root.is_dir():
        raise VTUExportError(
            f"OpenRadioss root is not a directory: {openradioss_root}"
        )

    frames_with_step = _enumerate_frames_with_step(openradioss_root, rootname)
    if not frames_with_step:
        raise VTUExportError(
            f"no animation frames found at {openradioss_root}/{rootname}A* "
            f"(checked plain and .gz). Did the engine run terminate normally?"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    with _StreamingExporter(
        rootname=rootname,
        output_dir=output_dir,
        unit_system=unit_system,
        pv=pv,
        reader_cls=RadiossReader,
    ) as exporter:
        for step_num, frame_path in frames_with_step:
            exporter.export_one(frame_path, step_num=step_num)
        return exporter.write_manifest()


def export_run_streaming(
    *,
    openradioss_root: Path,
    rootname: str,
    output_dir: Path,
    unit_system: UnitSystem = UnitSystem.SI_MM,
    poll_interval_s: float = 1.0,
    max_idle_s: float = 30.0,
    timeout_s: float | None = None,
    on_state_appended: Callable[[_StateRecord], None] | None = None,
    _now: Callable[[], float] = time.monotonic,
    _sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """RFC-001 W8c — watcher variant of ``export_run``.

    Polls ``openradioss_root`` for ``<rootname>A###(.gz)?`` frames,
    incrementally exports each new one, and atomically rewrites the
    manifest after every state. A live viewport polling the manifest
    sees state count grow as the solver writes frames.

    Parameters
    ----------
    openradioss_root, rootname, output_dir, unit_system
        Same as ``export_run``.
    poll_interval_s
        Seconds between ``_enumerate_frames`` calls. Default 1.0s — fast
        enough for engineer-perceived liveness, slow enough not to hammer
        a disk that's also being written by the engine.
    max_idle_s
        Exit cleanly when no new frame has appeared for this many
        seconds — interpreted as "solver finished, no more frames
        expected". Default 30s. Pass ``math.inf`` to never auto-exit.
    timeout_s
        Hard wall-clock cap. None = no cap. Useful for tests; in
        production the idle-timeout is the natural exit.
    on_state_appended
        Optional callback fired after each successful ``export_one``
        with the freshly written ``_StateRecord``. Tests use this to
        verify ordering without reading manifest mid-loop.
    _now, _sleep
        Hooks for tests to inject fake time so the polling loop runs
        instantly.

    Returns
    -------
    Path
        Absolute path to ``viewport_manifest.json`` after the loop
        exits. May reference 0 states if the loop timed out before
        any frame appeared (caller decides how to react).

    Raises
    ------
    VTUExportError
        If a frame fails the export contract (mesh topology change,
        bad deletion flags, etc.). Streaming does NOT swallow these —
        a corrupt frame is a fatal manifest event.
    """
    pv, RadiossReader = _resolve_pyvista_and_reader()
    _check_unit_system(unit_system)

    if not openradioss_root.is_dir():
        raise VTUExportError(
            f"OpenRadioss root is not a directory: {openradioss_root}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    if max_idle_s <= 0:
        raise VTUExportError(
            f"max_idle_s must be positive; got {max_idle_s}"
        )
    if poll_interval_s <= 0:
        raise VTUExportError(
            f"poll_interval_s must be positive; got {poll_interval_s}"
        )

    with _StreamingExporter(
        rootname=rootname,
        output_dir=output_dir,
        unit_system=unit_system,
        pv=pv,
        reader_cls=RadiossReader,
    ) as exporter:
        # Always emit an initial manifest so a polling viewer sees a
        # well-formed (zero-state) manifest immediately. Otherwise
        # viewport startup races with the first frame.
        exporter.write_manifest()

        start = _now()
        last_progress = start
        # Codex R2 PR #113 MEDIUM — track the latest unresolved gap
        # observation across polls so an idle-timeout exit can refuse
        # rather than silently truncate. If the watcher saw A005 but
        # never observed A002-A004, the run is partial and the
        # engineer needs to know.
        unresolved_gap: tuple[int, str] | None = None
        while True:
            try:
                all_frames = _enumerate_frames_with_step(
                    openradioss_root, rootname
                )
            except VTUExportError:
                # Ambiguous frame (plain + .gz both present) — let the
                # error bubble; this is a deck/run misconfiguration the
                # engineer must resolve.
                raise
            # Codex R1 PR #113 HIGH — only consume frames that extend
            # the contiguous A001..A### prefix the exporter has
            # already processed. If the watcher starts with {A001,
            # A005} or {A005} (engine partial recovery, user invokes
            # mid-bake), we must NOT export A005 as state 2 or anchor
            # displacement on A005. Instead we wait until A002, A003,
            # A004 fill in.
            next_expected = len(exporter.records) + 1
            current_gap: tuple[int, str] | None = None
            for step_num, frame_path in all_frames:
                if frame_path in exporter.processed:
                    continue
                if step_num < next_expected:
                    # Smaller step than expected after the contiguous
                    # prefix has already advanced past it. Filenames
                    # are derived from solver output; this only
                    # happens if a frame was processed then deleted
                    # then re-created. Treat as a hard error.
                    raise VTUExportError(
                        f"frame {frame_path.name} step {step_num} "
                        f"reappeared after the contiguous prefix moved "
                        f"past it (next expected {next_expected}); "
                        f"OpenRadioss output dir was mutated during a "
                        f"streaming run."
                    )
                if step_num != next_expected:
                    # Gap — stop scanning, wait for the gap to fill.
                    current_gap = (step_num, frame_path.name)
                    break
                record = exporter.export_one(frame_path, step_num=step_num)
                exporter.write_manifest()
                last_progress = _now()
                if on_state_appended is not None:
                    on_state_appended(record)
                next_expected += 1
            unresolved_gap = current_gap

            now = _now()
            if now - last_progress >= max_idle_s:
                if unresolved_gap is not None:
                    obs_step, obs_name = unresolved_gap
                    raise VTUExportError(
                        f"streaming exporter idled out with unresolved "
                        f"gap: observed frame {obs_name} (step "
                        f"{obs_step}) but next expected step is "
                        f"{next_expected}. Frame(s) "
                        f"A{next_expected:03d}..A{obs_step - 1:03d} "
                        f"were never written; the engine likely "
                        f"crashed mid-run. Manifest contains the "
                        f"contiguous A001..A{next_expected - 1:03d} "
                        f"prefix."
                    )
                break
            if timeout_s is not None and (now - start) >= timeout_s:
                # Hard timeout — let it through even with an
                # unresolved gap (caller asked for a wall-clock cap).
                break
            _sleep(poll_interval_s)

        return exporter.output_dir / "viewport_manifest.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enumerate_frames(root: Path, rootname: str) -> list[Path]:
    """Return the animation frames for ``rootname`` sorted by step id.

    OpenRadioss writes frames as ``<rootname>A001``, ``<rootname>A002``,
    … optionally gzipped to ``.gz``. We accept either form, but a frame
    must exist in exactly one form (a stale ``A001`` next to a fresh
    ``A001.gz`` is ambiguous and we reject the run).
    """
    return [p for _, p in _enumerate_frames_with_step(root, rootname)]


def _enumerate_frames_with_step(
    root: Path, rootname: str
) -> list[tuple[int, Path]]:
    """Same as ``_enumerate_frames`` but pairs each path with its
    canonical A### step number parsed from the filename. Streaming uses
    this so it can enforce contiguous-from-A001 ordering and refuse to
    process a frame whose step number does not match the next expected
    slot (Codex R1 PR #113 HIGH).
    """
    candidates: dict[int, Path] = {}
    pattern_prefix = f"{rootname}A"
    for entry in root.iterdir():
        name = entry.name
        if not name.startswith(pattern_prefix):
            continue
        rest = name[len(pattern_prefix):]
        if rest.endswith(".gz"):
            rest = rest[:-3]
        if not rest.isdigit():
            continue
        step = int(rest)
        # Codex R2 PR #113 MEDIUM — refuse non-positive step numbers
        # explicitly. ``A000`` (or worse) parses to step=0 which would
        # otherwise silently get filtered out by the streaming loop's
        # ``< next_expected`` skip and never surface as the broken
        # solver output it actually is.
        if step <= 0:
            raise VTUExportError(
                f"frame {name} has non-positive step number {step}; "
                f"OpenRadioss A### frames must start at A001 (the "
                f"reference) and increment monotonically."
            )
        if step in candidates:
            raise VTUExportError(
                f"ambiguous frame {step}: both {candidates[step].name} "
                f"and {name} present"
            )
        candidates[step] = entry
    return [(k, candidates[k]) for k in sorted(candidates)]


def _decompress_frames_to(scratch: Path, frames: list[Path]) -> list[Path]:
    """Decompress (or copy) frames into ``scratch`` so RadiossReader
    sees plain binary files. Returns the scratch paths in the same
    order as input.
    """
    out: list[Path] = []
    for frame in frames:
        if frame.suffix == ".gz":
            stem = frame.name[:-3]
            dest = scratch / stem
            with gzip.open(frame, "rb") as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            dest = scratch / frame.name
            shutil.copyfile(frame, dest)
        out.append(dest)
    return out


def _validate_deletion_flags(
    arr: Any, array_name: str, frame_name: str
) -> None:
    """Codex R2 HIGH on PR #111 — assert ``arr`` contains only the
    documented ``{0, 1}`` values.

    OpenRadioss writes ``delEltA`` / ``delElt3DA`` as alive-flags
    where 1 = alive and 0 = deleted. A bare ``np.asarray(..., dtype=bool)``
    would silently coerce any non-zero (e.g. ``2`` from a corrupt
    parse, or ``-1`` from an int-flow-through) to True, which would
    contaminate the manifest's alive counts and the VTU's per-cell
    ``alive`` array without raising. This helper raises
    :class:`VTUExportError` on any value outside ``{0, 1}`` so the
    bug class surfaces at export time rather than as a misleading
    viewport.
    """
    raw = np.asarray(arr)
    # Already-bool arrays are by definition in {0,1}.
    if raw.dtype == bool:
        return
    # Numeric arrays: every entry must be exactly 0 or 1.
    finite = np.isfinite(raw)
    if not bool(finite.all()):
        raise VTUExportError(
            f"frame {frame_name} {array_name} contains non-finite values; "
            f"expected alive-flags in {{0, 1}}"
        )
    bad = raw[(raw != 0) & (raw != 1)]
    if bad.size > 0:
        raise VTUExportError(
            f"frame {frame_name} {array_name} contains values outside "
            f"{{0, 1}}: {sorted({float(v) for v in bad[:5]})}; expected "
            f"alive-flags only"
        )


def _von_mises_voigt6(tens: np.ndarray) -> np.ndarray:
    """Voigt-6 stress → von Mises scalar.

    Input shape ``(n, 6)`` with components ordered
    ``(sxx, syy, szz, syz, sxz, sxy)`` per OpenRadioss convention.
    Output shape ``(n,)`` float32.
    """
    sxx = tens[:, 0]
    syy = tens[:, 1]
    szz = tens[:, 2]
    syz = tens[:, 3]
    sxz = tens[:, 4]
    sxy = tens[:, 5]
    return np.sqrt(
        0.5
        * (
            (sxx - syy) ** 2
            + (syy - szz) ** 2
            + (szz - sxx) ** 2
            + 6.0 * (sxy**2 + syz**2 + sxz**2)
        )
    ).astype(np.float32)


__all__ = [
    "SCHEMA_VERSION",
    "VTUExportError",
    "export_run",
]
