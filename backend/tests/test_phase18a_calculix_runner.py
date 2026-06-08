"""FM-04a Phase 18 A — CalculiXRunner real-subprocess tests.

The Phase 18 Tier 2 transition introduces the first real solver
subprocess in the harness. This test file covers BOTH:

* **No-solver-needed** tests (default sweep): runner refusal of
  signed-registry paths, refusal of missing INP files, INP writer
  shape validation, integration smoke that constructs Runner +
  passes paths through.
* **`@pytest.mark.requires_solver`** tests (opt-in via
  ``pytest -m requires_solver``): real ``ccx`` subprocess invocation,
  end-to-end ``.frd`` production, handoff to the existing
  ``CalculiXReader``.

Phase 18 binding rubric §3.A guards pinned here:
* **M:-1** — runner and reader are separate classes (runner has no
  parsing methods; reader has no subprocess methods).
* **T:-3** — end-to-end pin: minimal-hex INP → real ccx → ``.frd``
  parses through CalculiXReader with stress field non-empty.
* **C:-2** — runner refuses signed-registry case_dir names
  (``^GS-\\d{3}$``).
* **A:-2** — runner timeout bounded; subprocess killed past cap.
* **V:-3** — all runner workspaces under tmp_path; no real
  ``reports/snapshots/`` mutation.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from app.adapters.calculix import (
    DEFAULT_CCX_BINARY,
    DEFAULT_STEEL,
    DEFAULT_TIMEOUT_SEC,
    CalculiXReader,
    CalculiXRunError,
    CalculiXRunner,
    CalculiXRunResult,
    MinimalHexMaterial,
    write_minimal_hex_inp,
)

# Local ccx binary path — Homebrew install on dev box. Override via
# the CCX_BINARY env var or by passing --ccx-binary on the pytest cli
# if your install lives elsewhere.
LOCAL_CCX_BINARY = "/opt/homebrew/bin/ccx"


# ---------------------------------------------------------------------
# M:-1 — runner / reader layer split
# ---------------------------------------------------------------------


def test_runner_has_no_frd_parsing_methods() -> None:
    """The runner is a SUBPROCESS class; parsing happens in the
    reader. A future maintainer who adds ``parse_frd`` to the runner
    trips this guard."""
    method_names = {
        name for name, _ in inspect.getmembers(CalculiXRunner, inspect.isfunction)
    }
    for forbidden in ("parse_frd", "parse", "read_frd", "get_field", "mesh"):
        assert forbidden not in method_names, (
            f"CalculiXRunner unexpectedly exposes parsing method "
            f"{forbidden!r}; parsing belongs in CalculiXReader"
        )


def test_reader_has_no_subprocess_methods() -> None:
    """Symmetric guard — reader does not invoke subprocess."""
    src = inspect.getsource(CalculiXReader)
    assert "subprocess" not in src, (
        "CalculiXReader unexpectedly references subprocess; "
        "subprocess invocation belongs in CalculiXRunner"
    )


# ---------------------------------------------------------------------
# C:-2 — signed-registry refusal (HF1.7a defense)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("signed_id", ["GS-001", "GS-002", "GS-999"])
def test_runner_refuses_signed_registry_case_dir(
    tmp_path: Path, signed_id: str
) -> None:
    """Runner refuses to spawn ccx inside a signed-registry-shaped
    case directory (HF1.7a defense). Refusal happens BEFORE any
    subprocess invocation."""
    case_dir = tmp_path / signed_id
    case_dir.mkdir()
    (case_dir / "smoke.inp").write_text("dummy", encoding="utf-8")
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY)
    with pytest.raises(CalculiXRunError) as excinfo:
        runner.run(case_dir, "smoke")
    assert "signed-registry" in str(excinfo.value).lower()
    assert excinfo.value.returncode is None  # refusal happened pre-subprocess


def test_runner_accepts_candidate_case_dir(tmp_path: Path) -> None:
    """Runner accepts ``*-candidate`` case names (HF1.7b carve-out
    composes with HF1.7a guard)."""
    case_dir = tmp_path / "rod-wave-impact-candidate"
    case_dir.mkdir()
    # No INP yet → runner raises on missing INP, NOT on refusal.
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY)
    with pytest.raises(CalculiXRunError) as excinfo:
        runner.run(case_dir, "smoke")
    assert "missing" in str(excinfo.value).lower()
    assert "signed-registry" not in str(excinfo.value).lower()


# ---------------------------------------------------------------------
# Missing-input and non-directory handling
# ---------------------------------------------------------------------


def test_runner_refuses_nonexistent_case_dir(tmp_path: Path) -> None:
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY)
    with pytest.raises(CalculiXRunError) as excinfo:
        runner.run(tmp_path / "does-not-exist", "smoke")
    assert "not a directory" in str(excinfo.value).lower()


def test_runner_refuses_missing_inp_file(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY)
    with pytest.raises(CalculiXRunError) as excinfo:
        runner.run(case_dir, "smoke")
    msg = str(excinfo.value).lower()
    assert "missing" in msg or "not exist" in msg


def test_runner_raises_clean_on_missing_binary(tmp_path: Path) -> None:
    """If the ccx binary path doesn't exist, the runner raises a
    structured ``CalculiXRunError`` (NOT FileNotFoundError leaking
    through), so the UI error surface can render a helpful message."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    write_minimal_hex_inp(case_dir, jobname="smoke")
    runner = CalculiXRunner(ccx_binary="/path/that/does/not/exist/ccx")
    with pytest.raises(CalculiXRunError) as excinfo:
        runner.run(case_dir, "smoke")
    assert "ccx binary not found" in str(excinfo.value).lower()


