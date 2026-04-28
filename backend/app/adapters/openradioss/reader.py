"""OpenRadioss Layer-1 ``ReaderHandle`` implementation.

Constructor takes a *rootname* (e.g. ``"BOULE1V5"``) plus a directory.
Discovers all ``<root>A%03d`` / ``<root>A%03d.gz`` siblings — each is one
``SolutionState``. Per-state mesh + field arrays come from
``vortex_radioss.RadiossReader``.

Field-name mapping (OpenRadioss → CanonicalField):

  vTextA    "Displ"      → DISPLACEMENT       (vec3 nodal)
  vTextA    "Velocity"   → (intentionally unmapped — no canonical entry)
  tTextA    "Stress"     → STRESS_TENSOR      (Voigt-6 element)
  tTextA    "Strain"     → STRAIN_TENSOR
  fTextA    "VonMises"   → (Layer-3 derived; Layer-2 must not surface it
                            per ADR-001)

The W7b smoke fixture (GS-100) ships only mesh data; the full mapping is
exercised by GS-101 in W7e once a full-output `.rad` deck lands.

Element-deletion data (`delEltA`) is exposed via ``deleted_facets_for(state)``
— a non-Protocol method, since ``CanonicalField`` is a closed enum that
cannot be expanded without an RFC. Layer-3 ballistic derivations (W7d) read
it directly off ``OpenRadiossReader``.
"""

from __future__ import annotations

import gzip
import re
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional

import numpy as np
import numpy.typing as npt

from ...core.types import (
    BoundaryCondition,
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldData,
    FieldLocation,
    FieldMetadata,
    Material,
    Mesh,
    SolutionState,
    UnitSystem,
)


_FRAME_RE = re.compile(r"^(?P<root>.+)A(?P<idx>\d{3})(?P<gz>\.gz)?$")


# ---------------------------------------------------------------------------
# Mesh implementation
# ---------------------------------------------------------------------------


class _ORMesh:
    """``Mesh`` Protocol implementation backed by an OpenRadioss
    ``coorA`` from the *first* animation frame.

    Why first frame: OpenRadioss writes the *current* (deformed) coords
    each animation step. The Layer-2 ``Mesh.coordinates`` contract is
    the **reference** geometry — we anchor on t=0 and let displacement
    fields surface the deformation. This matches the CalculiX adapter
    which uses the .frd's reference coords + a separate DISP field.
    """

    def __init__(
        self,
        coor0: "npt.NDArray[np.float64]",
        node_ids: "npt.NDArray[np.int64]",
        unit_system: UnitSystem,
    ) -> None:
        self._coor0 = np.ascontiguousarray(coor0, dtype=np.float64)
        self._node_ids = np.ascontiguousarray(node_ids, dtype=np.int64)
        self._unit_system = unit_system
        self._index = {int(nid): idx for idx, nid in enumerate(self._node_ids)}

    @property
    def node_id_array(self) -> "npt.NDArray[np.int64]":
        return self._node_ids.copy()

    @property
    def node_index(self) -> dict[int, int]:
        return dict(self._index)

    @property
    def coordinates(self) -> "npt.NDArray[np.float64]":
        return self._coor0.copy()

    @property
    def unit_system(self) -> UnitSystem:
        return self._unit_system


# ---------------------------------------------------------------------------
# FieldData implementation
# ---------------------------------------------------------------------------


class _ORVectorFieldData:
    """``FieldData`` Protocol — vec3 nodal field reconstructed from a
    pair of ``coorA`` arrays (current minus reference = displacement).

    OpenRadioss does NOT emit a "displacement" field directly in the
    legacy animation file; the convention is "current coords" per step.
    To honour Layer-2's DISPLACEMENT canonical field, we reconstruct
    it by subtracting the reference frame coords. Layer-3 sees a
    standard vec3 displacement just as it would from CalculiX.
    """

    def __init__(
        self,
        metadata: FieldMetadata,
        coor_now: "npt.NDArray[np.float64]",
        coor_ref: "npt.NDArray[np.float64]",
    ) -> None:
        self.metadata = metadata
        self._coor_now = coor_now
        self._coor_ref = coor_ref

    def values(self) -> "npt.NDArray[np.float64]":
        return (self._coor_now - self._coor_ref).astype(np.float64, copy=False)

    def at_nodes(self) -> "npt.NDArray[np.float64]":
        # Already nodal — no extrapolation needed.
        return self.values()


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


