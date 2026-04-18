"""P1-01 toolchain probes.

Verifies that the container / dev environment exposes the three external
components the engine depends on:

  * ``ccx`` — CalculiX 2.21 main solver (ADR-002).
  * ``gmsh`` Python bindings — meshing.
  * ``FreeCAD`` Python module — geometry.

Outside the P1-01 container these probes ``skip`` by default so the
local dev loop keeps working. Inside CI / container we set
``AI_FEA_IN_CONTAINER=1`` and the same probes convert skips into hard
failures.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

IN_CONTAINER = os.getenv("AI_FEA_IN_CONTAINER", "").strip().lower() in {"1", "true", "yes"}

#
# ADR-002 specifies CalculiX 2.21 as the approval target. Debian bookworm
# main ships calculix-ccx 2.20; trixie has no installation candidate.
# The P1-01 baseline ships 2.20 from Debian bookworm (honest reporting
# via manifest.tool_versions per ADR-008 N-3); upgrading the shipped
# binary to 2.21 via source-build is a follow-up task, not a P1-01 gate.
# Probe floor is therefore 2.20, not exact-match 2.21.
_MIN_CCX_VERSION = (2, 20)


def _require(reason: str) -> None:
    """In-container: fail hard. Elsewhere: skip."""
    if IN_CONTAINER:
        pytest.fail(reason)
    pytest.skip(reason)


def test_ccx_on_path_and_version():
    ccx = shutil.which("ccx")
    if ccx is None:
        _require("ccx not on PATH — P1-01 base image missing CalculiX")
        return

    proc = subprocess.run([ccx, "-v"], capture_output=True, text=True, timeout=30)
    combined = (proc.stdout + proc.stderr).strip()
    match = re.search(r"Version\s+([0-9]+)\.([0-9]+)", combined)
    assert match, f"ccx -v produced unparseable output: {combined!r}"
    major, minor = int(match.group(1)), int(match.group(2))
    assert (major, minor) >= _MIN_CCX_VERSION, (
        f"CalculiX {major}.{minor} is below floor {_MIN_CCX_VERSION[0]}.{_MIN_CCX_VERSION[1]} "
        "— P1-01 ships Debian's calculix-ccx; upgrade to 2.21 is tracked "
        "as a follow-up task per ADR-008 N-3."
    )


def test_gmsh_python_bindings_available():
    try:
        import gmsh  # noqa: F401
    except ImportError:
        _require("gmsh Python bindings missing — install via P1-01 image")
        return

    import gmsh

    gmsh.initialize()
    try:
        assert hasattr(gmsh, "model")
        assert hasattr(gmsh, "option")
    finally:
        gmsh.finalize()


def test_freecad_python_module_available():
    try:
        import FreeCAD  # type: ignore  # noqa: F401
    except ImportError:
        _require("FreeCAD Python module missing — install via P1-01 image")
        return

    import FreeCAD  # type: ignore

    assert hasattr(FreeCAD, "Version")


def test_freecad_driver_flag_is_consistent_with_import():
    """The module-level flag and the real import must agree."""
    import tools.freecad_driver as drv

    try:
        import FreeCAD  # type: ignore  # noqa: F401

        real_available = True
    except ImportError:
        real_available = False

    assert drv.FREECAD_AVAILABLE is real_available
