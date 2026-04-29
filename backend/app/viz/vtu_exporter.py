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
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

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
    # Lazy imports — pyvista pulls vtk; vortex_radioss pulls lasso. We
    # don't want either at module-import time so a ``--doctor`` probe
    # can introspect this module without a graphics stack.
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

    # Codex R1 HIGH on PR #111 — the manifest keys ``time_ms`` and
    # ``max_displacement_mm`` are unit-bearing, but the parameter
    # accepts arbitrary UnitSystem values. Until the schema grows
    # explicit per-key units (e.g. via a ``units: {time: "ms", ...}``
    # block, deferred to W8a-units), the only honest contract is to
    # refuse non-si-mm runs rather than silently mislabel them. The
    # OpenRadioss adapter in W7b is itself si-mm-only, so this is not
    # a regression of any user flow today — it just locks the contract
    # so a future ADR-003 violation cannot slip in via a different
    # ``UnitSystem`` value.
    if unit_system is not UnitSystem.SI_MM:
        raise VTUExportError(
            f"viewport export currently only supports SI_MM; got "
            f"{unit_system.value}. Multi-unit manifest schema is "
            f"planned for W8a-units."
        )

    if not openradioss_root.is_dir():
        raise VTUExportError(
            f"OpenRadioss root is not a directory: {openradioss_root}"
        )

    frames = _enumerate_frames(openradioss_root, rootname)
    if not frames:
        raise VTUExportError(
            f"no animation frames found at {openradioss_root}/{rootname}A* "
            f"(checked plain and .gz). Did the engine run terminate normally?"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    states_dir = output_dir / "states"
    states_dir.mkdir(exist_ok=True)

    # Decompress frames into a scratch dir so RadiossReader can mmap
    # them. We do this once for the whole run rather than per-state to
    # amortise the gzip cost.
    with tempfile.TemporaryDirectory(prefix="vtu-export-") as scratch_str:
        scratch = Path(scratch_str)
        decompressed = _decompress_frames_to(scratch, frames)

        # First frame anchors the reference coordinates for displacement.
        ref_reader = RadiossReader(str(decompressed[0]))
        ref_coords = np.asarray(
            ref_reader.raw_arrays["coorA"], dtype=np.float64
        )
        ref_header = ref_reader.raw_header
        n_solids_total = int(ref_header["nbElts3D"])
        n_facets_total = int(ref_header["nbFacets"])
        n_nodes = int(ref_header["nbNodes"])

        records: list[_StateRecord] = []
        available_fields: set[str] = set()

        for state_idx, frame_path in enumerate(decompressed, start=1):
            reader = RadiossReader(str(frame_path))
            arrays = reader.raw_arrays
            header = reader.raw_header
            time_ms = float(header["time"])

            coords = np.asarray(arrays["coorA"], dtype=np.float64)
            if coords.shape != (n_nodes, 3):
                raise VTUExportError(
                    f"frame {frame_path.name} node count {coords.shape[0]} "
                    f"differs from reference {n_nodes}; mesh topology "
                    f"changed mid-run, which the viewport contract forbids"
                )

            disp = coords - ref_coords
            disp_mag = np.linalg.norm(disp, axis=1)

            # Build a single UnstructuredGrid combining 3D bricks and
            # 2D facets — vtk.js can read mixed cell types in one VTU.
            connect_3d = np.asarray(arrays["connect3DA"], dtype=np.int64)
            connect_2d = np.asarray(arrays["connectA"], dtype=np.int64)

            # Codex R2 HIGH on PR #111 — validate the deletion arrays
            # carry only the documented {0, 1} values BEFORE casting
            # to bool. Direct ``dtype=bool`` coercion silently treats
            # any non-zero (e.g. 2, -1 from a corrupt parse) as "alive",
            # which would let parser drift contaminate the manifest's
            # alive counts and the VTU's per-cell ``alive`` array
            # without raising. Layer-3 ballistics already uses the same
            # contract (app/domain/ballistics/__init__.py:_validate_flags).
            _validate_deletion_flags(
                arrays["delElt3DA"], "delElt3DA", frame_path.name
            )
            _validate_deletion_flags(
                arrays["delEltA"], "delEltA", frame_path.name
            )
            del_3d = np.asarray(arrays["delElt3DA"], dtype=bool)
            del_2d = np.asarray(arrays["delEltA"], dtype=bool)

            # Codex R1 HIGH on PR #111 — assert connectivity / deletion
            # array lengths agree with the header BEFORE assembling the
            # grid. The previous ``zip(..., strict=False)`` silently
            # truncated to the shorter array, so a length drift would
            # drop cells from the VTU while the manifest still reported
            # the full header counts. That is a data-integrity bug for
            # the viewport — refuse the frame instead.
            if connect_3d.shape[0] != n_solids_total:
                raise VTUExportError(
                    f"frame {frame_path.name} solid connectivity rows "
                    f"({connect_3d.shape[0]}) differ from reference "
                    f"nbElts3D ({n_solids_total}); mesh topology "
                    f"changed mid-run, viewport contract forbids."
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
                    f"nbFacets ({n_facets_total}); mesh topology "
                    f"changed mid-run, viewport contract forbids."
                )
            if del_2d.shape[0] != n_facets_total:
                raise VTUExportError(
                    f"frame {frame_path.name} facet delElt array length "
                    f"({del_2d.shape[0]}) differs from nbFacets "
                    f"({n_facets_total})."
                )

            # pyvista cells layout: [n_pts_in_cell, p0, p1, ..., n_pts_in_cell, ...]
            # Lengths are pinned by the asserts above; ``strict=True``
            # makes the contract explicit and any future regression
            # surfaces as a clean ValueError instead of a silent drop.
            cells_blocks: list[np.ndarray] = []
            cell_types: list[int] = []
            cell_alive: list[bool] = []
            cell_kind: list[int] = []  # 0 = solid (brick), 1 = facet (quad)

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
            grid = pv.UnstructuredGrid(
                cells, np.array(cell_types, dtype=np.uint8), coords
            )

            # Per-point fields.
            grid.point_data["displacement"] = disp.astype(np.float32)
            grid.point_data["displacement_magnitude"] = disp_mag.astype(np.float32)
            available_fields.update(["displacement", "displacement_magnitude"])

            # Per-cell fields. Plastic strain is the only scalar
            # OpenRadioss writes uniformly across solids and facets;
            # we concatenate solid then facet to match cell ordering.
            efunc_solid = np.asarray(arrays.get("eFunc3DA"), dtype=np.float32)
            efunc_shell = np.asarray(arrays.get("eFuncA"), dtype=np.float32)
            if efunc_solid.size == n_solids_total and efunc_shell.size == n_facets_total:
                grid.cell_data["plastic_strain"] = np.concatenate(
                    [efunc_solid, efunc_shell]
                )
                available_fields.add("plastic_strain")

            # vmises_solid: Voigt-6 → von Mises for the brick cells.
            tens_3d = np.asarray(arrays.get("tensVal3DA"), dtype=np.float32)
            if tens_3d.shape == (n_solids_total, 6):
                vm_solid = _von_mises_voigt6(tens_3d)
                # Pad with NaN for the facet cells so the array length
                # matches total cell count. NaN signals "not applicable
                # for this cell kind"; vtk.js skips NaN in colormap.
                vm_full = np.full(
                    n_solids_total + n_facets_total, np.nan, dtype=np.float32
                )
                vm_full[:n_solids_total] = vm_solid
                grid.cell_data["vmises_solid"] = vm_full
                available_fields.add("vmises_solid")

            # Always write alive + kind so the viewport can hide dead
            # cells (element-deletion view) and colour by part type.
            grid.cell_data["alive"] = np.array(cell_alive, dtype=np.uint8)
            grid.cell_data["cell_kind"] = np.array(cell_kind, dtype=np.uint8)
            available_fields.update(["alive", "cell_kind"])

            vtu_path = states_dir / f"{rootname}_state_{state_idx:03d}.vtu"
            grid.save(str(vtu_path))

            records.append(
                _StateRecord(
                    step_id=state_idx,
                    time_ms=time_ms,
                    vtu_relpath=f"states/{vtu_path.name}",
                    max_displacement_mm=float(disp_mag.max()),
                    n_solids_alive=int(del_3d.sum()),
                    n_solids_total=n_solids_total,
                    n_facets_alive=int(del_2d.sum()),
                    n_facets_total=n_facets_total,
                )
            )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "rootname": rootname,
        "unit_system": unit_system.value,
        "n_states": len(records),
        "available_fields": sorted(available_fields),
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
            for r in records
        ],
    }
    manifest_path = output_dir / "viewport_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


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
        if step in candidates:
            raise VTUExportError(
                f"ambiguous frame {step}: both {candidates[step].name} "
                f"and {name} present"
            )
        candidates[step] = entry
    return [candidates[k] for k in sorted(candidates)]


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