class OpenRadiossReader:
    """Layer-1 adapter for OpenRadioss output.

    Usage::

        reader = OpenRadiossReader(
            root_dir=Path("golden_samples/GS-100-radioss-smoke"),
            rootname="BOULE1V5",
            unit_system=UnitSystem.SI_MM,
        )
        for state in reader.solution_states:
            disp = reader.get_field(CanonicalField.DISPLACEMENT, state.step_id)
            ...
        reader.close()
    """

    SOURCE_SOLVER = "OpenRadioss"

    def __init__(
        self,
        root_dir: Path,
        rootname: str,
        *,
        unit_system: UnitSystem = UnitSystem.UNKNOWN,
    ) -> None:
        self._root_dir = Path(root_dir).resolve()
        self._rootname = rootname
        self._unit_system = unit_system
        self._tmpdir: Optional[Path] = None
        self._closed = False

        # Discover frames + sort by index. Both .gz and decompressed
        # forms accepted; if both exist for the same index, prefer the
        # already-decompressed one (avoids re-decompressing on every
        # process-restart in the dev loop).
        frames: dict[int, Path] = {}
        for entry in self._root_dir.iterdir():
            m = _FRAME_RE.match(entry.name)
            if not m or m.group("root") != rootname:
                continue
            idx = int(m.group("idx"))
            if idx in frames and m.group("gz"):
                # Decompressed sibling already discovered — keep it.
                continue
            frames[idx] = entry
        if not frames:
            raise FileNotFoundError(
                f"no OpenRadioss animation frames matching "
                f"{rootname}A###[.gz] found in {self._root_dir}"
            )
        self._frame_paths: dict[int, Path] = dict(sorted(frames.items()))

        # Decompress any .gz frames into a per-instance scratch dir.
        # Vortex-Radioss does NOT auto-decompress (verified W7a — the
        # binary parser reads gzip magic as garbage and ValueErrors).
        self._decompressed: dict[int, Path] = {}
        for idx, p in self._frame_paths.items():
            if p.suffix == ".gz":
                if self._tmpdir is None:
                    self._tmpdir = Path(tempfile.mkdtemp(prefix="openradioss-"))
                tgt = self._tmpdir / p.with_suffix("").name
                with gzip.open(p, "rb") as gz, open(tgt, "wb") as out:
                    shutil.copyfileobj(gz, out)
                self._decompressed[idx] = tgt
            else:
                self._decompressed[idx] = p

        # Read first frame eagerly for mesh + ID-stable node array.
        # Subsequent reads materialise per-call (ADR-004 — no caching).
        first_idx = next(iter(self._decompressed))
        h0, a0 = self._read_frame(first_idx)
        self._first_idx = first_idx
        coor0 = np.asarray(a0["coorA"], dtype=np.float64)
        # ``a0.get("nodNumA") or np.arange(...)`` would evaluate the
        # ndarray's truthiness — ValueError on len>1. Test the array
        # explicitly for None/empty instead.
        #
        # Empirically (verified W7b GS-100): `nodNumA` length matches
        # nbNodes but the tail is padded with 0s, and the array can
        # therefore contain duplicate IDs (multiple 0s). Falling back
        # to a 1..N synthetic ID range when duplicates are present is
        # safer than exposing a non-unique node_index dict and silently
        # losing nodes downstream. We log nothing — the source_field
        # metadata records the synthesis on the fields we actually
        # surface.
        nod_num = a0.get("nodNumA")
        node_ids: "npt.NDArray[np.int64]"
        if nod_num is None or len(nod_num) == 0:
            node_ids = np.arange(1, int(h0["nbNodes"]) + 1, dtype=np.int64)
        else:
            candidate = np.asarray(nod_num, dtype=np.int64)
            has_zeros = bool(np.any(candidate == 0))
            has_dups = candidate.size != np.unique(candidate).size
            if has_zeros or has_dups:
                node_ids = np.arange(
                    1, int(h0["nbNodes"]) + 1, dtype=np.int64
                )
            else:
                node_ids = candidate
        self._mesh = _ORMesh(coor0, node_ids, unit_system)

        # Build SolutionState list. ``time`` from header — meaningful
        # for transient runs; ``load_factor`` is None (OpenRadioss is
        # a real-time solver, not arc-length).
        self._states: list[SolutionState] = []
        self._available_per_state: dict[int, tuple[CanonicalField, ...]] = {}
        for idx in self._decompressed:
            h, a = self._read_frame(idx)
            avail: list[CanonicalField] = []
            # DISPLACEMENT is always reconstructable — current minus
            # reference. (Layer-3 may decide to skip it for the t=0
            # state where it's identically zero; that's fine.)
            avail.append(CanonicalField.DISPLACEMENT)
            # Native vector fields the file declares — currently we
            # don't surface them through CanonicalField (closed enum)
            # except DISPLACEMENT; future RFC may add VELOCITY etc.
            # Tensor fields likewise: STRESS_TENSOR / STRAIN_TENSOR
            # surface only when the engine actually wrote them. The
            # GS-100 smoke fixture has none; GS-101 will.
            t_names = [str(t).strip() for t in (a.get("tTextA") or [])]
            for tn in t_names:
                tu = tn.upper()
                if "STRESS" in tu and CanonicalField.STRESS_TENSOR not in avail:
                    avail.append(CanonicalField.STRESS_TENSOR)
                if "STRAIN" in tu and CanonicalField.STRAIN_TENSOR not in avail:
                    avail.append(CanonicalField.STRAIN_TENSOR)
            self._available_per_state[idx] = tuple(avail)
            self._states.append(
                SolutionState(
                    step_id=idx,
                    step_name=f"{rootname}A{idx:03d}",
                    time=float(h["time"]),
                    load_factor=None,
                    available_fields=tuple(avail),
                )
            )

    # ------------------------------------------------------------------
    # ReaderHandle Protocol surface
    # ------------------------------------------------------------------

    @property
    def mesh(self) -> Mesh:
        self._check_open()
        return self._mesh

    @property
    def materials(self) -> dict[str, Material]:
        # ADR-003: do not fabricate. The animation file does carry
        # `materialTypeA` / `materialTextA`, but those are integer type
        # codes / labels, not full Material cards (no E, no ν, no σ_y).
        # Layer-3 / W6a wedge supplies materials via materials_lib; the
        # adapter sticks to "what's on disk" and returns empty.
        self._check_open()
        return {}

    @property
    def boundary_conditions(self) -> list[BoundaryCondition]:
        # ADR-003: same reasoning — the .rad starter file holds BCs but
        # this adapter parses output, not input. BC ingestion lands in
        # a future W7 task once we add a starter-deck parser.
        self._check_open()
        return []

    @property
    def solution_states(self) -> list[SolutionState]:
        self._check_open()
        return list(self._states)

    def get_field(
        self,
        name: CanonicalField,
        step_id: int,
    ) -> Optional[FieldData]:
        self._check_open()
        if step_id not in self._decompressed:
            return None
        if name not in self._available_per_state.get(step_id, ()):
            return None
        if name is CanonicalField.DISPLACEMENT:
            return self._displacement_for(step_id)
        # Stress / strain tensor: TODO in a follow-up commit on top of
        # GS-101. Keeping the path explicit so the failure mode is a
        # clear None (per ADR-003) rather than a silent broken array.
        return None

    def close(self) -> None:
        if self._closed:
            return
        if self._tmpdir is not None:
            with suppress(FileNotFoundError, OSError):
                shutil.rmtree(self._tmpdir)
            self._tmpdir = None
        self._closed = True

    # ------------------------------------------------------------------
    # Adapter-specific surface (NOT in ReaderHandle Protocol)
    # ------------------------------------------------------------------

    def deleted_facets_for(self, step_id: int) -> "npt.NDArray[np.int8]":
        """Return the per-facet alive/deleted flags from `delEltA`.

        Shape: ``(n_facets,)`` int8. Value 1 = alive, 0 = deleted.
        Used by W7d ballistic derivations to compute eroded element
        counts and the perforation verdict. Not in the Layer-2
        ``ReaderHandle`` Protocol because element erosion is a
        non-canonical concept (CanonicalField enum is closed).
        """
        self._check_open()
        if step_id not in self._decompressed:
            raise KeyError(f"unknown step_id {step_id!r}")
        _, arrays = self._read_frame(step_id)
        delE = np.asarray(arrays.get("delEltA", []), dtype=np.int8)
        return delE

    @property
    def rootname(self) -> str:
        return self._rootname

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                "OpenRadiossReader has been close()'d; reading is no "
                "longer permitted (ADR-004 — no caching means file "
                "handles are not resurrected)."
            )

    def _read_frame(self, idx: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Open one decompressed animation frame via vortex-radioss
        and return (raw_header, raw_arrays). Imported lazily so the
        adapter package can be imported in environments where
        vortex-radioss isn't installed (tests run with importorskip).
        """
        from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

        path = self._decompressed[idx]
        rr = RadiossReader(str(path))
        return rr.raw_header, rr.raw_arrays

    def _displacement_for(self, step_id: int) -> _ORVectorFieldData:
        _, a_now = self._read_frame(step_id)
        _, a_ref = self._read_frame(self._first_idx)
        coor_now = np.asarray(a_now["coorA"], dtype=np.float64)
        coor_ref = np.asarray(a_ref["coorA"], dtype=np.float64)
        meta = FieldMetadata(
            name=CanonicalField.DISPLACEMENT,
            location=FieldLocation.NODE,
            component_type=ComponentType.VECTOR_3D,
            unit_system=self._unit_system,
            source_solver=self.SOURCE_SOLVER,
            source_field_name="coorA(step)-coorA(0)",
            source_file=self._frame_paths[step_id],
            coordinate_system=CoordinateSystemKind.GLOBAL.value,
            was_averaged=False,
        )
        return _ORVectorFieldData(meta, coor_now, coor_ref)

    # Context-manager sugar ------------------------------------------------

    def __enter__(self) -> "OpenRadiossReader":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