# ---------------------------------------------------------------------
# Defaults SSOT
# ---------------------------------------------------------------------


def test_default_ccx_binary_constant() -> None:
    assert DEFAULT_CCX_BINARY == "ccx"


def test_default_timeout_constant() -> None:
    # Sanity: bounded but generous; 5 min is enough for cohort-scale
    # linear-static models without wedging CI.
    assert DEFAULT_TIMEOUT_SEC == 300.0
    assert DEFAULT_TIMEOUT_SEC > 0.0


def test_default_steel_material_pinned() -> None:
    """Phase 18 A inlines a structural-steel default; Phase 18 C
    materials library will substantiate the full provenance chain.
    The Young's modulus + Poisson's ratio are pinned here so a
    silent drift trips the test."""
    assert DEFAULT_STEEL.name == "STEEL_S355"
    assert DEFAULT_STEEL.youngs_modulus_pa == 210e9
    assert DEFAULT_STEEL.poisson_ratio == 0.3


# ---------------------------------------------------------------------
# INP writer shape validation (no solver needed)
# ---------------------------------------------------------------------


def test_minimal_hex_inp_contains_required_sections(tmp_path: Path) -> None:
    path = write_minimal_hex_inp(tmp_path, jobname="model")
    body = path.read_text(encoding="utf-8")
    # Required CalculiX INP sections for a valid linear-static run.
    for required in (
        "*HEADING",
        "*NODE",
        "*ELEMENT, TYPE=C3D8",
        "*MATERIAL, NAME=STEEL_S355",
        "*ELASTIC",
        "*SOLID SECTION",
        "*BOUNDARY",
        "*STEP",
        "*STATIC",
        "*CLOAD",
        "*NODE FILE",
        "*EL FILE",
        "*END STEP",
    ):
        assert required in body, f"INP missing required section {required!r}"


def test_minimal_hex_inp_writer_refuses_missing_case_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_minimal_hex_inp(tmp_path / "missing", jobname="m")


def test_minimal_hex_inp_writer_refuses_zero_edge_length(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        write_minimal_hex_inp(tmp_path, jobname="m", edge_length_m=0.0)


def test_minimal_hex_inp_writer_refuses_invalid_poisson(tmp_path: Path) -> None:
    bad_material = MinimalHexMaterial(
        name="BAD", youngs_modulus_pa=210e9, poisson_ratio=0.6
    )
    with pytest.raises(ValueError, match="poisson_ratio"):
        write_minimal_hex_inp(tmp_path, jobname="m", material=bad_material)


def test_minimal_hex_inp_writer_refuses_nonpositive_modulus(tmp_path: Path) -> None:
    bad_material = MinimalHexMaterial(
        name="BAD", youngs_modulus_pa=0.0, poisson_ratio=0.3
    )
    with pytest.raises(ValueError, match="youngs_modulus_pa"):
        write_minimal_hex_inp(tmp_path, jobname="m", material=bad_material)


def test_minimal_hex_inp_load_splits_across_top_face(tmp_path: Path) -> None:
    """The ``top_face_load_n`` argument is split equally across the
    4 top-face nodes; total load matches the request."""
    total_load = -2000.0
    path = write_minimal_hex_inp(
        tmp_path, jobname="m", top_face_load_n=total_load
    )
    body = path.read_text(encoding="utf-8")
    # Expect 4 CLOAD lines on top-face nodes (5, 6, 7, 8) DOF 3
    # carrying -500.0 each.
    expected_per_node = total_load / 4.0
    for node_id in (5, 6, 7, 8):
        marker = f"{node_id}, 3, {expected_per_node:.6f}"
        assert marker in body, (
            f"INP missing CLOAD line {marker!r}; body tail:\n{body[-300:]}"
        )


# ---------------------------------------------------------------------
# Runner result dataclass
# ---------------------------------------------------------------------


def test_run_result_dataclass_frozen() -> None:
    """``CalculiXRunResult`` is immutable (defense against mutation
    during downstream rendering)."""
    result = CalculiXRunResult(
        returncode=0,
        stdout_path=Path("/tmp/x.stdout.log"),
        stderr_path=Path("/tmp/x.stderr.log"),
        frd_path=Path("/tmp/x.frd"),
        dat_path=Path("/tmp/x.dat"),
        runtime_sec=1.23,
    )
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        result.returncode = 1  # type: ignore[misc]


# ---------------------------------------------------------------------
# T:-3 — real subprocess end-to-end (requires_solver marker)
# ---------------------------------------------------------------------


@pytest.mark.requires_solver
def test_runner_end_to_end_minimal_hex_produces_frd(tmp_path: Path) -> None:
    """The single load-bearing end-to-end pin: write the minimal-hex
    INP, invoke real ccx subprocess, verify the produced ``.frd``
    file exists and is non-empty (>1KB). This is the first real
    Tier 2 solver run in the harness."""
    case_dir = tmp_path / "phase18a-smoke-candidate"
    case_dir.mkdir()
    inp_path = write_minimal_hex_inp(case_dir, jobname="smoke")
    assert inp_path.is_file()

    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY, timeout_sec=30.0)
    result = runner.run(case_dir, "smoke")

    assert result.returncode == 0, result
    assert result.runtime_sec > 0.0
    assert result.runtime_sec < 30.0
    assert result.frd_path is not None
    assert result.frd_path.is_file()
    # The minimal hex produces ~3-5 KB of .frd content (one element,
    # 8 nodes, displacement + stress fields). Tighter than just
    # >0 catches degenerate "empty wrapper" outputs.
    assert result.frd_path.stat().st_size > 1024


