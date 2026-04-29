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
plus the runtime-checked ``SupportsElementDeletion`` sub-Protocol, since
``CanonicalField`` is a closed enum that cannot be expanded without an RFC.
Layer-3 ballistic derivations (W7d) check the Protocol and read it off the
reader without depending on the concrete adapter type.

ADR-001 narrow carve-out for DISPLACEMENT
-----------------------------------------
ADR-001 forbids Layer-1 adapters from emitting *derived* quantities
(von Mises, principal stress, safety factor, etc.). The OpenRadioss
animation files do not write a DISPLACEMENT field directly — they
write the *deformed* coordinates per frame in ``coorA``. We surface
DISPLACEMENT as ``coorA(step) - coorA(0)``, which is **not** a
derivation in the ADR-001 sense (no constitutive law, no failure
criterion, no calibration). It is a coordinate-frame re-expression of
the same data the file already contains. ADR-021 §Decision pins this
narrow carve-out so future readers don't mistake it for a precedent
for emitting von Mises here.
"""

from __future__ import annotations

import gzip
import re
import shutil
import tempfile
import weakref
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


def _rmtree_safely(path: Path) -> None:
    """Module-level helper so :func:`weakref.finalize` keeps no
    reference to the ``OpenRadiossReader`` instance — if the closure
    captured ``self`` the finalizer would be unable to run on GC.
    """
    with suppress(FileNotFoundError, OSError):
        shutil.rmtree(path)


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


class _ORArrayFieldData:
    """``FieldData`` Protocol for native OpenRadioss arrays.

    This class surfaces raw arrays only. It does not extrapolate,
    average, derive von Mises, or translate part/material semantics.
    Element-located data therefore returns its natural array from
    ``at_nodes()`` as a conservative no-op; Layer 3 must decide whether
    a consumer is allowed to use a non-nodal field.
    """

    def __init__(
        self,
        metadata: FieldMetadata,
        values: "npt.NDArray[np.float64]",
    ) -> None:
        self.metadata = metadata
        self._values = np.asarray(values, dtype=np.float64)

    def values(self) -> "npt.NDArray[np.float64]":
        return self._values.copy()

    def at_nodes(self) -> "npt.NDArray[np.float64]":
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
        #
        # Cleanup safety net (Codex R2 MEDIUM): register
        # ``weakref.finalize`` *immediately* after ``mkdtemp`` succeeds
        # so a failure later in ``__init__`` (first ``_read_frame``
        # raises, gzip is corrupt, etc.) still wipes the scratch dir on
        # GC. Earlier code only installed the finalizer after the first
        # frame had been parsed, leaking the tmpdir on constructor
        # failure. We also try eager cleanup in the failure path so the
        # caller doesn't have to wait for GC.
        self._finalizer: Optional[weakref.finalize] = None
        self._decompressed: dict[int, Path] = {}
        try:
            for idx, p in self._frame_paths.items():
                if p.suffix == ".gz":
                    if self._tmpdir is None:
                        self._tmpdir = Path(
                            tempfile.mkdtemp(prefix="openradioss-")
                        )
                        self._finalizer = weakref.finalize(
                            self, _rmtree_safely, self._tmpdir
                        )
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
            node_ids, n_synth = self._resolve_node_ids(
                a0.get("nodNumA"), int(h0["nbNodes"])
            )
            self._n_synthesized_ids = n_synth
            self._mesh = _ORMesh(coor0, node_ids, unit_system)
        except BaseException:
            # Eager cleanup so the caller doesn't have to wait for GC.
            # ``self._finalizer()`` invokes the underlying callable and
            # detaches it in one step (weakref.finalize semantics), so
            # by the time we re-raise the dir is gone (or the
            # ``_rmtree_safely`` suppress(...) swallowed the failure
            # path). No GC fallback after this point.
            if self._finalizer is not None:
                with suppress(Exception):
                    self._finalizer()
                self._finalizer = None
            self._tmpdir = None
            raise

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
            if self._native_tensor_values(
                a, ("STRESS",), expected_width=6
            ) is not None:
                avail.append(CanonicalField.STRESS_TENSOR)
            if self._native_tensor_values(
                a, ("STRAIN",), expected_width=6
            ) is not None:
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
        if name is CanonicalField.STRESS_TENSOR:
            return self._tensor_field_for(step_id, ("STRESS",), name)
        if name is CanonicalField.STRAIN_TENSOR:
            return self._tensor_field_for(step_id, ("STRAIN",), name)
        return None

    def close(self) -> None:
        if self._closed:
            return
        if self._finalizer is not None:
            # Detach + invoke under our control so we both clean up
            # eagerly *and* prevent the GC finalizer from running again.
            self._finalizer()
            self._finalizer = None
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

    def nodal_velocity_for(
        self, step_id: int
    ) -> "npt.NDArray[np.float64] | None":
        """Return raw nodal velocity vectors when written by OpenRadioss.

        Velocity is not a ``CanonicalField`` member, so it is exposed as
        an optional capability for Layer-3 candidate metrics. ``None``
        means the run did not write a native velocity array; it is not a
        license to fabricate zeros.
        """
        self._check_open()
        if step_id not in self._decompressed:
            raise KeyError(f"unknown step_id {step_id!r}")
        _, arrays = self._read_frame(step_id)
        found = self._native_vector_values(arrays, ("VELOCITY", "VELO"))
        if found is None:
            return None
        values, _, _ = found
        return values.copy()

    def element_part_ids_for(
        self, step_id: int
    ) -> "npt.NDArray[np.int64] | None":
        """Return solver-native element part/material IDs if present.

        The legacy animation files often carry integer labels such as
        ``materialTypeA``. They are useful for projectile/plate
        partitioning, but they are not material cards; this method
        deliberately returns raw IDs only.
        """
        self._check_open()
        if step_id not in self._decompressed:
            raise KeyError(f"unknown step_id {step_id!r}")
        _, arrays = self._read_frame(step_id)
        for key in (
            "partIdA",
            "partIDA",
            "partId3DA",
            "materialTypeA",
            "materialIdA",
            "materialType3DA",
        ):
            raw = arrays.get(key)
            if raw is None:
                continue
            values = np.asarray(raw, dtype=np.int64).reshape(-1)
            if values.size:
                return values.copy()
        return None

    @property
    def rootname(self) -> str:
        return self._rootname

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_node_ids(
        nod_num_raw: Any,
        n_nodes: int,
    ) -> tuple["npt.NDArray[np.int64]", int]:
        """Materialise the node-ID array, repairing only the bad slots.

        OpenRadioss legacy decks pad ``nodNumA`` past ``nbNodes`` with
        zeros (and, occasionally, a duplicate of an earlier slot).
        Earlier W7b iterations replaced the *whole* array with
        ``arange(1, N+1)`` if any slot was bad — Codex R1 (HIGH)
        flagged this as data loss because a perfectly fine partial
        array (e.g. ``[1, 2, 0, 4, 5]``) would be clobbered to
        ``[1, 2, 3, 4, 5]``, silently rewriting valid IDs.

        New behaviour: keep every slot whose ID is non-zero AND has
        not appeared earlier in the array; for each *bad* slot, mint
        a fresh ID strictly greater than ``max(valid_ids)`` + the
        running synth counter, guaranteeing no collision with valid
        IDs even if they were sparse to begin with.

        Returns ``(ids, n_synthesized)``. ``n_synthesized`` is recorded
        on the reader and surfaced in field metadata so a downstream
        consumer can tell synthesised IDs from solver-emitted ones.
        """
        if nod_num_raw is None or len(nod_num_raw) == 0:
            return np.arange(1, n_nodes + 1, dtype=np.int64), n_nodes
        candidate = np.asarray(nod_num_raw, dtype=np.int64)
        # Truncate / extend to nbNodes; pad with zeros (treated as bad).
        if candidate.size < n_nodes:
            pad = np.zeros(n_nodes - candidate.size, dtype=np.int64)
            candidate = np.concatenate([candidate, pad])
        elif candidate.size > n_nodes:
            candidate = candidate[:n_nodes]

        bad = np.zeros(candidate.shape, dtype=bool)
        seen: set[int] = set()
        for i, nid in enumerate(candidate.tolist()):
            if nid == 0 or nid in seen:
                bad[i] = True
            else:
                seen.add(int(nid))
        if not bad.any():
            return candidate.copy(), 0
        valid_max = int(candidate[~bad].max()) if (~bad).any() else 0
        repaired = candidate.copy()
        next_id = valid_max + 1
        for i in np.flatnonzero(bad):
            repaired[i] = next_id
            next_id += 1
        return repaired, int(bad.sum())

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

    @staticmethod
    def _text_labels(raw: Any) -> list[str]:
        if raw is None:
            return []
        arr = np.asarray(raw).reshape(-1)
        labels: list[str] = []
        for item in arr.tolist():
            if isinstance(item, bytes):
                labels.append(item.decode("utf-8", errors="ignore").strip())
            else:
                labels.append(str(item).strip())
        return labels

    @staticmethod
    def _label_index(labels: list[str], needles: tuple[str, ...]) -> int | None:
        for i, label in enumerate(labels):
            upper = label.upper()
            if any(needle in upper for needle in needles):
                return i
        return None

    @staticmethod
    def _slice_labeled_values(
        raw: Any,
        *,
        label_index: int,
        n_labels: int,
        expected_width: int,
    ) -> "npt.NDArray[np.float64] | None":
        arr = np.asarray(raw, dtype=np.float64)
        if arr.size == 0:
            return None
        if arr.ndim == 3:
            # Vortex/lasso arrays normally put the entity axis first and
            # the text-label axis second: (n_entities, n_labels, width).
            # Check that form first so small synthetic fixtures where
            # n_entities == n_labels do not get sliced on the wrong axis.
            if arr.shape[1] == n_labels and arr.shape[2] >= expected_width:
                return np.asarray(
                    arr[:, label_index, :expected_width],
                    dtype=np.float64,
                )
            if arr.shape[0] == n_labels and arr.shape[2] >= expected_width:
                return np.asarray(
                    arr[label_index, :, :expected_width],
                    dtype=np.float64,
                )
            if n_labels == 1 and arr.shape[-1] >= expected_width:
                return np.asarray(
                    arr.reshape(-1, arr.shape[-1])[:, :expected_width],
                    dtype=np.float64,
                )
        if arr.ndim == 2:
            if n_labels == 1 and arr.shape[1] >= expected_width:
                return np.asarray(arr[:, :expected_width], dtype=np.float64)
            if arr.shape[0] == n_labels and arr.shape[1] % expected_width == 0:
                return np.asarray(
                    arr[label_index].reshape(-1, expected_width),
                    dtype=np.float64,
                )
        if arr.ndim == 1 and n_labels == 1 and arr.size % expected_width == 0:
            return np.asarray(arr.reshape(-1, expected_width), dtype=np.float64)
        return None

    def _native_vector_values(
        self, arrays: dict[str, Any], needles: tuple[str, ...]
    ) -> tuple["npt.NDArray[np.float64]", str, str] | None:
        labels = self._text_labels(arrays.get("vTextA"))
        idx = self._label_index(labels, needles)
        if idx is None:
            return None
        for key in ("vectValA", "vectVal3DA", "vValA", "vectorValA"):
            raw = arrays.get(key)
            if raw is None:
                continue
            values = self._slice_labeled_values(
                raw, label_index=idx, n_labels=len(labels), expected_width=3
            )
            if values is not None:
                return values, key, labels[idx]
        return None

    def _native_tensor_values(
        self,
        arrays: dict[str, Any],
        needles: tuple[str, ...],
        *,
        expected_width: int,
    ) -> tuple["npt.NDArray[np.float64]", str, str] | None:
        labels = self._text_labels(arrays.get("tTextA"))
        idx = self._label_index(labels, needles)
        if idx is None:
            return None
        for key in ("tensValA", "tensVal3DA", "tValA", "tensorValA"):
            raw = arrays.get(key)
            if raw is None:
                continue
            values = self._slice_labeled_values(
                raw,
                label_index=idx,
                n_labels=len(labels),
                expected_width=expected_width,
            )
            if values is not None:
                return values, key, labels[idx]
        return None

    def _tensor_field_for(
        self,
        step_id: int,
        needles: tuple[str, ...],
        name: CanonicalField,
    ) -> FieldData | None:
        _, arrays = self._read_frame(step_id)
        found = self._native_tensor_values(
            arrays, needles, expected_width=6
        )
        if found is None:
            return None
        values, key, label = found
        meta = FieldMetadata(
            name=name,
            location=FieldLocation.ELEMENT,
            component_type=ComponentType.TENSOR_SYM_3D,
            unit_system=self._unit_system,
            source_solver=self.SOURCE_SOLVER,
            source_field_name=f"{key}:{label}",
            source_file=self._frame_paths[step_id],
            coordinate_system=CoordinateSystemKind.GLOBAL.value,
            was_averaged=False,
        )
        return _ORArrayFieldData(meta, values)

    def _displacement_for(self, step_id: int) -> _ORVectorFieldData:
        _, a_now = self._read_frame(step_id)
        _, a_ref = self._read_frame(self._first_idx)
        coor_now = np.asarray(a_now["coorA"], dtype=np.float64)
        coor_ref = np.asarray(a_ref["coorA"], dtype=np.float64)
        # Surface ID-synthesis provenance: if any node IDs were minted
        # by the adapter (zeros / duplicates in nodNumA) the field's
        # source_field_name records how many. Codex R1 MEDIUM #5 fix —
        # don't pretend synthesised IDs came from the solver.
        if self._n_synthesized_ids:
            field_name = (
                f"coorA(step)-coorA(0) "
                f"[adapter-synthesised {self._n_synthesized_ids} of "
                f"{self._mesh.node_id_array.size} node IDs]"
            )
        else:
            field_name = "coorA(step)-coorA(0)"
        meta = FieldMetadata(
            name=CanonicalField.DISPLACEMENT,
            location=FieldLocation.NODE,
            component_type=ComponentType.VECTOR_3D,
            unit_system=self._unit_system,
            source_solver=self.SOURCE_SOLVER,
            source_field_name=field_name,
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
