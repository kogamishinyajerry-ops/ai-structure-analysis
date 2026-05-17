"""Gmsh subprocess runner — FM-04a Phase 18 C.

Spawns the real ``gmsh`` binary as a subprocess to mesh a geometry
file (STEP / STL / BREP / GEO) inside a case workspace, producing a
CalculiX-compatible mesh on disk.

Layer split (RFC-001 §4.5):
* This runner is responsible for SUBPROCESS INVOCATION only. It does
  not parse the resulting mesh (that lives in Layer-3 mesh consumers).
* It does not author the mesh INP either — Phase 18 C+ wires
  gmsh-produced meshes into ``calculix.inp_writer`` via a separate
  composition layer.

Tier 2 posture (per Phase 18 blueprint §0): this is the second real
subprocess in the harness (after CalculiX). Tests that exercise this
path carry the ``@pytest.mark.requires_solver`` marker so CI without
``gmsh`` installed can still run the default sweep.

Defense in depth:
* Path-guard — input geometry path must resolve inside the case
  workspace directory; arbitrary paths are refused.
* HF1.7a — signed-registry case-id pattern is refused by the runner
  before any subprocess launch.
* Bounded timeout — every ``run()`` call carries a wall-clock cap;
  long-running gmsh jobs are killed and a ``GmshRunError`` is raised
  rather than wedging the calling process.
* stdout/stderr captured to files — the calling process never reads
  unbounded gmsh chatter.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_GMSH_BINARY: Final[str] = "gmsh"
"""Default binary name. Resolved via PATH unless overridden by the
constructor. Dev box typically has ``/opt/homebrew/bin/gmsh``
(Homebrew Gmsh 4.15+)."""

DEFAULT_TIMEOUT_SEC: Final[float] = 300.0
"""Default wall-clock cap for a single gmsh run."""

DEFAULT_CHARACTERISTIC_LENGTH_M: Final[float] = 0.05
"""Default characteristic mesh length in meters (50 mm). Reasonable
starting point for centimeter-to-meter-scale geometries; finer values
produce more elements + longer ccx runs."""

_SIGNED_REGISTRY_PATTERN = re.compile(r"^GS-\d{3}$")
"""HF1.7a defense — refuses ``case_dir.name`` matching the signed-
registry shape."""

_SUPPORTED_GEOMETRY_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".step", ".stp", ".stl", ".brep", ".geo"}
)
"""File extensions the runner will accept as geometry input. Other
extensions are refused at validation time before any gmsh invocation."""

_DEFAULT_STDOUT_TAIL_BYTES = 8192
_DEFAULT_STDERR_TAIL_BYTES = 8192


class GmshRunError(RuntimeError):
    """Raised when a ``gmsh`` subprocess fails to produce a mesh.

    Carries diagnostics so callers can present an actionable error.
    """

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None,
        stderr_tail: str,
        stdout_tail: str,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr_tail = stderr_tail
        self.stdout_tail = stdout_tail


@dataclass(frozen=True)
class MeshQualityHistogram:
    """A 5-bin histogram over Gmsh's per-element quality (0..1).

    Attributes:
        bin_edges: 6 monotonically increasing edges in [0, 1].
        bin_counts: 5 non-negative integer counts (counts[i] = elements
            with quality in [bin_edges[i], bin_edges[i+1])).
        element_count_total: sum of bin_counts (convenience).
    """

    bin_edges: tuple[float, float, float, float, float, float]
    bin_counts: tuple[int, int, int, int, int]
    element_count_total: int


@dataclass(frozen=True)
class GmshRunResult:
    """Outcome of a single ``gmsh`` subprocess execution.

    Attributes:
        returncode: gmsh's process exit code (0 on success).
        stdout_path: absolute path to the captured stdout log.
        stderr_path: absolute path to the captured stderr log.
        mesh_path: absolute path to the produced mesh file (.msh or
            other format depending on output_format argument).
        node_count: number of nodes in the produced mesh, or None when
            metadata could not be parsed from gmsh stdout.
        element_count: number of volume elements in the produced mesh.
        runtime_sec: wall-clock seconds the subprocess took.
    """

    returncode: int
    stdout_path: Path
    stderr_path: Path
    mesh_path: Path
    node_count: int | None
    element_count: int | None
    runtime_sec: float


class GmshRunner:
    """Spawn ``gmsh`` subprocess to mesh a geometry file.

    Usage:

        runner = GmshRunner()  # uses `gmsh` from PATH
        result = runner.run(
            case_dir=Path("/tmp/case1"),
            geometry_path=Path("/tmp/case1/cylinder.step"),
            output_name="cylinder_mesh",
            characteristic_length_m=0.05,
        )
        # result.mesh_path points to /tmp/case1/cylinder_mesh.msh

    Args:
        gmsh_binary: path or name of the gmsh executable.
        timeout_sec: wall-clock cap; subprocess killed past this.
    """

    def __init__(
        self,
        gmsh_binary: str | Path = DEFAULT_GMSH_BINARY,
        *,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._binary = str(gmsh_binary)
        self._timeout_sec = float(timeout_sec)

    def run(
        self,
        case_dir: Path,
        geometry_path: Path,
        *,
        output_name: str,
        characteristic_length_m: float = DEFAULT_CHARACTERISTIC_LENGTH_M,
        element_order: int = 1,
        output_format: str = "msh22",
    ) -> GmshRunResult:
        """Mesh ``geometry_path`` into ``case_dir/<output_name>.msh``.

        Args:
            case_dir: workspace directory; must exist + be a directory.
            geometry_path: input geometry; must exist and resolve inside
                ``case_dir`` (path-guard defense).
            output_name: stem of the output mesh file (no extension);
                runner appends ``.msh``.
            characteristic_length_m: target mesh edge length in meters.
            element_order: 1 for linear tets (C3D4 in CalculiX), 2 for
                quadratic tets (C3D10). Phase 18 C default = 1.
            output_format: gmsh ``Mesh.Format`` selector. ``msh22`` is
                CalculiX-friendly; ``inp`` writes an Abaqus/CalculiX
                INP directly.

        Raises:
            GmshRunError: on signed-registry refusal, missing geometry,
                path-guard violation, unsupported extension, subprocess
                timeout, or non-zero exit.
        """
        case_dir = Path(case_dir).resolve()
        if _SIGNED_REGISTRY_PATTERN.fullmatch(case_dir.name):
            raise GmshRunError(
                f"refused to run gmsh inside signed-registry case "
                f"{case_dir.name!r} (HF1.7a defense)",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        if not case_dir.is_dir():
            raise GmshRunError(
                f"case_dir {case_dir!s} is not a directory",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        if characteristic_length_m <= 0:
            raise GmshRunError(
                f"characteristic_length_m must be positive; got "
                f"{characteristic_length_m}",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        if element_order not in (1, 2):
            raise GmshRunError(
                f"element_order must be 1 or 2; got {element_order}",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )

        geometry_path = Path(geometry_path).resolve()
        if not geometry_path.is_file():
            raise GmshRunError(
                f"geometry file {geometry_path!s} is missing",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )
        # Path-guard: geometry must resolve inside case_dir.
        try:
            geometry_path.relative_to(case_dir)
        except ValueError as exc:
            raise GmshRunError(
                f"geometry path {geometry_path!s} resolves outside "
                f"case_dir {case_dir!s}; arbitrary paths refused",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            ) from exc
        ext = geometry_path.suffix.lower()
        if ext not in _SUPPORTED_GEOMETRY_EXTENSIONS:
            raise GmshRunError(
                f"unsupported geometry extension {ext!r}; supported = "
                f"{sorted(_SUPPORTED_GEOMETRY_EXTENSIONS)!r}",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            )

        mesh_path = case_dir / f"{output_name}.msh"
        stdout_path = case_dir / f"{output_name}.gmsh.stdout.log"
        stderr_path = case_dir / f"{output_name}.gmsh.stderr.log"

        args = [
            self._binary,
            "-3",  # 3-D mesh generation
            "-clmax",
            f"{characteristic_length_m}",
            "-order",
            str(element_order),
            "-format",
            output_format,
            "-o",
            str(mesh_path),
            str(geometry_path),
        ]

        start = time.monotonic()
        try:
            with (
                stdout_path.open("w", encoding="utf-8") as stdout_f,
                stderr_path.open("w", encoding="utf-8") as stderr_f,
            ):
                completed = subprocess.run(  # noqa: S603 - controlled args
                    args,
                    cwd=str(case_dir),
                    stdout=stdout_f,
                    stderr=stderr_f,
                    timeout=self._timeout_sec,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            runtime = time.monotonic() - start
            raise GmshRunError(
                f"gmsh subprocess timed out after {runtime:.2f}s "
                f"(cap {self._timeout_sec}s) for "
                f"output_name={output_name!r}",
                returncode=None,
                stderr_tail=_safe_tail(stderr_path, _DEFAULT_STDERR_TAIL_BYTES),
                stdout_tail=_safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES),
            ) from exc
        except FileNotFoundError as exc:
            raise GmshRunError(
                f"gmsh binary not found at {self._binary!r}; install "
                f"Gmsh or override the binary path",
                returncode=None,
                stderr_tail="",
                stdout_tail="",
            ) from exc

        runtime = time.monotonic() - start

        if completed.returncode != 0:
            raise GmshRunError(
                f"gmsh exited with returncode {completed.returncode} "
                f"for output_name={output_name!r}",
                returncode=completed.returncode,
                stderr_tail=_safe_tail(stderr_path, _DEFAULT_STDERR_TAIL_BYTES),
                stdout_tail=_safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES),
            )

        if not mesh_path.is_file():
            raise GmshRunError(
                f"gmsh exited 0 but mesh file {mesh_path!s} not found",
                returncode=completed.returncode,
                stderr_tail=_safe_tail(stderr_path, _DEFAULT_STDERR_TAIL_BYTES),
                stdout_tail=_safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES),
            )

        node_count, element_count = _parse_mesh_counts(
            _safe_tail(stdout_path, _DEFAULT_STDOUT_TAIL_BYTES)
        )

        return GmshRunResult(
            returncode=completed.returncode,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            mesh_path=mesh_path,
            node_count=node_count,
            element_count=element_count,
            runtime_sec=runtime,
        )


_NODES_RE = re.compile(r"(\d+)\s+nodes", re.IGNORECASE)
_ELEMENTS_RE = re.compile(r"(\d+)\s+elements", re.IGNORECASE)


def _parse_mesh_counts(stdout_text: str) -> tuple[int | None, int | None]:
    """Extract ``node_count`` and ``element_count`` from gmsh stdout.

    Gmsh prints lines like ``"Info    : 1234 nodes 5678 elements"``
    near the end of a successful mesh generation. We scan the tail
    for the last occurrence of each pattern. Returns ``(None, None)``
    when neither pattern matches (graceful degradation — the mesh
    file itself is the authoritative source).
    """
    node_match = None
    element_match = None
    for line in reversed(stdout_text.splitlines()):
        if node_match is None:
            m = _NODES_RE.search(line)
            if m:
                node_match = int(m.group(1))
        if element_match is None:
            m = _ELEMENTS_RE.search(line)
            if m:
                element_match = int(m.group(1))
        if node_match is not None and element_match is not None:
            break
    return node_match, element_match


def _safe_tail(path: Path, max_bytes: int) -> str:
    """Return the last ``max_bytes`` of ``path`` as utf-8 text.

    Never raises on read failure (returns empty string). Encoding
    errors are replaced rather than raised.
    """
    try:
        size = path.stat().st_size
        offset = max(0, size - max_bytes)
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""