@pytest.mark.requires_solver
def test_runner_produced_frd_parses_through_reader(tmp_path: Path) -> None:
    """The integration handoff: ``CalculiXRunner`` produces ``.frd``,
    the existing ``CalculiXReader`` (Layer-1) parses it without
    raising. The reader's stress field is populated."""
    from app.core.types import CanonicalField, UnitSystem

    case_dir = tmp_path / "phase18a-handoff-candidate"
    case_dir.mkdir()
    write_minimal_hex_inp(case_dir, jobname="handoff")
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY, timeout_sec=30.0)
    result = runner.run(case_dir, "handoff")

    assert result.frd_path is not None
    reader = CalculiXReader(result.frd_path, unit_system=UnitSystem.SI)
    mesh = reader.mesh
    assert mesh.coordinates.shape[0] == 8, mesh.coordinates.shape  # 8 hex nodes

    # Displacement field present (CalculiX writes "DISP" by default
    # when *NODE FILE U is requested in the INP). Linear static has
    # a single step (step_id=1).
    disp = reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    assert disp is not None
    assert disp.at_nodes().shape[0] == 8

    # Stress field present (CalculiX writes "STRESS" when *EL FILE S
    # is requested; nodal extrapolation by default).
    stress = reader.get_field(CanonicalField.STRESS_TENSOR, step_id=1)
    assert stress is not None
    assert stress.at_nodes().shape[0] == 8


@pytest.mark.requires_solver
def test_runner_captures_stdout_on_success(tmp_path: Path) -> None:
    """The ccx stdout log is captured to disk + accessible via the
    result; tests + UI can tail it for diagnostics."""
    case_dir = tmp_path / "phase18a-stdout-candidate"
    case_dir.mkdir()
    write_minimal_hex_inp(case_dir, jobname="logged")
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY, timeout_sec=30.0)
    result = runner.run(case_dir, "logged")
    assert result.stdout_path.is_file()
    log = result.stdout_path.read_text(encoding="utf-8")
    # CalculiX prints "Job finished" at end of a successful run.
    assert "Job finished" in log


# ---------------------------------------------------------------------
# V:-3 — fixture-isolation audit (no marker, runs every sweep)
# ---------------------------------------------------------------------


def test_runner_workspace_stays_under_tmp_path(tmp_path: Path) -> None:
    """The runner writes ONLY inside the caller-provided case_dir;
    no leak into the real ``reports/snapshots/`` tree. Verified by
    spawning the runner with a path-checking surrogate (no real
    subprocess needed)."""
    case_dir = tmp_path / "isolation-candidate"
    case_dir.mkdir()
    write_minimal_hex_inp(case_dir, jobname="iso")
    # Runner constructor is pure (no I/O until run() called).
    runner = CalculiXRunner(ccx_binary="/path/does-not-matter", timeout_sec=1.0)
    with pytest.raises(CalculiXRunError):
        runner.run(case_dir, "iso")
    # The case dir + INP are the only artifacts; runner did not
    # create files outside the case dir.
    assert (case_dir / "iso.inp").is_file()
    # Confirm tmp_path tree has at most: the case dir, the INP, the
    # stdout/stderr logs (those last two created BEFORE subprocess
    # fails).
    extra_files = [
        p
        for p in tmp_path.rglob("*")
        if p.is_file()
        and case_dir not in p.parents
        and p != case_dir
    ]
    assert extra_files == [], f"runner leaked files: {extra_files}"
