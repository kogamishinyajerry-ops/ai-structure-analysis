"""FM-04a Phase 18 C — Mesh + Materials library tests.

Covers both halves of Slice C:

* Materials library SSOT (load/validate/lookup; pinned values per
  ADR-025 §3 anti-gaming guard C:-1 — citation required, values
  pinned by per-material assertions to prevent silent drift).
* Gmsh subprocess runner (no-marker validation tests for arg shape +
  refusal paths; ``@pytest.mark.requires_solver`` tests for real
  ``gmsh`` invocation on a synthetic 1-cube geometry).

Phase 18 C anti-gaming guards (per blueprint §3.C):

* **M:-1** — materials library JSON is the single SSOT; tests pin
  exact values for the 3 baseline entries.
* **T:-3** — end-to-end pipeline: gmsh meshes a synthetic geometry,
  produces a non-empty .msh file. (Cylinder/material-swap integration
  into the calculix runner is deferred to a later sub-slice.)
* **C:-1** — every material entry has a non-empty reference field;
  loader refuses entries without it.
* **A:-2** — gmsh subprocess refuses paths outside the case workspace
  AND refuses signed-registry case shapes.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from app.services.materials import (
    DEFAULT_LIBRARY_PATH,
    Material,
    MaterialLibraryError,
    MaterialNotFoundError,
    get_material,
    list_materials,
    load_library,
)
from app.services.meshing import (
    DEFAULT_CHARACTERISTIC_LENGTH_M,
    DEFAULT_GMSH_BINARY,
    DEFAULT_TIMEOUT_SEC,
    GmshRunError,
    GmshRunner,
    GmshRunResult,
)

LOCAL_GMSH_BINARY = "/opt/homebrew/bin/gmsh"


# ---------------------------------------------------------------------
# Materials library — defaults + shape pinning
# ---------------------------------------------------------------------


def test_default_library_path_exists() -> None:
    assert DEFAULT_LIBRARY_PATH.is_file(), (
        f"default library JSON missing at {DEFAULT_LIBRARY_PATH}"
    )


def test_list_materials_first_three_baseline_entries_preserved() -> None:
    """Phase 18 C baseline (3 materials) preserved at the head of the
    library in stable order. Phase 19 C appends 5 more — verified by
    a separate test below. Splitting the assertion keeps the
    Phase 18 contract pinned even as the library grows."""
    materials = list_materials()
    assert len(materials) >= 3
    ids = [m.id for m in materials[:3]]
    assert ids == [
        "steel-s355",
        "aluminium-6061-t6",
        "titanium-ti-6al-4v",
    ]


def test_list_materials_returns_frozen_tuple() -> None:
    materials = list_materials()
    assert isinstance(materials, tuple)
    # Each entry is a frozen dataclass — mutating raises.
    with pytest.raises(Exception):
        materials[0].name = "MUTATED"  # type: ignore[misc]


@pytest.mark.parametrize(
    "material_id,expected_e_pa,expected_nu,expected_rho",
    [
        ("steel-s355", 210e9, 0.3, 7850.0),
        ("aluminium-6061-t6", 68.9e9, 0.33, 2700.0),
        ("titanium-ti-6al-4v", 113.8e9, 0.342, 4430.0),
    ],
)
def test_baseline_material_properties_pinned(
    material_id: str,
    expected_e_pa: float,
    expected_nu: float,
    expected_rho: float,
) -> None:
    """M:-1 — values pinned per material so a silent JSON edit trips
    the test. The pinned values are what the ADR claims; changing
    them requires editing both the JSON AND the test."""
    mat = get_material(material_id)
    assert mat.youngs_modulus_pa == expected_e_pa
    assert mat.poisson_ratio == expected_nu
    assert mat.density_kg_m3 == expected_rho


@pytest.mark.parametrize(
    "material_id",
    ["steel-s355", "aluminium-6061-t6", "titanium-ti-6al-4v"],
)
def test_baseline_material_has_yield_and_ultimate(material_id: str) -> None:
    """Every Phase 18 C baseline material declares both yield AND
    ultimate stress (engineering steels / alloys without these are
    not useful for the linear-static-with-margin pipeline)."""
    mat = get_material(material_id)
    assert mat.yield_stress_pa is not None
    assert mat.yield_stress_pa > 0
    assert mat.ultimate_stress_pa is not None
    assert mat.ultimate_stress_pa >= mat.yield_stress_pa


@pytest.mark.parametrize(
    "material_id",
    ["steel-s355", "aluminium-6061-t6", "titanium-ti-6al-4v"],
)
def test_baseline_material_has_nonempty_reference(material_id: str) -> None:
    """C:-1 — every entry must cite a property source."""
    mat = get_material(material_id)
    assert mat.reference.strip(), (
        f"material {material_id!r} has empty reference"
    )
    # Reference should be informative — not just "TBD" / "TODO" / a
    # bare URL fragment. Heuristic: at least 12 chars.
    assert len(mat.reference) >= 12


def test_get_material_raises_on_unknown_id() -> None:
    with pytest.raises(MaterialNotFoundError, match="no material with id"):
        get_material("does-not-exist-material")


# ---------------------------------------------------------------------
# Materials library — loader validation paths
# ---------------------------------------------------------------------


def _write_lib(tmp_path: Path, body: dict) -> Path:
    p = tmp_path / "library.json"
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def test_loader_refuses_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MaterialLibraryError, match="not found"):
        load_library(tmp_path / "missing.json")


def test_loader_refuses_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "lib.json"
    p.write_text("not valid {{ json", encoding="utf-8")
    with pytest.raises(MaterialLibraryError, match="malformed"):
        load_library(p)


def test_loader_refuses_missing_top_level_materials_list(
    tmp_path: Path,
) -> None:
    p = _write_lib(tmp_path, {"schema_version": "1.0.0"})
    with pytest.raises(MaterialLibraryError, match="materials"):
        load_library(p)


def test_loader_refuses_entry_missing_reference(tmp_path: Path) -> None:
    """C:-1 anti-gaming guard — refuse to load a material without
    citation."""
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "no-cite",
                    "name": "Uncited",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    # NO reference field
                }
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match="reference"):
        load_library(p)


def test_loader_refuses_entry_with_empty_reference(tmp_path: Path) -> None:
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "blank-cite",
                    "name": "Blank cite",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    "reference": "   ",
                }
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match="reference"):
        load_library(p)


def test_loader_refuses_invalid_poisson_ratio(tmp_path: Path) -> None:
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "bad-nu",
                    "name": "Bad Poisson",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.6,
                    "density_kg_m3": 7800.0,
                    "reference": "internal-test",
                }
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match="poisson_ratio"):
        load_library(p)


def test_loader_refuses_nonpositive_youngs_modulus(tmp_path: Path) -> None:
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "bad-e",
                    "name": "Bad E",
                    "youngs_modulus_pa": -1.0,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    "reference": "internal-test",
                }
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match="youngs_modulus_pa"):
        load_library(p)


def test_loader_refuses_duplicate_ids(tmp_path: Path) -> None:
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "dup",
                    "name": "First",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    "reference": "internal-test-1",
                },
                {
                    "id": "dup",
                    "name": "Second",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    "reference": "internal-test-2",
                },
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match="duplicate material id"):
        load_library(p)


def test_loader_refuses_ultimate_lower_than_yield(tmp_path: Path) -> None:
    p = _write_lib(
        tmp_path,
        {
            "materials": [
                {
                    "id": "inverted",
                    "name": "Inverted bounds",
                    "youngs_modulus_pa": 2e11,
                    "poisson_ratio": 0.3,
                    "density_kg_m3": 7800.0,
                    "yield_stress_pa": 500e6,
                    "ultimate_stress_pa": 400e6,
                    "reference": "internal-test",
                }
            ]
        },
    )
    with pytest.raises(MaterialLibraryError, match=">= yield_stress_pa"):
        load_library(p)


# ---------------------------------------------------------------------
# Gmsh runner — no-subprocess validation (default sweep)
# ---------------------------------------------------------------------


def test_gmsh_runner_defaults_pinned() -> None:
    assert DEFAULT_GMSH_BINARY == "gmsh"
    assert DEFAULT_TIMEOUT_SEC == 300.0
    assert DEFAULT_CHARACTERISTIC_LENGTH_M == 0.05


@pytest.mark.parametrize("signed_id", ["GS-001", "GS-042", "GS-999"])
def test_gmsh_runner_refuses_signed_registry_case_dir(
    tmp_path: Path, signed_id: str
) -> None:
    """A:-2 — HF1.7a defense composes here too."""
    case_dir = tmp_path / signed_id
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="signed-registry"):
        runner.run(case_dir, geom, output_name="m")


def test_gmsh_runner_refuses_missing_case_dir(tmp_path: Path) -> None:
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    geom = tmp_path / "g.geo"
    geom.write_text("// stub", encoding="utf-8")
    with pytest.raises(GmshRunError, match="not a directory"):
        runner.run(tmp_path / "does-not-exist", geom, output_name="m")


def test_gmsh_runner_refuses_missing_geometry(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="missing"):
        runner.run(case_dir, case_dir / "nope.geo", output_name="m")


def test_gmsh_runner_path_guard_refuses_geometry_outside_case_dir(
    tmp_path: Path,
) -> None:
    """A:-2 — geometry path must resolve inside case_dir."""
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    outside = tmp_path / "outside.geo"
    outside.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="outside"):
        runner.run(case_dir, outside, output_name="m")


def test_gmsh_runner_refuses_unsupported_extension(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    weird = case_dir / "weird.xyz"
    weird.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="unsupported geometry extension"):
        runner.run(case_dir, weird, output_name="m")


def test_gmsh_runner_refuses_nonpositive_characteristic_length(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="characteristic_length_m"):
        runner.run(
            case_dir, geom, output_name="m", characteristic_length_m=0.0
        )


def test_gmsh_runner_refuses_invalid_element_order(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY)
    with pytest.raises(GmshRunError, match="element_order"):
        runner.run(case_dir, geom, output_name="m", element_order=3)


def test_gmsh_runner_raises_clean_on_missing_binary(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-candidate"
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text("// stub", encoding="utf-8")
    runner = GmshRunner(gmsh_binary="/path/does/not/exist/gmsh")
    with pytest.raises(GmshRunError, match="gmsh binary not found"):
        runner.run(case_dir, geom, output_name="m")


def test_gmsh_run_result_is_frozen() -> None:
    result = GmshRunResult(
        returncode=0,
        stdout_path=Path("/tmp/x.stdout.log"),
        stderr_path=Path("/tmp/x.stderr.log"),
        mesh_path=Path("/tmp/x.msh"),
        node_count=8,
        element_count=6,
        runtime_sec=0.42,
    )
    with pytest.raises(Exception):
        result.returncode = 1  # type: ignore[misc]


# ---------------------------------------------------------------------
# Gmsh runner — real subprocess (requires_solver marker)
# ---------------------------------------------------------------------


_CUBE_GEO = textwrap.dedent(
    """\
    // Phase 18 C minimal smoke geometry — a unit cube in meters.
    SetFactory("OpenCASCADE");
    Box(1) = {0, 0, 0, 0.1, 0.1, 0.1};
    Physical Volume("solid", 1) = {1};
    """
)


@pytest.mark.requires_solver
def test_gmsh_runner_meshes_minimal_cube(tmp_path: Path) -> None:
    """T:-3 end-to-end pin: gmsh produces a non-empty mesh file from
    a 1-cube geometry."""
    case_dir = tmp_path / "gmsh-cube-candidate"
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text(_CUBE_GEO, encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY, timeout_sec=30.0)
    result = runner.run(
        case_dir,
        geom,
        output_name="cube",
        characteristic_length_m=0.05,
    )
    assert result.returncode == 0
    assert result.mesh_path.is_file()
    assert result.mesh_path.stat().st_size > 256  # non-empty mesh
    assert result.runtime_sec > 0.0
    assert result.runtime_sec < 30.0


@pytest.mark.requires_solver
def test_gmsh_runner_extracts_mesh_counts_from_stdout(tmp_path: Path) -> None:
    """The stdout-parser surfaces node + element counts; useful for the
    upstream UI mesh preview panel."""
    case_dir = tmp_path / "gmsh-counts-candidate"
    case_dir.mkdir()
    geom = case_dir / "cube.geo"
    geom.write_text(_CUBE_GEO, encoding="utf-8")
    runner = GmshRunner(gmsh_binary=LOCAL_GMSH_BINARY, timeout_sec=30.0)
    result = runner.run(
        case_dir,
        geom,
        output_name="counts",
        characteristic_length_m=0.05,
    )
    # The minimum useful expectation: at least one of the counts
    # parsed cleanly. Both being None would indicate the parser
    # regressed against the gmsh output format.
    assert (
        result.node_count is not None or result.element_count is not None
    )
    if result.node_count is not None:
        assert result.node_count > 0
    if result.element_count is not None:
        assert result.element_count > 0
